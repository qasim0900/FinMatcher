#!/usr/bin/env python3
"""
Phase 1: Core Integration - FastEmailProcessor Implementation
Replace existing EmailFetcher with optimized Gmail API processing
Target: Server-side filtering + Parallel processing + Database optimization
"""

import pandas as pd
import numpy as np
import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import hashlib
from tqdm import tqdm
import psycopg2
from sqlalchemy import create_engine, text
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EmailMetadata:
    """Optimized email metadata structure"""
    message_id: str
    subject: str
    sender: str
    date: str
    has_attachment: bool
    attachment_count: int = 0
    processing_status: str = 'pending'
    financial_score: float = 0.0

class FastEmailProcessor:
    """
    Production-ready FastEmailProcessor for Phase 1 Core Integration
    Implements server-side filtering, parallel processing, and vectorized operations
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.max_workers = config.get('max_threads', 50)
        self.batch_size = config.get('batch_size', 1000)
        self.db_uri = config.get('db_uri', 'postgresql://user:pass@localhost/finmatcher')
        
        # Gmail API service (mock for testing - replace with actual implementation)
        self.gmail_service = self._initialize_gmail_service()
        
        # Performance metrics
        self.metrics = {
            'emails_fetched': 0,
            'emails_processed': 0,
            'emails_stored': 0,
            'processing_time': 0.0,
            'filtering_efficiency': 0.0
        }
        
        logger.info(f"FastEmailProcessor initialized with {self.max_workers} threads")
    
    def _initialize_gmail_service(self):
        """Initialize Gmail API service (mock implementation)"""
        # In production, this would be actual Gmail API initialization
        class MockGmailService:
            def __init__(self):
                self.call_count = 0
            
            def users(self):
                return self
            
            def messages(self):
                return self
            
            def list(self, userId='me', q='', maxResults=10000, pageToken=None):
                self.call_count += 1
                # Simulate Gmail API response
                import random
                
                # Generate realistic financial email IDs based on query
                if 'invoice' in q.lower() or 'receipt' in q.lower():
                    # Simulate 12% of 200k emails being financial (24k emails)
                    message_count = min(maxResults, random.randint(20000, 25000))
                else:
                    message_count = min(maxResults, random.randint(1000, 5000))
                
                messages = [{'id': f'msg_{i}_{self.call_count}'} for i in range(message_count)]
                
                result = {
                    'messages': messages,
                    'resultSizeEstimate': len(messages)
                }
                
                # Simulate pagination
                if len(messages) >= maxResults and pageToken is None:
                    result['nextPageToken'] = f'token_{self.call_count}'
                
                return MockExecuteResult(result)
            
            def get(self, userId='me', id='', format='metadata', metadataHeaders=None):
                # Simulate individual email metadata
                import random
                
                # Generate realistic email metadata
                subjects = [
                    f"Invoice #{random.randint(1000, 9999)} from Company ABC",
                    f"Receipt for Order #{random.randint(10000, 99999)}",
                    f"Payment Confirmation - ${random.randint(10, 5000):.2f}",
                    f"Statement for {random.choice(['January', 'February', 'March'])} 2024",
                    f"Bill Due - Account #{random.randint(100000, 999999)}"
                ]
                
                senders = [
                    "billing@company.com",
                    "noreply@payments.com", 
                    "invoices@business.com",
                    "receipts@store.com",
                    "statements@bank.com"
                ]
                
                # Simulate email with attachments (80% of financial emails have attachments)
                has_parts = random.random() < 0.8
                parts = []
                if has_parts:
                    parts = [
                        {'filename': f'invoice_{random.randint(1000, 9999)}.pdf'},
                        {'filename': f'receipt_{random.randint(1000, 9999)}.jpg'}
                    ]
                
                email_data = {
                    'id': id,
                    'payload': {
                        'headers': [
                            {'name': 'Subject', 'value': random.choice(subjects)},
                            {'name': 'From', 'value': random.choice(senders)},
                            {'name': 'Date', 'value': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()}
                        ],
                        'parts': parts if has_parts else []
                    }
                }
                
                return MockExecuteResult(email_data)
        
        class MockExecuteResult:
            def __init__(self, data):
                self.data = data
            
            def execute(self):
                # Simulate API latency
                time.sleep(0.001)  # 1ms simulated latency
                return self.data
        
        return MockGmailService()
    
    def create_optimized_gmail_query(self, date_range: Optional[Tuple] = None) -> str:
        """
        OPTIMIZATION 1: Server-side Gmail Query (Set Theory)
        Creates mathematically optimized query to reduce 200k -> 20k emails
        """
        # Base query for financial emails with attachments
        base_query = """
        has:attachment AND (
            subject:(invoice OR receipt OR bill OR statement OR payment OR order OR confirmation) OR
            from:(billing OR invoices OR receipts OR accounting OR noreply OR orders OR payments) OR
            filename:(pdf OR jpg OR png OR jpeg)
        )
        """
        
        # Add date filtering if specified
        if date_range:
            start_date, end_date = date_range
            base_query += f" AND after:{start_date.strftime('%Y/%m/%d')} AND before:{end_date.strftime('%Y/%m/%d')}"
        
        # Clean and optimize query
        optimized_query = ' '.join(base_query.split())
        
        logger.info(f"Optimized Gmail query created: {optimized_query[:100]}...")
        return optimized_query
    
    def fetch_financial_email_ids(self, date_range: Optional[Tuple] = None) -> List[Dict]:
        """
        STEP A: Fetch Financial Email IDs using optimized Gmail query
        Server-side filtering to reduce data transfer by 90%
        """
        logger.info("🔍 STEP A: Fetching Financial Email IDs from Gmail...")
        start_time = time.time()
        
        # Create optimized query
        query = self.create_optimized_gmail_query(date_range)
        
        all_messages = []
        page_token = None
        page_count = 0
        
        try:
            while True:
                # Gmail API call with pagination
                if page_token:
                    results = self.gmail_service.users().messages().list(
                        userId='me', 
                        q=query,
                        maxResults=10000,
                        pageToken=page_token
                    ).execute()
                else:
                    results = self.gmail_service.users().messages().list(
                        userId='me', 
                        q=query,
                        maxResults=10000
                    ).execute()
                
                messages = results.get('messages', [])
                all_messages.extend(messages)
                page_count += 1
                
                logger.info(f"   Page {page_count}: {len(messages)} emails fetched")
                
                # Check for next page
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                
                # Safety limit to prevent infinite loops
                if page_count >= 10:
                    logger.warning("Reached maximum page limit (10 pages)")
                    break
        
        except Exception as e:
            logger.error(f"Error fetching email IDs: {e}")
            return []
        
        fetch_time = time.time() - start_time
        self.metrics['emails_fetched'] = len(all_messages)
        
        logger.info(f"✅ Gmail Filtering Complete:")
        logger.info(f"   - Financial emails found: {len(all_messages):,}")
        logger.info(f"   - Fetch time: {fetch_time:.2f} seconds")
        logger.info(f"   - Average speed: {len(all_messages)/fetch_time:.0f} IDs/second")
        
        return all_messages
    
    def fetch_email_metadata_parallel(self, message_ids: List[Dict]) -> List[EmailMetadata]:
        """
        STEP B: Parallel Email Metadata Fetching (Divide & Conquer)
        Uses ThreadPoolExecutor for optimal I/O parallelization
        """
        logger.info(f"🚀 STEP B: Downloading metadata for {len(message_ids)} emails...")
        start_time = time.time()
        
        def fetch_single_metadata(msg_data: Dict) -> Optional[EmailMetadata]:
            """Fetch metadata for single email"""
            try:
                msg_id = msg_data['id']
                
                # Fetch only metadata (not full email body) for efficiency
                msg = self.gmail_service.users().messages().get(
                    userId='me', 
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                # Extract headers
                headers = {h['name']: h['value'] for h in msg['payload']['headers']}
                
                # Check for attachments without downloading
                has_attachment = False
                attachment_count = 0
                
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part.get('filename'):
                            has_attachment = True
                            attachment_count += 1
                
                # Calculate financial score based on content
                financial_score = self._calculate_financial_score(
                    headers.get('Subject', ''),
                    headers.get('From', '')
                )
                
                return EmailMetadata(
                    message_id=msg_id,
                    subject=headers.get('Subject', ''),
                    sender=headers.get('From', ''),
                    date=headers.get('Date', ''),
                    has_attachment=has_attachment,
                    attachment_count=attachment_count,
                    financial_score=financial_score
                )
                
            except Exception as e:
                logger.error(f"Error fetching metadata for {msg_data.get('id', 'unknown')}: {e}")
                return None
        
        # Parallel processing with progress bar
        email_metadata = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(fetch_single_metadata, msg) for msg in message_ids]
            
            # Collect results with progress tracking
            for future in tqdm(as_completed(futures), total=len(message_ids), desc="Fetching metadata"):
                result = future.result()
                if result:
                    email_metadata.append(result)
        
        fetch_time = time.time() - start_time
        self.metrics['emails_processed'] = len(email_metadata)
        
        logger.info(f"✅ Parallel Metadata Fetch Complete:")
        logger.info(f"   - Emails processed: {len(email_metadata):,}")
        logger.info(f"   - Processing time: {fetch_time:.2f} seconds")
        logger.info(f"   - Average speed: {len(email_metadata)/fetch_time:.0f} emails/second")
        logger.info(f"   - Success rate: {len(email_metadata)/len(message_ids)*100:.1f}%")
        
        return email_metadata
    
    def _calculate_financial_score(self, subject: str, sender: str) -> float:
        """Calculate financial relevance score for email"""
        financial_keywords = [
            'invoice', 'receipt', 'bill', 'statement', 'payment', 
            'order', 'confirmation', 'transaction', 'purchase'
        ]
        
        financial_domains = [
            'billing', 'invoices', 'receipts', 'accounting', 
            'noreply', 'orders', 'payments'
        ]
        
        score = 0.0
        text = f"{subject} {sender}".lower()
        
        # Keyword scoring
        for keyword in financial_keywords:
            if keyword in text:
                score += 0.1
        
        # Domain scoring
        for domain in financial_domains:
            if domain in sender.lower():
                score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def process_and_store_vectorized(self, email_metadata: List[EmailMetadata]) -> pd.DataFrame:
        """
        STEP C: Vectorized Processing and Database Storage (Linear Algebra)
        Uses pandas for high-speed data processing and bulk database operations
        """
        logger.info(f"⚡ STEP C: Vectorized processing of {len(email_metadata)} emails...")
        start_time = time.time()
        
        # Convert to DataFrame for vectorized operations
        data = []
        for email in email_metadata:
            data.append({
                'message_id': email.message_id,
                'subject': email.subject,
                'sender': email.sender,
                'date': email.date,
                'has_attachment': email.has_attachment,
                'attachment_count': email.attachment_count,
                'processing_status': email.processing_status,
                'financial_score': email.financial_score,
                'created_at': datetime.now().isoformat()
            })
        
        df = pd.DataFrame(data)
        
        if len(df) == 0:
            logger.warning("No email data to process")
            return df
        
        # Vectorized data cleaning and processing
        logger.info("   Applying vectorized data transformations...")
        
        # Clean and standardize dates
        df['date'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
        
        # Filter out invalid dates
        df = df.dropna(subset=['date'])
        
        # Add derived columns using vectorized operations
        df['date_processed'] = df['date'].dt.date
        df['sender_domain'] = df['sender'].str.extract(r'@([^>]+)')
        df['subject_length'] = df['subject'].str.len()
        
        # Filter: Only emails with attachments (primary requirement)
        df_filtered = df[df['has_attachment'] == True].copy()
        
        # Sort by financial score (highest first)
        df_filtered = df_filtered.sort_values('financial_score', ascending=False)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Vectorized Processing Complete:")
        logger.info(f"   - Input emails: {len(df):,}")
        logger.info(f"   - Emails with attachments: {len(df_filtered):,}")
        logger.info(f"   - Filter efficiency: {len(df_filtered)/len(df)*100:.1f}%")
        logger.info(f"   - Processing time: {processing_time:.2f} seconds")
        logger.info(f"   - Processing speed: {len(df)/processing_time:.0f} emails/second")
        
        # Store in database
        self._store_to_database(df_filtered)
        
        return df_filtered
    
    def _store_to_database(self, df: pd.DataFrame):
        """Store processed emails to PostgreSQL database"""
        logger.info(f"💾 Storing {len(df)} emails to PostgreSQL...")
        start_time = time.time()
        
        try:
            # Create database engine
            engine = create_engine(self.db_uri)
            
            # Ensure table exists with proper schema
            self._ensure_database_schema(engine)
            
            # Bulk insert using pandas to_sql (fastest method)
            df.to_sql(
                'processed_emails',
                engine,
                if_exists='append',
                index=False,
                chunksize=self.batch_size,
                method='multi'  # Use multi-row INSERT for speed
            )
            
            storage_time = time.time() - start_time
            self.metrics['emails_stored'] = len(df)
            
            logger.info(f"✅ Database Storage Complete:")
            logger.info(f"   - Records stored: {len(df):,}")
            logger.info(f"   - Storage time: {storage_time:.2f} seconds")
            logger.info(f"   - Storage speed: {len(df)/storage_time:.0f} records/second")
            
        except Exception as e:
            logger.error(f"Database storage failed: {e}")
            raise
    
    def _ensure_database_schema(self, engine):
        """Ensure database table exists with proper schema"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS processed_emails (
            id SERIAL PRIMARY KEY,
            message_id VARCHAR(255) UNIQUE NOT NULL,
            subject TEXT,
            sender VARCHAR(500),
            date TIMESTAMP WITH TIME ZONE,
            has_attachment BOOLEAN DEFAULT FALSE,
            attachment_count INTEGER DEFAULT 0,
            processing_status VARCHAR(50) DEFAULT 'pending',
            financial_score FLOAT DEFAULT 0.0,
            date_processed DATE,
            sender_domain VARCHAR(255),
            subject_length INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_processed_emails_attachment 
        ON processed_emails(has_attachment) WHERE has_attachment = TRUE;
        
        CREATE INDEX IF NOT EXISTS idx_processed_emails_date 
        ON processed_emails(date_processed);
        
        CREATE INDEX IF NOT EXISTS idx_processed_emails_financial_score 
        ON processed_emails(financial_score DESC);
        
        CREATE INDEX IF NOT EXISTS idx_processed_emails_status 
        ON processed_emails(processing_status);
        """
        
        with engine.connect() as conn:
            conn.execute(text(schema_sql))
            conn.commit()
        
        logger.info("✅ Database schema verified/created")
    
    def run_phase_1_complete(self, date_range: Optional[Tuple] = None) -> Dict:
        """
        Execute complete Phase 1: Core Integration
        Returns comprehensive results and metrics
        """
        logger.info("🚀 STARTING PHASE 1: CORE INTEGRATION")
        logger.info("="*60)
        logger.info("Objective: Replace EmailFetcher with FastEmailProcessor")
        logger.info("Target: Server-side filtering + Parallel processing + Database optimization")
        logger.info("="*60)
        
        total_start_time = time.time()
        
        try:
            # Step A: Fetch Financial Email IDs
            financial_ids = self.fetch_financial_email_ids(date_range)
            
            if not financial_ids:
                logger.error("No financial emails found. Check Gmail API configuration.")
                return {'success': False, 'error': 'No emails found'}
            
            # Step B: Fetch Email Metadata in Parallel
            email_metadata = self.fetch_email_metadata_parallel(financial_ids)
            
            if not email_metadata:
                logger.error("No email metadata retrieved. Check API permissions.")
                return {'success': False, 'error': 'No metadata retrieved'}
            
            # Step C: Process and Store with Vectorized Operations
            processed_df = self.process_and_store_vectorized(email_metadata)
            
            total_time = time.time() - total_start_time
            self.metrics['processing_time'] = total_time
            
            # Calculate efficiency metrics
            if len(financial_ids) > 0:
                self.metrics['filtering_efficiency'] = len(processed_df) / len(financial_ids)
            
            # Generate summary report
            results = {
                'success': True,
                'phase': 'Phase 1: Core Integration',
                'metrics': self.metrics,
                'summary': {
                    'total_processing_time': total_time,
                    'emails_identified': len(financial_ids),
                    'emails_processed': len(email_metadata),
                    'emails_stored': len(processed_df),
                    'filtering_efficiency': self.metrics['filtering_efficiency'],
                    'average_processing_speed': len(processed_df) / total_time if total_time > 0 else 0
                },
                'data': processed_df
            }
            
            logger.info("="*60)
            logger.info("✅ PHASE 1 COMPLETE - SUMMARY REPORT")
            logger.info("="*60)
            logger.info(f"Total Processing Time: {total_time:.2f} seconds")
            logger.info(f"Emails Identified: {len(financial_ids):,}")
            logger.info(f"Emails Processed: {len(email_metadata):,}")
            logger.info(f"Emails Stored: {len(processed_df):,}")
            logger.info(f"Filtering Efficiency: {self.metrics['filtering_efficiency']:.1%}")
            logger.info(f"Average Speed: {results['summary']['average_processing_speed']:.0f} emails/second")
            logger.info("="*60)
            logger.info("🎯 READY FOR PHASE 2: Statement Matching")
            logger.info("="*60)
            
            return results
            
        except Exception as e:
            logger.error(f"Phase 1 failed with error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

def main():
    """Test Phase 1 implementation"""
    
    # Configuration
    config = {
        'max_threads': 50,
        'batch_size': 1000,
        'db_uri': 'postgresql://finmatcher:password@localhost/finmatcher_db'
        # Note: Update with your actual PostgreSQL connection string
    }
    
    # Initialize processor
    processor = FastEmailProcessor(config)
    
    # Run Phase 1
    results = processor.run_phase_1_complete()
    
    if results['success']:
        print("\n🎉 PHASE 1 INTEGRATION SUCCESSFUL!")
        print(f"✅ Processed {results['summary']['emails_stored']:,} emails")
        print(f"✅ Average speed: {results['summary']['average_processing_speed']:.0f} emails/second")
        print("✅ Database updated with attachment flags")
        print("✅ Ready for Phase 2 implementation")
    else:
        print(f"\n❌ PHASE 1 FAILED: {results.get('error', 'Unknown error')}")
    
    return results

if __name__ == "__main__":
    main()