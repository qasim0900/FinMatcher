"""
Google Drive Integration with OAuth2 Authentication.

This module handles uploading reports and attachments to Google Drive
with automatic folder creation, retry logic, and OAuth2 authentication.

Validates Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

import os
import time
from pathlib import Path
from typing import Optional, List, Dict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from finmatcher.utils.logger import get_logger
from finmatcher.config.settings import get_settings


logger = get_logger(__name__)


class DriveSync:
    """
    Google Drive synchronization manager.
    
    Handles OAuth2 authentication, folder creation, and file uploads
    with retry logic and exponential backoff.
    
    Validates Requirements:
    - 9.1: OAuth2 authentication with Google Drive API
    - 9.2: Token refresh mechanism
    - 9.3: Folder idempotence (check before creating)
    - 9.4: Retry logic with exponential backoff
    - 9.5: Upload Excel reports to statement-specific folders
    - 9.6: Upload Other_Financial_records to separate folder
    """
    
    def __init__(self, google_account_email: Optional[str] = None):
        """
        Initialize Drive sync with OAuth2 credentials.
        
        Args:
            google_account_email: Email of Google account to use (defaults to first account)
        """
        self.settings = get_settings()
        
        # Select Google account
        if google_account_email:
            self.google_account = next(
                (acc for acc in self.settings.google_accounts if acc.email == google_account_email),
                self.settings.google_accounts[0]
            )
        else:
            self.google_account = self.settings.google_accounts[0]
        
        logger.info(f"Initializing Drive sync for account: {self.google_account.email}")
        
        # Authenticate and build service
        self.creds = self._authenticate()
        self.service = build('drive', 'v3', credentials=self.creds)
        
        # Cache for folder IDs
        self._folder_cache: Dict[str, str] = {}
    
    def _authenticate(self) -> Credentials:
        """
        Authenticate with Google Drive API using OAuth2.
        
        Implements token refresh mechanism for expired tokens.
        
        Returns:
            Credentials: Authenticated Google credentials
            
        Validates Requirements: 9.1, 9.2
        """
        creds = None
        token_path = Path(self.google_account.token_file)
        creds_path = Path(self.google_account.creds_file)
        
        # Load existing token if available
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(token_path),
                    self.settings.gmail_api_credentials.scopes
                )
                logger.info(f"Loaded existing token from {token_path}")
            except Exception as e:
                logger.warning(f"Failed to load token from {token_path}: {e}")
        
        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {creds_path}\n"
                        f"Please download OAuth2 credentials from Google Cloud Console"
                    )
                
                logger.info("Starting OAuth2 flow for new token...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path),
                    self.settings.gmail_api_credentials.scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("OAuth2 flow completed successfully")
            
            # Save token for future use
            try:
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(token_path, 'w') as token_file:
                    token_file.write(creds.to_json())
                logger.info(f"Token saved to {token_path}")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")
        
        return creds

    
    def _find_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find folder by name in Drive.
        
        Args:
            folder_name: Name of folder to find
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID if found, None otherwise
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()
            
            files = results.get('files', [])
            if files:
                logger.debug(f"Found existing folder '{folder_name}': {files[0]['id']}")
                return files[0]['id']
            
            return None
        except HttpError as e:
            logger.error(f"Error searching for folder '{folder_name}': {e}")
            return None
    
    def _create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create folder in Drive with idempotence check.
        
        Checks if folder exists before creating to ensure idempotence.
        
        Args:
            folder_name: Name of folder to create
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID (existing or newly created)
            
        Validates Requirements: 9.3
        """
        # Check cache first
        cache_key = f"{parent_id or 'root'}:{folder_name}"
        if cache_key in self._folder_cache:
            logger.debug(f"Using cached folder ID for '{folder_name}'")
            return self._folder_cache[cache_key]
        
        # Check if folder already exists
        existing_id = self._find_folder(folder_name, parent_id)
        if existing_id:
            self._folder_cache[cache_key] = existing_id
            return existing_id
        
        # Create new folder
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created folder '{folder_name}': {folder_id}")
            
            # Cache the folder ID
            self._folder_cache[cache_key] = folder_id
            return folder_id
        
        except HttpError as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise
    
    def _upload_file_with_retry(
        self,
        file_path: Path,
        folder_id: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Upload file to Drive with exponential backoff retry logic.
        
        Retries failed uploads up to max_retries times with exponential backoff.
        
        Args:
            file_path: Path to file to upload
            folder_id: Destination folder ID
            max_retries: Maximum number of retry attempts
            
        Returns:
            File ID if successful, None otherwise
            
        Validates Requirements: 9.4
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        file_metadata = {
            'name': file_path.name,
            'parents': [folder_id]
        }
        
        # Determine MIME type
        mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        if file_path.suffix.lower() == '.pdf':
            mime_type = 'application/pdf'
        
        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Uploading {file_path.name} (attempt {attempt + 1}/{max_retries})...")
                
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                file_id = file.get('id')
                logger.info(f"Successfully uploaded {file_path.name}: {file_id}")
                return file_id
            
            except HttpError as e:
                logger.warning(f"Upload attempt {attempt + 1} failed for {file_path.name}: {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2 ** attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} upload attempts failed for {file_path.name}")
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error uploading {file_path.name}: {e}")
                return None
        
        return None

    
    def upload_statement_report(
        self,
        report_path: Path,
        statement_type: str
    ) -> bool:
        """
        Upload statement report to appropriate Drive folder.
        
        Creates statement-specific folder if it doesn't exist and uploads report.
        
        Args:
            report_path: Path to Excel report file
            statement_type: Type of statement (meriwest, amex, chase)
            
        Returns:
            True if upload successful, False otherwise
            
        Validates Requirements: 9.3, 9.5
        """
        try:
            # Get main drive folder ID
            main_folder_id = self.settings.drive_folder_ids.drive_folder_id
            
            # Determine statement-specific folder name
            folder_name_map = {
                'meriwest': 'Meriwest_Receipts',
                'amex': 'Amex_Receipts',
                'chase': 'Chase_Receipts'
            }
            
            folder_name = folder_name_map.get(statement_type.lower())
            if not folder_name:
                logger.error(f"Unknown statement type: {statement_type}")
                return False
            
            # Create or get statement-specific folder
            logger.info(f"Ensuring folder exists: {folder_name}")
            folder_id = self._create_folder(folder_name, main_folder_id)
            
            # Upload report with retry
            file_id = self._upload_file_with_retry(report_path, folder_id)
            
            if file_id:
                logger.info(f"Successfully uploaded {report_path.name} to {folder_name}")
                return True
            else:
                logger.error(f"Failed to upload {report_path.name}")
                return False
        
        except Exception as e:
            logger.error(f"Error uploading statement report: {e}")
            return False
    
    def upload_other_financial_records(self, report_path: Path) -> bool:
        """
        Upload Other_Financial_records.xlsx to separate Drive folder.
        
        Args:
            report_path: Path to Other_Financial_records.xlsx
            
        Returns:
            True if upload successful, False otherwise
            
        Validates Requirements: 9.6
        """
        try:
            # Get main drive folder ID
            main_folder_id = self.settings.drive_folder_ids.drive_folder_id
            
            # Create or get Other_Financial_Records folder
            folder_name = 'Other_Financial_Records'
            logger.info(f"Ensuring folder exists: {folder_name}")
            folder_id = self._create_folder(folder_name, main_folder_id)
            
            # Upload report with retry
            file_id = self._upload_file_with_retry(report_path, folder_id)
            
            if file_id:
                logger.info(f"Successfully uploaded {report_path.name} to {folder_name}")
                return True
            else:
                logger.error(f"Failed to upload {report_path.name}")
                return False
        
        except Exception as e:
            logger.error(f"Error uploading other financial records: {e}")
            return False
    
    def upload_attachments(
        self,
        attachment_paths: List[Path],
        statement_type: str
    ) -> Dict[str, bool]:
        """
        Upload multiple attachments to statement-specific attachments folder.
        
        Args:
            attachment_paths: List of attachment file paths
            statement_type: Type of statement (meriwest, amex, chase)
            
        Returns:
            Dictionary mapping file names to upload success status
        """
        results = {}
        
        try:
            # Get main drive folder ID
            main_folder_id = self.settings.drive_folder_ids.drive_folder_id
            
            # Create attachments folder structure
            attachments_folder = self._create_folder('Attachments', main_folder_id)
            statement_folder_name = f"{statement_type.capitalize()}_Attachments"
            statement_attachments_folder = self._create_folder(
                statement_folder_name,
                attachments_folder
            )
            
            # Upload each attachment
            for attachment_path in attachment_paths:
                if not attachment_path.exists():
                    logger.warning(f"Attachment not found: {attachment_path}")
                    results[attachment_path.name] = False
                    continue
                
                file_id = self._upload_file_with_retry(
                    attachment_path,
                    statement_attachments_folder
                )
                results[attachment_path.name] = file_id is not None
            
            success_count = sum(1 for success in results.values() if success)
            logger.info(
                f"Uploaded {success_count}/{len(attachment_paths)} attachments "
                f"for {statement_type}"
            )
        
        except Exception as e:
            logger.error(f"Error uploading attachments: {e}")
            for path in attachment_paths:
                if path.name not in results:
                    results[path.name] = False
        
        return results
    
    def get_folder_link(self, folder_id: str) -> str:
        """
        Get shareable link for a Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Shareable URL for the folder
        """
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def close(self):
        """Clean up resources."""
        logger.info("Drive sync session closed")


# Convenience function for single-use uploads
def upload_report(
    report_path: Path,
    statement_type: str,
    google_account_email: Optional[str] = None
) -> bool:
    """
    Convenience function to upload a single report.
    
    Args:
        report_path: Path to report file
        statement_type: Type of statement (meriwest, amex, chase, other)
        google_account_email: Email of Google account to use
        
    Returns:
        True if upload successful, False otherwise
    """
    try:
        drive_sync = DriveSync(google_account_email)
        
        if statement_type.lower() == 'other':
            success = drive_sync.upload_other_financial_records(report_path)
        else:
            success = drive_sync.upload_statement_report(report_path, statement_type)
        
        drive_sync.close()
        return success
    
    except Exception as e:
        logger.error(f"Error in upload_report: {e}")
        return False
