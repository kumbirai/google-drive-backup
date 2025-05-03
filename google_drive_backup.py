#!/usr/bin/env python3

import os
import sys
import logging
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Configure logging
def setup_logging():
    # Get the directory where the script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = Path(os.path.join(base_dir, "logs"))
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

class GoogleDriveBackup:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        self.logger = setup_logging()
        load_dotenv()
        
        # Get the directory where the script is located
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set up paths for credentials and token files
        self.credentials_file = os.path.join(
            self.base_dir,
            os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        )
        self.token_file = os.path.join(
            self.base_dir,
            os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
        )
        
        self.service = self._get_drive_service()
        
    def _get_drive_service(self):
        """Get or create Google Drive service."""
        creds = None
        
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as token:
                creds = Credentials.from_authorized_user_info(
                    json.loads(token.read()), self.SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
                
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        return build('drive', 'v3', credentials=creds)
    
    def _delete_folder_contents(self, folder_id: str):
        """Delete all contents of a folder in Google Drive."""
        try:
            # List all files in the folder
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name, mimeType)'
            ).execute()
            
            files = results.get('files', [])
            
            for file in files:
                try:
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        # Recursively delete contents of subfolders
                        self._delete_folder_contents(file['id'])
                    
                    # Delete the file/folder
                    self.service.files().delete(fileId=file['id']).execute()
                    self.logger.info(f"Deleted: {file['name']}")
                except Exception as e:
                    self.logger.error(f"Error deleting {file['name']}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error listing folder contents: {str(e)}")
    
    def _create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Create a folder in Google Drive and return its ID."""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
            
        folder = self.service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        self.logger.info(f"Created folder: {folder_name}")
        return folder.get('id')
    
    def _get_folder_id(self, folder_path: str) -> str:
        """Get folder ID from path, creating folders if they don't exist."""
        if not folder_path:
            return 'root'
            
        parts = folder_path.split('/')
        current_id = 'root'
        
        for part in parts:
            if not part:
                continue
                
            query = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and '{current_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                current_id = files[0]['id']
            else:
                current_id = self._create_folder(part, current_id)
                
        return current_id
    
    def upload_file(self, file_path: str, destination_folder: str):
        """Upload a file to Google Drive."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                return
                
            folder_id = self._get_folder_id(destination_folder)
            
            file_metadata = {
                'name': file_path.name,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                str(file_path),
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            self.logger.info(f"Uploaded file: {file_path.name}")
            
        except Exception as e:
            self.logger.error(f"Error uploading file {file_path}: {str(e)}")
    
    def upload_folder(self, folder_path: str, destination_folder: str):
        """Upload a folder and its contents to Google Drive."""
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                self.logger.error(f"Folder not found: {folder_path}")
                return
                
            # Create the destination folder
            dest_folder_id = self._get_folder_id(destination_folder)
            
            # Delete existing contents of the destination folder
            self.logger.info(f"Deleting existing contents of {destination_folder}")
            self._delete_folder_contents(dest_folder_id)
            
            # Upload all files in the folder
            for item in folder_path.rglob('*'):
                if item.is_file():
                    # Calculate relative path for destination
                    rel_path = item.relative_to(folder_path)
                    dest_path = str(Path(destination_folder) / rel_path.parent)
                    
                    self.upload_file(str(item), dest_path)
                    
        except Exception as e:
            self.logger.error(f"Error uploading folder {folder_path}: {str(e)}")
    
    def process_backup_config(self, config_file: str):
        """Process the backup configuration file."""
        try:
            config_path = os.path.join(self.base_dir, config_file)
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            for backup_item in config['backup_paths']:
                source = backup_item['source']
                destination = backup_item['destination']
                
                source_path = Path(source)
                if not source_path.exists():
                    self.logger.error(f"Source path does not exist: {source}")
                    continue
                    
                if source_path.is_file():
                    # For single files, delete any existing file with the same name
                    folder_id = self._get_folder_id(destination)
                    query = f"name='{source_path.name}' and '{folder_id}' in parents and trashed=false"
                    results = self.service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id)'
                    ).execute()
                    
                    for file in results.get('files', []):
                        self.service.files().delete(fileId=file['id']).execute()
                        self.logger.info(f"Deleted existing file: {source_path.name}")
                    
                    self.upload_file(source, destination)
                elif source_path.is_dir():
                    self.upload_folder(source, destination)
                    
        except Exception as e:
            self.logger.error(f"Error processing backup config: {str(e)}")

def main():
    backup = GoogleDriveBackup()
    backup.process_backup_config('config.yaml')

if __name__ == '__main__':
    main() 