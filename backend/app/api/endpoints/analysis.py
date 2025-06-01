from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Response
from pydantic import BaseModel, EmailStr, ValidationError
from typing import Optional
from sqlalchemy.orm import Session
import json
import uuid
import os
import time
from datetime import datetime
import asyncio
import threading
from uuid import UUID
from fastapi import status

# Import our core processing modules
from app.core.llm_processing import parse_file_to_structured_data, parse_file_with_optimal_strategy, convert_two_pass_to_single_pass_format
from app.core.compliance_rules import detect_compliance_violations_with_costs, detect_duplicate_employees
from app.core.reporting import (
    calculate_kpi_tiles_data,
    generate_staffing_density_heatmap_data,
    compile_general_compliance_violations,
    generate_employee_summary_table_data,
    get_all_violation_types_with_advice
)
from app.models.schemas import (
    LeadCaptureData, 
    FinalAnalysisReport
)
from app.db import get_db, SavedReport, Lead
from app.db import repositories
from app.db.supabase_client import log_lead_to_supabase, log_analysis_to_supabase
from app.core.logging_config import (
    get_logger, 
    log_analysis_start, 
    log_parsing_result, 
    log_compliance_analysis,
    log_database_operation,
    log_performance_metric
)
# Import new error handling system (task 5.3)
from app.core.error_handlers import (
    ErrorHandler,
    TimesheetAnalysisError,
    FileValidationError,
    FileSizeError,
    ParsingError,
    LLMServiceError,
    ComplianceAnalysisError,
    DatabaseError,
    validate_file_upload,
    map_core_exceptions,
    ErrorCategory,
    ErrorSeverity
)

# Initialize logger for this module
logger = get_logger("analysis")

router = APIRouter()

class LeadData(BaseModel):
    manager_name: str
    manager_email: EmailStr
    manager_phone: Optional[str] = None
    store_name: str
    store_address: str

class LeadSubmissionRequest(BaseModel):
    analysis_id: str
    manager_name: str
    email: EmailStr
    phone: Optional[str] = None
    store_name: str
    store_address: str

class ProcessingOptions(BaseModel):
    """Processing options for controlling analysis behavior"""
    enable_two_pass: Optional[bool] = None
    force_two_pass: Optional[bool] = None
    force_single_pass: Optional[bool] = None
    batch_size: Optional[int] = None
    timeout_per_employee: Optional[float] = None
    max_retries: Optional[int] = None
    enable_deduplication: Optional[bool] = None
    strict_validation: Optional[bool] = None

@router.post("/submit-lead")
async def submit_lead_data(lead_request: LeadSubmissionRequest, db: Session = Depends(get_db)):
    """
    Submit lead capture data to be stored in the database.
    This endpoint can now receive lead information immediately after file upload,
    even before analysis is complete.
    """
    lead_logger = get_logger("analysis", {"request_id": lead_request.analysis_id})
    
    try:
        lead_logger.info(f"Lead submission started for manager: {lead_request.manager_name}")
        
        # Check if analysis_id exists in saved reports
        saved_report = db.query(SavedReport).filter(SavedReport.id == lead_request.analysis_id).first()
        
        if not saved_report:
            lead_logger.warning(f"Analysis report not found for ID: {lead_request.analysis_id}")
            error = TimesheetAnalysisError(
                message="Analysis report not found for the provided ID",
                code="ANALYSIS_NOT_FOUND",
                category="not_found",
                severity="low",
                http_status=404,
                suggestion="Verify the analysis ID is correct or run a new analysis"
            )
            raise ErrorHandler.create_http_exception(error, lead_request.analysis_id)
        
        # Update the saved report with lead information
        saved_report.manager_name = lead_request.manager_name
        saved_report.manager_email = lead_request.email
        saved_report.manager_phone = lead_request.phone
        saved_report.store_name = lead_request.store_name
        saved_report.store_address = lead_request.store_address
        db.commit()
        
        # Create lead record
        lead_id = str(uuid.uuid4())
        lead = Lead(
            id=lead_id,
            analysis_id=lead_request.analysis_id,
            manager_name=lead_request.manager_name,
            email=lead_request.email,
            phone=lead_request.phone,
            store_name=lead_request.store_name,
            store_address=lead_request.store_address
        )
        
        db.add(lead)
        db.commit()
        
        lead_logger.info(
            f"Lead submitted successfully | Manager: {lead_request.manager_name} | "
            f"Email: {lead_request.email} | Store: {lead_request.store_name} | "
            f"Lead ID: {lead_id}"
        )
        
        log_database_operation(
            lead_logger, "INSERT", "leads", True, lead_id
        )
        
        # Log lead data to Supabase (task 5.2.1)
        supabase_result = await log_lead_to_supabase(
            manager_name=lead_request.manager_name,
            email=lead_request.email,
            store_name=lead_request.store_name,
            store_address=lead_request.store_address,
            phone=lead_request.phone,
            analysis_id=lead_request.analysis_id,
            request_id=lead_request.analysis_id
        )
        
        if supabase_result["success"]:
            lead_logger.info(f"Lead data also logged to Supabase successfully")
        else:
            lead_logger.warning(f"Failed to log lead to Supabase: {supabase_result.get('error', 'Unknown error')}")
        
        # Return success response
        response = {
            "success": True,
            "message": "Lead data submitted successfully",
            "lead_id": lead_id,
            "analysis_id": lead_request.analysis_id
        }
        
        # Include Supabase status in response for debugging
        if not supabase_result["success"]:
            response["supabase_warning"] = f"Supabase logging failed: {supabase_result.get('error', 'Unknown error')}"
        
        return response
        
    except HTTPException:
        # Re-raise HTTPExceptions from error handling
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        lead_logger.error(f"Failed to submit lead data: {str(e)}")
        log_database_operation(
            lead_logger, "INSERT", "leads", False, None, str(e)
        )
        
        # Use standardized error handling (task 5.3)
        mapped_error = map_core_exceptions(e, "lead_submission")
        if isinstance(mapped_error, DatabaseError):
            # Already mapped correctly
            raise ErrorHandler.create_http_exception(mapped_error, lead_request.analysis_id)
        else:
            # Create database error
            db_error = DatabaseError(
                message=f"Failed to submit lead data: {str(e)}",
                operation="lead_submission"
            )
            raise ErrorHandler.create_http_exception(db_error, lead_request.analysis_id)

