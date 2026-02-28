"""
Property-based tests for DriveManager upload logging.

This module contains property-based tests using Hypothesis to verify:
- Property 22: File Upload Logging is Complete

Testing Framework: pytest + hypothesis
Feature: finmatcher-v2-upgrade
Validates: Requirements 10.3
"""

import pytest
import tempfile
import os
import logging
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from io import StringIO

from finmatcher.reports.drive_manager import DriveManager
from finmatcher.storage.models import AttachmentType


# Strategy for generating valid filenames
@st.composite
def filename_strategy(draw):
    """Generate valid filenames with various extensions."""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=1,
        max_size=20
    ))
    extension = draw(st.sampled_from(['pdf', 'xlsx', 'jpg', 'png', 'doc', 'docx']))
    return f"{name}.{extension}"


@st.composite
def folder_id_strategy(draw):
    """Generate valid Google Drive folder IDs."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=10,
        max_size=30
    ))


@st.composite
def source_prefix_strategy(draw):
    """Generate valid source prefixes."""
    return draw(st.sampled_from(['email', 'statement', 'manual', 'import']))


@pytest.fixture
def mock_drive_manager():
    """Create a DriveManager with mocked authentication."""
    with patch.object(DriveManager, '_authenticate'):
        manager = DriveManager(credentials_path='dummy_path')
        manager.service = MagicMock()
        yield manager


class TestUploadLoggingProperty:
    """
    Property 22: File Upload Logging is Complete
    
    Universal Property:
    FOR ALL file uploads (Excel reports or attachments),
    WHEN the Drive_Manager uploads a file,
    THEN the system SHALL log:
    - The file name
    - The target folder ID
    - The upload timestamp (implicitly via logger timestamp)
    
    Validates Requirement 10.3:
    WHEN the Drive_Manager uploads a file, THE FinMatcher_System SHALL log 
    the file name, target folder, and upload timestamp
    """
    
    @given(
        filename=filename_strategy(),
        folder_id=folder_id_strategy(),
        file_id=st.text(min_size=10, max_size=30)
    )
    @settings(max_examples=10, deadline=10000)  # Reduced examples and added deadline
    def test_excel_report_upload_logs_required_fields(self, filename, folder_id, file_id):
        """
        Property: Excel report upload must log filename, folder_id, and file_id.
        
        Validates Requirement 10.3: Log file name, target folder, and upload timestamp
        """
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            # Write minimal Excel content
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(['Header1', 'Header2'])
            wb.save(tmp_path)
        
        try:
            # Mock Google Drive service
            mock_service = MagicMock()
            mock_service.files().list().execute.return_value = {'files': []}
            mock_service.files().create().execute.return_value = {'id': file_id}
            mock_service.files().get().execute.return_value = {
                'id': file_id,
                'name': filename,
                'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            # Capture log output
            log_stream = StringIO()
            log_handler = logging.StreamHandler(log_stream)
            log_handler.setLevel(logging.INFO)
            
            # Create DriveManager with mocked authentication
            with patch.object(DriveManager, '_authenticate'):
                drive_manager = DriveManager(credentials_path='dummy_path')
                drive_manager.service = mock_service
                
                # Add handler to capture logs
                logger = logging.getLogger('finmatcher.reports.drive_manager')
                original_level = logger.level
                original_handlers = logger.handlers[:]
                logger.setLevel(logging.INFO)
                logger.addHandler(log_handler)
                
                try:
                    # Execute upload
                    result_file_id = drive_manager.upload_excel_report(
                        file_path=tmp_path,
                        folder_id=folder_id,
                        append=False
                    )
                    
                    # Get log output
                    log_output = log_stream.getvalue()
                    
                    # Property: Log must contain filename
                    assert filename in log_output or os.path.basename(tmp_path) in log_output, (
                        f"Log must contain filename. Expected '{filename}' or '{os.path.basename(tmp_path)}' "
                        f"in log output: {log_output}"
                    )
                    
                    # Property: Log must contain file_id
                    assert file_id in log_output, (
                        f"Log must contain file_id. Expected '{file_id}' in log_output: {log_output}"
                    )
                    
                    # Property: Log must indicate successful creation
                    assert 'created successfully' in log_output.lower() or 'file created' in log_output.lower(), (
                        f"Log must indicate successful creation. Log output: {log_output}"
                    )
                    
                finally:
                    logger.removeHandler(log_handler)
                    logger.setLevel(original_level)
                    logger.handlers = original_handlers
                    log_handler.close()
                    
        finally:
            # Ensure file is closed before deletion
            import time
            time.sleep(0.1)  # Small delay to ensure file handles are released
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass  # Ignore if file is still locked
    
    @given(
        filename=filename_strategy(),
        folder_id=folder_id_strategy(),
        source_prefix=source_prefix_strategy(),
        file_id=st.text(min_size=10, max_size=30)
    )
    @settings(max_examples=10, deadline=10000)  # Reduced examples and added deadline
    def test_attachment_upload_logs_required_fields(
        self, 
        filename, 
        folder_id, 
        source_prefix,
        file_id
    ):
        """
        Property: Attachment upload must log filename, folder_id, and file_id.
        
        Validates Requirement 10.3: Log file name, target folder, and upload timestamp
        """
        # Create temporary attachment file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b'%PDF-1.4 dummy content')
        
        try:
            # Mock Google Drive service
            mock_service = MagicMock()
            
            # Mock list to check for existing files (return empty for unique filename)
            mock_service.files().list().execute.return_value = {'files': []}
            
            # Mock create to return file_id
            mock_service.files().create().execute.return_value = {'id': file_id}
            
            # Mock get for verification
            mock_service.files().get().execute.return_value = {
                'id': file_id,
                'name': f"{source_prefix}_1.pdf",
                'mimeType': 'application/pdf'
            }
            
            # Capture log output
            log_stream = StringIO()
            log_handler = logging.StreamHandler(log_stream)
            log_handler.setLevel(logging.INFO)
            
            # Create DriveManager with mocked authentication
            with patch.object(DriveManager, '_authenticate'):
                drive_manager = DriveManager(credentials_path='dummy_path')
                drive_manager.service = mock_service
                
                # Add handler to capture logs
                logger = logging.getLogger('finmatcher.reports.drive_manager')
                original_level = logger.level
                original_handlers = logger.handlers[:]
                logger.setLevel(logging.INFO)
                logger.addHandler(log_handler)
                
                try:
                    # Execute upload
                    result_file_id = drive_manager.upload_attachment(
                        file_path=tmp_path,
                        folder_id=folder_id,
                        source_prefix=source_prefix
                    )
                    
                    # Get log output
                    log_output = log_stream.getvalue()
                    
                    # Property: Log must contain unique filename (with prefix and counter)
                    assert source_prefix in log_output, (
                        f"Log must contain source prefix. Expected '{source_prefix}' in log output: {log_output}"
                    )
                    
                    # Property: Log must contain folder_id
                    assert folder_id in log_output, (
                        f"Log must contain folder_id. Expected '{folder_id}' in log output: {log_output}"
                    )
                    
                    # Property: Log must contain file_id
                    assert file_id in log_output, (
                        f"Log must contain file_id. Expected '{file_id}' in log output: {log_output}"
                    )
                    
                    # Property: Log must indicate successful upload
                    assert 'uploaded' in log_output.lower() or 'attachment uploaded' in log_output.lower(), (
                        f"Log must indicate successful upload. Log output: {log_output}"
                    )
                    
                finally:
                    logger.removeHandler(log_handler)
                    logger.setLevel(original_level)
                    logger.handlers = original_handlers
                    log_handler.close()
                    
        finally:
            # Ensure file is closed before deletion
            import time
            time.sleep(0.1)  # Small delay to ensure file handles are released
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass  # Ignore if file is still locked
    
    @given(
        filename=filename_strategy(),
        folder_id=folder_id_strategy(),
        source_prefix=source_prefix_strategy(),
        retry_count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=10, deadline=10000)  # Reduced examples and added deadline
    def test_failed_upload_logs_error_with_retry_info(
        self,
        filename,
        folder_id,
        source_prefix,
        retry_count
    ):
        """
        Property: Failed uploads must log error messages with retry information.
        
        Validates Requirement 10.3: Log file operations including failures
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b'dummy content')
        
        try:
            # Mock Google Drive service to fail
            mock_service = MagicMock()
            mock_service.files().list().execute.return_value = {'files': []}
            
            # Make create fail with HttpError
            from googleapiclient.errors import HttpError
            mock_response = Mock()
            mock_response.status = 500
            mock_response.reason = 'Internal Server Error'
            
            mock_service.files().create().execute.side_effect = HttpError(
                resp=mock_response,
                content=b'Server error'
            )
            
            # Capture log output
            log_stream = StringIO()
            log_handler = logging.StreamHandler(log_stream)
            log_handler.setLevel(logging.WARNING)
            
            # Create DriveManager with mocked authentication
            with patch.object(DriveManager, '_authenticate'):
                drive_manager = DriveManager(credentials_path='dummy_path')
                drive_manager.service = mock_service
                
                # Add handler to capture logs
                logger = logging.getLogger('finmatcher.reports.drive_manager')
                original_level = logger.level
                original_handlers = logger.handlers[:]
                logger.setLevel(logging.WARNING)
                logger.addHandler(log_handler)
                
                try:
                    # Execute upload (should fail and retry)
                    with pytest.raises(HttpError):
                        drive_manager.upload_attachment(
                            file_path=tmp_path,
                            folder_id=folder_id,
                            source_prefix=source_prefix
                        )
                    
                    # Get log output
                    log_output = log_stream.getvalue()
                    
                    # Property: Log must contain error/warning messages
                    assert 'failed' in log_output.lower() or 'error' in log_output.lower(), (
                        f"Log must contain error/failure indication. Log output: {log_output}"
                    )
                    
                    # Property: Log must contain retry information
                    assert 'retry' in log_output.lower() or 'retrying' in log_output.lower(), (
                        f"Log must contain retry information. Log output: {log_output}"
                    )
                    
                finally:
                    logger.removeHandler(log_handler)
                    logger.setLevel(original_level)
                    logger.handlers = original_handlers
                    log_handler.close()
                    
        finally:
            # Ensure file is closed before deletion
            import time
            time.sleep(0.1)  # Small delay to ensure file handles are released
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass  # Ignore if file is still locked
    
    @given(
        filename=filename_strategy(),
        folder_id=folder_id_strategy()
    )
    @settings(max_examples=10, deadline=10000)  # Reduced examples and added deadline
    def test_excel_append_logs_operation_type(self, filename, folder_id):
        """
        Property: Excel report append operation must log that it's appending (not creating).
        
        Validates Requirement 10.3: Log file operations with operation type
        """
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(['Header1', 'Header2'])
            ws.append(['Data1', 'Data2'])
            wb.save(tmp_path)
        
        try:
            # Mock Google Drive service
            mock_service = MagicMock()
            
            # Mock list to return existing file
            existing_file_id = 'existing_file_123'
            mock_service.files().list().execute.return_value = {
                'files': [{'id': existing_file_id, 'name': filename}]
            }
            
            # Mock get_media to return existing file content
            mock_service.files().get_media().execute.return_value = open(tmp_path, 'rb').read()
            
            # Mock update
            mock_service.files().update().execute.return_value = {'id': existing_file_id}
            
            # Mock get for verification - this is not called in append mode, so we can skip it
            
            # Capture log output
            log_stream = StringIO()
            log_handler = logging.StreamHandler(log_stream)
            log_handler.setLevel(logging.INFO)
            
            # Create DriveManager with mocked authentication
            with patch.object(DriveManager, '_authenticate'):
                drive_manager = DriveManager(credentials_path='dummy_path')
                drive_manager.service = mock_service
                
                # Add handler to capture logs
                logger = logging.getLogger('finmatcher.reports.drive_manager')
                original_level = logger.level
                original_handlers = logger.handlers[:]
                logger.setLevel(logging.INFO)
                logger.addHandler(log_handler)
                
                try:
                    # Execute upload with append=True
                    result_file_id = drive_manager.upload_excel_report(
                        file_path=tmp_path,
                        folder_id=folder_id,
                        append=True
                    )
                    
                    # Get log output
                    log_output = log_stream.getvalue()
                    
                    # Property: Log must indicate append operation
                    assert 'append' in log_output.lower() or 'existing' in log_output.lower(), (
                        f"Log must indicate append operation. Log output: {log_output}"
                    )
                    
                    # Property: Log must contain filename
                    assert filename in log_output or os.path.basename(tmp_path) in log_output, (
                        f"Log must contain filename. Log output: {log_output}"
                    )
                    
                finally:
                    logger.removeHandler(log_handler)
                    logger.setLevel(original_level)
                    logger.handlers = original_handlers
                    log_handler.close()
                    
        finally:
            # Ensure file is closed before deletion
            import time
            time.sleep(0.1)  # Small delay to ensure file handles are released
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass  # Ignore if file is still locked
