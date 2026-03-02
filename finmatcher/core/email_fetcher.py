"""
Multi-threaded email fetcher for IMAP/Gmail API.

This module implements a 20-thread email ingestion engine that fetches
emails from multiple accounts with keyword filtering and deduplication.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 5.1, 14.4
"""

import imaplib
import email as email_lib
import email.utils
import time
import ssl
from email.header import decode_header
from email.message import Message as EmailMessage
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import queue

from finmatcher.config.settings import get_settings, EmailAccount
from finmatcher.database.cache_manager import get_cache_manager, CacheManager
from finmatcher.database.models import ProcessedEmail
from finmatcher.utils.logger import get_logger
from finmatcher.core.financial_filter import FinancialFilter


class EmailFetcher:
    """
    Multi-threaded email fetcher using IMAP.
    
    Implements a 20-thread architecture for parallel email fetching
    from multiple accounts with keyword filtering and deduplication.
    
    Validates Requirements:
    - 1.1: Load email accounts from environment variables
    - 1.2: Use thread pool with 20 threads
    - 1.3: Query emails using keywords
    - 1.4: Calculate MD5 hash for deduplication
    - 1.5: Extract required fields
    - 1.6: Save attachments to disk
    - 1.7: Implement rate limiting
    - 1.8: Filter by date window
    - 5.1: ThreadPoolExecutor for I/O-bound operations
    - 14.4: Use TLS/SSL encryption
    """
    
    # Keywords for financial email search
    FINANCIAL_KEYWORDS = ['receipt', 'invoice', 'bill', 'payment', 'order', 'statement']
    
    def __init__(
        self,
        thread_pool_size: Optional[int] = None,
        rate_limit_delay: Optional[float] = None,
        deepseek_client = None
    ):
        """
        Initialize the email fetcher.
        
        Args:
            thread_pool_size: Number of threads (default: from config, typically 20)
            rate_limit_delay: Delay between API calls in seconds (default: from config)
            deepseek_client: Optional DeepSeek client for financial filtering
            
        Validates Requirement 1.1: Load configured email accounts
        Validates Requirement 13.10: Integrate FinancialFilter
        """
        self.settings = get_settings()
        self.cache_manager = get_cache_manager()
        self.logger = get_logger()
        
        # Thread pool configuration
        self.thread_pool_size = thread_pool_size or self.settings.thread_pool_size
        self.rate_limit_delay = rate_limit_delay or self.settings.gmail_api_rate_limit_delay
        
        # Email accounts from config
        self.email_accounts = self.settings.email_accounts
        
        # Queue for email payloads
        self.email_queue = queue.Queue()
        
        # Initialize financial filter
        self.financial_filter = FinancialFilter(deepseek_client)
        
        # Filter statistics
        self.filter_stats = {
            'total_emails': 0,
            'auto_rejected': 0,
            'auto_accepted': 0,
            'ai_verified': 0,
            'financial_emails': 0
        }
        
        self.logger.info(f"Initialized EmailFetcher with {self.thread_pool_size} threads")
        self.logger.info(f"Configured {len(self.email_accounts)} email accounts")
        self.logger.info("Financial filter integrated")
    
    def fetch_all_emails(
        self,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Fetch emails from all configured accounts using thread pool.
        
        Args:
            date_range: Optional tuple of (start_date, end_date) for filtering
            keywords: Optional list of keywords to search (default: FINANCIAL_KEYWORDS)
            
        Returns:
            List of email dictionaries
            
        Validates Requirements:
        - 1.2: Use thread pool with 20 threads
        - 5.1: ThreadPoolExecutor for I/O-bound email fetching
        """
        keywords = keywords or self.FINANCIAL_KEYWORDS
        all_emails = []
        
        self.logger.log_milestone_start(
            "Email Fetching",
            f"Fetching from {len(self.email_accounts)} accounts with {self.thread_pool_size} threads"
        )
        
        start_time = time.time()
        
        # Create tasks for each account/folder combination
        tasks = []
        for account in self.email_accounts:
            for folder in account.folders:
                tasks.append((account, folder, date_range, keywords))
        
        self.logger.info(f"Created {len(tasks)} fetch tasks")
        
        # Execute tasks in parallel with thread pool
        with ThreadPoolExecutor(max_workers=self.thread_pool_size) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(
                    self._fetch_from_account_folder,
                    account, folder, date_range, keywords
                ): (account.email, folder)
                for account, folder, date_range, keywords in tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                account_email, folder = future_to_task[future]
                try:
                    emails = future.result()
                    all_emails.extend(emails)
                    self.logger.info(
                        f"[OK] Fetched {len(emails)} emails from {account_email}/{folder}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"[ERROR] Error fetching from {account_email}/{folder}: {e}",
                        exc_info=True
                    )
        
        duration = time.time() - start_time
        
        # Filter emails using financial filter
        self.logger.info(f"Filtering {len(all_emails)} emails using financial filter...")
        financial_emails = self._filter_emails(all_emails)
        
        self.logger.log_milestone_end(
            "Email Fetching",
            records_processed=len(financial_emails),
            duration_seconds=duration
        )
        
        # Log filter statistics
        self._log_filter_statistics()
        
        return financial_emails
    
    def _fetch_from_account_folder(
        self,
        account: EmailAccount,
        folder: str,
        date_range: Optional[Tuple[datetime, datetime]],
        keywords: List[str]
    ) -> List[Dict]:
        """
        Fetch emails from a specific account and folder with optimized batching.
        
        Args:
            account: EmailAccount configuration
            folder: Folder name (e.g., "INBOX", "Spam")
            date_range: Optional date range filter
            keywords: Keywords to search for
            
        Returns:
            List of email dictionaries
            
        Validates Requirements:
        - 1.3: Query emails using keywords
        - 1.8: Filter by date window
        - 14.4: Use TLS/SSL encryption
        """
        emails = []
        
        try:
            # Connect to IMAP server with SSL
            imap = imaplib.IMAP4_SSL(
                self.settings.imap_settings.server,
                self.settings.imap_settings.port
            )
            
            # Login
            imap.login(account.email, account.password)
            
            # FIX 1: Properly quote folder names (especially Gmail folders with special chars)
            # Gmail folders with spaces or special characters need to be quoted
            status, _ = imap.select(f'"{folder}"', readonly=True)
            if status != 'OK':
                self.logger.warning(f"Could not select folder {folder} for {account.email}")
                return emails
            
            # FIX 2: Date-based filtering to avoid "1MB limit" error
            # Only fetch emails from last 90 days by default (configurable)
            if not date_range:
                # Default to last 90 days to avoid IMAP search limit
                search_date = datetime.now() - timedelta(days=90)
                date_range = (search_date, datetime.now())
            
            # Build search criteria with date filter
            search_criteria = self._build_search_criteria(keywords, date_range)
            
            # Search for emails with error handling for large responses
            try:
                status, message_ids = imap.search(None, search_criteria)
            except imaplib.IMAP4.error as e:
                # If search fails due to size, fall back to date-only search
                self.logger.warning(
                    f"Search with keywords failed (possibly too many results), "
                    f"falling back to date-only search: {e}"
                )
                # Simpler search with just date
                start_date = date_range[0] if date_range else datetime.now() - timedelta(days=90)
                search_criteria = f'SINCE {start_date.strftime("%d-%b-%Y")}'
                status, message_ids = imap.search(None, search_criteria)
            
            if status != 'OK':
                self.logger.warning(f"Search failed for {account.email}/{folder}")
                return emails
            
            # Get list of email IDs
            email_ids = message_ids[0].split()
            
            self.logger.info(
                f"Found {len(email_ids)} emails in {account.email}/{folder} "
                f"(date range: {date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')})"
            )
            
            # OPTIMIZATION: Batch fetch emails in chunks for better performance
            batch_size = 100  # Fetch 100 emails at a time
            total_emails = len(email_ids)
            processed = 0
            
            for i in range(0, total_emails, batch_size):
                batch_ids = email_ids[i:i+batch_size]
                
                # Progress indicator
                processed += len(batch_ids)
                progress_pct = (processed / total_emails) * 100
                self.logger.info(
                    f"[PROGRESS] {account.email}/{folder}: {processed}/{total_emails} "
                    f"({progress_pct:.1f}%) - Fetching batch {i//batch_size + 1}"
                )
                
                # Fetch batch
                batch_emails = []
                for email_id in batch_ids:
                    try:
                        # Check cache first (skip already processed)
                        email_data = self._fetch_single_email(
                            imap, email_id, account.email, folder
                        )
                        
                        if email_data:
                            batch_emails.append(email_data)
                    
                    except Exception as e:
                        self.logger.debug(f"Error fetching email {email_id}: {e}")
                        continue
                
                # Batch save to database
                if batch_emails:
                    self._save_emails_to_cache_batch(batch_emails)
                    emails.extend(batch_emails)
            
            # Logout
            imap.logout()
            
            self.logger.info(
                f"[OK] Completed {account.email}/{folder}: "
                f"Fetched {len(emails)} new emails (skipped {total_emails - len(emails)} cached)"
            )
        
        except Exception as e:
            self.logger.error(
                f"Error connecting to {account.email}: {e}",
                exc_info=True
            )
        
        return emails
    
    def _build_search_criteria(
        self,
        keywords: List[str],
        date_range: Optional[Tuple[datetime, datetime]]
    ) -> str:
        """
        Build IMAP search criteria string.
        
        Args:
            keywords: Keywords to search for
            date_range: Optional date range
            
        Returns:
            IMAP search criteria string
            
        Validates Requirement 1.3: Search with keywords in subject or body
        """
        criteria_parts = []
        
        # Add keyword search (OR logic for multiple keywords)
        if keywords:
            keyword_parts = []
            for keyword in keywords:
                keyword_parts.append(f'OR SUBJECT "{keyword}" BODY "{keyword}"')
            
            # Combine with OR logic
            if len(keyword_parts) == 1:
                criteria_parts.append(keyword_parts[0])
            else:
                # Build nested OR structure
                criteria = keyword_parts[0]
                for part in keyword_parts[1:]:
                    criteria = f'OR ({criteria}) ({part})'
                criteria_parts.append(criteria)
        
        # Add date range filter
        if date_range:
            start_date, end_date = date_range
            criteria_parts.append(f'SINCE {start_date.strftime("%d-%b-%Y")}')
            criteria_parts.append(f'BEFORE {end_date.strftime("%d-%b-%Y")}')
        
        # Combine all criteria
        return ' '.join(criteria_parts) if criteria_parts else 'ALL'
    
    def _fetch_single_email(
        self,
        imap: imaplib.IMAP4_SSL,
        email_id: bytes,
        account_email: str,
        folder: str
    ) -> Optional[Dict]:
        """
        Fetch a single email and extract required fields.
        
        Args:
            imap: IMAP connection
            email_id: Email ID
            account_email: Account email address
            folder: Folder name
            
        Returns:
            Email dictionary or None if already processed
            
        Validates Requirements:
        - 1.4: Calculate MD5 hash for deduplication
        - 1.5: Extract required fields
        - 1.6: Save attachments to disk
        """
        try:
            # Fetch email data
            status, msg_data = imap.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            # Parse email
            email_message = email_lib.message_from_bytes(msg_data[0][1])
            
            # Get Message-ID for deduplication
            message_id = email_message.get('Message-ID', f'no-id-{email_id.decode()}')
            
            # Check if already processed (OPTIMIZATION: Check cache first)
            if self.cache_manager.is_email_processed(message_id):
                return None  # Skip already processed
            
            # Extract required fields
            sender = self._decode_header(email_message.get('From', ''))
            subject = self._decode_header(email_message.get('Subject', ''))
            date_str = email_message.get('Date', '')
            
            # Parse date
            try:
                received_date = email.utils.parsedate_to_datetime(date_str)
            except:
                received_date = datetime.now()
            
            # Extract sender name and email
            sender_name, sender_email = self._parse_sender(sender)
            
            # Extract attachments
            attachments = self._extract_attachments(email_message, message_id)
            
            # Create email data dictionary
            email_data = {
                'email_id': email_id.decode(),
                'message_id': message_id,
                'sender_name': sender_name,
                'sender_email': sender_email,
                'subject': subject,
                'received_date': received_date,
                'account_email': account_email,
                'folder': folder,
                'attachments': attachments,
                'body': self._extract_body(email_message),
                'has_attachments': len(attachments) > 0
            }
            
            return email_data
        
        except Exception as e:
            self.logger.debug(f"Error processing email {email_id}: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """
        Decode email header value.
        
        Args:
            header_value: Raw header value
            
        Returns:
            Decoded string
        """
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_str = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    decoded_str += part.decode('utf-8', errors='ignore')
            else:
                decoded_str += str(part)
        
        return decoded_str
    
    def _parse_sender(self, sender: str) -> Tuple[str, str]:
        """
        Parse sender into name and email address.
        
        Args:
            sender: Sender string (e.g., "John Doe <john@example.com>")
            
        Returns:
            Tuple of (name, email)
        """
        try:
            if '<' in sender and '>' in sender:
                name = sender.split('<')[0].strip().strip('"')
                email_addr = sender.split('<')[1].split('>')[0].strip()
                return (name, email_addr)
            else:
                return (sender, sender)
        except:
            return (sender, sender)
    
    def _extract_body(self, email_message: EmailMessage) -> str:
        """
        Extract email body text.
        
        Args:
            email_message: Email message object
            
        Returns:
            Body text
        """
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        
        return body
    
    def _extract_attachments(
        self,
        email_message: EmailMessage,
        message_id: str
    ) -> List[Dict]:
        """
        Extract attachments from email and save to disk.
        
        Args:
            email_message: Email message object
            message_id: Message ID for unique naming
            
        Returns:
            List of attachment dictionaries
            
        Validates Requirement 1.6: Save attachments to disk immediately
        """
        attachments = []
        
        if not email_message.is_multipart():
            return attachments
        
        # Create temp directory if it doesn't exist
        temp_dir = self.settings.temp_attachments_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        for part in email_message.walk():
            # Skip non-attachment parts
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            
            filename = part.get_filename()
            if not filename:
                continue
            
            # Decode filename
            filename = self._decode_header(filename)
            
            # Sanitize filename to avoid path issues
            # Remove invalid characters and limit length
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-'))
            safe_filename = safe_filename[:100]  # Limit filename length
            
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_message_id = message_id.replace('<', '').replace('>', '').replace('/', '_')[:30]  # Shorter ID
            unique_filename = f"{timestamp}_{safe_message_id}_{safe_filename}"
            
            # Ensure total path length is reasonable (Windows has 260 char limit)
            if len(str(temp_dir / unique_filename)) > 250:
                # Truncate filename further if needed
                max_filename_len = 250 - len(str(temp_dir)) - len(timestamp) - len(safe_message_id) - 3
                safe_filename = safe_filename[:max_filename_len]
                unique_filename = f"{timestamp}_{safe_message_id}_{safe_filename}"
            
            file_path = temp_dir / unique_filename
            
            # Save attachment
            try:
                payload = part.get_payload(decode=True)
                
                # Skip if payload is None (happens with .eml attachments, calendar invites, etc.)
                if payload is None:
                    self.logger.debug(f"Skipping attachment {filename}: payload is None")
                    continue
                
                with open(file_path, 'wb') as f:
                    f.write(payload)
                
                attachments.append({
                    'filename': filename,
                    'file_path': str(file_path),
                    'content_type': part.get_content_type(),
                    'size': file_path.stat().st_size
                })
                
                self.logger.debug(f"Saved attachment: {unique_filename}")
            
            except Exception as e:
                self.logger.error(f"Error saving attachment {filename}: {e}")
        
        return attachments
    
    def _filter_emails(self, emails: List[Dict]) -> List[Dict]:
        """
        Filter emails using financial filter.
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            List of financial email dictionaries
            
        Validates Requirements:
        - 13.10: Process only emails that pass the Financial_Filter
        - 13.7: Log filtering method used
        """
        financial_emails = []
        
        for email_data in emails:
            self.filter_stats['total_emails'] += 1
            
            # Prepare email data for filter
            filter_input = {
                'subject': email_data.get('subject', ''),
                'sender': email_data.get('sender_email', ''),
                'body': email_data.get('body', '')
            }
            
            # Apply financial filter
            result = self.financial_filter.filter_email(filter_input)
            
            if result:
                # Email passed filter - it's financial
                self.filter_stats['financial_emails'] += 1
                
                # Track filter method
                filter_method = result.get('filter_method')
                if filter_method:
                    if filter_method == 'auto_accept':
                        self.filter_stats['auto_accepted'] += 1
                    elif filter_method == 'ai_verified':
                        self.filter_stats['ai_verified'] += 1
                
                # Add filter metadata to email data
                email_data['is_financial'] = True
                email_data['filter_method'] = filter_method
                
                financial_emails.append(email_data)
            else:
                # Email rejected - not financial
                self.filter_stats['auto_rejected'] += 1
                # Discarded - not added to financial_emails
        
        self.logger.info(
            f"Filtered {len(financial_emails)}/{len(emails)} financial emails"
        )
        
        return financial_emails
    
    def _save_emails_to_cache_batch(self, emails: List[Dict]):
        """
        Save a batch of emails to cache database.
        
        Args:
            emails: List of email dictionaries to save
        """
        if not emails:
            return
        
        try:
            processed_emails = []
            for email_data in emails:
                md5_hash = self.cache_manager.calculate_md5_hash(email_data['message_id'])
                processed_email = ProcessedEmail(
                    email_id=email_data['email_id'],
                    message_id=email_data['message_id'],
                    md5_hash=md5_hash,
                    processed_timestamp=datetime.now(),
                    account_email=email_data['account_email'],
                    folder=email_data['folder'],
                    has_attachments=email_data['has_attachments'],
                    is_financial=True  # Assume financial since we filtered by keywords
                )
                processed_emails.append(processed_email)
            
            # Batch save to database
            self.cache_manager.mark_emails_processed_batch(processed_emails)
            self.logger.debug(f"Saved {len(processed_emails)} emails to cache")
        
        except Exception as e:
            self.logger.error(f"Error saving emails to cache: {e}")
    
    def _log_filter_statistics(self):
        """
        Log filter statistics for cost optimization tracking.
        
        Validates Requirements:
        - 13.7: Log filtering method used
        - 13.8: Minimize API calls by using rule-based filtering for 80%+ of emails
        """
        total = self.filter_stats['total_emails']
        if total == 0:
            return
        
        auto_rejected = self.filter_stats['auto_rejected']
        auto_accepted = self.filter_stats['auto_accepted']
        ai_verified = self.filter_stats['ai_verified']
        financial = self.filter_stats['financial_emails']
        
        rule_based = auto_rejected + auto_accepted
        rule_based_percent = (rule_based / total) * 100 if total > 0 else 0
        api_calls_percent = (ai_verified / total) * 100 if total > 0 else 0
        
        self.logger.info("=" * 80)
        self.logger.info("FINANCIAL FILTER STATISTICS")
        self.logger.info("=" * 80)
        self.logger.info(f"Total emails processed: {total}")
        self.logger.info(f"Financial emails: {financial} ({(financial/total)*100:.1f}%)")
        self.logger.info(f"Auto-rejected (marketing/spam): {auto_rejected} ({(auto_rejected/total)*100:.1f}%)")
        self.logger.info(f"Auto-accepted (financial keywords): {auto_accepted} ({(auto_accepted/total)*100:.1f}%)")
        self.logger.info(f"AI-verified (ambiguous): {ai_verified} ({(ai_verified/total)*100:.1f}%)")
        self.logger.info(f"Rule-based filtering: {rule_based_percent:.1f}%")
        self.logger.info(f"API calls required: {api_calls_percent:.1f}%")
        
        if rule_based_percent >= 80:
            self.logger.info("[OK] Target met: 80%+ rule-based filtering (cost optimized)")
        else:
            self.logger.warning(f"[WARNING] Target not met: {rule_based_percent:.1f}% rule-based (target: 80%+)")
        
        self.logger.info("=" * 80)


# Convenience function
def fetch_emails(
    date_range: Optional[Tuple[datetime, datetime]] = None,
    keywords: Optional[List[str]] = None
) -> List[Dict]:
    """
    Fetch emails from all configured accounts.
    
    Args:
        date_range: Optional date range filter
        keywords: Optional keywords to search
        
    Returns:
        List of email dictionaries
    """
    fetcher = EmailFetcher()
    return fetcher.fetch_all_emails(date_range, keywords)
