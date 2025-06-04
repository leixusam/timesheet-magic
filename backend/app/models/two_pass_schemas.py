"""
Two-Pass Data Pipeline Schemas

This module contains Pydantic models specifically designed for the two-pass
approach to timesheet processing, which solves Gemini's output token limits
by separating employee discovery from individual parsing.

Pass 1: Employee Discovery - identifies all employees and estimates punch counts
Pass 2: Per-Employee Parsing - processes each employee's punches individually
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ===== PASS 1: EMPLOYEE DISCOVERY SCHEMAS =====

class EmployeeDiscoveryResult(BaseModel):
    """
    Represents a single employee discovered during Pass 1 analysis.
    
    This schema captures the essential information needed to identify
    an employee in the file and estimate the scope of their data.
    """
    employee_identifier_in_file: str = Field(
        ..., 
        description="The EXACT employee name/ID string as it appears in the raw file. Must be an exact substring match for filtering in Pass 2."
    )
    punch_count_estimate: int = Field(
        ..., 
        description="Estimated number of time punch events for this employee (helps with resource planning for Pass 2)."
    )
    canonical_name_suggestion: Optional[str] = Field(
        None,
        description="Optional cleaned/normalized version of the employee name for display purposes (e.g., 'John Doe' from 'JD-903')."
    )


class EmployeeDiscoveryOutput(BaseModel):
    """
    Complete response structure for Pass 1 employee discovery.
    
    Contains all discovered employees plus any issues encountered
    during the discovery process.
    """
    employees: List[EmployeeDiscoveryResult] = Field(
        ...,
        description="List of all unique employees discovered in the timesheet file."
    )
    discovery_issues: List[str] = Field(
        default_factory=list,
        description="Any issues or warnings encountered during employee discovery (e.g., ambiguous entries, formatting problems)."
    )


# ===== FUNCTION CALLING SCHEMA CONVERTERS =====

def employee_discovery_to_gemini_tool_dict(
    tool_name: str = "discover_employees", 
    tool_description: str = "Discover all unique employees in the timesheet file and estimate their punch counts"
) -> Dict[str, Any]:
    """
    Converts the EmployeeDiscoveryOutput schema into a Gemini function calling tool definition.
    
    This function creates the tool schema that Gemini will use to structure its response
    during Pass 1 employee discovery.
    
    Args:
        tool_name: Name of the function tool for Gemini to call
        tool_description: Description of what the tool does
        
    Returns:
        Dictionary formatted as a Gemini FunctionDeclaration for employee discovery
    """
    
    # Define the employee result properties
    employee_properties = {
        "employee_identifier_in_file": {
            "type": "STRING",
            "description": "The EXACT employee name/ID string as it appears in the raw file. Must be an exact substring match for filtering in Pass 2."
        },
        "punch_count_estimate": {
            "type": "INTEGER", 
            "description": "Estimated number of time punch events for this employee (helps with resource planning for Pass 2)."
        },
        "canonical_name_suggestion": {
            "type": "STRING",
            "description": "Optional cleaned/normalized version of the employee name for display purposes (e.g., 'John Doe' from 'JD-903'). Leave empty if no cleaning needed."
        }
    }
    
    # Define the main tool parameters schema
    tool_parameters_schema = {
        "type": "OBJECT",
        "properties": {
            "employees": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": employee_properties,
                    "required": ["employee_identifier_in_file", "punch_count_estimate"]
                },
                "description": "List of all unique employees discovered in the timesheet file."
            },
            "discovery_issues": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Any issues or warnings encountered during employee discovery (e.g., ambiguous entries, formatting problems). Leave empty if no issues."
            }
        },
        "required": ["employees"]
    }
    
    return {
        "name": tool_name,
        "description": tool_description,
        "parameters": tool_parameters_schema
    }


def per_employee_parsing_to_gemini_tool_dict(
    tool_name: str = "parse_employee_punches",
    tool_description: str = "Parse all time punch events for a specific employee"
) -> Dict[str, Any]:
    """
    Converts the per-employee parsing schema into a Gemini function calling tool definition.
    
    This function creates the tool schema that Gemini will use during Pass 2
    for parsing individual employee punch events.
    
    Args:
        tool_name: Name of the function tool for Gemini to call
        tool_description: Description of what the tool does
        
    Returns:
        Dictionary formatted as a Gemini FunctionDeclaration for per-employee parsing
    """
    
    # Import here to avoid circular imports
    try:
        from app.models.schemas import LLMParsedPunchEvent
        
        # Get the punch event schema properties
        punch_event_schema = LLMParsedPunchEvent.model_json_schema()
        punch_event_properties = {}
        
        for prop_name, prop_schema in punch_event_schema.get("properties", {}).items():
            # Convert to Gemini format
            if "anyOf" in prop_schema:
                # Handle optional fields
                punch_event_properties[prop_name] = {
                    "type": "STRING",
                    "description": prop_schema.get("description", "") + " (Optional - leave empty if not available)"
                }
            else:
                json_type = prop_schema.get("type", "string")
                gemini_type = {
                    "string": "STRING",
                    "number": "NUMBER", 
                    "integer": "INTEGER",
                    "boolean": "BOOLEAN",
                    "array": "ARRAY",
                    "object": "OBJECT"
                }.get(json_type.lower(), "STRING")
                
                punch_event_properties[prop_name] = {
                    "type": gemini_type,
                    "description": prop_schema.get("description", "")
                }
                
                # Handle datetime format
                if prop_schema.get("format") == "date-time":
                    punch_event_properties[prop_name]["description"] += " (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)"
        
    except ImportError:
        # Fallback basic schema if import fails
        punch_event_properties = {
            "employee_identifier_in_file": {
                "type": "STRING", 
                "description": "Employee name/ID as it appeared in the raw file segment related to this punch."
            },
            "timestamp": {
                "type": "STRING",
                "description": "The exact date and time of the punch event in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SS). Preserve original timezone - only add 'Z' suffix if the source data explicitly contains UTC/timezone information."
            },
            "punch_type_as_parsed": {
                "type": "STRING",
                "description": "The type of punch as interpreted from the source (e.g., 'In', 'Out', 'Lunch Start')."
            }
        }
    
    tool_parameters_schema = {
        "type": "OBJECT",
        "properties": {
            "punch_events": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": punch_event_properties,
                    "required": ["employee_identifier_in_file", "timestamp", "punch_type_as_parsed"]
                },
                "description": "All time punch events parsed for the specific employee being processed."
            },
            "parsing_issues": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Any parsing issues specific to this employee's data. Leave empty if no issues."
            }
        },
        "required": ["punch_events"]
    }
    
    return {
        "name": tool_name,
        "description": tool_description,
        "parameters": tool_parameters_schema
    }


# ===== VALIDATION FUNCTIONS =====

def validate_employee_identifiers_in_file(
    employees: List[EmployeeDiscoveryResult], 
    file_content: str
) -> tuple[List[EmployeeDiscoveryResult], List[str]]:
    """
    Validates that all discovered employee identifiers are exact substrings in the file content.
    
    This is critical for Pass 2 filtering - if an employee identifier is not an exact
    substring, Pass 2 filtering will fail to find any punch events for that employee.
    
    Args:
        employees: List of discovered employees from Pass 1
        file_content: The complete file content string
        
    Returns:
        Tuple of (validated_employees, validation_issues)
        - validated_employees: List of employees that passed validation
        - validation_issues: List of validation error messages
    """
    validated_employees = []
    validation_issues = []
    
    for employee in employees:
        identifier = employee.employee_identifier_in_file
        
        # Check if identifier is an exact substring
        if identifier in file_content:
            # Additional check: ensure it's not just a partial match within a larger string
            # This helps catch cases like "John" matching "Johnson"
            
            # Find all occurrences and check context
            import re
            # Use word boundary matching for better precision
            pattern = re.escape(identifier)
            matches = list(re.finditer(pattern, file_content, re.IGNORECASE))
            
            if matches:
                validated_employees.append(employee)
            else:
                validation_issues.append(
                    f"Employee identifier '{identifier}' found in file but may be part of a larger string. "
                    f"Consider using a more specific identifier for reliable Pass 2 filtering."
                )
        else:
            validation_issues.append(
                f"Employee identifier '{identifier}' is not found as an exact substring in the file content. "
                f"This will cause Pass 2 filtering to fail. The LLM may have hallucinated or modified this identifier."
            )
    
    return validated_employees, validation_issues


def deduplicate_employee_identifiers(
    employees: List[EmployeeDiscoveryResult]
) -> tuple[List[EmployeeDiscoveryResult], List[str]]:
    """
    Removes duplicate employee identifiers and consolidates their data.
    
    This handles cases where the LLM might return the same employee with
    slight variations in the identifier or multiple entries for the same person.
    
    Args:
        employees: List of potentially duplicate employees
        
    Returns:
        Tuple of (deduplicated_employees, deduplication_notes)
    """
    seen_identifiers = {}
    deduplicated = []
    deduplication_notes = []
    
    for employee in employees:
        identifier = employee.employee_identifier_in_file.strip()
        
        if identifier in seen_identifiers:
            # Found duplicate - merge the data
            existing_employee = seen_identifiers[identifier]
            
            # Take the higher punch count estimate
            if employee.punch_count_estimate > existing_employee.punch_count_estimate:
                existing_employee.punch_count_estimate = employee.punch_count_estimate
                deduplication_notes.append(
                    f"Updated punch count for '{identifier}' from {existing_employee.punch_count_estimate} "
                    f"to {employee.punch_count_estimate} (taking higher estimate)"
                )
            
            # Use canonical name if one is empty
            if not existing_employee.canonical_name_suggestion and employee.canonical_name_suggestion:
                existing_employee.canonical_name_suggestion = employee.canonical_name_suggestion
                deduplication_notes.append(
                    f"Added canonical name '{employee.canonical_name_suggestion}' for '{identifier}'"
                )
            
            deduplication_notes.append(f"Removed duplicate entry for employee '{identifier}'")
        else:
            # New employee
            seen_identifiers[identifier] = employee
            deduplicated.append(employee)
    
    return deduplicated, deduplication_notes


def normalize_employee_discovery_output(
    discovery_output: EmployeeDiscoveryOutput,
    file_content: str
) -> EmployeeDiscoveryOutput:
    """
    Normalizes and validates a complete employee discovery output.
    
    This function applies all validation and normalization steps to ensure
    the discovery results are suitable for Pass 2 processing.
    
    Args:
        discovery_output: Raw discovery output from LLM
        file_content: Complete file content for validation
        
    Returns:
        Normalized and validated discovery output
    """
    all_issues = list(discovery_output.discovery_issues)
    
    # Step 1: Deduplicate employees
    deduplicated_employees, dedup_notes = deduplicate_employee_identifiers(discovery_output.employees)
    all_issues.extend(dedup_notes)
    
    # Step 2: Validate identifiers are in file
    validated_employees, validation_issues = validate_employee_identifiers_in_file(
        deduplicated_employees, 
        file_content
    )
    all_issues.extend(validation_issues)
    
    # Step 3: Filter out employees with zero estimated punches
    final_employees = []
    for employee in validated_employees:
        if employee.punch_count_estimate > 0:
            final_employees.append(employee)
        else:
            all_issues.append(
                f"Filtered out employee '{employee.employee_identifier_in_file}' "
                f"with zero estimated punch events"
            )
    
    return EmployeeDiscoveryOutput(
        employees=final_employees,
        discovery_issues=all_issues
    )


# ===== PASS 2: PER-EMPLOYEE PARSING SCHEMAS =====

class PerEmployeeParsingInput(BaseModel):
    """
    Input structure for Pass 2 per-employee parsing operations.
    
    Contains the employee filter and context needed for targeted parsing.
    """
    employee_filter: str = Field(
        ...,
        description="The exact employee_identifier_in_file from Pass 1 to filter for in Pass 2."
    )
    file_content: str = Field(
        ...,
        description="The complete timesheet file content (same as Pass 1)."
    )
    original_filename: str = Field(
        ...,
        description="Original filename for context and error reporting."
    )


class PerEmployeeParsingOutput(BaseModel):
    """
    Response structure for Pass 2 individual employee parsing.
    
    Contains all punch events for a specific employee plus any
    employee-specific parsing issues.
    """
    employee_identifier: str = Field(
        ...,
        description="The employee identifier this result corresponds to."
    )
    punch_events: List = Field(  # Will be List[LLMParsedPunchEvent] when imported
        ...,
        description="All time punch events parsed for this specific employee."
    )
    parsing_issues: List[str] = Field(
        default_factory=list,
        description="Any parsing issues specific to this employee's data."
    )


# ===== AGGREGATED RESULTS SCHEMA =====

class TwoPassProcessingResult(BaseModel):
    """
    Final aggregated result from the complete two-pass processing workflow.
    
    Contains all parsed data plus metadata about the two-pass process.
    """
    total_employees_discovered: int = Field(
        ...,
        description="Total number of unique employees found in Pass 1."
    )
    employees_successfully_parsed: int = Field(
        ...,
        description="Number of employees successfully parsed in Pass 2."
    )
    employees_failed_parsing: int = Field(
        ...,
        description="Number of employees that failed during Pass 2 parsing."
    )
    all_punch_events: List = Field(  # Will be List[LLMParsedPunchEvent] when imported
        ...,
        description="Combined punch events from all successfully parsed employees."
    )
    discovery_issues: List[str] = Field(
        default_factory=list,
        description="Issues from Pass 1 employee discovery."
    )
    parsing_issues: List[str] = Field(
        default_factory=list,
        description="Aggregated parsing issues from all Pass 2 operations."
    )
    failed_employees: List[str] = Field(
        default_factory=list,
        description="List of employee identifiers that failed during Pass 2."
    )
    processing_metadata: dict = Field(
        default_factory=dict,
        description="Metadata about the two-pass processing (timing, batch sizes, etc.)."
    ) 