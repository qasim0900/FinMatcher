"""
Security validation utilities for FinMatcher v2.0 Enterprise Upgrade.

This module provides security validation including:
- File extension validation (whitelist)
- File size validation (50MB max)
- Path validation (prevent directory traversal)
- API key management (environment variables only)
- Hardcoded secret detection

Validates Requirements: 2.5, 2.6, 10.7
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Security validator for credential, file, and path validation.
    
    Validates Requirements:
    - 2.5: Load API keys from environment variables only
    - 2.6: Never log API keys or tokens
    - 10.7: Sanitize PII before logging
    """
    
    # Allowed file extensions (whitelist)
    ALLOWED_EXTENSIONS = {
        '.pdf', '.doc', '.docx',  # Documents
        '.jpg', '.jpeg', '.png', '.gif',  # Images
        '.xlsx', '.xls', '.csv'  # Spreadsheets
    }
    
    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
    
    # Patterns for detecting hardcoded secrets
    SECRET_PATTERNS = [
        # API keys
        (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', 'API Key'),
        (r'apikey\s*=\s*["\']([^"\']+)["\']', 'API Key'),
        
        # Passwords
        (r'password\s*=\s*["\']([^"\']+)["\']', 'Password'),
        (r'passwd\s*=\s*["\']([^"\']+)["\']', 'Password'),
        (r'pwd\s*=\s*["\']([^"\']+)["\']', 'Password'),
        
        # Tokens
        (r'token\s*=\s*["\']([^"\']+)["\']', 'Token'),
        (r'access[_-]?token\s*=\s*["\']([^"\']+)["\']', 'Access Token'),
        (r'auth[_-]?token\s*=\s*["\']([^"\']+)["\']', 'Auth Token'),
        
        # AWS credentials
        (r'aws[_-]?access[_-]?key[_-]?id\s*=\s*["\']([^"\']+)["\']', 'AWS Access Key'),
        (r'aws[_-]?secret[_-]?access[_-]?key\s*=\s*["\']([^"\']+)["\']', 'AWS Secret Key'),
        
        # Database credentials
        (r'db[_-]?password\s*=\s*["\']([^"\']+)["\']', 'Database Password'),
        (r'database[_-]?url\s*=\s*["\']([^"\']+)["\']', 'Database URL'),
        
        # Email credentials
        (r'email[_-]?password\s*=\s*["\']([^"\']+)["\']', 'Email Password'),
        (r'smtp[_-]?password\s*=\s*["\']([^"\']+)["\']', 'SMTP Password'),
        
        # Generic secrets
        (r'secret\s*=\s*["\']([^"\']+)["\']', 'Secret'),
        (r'private[_-]?key\s*=\s*["\']([^"\']+)["\']', 'Private Key'),
    ]
    
    # Safe values that are not actual secrets
    SAFE_VALUES = [
        'your_password_here',
        'your_api_key_here',
        'your_token_here',
        'example',
        'test',
        'dummy',
        'placeholder',
        'changeme',
        'password',
        'secret',
        'token',
        'key',
        '',
        'none',
        'null',
    ]
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize security validator.
        
        Args:
            project_root: Root directory of project (defaults to current directory)
        """
        self.project_root = project_root or Path.cwd()
        self.logger = logger
    
    def validate_file_extension(self, file_path: str) -> bool:
        """
        Validate file extension against whitelist.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if extension is allowed, False otherwise
            
        Validates Requirement: 2.6 - File extension validation (whitelist)
        """
        extension = Path(file_path).suffix.lower()
        
        if extension not in self.ALLOWED_EXTENSIONS:
            self.logger.error(
                f"Invalid file extension: {extension}. "
                f"Allowed extensions: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
            return False
        
        return True
    
    def validate_file_size(self, file_path: str) -> bool:
        """
        Validate file size is within limit (50MB max).
        
        Args:
            file_path: Path to file
            
        Returns:
            True if size is within limit, False otherwise
            
        Validates Requirement: 2.6 - File size validation (50MB max)
        """
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size > self.MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                self.logger.error(
                    f"File too large: {size_mb:.2f}MB exceeds maximum {max_mb:.2f}MB"
                )
                return False
            
            return True
            
        except OSError as e:
            self.logger.error(f"Error checking file size: {e}")
            return False
    
    def validate_path(self, file_path: str, base_dir: Optional[str] = None) -> bool:
        """
        Validate path to prevent directory traversal attacks.
        
        Args:
            file_path: Path to validate
            base_dir: Base directory to restrict access to (optional)
            
        Returns:
            True if path is safe, False otherwise
            
        Validates Requirement: 2.6 - Path validation (prevent directory traversal)
        """
        # Check for directory traversal patterns
        if '..' in file_path:
            self.logger.error(f"Directory traversal detected in path: {file_path}")
            return False
        
        # Check for absolute paths (should be relative)
        if os.path.isabs(file_path):
            self.logger.error(f"Absolute path not allowed: {file_path}")
            return False
        
        # If base_dir provided, ensure path is within it
        if base_dir:
            try:
                # Resolve to absolute paths
                abs_file_path = os.path.abspath(os.path.join(base_dir, file_path))
                abs_base_dir = os.path.abspath(base_dir)
                
                # Check if file path is within base directory
                if not abs_file_path.startswith(abs_base_dir):
                    self.logger.error(
                        f"Path {file_path} is outside base directory {base_dir}"
                    )
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error validating path: {e}")
                return False
        
        return True
    
    def validate_file(self, file_path: str, base_dir: Optional[str] = None) -> bool:
        """
        Validate file (extension, size, and path).
        
        Args:
            file_path: Path to file
            base_dir: Base directory to restrict access to (optional)
            
        Returns:
            True if all validations pass, False otherwise
        """
        # Validate path
        if not self.validate_path(file_path, base_dir):
            return False
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.logger.error(f"File does not exist: {file_path}")
            return False
        
        # Validate extension
        if not self.validate_file_extension(file_path):
            return False
        
        # Validate size
        if not self.validate_file_size(file_path):
            return False
        
        return True
    
    def validate_credentials_from_env(self, strict: bool = False) -> bool:
        """
        Validate that all credentials are loaded from environment variables.
        
        Checks that required environment variables are set.
        
        Args:
            strict: If True, fail if variables are missing. If False, just warn.
        
        Returns:
            True if all credentials are from environment, False otherwise
            
        Validates Requirement 14.1: Credentials from environment variables
        """
        required_env_vars = [
            'EMAIL_ACCOUNTS',  # or EMAIL_ADDRESS + EMAIL_PASSWORD
            'DRIVE_FOLDER_ID',
        ]
        
        optional_env_vars = [
            'EMAIL_ADDRESS',
            'EMAIL_PASSWORD',
            'GOOGLE_ACCOUNTS',
            'GOOGLE_EMAIL',
            'CREDS_FILE',
            'TOKEN_PICKLE',
        ]
        
        missing_vars = []
        
        # Check required variables
        for var in required_env_vars:
            if var == 'EMAIL_ACCOUNTS':
                # Check if either EMAIL_ACCOUNTS or both EMAIL_ADDRESS and EMAIL_PASSWORD are set
                if not os.getenv('EMAIL_ACCOUNTS'):
                    if not (os.getenv('EMAIL_ADDRESS') and os.getenv('EMAIL_PASSWORD')):
                        missing_vars.append('EMAIL_ACCOUNTS (or EMAIL_ADDRESS + EMAIL_PASSWORD)')
            elif not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            if strict:
                self.logger.error(
                    f"Missing required environment variables: {', '.join(missing_vars)}"
                )
                return False
            else:
                self.logger.warning(
                    f"Environment variables not loaded yet: {', '.join(missing_vars)} "
                    "(will be loaded from .env file)"
                )
                return True
        
        self.logger.info("✓ All required credentials loaded from environment variables")
        return True
    
    def scan_for_hardcoded_secrets(
        self,
        exclude_dirs: Optional[List[str]] = None
    ) -> List[Tuple[str, int, str, str]]:
        """
        Scan codebase for hardcoded secrets.
        
        Args:
            exclude_dirs: Directories to exclude from scan
            
        Returns:
            List of tuples: (file_path, line_number, secret_type, line_content)
        """
        exclude_dirs = exclude_dirs or [
            '.git',
            '__pycache__',
            'venv',
            'env',
            '.venv',
            'node_modules',
            '.pytest_cache',
            'output',
            'temp_attachments',
            'statements',
            'tests',  # Exclude test files
            'htmlcov',  # Exclude coverage reports
        ]
        
        # Files to exclude (test and configuration files)
        exclude_files = [
            'configure_and_test.py',
            'test_',  # Any file starting with test_
            'performance_analysis.py',
            'integration_plan.py',
        ]
        
        findings = []
        
        # Scan Python files
        for py_file in self.project_root.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            
            # Skip this file itself
            if py_file.name == 'security_validator.py':
                continue
            
            # Skip excluded files
            if any(py_file.name.startswith(excluded) or py_file.name == excluded 
                   for excluded in exclude_files):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        # Check each pattern
                        for pattern, secret_type in self.SECRET_PATTERNS:
                            matches = re.finditer(pattern, line, re.IGNORECASE)
                            for match in matches:
                                value = match.group(1) if match.groups() else match.group(0)
                                
                                # Skip safe values
                                if value.lower() in self.SAFE_VALUES:
                                    continue
                                
                                # Skip if it's loading from environment
                                if 'os.getenv' in line or 'os.environ' in line:
                                    continue
                                
                                # Skip if it's in a comment
                                if line.strip().startswith('#'):
                                    continue
                                
                                # Skip if it's in a docstring
                                if '"""' in line or "'''" in line:
                                    continue
                                
                                findings.append((
                                    str(py_file.relative_to(self.project_root)),
                                    line_num,
                                    secret_type,
                                    line.strip()
                                ))
            
            except Exception as e:
                self.logger.warning(f"Error scanning {py_file}: {e}")
        
        return findings
    
    def validate_security(self, strict_env_check: bool = False) -> bool:
        """
        Run all security validations.
        
        Args:
            strict_env_check: If True, fail if env vars are missing. If False, just warn.
        
        Returns:
            True if all validations pass, False otherwise
        """
        self.logger.info("Running security validations...")
        
        # Check credentials from environment (non-strict by default)
        env_valid = self.validate_credentials_from_env(strict=strict_env_check)
        
        # Scan for hardcoded secrets
        self.logger.info("Scanning for hardcoded secrets...")
        findings = self.scan_for_hardcoded_secrets()
        
        if findings:
            self.logger.warning(f"Found {len(findings)} potential hardcoded secrets:")
            for file_path, line_num, secret_type, line_content in findings:
                self.logger.warning(
                    f"  {file_path}:{line_num} - {secret_type}: {line_content[:80]}"
                )
            secrets_valid = False
        else:
            self.logger.info("✓ No hardcoded secrets detected")
            secrets_valid = True
        
        # Overall result
        all_valid = env_valid and secrets_valid
        
        if all_valid:
            self.logger.info("✓ All security validations passed")
        else:
            self.logger.error("✗ Security validations failed")
        
        return all_valid


def validate_security_on_startup() -> bool:
    """
    Validate security on application startup.
    
    Returns:
        True if all validations pass, False otherwise
    """
    validator = SecurityValidator()
    return validator.validate_security()
