"""
Credit Card Statement Parser
Parses PDF and Excel statements from Meriwest, Amex, and Chase
"""

import pandas as pd
import PyPDF2
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Transaction:
    """Represents a credit card transaction"""
    
    def __init__(
        self,
        date: datetime,
        description: str,
        amount: float,
        card_type: str,
        card_last4: Optional[str] = None,
        category: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.date = date
        self.description = description
        self.amount = amount
        self.card_type = card_type
        self.card_last4 = card_last4
        self.category = category
        self.raw_data = raw_data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'card_type': self.card_type,
            'card_last4': self.card_last4,
            'category': self.category,
            'raw_data': self.raw_data
        }
    
    def __repr__(self):
        return f"Transaction({self.date}, {self.description}, ${self.amount}, {self.card_type})"


class MeriwestParser:
    """Parser for Meriwest PDF statements"""
    
    @staticmethod
    def parse(file_path: str) -> List[Transaction]:
        """
        Parse Meriwest PDF statement
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            List of transactions
        """
        transactions = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                # Parse transactions
                # Pattern: MM/DD/YYYY Description Amount
                pattern = r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$?([\d,]+\.\d{2})'
                
                for match in re.finditer(pattern, text):
                    date_str, description, amount_str = match.groups()
                    
                    try:
                        date = datetime.strptime(date_str, '%m/%d/%Y')
                        amount = float(amount_str.replace(',', ''))
                        
                        transaction = Transaction(
                            date=date,
                            description=description.strip(),
                            amount=amount,
                            card_type='Meriwest',
                            raw_data={'source': 'pdf', 'raw_text': match.group(0)}
                        )
                        
                        transactions.append(transaction)
                        
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Failed to parse Meriwest transaction: {e}")
                        continue
                
                logger.info(f"Parsed {len(transactions)} transactions from Meriwest statement")
                
        except Exception as e:
            logger.error(f"Failed to parse Meriwest statement: {e}")
            raise
        
        return transactions


class AmexParser:
    """Parser for Amex Excel statements"""
    
    @staticmethod
    def parse(file_path: str) -> List[Transaction]:
        """
        Parse Amex Excel statement
        
        Args:
            file_path: Path to Excel file
        
        Returns:
            List of transactions
        """
        transactions = []
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Common Amex column names (try different variations)
            date_cols = ['Date', 'Transaction Date', 'Post Date', 'date']
            desc_cols = ['Description', 'Merchant', 'Payee', 'description']
            amount_cols = ['Amount', 'Charge Amount', 'amount']
            
            # Find actual column names
            date_col = next((col for col in date_cols if col in df.columns), None)
            desc_col = next((col for col in desc_cols if col in df.columns), None)
            amount_col = next((col for col in amount_cols if col in df.columns), None)
            
            if not all([date_col, desc_col, amount_col]):
                logger.error(f"Could not find required columns in Amex statement. Columns: {df.columns.tolist()}")
                raise ValueError("Missing required columns in Amex statement")
            
            # Parse each row
            for idx, row in df.iterrows():
                try:
                    date = pd.to_datetime(row[date_col])
                    description = str(row[desc_col]).strip()
                    amount = float(row[amount_col])
                    
                    # Skip if amount is 0 or NaN
                    if pd.isna(amount) or amount == 0:
                        continue
                    
                    transaction = Transaction(
                        date=date,
                        description=description,
                        amount=abs(amount),  # Ensure positive
                        card_type='Amex',
                        raw_data={'source': 'excel', 'row': idx}
                    )
                    
                    transactions.append(transaction)
                    
                except (ValueError, KeyError, AttributeError) as e:
                    logger.warning(f"Failed to parse Amex transaction at row {idx}: {e}")
                    continue
            
            logger.info(f"Parsed {len(transactions)} transactions from Amex statement")
            
        except Exception as e:
            logger.error(f"Failed to parse Amex statement: {e}")
            raise
        
        return transactions


