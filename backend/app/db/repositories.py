from sqlalchemy.orm import Session, joinedload, undefer
from sqlalchemy import desc, func, or_
from typing import List, Optional, Dict, Any
from uuid import UUID

from . import SavedReport, Lead
from ..models.schemas import (
    LeadCaptureData, 
    FinalAnalysisReport
)

# Report related functions
def get_report(db: Session, report_id: UUID) -> Optional[SavedReport]:
    # Remove undefer to avoid potential session issues with recently created reports
    return db.query(SavedReport).filter(SavedReport.id == report_id).first()

def get_reports_paginated(
    db: Session, skip: int = 0, limit: int = 10, 
    sort_by: Optional[str] = None, sort_order: Optional[str] = 'desc',
    filter_by_status: Optional[str] = None
) -> List[SavedReport]:
    query = db.query(SavedReport)
    # Note: SavedReport doesn't have a status field in current schema
    # if filter_by_status:
    #     query = query.filter(SavedReport.status == filter_by_status)
    if sort_by:
        column = getattr(SavedReport, sort_by, None)
        if column:
            if sort_order == 'asc':
                query = query.order_by(column.asc())
            else:
                query = query.order_by(column.desc())
        else:
            # Default sort if column not found or invalid
            query = query.order_by(SavedReport.created_at.desc())
    else:
        query = query.order_by(SavedReport.created_at.desc())
    return query.offset(skip).limit(limit).all()

def get_total_reports_count(db: Session, filter_by_status: Optional[str] = None) -> int:
    query = db.query(func.count(SavedReport.id))
    # Note: SavedReport doesn't have a status field in current schema
    # if filter_by_status:
    #     query = query.filter(SavedReport.status == filter_by_status)
    return query.scalar()

def create_report(db: Session, report_data: Dict[str, Any]) -> SavedReport:
    db_report = SavedReport(**report_data)
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def update_report_status_and_save_data(
    db: Session, 
    report_id: UUID, 
    status: str, 
    status_message: Optional[str] = None,
    original_filename: Optional[str] = None,
    llm_output: Optional[Dict[str, Any]] = None, 
    analysis_summary: Optional[Dict[str, Any]] = None,
    processing_errors: Optional[List[Dict[str, Any]]] = None,
    total_raw_punch_events: Optional[int] = None,
    total_processed_punch_events: Optional[int] = None,
    total_violation_count: Optional[int] = None,
    total_employee_count: Optional[int] = None
) -> Optional[SavedReport]:
    db_report = db.query(SavedReport).filter(SavedReport.id == report_id).first()
    if db_report:
        # Note: SavedReport doesn't have status/status_message fields in current schema
        # db_report.status = status
        # if status_message is not None:
        #     db_report.status_message = status_message
        if original_filename:
            db_report.original_filename = original_filename
        # Note: SavedReport doesn't have separate llm_output field, using report_data
        if analysis_summary:
            db_report.report_data = analysis_summary.get("report_data", "{}")
        # Map to existing fields in SavedReport
        if total_employee_count is not None:
            db_report.employee_count = total_employee_count
        if total_violation_count is not None:
            db_report.total_violations = total_violation_count
            
        # Note: processing_errors would need a separate table to store properly
        # For now, skipping this functionality
        
        db.commit()
        db.refresh(db_report)
    return db_report

def delete_report_and_associated_data(db: Session, report_id: UUID) -> bool:
    """
    Deletes a SavedReport and all its associated data.
    """
    report = db.query(SavedReport).filter(SavedReport.id == report_id).first()
    if not report:
        return False

    # Delete associated lead if any
    db.query(Lead).filter(Lead.analysis_id == str(report_id)).delete(synchronize_session=False)

    # Delete the report itself
    db.delete(report)
    db.commit()
    return True

# Lead related functions
def get_all_leads(db: Session, skip: int = 0, limit: int = 100) -> List[Lead]:
    return db.query(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()

def get_lead_by_id(db: Session, lead_id: UUID) -> Optional[Lead]:
    return db.query(Lead).filter(Lead.id == lead_id).first()

def create_lead(db: Session, lead_data: Dict[str, Any], request_id: Optional[UUID] = None) -> Lead:
    if request_id:
        lead_data['analysis_id'] = str(request_id)
    db_lead = Lead(**lead_data)
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead

def update_lead(db: Session, lead_id: UUID, lead_update: Dict[str, Any]) -> Optional[Lead]:
    db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if db_lead:
        for key, value in lead_update.items():
            if hasattr(db_lead, key):
                setattr(db_lead, key, value)
        db.commit()
        db.refresh(db_lead)
    return db_lead

def delete_lead(db: Session, lead_id: UUID) -> bool:
    db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if db_lead:
        db.delete(db_lead)
        db.commit()
        return True
    return False

# User-specific reports (Placeholder, assuming user_id is a string for now)
def get_reports_for_user(db: Session, user_id: str, skip: int = 0, limit: int = 10) -> List[SavedReport]:
    # This is a placeholder. Actual implementation would depend on how users are associated with reports.
    # For now, just return all reports since we don't have user association
    return get_reports_paginated(db, skip, limit)

# Simplified functions for compatibility
def save_punch_events(db: Session, report_id: UUID, punch_events_data: List[Dict[str, Any]]):
    # Placeholder - would need PunchEvent model
    pass

def save_compliance_violations(db: Session, report_id: UUID, violations_data: List[Dict[str, Any]]):
    # Placeholder - would need ComplianceViolation model
    pass

def get_processing_errors_for_report(db: Session, report_id: UUID) -> List[Dict[str, Any]]:
    # Placeholder - would need ReportProcessingError model
    return []

def get_report_summary_data(db: Session, report_id: UUID) -> Optional[Dict[str, Any]]:
    report = get_report(db, report_id)
    if not report:
        return None
    
    return {
        "request_id": str(report.id),
        "original_filename": report.original_filename,
        "created_at": report.created_at,
        "employee_count": report.employee_count,
        "total_violations": report.total_violations,
        "total_hours": report.total_hours,
        "overtime_cost": report.overtime_cost
    } 