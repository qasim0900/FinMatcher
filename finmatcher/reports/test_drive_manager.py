"""
Unit tests for DriveManager.

This module contains unit tests to verify Google Drive operations including:
- Folder creation with get_or_create pattern
- Excel report upload with append-or-create logic
- Attachment upload with unique filename generation
- Upload verification
- Retry logic with exponential backoff
- Error handling for various failure scenarios

Testing Framework: pytest
Feature: finmatcher-v2-upgrade
Validates: Requirement 4.6 (retry logic with exponential backoff for failed uploads)
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from decimal import Decimal
from datetime import date
from io import BytesIO
import openpyxl

from finmatcher.reports.drive_manager import DriveManager
from finmatcher.storage.models import (
    FolderStructure, AttachmentType, MatchConfidence
)
from googleapiclient.errors import HttpError


@pytest.fixture
def mock_credentials():
    """Create mock Google credentials."""
    with patch('finmatcher.reports.drive_manager.Credentials') as mock_creds:
        mock_creds.from_authorized_user_file.return_value = MagicMock(
            valid=True,
            expired=False
        )
        yield mock_creds


@pytest.fixture
def mock_drive_service():
    """Create mock Google Drive service."""
    service = MagicMock()
    
    # Mock files().list() for folder queries
    service.files().list().execute.return_value = {'files': []}
    
    # Mock files().create() for folder/file creation
    service.files().create().execute.return_value = {'id': 'mock_folder_id'}
    
    # Mock files().get() for verification
    service.files().get().execute.return_value = {'id': 'mock_file_id', 'name': 'test.xlsx'}
    
    # Mock files().get_media() for downloading files
    service.files().get_media().execute.return_value = b''
    
    # Mock files().update() for updating files
    service.files().update().execute.return_value = {'id': 'mock_file_id'}
    
    return service


@pytest.fixture
def drive_manager(mock_credentials, mock_drive_service):
    """Create DriveManager instance with mocked service."""
    with patch('finmatcher.reports.drive_manager.build', return_value=mock_drive_service):
        with patch('finmatcher.reports.drive_manager.os.path.exists', return_value=True):
            manager = DriveManager(credentials_path='mock_credentials.json')
            manager.service = mock_drive_service
            return manager


@pytest.fixture
def temp_excel_file():
    """Create a temporary Excel file for testing."""
    fd, path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)
    
    # Create a simple Excel file
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Header1', 'Header2', 'Header3'])
    ws.append(['Data1', 'Data2', 'Data3'])
    wb.save(path)
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_attachment_file():
    """Create a temporary attachment file for testing."""
    fd, path = tempfile.mkstemp(suffix='.pdf')
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(b'Mock PDF content')
    
    yield path
    
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


class TestFolderCreation:
    """
    Test folder creation scenarios.
    
    Validates: Requirements 3.9, 3.10 (get_or_create pattern)
    """
    
    def test_create_new_folder(self, drive_manager, mock_drive_service):
        """Test creating a new folder when it doesn't exist."""
        # Mock: folder doesn't exist
        mock_drive_service.files().list().execute.return_value = {'files': []}
        mock_drive_service.files().create().execute.return_value = {'id': 'new_folder_id'}
        
        folder_id = drive_manager.get_or_create_folder('TestFolder')
        
        assert folder_id == 'new_folder_id'
        
        # Verify folder creation was called
        mock_drive_service.files().create.assert_called_once()