class ChaseParser:
    """Parser for Chase Excel statements"""
    
    @staticmethod
    def parse(file_path: str) -> List[Transaction]:
        """
        Parse Chase Excel statement
        
        Args:
            file_path: Path to Excel file
        
        Returns:
            List of transactions
        """
        transactions = []
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Common Chase column names
            date_cols = ['Transaction Date', 'Date', 'Post Date', 'date']
            desc_cols = ['Description', 'Merchant', 'Payee', 'description']
            amount_cols = ['Amount', 'Charge', 'amount']
            category_cols = ['Category', 'Type', 'category']
            
            # Find actual column names
            date_col = next((col for col in date_cols if col in df.columns), None)
            desc_col = next((col for col in desc_cols if col in df.columns), None)
            amount_col = next((col for col in amount_cols if col in df.columns), None)
            category_col = next((col for col in category_cols if col in df.columns), None)
            
            if not all([date_col, desc_col, amount_col]):
                logger.error(f"Could not find required columns in Chase statement. Columns: {df.columns.tolist()}")
                raise ValueError("Missing required columns in Chase statement")
            
            # Parse each row
            for idx, row in df.iterrows():
                try:
                    date = pd.to_datetime(row[date_col])
                    description = str(row[desc_col]).strip()
                    amount = float(row[amount_col])
                    category = str(row[category_col]).strip() if category_col else None
                    
                    # Skip if amount is 0 or NaN
                    if pd.isna(amount) or amount == 0:
                        continue
                    
                    transaction = Transaction(
                        date=date,
                        description=description,
                        amount=abs(amount),  # Ensure positive
                        card_type='Chase',
                        category=category,
                        raw_data={'source': 'excel', 'row': idx}
                    )
                    
                    transactions.append(transaction)
                    
                except (ValueError, KeyError, AttributeError) as e:
                    logger.warning(f"Failed to parse Chase transaction at row {idx}: {e}")
                    continue
            
            logger.info(f"Parsed {len(transactions)} transactions from Chase statement")
            
        except Exception as e:
            logger.error(f"Failed to parse Chase statement: {e}")
            raise
        
        return transactions


class StatementParser:
    """Main statement parser that handles all card types"""
    
    def __init__(self, statements_dir: str = "statements"):
        self.statements_dir = Path(statements_dir)
        self.parsers = {
            'meriwest': MeriwestParser(),
            'amex': AmexParser(),
            'chase': ChaseParser()
        }
    
    def parse_all(self) -> Dict[str, List[Transaction]]:
        """
        Parse all statements in the statements directory
        
        Returns:
            Dictionary mapping card type to list of transactions
        """
        results = {}
        
        # Parse Meriwest (PDF)
        meriwest_files = list(self.statements_dir.glob("*Meriwest*.pdf"))
        if meriwest_files:
            logger.info(f"Found Meriwest statement: {meriwest_files[0]}")
            results['meriwest'] = self.parsers['meriwest'].parse(str(meriwest_files[0]))
        else:
            logger.warning("No Meriwest statement found")
            results['meriwest'] = []
        
        # Parse Amex (Excel)
        amex_files = list(self.statements_dir.glob("*Amex*.xlsx"))
        if amex_files:
            logger.info(f"Found Amex statement: {amex_files[0]}")
            results['amex'] = self.parsers['amex'].parse(str(amex_files[0]))
        else:
            logger.warning("No Amex statement found")
            results['amex'] = []
        
        # Parse Chase (Excel)
        chase_files = list(self.statements_dir.glob("*Chase*.xlsx"))
        if chase_files:
            logger.info(f"Found Chase statement: {chase_files[0]}")
            results['chase'] = self.parsers['chase'].parse(str(chase_files[0]))
        else:
            logger.warning("No Chase statement found")
            results['chase'] = []
        
        total = sum(len(txns) for txns in results.values())
        logger.info(f"Total transactions parsed: {total}")
        
        return results
    
    def save_to_database(self, transactions_by_card: Dict[str, List[Transaction]], db_pool):
        """
        Save parsed transactions to receipts table
        
        Args:
            transactions_by_card: Dictionary of transactions by card type
            db_pool: Database connection pool
        """
        from datetime import datetime
        
        all_transactions = []
        for card_type, transactions in transactions_by_card.items():
            for txn in transactions:
                all_transactions.append((
                    f"{card_type}-{txn.date.strftime('%Y%m%d')}-{abs(hash(txn.description)) % 10000}",  # receipt_number
                    txn.amount,
                    'USD',
                    txn.description,
                    txn.date,
                    txn.category,
                    card_type,
                    str(txn.raw_data)
                ))
        
        if all_transactions:
            db_pool.execute_values(
                """
                INSERT INTO receipts (
                    receipt_number, amount, currency, merchant_name,
                    transaction_date, category, payment_method, description
                )
                VALUES %s
                ON CONFLICT (receipt_number) DO NOTHING
                """,
                all_transactions
            )
            
            logger.info(f"Saved {len(all_transactions)} transactions to database")
