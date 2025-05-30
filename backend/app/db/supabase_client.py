"""
Supabase Client Module for Time Sheet Magic

This module implements task 5.2 - Supabase integration for database operations.
It provides functions to:
- Log captured lead information to Supabase (task 5.2.1)
- Log basic analysis metadata (task 5.2.2)
- Manage database connections and error handling

The module supports both Supabase and local database operations for flexibility.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Union
from supabase import create_client, Client
from pydantic import BaseModel, EmailStr

from app.core.logging_config import get_logger, log_database_operation

# Initialize logger for this module
logger = get_logger("supabase")

class SupabaseConfig:
    """Configuration class for Supabase connection."""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.enabled = bool(self.supabase_url and self.supabase_key)
        
        # Debug logging to see what we're getting
        logger.info(f"Supabase URL: {'SET' if self.supabase_url else 'MISSING'}")
        logger.info(f"Supabase Key: {'SET' if self.supabase_key else 'MISSING'}")
        logger.info(f"Supabase enabled: {self.enabled}")
        
        if not self.enabled:
            logger.warning(
                "Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY "
                "environment variables to enable Supabase integration."
            )

class LeadData(BaseModel):
    """Data model for lead information."""
    manager_name: str
    email: EmailStr
    phone: Optional[str] = None
    store_name: str
    store_address: str
    analysis_id: Optional[str] = None

class AnalysisMetadata(BaseModel):
    """Data model for analysis metadata."""
    request_id: str
    original_filename: str
    status: str  # "success", "partial_success_with_warnings", "error_parsing_failed", etc.
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    employee_count: Optional[int] = None
    total_violations: Optional[int] = None
    total_hours: Optional[float] = None
    overtime_cost: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None

class SupabaseClient:
    """
    Client class for interacting with Supabase database.
    
    This class provides methods for logging leads and analysis metadata
    as required by tasks 5.2.1 and 5.2.2.
    """
    
    def __init__(self):
        self.config = SupabaseConfig()
        self.client: Optional[Client] = None
        
        if self.config.enabled:
            try:
                self.client = create_client(
                    self.config.supabase_url,
                    self.config.supabase_key
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None
        else:
            logger.info("Supabase client not initialized - missing configuration")
    
    def is_available(self) -> bool:
        """Check if Supabase client is available and configured."""
        return self.client is not None
    
    async def log_lead_information(
        self,
        lead_data: LeadData,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log captured lead information to Supabase.
        
        Implements task 5.2.1 - Function to log captured lead information
        (Manager Name, Email, Phone, Store Name, Address) to Supabase table.
        
        Args:
            lead_data: Lead information to store
            request_id: Optional request ID for correlation with analysis
            
        Returns:
            Dictionary with success status and lead ID or error information
        """
        operation_logger = get_logger("supabase", {"request_id": request_id})
        
        if not self.is_available():
            error_msg = "Supabase client not available"
            operation_logger.warning(error_msg)
            log_database_operation(operation_logger, "INSERT", "leads", False, None, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "fallback": "Lead data not stored in Supabase (client unavailable)"
            }
        
        try:
            # Generate unique lead ID
            lead_id = str(uuid.uuid4())
            
            # Prepare data for insertion
            lead_record = {
                "id": lead_id,
                "analysis_id": lead_data.analysis_id or request_id,
                "manager_name": lead_data.manager_name,
                "email": lead_data.email,
                "phone": lead_data.phone,
                "store_name": lead_data.store_name,
                "store_address": lead_data.store_address,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into Supabase
            result = self.client.table("leads").insert(lead_record).execute()
            
            if result.data:
                operation_logger.info(
                    f"Lead successfully logged to Supabase | "
                    f"Manager: {lead_data.manager_name} | "
                    f"Email: {lead_data.email} | "
                    f"Store: {lead_data.store_name} | "
                    f"Lead ID: {lead_id}"
                )
                
                log_database_operation(
                    operation_logger, "INSERT", "leads", True, lead_id
                )
                
                return {
                    "success": True,
                    "lead_id": lead_id,
                    "message": "Lead information logged successfully to Supabase"
                }
            else:
                error_msg = "No data returned from Supabase insert operation"
                operation_logger.error(error_msg)
                log_database_operation(
                    operation_logger, "INSERT", "leads", False, None, error_msg
                )
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"Failed to log lead to Supabase: {str(e)}"
            operation_logger.error(error_msg)
            log_database_operation(
                operation_logger, "INSERT", "leads", False, None, error_msg
            )
            return {
                "success": False,
                "error": error_msg
            }
    
    async def log_analysis_metadata(
        self,
        metadata: AnalysisMetadata
    ) -> Dict[str, Any]:
        """
        Log basic analysis metadata to Supabase.
        
        Implements task 5.2.2 - Function to log basic analysis metadata
        (request ID, success/failure, timestamp) to Supabase table.
        
        Args:
            metadata: Analysis metadata to store
            
        Returns:
            Dictionary with success status and metadata ID or error information
        """
        operation_logger = get_logger("supabase", {"request_id": metadata.request_id})
        
        if not self.is_available():
            error_msg = "Supabase client not available"
            operation_logger.warning(error_msg)
            log_database_operation(
                operation_logger, "INSERT", "analysis_metadata", False, None, error_msg
            )
            return {
                "success": False,
                "error": error_msg,
                "fallback": "Analysis metadata not stored in Supabase (client unavailable)"
            }
        
        try:
            # Prepare metadata record
            metadata_record = {
                "request_id": metadata.request_id,
                "original_filename": metadata.original_filename,
                "status": metadata.status,
                "file_size": metadata.file_size,
                "file_type": metadata.file_type,
                "employee_count": metadata.employee_count,
                "total_violations": metadata.total_violations,
                "total_hours": metadata.total_hours,
                "overtime_cost": metadata.overtime_cost,
                "processing_time_seconds": metadata.processing_time_seconds,
                "error_message": metadata.error_message,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into Supabase
            result = self.client.table("analysis_metadata").insert(metadata_record).execute()
            
            if result.data:
                operation_logger.info(
                    f"Analysis metadata logged to Supabase | "
                    f"Request ID: {metadata.request_id} | "
                    f"Status: {metadata.status} | "
                    f"File: {metadata.original_filename}"
                )
                
                log_database_operation(
                    operation_logger, "INSERT", "analysis_metadata", True, metadata.request_id
                )
                
                return {
                    "success": True,
                    "request_id": metadata.request_id,
                    "message": "Analysis metadata logged successfully to Supabase"
                }
            else:
                error_msg = "No data returned from Supabase insert operation"
                operation_logger.error(error_msg)
                log_database_operation(
                    operation_logger, "INSERT", "analysis_metadata", False, None, error_msg
                )
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"Failed to log analysis metadata to Supabase: {str(e)}"
            operation_logger.error(error_msg)
            log_database_operation(
                operation_logger, "INSERT", "analysis_metadata", False, None, error_msg
            )
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_analysis_history(
        self,
        limit: int = 50,
        store_name_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve analysis history from Supabase.
        
        Args:
            limit: Maximum number of records to return
            store_name_filter: Optional filter by store name
            
        Returns:
            Dictionary with success status and analysis history data
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Supabase client not available",
                "data": []
            }
        
        try:
            # Build query
            query = self.client.table("analysis_metadata").select("*")
            
            if store_name_filter:
                # Join with leads table to filter by store name
                query = (self.client.table("analysis_metadata")
                        .select("*, leads(store_name)")
                        .eq("leads.store_name", store_name_filter))
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            
            logger.info(f"Retrieved {len(result.data) if result.data else 0} analysis records from Supabase")
            
            return {
                "success": True,
                "data": result.data or [],
                "count": len(result.data) if result.data else 0
            }
            
        except Exception as e:
            error_msg = f"Failed to retrieve analysis history from Supabase: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "data": []
            }
    
    async def get_lead_statistics(self) -> Dict[str, Any]:
        """
        Get lead statistics from Supabase.
        
        Returns:
            Dictionary with lead statistics or error information
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Supabase client not available"
            }
        
        try:
            # Get total leads count
            total_result = self.client.table("leads").select("id", count="exact").execute()
            total_leads = total_result.count if hasattr(total_result, 'count') else 0
            
            # Get recent leads (last 30 days)
            recent_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            recent_result = (self.client.table("leads")
                           .select("id", count="exact")
                           .gte("created_at", recent_date)
                           .execute())
            recent_leads = recent_result.count if hasattr(recent_result, 'count') else 0
            
            # Get unique stores count
            stores_result = (self.client.table("leads")
                           .select("store_name")
                           .execute())
            unique_stores = len(set([lead["store_name"] for lead in stores_result.data])) if stores_result.data else 0
            
            logger.info(f"Lead statistics retrieved: {total_leads} total, {recent_leads} recent, {unique_stores} stores")
            
            return {
                "success": True,
                "statistics": {
                    "total_leads": total_leads,
                    "recent_leads_30_days": recent_leads,
                    "unique_stores": unique_stores
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to retrieve lead statistics from Supabase: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

# Global Supabase client instance
_supabase_client: Optional[SupabaseClient] = None

def get_supabase_client() -> SupabaseClient:
    """
    Get the global Supabase client instance.
    
    Returns:
        SupabaseClient instance
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client

# Convenience functions for easy integration

async def log_lead_to_supabase(
    manager_name: str,
    email: str,
    store_name: str,
    store_address: str,
    phone: Optional[str] = None,
    analysis_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to log lead information to Supabase.
    
    This function implements the requirements for task 5.2.1.
    
    Args:
        manager_name: Manager's full name
        email: Manager's email address
        store_name: Store name
        store_address: Store physical address
        phone: Optional phone number
        analysis_id: Optional analysis ID for correlation
        request_id: Optional request ID for logging correlation
        
    Returns:
        Dictionary with success status and lead ID or error information
    """
    client = get_supabase_client()
    
    lead_data = LeadData(
        manager_name=manager_name,
        email=email,
        phone=phone,
        store_name=store_name,
        store_address=store_address,
        analysis_id=analysis_id
    )
    
    return await client.log_lead_information(lead_data, request_id)

async def log_analysis_to_supabase(
    request_id: str,
    original_filename: str,
    status: str,
    file_size: Optional[int] = None,
    file_type: Optional[str] = None,
    employee_count: Optional[int] = None,
    total_violations: Optional[int] = None,
    total_hours: Optional[float] = None,
    overtime_cost: Optional[float] = None,
    processing_time_seconds: Optional[float] = None,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to log analysis metadata to Supabase.
    
    This function implements the requirements for task 5.2.2.
    
    Args:
        request_id: Unique request identifier
        original_filename: Name of the processed file
        status: Analysis status (success, error, etc.)
        file_size: Size of the processed file in bytes
        file_type: MIME type or file extension
        employee_count: Number of employees processed
        total_violations: Total compliance violations found
        total_hours: Total labor hours processed
        overtime_cost: Estimated overtime cost
        processing_time_seconds: Total processing time
        error_message: Error message if analysis failed
        
    Returns:
        Dictionary with success status and metadata ID or error information
    """
    client = get_supabase_client()
    
    metadata = AnalysisMetadata(
        request_id=request_id,
        original_filename=original_filename,
        status=status,
        file_size=file_size,
        file_type=file_type,
        employee_count=employee_count,
        total_violations=total_violations,
        total_hours=total_hours,
        overtime_cost=overtime_cost,
        processing_time_seconds=processing_time_seconds,
        error_message=error_message
    )
    
    return await client.log_analysis_metadata(metadata) 