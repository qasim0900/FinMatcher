#!/usr/bin/env python3
"""
Create a dummy folder in Google Drive
Simple script to test Google Drive integration
"""

import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Authenticate and return Google Drive service."""
    creds = None
    token_path = 'finmatcher/auth_files/token.json'
    credentials_path = 'finmatcher/auth_files/credentials.json'
    
    # Check if token.json exists (saved credentials)
    if Path(token_path).exists():
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            print("✅ Loaded existing credentials")
        except:
            # Try loading as JSON
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print("✅ Loaded credentials from JSON")
    
    # If credentials are invalid or don't exist, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
            print("✅ Token refreshed")
        else:
            if not Path(credentials_path).exists():
                print(f"❌ Credentials file not found: {credentials_path}")
                print("\nPlease:")
                print("1. Go to Google Cloud Console")
                print("2. Enable Google Drive API")
                print("3. Create OAuth 2.0 credentials")
                print("4. Download and save as finmatcher/auth_files/credentials.json")
                return None
            
            print("🔐 Starting authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ Authentication successful")
        
        # Save credentials for future use
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
        print(f"💾 Credentials saved to {token_path}")
    
    # Build and return Drive service
    service = build('drive', 'v3', credentials=creds)
    return service

def create_folder(service, folder_name, parent_folder_id=None):
    """Create a folder in Google Drive."""
    
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    # If parent folder specified, add it
    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]
    
    try:
        folder = service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        return folder
    
    except Exception as e:
        print(f"❌ Error creating folder: {e}")
        return None

def list_folders(service, max_results=10):
    """List existing folders in Google Drive."""
    try:
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            pageSize=max_results,
            fields="files(id, name, webViewLink)"
        ).execute()
        
        folders = results.get('files', [])
        return folders
    
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
        return []

def main():
    """Main function."""
    print("=" * 70)
    print("🗂️  Google Drive Folder Creator")
    print("=" * 70)
    print()
    
    # Get Drive service
    print("🔐 Authenticating with Google Drive...")
    service = get_drive_service()
    
    if not service:
        print("\n❌ Failed to authenticate with Google Drive")
        return 1
    
    print("✅ Successfully connected to Google Drive")
    print()
    
    # List existing folders
    print("📁 Existing folders in your Drive:")
    print("-" * 70)
    existing_folders = list_folders(service)
    
    if existing_folders:
        for idx, folder in enumerate(existing_folders, 1):
            print(f"{idx}. {folder['name']} (ID: {folder['id']})")
    else:
        print("No folders found")
    
    print()
    
    # Ask for folder name
    print("=" * 70)
    folder_name = input("Enter folder name to create (or press Enter for 'FinMatcher_Test'): ").strip()
    
    if not folder_name:
        folder_name = "FinMatcher_Test"
    
    print()
    
    # Ask if user wants to create inside existing folder
    parent_id = None
    if existing_folders:
        create_inside = input("Create inside an existing folder? (y/N): ").strip().lower()
        
        if create_inside == 'y':
            print("\nSelect parent folder:")
            for idx, folder in enumerate(existing_folders, 1):
                print(f"{idx}. {folder['name']}")
            
            try:
                choice = int(input("\nEnter number: ").strip())
                if 1 <= choice <= len(existing_folders):
                    parent_id = existing_folders[choice - 1]['id']
                    print(f"✅ Will create inside: {existing_folders[choice - 1]['name']}")
            except:
                print("Invalid choice, creating in root")
    
    print()
    
    # Create folder
    print(f"📁 Creating folder: '{folder_name}'...")
    folder = create_folder(service, folder_name, parent_id)
    
    if folder:
        print()
        print("=" * 70)
        print("✅ Folder created successfully!")
        print("=" * 70)
        print(f"📁 Name: {folder['name']}")
        print(f"🆔 ID: {folder['id']}")
        print(f"🔗 Link: {folder['webViewLink']}")
        print()
        print("💡 You can use this folder ID in your .env file:")
        print(f"   DRIVE_FOLDER_ID={folder['id']}")
        print("=" * 70)
        return 0
    else:
        print("\n❌ Failed to create folder")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
