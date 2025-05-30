"""
Unit tests for the Supabase client module.

This module tests the implementation of tasks 5.2.1 and 5.2.2:
- Lead information logging to Supabase
- Analysis metadata logging to Supabase
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.db.supabase_client import (
    SupabaseClient,
    SupabaseConfig,
    LeadData,
    AnalysisMetadata,
    log_lead_to_supabase,
    log_analysis_to_supabase,
    get_supabase_client
)

class TestSupabaseConfig:
    """Test Supabase configuration handling."""
    
    def test_config_with_environment_variables(self):
        """Test configuration when environment variables are set."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key'
        }):
            config = SupabaseConfig()
            assert config.supabase_url == 'https://test.supabase.co'
            assert config.supabase_key == 'test-service-key'
            assert config.enabled is True
    
    def test_config_without_environment_variables(self):
        """Test configuration when environment variables are missing."""
        with patch.dict('os.environ', {}, clear=True):
            config = SupabaseConfig()
            assert config.supabase_url is None
            assert config.supabase_key is None
            assert config.enabled is False
    
    def test_config_with_anon_key_fallback(self):
        """Test configuration with anonymous key fallback."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-anon-key'
        }):
            config = SupabaseConfig()
            assert config.supabase_url == 'https://test.supabase.co'
            assert config.supabase_key == 'test-anon-key'
            assert config.enabled is True

class TestLeadDataModel:
    """Test LeadData Pydantic model."""
    
    def test_valid_lead_data(self):
        """Test creating valid lead data."""
        lead_data = LeadData(
            manager_name="John Smith",
            email="john@example.com",
            store_name="Test Store",
            store_address="123 Main St",
            phone="555-1234",
            analysis_id="test-123"
        )
        assert lead_data.manager_name == "John Smith"
        assert lead_data.email == "john@example.com"
        assert lead_data.phone == "555-1234"
    
    def test_optional_fields(self):
        """Test lead data with optional fields missing."""
        lead_data = LeadData(
            manager_name="Jane Doe",
            email="jane@example.com",
            store_name="Another Store",
            store_address="456 Oak Ave"
        )
        assert lead_data.phone is None
        assert lead_data.analysis_id is None
    
    def test_invalid_email(self):
        """Test validation with invalid email."""
        with pytest.raises(ValueError):
            LeadData(
                manager_name="John Smith",
                email="invalid-email",
                store_name="Test Store",
                store_address="123 Main St"
            )

class TestAnalysisMetadataModel:
    """Test AnalysisMetadata Pydantic model."""
    
    def test_valid_analysis_metadata(self):
        """Test creating valid analysis metadata."""
        metadata = AnalysisMetadata(
            request_id="test-123",
            original_filename="test.csv",
            status="success",
            file_size=1024,
            employee_count=5,
            total_violations=2
        )
        assert metadata.request_id == "test-123"
        assert metadata.status == "success"
        assert metadata.file_size == 1024
    
    def test_optional_fields_analysis_metadata(self):
        """Test analysis metadata with optional fields."""
        metadata = AnalysisMetadata(
            request_id="test-456",
            original_filename="test2.xlsx",
            status="error_parsing_failed"
        )
        assert metadata.file_size is None
        assert metadata.employee_count is None
        assert metadata.error_message is None

class TestSupabaseClient:
    """Test SupabaseClient functionality."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client for testing."""
        with patch('app.db.supabase_client.create_client') as mock_create:
            mock_client = Mock()
            mock_create.return_value = mock_client
            
            # Mock table operations
            mock_table = Mock()
            mock_client.table.return_value = mock_table
            mock_table.insert.return_value = mock_table
            mock_table.select.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.gte.return_value = mock_table
            
            # Mock execute results
            mock_result = Mock()
            mock_result.data = [{"id": "test-id", "status": "success"}]
            mock_result.count = 1
            mock_table.execute.return_value = mock_result
            
            yield mock_client
    
    def test_client_initialization_with_config(self, mock_supabase_client):
        """Test client initialization when properly configured."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            client = SupabaseClient()
            assert client.is_available() is True
    
    def test_client_initialization_without_config(self):
        """Test client initialization when not configured."""
        with patch.dict('os.environ', {}, clear=True):
            client = SupabaseClient()
            assert client.is_available() is False
    
    @pytest.mark.asyncio
    async def test_log_lead_information_success(self, mock_supabase_client):
        """Test successful lead information logging (Task 5.2.1)."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            client = SupabaseClient()
            
            lead_data = LeadData(
                manager_name="Test Manager",
                email="test@example.com",
                store_name="Test Store",
                store_address="123 Test St"
            )
            
            result = await client.log_lead_information(lead_data, "test-request-123")
            
            assert result["success"] is True
            assert "lead_id" in result
            assert result["message"] == "Lead information logged successfully to Supabase"
    
    @pytest.mark.asyncio
    async def test_log_lead_information_client_unavailable(self):
        """Test lead logging when Supabase client is unavailable."""
        with patch.dict('os.environ', {}, clear=True):
            client = SupabaseClient()
            
            lead_data = LeadData(
                manager_name="Test Manager",
                email="test@example.com",
                store_name="Test Store",
                store_address="123 Test St"
            )
            
            result = await client.log_lead_information(lead_data)
            
            assert result["success"] is False
            assert "Supabase client not available" in result["error"]
            assert "fallback" in result
    
    @pytest.mark.asyncio
    async def test_log_analysis_metadata_success(self, mock_supabase_client):
        """Test successful analysis metadata logging (Task 5.2.2)."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            client = SupabaseClient()
            
            metadata = AnalysisMetadata(
                request_id="test-request-456",
                original_filename="test.csv",
                status="success",
                file_size=2048,
                employee_count=3,
                total_violations=1
            )
            
            result = await client.log_analysis_metadata(metadata)
            
            assert result["success"] is True
            assert result["request_id"] == "test-request-456"
            assert result["message"] == "Analysis metadata logged successfully to Supabase"
    
    @pytest.mark.asyncio
    async def test_log_analysis_metadata_client_unavailable(self):
        """Test analysis metadata logging when Supabase client is unavailable."""
        with patch.dict('os.environ', {}, clear=True):
            client = SupabaseClient()
            
            metadata = AnalysisMetadata(
                request_id="test-request-789",
                original_filename="test.xlsx",
                status="error_parsing_failed",
                error_message="Test error"
            )
            
            result = await client.log_analysis_metadata(metadata)
            
            assert result["success"] is False
            assert "Supabase client not available" in result["error"]
            assert "fallback" in result
    
    @pytest.mark.asyncio
    async def test_get_analysis_history_success(self, mock_supabase_client):
        """Test analysis history retrieval."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            client = SupabaseClient()
            
            result = await client.get_analysis_history(limit=10)
            
            assert result["success"] is True
            assert "data" in result
            assert "count" in result
    
    @pytest.mark.asyncio
    async def test_get_lead_statistics_success(self, mock_supabase_client):
        """Test lead statistics retrieval."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            # Update mock to handle the stores query specifically
            mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = [
                {"store_name": "Store A"},
                {"store_name": "Store B"},
                {"store_name": "Store A"}  # Duplicate to test unique count
            ]
            
            client = SupabaseClient()
            
            result = await client.get_lead_statistics()
            
            assert result["success"] is True
            assert "statistics" in result

class TestConvenienceFunctions:
    """Test convenience functions for easy integration."""
    
    @pytest.mark.asyncio
    async def test_log_lead_to_supabase_function(self):
        """Test log_lead_to_supabase convenience function."""
        with patch('app.db.supabase_client.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_client.log_lead_information = AsyncMock(return_value={
                "success": True,
                "lead_id": "test-lead-123"
            })
            mock_get_client.return_value = mock_client
            
            result = await log_lead_to_supabase(
                manager_name="Test Manager",
                email="test@example.com",
                store_name="Test Store",
                store_address="123 Test St",
                request_id="test-request"
            )
            
            assert result["success"] is True
            assert result["lead_id"] == "test-lead-123"
            mock_client.log_lead_information.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_analysis_to_supabase_function(self):
        """Test log_analysis_to_supabase convenience function."""
        with patch('app.db.supabase_client.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_client.log_analysis_metadata = AsyncMock(return_value={
                "success": True,
                "request_id": "test-analysis-456"
            })
            mock_get_client.return_value = mock_client
            
            result = await log_analysis_to_supabase(
                request_id="test-analysis-456",
                original_filename="test.csv",
                status="success",
                employee_count=5
            )
            
            assert result["success"] is True
            assert result["request_id"] == "test-analysis-456"
            mock_client.log_analysis_metadata.assert_called_once()

class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_lead_logging_with_supabase_exception(self):
        """Test lead logging when Supabase raises an exception."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            with patch('app.db.supabase_client.create_client') as mock_create:
                mock_client = Mock()
                mock_table = Mock()
                mock_client.table.return_value = mock_table
                mock_table.insert.side_effect = Exception("Supabase connection error")
                mock_create.return_value = mock_client
                
                client = SupabaseClient()
                lead_data = LeadData(
                    manager_name="Test Manager",
                    email="test@example.com",
                    store_name="Test Store",
                    store_address="123 Test St"
                )
                
                result = await client.log_lead_information(lead_data)
                
                assert result["success"] is False
                assert "Failed to log lead to Supabase" in result["error"]
    
    @pytest.mark.asyncio
    async def test_analysis_logging_with_supabase_exception(self):
        """Test analysis metadata logging when Supabase raises an exception."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            with patch('app.db.supabase_client.create_client') as mock_create:
                mock_client = Mock()
                mock_table = Mock()
                mock_client.table.return_value = mock_table
                mock_table.insert.side_effect = Exception("Network timeout")
                mock_create.return_value = mock_client
                
                client = SupabaseClient()
                metadata = AnalysisMetadata(
                    request_id="test-error",
                    original_filename="test.csv",
                    status="success"
                )
                
                result = await client.log_analysis_metadata(metadata)
                
                assert result["success"] is False
                assert "Failed to log analysis metadata to Supabase" in result["error"]

def test_get_supabase_client_singleton():
    """Test that get_supabase_client returns the same instance."""
    client1 = get_supabase_client()
    client2 = get_supabase_client()
    assert client1 is client2  # Should be the same instance 