async def _run_analysis_in_background(
    file_bytes: bytes,
    request_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    db_session: Session
):
    """
    Run the actual analysis in a background task.
    This would typically be handled by a task queue in production.
    """
    # Create a new database session for the background task
    from app.db import SessionLocal
    db = SessionLocal()
    
    try:
        request_logger = get_logger("analysis", {"request_id": request_id})
        request_logger.info(f"Starting background analysis for request {request_id}")
        
        # Use the existing analyze logic here
        # This is essentially the same as the analyze_timesheet function
        # but working with the existing placeholder record
        
        # Determine debug directory (optional)
        debug_dir = os.getenv("DEBUG_DIR")
        if debug_dir:
            debug_dir = os.path.join(debug_dir, f"analysis_{request_id}")
        
        # Step 1: Parse file to structured data using optimal LLM strategy
        parsing_start_time = time.time()
        processing_metadata = None  # Initialize metadata storage
        try:
            # Use the new integrated processing function
            processing_result = await parse_file_with_optimal_strategy(
                file_bytes=file_bytes,
                mime_type=content_type or f"application/{filename.split('.')[-1].lower()}",
                original_filename=filename,
                debug_dir=debug_dir
            )
            
            # Handle both single-pass and two-pass results
            if isinstance(processing_result, dict):
                # Two-pass result - convert to single-pass format for backward compatibility
                llm_output = convert_two_pass_to_single_pass_format(processing_result)
                
                # Capture processing metadata for the report
                processing_metadata = processing_result.get('processing_metadata', {})
                request_logger.info(f"Two-pass processing completed: {processing_metadata.get('processing_mode', 'unknown')}")
                
                # Log additional two-pass metrics
                if 'performance_metrics' in processing_metadata:
                    metrics = processing_metadata['performance_metrics']
                    request_logger.info(
                        f"Two-pass metrics: Total={metrics.get('total_workflow_duration_seconds', 0):.2f}s, "
                        f"Discovery={metrics.get('discovery_duration_seconds', 0):.2f}s, "
                        f"Parallel={metrics.get('parallel_processing_duration_seconds', 0):.2f}s"
                    )
            else:
                # Single-pass result (LLMProcessingOutput)
                llm_output = processing_result
                processing_metadata = {
                    'processing_mode': 'single_pass',
                    'decision_reason': 'Single-pass processing used'
                }
                request_logger.info("Single-pass processing completed")
            
            parsing_end_time = time.time()
            parsing_duration = parsing_end_time - parsing_start_time
            
            events_found = len(llm_output.punch_events) if llm_output.punch_events else 0
            parsing_success = events_found > 0
            
            # Log parsing result
            log_parsing_result(
                request_logger, request_id, filename, parsing_success,
                events_found, parsing_duration, llm_output.parsing_issues
            )
            
            if not llm_output.punch_events:
                request_logger.error("No punch events found in file")
                # Update the placeholder report with error status
                placeholder_report = db.query(SavedReport).filter(SavedReport.id == request_id).first()
                if placeholder_report:
                    placeholder_report.report_data = json.dumps({
                        "request_id": request_id,
                        "original_filename": filename,
                        "status": "error_parsing_failed",
                        "status_message": "No punch events could be extracted from the file",
                        "error": "No punch events found in file"
                    })
                    db.commit()
                return
        
        except Exception as e:
            request_logger.error(f"LLM parsing failed: {str(e)}")
            # Update the placeholder report with error status
            placeholder_report = db.query(SavedReport).filter(SavedReport.id == request_id).first()
            if placeholder_report:
                placeholder_report.report_data = json.dumps({
                    "request_id": request_id,
                    "original_filename": filename,
                    "status": "error_parsing_failed",
                    "status_message": f"Failed to parse file: {str(e)}",
                    "error": str(e)
                })
                db.commit()
            return
        
        # Step 2: Detect duplicate employees and get warnings
        duplicate_groups = detect_duplicate_employees(llm_output.punch_events)
        duplicate_warnings = []
        if duplicate_groups:
            for canonical_name, variations in duplicate_groups.items():
                if len(variations) > 1:
                    warning_msg = f"Potential duplicate employee '{canonical_name}' found with variations: {', '.join(variations)}"
                    duplicate_warnings.append(warning_msg)
        
        # Step 3: Run compliance analysis with cost calculations
        compliance_start_time = time.time()
        try:
            # Generate KPI data
            kpis = calculate_kpi_tiles_data(llm_output.punch_events)
            
            # Generate staffing density heatmap
            heatmap_data = generate_staffing_density_heatmap_data(llm_output.punch_events)
            
            # Compile all violations
            all_violations = compile_general_compliance_violations(llm_output.punch_events)
            
            # Generate employee summaries
            employee_summaries = generate_employee_summary_table_data(llm_output.punch_events)
            
            compliance_end_time = time.time()
            compliance_duration = compliance_end_time - compliance_start_time
            
            # Log compliance analysis results
            log_compliance_analysis(
                request_logger, request_id, len(all_violations),
                len(employee_summaries), compliance_duration
            )
            
            # Generate overall summary text
            overall_summary = _generate_overall_report_summary(
                kpis=kpis,
                total_violations=len(all_violations),
                employee_count=len(employee_summaries),
                duplicate_warnings=duplicate_warnings
            )
            
            # Determine status
            status = "success"
            status_message = None
            
            if llm_output.parsing_issues or duplicate_warnings:
                status = "partial_success_with_warnings"
                status_message = "Analysis completed with some warnings. Please review parsing issues and duplicate name warnings."
            
            # Create final report
            report = FinalAnalysisReport(
                request_id=request_id,
                original_filename=filename,
                status=status,
                status_message=status_message,
                kpis=kpis,
                staffing_density_heatmap=heatmap_data,
                all_identified_violations=all_violations,
                employee_summaries=employee_summaries,
                duplicate_name_warnings=duplicate_warnings,
                parsing_issues_summary=llm_output.parsing_issues or [],
                overall_report_summary_text=overall_summary,
                processing_metadata=processing_metadata,
                processing_mode=processing_metadata.get('processing_mode') if processing_metadata else None,
                discovered_employees=processing_metadata.get('discovered_employees') if processing_metadata else None,
                quality_score=processing_metadata.get('workflow_stages', {}).get('stitching', {}).get('quality_score') if processing_metadata else None
            )
            
            # Update the placeholder report with actual analysis data
            placeholder_report = db.query(SavedReport).filter(SavedReport.id == request_id).first()
            if placeholder_report:
                employee_count = len(employee_summaries) if employee_summaries else 0
                total_violations = len(all_violations) if all_violations else 0
                total_hours = kpis.total_scheduled_labor_hours if kpis else 0
                overtime_cost = kpis.estimated_overtime_cost if kpis else 0
                
                placeholder_report.report_data = report.model_dump_json()
                placeholder_report.employee_count = employee_count
                placeholder_report.total_violations = total_violations
                placeholder_report.total_hours = total_hours
                placeholder_report.overtime_cost = overtime_cost
                
                db.commit()
                
                request_logger.info(f"Background analysis completed successfully for request {request_id}")
            
        except Exception as e:
            request_logger.error(f"Compliance analysis failed: {str(e)}")
            # Update the placeholder report with error status
            placeholder_report = db.query(SavedReport).filter(SavedReport.id == request_id).first()
            if placeholder_report:
                placeholder_report.report_data = json.dumps({
                    "request_id": request_id,
                    "original_filename": filename,
                    "status": "error_analysis_failed",
                    "status_message": f"Failed to complete compliance analysis: {str(e)}",
                    "error": str(e)
                })
                db.commit()
            
    except Exception as e:
        request_logger.error(f"Background analysis failed with unexpected error: {str(e)}")
    finally:
        db.close()

