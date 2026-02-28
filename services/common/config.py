"""
Configuration Management
Loads and validates environment variables
"""

import os
from typing import Optional, List
from dotenv import load_dotenv
from dataclasses import dataclass

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    ssl_mode: str = "prefer"
    
    @classmethod
    def from_env(cls):
        """Load database config from environment"""
        url = os.getenv('DATABASE_URL')
        if not url:
            raise ValueError("DATABASE_URL not found in environment")
        
        # Remove quotes if present
        url = url.strip('"')
        
        return cls(
            url=url,
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            ssl_mode=os.getenv('DB_SSL_MODE', 'prefer')
        )


@dataclass
class IMAPConfig:
    """IMAP configuration"""
    host: str
    port: int
    accounts: List[dict]
    
    @classmethod
    def from_env(cls):
        """Load IMAP config from environment"""
        host = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        port = int(os.getenv('IMAP_PORT', '993'))
        
        # Parse accounts from EMAIL_ACCOUNTS
        accounts_str = os.getenv('EMAIL_ACCOUNTS', '')
        accounts = []
        
        for account_data in accounts_str.split(';'):
            if not account_data.strip():
                continue
            
            parts = account_data.split(',')
            if len(parts) >= 3:
                accounts.append({
                    'email': parts[0].strip(),
                    'password': parts[1].strip(),
                    'folders': [f.strip() for f in parts[2].split('|')]
                })
        
        return cls(
            host=host,
            port=port,
            accounts=accounts
        )


@dataclass
class ServiceConfig:
    """Service-level configuration"""
    service_name: str
    worker_id: str
    max_threads: int = 8
    batch_size: int = 100
    poll_interval: int = 5
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls, service_name: str):
        """Load service config from environment"""
        import socket
        
        worker_id = os.getenv('WORKER_ID', f"{service_name}-{socket.gethostname()}")
        
        return cls(
            service_name=service_name,
            worker_id=worker_id,
            max_threads=int(os.getenv('MAX_THREADS', '8')),
            batch_size=int(os.getenv('BATCH_SIZE', '100')),
            poll_interval=int(os.getenv('POLL_INTERVAL', '5')),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )


@dataclass
class StorageConfig:
    """Storage configuration"""
    attachments_dir: str
    reports_dir: str
    cache_dir: str
    
    @classmethod
    def from_env(cls):
        """Load storage config from environment"""
        return cls(
            attachments_dir=os.getenv('ATTACHMENTS_DIR', 'attachments'),
            reports_dir=os.getenv('REPORTS_DIR', 'reports'),
            cache_dir=os.getenv('CACHE_DIR', '.kiro/cache')
        )


@dataclass
class UploadConfig:
    """Upload service configuration"""
    endpoint: Optional[str]
    api_key: Optional[str]
    upload_type: str = "local"  # local, s3, api, ftp
    
    @classmethod
    def from_env(cls):
        """Load upload config from environment"""
        return cls(
            endpoint=os.getenv('UPLOAD_ENDPOINT'),
            api_key=os.getenv('UPLOAD_API_KEY'),
            upload_type=os.getenv('UPLOAD_TYPE', 'local')
        )


class Config:
    """Main configuration class"""
    
    def __init__(self, service_name: str = "finmatcher"):
        self.database = DatabaseConfig.from_env()
        self.imap = IMAPConfig.from_env()
        self.service = ServiceConfig.from_env(service_name)
        self.storage = StorageConfig.from_env()
        self.upload = UploadConfig.from_env()
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(self.storage.attachments_dir, exist_ok=True)
        os.makedirs(self.storage.reports_dir, exist_ok=True)
        os.makedirs(self.storage.cache_dir, exist_ok=True)
    
    def validate(self):
        """Validate configuration"""
        errors = []
        
        # Validate database
        if not self.database.url:
            errors.append("DATABASE_URL is required")
        
        # Validate IMAP
        if not self.imap.accounts:
            errors.append("EMAIL_ACCOUNTS is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True


# Global config instance
_config: Optional[Config] = None


def get_config(service_name: str = "finmatcher") -> Config:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = Config(service_name)
        _config.validate()
    return _config


def reload_config(service_name: str = "finmatcher") -> Config:
    """Reload configuration"""
    global _config
    _config = Config(service_name)
    _config.validate()
    return _config
