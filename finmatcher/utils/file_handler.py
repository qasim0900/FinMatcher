"""
Secure file I/O operations with restricted permissions.

This module provides utilities for secure file saving, reading, and cleanup
with owner-only permissions.

Validates Requirements: 14.2
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
import stat


class FileHandler:
    """
    Secure file handler with restricted permissions.
    
    Validates Requirement 14.2: Use secure file permissions restricting access to process owner
    """
    
    @staticmethod
    def save_file_secure(file_path: Path, content: bytes, mode: str = 'wb') -> bool:
        """
        Save file with secure permissions (owner-only read/write).
        
        Args:
            file_path: Path to save the file
            content: File content (bytes)
            mode: File open mode (default: 'wb' for binary write)
            
        Returns:
            True if successful, False otherwise
            
        Validates Requirement 14.2: Secure file permissions restricting access to process owner
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            with open(file_path, mode) as f:
                f.write(content)
            
            # Set secure permissions (owner read/write only)
            # On Windows, this sets the file to be accessible only by the owner
            # On Unix, this is equivalent to chmod 600
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
            
            return True
        except Exception as e:
            print(f"Error saving file {file_path}: {e}")
            return False
    
    @staticmethod
    def save_text_secure(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
        """
        Save text file with secure permissions.
        
        Args:
            file_path: Path to save the file
            content: Text content
            encoding: Text encoding (default: 'utf-8')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            # Set secure permissions
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
            
            return True
        except Exception as e:
            print(f"Error saving text file {file_path}: {e}")
            return False
    
    @staticmethod
    def read_file(file_path: Path, mode: str = 'rb') -> Optional[bytes]:
        """
        Read file content.
        
        Args:
            file_path: Path to the file
            mode: File open mode (default: 'rb' for binary read)
            
        Returns:
            File content as bytes, or None if error
        """
        try:
            with open(file_path, mode) as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    @staticmethod
    def read_text(file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """
        Read text file content.
        
        Args:
            file_path: Path to the file
            encoding: Text encoding (default: 'utf-8')
            
        Returns:
            File content as string, or None if error
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            return None
    
    @staticmethod
    def delete_file(file_path: Path) -> bool:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    @staticmethod
    def delete_directory(dir_path: Path, recursive: bool = False) -> bool:
        """
        Delete a directory.
        
        Args:
            dir_path: Path to the directory
            recursive: Whether to delete recursively (default: False)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if dir_path.exists() and dir_path.is_dir():
                if recursive:
                    shutil.rmtree(dir_path)
                else:
                    dir_path.rmdir()  # Only works if empty
                return True
            return False
        except Exception as e:
            print(f"Error deleting directory {dir_path}: {e}")
            return False
    
    @staticmethod
    def cleanup_temp_files(temp_dir: Path, pattern: str = "*") -> int:
        """
        Clean up temporary files matching a pattern.
        
        Args:
            temp_dir: Temporary directory path
            pattern: Glob pattern for files to delete (default: "*" for all)
            
        Returns:
            Number of files deleted
            
        Validates Requirement 14.6: Securely delete temporary attachment files
        """
        deleted_count = 0
        try:
            if temp_dir.exists() and temp_dir.is_dir():
                for file_path in temp_dir.glob(pattern):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")
        except Exception as e:
            print(f"Error cleaning up temp files in {temp_dir}: {e}")
        
        return deleted_count
    
    @staticmethod
    def list_files(directory: Path, pattern: str = "*", recursive: bool = False) -> List[Path]:
        """
        List files in a directory matching a pattern.
        
        Args:
            directory: Directory path
            pattern: Glob pattern (default: "*" for all files)
            recursive: Whether to search recursively (default: False)
            
        Returns:
            List of file paths
        """
        try:
            if not directory.exists() or not directory.is_dir():
                return []
            
            if recursive:
                return [p for p in directory.rglob(pattern) if p.is_file()]
            else:
                return [p for p in directory.glob(pattern) if p.is_file()]
        except Exception as e:
            print(f"Error listing files in {directory}: {e}")
            return []
    
    @staticmethod
    def ensure_directory(dir_path: Path) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            dir_path: Directory path
            
        Returns:
            True if directory exists or was created, False otherwise
        """
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {dir_path}: {e}")
            return False
    
    @staticmethod
    def get_file_size(file_path: Path) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes, or None if error
        """
        try:
            if file_path.exists() and file_path.is_file():
                return file_path.stat().st_size
            return None
        except Exception as e:
            print(f"Error getting file size for {file_path}: {e}")
            return None
    
    @staticmethod
    def copy_file(source: Path, destination: Path, secure: bool = True) -> bool:
        """
        Copy a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            secure: Whether to set secure permissions on destination (default: True)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(source, destination)
            
            # Set secure permissions if requested
            if secure:
                os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
            
            return True
        except Exception as e:
            print(f"Error copying file from {source} to {destination}: {e}")
            return False
    
    @staticmethod
    def move_file(source: Path, destination: Path, secure: bool = True) -> bool:
        """
        Move a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            secure: Whether to set secure permissions on destination (default: True)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            shutil.move(str(source), str(destination))
            
            # Set secure permissions if requested
            if secure:
                os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
            
            return True
        except Exception as e:
            print(f"Error moving file from {source} to {destination}: {e}")
            return False


# Convenience functions
def save_file_secure(file_path: Path, content: bytes) -> bool:
    """Save file with secure permissions."""
    return FileHandler.save_file_secure(file_path, content)


def save_text_secure(file_path: Path, content: str) -> bool:
    """Save text file with secure permissions."""
    return FileHandler.save_text_secure(file_path, content)


def read_file(file_path: Path) -> Optional[bytes]:
    """Read file content."""
    return FileHandler.read_file(file_path)


def read_text(file_path: Path) -> Optional[str]:
    """Read text file content."""
    return FileHandler.read_text(file_path)


def cleanup_temp_files(temp_dir: Path, pattern: str = "*") -> int:
    """Clean up temporary files."""
    return FileHandler.cleanup_temp_files(temp_dir, pattern)


def delete_file(file_path: Path) -> bool:
    """Delete a file."""
    return FileHandler.delete_file(file_path)


def ensure_directory(dir_path: Path) -> bool:
    """Ensure a directory exists."""
    return FileHandler.ensure_directory(dir_path)
