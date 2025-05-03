# Google Drive Backup Tool

A Python application that backs up files and folders from your local system to Google Drive. The application maintains a clean backup by removing existing files in the destination before uploading new content.

## Features

- Backup both files and folders to Google Drive
- Maintain folder structure in Google Drive
- Automatic folder creation in Google Drive
- Clean backup process (removes existing files before upload)
- Comprehensive logging
- Cross-platform support (Windows and Ubuntu)
- Configuration via YAML file
- Environment variables support
- Relative path handling for all files
- Recursive folder deletion and upload

## Prerequisites

- Python 3.7 or higher
- Google Cloud Platform account
- Google Drive API enabled
- OAuth 2.0 credentials

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Google Cloud Platform:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials
   - Download the credentials and save them as `credentials.json` in the project directory

3. Create a `.env` file with the following variables:
   ```
   GOOGLE_CREDENTIALS_FILE=credentials.json
   GOOGLE_TOKEN_FILE=token.json
   LOG_LEVEL=INFO
   ```
   Note: File paths in .env are relative to the script's location

4. Configure your backup paths in `config.yaml`:
   ```yaml
   backup_paths:
     - source: "/path/to/local/folder1"
       destination: "Backup/Folder1"
     - source: "/path/to/local/file1.txt"
       destination: "Backup/Documents"
   ```

## Usage

1. Activate the virtual environment (if using one):
   ```bash
   source venv/bin/activate  # On Unix/Linux
   venv\Scripts\activate     # On Windows
   ```

2. Run the backup tool:
   ```bash
   python google_drive_backup.py
   ```

The first time you run the application, it will:
1. Open a browser window for Google OAuth authentication
2. Save the authentication token for future use
3. Create necessary folders in Google Drive
4. Delete any existing files in the destination folders
5. Upload the new files and folders

## File Structure

The application uses relative paths for all files, making it portable across different systems:
- `google_drive_backup.py` - Main application file
- `config.yaml` - Backup configuration
- `credentials.json` - Google API credentials
- `token.json` - OAuth token (created after first run)
- `logs/app.log` - Application logs
- `.env` - Environment variables

## Logging

Logs are stored in the `logs/app.log` file by default. The application outputs logs to both:
- Console (for real-time monitoring)
- Log file (for historical record)

Log entries include:
- File/folder creation
- File/folder deletion
- Upload progress
- Error messages
- Authentication events

## Error Handling

The application includes comprehensive error handling and logging:
- File/folder not found errors
- Authentication errors
- API errors
- Configuration errors
- Deletion errors
- Upload errors

All errors are logged with detailed information to help with troubleshooting.

## Security

- OAuth 2.0 authentication
- Secure token storage
- No hardcoded credentials
- Environment variable support for sensitive data

## Best Practices

1. Always use relative paths in your configuration
2. Keep your credentials secure
3. Regularly check the logs for any issues
4. Back up your configuration files
5. Use version control for your configuration 