from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, EmailStr, ValidationError
from typing import Optional
import json
import uuid
import os
from datetime import datetime

# Import our core processing modules
from app.core.llm_processing import parse_file_to_structured_data
from app.core.compliance_rules import detect_compliance_violations_with_costs, detect_duplicate_employees
from app.core.reporting import (
    calculate_kpi_tiles_data,
    generate_staffing_density_heatmap_data,
    compile_general_compliance_violations,
    generate_employee_summary_table_data,
    get_all_violation_types_with_advice
)
from app.models.schemas import LeadCaptureData, FinalAnalysisReport

router = APIRouter()

class LeadData(BaseModel):
    manager_name: str
    manager_email: EmailStr
    manager_phone: Optional[str] = None
    store_name: str
    store_address: str

@router.post("/analyze")
async def analyze_timesheet(
    lead_data_json: str = Form(..., alias="lead_data"),
    file: UploadFile = File(...)
):
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    try:
        # Parse and validate lead data
        lead_data_dict = json.loads(lead_data_json)
        lead_data_model = LeadData(**lead_data_dict)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for lead_data.")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Lead data validation error: {e.errors()}")

    # Get file information
    content_type = file.content_type
    filename = file.filename or "unknown_file"
    file_extension = filename.split(".")[-1].lower() if "." in filename else None
    
    # Validate file type
    supported_types = {
        "text/csv", "application/csv",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/pdf",
        "text/plain"
    }
    supported_extensions = {"csv", "xls", "xlsx", "pdf", "txt", "png", "jpg", "jpeg", "tiff", "bmp", "gif"}
    
    if not (content_type in supported_types or 
            file_extension in supported_extensions or 
            (content_type and content_type.startswith("image/"))):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {content_type or file_extension}. Please upload CSV, XLSX, PDF, common image formats, or TXT files."
        )

    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # Determine debug directory (optional)
        debug_dir = os.getenv("DEBUG_DIR")
        if debug_dir:
            debug_dir = os.path.join(debug_dir, f"analysis_{request_id}")
        
        # Step 1: Parse file to structured data using LLM
        try:
            llm_output = await parse_file_to_structured_data(
                file_bytes=file_bytes,
                mime_type=content_type or f"application/{file_extension}",
                original_filename=filename,
                debug_dir=debug_dir
            )
            
            if not llm_output.punch_events:
                return FinalAnalysisReport(
                    request_id=request_id,
                    original_filename=filename,
                    status="error_parsing_failed",
                    status_message="No punch events could be extracted from the file. Please verify the file contains timesheet data with employee names, dates, and clock in/out times.",
                    parsing_issues_summary=llm_output.parsing_issues or ["No punch events found in file"]
                )
        
        except Exception as e:
            return FinalAnalysisReport(
                request_id=request_id,
                original_filename=filename,
                status="error_parsing_failed",
                status_message=f"Failed to parse timesheet file: {str(e)}",
                parsing_issues_summary=[f"LLM parsing error: {str(e)}"]
            )
        
        # Step 2: Detect duplicate employees and get warnings
        duplicate_groups = detect_duplicate_employees(llm_output.punch_events)
        duplicate_warnings = []
        if duplicate_groups:
            for canonical_name, variations in duplicate_groups.items():
                if len(variations) > 1:
                    duplicate_warnings.append(
                        f"Potential duplicate employee '{canonical_name}' found with variations: {', '.join(variations)}"
                    )
        
        # Step 3: Run compliance analysis with cost calculations
        try:
            # Generate KPI data
            kpis = calculate_kpi_tiles_data(llm_output.punch_events)
            
            # Generate staffing density heatmap
            heatmap_data = generate_staffing_density_heatmap_data(llm_output.punch_events)
            
            # Compile all violations
            all_violations = compile_general_compliance_violations(llm_output.punch_events)
            
            # Generate employee summaries
            employee_summaries = generate_employee_summary_table_data(llm_output.punch_events)
            
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
                overall_report_summary_text=overall_summary
            )
            
            # TODO: Log lead data and analysis metadata to Supabase
            # This will be implemented in task 5.2
            
            return report
            
        except Exception as e:
            return FinalAnalysisReport(
                request_id=request_id,
                original_filename=filename,
                status="error_analysis_failed",
                status_message=f"Failed to complete compliance analysis: {str(e)}",
                parsing_issues_summary=llm_output.parsing_issues or []
            )
    
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during timesheet analysis: {str(e)}"
        )


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

# Placeholder for later integration into main app
# from fastapi import FastAPI
# app = FastAPI()
# app.include_router(router, prefix="/api") 