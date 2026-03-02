#!/usr/bin/env python3
"""
Quick Google Drive Folder Creator
Creates a folder with one command
"""

import sys
import argparse
from finmatcher.reports.drive_sync import DriveSync
from finmatcher.utils.logger import get_logger

def create_folder(folder_name, parent_id=None):
    """Create a folder in Google Drive using existing DriveSync."""
    
    logger = get_logger()
    
    print("\n" + "=" * 70)
    print(f"📁 Creating Google Drive Folder: '{folder_name}'")
    print("=" * 70)
    
    try:
        # Initialize DriveSync
        print("\n🔐 Connecting to Google Drive...")
        drive_sync = DriveSync()
        
        print("✅ Connected successfully")
        
        # Create folder
        print(f"\n📁 Creating folder...")
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = drive_sync.service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        print("\n" + "=" * 70)
        print("✅ FOLDER CREATED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\n📁 Folder Name: {folder['name']}")
        print(f"🆔 Folder ID: {folder['id']}")
        print(f"🔗 Web Link: {folder['webViewLink']}")
        
        print("\n💡 Add this to your .env file:")
        print(f"   DRIVE_FOLDER_ID={folder['id']}")
        
        print("\n" + "=" * 70)
        
        return folder['id']
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def list_folders():
    """List existing folders in Google Drive."""
    
    print("\n" + "=" * 70)
    print("📁 Listing Google Drive Folders")
    print("=" * 70)
    
    try:
        drive_sync = DriveSync()
        
        results = drive_sync.service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            pageSize=20,
            fields="files(id, name, webViewLink, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        folders = results.get('files', [])
        
        if not folders:
            print("\n⚠️  No folders found")
            return
        
        print(f"\n📂 Found {len(folders)} folders:\n")
        
        for idx, folder in enumerate(folders, 1):
            print(f"{idx}. {folder['name']}")
            print(f"   ID: {folder['id']}")
            print(f"   Link: {folder['webViewLink']}")
            print()
        
        print("=" * 70)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

def main():
    """Main function."""
    
    parser = argparse.ArgumentParser(
        description="Quick Google Drive Folder Creator"
    )
    
    parser.add_argument(
        'folder_name',
        nargs='?',
        default='FinMatcher_Reports',
        help='Name of folder to create (default: FinMatcher_Reports)'
    )
    
    parser.add_argument(
        '--parent',
        '-p',
        help='Parent folder ID (optional)'
    )
    
    parser.add_argument(
        '--list',
        '-l',
        action='store_true',
        help='List existing folders'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_folders()
        return 0
    
    folder_id = create_folder(args.folder_name, args.parent)
    
    if folder_id:
        return 0
    else:
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(130)
