"""
Intelligent date extraction and normalization utilities.

This module provides regex-based date parsing for multiple formats
and normalization to YYYY-MM-DD format.

Validates Requirements: 2.4, 12.1
"""

import re
from datetime import datetime
from typing import Optional, List, Tuple
from dateutil import parser as dateutil_parser


class DateParser:
    """
    Intelligent date parser supporting multiple formats.
    
    Supports:
    - MM/DD/YYYY
    - DD/MM/YYYY
    - YYYY-MM-DD
    - Month DD, YYYY (e.g., "January 15, 2024")
    - DD Month YYYY (e.g., "15 January 2024")
    - Mon DD, YYYY (e.g., "Jan 15, 2024")
    - And many more via dateutil
    
    Validates Requirements:
    - 2.4: Normalize dates to YYYY-MM-DD format
    - 12.1: Validate extracted values are valid calendar dates
    """
    
    # Regex patterns for common date formats
    PATTERNS = [
        # YYYY-MM-DD or YYYY/MM/DD
        (re.compile(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b'), 'YYYY-MM-DD'),
        
        # MM/DD/YYYY or MM-DD-YYYY
        (re.compile(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b'), 'MM/DD/YYYY'),
        
        # Month DD, YYYY (e.g., "January 15, 2024" or "Jan 15, 2024")
        (re.compile(r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})\b', re.IGNORECASE), 'Month DD, YYYY'),
        
        # DD Month YYYY (e.g., "15 January 2024" or "15 Jan 2024")
        (re.compile(r'\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+(\d{4})\b', re.IGNORECASE), 'DD Month YYYY'),
    ]
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """
        Extract all dates from text and normalize to YYYY-MM-DD format.
        
        Args:
            text: Text containing dates
            
        Returns:
            List of normalized dates in YYYY-MM-DD format
            
        Validates Requirement 2.4: Normalize dates to YYYY-MM-DD format
        """
        dates = []
        
        # Try each regex pattern
        for pattern, format_name in DateParser.PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    normalized = DateParser._normalize_match(match, format_name)
                    if normalized and DateParser.is_valid_date(normalized):
                        dates.append(normalized)
                except (ValueError, IndexError):
                    continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_dates = []
        for date in dates:
            if date not in seen:
                seen.add(date)
                unique_dates.append(date)
        
        return unique_dates
    
    @staticmethod
    def _normalize_match(match: Tuple, format_name: str) -> Optional[str]:
        """
        Normalize a regex match to YYYY-MM-DD format.
        
        Args:
            match: Tuple of matched groups
            format_name: Name of the format pattern
            
        Returns:
            Normalized date string in YYYY-MM-DD format, or None if invalid
        """
        try:
            if format_name == 'YYYY-MM-DD':
                year, month, day = match
                return f"{year}-{int(month):02d}-{int(day):02d}"
            
            elif format_name == 'MM/DD/YYYY':
                month, day, year = match
                return f"{year}-{int(month):02d}-{int(day):02d}"
            
            elif format_name in ['Month DD, YYYY', 'DD Month YYYY']:
                # Use dateutil to parse month names
                date_str = ' '.join(match)
                parsed = dateutil_parser.parse(date_str, fuzzy=False)
                return parsed.strftime('%Y-%m-%d')
            
        except (ValueError, AttributeError):
            return None
        
        return None
    
    @staticmethod
    def parse_date(date_str: str, fuzzy: bool = True) -> Optional[str]:
        """
        Parse a date string using dateutil and normalize to YYYY-MM-DD.
        
        Args:
            date_str: Date string to parse
            fuzzy: Whether to use fuzzy parsing (extract date from text)
            
        Returns:
            Normalized date in YYYY-MM-DD format, or None if parsing fails
            
        Validates Requirement 2.4: Normalize dates to YYYY-MM-DD format
        """
        try:
            parsed = dateutil_parser.parse(date_str, fuzzy=fuzzy)
            normalized = parsed.strftime('%Y-%m-%d')
            
            # Validate the date
            if DateParser.is_valid_date(normalized):
                return normalized
        except (ValueError, TypeError, AttributeError):
            pass
        
        return None
    
    @staticmethod
    def is_valid_date(date_str: str) -> bool:
        """
        Validate that a date string represents a valid calendar date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            True if valid, False otherwise
            
        Validates Requirement 12.1: Validate extracted values are valid calendar dates
        """
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Check reasonable year range (1900-2100)
            if not (1900 <= date_obj.year <= 2100):
                return False
            
            # Check month and day are valid
            if not (1 <= date_obj.month <= 12):
                return False
            
            if not (1 <= date_obj.day <= 31):
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def normalize_date(date_str: str) -> Optional[str]:
        """
        Normalize any date string to YYYY-MM-DD format.
        
        This is the main entry point for date normalization.
        Tries multiple parsing strategies.
        
        Args:
            date_str: Date string in any supported format
            
        Returns:
            Normalized date in YYYY-MM-DD format, or None if parsing fails
            
        Validates Requirement 2.4: Normalize dates to YYYY-MM-DD format
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        # Clean the input
        date_str = date_str.strip()
        
        # Try direct parsing first
        normalized = DateParser.parse_date(date_str, fuzzy=False)
        if normalized:
            return normalized
        
        # Try fuzzy parsing
        normalized = DateParser.parse_date(date_str, fuzzy=True)
        if normalized:
            return normalized
        
        # Try extracting dates from text
        dates = DateParser.extract_dates(date_str)
        if dates:
            return dates[0]  # Return first found date
        
        return None
    
    @staticmethod
    def parse_date_range(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract a date range from text (e.g., "01/01/2024 - 01/31/2024").
        
        Args:
            text: Text containing date range
            
        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format, or (None, None)
        """
        # Extract all dates
        dates = DateParser.extract_dates(text)
        
        if len(dates) >= 2:
            return (dates[0], dates[1])
        elif len(dates) == 1:
            return (dates[0], None)
        
        return (None, None)


# Convenience functions
def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize any date string to YYYY-MM-DD format.
    
    Args:
        date_str: Date string in any supported format
        
    Returns:
        Normalized date in YYYY-MM-DD format, or None if parsing fails
    """
    return DateParser.normalize_date(date_str)


def extract_dates(text: str) -> List[str]:
    """
    Extract all dates from text and normalize to YYYY-MM-DD format.
    
    Args:
        text: Text containing dates
        
    Returns:
        List of normalized dates in YYYY-MM-DD format
    """
    return DateParser.extract_dates(text)


def is_valid_date(date_str: str) -> bool:
    """
    Validate that a date string represents a valid calendar date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        True if valid, False otherwise
    """
    return DateParser.is_valid_date(date_str)


def parse_date_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract a date range from text.
    
    Args:
        text: Text containing date range
        
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    return DateParser.parse_date_range(text)
