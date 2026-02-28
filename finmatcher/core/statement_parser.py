"""
Statement parser for PDF and Excel bank statements.

This module parses bank statements from different institutions
(Meriwest PDF, Amex Excel, Chase Excel) and normalizes the data.

Validates Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 12.5
"""

import re
from pathlib import Path
from typing import List, Optional, Dict
from decimal import Decimal
import pandas as pd
import pdfplumber

from database.models import Transaction
from utils.date_parser import normalize_date
from utils.logger import get_logger


class StatementParser:
    """
    Parser for bank statements from multiple institutions.
    
    Supports:
    - Meriwest PDF statements (using pdfplumber)
    - Amex Excel statements (using pandas)
    - Chase Excel statements (using pandas)
    
    Validates Requirements:
    - 2.1: Parse Meriwest PDF using pdfplumber
    - 2.2: Parse Amex Excel using pandas
    - 2.3: Parse Chase Excel using pandas
    - 2.4: Normalize dates to YYYY-MM-DD
    - 2.5: Normalize amounts to float
    - 2.6: Return descriptive errors on failure
    - 12.5: Skip malformed rows and log warnings
    """
    
    def __init__(self):
        """Initialize the statement parser."""
        self.logger = get_logger()
    
    def parse_statement(
        self,
        file_path: Path,
        statement_type: str
    ) -> List[Transaction]:
        """
        Parse a bank statement file.
        
        Args:
            file_path: Path to statement file
            statement_type: Type of statement ("meriwest", "amex", "chase")
            
        Returns:
            List of Transaction objects
            
        Raises:
            ValueError: If file format is invalid or parsing fails
        """
        if not file_path.exists():
            raise ValueError(f"Statement file not found: {file_path}")
        
        statement_type = statement_type.lower()
        
        try:
            if statement_type == "meriwest":
                # Check if it's PDF or Excel
                if file_path.suffix.lower() == '.pdf':
                    return self.parse_meriwest_pdf(file_path)
                else:
                    return self.parse_meriwest_excel(file_path)
            elif statement_type == "amex":
                return self.parse_amex_excel(file_path)
            elif statement_type == "chase":
                return self.parse_chase_excel(file_path)
            else:
                raise ValueError(
                    f"Unknown statement type: {statement_type}. "
                    f"Supported types: meriwest, amex, chase"
                )
        except Exception as e:
            error_msg = f"Failed to parse {statement_type} statement from {file_path}: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    def parse_meriwest_excel(self, file_path: Path) -> List[Transaction]:
        """
        Parse Meriwest Excel statement using pandas.
        
        Args:
            file_path: Path to Meriwest Excel file
            
        Returns:
            List of Transaction objects
            
        Validates Requirement 2.2: Read transaction data using pandas
        """
        transactions = []
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Meriwest Excel format: Date, Transaction, Name, Memo, Amount, Extra
            date_col = 'Date'
            desc_col = 'Name'
            amount_col = 'Amount'
            type_col = 'Transaction'
            memo_col = 'Memo'
            
            # Verify columns exist
            if date_col not in df.columns or desc_col not in df.columns or amount_col not in df.columns:
                raise ValueError(
                    f"Could not find required columns in Meriwest Excel. "
                    f"Found columns: {list(df.columns)}"
                )
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Extract fields
                    date_value = row[date_col]
                    description = str(row[desc_col]) if pd.notna(row[desc_col]) else ""
                    amount_value = row[amount_col]
                    transaction_type = str(row[type_col]).lower() if pd.notna(row[type_col]) else "debit"
                    memo = str(row[memo_col]) if pd.notna(row[memo_col]) else ""
                    
                    # Normalize date
                    if pd.isna(date_value):
                        continue
                    
                    if isinstance(date_value, pd.Timestamp):
                        normalized_date = date_value.strftime('%Y-%m-%d')
                    else:
                        normalized_date = normalize_date(str(date_value))
                    
                    if not normalized_date:
                        continue
                    
                    # Parse amount
                    amount = self._parse_amount(amount_value)
                    if amount is None:
                        continue
                    
                    # Build description
                    full_description = f"{description} {memo}".strip()
                    
                    # Create transaction
                    transaction_id = f"meriwest_{normalized_date}_{abs(hash(full_description))}"
                    
                    transaction = Transaction(
                        transaction_id=transaction_id,
                        date=normalized_date,
                        description=full_description,
                        amount=abs(amount),
                        transaction_type=transaction_type,
                        statement_name=file_path.stem
                    )
                    transactions.append(transaction)
                
                except Exception as e:
                    self.logger.warning(
                        f"Skipping malformed row {idx} in {file_path}: {e}"
                    )
                    continue
            
            self.logger.info(f"Parsed {len(transactions)} transactions from Meriwest Excel")
            return transactions
        
        except Exception as e:
            raise ValueError(f"Error parsing Meriwest Excel: {e}")
    
    def parse_meriwest_pdf(self, file_path: Path) -> List[Transaction]:
        """
        Parse Meriwest PDF statement using pdfplumber.
        
        Args:
            file_path: Path to Meriwest PDF file
            
        Returns:
            List of Transaction objects
            
        Validates Requirement 2.1: Extract transaction tables using pdfplumber
        """
        transactions = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables with default settings (works best for Meriwest)
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # Process each row (skip header row)
                        for row_idx, row in enumerate(table):
                            try:
                                # Skip header row
                                if row_idx == 0:
                                    continue
                                
                                # Skip empty rows
                                if not row or len(row) < 3:
                                    continue
                                
                                # Meriwest format: [Date, Transaction, Name, Memo, Amount, Extra]
                                date_str = row[0] if len(row) > 0 and row[0] else None
                                transaction_type = row[1] if len(row) > 1 and row[1] else ""
                                merchant_name = row[2] if len(row) > 2 and row[2] else ""
                                memo = row[3] if len(row) > 3 and row[3] else ""
                                amount_str = row[4] if len(row) > 4 and row[4] else ""
                                
                                # Validate date
                                if not date_str:
                                    continue
                                
                                normalized_date = normalize_date(date_str)
                                if not normalized_date:
                                    continue
                                
                                # Parse amount (may have extra characters, extract first valid amount)
                                # Example formats:
                                # - Simple: "-30" or "235.36"
                                # - Complex: "91395546-7314;3 0.7587" (encoded/corrupted)
                                amount = None
                                
                                # First try simple parsing
                                amount = self._parse_amount(amount_str)
                                
                                # If that fails, try to extract from complex format
                                if not amount:
                                    import re
                                    # Look for patterns like: 123.45 or -123.45 or 123
                                    # Try to find standalone numbers
                                    amount_pattern = re.compile(r'(?:^|\s)(-?\d+(?:\.\d{2})?)(?:\s|$)')
                                    matches = amount_pattern.findall(amount_str)
                                    
                                    if matches:
                                        # Take the last match (usually the actual amount)
                                        try:
                                            amount = self._parse_amount(matches[-1])
                                        except:
                                            pass
                                
                                # If still no amount, skip this row
                                if not amount:
                                    self.logger.debug(f"Could not parse amount from: {amount_str}")
                                    continue
                                
                                # Build description from merchant name and memo
                                description = f"{merchant_name} {memo}".strip()
                                
                                # Create transaction
                                transaction_id = f"meriwest_{normalized_date}_{abs(hash(description))}"
                                
                                transaction = Transaction(
                                    transaction_id=transaction_id,
                                    date=normalized_date,
                                    description=description,
                                    amount=abs(amount),
                                    transaction_type=transaction_type.lower() if transaction_type else "debit",
                                    statement_name=file_path.stem
                                )
                                transactions.append(transaction)
                            
                            except Exception as e:
                                # Skip malformed rows
                                self.logger.warning(
                                    f"Skipping malformed row in {file_path} page {page_num+1}: {e}"
                                )
                                continue
            
            self.logger.info(f"Parsed {len(transactions)} transactions from Meriwest PDF")
            return transactions
        
        except Exception as e:
            raise ValueError(f"Error parsing Meriwest PDF: {e}")
    
    def _parse_meriwest_row(self, row: List[str], statement_name: str) -> Optional[Transaction]:
        """
        Parse a single row from Meriwest statement.
        
        Expected format: [Date, Description, Amount, Balance]
        
        Args:
            row: List of cell values
            statement_name: Name of the statement
            
        Returns:
            Transaction object or None if invalid
        """
        if len(row) < 3:
            return None
        
        # Extract fields
        date_str = row[0] if row[0] else ""
        description = row[1] if row[1] else ""
        amount_str = row[2] if row[2] else ""
        balance_str = row[3] if len(row) > 3 and row[3] else None
        
        # Normalize date
        normalized_date = normalize_date(date_str)
        if not normalized_date:
            return None
        
        # Parse amount
        amount = self._parse_amount(amount_str)
        if amount is None:
            return None
        
        # Parse balance if available
        balance = self._parse_amount(balance_str) if balance_str else None
        
        # Create transaction
        transaction_id = f"meriwest_{normalized_date}_{abs(hash(description))}"
        
        return Transaction(
            transaction_id=transaction_id,
            date=normalized_date,
            description=description.strip(),
            amount=abs(amount),  # Ensure positive
            transaction_type="debit" if amount < 0 else "credit",
            balance=balance,
            statement_name=statement_name
        )
    
    def parse_amex_excel(self, file_path: Path) -> List[Transaction]:
        """
        Parse Amex Excel statement using pandas.
        
        Args:
            file_path: Path to Amex Excel file
            
        Returns:
            List of Transaction objects
            
        Validates Requirement 2.2: Read transaction data using pandas
        """
        transactions = []
        
        try:
            # Amex Excel has headers starting at row 7 (index 6)
            df = pd.read_excel(file_path, header=6)
            
            # Expected columns after header row 6: Date, Receipt Label, Description, Amount, etc.
            date_col = 'Date'
            desc_col = 'Description'
            amount_col = 'Amount'
            
            # Verify columns exist
            if date_col not in df.columns or desc_col not in df.columns or amount_col not in df.columns:
                raise ValueError(
                    f"Could not find required columns in Amex Excel. "
                    f"Found columns: {list(df.columns)}"
                )
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    transaction = self._parse_excel_row(
                        row, date_col, desc_col, amount_col, file_path.stem
                    )
                    if transaction:
                        transactions.append(transaction)
                
                except Exception as e:
                    self.logger.warning(
                        f"Skipping malformed row {idx} in {file_path}: {e}"
                    )
                    continue
            
            self.logger.info(f"Parsed {len(transactions)} transactions from Amex Excel")
            return transactions
        
        except Exception as e:
            raise ValueError(f"Error parsing Amex Excel: {e}")
    
    def parse_chase_excel(self, file_path: Path) -> List[Transaction]:
        """
        Parse Chase Excel statement using pandas.
        
        Args:
            file_path: Path to Chase Excel file
            
        Returns:
            List of Transaction objects
            
        Validates Requirement 2.3: Read transaction data using pandas
        """
        transactions = []
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Expected columns: Date, Description, Amount
            date_col = self._find_column(df, ['date', 'posting date', 'transaction date'])
            desc_col = self._find_column(df, ['description', 'desc', 'details'])
            amount_col = self._find_column(df, ['amount', 'charge', 'debit'])
            
            if not all([date_col, desc_col, amount_col]):
                raise ValueError(
                    f"Could not find required columns in Chase Excel. "
                    f"Found columns: {list(df.columns)}"
                )
            
            # Process each row
            for idx, row in df.iterrows():
                try:
                    transaction = self._parse_excel_row(
                        row, date_col, desc_col, amount_col, file_path.stem
                    )
                    if transaction:
                        transactions.append(transaction)
                
                except Exception as e:
                    self.logger.warning(
                        f"Skipping malformed row {idx} in {file_path}: {e}"
                    )
                    continue
            
            self.logger.info(f"Parsed {len(transactions)} transactions from Chase Excel")
            return transactions
        
        except Exception as e:
            raise ValueError(f"Error parsing Chase Excel: {e}")
    
    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """
        Find a column in DataFrame by trying multiple possible names.
        
        Args:
            df: DataFrame
            possible_names: List of possible column names (case-insensitive)
            
        Returns:
            Actual column name or None if not found
        """
        df_columns_lower = {col.lower(): col for col in df.columns}
        
        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns_lower[name.lower()]
        
        return None
    
    def _parse_excel_row(
        self,
        row: pd.Series,
        date_col: str,
        desc_col: str,
        amount_col: str,
        statement_name: str
    ) -> Optional[Transaction]:
        """
        Parse a single row from Excel statement.
        
        Args:
            row: Pandas Series (row)
            date_col: Date column name
            desc_col: Description column name
            amount_col: Amount column name
            statement_name: Name of the statement
            
        Returns:
            Transaction object or None if invalid
        """
        # Extract fields
        date_value = row[date_col]
        description = str(row[desc_col]) if pd.notna(row[desc_col]) else ""
        amount_value = row[amount_col]
        
        # Normalize date
        if pd.isna(date_value):
            return None
        
        # Handle datetime objects from pandas
        if isinstance(date_value, pd.Timestamp):
            normalized_date = date_value.strftime('%Y-%m-%d')
        else:
            normalized_date = normalize_date(str(date_value))
        
        if not normalized_date:
            return None
        
        # Parse amount
        amount = self._parse_amount(amount_value)
        if amount is None:
            return None
        
        # Create transaction
        transaction_id = f"{statement_name}_{normalized_date}_{abs(hash(description))}"
        
        return Transaction(
            transaction_id=transaction_id,
            date=normalized_date,
            description=description.strip(),
            amount=abs(amount),  # Ensure positive
            transaction_type="debit" if amount < 0 else "credit",
            statement_name=statement_name
        )
    
    def _parse_amount(self, amount_value) -> Optional[Decimal]:
        """
        Parse amount from various formats.
        
        Args:
            amount_value: Amount value (string, float, or Decimal)
            
        Returns:
            Decimal amount or None if invalid
            
        Validates Requirement 2.5: Normalize amounts to float values
        """
        if amount_value is None or (isinstance(amount_value, str) and not amount_value.strip()):
            return None
        
        try:
            # Handle pandas NaN
            if pd.isna(amount_value):
                return None
            
            # Convert to string and clean
            amount_str = str(amount_value).strip()
            
            # Remove currency symbols and commas
            amount_str = re.sub(r'[$,\s]', '', amount_str)
            
            # Handle parentheses (negative amounts)
            if '(' in amount_str and ')' in amount_str:
                amount_str = '-' + amount_str.replace('(', '').replace(')', '')
            
            # Parse to Decimal
            amount = Decimal(amount_str)
            
            # Validate positive (we'll handle sign separately)
            if amount == 0:
                return None
            
            return amount
        
        except (ValueError, TypeError, Exception):
            return None


# Convenience function
def parse_statement(file_path: Path, statement_type: str) -> List[Transaction]:
    """
    Parse a bank statement file.
    
    Args:
        file_path: Path to statement file
        statement_type: Type of statement ("meriwest", "amex", "chase")
        
    Returns:
        List of Transaction objects
    """
    parser = StatementParser()
    return parser.parse_statement(file_path, statement_type)
