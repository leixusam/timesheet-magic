from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import uuid

from app.db import get_db, SavedReport, Lead
from app.models.schemas import FinalAnalysisReport
from pydantic import BaseModel

router = APIRouter()

class SavedReportSummary(BaseModel):
    id: str
    original_filename: str
    manager_name: Optional[str] = None
    store_name: Optional[str] = None
    created_at: datetime
    employee_count: Optional[int] = None
    total_violations: Optional[int] = None
    total_hours: Optional[float] = None
    overtime_cost: Optional[float] = None

class SaveReportRequest(BaseModel):
    report_data: FinalAnalysisReport
    manager_name: Optional[str] = None
    manager_email: Optional[str] = None
    manager_phone: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None

@router.post("/save")
async def save_report(
    request: SaveReportRequest,
    db: Session = Depends(get_db)
):
    """
    Save a completed analysis report to the database
    """
    try:
        # Extract quick access fields from report data
        kpis = request.report_data.kpis
        employee_count = len(request.report_data.employee_summaries) if request.report_data.employee_summaries else 0
        total_violations = len(request.report_data.all_identified_violations) if request.report_data.all_identified_violations else 0
        total_hours = kpis.total_scheduled_labor_hours if kpis else 0
        overtime_cost = kpis.estimated_overtime_cost if kpis else 0
        
        # Create new saved report
        saved_report = SavedReport(
            id=request.report_data.request_id,
            original_filename=request.report_data.original_filename,
            manager_name=request.manager_name,
            manager_email=request.manager_email,
            manager_phone=request.manager_phone,
            store_name=request.store_name,
            store_address=request.store_address,
            report_data=request.report_data.model_dump_json(),
            file_size=request.file_size,
            file_type=request.file_type,
            employee_count=employee_count,
            total_violations=total_violations,
            total_hours=total_hours,
            overtime_cost=overtime_cost
        )
        
        db.add(saved_report)
        db.commit()
        db.refresh(saved_report)
        
        return {
            "success": True,
            "message": "Report saved successfully",
            "report_id": saved_report.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save report: {str(e)}"
        )

@router.get("/list", response_model=List[SavedReportSummary])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get a list of all saved reports with summary information
    """
    try:
        reports = db.query(SavedReport).order_by(SavedReport.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            SavedReportSummary(
                id=report.id,
                original_filename=report.original_filename,
                manager_name=report.manager_name,
                store_name=report.store_name,
                created_at=report.created_at,
                employee_count=report.employee_count,
                total_violations=report.total_violations,
                total_hours=report.total_hours,
                overtime_cost=report.overtime_cost
            )
            for report in reports
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reports: {str(e)}"
        )

@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific report by ID
    """
    try:
        saved_report = db.query(SavedReport).filter(SavedReport.id == report_id).first()
        
        if not saved_report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        # Check if this is a placeholder report (still processing)
        if saved_report.report_data == "{}":
            return {
                "status": "processing",
                "message": "Analysis is still in progress",
                "request_id": report_id,
                "original_filename": saved_report.original_filename,
                "created_at": saved_report.created_at.isoformat()
            }
        
        # Try to parse the JSON report data back to FinalAnalysisReport
        try:
            report_data = json.loads(saved_report.report_data)
            # Create the FinalAnalysisReport object
            final_report = FinalAnalysisReport(**report_data)
            
            # Add manager information from the SavedReport table
            report_dict = final_report.model_dump()
            report_dict["manager_name"] = saved_report.manager_name
            report_dict["manager_email"] = saved_report.manager_email
            report_dict["manager_phone"] = saved_report.manager_phone
            report_dict["store_name"] = saved_report.store_name
            report_dict["store_address"] = saved_report.store_address
            report_dict["created_at"] = saved_report.created_at.isoformat()
            
            return report_dict
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Corrupted report data"
            )
        except Exception as parse_error:
            # If parsing fails, it might be incomplete data - return processing status
            return {
                "status": "processing",
                "message": "Analysis is still in progress",
                "request_id": report_id,
                "original_filename": saved_report.original_filename,
                "created_at": saved_report.created_at.isoformat(),
                "note": "Report data is being generated"
            }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report: {str(e)}"
        )

@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a specific report by ID
    """
    try:
        saved_report = db.query(SavedReport).filter(SavedReport.id == report_id).first()
        
        if not saved_report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        # Also delete any associated leads
        db.query(Lead).filter(Lead.analysis_id == report_id).delete()
        
        # Delete the report
        db.delete(saved_report)
        db.commit()
        
        return {
            "success": True,
            "message": "Report deleted successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete report: {str(e)}"
        ) 