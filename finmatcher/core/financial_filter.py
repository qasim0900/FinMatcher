"""
Financial email filter for FinMatcher v2.0 Enterprise Upgrade.

This module implements a strict three-layer filtering system to accept only
financial emails and reject all others, minimizing API costs by 85%.

Three-layer approach:
1. Auto-Reject: Fast keyword-based rejection for marketing/spam (40-50%)
2. Auto-Accept: Fast keyword-based acceptance for financial emails (30-40%)
3. AI Verification: DeepSeek-powered verification for ambiguous emails (10-20%)

Validates Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

from finmatcher.core.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


class FilterMethod(Enum):
    """
    Financial email filtering method used.
    
    Validates Requirement: 13.1
    """
    AUTO_REJECT = "auto_reject"    # Rejected by marketing/spam keywords
    AUTO_ACCEPT = "auto_accept"    # Accepted by financial keywords
    AI_VERIFIED = "ai_verified"    # Verified by DeepSeek AI


class FinancialFilter:
    """
    Three-layer financial email filter.
    
    Implements strict binary filtering:
    - Layer 1: Auto-reject marketing/spam emails (no API cost)
    - Layer 2: Auto-accept financial emails (no API cost)
    - Layer 3: AI verification for ambiguous emails (API cost only for unclear cases)
    
    Target: 80%+ rule-based filtering, 85% API cost reduction
    
    Validates Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10
    """
    
    # Financial keywords for auto-accept (Requirement 13.3)
    FINANCIAL_KEYWORDS = [
        'receipt',
        'invoice',
        'bill',
        'payment',
        'transaction',
        'order confirmation',
        'purchase',
        'statement',
        'total amount',
        'amount due',
        'payment received',
        'order #',
        'invoice #',
        'account statement',
        'payment confirmation'
    ]
    
    # Marketing/spam keywords for auto-reject (Requirement 13.2)
    MARKETING_SPAM_KEYWORDS = [
        'unsubscribe',
        'newsletter',
        'discount',
        'sale',
        'offer',
        'limited time',
        'subscribe',
        'click here',
        'job offer',
        'resume',
        'meeting',
        'promotion',
        'deal',
        'coupon',
        'free shipping',
        '% off'
    ]
    
    def __init__(self, deepseek_client: Optional[DeepSeekClient] = None):
        """
        Initialize financial filter with optional AI client.
        
        Args:
            deepseek_client: DeepSeek client for AI verification (optional)
        """
        self.deepseek_client = deepseek_client
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'auto_rejected': 0,
            'auto_accepted': 0,
            'ai_verified': 0,
            'ai_rejected': 0
        }
        
        logger.info(
            f"Financial filter initialized "
            f"(AI enabled: {deepseek_client is not None})"
        )
    
    def filter_email(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filter email using three-layer approach.
        
        Args:
            email_data: Dict with 'subject', 'sender', 'body' keys
            
        Returns:
            Email data dict if financial, None if non-financial
            
        Validates Requirements:
        - 13.1: Implement three-layer filtering system
        - 13.2: Auto-reject for marketing/spam keywords
        - 13.3: Auto-accept for financial keywords
        - 13.4: AI verification for ambiguous emails
        - 13.9: Return email data if financial, None if non-financial
        - 13.10: Process only emails that pass filter
        """
        self.stats['total_processed'] += 1
        
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        body = email_data.get('body', '').lower()
        
        combined_text = f"{subject} {sender} {body}"
        
        # Layer 1: Auto-Reject (Fastest - No API Call)
        # Requirement 13.2: Reject marketing/spam keywords
        if self._is_clear_spam_marketing(combined_text):
            self.stats['auto_rejected'] += 1
            logger.debug(f"Rejected (Marketing/Spam): {email_data.get('subject', 'N/A')}")
            return None
        
        # Layer 2: Auto-Accept (Fast - No API Call)
        # Requirement 13.3: Accept financial keywords
        if self._is_clear_financial(combined_text):
            self.stats['auto_accepted'] += 1
            logger.info(f"Accepted (Financial Rule): {email_data.get('subject', 'N/A')}")
            email_data['is_financial'] = True
            email_data['filter_method'] = FilterMethod.AUTO_ACCEPT.value
            return email_data
        
        # Layer 3: AI Verification (Slow - API Call for Ambiguous Only)
        # Requirement 13.4: AI verification for ambiguous emails
        if self.deepseek_client:
            if self._ai_verification(email_data.get('subject', ''), email_data.get('body', '')):
                self.stats['ai_verified'] += 1
                logger.info(f"Accepted (AI Verified): {email_data.get('subject', 'N/A')}")
                email_data['is_financial'] = True
                email_data['filter_method'] = FilterMethod.AI_VERIFIED.value
                return email_data
            else:
                self.stats['ai_rejected'] += 1
        
        # Default: Reject (Conservative Approach)
        # Requirement 13.6: Reject on API failure or unavailability
        logger.debug(f"Rejected (Non-Financial): {email_data.get('subject', 'N/A')}")
        return None
    
    def _is_clear_financial(self, text: str) -> bool:
        """
        Layer 2: Check if email is clearly financial (Auto-Accept).
        
        Args:
            text: Combined email text (subject + sender + body)
            
        Returns:
            True if financial keywords found
            
        Validates Requirement: 13.3 - Auto-accept for financial keywords
        """
        text_lower = text.lower()
        
        for keyword in self.FINANCIAL_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def _is_clear_spam_marketing(self, text: str) -> bool:
        """
        Layer 1: Check if email is clearly spam/marketing (Auto-Reject).
        
        Args:
            text: Combined email text (subject + sender + body)
            
        Returns:
            True if marketing/spam keywords found
            
        Validates Requirement: 13.2 - Auto-reject for marketing/spam keywords
        """
        text_lower = text.lower()
        
        for keyword in self.MARKETING_SPAM_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def _ai_verification(self, subject: str, body: str) -> bool:
        """
        Layer 3: DeepSeek AI verification for ambiguous emails.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            True if AI confirms financial, False otherwise
            
        Validates Requirements:
        - 13.4: AI verification for ambiguous emails
        - 13.5: Binary AI response (is_financial: true/false)
        - 13.6: Conservative fallback on API failure
        """
        try:
            is_financial = self.deepseek_client.verify_financial_email(subject, body)
            return is_financial
        except Exception as e:
            logger.error(f"AI verification error: {e}")
            return False  # Conservative: reject on error
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get filtering statistics.
        
        Returns:
            Dictionary with filtering statistics
            
        Validates Requirement: 13.8 - Minimize API calls by using rule-based filtering for at least 80% of emails
        """
        total = self.stats['total_processed']
        
        if total == 0:
            return {
                'total_processed': 0,
                'auto_rejected': 0,
                'auto_accepted': 0,
                'ai_verified': 0,
                'ai_rejected': 0,
                'rule_based_percentage': 0.0,
                'api_cost_reduction': 0.0
            }
        
        rule_based = self.stats['auto_rejected'] + self.stats['auto_accepted']
        rule_based_percentage = (rule_based / total) * 100
        
        # API cost reduction: percentage of emails filtered without API
        api_cost_reduction = rule_based_percentage
        
        return {
            'total_processed': total,
            'auto_rejected': self.stats['auto_rejected'],
            'auto_rejected_pct': (self.stats['auto_rejected'] / total) * 100,
            'auto_accepted': self.stats['auto_accepted'],
            'auto_accepted_pct': (self.stats['auto_accepted'] / total) * 100,
            'ai_verified': self.stats['ai_verified'],
            'ai_verified_pct': (self.stats['ai_verified'] / total) * 100,
            'ai_rejected': self.stats['ai_rejected'],
            'ai_rejected_pct': (self.stats['ai_rejected'] / total) * 100,
            'rule_based_percentage': rule_based_percentage,
            'api_cost_reduction': api_cost_reduction
        }
    
    def log_statistics(self):
        """
        Log filtering statistics.
        
        Validates Requirement: 13.7 - Log filtering method used for each email
        """
        stats = self.get_statistics()
        
        logger.info("=" * 80)
        logger.info("Financial Filter Statistics")
        logger.info("=" * 80)
        logger.info(f"Total Emails Processed: {stats['total_processed']:,}")
        logger.info(f"Auto-Rejected (Marketing/Spam): {stats['auto_rejected']:,} ({stats['auto_rejected_pct']:.1f}%)")
        logger.info(f"Auto-Accepted (Financial): {stats['auto_accepted']:,} ({stats['auto_accepted_pct']:.1f}%)")
        logger.info(f"AI Verified (Financial): {stats['ai_verified']:,} ({stats['ai_verified_pct']:.1f}%)")
        logger.info(f"AI Rejected (Non-Financial): {stats['ai_rejected']:,} ({stats['ai_rejected_pct']:.1f}%)")
        logger.info(f"Rule-Based Filtering: {stats['rule_based_percentage']:.1f}%")
        logger.info(f"API Cost Reduction: {stats['api_cost_reduction']:.1f}%")
        logger.info("=" * 80)