@router.post("/start-analysis")
async def start_analysis(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Start timesheet analysis and return request ID immediately.
    The actual analysis continues in the background.
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request_logger = get_logger("analysis", {"request_id": request_id})
    
    # Get file information
    content_type = file.content_type
    filename = file.filename or "unknown_file"
    file_extension = filename.split(".")[-1].lower() if "." in filename else None
    
    # Read file bytes first to get size
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
    except Exception as e:
        request_logger.error(f"Failed to read uploaded file: {str(e)}")
        file_error = FileValidationError(
            message="Failed to read uploaded file",
            filename=filename
        )
        raise ErrorHandler.create_http_exception(file_error, request_id)
    
    # Validate file using new error handling system
    try:
        validate_file_upload(file_bytes, filename, content_type)
    except (FileValidationError, FileSizeError) as e:
        request_logger.warning(f"File validation failed: {e.message}")
        raise ErrorHandler.create_http_exception(e, request_id)
    
    # Log analysis start
    log_analysis_start(
        request_logger, request_id, filename, file_size, 
        content_type or "unknown", file_extension
    )
    
    # Create a placeholder SavedReport immediately
    try:
        placeholder_report = SavedReport(
            id=request_id,
            original_filename=filename,
            report_data="{}",  # Empty JSON, will be updated when analysis completes
            file_size=file_size,
            file_type=content_type or file_extension,
            employee_count=0,  # Will be updated
            total_violations=0,  # Will be updated
            total_hours=0.0,  # Will be updated
            overtime_cost=0.0  # Will be updated
        )
        
        db.add(placeholder_report)
        db.commit()
        
        request_logger.info(f"Placeholder report created for immediate lead submission | ID: {request_id}")
        log_database_operation(
            request_logger, "INSERT", "saved_reports", True, request_id
        )
        
    except Exception as e:
        request_logger.error(f"Failed to create placeholder report: {str(e)}")
        db.rollback()
        db_error = DatabaseError(
            message=f"Failed to create analysis record: {str(e)}",
            operation="create_placeholder"
        )
        raise ErrorHandler.create_http_exception(db_error, request_id)
    
    # Start the analysis in the background
    # Note: In a production system, you'd want to use Celery or similar for background tasks
    def run_background_analysis():
        # Add a small delay to ensure the main transaction is committed
        time.sleep(0.1)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_analysis_in_background(
                file_bytes, request_id, filename, content_type, file_size, db
            ))
        finally:
            loop.close()
    
    # Start the background thread
    analysis_thread = threading.Thread(target=run_background_analysis)
    analysis_thread.daemon = True  # Dies when main thread dies
    analysis_thread.start()
    
    # Return the request ID immediately so lead submission can happen
    return {
        "success": True,
        "request_id": request_id,
        "message": "Analysis started successfully",
        "filename": filename,
        "status": "processing"
    }

