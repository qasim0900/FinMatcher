"""
Property-based tests for DriveManager attachment filename pattern.

This module contains property-based tests using Hypothesis to verify:
- Property 11: Attachment Filename Pattern

Testing Framework: pytest + hypothesis
Feature: finmatcher-v2-upgrade
Validates: Requirements 4.4
"""

import pytest
import tempfile
import os
import re
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume

from finmatcher.reports.drive_manager import DriveManager


# Strategy for generating valid source prefixes
@st.composite
def source_prefix_strategy(draw):
    """Generate valid source prefixes."""
    return draw(st.sampled_from(['email', 'statement', 'manual', 'import', 'receipt']))


# Strategy for generating valid file extensions
@st.composite
def file_extension_strategy(draw):
    """Generate valid file extensions."""
    return draw(st.sampled_from(['pdf', 'jpg', 'png', 'gif', 'doc', 'docx', 'xlsx', 'txt']))


# Strategy for generating valid folder IDs
@st.composite
def folder_id_strategy(draw):
    """Generate valid Google Drive folder IDs."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=10,
        max_size=30
    ))


# Strategy for generating valid original filenames
@st.composite
def original_filename_strategy(draw):
    """Generate valid original filenames with various extensions."""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=1,
        max_size=20
    ))
    extension = draw(file_extension_strategy())
    return f"{name}.{extension}"


class TestAttachmentFilenamePatternProperty:
    """
    Property 11: Attachment Filename Pattern
    
    Universal Property:
    FOR ALL attachments with source prefix and extension,
    WHEN the Drive_Manager generates a unique filename,
    THEN the filename SHALL match the pattern "{Source}_{Counter}.{Extension}"
    WHERE Counter ensures uniqueness within the target folder.
    
    Validates Requirement 4.4:
    WHEN uploading an Attachment_File or Attachment_Image, THE Drive_Manager 
    SHALL generate a unique filename using the pattern "{Source}_{Counter}.{Extension}"
    """
    
    @given(
        source_prefix=source_prefix_strategy(),
        original_filename=original_filename_strategy(),
        folder_id=folder_id_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_filename_matches_pattern(self, source_prefix, original_filename, folder_id):
        """
        Property: Generated filename must match {Source}_{Counter}.{Extension} pattern.
        
        Validates Requirement 4.4: Generate unique filename using pattern
        """
        # Mock Google Drive service
        mock_service = MagicMock()
        
        # Mock list to return no existing files (first filename is available)
        mock_service.files().list().execute.return_value = {'files': []}
        
        # Create DriveManager with mocked authentication
        with patch.object(DriveManager, '_authenticate'):
            drive_manager = DriveManager(credentials_path='dummy_path')
            drive_manager.service = mock_service
            
            # Generate unique filename
            unique_filename = drive_manager._generate_unique_filename(
                original_name=original_filename,
                prefix=source_prefix,
                folder_id=folder_id
            )
            
            # Extract extension from original filename
            name_parts = original_filename.rsplit('.', 1)
            expected_extension = name_parts[1] if len(name_parts) > 1 else ''
            
            # Property: Filename must match pattern {Source}_{Counter}.{Extension}
            if expected_extension:
                pattern = rf'^{re.escape(source_prefix)}_(\d+)\.{re.escape(expected_extension)}$'
            else:
                pattern = rf'^{re.escape(source_prefix)}_(\d+)$'
            
            assert re.match(pattern, unique_filename), (
                f"Filename '{unique_filename}' does not match pattern '{pattern}'. "
                f"Expected format: {source_prefix}_<counter>.{expected_extension}"
            )
            
            # Property: Counter must be a positive integer
            if expected_extension:
                counter_match = re.search(rf'{re.escape(source_prefix)}_(\d+)\.{re.escape(expected_extension)}', unique_filename)
            else:
                counter_match = re.search(rf'{re.escape(source_prefix)}_(\d+)', unique_filename)
            
            assert counter_match, f"Could not extract counter from filename '{unique_filename}'"
            counter = int(counter_match.group(1))
            assert counter >= 1, f"Counter must be >= 1, got {counter}"
    
    @given(
        source_prefix=source_prefix_strategy(),
        original_filename=original_filename_strategy(),
        folder_id=folder_id_strategy(),
        existing_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=50, deadline=10000)
    def test_filename_counter_ensures_uniqueness(
        self, 
        source_prefix, 
        original_filename, 
        folder_id,
        existing_count
    ):
        """
        Property: Counter must increment to ensure uniqueness when files exist.
        
        Validates Requirement 4.4: Counter ensures uniqueness
        """
        # Extract extension from original filename
        name_parts = original_filename.rsplit('.', 1)
        extension = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create list of existing files with sequential counters
        existing_files = []
        for i in range(1, existing_count + 1):
            if extension:
                filename = f"{source_prefix}_{i}.{extension}"
            else:
                filename = f"{source_prefix}_{i}"
            existing_files.append({'id': f'file_{i}', 'name': filename})
        
        # Mock Google Drive service
        mock_service = MagicMock()
        
        # Mock list to return existing files on first calls, then empty for the new filename
        call_count = [0]
        
        def mock_list_execute():
            call_count[0] += 1
            # Return existing files for counters 1 through existing_count
            # Return empty for counter existing_count + 1
            if call_count[0] <= existing_count:
                # Return the file that matches this counter
                matching_file = [f for f in existing_files if f['name'].endswith(f"_{call_count[0]}.{extension}") or f['name'].endswith(f"_{call_count[0]}")]
                return {'files': matching_file if matching_file else []}
            else:
                return {'files': []}
        
        mock_service.files().list().execute.side_effect = mock_list_execute
        
        # Create DriveManager with mocked authentication
        with patch.object(DriveManager, '_authenticate'):
            drive_manager = DriveManager(credentials_path='dummy_path')
            drive_manager.service = mock_service
            
            # Generate unique filename
            unique_filename = drive_manager._generate_unique_filename(
                original_name=original_filename,
                prefix=source_prefix,
                folder_id=folder_id
            )
            
            # Property: Generated filename must have counter = existing_count + 1
            expected_counter = existing_count + 1
            if extension:
                expected_filename = f"{source_prefix}_{expected_counter}.{extension}"
            else:
                expected_filename = f"{source_prefix}_{expected_counter}"
            
            assert unique_filename == expected_filename, (
                f"Expected filename '{expected_filename}' with counter {expected_counter}, "
                f"got '{unique_filename}'"
            )
            
            # Property: Generated filename must not match any existing filename
            existing_filenames = [f['name'] for f in existing_files]
            assert unique_filename not in existing_filenames, (
                f"Generated filename '{unique_filename}' conflicts with existing files: {existing_filenames}"
            )
    
    @given(
        source_prefix=source_prefix_strategy(),
        original_filename=original_filename_strategy(),
        folder_id=folder_id_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_filename_preserves_extension(self, source_prefix, original_filename, folder_id):
        """
        Property: Generated filename must preserve the original file extension.
        
        Validates Requirement 4.4: Extension is preserved in pattern
        """
        # Mock Google Drive service
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': []}
        
        # Create DriveManager with mocked authentication
        with patch.object(DriveManager, '_authenticate'):
            drive_manager = DriveManager(credentials_path='dummy_path')
            drive_manager.service = mock_service
            
            # Generate unique filename
            unique_filename = drive_manager._generate_unique_filename(
                original_name=original_filename,
                prefix=source_prefix,
                folder_id=folder_id
            )
            
            # Extract extension from original filename
            name_parts = original_filename.rsplit('.', 1)
            original_extension = name_parts[1] if len(name_parts) > 1 else ''
            
            # Property: Generated filename must have the same extension
            if original_extension:
                assert unique_filename.endswith(f".{original_extension}"), (
                    f"Generated filename '{unique_filename}' does not preserve "
                    f"original extension '.{original_extension}'"
                )
                
                # Extract extension from generated filename
                generated_parts = unique_filename.rsplit('.', 1)
                generated_extension = generated_parts[1] if len(generated_parts) > 1 else ''
                
                assert generated_extension == original_extension, (
                    f"Extension mismatch: original='{original_extension}', "
                    f"generated='{generated_extension}'"
                )
            else:
                # If no extension in original, generated should also have no extension
                assert '.' not in unique_filename or unique_filename.count('.') == 0, (
                    f"Original filename '{original_filename}' has no extension, "
                    f"but generated filename '{unique_filename}' has one"
                )
    
    @given(
        source_prefix=source_prefix_strategy(),
        original_filename=original_filename_strategy(),
        folder_id=folder_id_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_filename_starts_with_source_prefix(self, source_prefix, original_filename, folder_id):
        """
        Property: Generated filename must start with the source prefix.
        
        Validates Requirement 4.4: Source prefix is first component of pattern
        """
        # Mock Google Drive service
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': []}
        
        # Create DriveManager with mocked authentication
        with patch.object(DriveManager, '_authenticate'):
            drive_manager = DriveManager(credentials_path='dummy_path')
            drive_manager.service = mock_service
            
            # Generate unique filename
            unique_filename = drive_manager._generate_unique_filename(
                original_name=original_filename,
                prefix=source_prefix,
                folder_id=folder_id
            )
            
            # Property: Filename must start with source prefix
            assert unique_filename.startswith(source_prefix), (
                f"Generated filename '{unique_filename}' does not start with "
                f"source prefix '{source_prefix}'"
            )
            
            # Property: After prefix, there must be an underscore
            assert unique_filename[len(source_prefix)] == '_', (
                f"Generated filename '{unique_filename}' does not have underscore "
                f"after source prefix '{source_prefix}'"
            )
    
    @given(
        source_prefix=source_prefix_strategy(),
        folder_id=folder_id_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_filename_handles_no_extension(self, source_prefix, folder_id):
        """
        Property: Generated filename must handle files without extensions correctly.
        
        Validates Requirement 4.4: Pattern works with or without extension
        """
        # Original filename without extension
        original_filename = "filename_without_extension"
        
        # Mock Google Drive service
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': []}
        
        # Create DriveManager with mocked authentication
        with patch.object(DriveManager, '_authenticate'):
            drive_manager = DriveManager(credentials_path='dummy_path')
            drive_manager.service = mock_service
            
            # Generate unique filename
            unique_filename = drive_manager._generate_unique_filename(
                original_name=original_filename,
                prefix=source_prefix,
                folder_id=folder_id
            )
            
            # Property: Filename must match pattern {Source}_{Counter} (no extension)
            pattern = rf'^{re.escape(source_prefix)}_(\d+)$'
            assert re.match(pattern, unique_filename), (
                f"Filename '{unique_filename}' does not match pattern '{pattern}' "
                f"for files without extension"
            )
            
            # Property: Filename must not have a dot (no extension)
            assert '.' not in unique_filename, (
                f"Filename '{unique_filename}' should not have extension when "
                f"original filename '{original_filename}' has none"
            )
    
    @given(
        source_prefix=source_prefix_strategy(),
        original_filename=original_filename_strategy(),
        folder_id=folder_id_strategy()
    )
    @settings(max_examples=50, deadline=10000)
    def test_upload_attachment_uses_generated_pattern(
        self, 
        source_prefix, 
        original_filename, 
        folder_id
    ):
        """
        Property: upload_attachment must use the generated filename pattern.
        
        Validates Requirement 4.4: Upload operation uses pattern
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b'%PDF-1.4 dummy content')
        
        try:
            # Mock Google Drive service
            mock_service = MagicMock()
            
            # Mock list to return no existing files
            mock_service.files().list().execute.return_value = {'files': []}
            
            # Mock create to capture the filename used
            file_id = 'test_file_123'
            mock_service.files().create().execute.return_value = {'id': file_id}
            
            # Mock get for verification
            mock_service.files().get().execute.return_value = {
                'id': file_id,
                'name': f"{source_prefix}_1.pdf",
                'mimeType': 'application/pdf'
            }
            
            # Create DriveManager with mocked authentication
            with patch.object(DriveManager, '_authenticate'):
                drive_manager = DriveManager(credentials_path='dummy_path')
                drive_manager.service = mock_service
                
                # Execute upload
                result_file_id = drive_manager.upload_attachment(
                    file_path=tmp_path,
                    folder_id=folder_id,
                    source_prefix=source_prefix
                )
                
                # Get the filename that was used in the create call
                create_call = mock_service.files().create.call_args
                file_metadata = create_call[1]['body']
                uploaded_filename = file_metadata['name']
                
                # Extract extension from temp file
                temp_extension = os.path.splitext(tmp_path)[1][1:]  # Remove leading dot
                
                # Property: Uploaded filename must match pattern
                pattern = rf'^{re.escape(source_prefix)}_(\d+)\.{re.escape(temp_extension)}$'
                assert re.match(pattern, uploaded_filename), (
                    f"Uploaded filename '{uploaded_filename}' does not match pattern '{pattern}'"
                )
                
                # Property: Result must be the file_id
                assert result_file_id == file_id, (
                    f"Expected file_id '{file_id}', got '{result_file_id}'"
                )
                
        finally:
            # Clean up temporary file
            import time
            time.sleep(0.1)
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass

