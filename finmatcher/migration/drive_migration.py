"""
Google Drive folder migration script from FinMatcher v1.0 to v2.0.

This script migrates the existing v1.0 Drive folder structure to the v2.0 structure by:
1. Creating the new 8-folder hierarchy
2. Migrating existing files from v1.0 structure to v2.0 structure
3. Mapping old folder names to new folder names
4. Preserving all existing files

V1.0 Folder Structure (assumed):
- FinMatcher_Reports/
  ├── Matched_Records/
  ├── Unmatched_Receipts/
  └── Attachments/

V2.0 Folder Structure:
- FinMatcher_Excel_Reports/
  ├── {Statement_File_Name}_record.xlsx/
  ├── Other_receipts_email.xlsx/
  ├── unmatch_email_records.xlsx/
  ├── Attach_files/
  ├── Attach_Image/
  ├── Unmatch_Email_Attach_files/
  └── unmatch_attach_image/

Usage:
    python -m finmatcher.migration.drive_migration --credentials auth_files/credentials.json
"""

import os
import logging
import argparse
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class DriveMigration:
    """
    Handles Google Drive folder migration from v1.0 to v2.0.
    
    Migration steps:
    1. Authenticate with Google Drive API
    2. Find existing v1.0 root folder
    3. Create new v2.0 folder hierarchy
    4. Map old folders to new folders
    5. Copy/move files from old structure to new structure
    6. Verify all files were migrated
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    # Folder name mappings from v1.0 to v2.0
    FOLDER_MAPPINGS = {
        'Matched_Records': 'Other_receipts_email.xlsx',  # Matched receipts
        'Unmatched_Receipts': 'unmatch_email_records.xlsx',  # Unmatched emails
        'Attachments': 'Attach_files',  # Default to document attachments
    }
    
    def __init__(self, credentials_path: str, 
                 old_root_name: str = "FinMatcher_Reports",
                 new_root_name: str = "FinMatcher_Excel_Reports"):
        """
        Initialize Drive migration.
        
        Args:
            credentials_path: Path to credentials.json file
            old_root_name: Name of v1.0 root folder
            new_root_name: Name of v2.0 root folder
        """
        self.credentials_path = credentials_path
        self.old_root_name = old_root_name
        self.new_root_name = new_root_name
        self.service = None
        self.old_root_id = None
        self.new_root_id = None
        self.new_folder_ids: Dict[str, str] = {}
        
        logger.info(f"Initialized Drive migration: {old_root_name} -> {new_root_name}")
    
    def authenticate(self):
        """
        Authenticate with Google Drive API using OAuth 2.0.
        """
        creds = None
        token_path = self.credentials_path.replace('credentials.json', 'token.json')
        
        # Load existing token
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        
        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive authentication successful")
    
    def find_folder(self, name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find folder by name.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID if found, None otherwise
        """
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
            
        except HttpError as e:
            logger.error(f"Error finding folder {name}: {e}")
            return None
    
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a new folder.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID
        """
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        try:
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder['id']
            logger.info(f"Created folder: {name} (ID: {folder_id})")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating folder {name}: {e}")
            raise
    
    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Get existing folder or create if not exists.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID
        """
        folder_id = self.find_folder(name, parent_id)
        if folder_id:
            logger.debug(f"Found existing folder: {name} (ID: {folder_id})")
            return folder_id
        else:
            return self.create_folder(name, parent_id)
    
    def create_v2_folder_structure(self) -> Dict[str, str]:
        """
        Create the new v2.0 8-folder hierarchy.
        
        Returns:
            Dictionary mapping folder names to folder IDs
        """
        logger.info("Creating v2.0 folder structure")
        
        # Create root folder
        self.new_root_id = self.get_or_create_folder(self.new_root_name)
        
        # Create standard subfolders
        folder_names = [
            'Other_receipts_email.xlsx',
            'unmatch_email_records.xlsx',
            'Attach_files',
            'Attach_Image',
            'Unmatch_Email_Attach_files',
            'unmatch_attach_image'
        ]
        
        self.new_folder_ids = {'root': self.new_root_id}
        
        for folder_name in folder_names:
            folder_id = self.get_or_create_folder(folder_name, self.new_root_id)
            self.new_folder_ids[folder_name] = folder_id
        
        logger.info(f"Created {len(folder_names)} subfolders in v2.0 structure")
        return self.new_folder_ids
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """
        List all files in a folder.
        
        Args:
            folder_id: Folder ID
            
        Returns:
            List of file metadata dictionaries
        """
        query = f"'{folder_id}' in parents and trashed=false"
        
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)',
                pageSize=1000
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            logger.error(f"Error listing files in folder {folder_id}: {e}")
            return []
    
    def copy_file(self, file_id: str, new_parent_id: str, new_name: Optional[str] = None) -> str:
        """
        Copy a file to a new location.
        
        Args:
            file_id: Source file ID
            new_parent_id: Destination folder ID
            new_name: New file name (optional)
            
        Returns:
            New file ID
        """
        try:
            # Get original file metadata
            original_file = self.service.files().get(
                fileId=file_id,
                fields='name, mimeType'
            ).execute()
            
            # Prepare copy metadata
            copy_metadata = {
                'parents': [new_parent_id],
                'name': new_name if new_name else original_file['name']
            }
            
            # Copy file
            copied_file = self.service.files().copy(
                fileId=file_id,
                body=copy_metadata,
                fields='id, name'
            ).execute()
            
            logger.debug(f"Copied file: {copied_file['name']} (ID: {copied_file['id']})")
            return copied_file['id']
            
        except HttpError as e:
            logger.error(f"Error copying file {file_id}: {e}")
            raise
    
    def classify_file_by_extension(self, filename: str) -> str:
        """
        Classify file by extension to determine target folder.
        
        Args:
            filename: File name
            
        Returns:
            Target folder name
        """
        extension = os.path.splitext(filename)[1].lower()
        
        # Document extensions -> Attach_files
        if extension in {'.pdf', '.doc', '.docx'}:
            return 'Attach_files'
        # Image extensions -> Attach_Image
        elif extension in {'.jpg', '.jpeg', '.png', '.gif'}:
            return 'Attach_Image'
        # Excel files -> Other_receipts_email.xlsx
        elif extension in {'.xlsx', '.xls'}:
            return 'Other_receipts_email.xlsx'
        else:
            # Default to Attach_files
            return 'Attach_files'
    
    def migrate_folder_contents(self, old_folder_name: str, old_folder_id: str):
        """
        Migrate contents from an old v1.0 folder to the new v2.0 structure.
        
        Args:
            old_folder_name: Name of old folder
            old_folder_id: ID of old folder
        """
        logger.info(f"Migrating contents from: {old_folder_name}")
        
        # Get all files in old folder
        files = self.list_files_in_folder(old_folder_id)
        logger.info(f"Found {len(files)} files to migrate")
        
        migrated_count = 0
        
        for file in files:
            file_id = file['id']
            file_name = file['name']
            mime_type = file['mimeType']
            
            # Skip folders
            if mime_type == 'application/vnd.google-apps.folder':
                logger.debug(f"Skipping subfolder: {file_name}")
                continue
            
            # Determine target folder based on file type
            if old_folder_name == 'Attachments':
                # Classify attachments by extension
                target_folder_name = self.classify_file_by_extension(file_name)
            else:
                # Use folder mapping
                target_folder_name = self.FOLDER_MAPPINGS.get(
                    old_folder_name,
                    'Other_receipts_email.xlsx'
                )
            
            target_folder_id = self.new_folder_ids.get(target_folder_name)
            
            if not target_folder_id:
                logger.warning(f"No target folder for {file_name}, skipping")
                continue
            
            # Copy file to new location
            try:
                self.copy_file(file_id, target_folder_id)
                migrated_count += 1
                logger.debug(f"Migrated: {file_name} -> {target_folder_name}")
            except Exception as e:
                logger.error(f"Failed to migrate {file_name}: {e}")
        
        logger.info(f"Migrated {migrated_count}/{len(files)} files from {old_folder_name}")
    
    def migrate(self) -> bool:
        """
        Execute the complete migration process.
        
        Returns:
            True if migration succeeded, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting Drive folder migration from v1.0 to v2.0")
            logger.info("=" * 60)
            
            # Step 1: Authenticate
            self.authenticate()
            
            # Step 2: Find old root folder
            logger.info(f"Looking for v1.0 root folder: {self.old_root_name}")
            self.old_root_id = self.find_folder(self.old_root_name)
            
            if not self.old_root_id:
                logger.warning(f"v1.0 root folder '{self.old_root_name}' not found")
                logger.info("Creating fresh v2.0 structure without migration")
                self.create_v2_folder_structure()
                logger.info("Fresh v2.0 structure created successfully")
                return True
            
            logger.info(f"Found v1.0 root folder (ID: {self.old_root_id})")
            
            # Step 3: Create new v2.0 folder structure
            self.create_v2_folder_structure()
            
            # Step 4: Find and migrate old folders
            old_folders = self.list_files_in_folder(self.old_root_id)
            
            for folder in old_folders:
                if folder['mimeType'] == 'application/vnd.google-apps.folder':
                    folder_name = folder['name']
                    folder_id = folder['id']
                    
                    if folder_name in self.FOLDER_MAPPINGS:
                        self.migrate_folder_contents(folder_name, folder_id)
                    else:
                        logger.debug(f"Skipping unknown folder: {folder_name}")
            
            # Step 5: Verify migration
            total_files = 0
            for folder_name, folder_id in self.new_folder_ids.items():
                if folder_name != 'root':
                    files = self.list_files_in_folder(folder_id)
                    file_count = len([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'])
                    total_files += file_count
                    logger.info(f"  {folder_name}: {file_count} files")
            
            logger.info("=" * 60)
            logger.info("Migration completed successfully!")
            logger.info(f"Total files in v2.0 structure: {total_files}")
            logger.info(f"New root folder: {self.new_root_name} (ID: {self.new_root_id})")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point for Drive folder migration."""
    parser = argparse.ArgumentParser(
        description="Migrate FinMatcher Drive folders from v1.0 to v2.0"
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default="auth_files/credentials.json",
        help="Path to credentials.json file (default: auth_files/credentials.json)"
    )
    parser.add_argument(
        "--old-root",
        type=str,
        default="FinMatcher_Reports",
        help="Name of v1.0 root folder (default: FinMatcher_Reports)"
    )
    parser.add_argument(
        "--new-root",
        type=str,
        default="FinMatcher_Excel_Reports",
        help="Name of v2.0 root folder (default: FinMatcher_Excel_Reports)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    migration = DriveMigration(
        credentials_path=args.credentials,
        old_root_name=args.old_root,
        new_root_name=args.new_root
    )
    success = migration.migrate()
    
    if success:
        print("\n✓ Migration completed successfully!")
        print(f"✓ New root folder: {args.new_root}")
        return 0
    else:
        print("\n✗ Migration failed!")
        return 1


if __name__ == "__main__":
    exit(main())
