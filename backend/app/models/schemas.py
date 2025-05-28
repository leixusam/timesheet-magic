from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any # Retaining Dict, Any for potential LLM metadata flexibility
from datetime import date, time, datetime

# --- API Input Schemas ---

class LeadCaptureData(BaseModel):
    """ Data captured from the lead form, potentially sent with the file or as part of the request """
    manager_name: str = Field(..., description="Name of the manager submitting the timesheet.")
    email: EmailStr = Field(..., description="Email address of the manager.")
    phone: Optional[str] = Field(None, description="Contact phone number (optional).")
    store_name: str = Field(..., description="Name of the restaurant/store.")
    store_address: str = Field(..., description="Physical address of the store.")

# --- LLM Interaction Schemas (Output from LLM Parsing Stage) ---

class LLMParsedPunchEvent(BaseModel):
    """ 
    Structure expected from LLM for a single time punch event.
    The LLM should capture what's present in the timesheet.
    Subsequent backend logic will interpret and normalize further.
    """
    employee_identifier_in_file: str = Field(..., description="Employee name/ID as it appeared in the raw file segment related to this punch.")
    timestamp: datetime = Field(..., description="The exact date and time of the punch event.")
    punch_type_as_parsed: str = Field(..., description="The type of punch as interpreted/transcribed by the LLM from the source (e.g., 'In', 'Out', 'Lunch Start', 'Break End', 'Lieu Day'). Backend will map to canonical types.")
    role_as_parsed: Optional[str] = Field(None, description="Employee's role for this shift/punch, if parseable from the timesheet (e.g., 'Server', 'Cook').")
    department_as_parsed: Optional[str] = Field(None, description="Department or work area for this shift/punch, if parseable (e.g., 'Kitchen', 'Front of House').")
    location_note_as_parsed: Optional[str] = Field(None, description="Any specific location notes associated with this punch if present (e.g., 'Station 3', 'Patio').")
    notes_as_parsed: Optional[str] = Field(None, description="Any free-text notes associated with this specific punch or shift segment in the original timesheet.")
    # raw_text_segment: Optional[str] = Field(None, description="Optional: the raw text chunk this punch was parsed from for developer audit/debugging.") # Consider if needed for V1 payload size

class LLMProcessingOutput(BaseModel):
    """ The complete output from the LLM processing stage for a given timesheet file """
    punch_events: List[LLMParsedPunchEvent]
    parsing_issues: Optional[List[str]] = Field(default_factory=list, description="List of any warnings or general issues encountered by the LLM during parsing (e.g., ambiguous lines, unparseable entries). Backend may also append to this.")
    # raw_extracted_text_preview: Optional[str] = Field(None, description="Optional: Preview of the full text extracted by OCR/text-extraction, before structured parsing. For debugging.")

# --- Backend Analysis & Frontend Report Schemas ---

class ViolationInstance(BaseModel):
    """ Represents a single instance of a compliance violation for the report """
    rule_id: str = Field(..., description="Unique identifier for the type of rule violated (e.g., 'MEAL_BREAK', 'DAILY_OT').")
    rule_description: str = Field(..., description="Human-readable description of the rule that was violated.")
    employee_identifier: str = Field(..., description="Normalized employee identifier for this upload session.")
    date_of_violation: date
    specific_details: str = Field(..., description="Details specific to this instance (e.g., 'Worked 6.5 hours, no meal break logged between 10:00 and 16:30.').")
    suggested_action_generic: str = Field(..., description="Generic actionable advice for this type of violation.")

class EmployeeReportDetails(BaseModel):
    """ Summary of an individual employee's hours and violations for the report """
    employee_identifier: str # Normalized by backend for this upload session
    roles_observed: Optional[List[str]] = Field(default_factory=list, description="List of distinct roles observed for this employee in the timesheet (e.g., ['Server', 'Host']).")
    departments_observed: Optional[List[str]] = Field(default_factory=list, description="List of distinct departments/areas observed for this employee.")
    total_hours_worked: float
    regular_hours: float
    overtime_hours: float
    double_overtime_hours: float
    violations_for_employee: List[ViolationInstance] = Field(default_factory=list)

class ReportKPIs(BaseModel):
    """ Key Performance Indicators for the report """
    total_scheduled_labor_hours: float # Renaming to total_calculated_labor_hours for clarity as it's from timesheet
    total_regular_hours: float
    total_overtime_hours: float
    total_double_overtime_hours: float
    estimated_overtime_cost: Optional[float] = None
    estimated_double_overtime_cost: Optional[float] = None
    compliance_risk_assessment: Optional[str] = Field(None, description="Qualitative assessment or count of compliance risks (e.g., 'High: 5 critical violations including 3 meal breaks').")
    count_meal_break_violations: int
    count_rest_break_violations: int # With caveat on data availability for V1
    count_daily_overtime_violations: int
    count_weekly_overtime_violations: int
    count_daily_double_overtime_violations: int
    wage_data_source_note: str = Field(..., description="Note on how wage data was sourced for cost estimations (e.g., 'Default V1 assumption of $X/hr used for overtime cost estimates.').")

class HeatMapDatapoint(BaseModel):
    """ Data for a single hour block in the heat-map """
    hour_timestamp: datetime # Represents the start of the hour block, e.g., 2023-10-26T09:00:00
    employee_count: int

class FinalAnalysisReport(BaseModel):
    """ The final report structure sent from backend to frontend """
    request_id: str = Field(..., description="Unique ID for this analysis request, generated by the backend.")
    original_filename: str
    
    status: str = Field(default="success", description="Overall processing status: 'success', 'partial_success_with_warnings', 'error_parsing_failed', 'error_analysis_failed'")
    status_message: Optional[str] = Field(None, description="User-friendly message, especially if status is not 'success'. Required if status indicates an error.")

    kpis: Optional[ReportKPIs] = None
    staffing_density_heatmap: Optional[List[HeatMapDatapoint]] = Field(default_factory=list)
    all_identified_violations: Optional[List[ViolationInstance]] = Field(default_factory=list)
    employee_summaries: Optional[List[EmployeeReportDetails]] = Field(default_factory=list)
        
    duplicate_name_warnings: Optional[List[str]] = Field(default_factory=list, description="Warnings if potential duplicate employee names were detected and grouped by backend.")
    parsing_issues_summary: Optional[List[str]] = Field(default_factory=list, description="Summary of parsing issues encountered, from LLM or backend processing.")
    # other_processing_warnings: Optional[List[str]] = Field(default_factory=list, description="Other general warnings from the backend processing.") # Merged into parsing_issues_summary for simplicity
            
    overall_report_summary_text: Optional[str] = Field(None, description="Plain-language summary of key findings generated by the backend.") 