@router.post("/analyze")
async def analyze_timesheet(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request_logger = get_logger("analysis", {"request_id": request_id})
    
    # Track overall processing time
    analysis_start_time = time.time()
    
    # Get file information
    content_type = file.content_type
    filename = file.filename or "unknown_file"
    file_extension = filename.split(".")[-1].lower() if "." in filename else None
    
    # Read file bytes first to get size
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
    except Exception as e:
        request_logger.error(f"Failed to read uploaded file: {str(e)}")
        file_error = FileValidationError(
            message="Failed to read uploaded file",
            filename=filename
        )
        raise ErrorHandler.create_http_exception(file_error, request_id)
    
    # Validate file using new error handling system (task 5.3)
    try:
        validate_file_upload(file_bytes, filename, content_type)
    except (FileValidationError, FileSizeError) as e:
        request_logger.warning(f"File validation failed: {e.message}")
        raise ErrorHandler.create_http_exception(e, request_id)
    
    # Log analysis start with file details (task 5.1.1 - raw input type)
    log_analysis_start(
        request_logger, request_id, filename, file_size, 
        content_type or "unknown", file_extension
    )

    try:
        # Determine debug directory (optional)
        debug_dir = os.getenv("DEBUG_DIR")
        if debug_dir:
            debug_dir = os.path.join(debug_dir, f"analysis_{request_id}")
        
        # Step 1: Parse file to structured data using optimal LLM strategy
        parsing_start_time = time.time()
        processing_metadata = None  # Initialize metadata storage
        try:
            # Use the new integrated processing function
            processing_result = await parse_file_with_optimal_strategy(
                file_bytes=file_bytes,
                mime_type=content_type or f"application/{file_extension}",
                original_filename=filename,
                debug_dir=debug_dir
            )
            
            # Handle both single-pass and two-pass results
            if isinstance(processing_result, dict):
                # Two-pass result - convert to single-pass format for backward compatibility
                llm_output = convert_two_pass_to_single_pass_format(processing_result)
                
                # Capture processing metadata for the report
                processing_metadata = processing_result.get('processing_metadata', {})
                request_logger.info(f"Two-pass processing completed: {processing_metadata.get('processing_mode', 'unknown')}")
                
                # Log additional two-pass metrics
                if 'performance_metrics' in processing_metadata:
                    metrics = processing_metadata['performance_metrics']
                    request_logger.info(
                        f"Two-pass metrics: Total={metrics.get('total_workflow_duration_seconds', 0):.2f}s, "
                        f"Discovery={metrics.get('discovery_duration_seconds', 0):.2f}s, "
                        f"Parallel={metrics.get('parallel_processing_duration_seconds', 0):.2f}s"
                    )
            else:
                # Single-pass result (LLMProcessingOutput)
                llm_output = processing_result
                processing_metadata = {
                    'processing_mode': 'single_pass',
                    'decision_reason': 'Single-pass processing used'
                }
                request_logger.info("Single-pass processing completed")
            
            parsing_end_time = time.time()
            parsing_duration = parsing_end_time - parsing_start_time
            
            events_found = len(llm_output.punch_events) if llm_output.punch_events else 0
            parsing_success = events_found > 0
            
            # Log parsing result (task 5.1.1 - parse success/failure and processing time)
            log_parsing_result(
                request_logger, request_id, filename, parsing_success,
                events_found, parsing_duration, llm_output.parsing_issues
            )
            
            if not llm_output.punch_events:
                request_logger.error("No punch events found in file")
                
                # Log parsing failure to Supabase (task 5.2.2)
                total_duration = time.time() - analysis_start_time
                supabase_result = await log_analysis_to_supabase(
                    request_id=request_id,
                    original_filename=filename,
                    status="error_parsing_failed",
                    file_size=file_size,
                    file_type=content_type or file_extension,
                    processing_time_seconds=total_duration,
                    error_message="No punch events found in file"
                )
                
                # Use standardized error handling (task 5.3)
                parsing_error = ParsingError(
                    message="No punch events could be extracted from the file",
                    filename=filename,
                    parsing_issues=llm_output.parsing_issues,
                    suggestion="Please verify the file contains timesheet data with employee names, dates, and clock in/out times"
                )
                raise ErrorHandler.create_http_exception(parsing_error, request_id)
        
        except (FileValidationError, ParsingError, LLMServiceError) as e:
            # These are already standardized errors - re-raise as HTTPException
            parsing_duration = time.time() - parsing_start_time
            log_parsing_result(
                request_logger, request_id, filename, False, 0, parsing_duration
            )
            
            # Log parsing failure to Supabase (task 5.2.2)
            total_duration = time.time() - analysis_start_time
            supabase_result = await log_analysis_to_supabase(
                request_id=request_id,
                original_filename=filename,
                status="error_parsing_failed",
                file_size=file_size,
                file_type=content_type or file_extension,
                processing_time_seconds=total_duration,
                error_message=e.message
            )
            
            raise ErrorHandler.create_http_exception(e, request_id)
            
        except Exception as e:
            parsing_duration = time.time() - parsing_start_time
            log_parsing_result(
                request_logger, request_id, filename, False, 0, parsing_duration
            )
            request_logger.error(f"LLM parsing failed: {str(e)}")
            
            # Log parsing failure to Supabase (task 5.2.2)
            total_duration = time.time() - analysis_start_time
            supabase_result = await log_analysis_to_supabase(
                request_id=request_id,
                original_filename=filename,
                status="error_parsing_failed",
                file_size=file_size,
                file_type=content_type or file_extension,
                processing_time_seconds=total_duration,
                error_message=f"LLM parsing failed: {str(e)}"
            )
            
            # Map to appropriate error type (task 5.3)
            mapped_error = map_core_exceptions(e, filename)
            raise ErrorHandler.create_http_exception(mapped_error, request_id)
        
        # Step 2: Detect duplicate employees and get warnings
        request_logger.debug("Detecting duplicate employees")
        duplicate_groups = detect_duplicate_employees(llm_output.punch_events)
        duplicate_warnings = []
        if duplicate_groups:
            for canonical_name, variations in duplicate_groups.items():
                if len(variations) > 1:
                    warning_msg = f"Potential duplicate employee '{canonical_name}' found with variations: {', '.join(variations)}"
                    duplicate_warnings.append(warning_msg)
                    request_logger.warning(f"Duplicate employee detected: {warning_msg}")
        
        # Step 3: Run compliance analysis with cost calculations
        compliance_start_time = time.time()
        try:
            request_logger.debug("Starting compliance analysis")
            
            # Generate KPI data
            kpis = calculate_kpi_tiles_data(llm_output.punch_events)
            
            # Generate staffing density heatmap
            heatmap_data = generate_staffing_density_heatmap_data(llm_output.punch_events)
            
            # Compile all violations
            all_violations = compile_general_compliance_violations(llm_output.punch_events)
            
            # Generate employee summaries
            employee_summaries = generate_employee_summary_table_data(llm_output.punch_events)
            
            compliance_end_time = time.time()
            compliance_duration = compliance_end_time - compliance_start_time
            
            # Log compliance analysis results
            log_compliance_analysis(
                request_logger, request_id, len(all_violations),
                len(employee_summaries), compliance_duration
            )
            
            # Generate overall summary text
            overall_summary = _generate_overall_report_summary(
                kpis=kpis,
                total_violations=len(all_violations),
                employee_count=len(employee_summaries),
                duplicate_warnings=duplicate_warnings
            )
            
            # Determine status
            status = "success"
            status_message = None
            
            if llm_output.parsing_issues or duplicate_warnings:
                status = "partial_success_with_warnings"
                status_message = "Analysis completed with some warnings. Please review parsing issues and duplicate name warnings."
            
            # Create final report
            report = FinalAnalysisReport(
                request_id=request_id,
                original_filename=filename,
                status=status,
                status_message=status_message,
                kpis=kpis,
                staffing_density_heatmap=heatmap_data,
                all_identified_violations=all_violations,
                employee_summaries=employee_summaries,
                duplicate_name_warnings=duplicate_warnings,
                parsing_issues_summary=llm_output.parsing_issues or [],
                overall_report_summary_text=overall_summary,
                processing_metadata=processing_metadata,
                processing_mode=processing_metadata.get('processing_mode') if processing_metadata else None,
                discovered_employees=processing_metadata.get('discovered_employees') if processing_metadata else None,
                quality_score=processing_metadata.get('workflow_stages', {}).get('stitching', {}).get('quality_score') if processing_metadata else None
            )
            
            # Automatically save successful reports to database
            try:
                employee_count = len(employee_summaries) if employee_summaries else 0
                total_violations = len(all_violations) if all_violations else 0
                total_hours = kpis.total_scheduled_labor_hours if kpis else 0
                overtime_cost = kpis.estimated_overtime_cost if kpis else 0
                
                # Check if a placeholder SavedReport already exists (from lead submission)
                existing_report = db.query(SavedReport).filter(SavedReport.id == request_id).first()
                is_update_operation = existing_report is not None
                
                if existing_report:
                    # Update the existing placeholder report with actual analysis data
                    request_logger.info(f"Updating existing placeholder report for ID: {request_id}")
                    existing_report.original_filename = filename
                    existing_report.report_data = report.model_dump_json()
                    existing_report.file_size = file_size
                    existing_report.file_type = content_type or file_extension
                    existing_report.employee_count = employee_count
                    existing_report.total_violations = total_violations
                    existing_report.total_hours = total_hours
                    existing_report.overtime_cost = overtime_cost
                    
                    db.commit()
                    
                    log_database_operation(
                        request_logger, "UPDATE", "saved_reports", True, request_id
                    )
                else:
                    # Create a new SavedReport (normal case when no lead was submitted first)
                    saved_report = SavedReport(
                        id=request_id,
                        original_filename=filename,
                        report_data=report.model_dump_json(),
                        file_size=file_size,
                        file_type=content_type or file_extension,
                        employee_count=employee_count,
                        total_violations=total_violations,
                        total_hours=total_hours,
                        overtime_cost=overtime_cost
                    )
                    
                    db.add(saved_report)
                    db.commit()
                    
                    log_database_operation(
                        request_logger, "INSERT", "saved_reports", True, request_id
                    )
                
                # Log analysis metadata to Supabase (task 5.2.2)
                total_duration = time.time() - analysis_start_time
                supabase_result = await log_analysis_to_supabase(
                    request_id=request_id,
                    original_filename=filename,
                    status=status,
                    file_size=file_size,
                    file_type=content_type or file_extension,
                    employee_count=employee_count,
                    total_violations=total_violations,
                    total_hours=total_hours,
                    overtime_cost=overtime_cost,
                    processing_time_seconds=total_duration
                )
                
                if supabase_result["success"]:
                    request_logger.info(f"Analysis metadata logged to Supabase successfully")
                else:
                    request_logger.warning(f"Failed to log analysis metadata to Supabase: {supabase_result.get('error', 'Unknown error')}")
                
            except Exception as save_error:
                request_logger.warning(f"Failed to save report to database: {save_error}")
                log_database_operation(
                    request_logger, "UPDATE" if is_update_operation else "INSERT", "saved_reports", False, request_id, str(save_error)
                )
                # Log database error but continue - don't fail the analysis if saving fails
                # The analysis was successful, we just couldn't save it
            
            # Log overall performance metrics
            total_duration = time.time() - analysis_start_time
            log_performance_metric(
                request_logger, "complete_analysis", total_duration,
                {
                    "parsing_time": parsing_duration,
                    "compliance_time": compliance_duration,
                    "events_processed": events_found,
                    "violations_found": len(all_violations),
                    "employees_analyzed": len(employee_summaries)
                }
            )
            
            request_logger.info(f"Analysis completed successfully | Status: {status}")
            return report
            
        except Exception as e:
            compliance_duration = time.time() - compliance_start_time
            request_logger.error(f"Compliance analysis failed: {str(e)}")
            
            # Log compliance analysis failure to Supabase (task 5.2.2)
            total_duration = time.time() - analysis_start_time
            supabase_result = await log_analysis_to_supabase(
                request_id=request_id,
                original_filename=filename,
                status="error_analysis_failed",
                file_size=file_size,
                file_type=content_type or file_extension,
                processing_time_seconds=total_duration,
                error_message=f"Compliance analysis failed: {str(e)}"
            )
            
            # Use standardized error handling (task 5.3)
            compliance_error = ComplianceAnalysisError(
                message=f"Failed to complete compliance analysis: {str(e)}"
            )
            raise ErrorHandler.create_http_exception(compliance_error, request_id)
    
    except HTTPException:
        # Re-raise HTTPExceptions from error handling (already standardized)
        total_duration = time.time() - analysis_start_time
        log_performance_metric(request_logger, "failed_analysis", total_duration)
        raise
    except Exception as e:
        # Catch-all for unexpected errors (task 5.3)
        total_duration = time.time() - analysis_start_time
        log_performance_metric(request_logger, "error_analysis", total_duration)
        request_logger.error(f"Unexpected error during analysis: {str(e)}")
        
        # Use the centralized error handler for unexpected errors
        raise ErrorHandler.handle_unexpected_error(e, "timesheet_analysis", request_id)

def _generate_overall_report_summary(
    kpis: any,
    total_violations: int,
    employee_count: int,
    duplicate_warnings: list
) -> str:
    """
    Generate a plain-language summary of the analysis results.
    
    Args:
        kpis: The KPI data object
        total_violations: Total number of violations found
        employee_count: Number of employees analyzed
        duplicate_warnings: List of duplicate name warnings
        
    Returns:
        Human-readable summary text
    """
    summary_parts = []
    
    # Basic statistics
    summary_parts.append(f"Analyzed timesheet data for {employee_count} employees.")
    summary_parts.append(f"Total labor hours: {kpis.total_scheduled_labor_hours:.1f} hours ({kpis.total_regular_hours:.1f} regular, {kpis.total_overtime_hours:.1f} overtime, {kpis.total_double_overtime_hours:.1f} double overtime).")
    
    # Compliance findings
    if total_violations == 0:
        summary_parts.append("Great news! No compliance violations were detected.")
    else:
        summary_parts.append(f"Found {total_violations} compliance violations that require attention.")
        
        # Highlight specific violation types
        violation_details = []
        if kpis.count_meal_break_violations > 0:
            violation_details.append(f"{kpis.count_meal_break_violations} meal break violations")
        if kpis.count_daily_overtime_violations > 0:
            violation_details.append(f"{kpis.count_daily_overtime_violations} daily overtime violations")
        if kpis.count_weekly_overtime_violations > 0:
            violation_details.append(f"{kpis.count_weekly_overtime_violations} weekly overtime violations")
        if kpis.count_rest_break_violations > 0:
            violation_details.append(f"{kpis.count_rest_break_violations} rest break violations")
        if kpis.count_daily_double_overtime_violations > 0:
            violation_details.append(f"{kpis.count_daily_double_overtime_violations} daily double overtime violations")
        
        if violation_details:
            summary_parts.append(f"Key issues include: {', '.join(violation_details[:3])}{'...' if len(violation_details) > 3 else ''}.")
    
    # Cost impact
    total_ot_cost = (kpis.estimated_overtime_cost or 0) + (kpis.estimated_double_overtime_cost or 0)
    if total_ot_cost > 0:
        summary_parts.append(f"Estimated additional labor costs from overtime premiums: ${total_ot_cost:.0f}.")
    
    # Warnings
    if duplicate_warnings:
        summary_parts.append(f"Note: {len(duplicate_warnings)} potential duplicate employee names detected - please verify employee records.")
    
    # Recommendations
    if total_violations > 0:
        summary_parts.append("Review the detailed violations list below and implement the suggested corrective actions to ensure compliance.")
    else:
        summary_parts.append("Continue monitoring timesheet compliance and consider implementing automated compliance checks.")
    
    return " ".join(summary_parts)

@router.get("/reports/{request_id}", 
            response_model=FinalAnalysisReport, 
            summary="Get Analysis Report by ID",
            description="Retrieve the full analysis report for a given request ID, including compliance results and punch event data.",
            responses={
                200: {"description": "Report found"},
                404: {"description": "Report not found"},
                500: {"description": "Internal server error"}
            }
)
async def get_report(request_id: UUID, db: Session = Depends(get_db)) -> FinalAnalysisReport:
    report_logger = get_logger("analysis", {"request_id": str(request_id)})
    report_logger.debug(f"Attempting to retrieve report with ID: {request_id}")

    # Add debug info about the database state
    total_reports = db.query(SavedReport).count()
    report_logger.debug(f"Total reports in database: {total_reports}")
    
    # Try to find the report with more detailed logging
    db_report = repositories.get_report(db, request_id)
    
    if db_report:
        report_logger.debug(f"Found report: ID={db_report.id}, filename={db_report.original_filename}")
    else:
        # Try alternative query to see if it's a UUID issue
        report_by_string = db.query(SavedReport).filter(SavedReport.id == str(request_id)).first()
        if report_by_string:
            report_logger.debug(f"Found report using string ID: {report_by_string.id}")
            db_report = report_by_string
        else:
            report_logger.warning(f"Report definitely not found: {request_id}")

    if not db_report:
        report_logger.warning(f"Report not found: {request_id}")
        error = TimesheetAnalysisError(
            message=f"Report with ID '{request_id}' not found.",
            code="REPORT_NOT_FOUND",
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            http_status=404
        )
        raise ErrorHandler.create_http_exception(error, str(request_id))

    try:
        if db_report.report_data and db_report.report_data.strip() and db_report.report_data != "{}":
            report_content_data = json.loads(db_report.report_data)
            
            # Ensure required fields for FinalAnalysisReport are present or defaulted
            if 'request_id' not in report_content_data:
                report_content_data['request_id'] = str(db_report.id)
            if 'original_filename' not in report_content_data:
                report_content_data['original_filename'] = db_report.original_filename or "Unknown"
            if 'status' not in report_content_data:
                 report_content_data['status'] = "success"  # Default status

            # Validate and construct FinalAnalysisReport
            final_report_model = FinalAnalysisReport(**report_content_data)

        else:
            # Handle cases where report_data is empty or "{}", typically for "processing" or "pending" states
            report_logger.info(f"Report {request_id} has no detailed data, likely processing.")
            final_report_model = FinalAnalysisReport(
                request_id=str(db_report.id),
                original_filename=db_report.original_filename or "Unknown",
                status="processing",
                status_message="Report is currently being processed or has no detailed data.",
                # Initialize other fields as empty or default as per FinalAnalysisReport schema
                kpis=None,
                staffing_density_heatmap=[],
                all_identified_violations=[],
                employee_summaries=[],
                duplicate_name_warnings=[],
                parsing_issues_summary=[],
                overall_report_summary_text=None
            )
        
        report_logger.info(f"Report {request_id} retrieved successfully with status: {final_report_model.status}")
        return final_report_model

    except json.JSONDecodeError as e:
        report_logger.error(f"Failed to parse report_data JSON for report {request_id}: {str(e)}")
        # Fallback to a generic error structure if JSON is corrupted
        final_report_model = FinalAnalysisReport(
            request_id=str(db_report.id),
            original_filename=db_report.original_filename or "Unknown",
            status="error_unknown",
            status_message="Failed to load report details due to corrupted data.",
            kpis=None, staffing_density_heatmap=[], all_identified_violations=[],
            employee_summaries=[], duplicate_name_warnings=[], parsing_issues_summary=[]
        )
        return final_report_model

    except ValidationError as e:
        report_logger.error(f"Pydantic validation error for report {request_id} data: {str(e)}")
        # This indicates that the stored report_data (even if valid JSON) does not match FinalAnalysisReport schema
        error = TimesheetAnalysisError(
            message=f"Report data for ID '{request_id}' is malformed or outdated.",
            code="REPORT_DATA_INVALID",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.HIGH,
            http_status=500,
            debug_info={"validation_errors": e.errors()}
        )
        raise ErrorHandler.create_http_exception(error, str(request_id))
    except Exception as e:
        report_logger.error(f"Unexpected error retrieving report {request_id}: {str(e)}")
        raise ErrorHandler.handle_unexpected_error(e, f"get_report {request_id}", str(request_id))

@router.delete("/reports/{request_id}", 
            status_code=status.HTTP_204_NO_CONTENT, 
            summary="Delete Analysis Report by ID",
            description="Permanently delete an analysis report and all associated data (including uploaded file if stored) for a given request ID.",
            responses={
                204: {"description": "Report deleted successfully"},
                404: {"description": "Report not found"},
                500: {"description": "Internal server error"}
            }
)
async def delete_report(request_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Attempting to delete report with ID: {request_id}")
    report_deleted = repositories.delete_report_and_associated_data(db, request_id)
    if not report_deleted:
        logger.warning(f"Report not found for deletion: {request_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report with ID '{request_id}' not found.")
    logger.info(f"Report {request_id} and associated data deleted successfully.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/analyze-advanced")
async def analyze_timesheet_advanced(
    file: UploadFile = File(...), 
    processing_options: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Advanced timesheet analysis with full two-pass processing control.
    
    This endpoint supports all two-pass processing parameters for fine-grained control
    over the analysis process. Processing options should be provided as JSON string.
    
    Example processing_options:
    {
        "force_two_pass": true,
        "batch_size": 25,
        "timeout_per_employee": 180.0,
        "enable_deduplication": true
    }
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request_logger = get_logger("analysis", {"request_id": request_id})
    
    # Parse processing options
    options = ProcessingOptions()
    if processing_options:
        try:
            options_dict = json.loads(processing_options)
            options = ProcessingOptions(**options_dict)
        except (json.JSONDecodeError, ValidationError) as e:
            request_logger.error(f"Invalid processing options: {str(e)}")
            validation_error = ParsingError(
                message="Invalid processing options format",
                filename=file.filename or "unknown",
                parsing_issues=[f"JSON parsing error: {str(e)}"]
            )
            raise ErrorHandler.create_http_exception(validation_error, request_id)
    
    # Track overall processing time
    analysis_start_time = time.time()
    
    # Get file information
    content_type = file.content_type
    filename = file.filename or "unknown_file"
    file_extension = filename.split(".")[-1].lower() if "." in filename else None
    
    # Read file bytes first to get size
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
    except Exception as e:
        request_logger.error(f"Failed to read uploaded file: {str(e)}")
        file_error = FileValidationError(
            message="Failed to read uploaded file",
            filename=filename
        )
        raise ErrorHandler.create_http_exception(file_error, request_id)
    
    # Validate file using new error handling system
    try:
        validate_file_upload(file_bytes, filename, content_type)
    except (FileValidationError, FileSizeError) as e:
        request_logger.warning(f"File validation failed: {e.message}")
        raise ErrorHandler.create_http_exception(e, request_id)
    
    # Log analysis start with processing options
    request_logger.info(f"Starting advanced analysis with options: {options.model_dump()}")
    log_analysis_start(
        request_logger, request_id, filename, file_size, 
        content_type or "unknown", file_extension
    )

    try:
        # Determine debug directory (optional)
        debug_dir = os.getenv("DEBUG_DIR")
        if debug_dir:
            debug_dir = os.path.join(debug_dir, f"analysis_advanced_{request_id}")
        
        # Step 1: Parse file using advanced processing options
        parsing_start_time = time.time()
        try:
            # Convert ProcessingOptions to kwargs for the processing function
            processing_kwargs = {
                k: v for k, v in options.model_dump().items() 
                if v is not None
            }
            
            # Use the integrated processing function with custom options
            processing_result = await parse_file_with_optimal_strategy(
                file_bytes=file_bytes,
                mime_type=content_type or f"application/{file_extension}",
                original_filename=filename,
                debug_dir=debug_dir,
                **processing_kwargs
            )
            
            # Handle both single-pass and two-pass results
            if isinstance(processing_result, dict):
                # Two-pass result - convert to single-pass format for backward compatibility
                llm_output = convert_two_pass_to_single_pass_format(processing_result)
                
                # Add detailed two-pass processing status to response metadata
                processing_metadata = processing_result.get('processing_metadata', {})
                request_logger.info(f"Advanced two-pass processing completed: {processing_metadata.get('processing_mode', 'unknown')}")
                
                # Log comprehensive two-pass metrics
                if 'performance_metrics' in processing_metadata:
                    metrics = processing_metadata['performance_metrics']
                    request_logger.info(
                        f"Advanced metrics: Total={metrics.get('total_workflow_duration_seconds', 0):.2f}s, "
                        f"Discovery={metrics.get('discovery_duration_seconds', 0):.2f}s, "
                        f"Parallel={metrics.get('parallel_processing_duration_seconds', 0):.2f}s, "
                        f"Stitching={metrics.get('stitching_duration_seconds', 0):.2f}s"
                    )
                
                # Add workflow stage info to parsing issues for visibility
                workflow_stages = processing_metadata.get('workflow_stages', {})
                if workflow_stages:
                    stage_info = f"Workflow stages completed: {', '.join(workflow_stages.keys())}"
                    if hasattr(llm_output, 'parsing_issues'):
                        llm_output.parsing_issues.append(stage_info)
            else:
                # Single-pass result (LLMProcessingOutput)
                llm_output = processing_result
                request_logger.info("Advanced single-pass processing completed")
            
            parsing_end_time = time.time()
            parsing_duration = parsing_end_time - parsing_start_time
            
            events_found = len(llm_output.punch_events) if llm_output.punch_events else 0
            parsing_success = events_found > 0
            
            # Log parsing result
            log_parsing_result(
                request_logger, request_id, filename, parsing_success,
                events_found, parsing_duration, llm_output.parsing_issues
            )
            
            if not llm_output.punch_events:
                request_logger.error("No punch events found in file with advanced processing")
                
                # Log parsing failure to Supabase
                total_duration = time.time() - analysis_start_time
                supabase_result = await log_analysis_to_supabase(
                    request_id=request_id,
                    original_filename=filename,
                    status="error_parsing_failed",
                    file_size=file_size,
                    file_type=content_type or file_extension,
                    processing_time_seconds=total_duration,
                    error_message="No punch events found in file (advanced processing)"
                )
                
                parsing_error = ParsingError(
                    message="No punch events could be extracted from the file using advanced processing",
                    filename=filename,
                    parsing_issues=llm_output.parsing_issues,
                    suggestion="Try adjusting processing options or verify the file contains valid timesheet data"
                )
                raise ErrorHandler.create_http_exception(parsing_error, request_id)
        
        except (FileValidationError, ParsingError, LLMServiceError) as e:
            # Log and re-raise standardized errors
            parsing_duration = time.time() - parsing_start_time
            log_parsing_result(
                request_logger, request_id, filename, False, 0, parsing_duration
            )
            
            total_duration = time.time() - analysis_start_time
            supabase_result = await log_analysis_to_supabase(
                request_id=request_id,
                original_filename=filename,
                status="error_parsing_failed",
                file_size=file_size,
                file_type=content_type or file_extension,
                processing_time_seconds=total_duration,
                error_message=f"Advanced processing error: {e.message}"
            )
            
            raise ErrorHandler.create_http_exception(e, request_id)
            
        except Exception as e:
            parsing_duration = time.time() - parsing_start_time
            log_parsing_result(
                request_logger, request_id, filename, False, 0, parsing_duration
            )
            request_logger.error(f"Advanced LLM parsing failed: {str(e)}")
            
            total_duration = time.time() - analysis_start_time
            supabase_result = await log_analysis_to_supabase(
                request_id=request_id,
                original_filename=filename,
                status="error_parsing_failed",
                file_size=file_size,
                file_type=content_type or file_extension,
                processing_time_seconds=total_duration,
                error_message=f"Advanced LLM parsing failed: {str(e)}"
            )
            
            mapped_error = map_core_exceptions(e, filename)
            raise ErrorHandler.create_http_exception(mapped_error, request_id)
        
        # Continue with the same analysis steps as the regular endpoint
        # (duplicate detection, compliance analysis, etc.)
        # ... [rest of analysis logic same as regular endpoint]
        
        request_logger.info("Advanced analysis endpoint requires full implementation")
        return {
            "message": "Advanced analysis endpoint with two-pass processing integration implemented",
            "request_id": request_id,
            "processing_mode": "advanced",
            "parsing_completed": True,
            "events_found": len(llm_output.punch_events),
            "note": "Full compliance analysis implementation needed"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        total_duration = time.time() - analysis_start_time
        request_logger.error(f"Unexpected error in advanced analysis: {str(e)}")
        
        mapped_error = map_core_exceptions(e, filename)
        raise ErrorHandler.create_http_exception(mapped_error, request_id)

# Placeholder for later integration into main app
# from fastapi import FastAPI
# app = FastAPI()
# app.include_router(router, prefix="/api") 