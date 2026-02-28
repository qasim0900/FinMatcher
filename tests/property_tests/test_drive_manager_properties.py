"""
Property-based tests for Drive Manager.

This module contains property-based tests using Hypothesis to verify
universal properties of the Drive Manager component.

Testing Framework: pytest + Hypothesis
Feature: finmatcher-v2-upgrade
Task: 9.3 - Write property test for folder name pattern
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, MagicMock, patch
from typing import List

from finmatcher.reports.drive_manager import DriveManager
from finmatcher.storage.models import FolderStructure, AttachmentType, MatchConfidence


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=100)
settings.load_profile("finmatcher")


class TestDriveManagerProperties:
    """
    Property-based tests for Drive Manager.
    
    Tests verify universal properties that should hold across all inputs.
    """
    
    # Feature: finmatcher-v2-upgrade, Property 8: Folder Name Pattern for Statements
    @given(
        statement_name=st.text(
            min_size=1, 
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='_-. '
            )
        )
    )
    @settings(max_examples=20)
    def test_folder_name_pattern_for_statements(self, statement_name: str):
        """
        **Validates: Requirements 3.2**
        
        Property 8: Folder Name Pattern for Statements
        
        For any statement filename, the generated subfolder name must follow
        the pattern "{Statement_File_Name}_record.xlsx".
        
        This property ensures that:
        1. The folder name is derived from the statement filename
        2. The pattern "{Statement_File_Name}_record.xlsx" is consistently applied
        3. The folder name is predictable and follows the specification
        """
        # Mock the Google Drive service and authentication
        with patch.object(DriveManager, '_authenticate') as mock_auth:
            # Setup mock service
            mock_service = MagicMock()
            
            # Create DriveManager with mocked authentication
            drive_manager = DriveManager(credentials_path="mock_credentials.json")
            drive_manager.service = mock_service
            
            # Mock the folder structure
            mock_folder_structure = FolderStructure(
                root_id="mock_root_id",
                statement_folders={},
                other_receipts_id="mock_other_receipts_id",
                unmatch_email_id="mock_unmatch_email_id",
                attach_files_id="mock_attach_files_id",
                attach_image_id="mock_attach_image_id",
                unmatch_attach_files_id="mock_unmatch_attach_files_id",
                unmatch_attach_image_id="mock_unmatch_attach_image_id"
            )
            drive_manager.folder_structure = mock_folder_structure
            
            # Mock the get_or_create_folder method to return a folder ID
            def mock_get_or_create_folder(name: str, parent_id: str = None) -> str:
                # Verify the folder name follows the pattern
                expected_pattern = f"{statement_name}_record.xlsx"
                assert name == expected_pattern, \
                    f"Folder name '{name}' does not match expected pattern '{expected_pattern}'"
                return f"folder_id_for_{name}"
            
            # Mock the get_or_create_folder method
            drive_manager.get_or_create_folder = mock_get_or_create_folder
            
            # Call the method under test
            folder_id = drive_manager.get_or_create_statement_folder(statement_name)
            
            # Verify the folder ID is returned
            expected_folder_name = f"{statement_name}_record.xlsx"
            expected_folder_id = f"folder_id_for_{expected_folder_name}"
            assert folder_id == expected_folder_id, \
                f"Expected folder ID '{expected_folder_id}', got '{folder_id}'"
            
            # Verify the folder name is cached in the folder structure
            assert expected_folder_name in drive_manager.folder_structure.statement_folders, \
                f"Folder name '{expected_folder_name}' not cached in folder structure"
            
            assert drive_manager.folder_structure.statement_folders[expected_folder_name] == expected_folder_id, \
                f"Cached folder ID does not match expected ID"
    
    # Feature: finmatcher-v2-upgrade, Property 9: Folder Creation is Idempotent
    @given(
        folder_name=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='_-. '
            )
        ),
        parent_id=st.one_of(
            st.none(),
            st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
        ),
        call_count=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=20)
    def test_folder_creation_is_idempotent(self, folder_name: str, parent_id: str, call_count: int):
        """
        **Validates: Requirements 3.10**
        
        Property 9: Folder Creation is Idempotent
        
        For any folder name and parent ID, calling get_or_create_folder multiple times
        must return the same folder ID.
        
        This property ensures that:
        1. Multiple calls with the same parameters return the same folder ID
        2. No duplicate folders are created
        3. The operation is truly idempotent (safe to retry)
        4. Caching works correctly across multiple calls
        """
        # Mock the Google Drive service and authentication
        with patch.object(DriveManager, '_authenticate') as mock_auth:
            # Setup mock service
            mock_service = MagicMock()
            
            # Track API calls to verify idempotency
            api_call_count = {'list': 0, 'create': 0}
            
            # Mock the files().list() method
            def mock_list(**kwargs):
                api_call_count['list'] += 1
                mock_result = MagicMock()
                
                # First call: folder doesn't exist
                # Subsequent calls: folder exists (simulating creation)
                if api_call_count['list'] == 1:
                    mock_result.execute.return_value = {'files': []}
                else:
                    mock_result.execute.return_value = {
                        'files': [{'id': f'folder_id_{folder_name}', 'name': folder_name}]
                    }
                return mock_result
            
            # Mock the files().create() method
            def mock_create(**kwargs):
                api_call_count['create'] += 1
                mock_result = MagicMock()
                mock_result.execute.return_value = {'id': f'folder_id_{folder_name}'}
                return mock_result
            
            # Setup mock service methods
            mock_files = MagicMock()
            mock_files.list = mock_list
            mock_files.create = mock_create
            mock_service.files.return_value = mock_files
            
            # Create DriveManager with mocked authentication
            drive_manager = DriveManager(credentials_path="mock_credentials.json")
            drive_manager.service = mock_service
            
            # Call get_or_create_folder multiple times
            folder_ids = []
            for i in range(call_count):
                folder_id = drive_manager.get_or_create_folder(folder_name, parent_id)
                folder_ids.append(folder_id)
            
            # Property: All returned folder IDs must be identical
            assert len(set(folder_ids)) == 1, \
                f"Folder creation is not idempotent: got different IDs {folder_ids}"
            
            expected_folder_id = f'folder_id_{folder_name}'
            assert all(fid == expected_folder_id for fid in folder_ids), \
                f"Expected all folder IDs to be '{expected_folder_id}', got {folder_ids}"
            
            # Verify that folder was only created once (idempotency check)
            # First call: list (not found) + create
            # Subsequent calls: should use cache (no API calls)
            assert api_call_count['create'] <= 1, \
                f"Folder was created {api_call_count['create']} times, expected at most 1"
            
            # Verify caching: after first call, subsequent calls should use cache
            # So we should only see 1 list call (first time) and 1 create call
            assert api_call_count['list'] <= 1, \
                f"API list was called {api_call_count['list']} times, expected at most 1 (caching should prevent repeated calls)"
    
    # Feature: finmatcher-v2-upgrade, Property 12: Attachment Classification by Extension
    @given(
        file_extension=st.sampled_from([
            '.pdf', '.doc', '.docx',  # Document extensions
            '.jpg', '.jpeg', '.png', '.gif',  # Image extensions
            '.PDF', '.DOC', '.DOCX',  # Uppercase document extensions
            '.JPG', '.JPEG', '.PNG', '.GIF',  # Uppercase image extensions
        ]),
        filename_base=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='_-'
            )
        )
    )
    @settings(max_examples=20)
    def test_attachment_classification_by_extension(self, file_extension: str, filename_base: str):
        """
        **Validates: Requirements 5.1, 5.2, 5.3**
        
        Property 12: Attachment Classification by Extension
        
        For any file with extension in {PDF, DOC, DOCX}, it must be classified as
        Attachment_File (DOCUMENT); for any file with extension in {JPG, JPEG, PNG, GIF},
        it must be classified as Attachment_Image (IMAGE).
        
        This property ensures that:
        1. PDF, DOC, DOCX files are classified as DOCUMENT
        2. JPG, JPEG, PNG, GIF files are classified as IMAGE
        3. Classification is case-insensitive
        4. Classification is based solely on file extension
        """
        # Mock the Google Drive service and authentication
        with patch.object(DriveManager, '_authenticate') as mock_auth:
            # Setup mock service
            mock_service = MagicMock()
            
            # Create DriveManager with mocked authentication
            drive_manager = DriveManager(credentials_path="mock_credentials.json")
            drive_manager.service = mock_service
            
            # Construct file path with the given extension
            file_path = f"{filename_base}{file_extension}"
            
            # Call the classify_attachment method
            attachment_type = drive_manager.classify_attachment(file_path)
            
            # Normalize extension to lowercase for comparison
            normalized_extension = file_extension.lower()
            
            # Define expected classification based on extension
            document_extensions = {'.pdf', '.doc', '.docx'}
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
            
            # Verify classification matches requirements
            if normalized_extension in document_extensions:
                assert attachment_type == AttachmentType.DOCUMENT, \
                    f"File '{file_path}' with extension '{file_extension}' should be classified as DOCUMENT, got {attachment_type}"
            elif normalized_extension in image_extensions:
                assert attachment_type == AttachmentType.IMAGE, \
                    f"File '{file_path}' with extension '{file_extension}' should be classified as IMAGE, got {attachment_type}"
            else:
                # This should not happen with our sampled_from strategy, but handle it for completeness
                pytest.fail(f"Unexpected extension '{file_extension}' in test data")
    
    @given(
        unknown_extension=st.text(
            min_size=2,
            max_size=10,
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
        ).filter(lambda ext: ext.lower() not in {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif'}),
        filename_base=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='_-'
            )
        )
    )
    @settings(max_examples=10)
    def test_unknown_extension_defaults_to_document(self, unknown_extension: str, filename_base: str):
        """
        **Validates: Requirements 5.1**
        
        Property 12 (Extended): Unknown Extension Default Classification
        
        For any file with an unknown extension (not in the defined document or image
        extensions), it must default to DOCUMENT classification.
        
        This property ensures that:
        1. Unknown file types are handled gracefully
        2. Default classification is DOCUMENT
        3. System doesn't crash on unexpected file types
        """
        # Mock the Google Drive service and authentication
        with patch.object(DriveManager, '_authenticate') as mock_auth:
            # Setup mock service
            mock_service = MagicMock()
            
            # Create DriveManager with mocked authentication
            drive_manager = DriveManager(credentials_path="mock_credentials.json")
            drive_manager.service = mock_service
            
            # Ensure extension starts with a dot
            if not unknown_extension.startswith('.'):
                unknown_extension = f'.{unknown_extension}'
            
            # Construct file path with the unknown extension
            file_path = f"{filename_base}{unknown_extension}"
            
            # Call the classify_attachment method
            attachment_type = drive_manager.classify_attachment(file_path)
            
            # Verify unknown extensions default to DOCUMENT
            assert attachment_type == AttachmentType.DOCUMENT, \
                f"File '{file_path}' with unknown extension '{unknown_extension}' should default to DOCUMENT, got {attachment_type}"

    # Feature: finmatcher-v2-upgrade, Property 13: Attachment Routing Based on Confidence and Type
    @given(
        confidence=st.sampled_from([
            MatchConfidence.EXACT,
            MatchConfidence.HIGH,
            MatchConfidence.LOW
        ]),
        file_extension=st.sampled_from([
            '.pdf', '.doc', '.docx',  # Document extensions
            '.jpg', '.jpeg', '.png', '.gif',  # Image extensions
        ]),
        filename_base=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='_-'
            )
        ),
        source_prefix=st.sampled_from(['email', 'statement', 'manual'])
    )
    @settings(max_examples=20)
    def test_attachment_routing_based_on_confidence_and_type(
        self, 
        confidence: MatchConfidence, 
        file_extension: str, 
        filename_base: str,
        source_prefix: str
    ):
        """
        **Validates: Requirements 5.4, 5.5, 5.6, 5.7**
        
        Property 13: Attachment Routing Based on Confidence and Type
        
        For any receipt with attachments, if confidence is Exact or High, documents
        must route to "Attach_files" and images to "Attach_Image"; if confidence is
        Low, documents must route to "Unmatch_Email_Attach_files" and images to
        "unmatch_attach_image".
        
        This property ensures that:
        1. Exact/High confidence documents route to "Attach_files" (Req 5.4)
        2. Exact/High confidence images route to "Attach_Image" (Req 5.5)
        3. Low confidence documents route to "Unmatch_Email_Attach_files" (Req 5.6)
        4. Low confidence images route to "unmatch_attach_image" (Req 5.7)
        5. Routing is deterministic based on confidence and file type
        """
        # Mock the Google Drive service and authentication
        with patch.object(DriveManager, '_authenticate') as mock_auth:
            # Setup mock service
            mock_service = MagicMock()
            
            # Create DriveManager with mocked authentication
            drive_manager = DriveManager(credentials_path="mock_credentials.json")
            drive_manager.service = mock_service
            
            # Mock the folder structure with all required folder IDs
            mock_folder_structure = FolderStructure(
                root_id="mock_root_id",
                statement_folders={},
                other_receipts_id="mock_other_receipts_id",
                unmatch_email_id="mock_unmatch_email_id",
                attach_files_id="mock_attach_files_id",
                attach_image_id="mock_attach_image_id",
                unmatch_attach_files_id="mock_unmatch_attach_files_id",
                unmatch_attach_image_id="mock_unmatch_attach_image_id"
            )
            drive_manager.folder_structure = mock_folder_structure
            
            # Track which folder ID was used for upload
            uploaded_to_folder_id = None
            
            # Mock the upload_attachment method to capture the folder ID
            def mock_upload_attachment(file_path: str, folder_id: str, prefix: str) -> str:
                nonlocal uploaded_to_folder_id
                uploaded_to_folder_id = folder_id
                return f"file_id_{filename_base}"
            
            drive_manager.upload_attachment = mock_upload_attachment
            
            # Construct file path with the given extension
            file_path = f"{filename_base}{file_extension}"
            
            # Call the route_attachment method
            file_id = drive_manager.route_attachment(file_path, confidence, source_prefix)
            
            # Verify the file was uploaded
            assert file_id == f"file_id_{filename_base}", \
                f"Expected file ID 'file_id_{filename_base}', got '{file_id}'"
            
            # Determine expected folder ID based on confidence and file type
            normalized_extension = file_extension.lower()
            document_extensions = {'.pdf', '.doc', '.docx'}
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
            
            # Classify attachment type
            is_document = normalized_extension in document_extensions
            is_image = normalized_extension in image_extensions
            
            # Determine expected folder based on requirements
            if confidence in (MatchConfidence.EXACT, MatchConfidence.HIGH):
                # Matched attachments (high confidence)
                if is_document:
                    # Requirement 5.4: Matched documents go to "Attach_files"
                    expected_folder_id = mock_folder_structure.attach_files_id
                    expected_folder_name = "Attach_files"
                elif is_image:
                    # Requirement 5.5: Matched images go to "Attach_Image"
                    expected_folder_id = mock_folder_structure.attach_image_id
                    expected_folder_name = "Attach_Image"
                else:
                    pytest.fail(f"Unexpected extension '{file_extension}' in test data")
            else:  # LOW confidence
                # Unmatched attachments (low confidence)
                if is_document:
                    # Requirement 5.6: Unmatched documents go to "Unmatch_Email_Attach_files"
                    expected_folder_id = mock_folder_structure.unmatch_attach_files_id
                    expected_folder_name = "Unmatch_Email_Attach_files"
                elif is_image:
                    # Requirement 5.7: Unmatched images go to "unmatch_attach_image"
                    expected_folder_id = mock_folder_structure.unmatch_attach_image_id
                    expected_folder_name = "unmatch_attach_image"
                else:
                    pytest.fail(f"Unexpected extension '{file_extension}' in test data")
            
            # Verify the attachment was routed to the correct folder
            assert uploaded_to_folder_id == expected_folder_id, \
                f"Attachment '{file_path}' with confidence '{confidence.value}' should be routed to '{expected_folder_name}' (ID: {expected_folder_id}), but was routed to folder ID: {uploaded_to_folder_id}"

