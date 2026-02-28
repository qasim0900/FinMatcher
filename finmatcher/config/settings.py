"""
Configuration management using Pydantic BaseSettings.

This module defines the configuration schema for the FinMatcher system,
loading settings from environment variables with validation.

Validates Requirements: 10.1, 10.2, 10.3
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ValidationError
from dotenv import load_dotenv


# Load .env file at module import
load_dotenv()


class EmailAccount(BaseModel):
    """Configuration for a single email account."""
    email: str
    password: str
    folders: List[str] = Field(default_factory=lambda: ["INBOX", "Spam", "[Gmail]/All Mail"])


class GoogleAccount(BaseModel):
    """Configuration for a single Google account."""
    email: str
    creds_file: str
    token_file: str


class IMAPSettings(BaseModel):
    """IMAP server configuration."""
    server: str = Field(default="imap.gmail.com")
    port: int = Field(default=993)
    use_ssl: bool = Field(default=True)


class GmailAPICredentials(BaseModel):
    """Gmail API OAuth2 credentials configuration."""
    credentials_path: str = Field(default="credentials.json")
    token_path: str = Field(default="token.json")
    scopes: List[str] = Field(default_factory=lambda: [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/gmail.readonly'
    ])


class DriveFolderIDs(BaseModel):
    """Google Drive folder IDs for different statement types."""
    meriwest_folder_id: Optional[str] = None
    amex_folder_id: Optional[str] = None
    chase_folder_id: Optional[str] = None
    attachments_folder_id: Optional[str] = None
    other_emails_folder_id: Optional[str] = None
    # Main drive folder (required)
    drive_folder_id: str


class OCRSettings(BaseModel):
    """OCR engine configuration."""
    tesseract_path: Optional[str] = None
    confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    language: str = Field(default="eng")


class MatchingThresholds(BaseModel):
    """Matching algorithm thresholds and tolerances."""
    amount_tolerance: float = Field(default=1.00, ge=0.0)  # ±$1.00
    date_variance_days: int = Field(default=3, ge=0, le=7)  # 0-3 days
    semantic_threshold: float = Field(default=0.85, ge=0.0, le=1.0)  # Match score threshold
    amount_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    date_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    @model_validator(mode='after')
    def validate_weights_sum(self):
        """Ensure weights sum to 1.0."""
        total = self.amount_weight + self.date_weight + self.semantic_weight
        if abs(total - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return self


class Settings(BaseModel):
    """
    Main configuration class for FinMatcher system.
    
    Loads configuration from .env file using Pydantic BaseSettings.
    Validates all required fields and raises descriptive errors on missing values.
    
    Validates Requirements:
    - 10.1: Load configuration from .env file
    - 10.2: Parse EMAIL_ACCOUNTS with multiple account credentials
    - 10.3: Raise descriptive errors on missing required values
    """
    
    # Email configuration - these will be populated by validators
    email_accounts: List[EmailAccount] = Field(default_factory=list)
    email_folders: List[str] = Field(default_factory=lambda: ["INBOX", "Spam", "[Gmail]/All Mail"])
    
    # IMAP settings
    imap_settings: IMAPSettings = Field(default_factory=IMAPSettings)
    
    # Gmail API credentials
    gmail_api_credentials: GmailAPICredentials = Field(default_factory=GmailAPICredentials)
    
    # Google accounts for Drive/Gmail API
    google_accounts: List[GoogleAccount] = Field(default_factory=list)
    
    # Drive folder IDs - will be populated by validator
    drive_folder_ids: Optional[DriveFolderIDs] = None
    
    # OCR settings
    ocr_settings: OCRSettings = Field(default_factory=OCRSettings)
    
    # Matching thresholds
    matching_thresholds: MatchingThresholds = Field(default_factory=MatchingThresholds)
    
    # File paths
    statements_dir: Path = Field(default=Path("statements"))
    temp_attachments_dir: Path = Field(default=Path("temp_attachments"))
    output_dir: Path = Field(default=Path("output"))
    
    # Processing settings
    thread_pool_size: int = Field(default=20, ge=1, le=100)
    process_pool_size: int = Field(default=10, ge=1, le=50)
    email_batch_size: int = Field(default=500, ge=1)
    
    # Rate limiting
    gmail_api_rate_limit_delay: float = Field(default=0.1, ge=0.0)  # seconds between API calls
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "validate_default": True,
    }
    
    def model_post_init(self, __context):
        """Post-initialization to parse complex fields from environment variables."""
        # Parse email accounts
        self.email_accounts = self._parse_email_accounts()
        
        # Parse Google accounts
        self.google_accounts = self._parse_google_accounts()
        
        # Parse drive folder IDs
        self.drive_folder_ids = self._parse_drive_folder_ids()
        
        # Parse email folders
        self.email_folders = self._parse_email_folders()
        
        # Parse matching thresholds
        self.matching_thresholds = self._parse_matching_thresholds()
        
        # Parse OCR settings
        self.ocr_settings = self._parse_ocr_settings()
        
        # Ensure directories exist
        self._ensure_directories_exist()
    
    def _parse_email_accounts(self) -> List[EmailAccount]:
        """
        Parse EMAIL_ACCOUNTS from environment variable.
        
        Format: email1@gmail.com,password1,folder1|folder2;email2@gmail.com,password2,folders
        Fallback: Single account from EMAIL_ADDRESS and EMAIL_PASSWORD
        """
        accounts = []
        email_accounts_str = os.getenv("EMAIL_ACCOUNTS", "")
        email_folders_default = self.email_folders
        
        if email_accounts_str:
            # Parse multiple accounts format
            for account_str in email_accounts_str.split(";"):
                parts = [p.strip() for p in account_str.strip().split(",")]
                if len(parts) >= 2:
                    folders = parts[2].split("|") if len(parts) > 2 else email_folders_default
                    accounts.append(EmailAccount(
                        email=parts[0],
                        password=parts[1],
                        folders=folders
                    ))
        else:
            # Fallback to single account
            email_address = os.getenv("EMAIL_ADDRESS")
            email_password = os.getenv("EMAIL_PASSWORD")
            if email_address and email_password:
                accounts.append(EmailAccount(
                    email=email_address,
                    password=email_password,
                    folders=email_folders_default
                ))
        
        if not accounts:
            raise ValueError(
                "No email accounts configured. Please set EMAIL_ACCOUNTS or both EMAIL_ADDRESS and EMAIL_PASSWORD "
                "in your .env file.\n"
                "Format: EMAIL_ACCOUNTS=email1@gmail.com,password1,folder1|folder2;email2@gmail.com,password2,folders"
            )
        
        return accounts
    
    def _parse_google_accounts(self) -> List[GoogleAccount]:
        """
        Parse GOOGLE_ACCOUNTS from environment variable.
        
        Format: email1@gmail.com,credentials1.json,token1.json;email2@gmail.com,creds2.json,token2.json
        Fallback: Single account from GOOGLE_EMAIL, CREDS_FILE, TOKEN_PICKLE
        """
        accounts = []
        google_accounts_str = os.getenv("GOOGLE_ACCOUNTS", "")
        
        if google_accounts_str:
            # Parse multiple accounts format
            for account_str in google_accounts_str.split(";"):
                parts = [p.strip() for p in account_str.strip().split(",")]
                if len(parts) >= 2:
                    token_file = parts[2] if len(parts) > 2 else f"token_{parts[0].split('@')[0]}.json"
                    accounts.append(GoogleAccount(
                        email=parts[0],
                        creds_file=parts[1],
                        token_file=token_file
                    ))
        else:
            # Fallback to single account
            google_email = os.getenv("GOOGLE_EMAIL", "default")
            creds_file = os.getenv("CREDS_FILE", "credentials.json")
            token_file = os.getenv("TOKEN_PICKLE", "token.json")
            accounts.append(GoogleAccount(
                email=google_email,
                creds_file=creds_file,
                token_file=token_file
            ))
        
        return accounts
    
    def _parse_drive_folder_ids(self) -> DriveFolderIDs:
        """Parse Drive folder IDs from environment variables."""
        drive_folder_id = os.getenv("DRIVE_FOLDER_ID")
        if not drive_folder_id:
            raise ValueError(
                "DRIVE_FOLDER_ID is required. Please set it in your .env file.\n"
                "This is the main Google Drive folder where reports will be uploaded."
            )
        
        return DriveFolderIDs(
            drive_folder_id=drive_folder_id,
            meriwest_folder_id=os.getenv("MERIWEST_FOLDER_ID"),
            amex_folder_id=os.getenv("AMEX_FOLDER_ID"),
            chase_folder_id=os.getenv("CHASE_FOLDER_ID"),
            attachments_folder_id=os.getenv("ATTACH_FILES_ID"),
            other_emails_folder_id=os.getenv("OTHER_EMAIL_FOLDER_ID")
        )
    
    def _parse_email_folders(self) -> List[str]:
        """Parse EMAIL_FOLDERS from comma-separated string."""
        folders_str = os.getenv("EMAIL_FOLDERS", "INBOX,Spam,[Gmail]/All Mail")
        return [f.strip() for f in folders_str.split(",")]
    
    def _parse_matching_thresholds(self) -> MatchingThresholds:
        """Parse matching thresholds from environment variables."""
        return MatchingThresholds(
            amount_tolerance=float(os.getenv("AMOUNT_TOLERANCE", "1.00")),
            date_variance_days=int(os.getenv("DATE_VARIANCE_DAYS", "3")),
            semantic_threshold=float(os.getenv("MATCH_THRESHOLD", "0.85")),
            amount_weight=float(os.getenv("AMOUNT_WEIGHT", "0.4")),
            date_weight=float(os.getenv("DATE_WEIGHT", "0.3")),
            semantic_weight=float(os.getenv("SEMANTIC_WEIGHT", "0.3"))
        )
    
    def _parse_ocr_settings(self) -> OCRSettings:
        """Parse OCR settings from environment variables."""
        return OCRSettings(
            tesseract_path=os.getenv("TESSERACT_PATH"),
            confidence_threshold=float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.80")),
            language=os.getenv("OCR_LANGUAGE", "eng")
        )
    
    def _ensure_directories_exist(self):
        """Ensure all required directories exist."""
        for dir_path in [self.statements_dir, self.temp_attachments_dir, self.output_dir]:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Failed to create directory '{dir_path}': {e}")


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the singleton Settings instance.
    
    Loads configuration from .env file on first call.
    Subsequent calls return the cached instance.
    
    Returns:
        Settings: The application settings instance
        
    Raises:
        SystemExit: If configuration is invalid or missing required values
    """
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
        except ValidationError as e:
            # Format validation errors for better readability
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                msg = error['msg']
                error_messages.append(f"  - {field}: {msg}")
            
            error_text = "\n".join(error_messages)
            print(f"\n❌ Configuration Error: Missing or invalid required values\n\n{error_text}\n", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"\n❌ Configuration Error: {e}\n", file=sys.stderr)
            sys.exit(1)
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from .env file.
    
    Useful for testing or when .env file changes.
    
    Returns:
        Settings: The newly loaded settings instance
    """
    global _settings
    # Reload .env file
    load_dotenv(override=True)
    try:
        _settings = Settings()
    except ValidationError as e:
        # Format validation errors for better readability
        error_messages = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            msg = error['msg']
            error_messages.append(f"  - {field}: {msg}")
        
        error_text = "\n".join(error_messages)
        print(f"\n❌ Configuration Error: Missing or invalid required values\n\n{error_text}\n", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n", file=sys.stderr)
        sys.exit(1)
    return _settings
