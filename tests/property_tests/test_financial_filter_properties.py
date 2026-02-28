"""
Property-based tests for Financial Filter.

This module contains property-based tests using Hypothesis to verify
universal properties of the Financial Filter component.

Testing Framework: pytest + Hypothesis
Feature: finmatcher-v2-upgrade
Task: 6.7 - Write property test for conservative fallback
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
import requests

from finmatcher.core.financial_filter import FinancialFilter, FilterMethod
from finmatcher.core.deepseek_client import DeepSeekClient


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=100)
settings.load_profile("finmatcher")


class TestFinancialFilterProperties:
    """
    Property-based tests for Financial Filter.
    
    Tests verify universal properties that should hold across all inputs.
    """
    
    # Feature: finmatcher-v2-upgrade, Property 32: Conservative Fallback on API Failure
    @given(
        subject=st.text(min_size=0, max_size=200),
        body=st.text(min_size=0, max_size=500),
        error_type=st.sampled_from([
            requests.exceptions.Timeout("Connection timeout"),
            requests.exceptions.ConnectionError("Connection refused"),
            requests.exceptions.RequestException("API error"),
            Exception("Unexpected error"),
            ValueError("Invalid response"),
            KeyError("Missing key")
        ])
    )
    @settings(max_examples=20)
    def test_conservative_fallback_on_api_failure(
        self, 
        subject: str, 
        body: str, 
        error_type: Exception
    ):
        """
        **Validates: Requirements 13.6**
        
        Property 32: Conservative Fallback on API Failure
        
        For any ambiguous email where the DeepSeek_API fails or is unavailable,
        the Financial_Filter must reject the email (conservative approach).
        
        This property verifies that:
        1. When the DeepSeek API fails with any error type, the filter rejects the email
        2. The conservative fallback returns None (reject) rather than accepting
        3. This applies to all types of API failures (network, timeout, server errors, etc.)
        4. The behavior is consistent across all email inputs
        """
        # Setup: Create a fresh mock for each test iteration
        mock_deepseek_client = Mock(spec=DeepSeekClient)
        mock_deepseek_client.verify_financial_email.side_effect = error_type
        
        # Create filter with the mock client
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        # Create email data that is ambiguous (no clear financial or spam keywords)
        # We need to ensure the email doesn't contain keywords that would trigger auto-accept/reject
        email_data = {
            'subject': subject,
            'sender': 'test@example.com',
            'body': body
        }
        
        # Check if email would be auto-accepted or auto-rejected by keywords
        combined_text = f"{subject} test@example.com {body}".lower()
        
        # Skip if email contains financial keywords (would be auto-accepted)
        has_financial_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.FINANCIAL_KEYWORDS
        )
        
        # Skip if email contains spam/marketing keywords (would be auto-rejected)
        has_spam_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
        )
        
        # Only test ambiguous emails (no clear keywords)
        if not has_financial_keywords and not has_spam_keywords:
            # Act: Filter the email
            result = financial_filter.filter_email(email_data)
            
            # Assert: Email must be rejected (conservative fallback)
            assert result is None, (
                f"Conservative fallback failed: Email should be rejected when API fails, "
                f"but got {result}. Error type: {type(error_type).__name__}"
            )
            
            # Verify that the API was called (email reached Layer 3)
            mock_deepseek_client.verify_financial_email.assert_called_once_with(
                subject, body
            )
    
    @given(
        subject=st.text(min_size=0, max_size=200),
        body=st.text(min_size=0, max_size=500)
    )
    @settings(max_examples=20)
    def test_conservative_fallback_when_api_unavailable(
        self, 
        subject: str, 
        body: str
    ):
        """
        **Validates: Requirements 13.6**
        
        Property 32: Conservative Fallback on API Failure (API Unavailable)
        
        For any ambiguous email where the DeepSeek_API is unavailable (None),
        the Financial_Filter must reject the email (conservative approach).
        
        This property verifies that:
        1. When no DeepSeek client is provided, ambiguous emails are rejected
        2. The filter doesn't attempt to call a non-existent API
        3. The conservative approach is applied consistently
        """
        # Create filter without DeepSeek client (API unavailable)
        financial_filter = FinancialFilter(deepseek_client=None)
        
        # Create email data that is ambiguous
        email_data = {
            'subject': subject,
            'sender': 'test@example.com',
            'body': body
        }
        
        # Check if email would be auto-accepted or auto-rejected by keywords
        combined_text = f"{subject} test@example.com {body}".lower()
        
        has_financial_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.FINANCIAL_KEYWORDS
        )
        
        has_spam_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
        )
        
        # Only test ambiguous emails
        if not has_financial_keywords and not has_spam_keywords:
            # Act: Filter the email
            result = financial_filter.filter_email(email_data)
            
            # Assert: Email must be rejected (conservative fallback)
            assert result is None, (
                f"Conservative fallback failed: Ambiguous email should be rejected "
                f"when API is unavailable, but got {result}"
            )
    
    @given(
        subject=st.text(min_size=0, max_size=200),
        body=st.text(min_size=0, max_size=500),
        api_returns_true=st.booleans()
    )
    @settings(max_examples=20)
    def test_api_false_response_rejects_email(
        self, 
        subject: str, 
        body: str,
        api_returns_true: bool
    ):
        """
        **Validates: Requirements 13.5, 13.6**
        
        Property 32: Conservative Fallback (API Returns False)
        
        For any ambiguous email where the DeepSeek_API returns False,
        the Financial_Filter must reject the email.
        
        This property verifies that:
        1. When the API successfully returns False, the email is rejected
        2. The filter respects the AI's decision
        3. Only True responses result in acceptance
        """
        # Setup: Create a fresh mock for each test iteration
        mock_deepseek_client = Mock(spec=DeepSeekClient)
        mock_deepseek_client.verify_financial_email.return_value = api_returns_true
        
        # Create filter with the mock client
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        # Create email data that is ambiguous
        email_data = {
            'subject': subject,
            'sender': 'test@example.com',
            'body': body
        }
        
        # Check if email would be auto-accepted or auto-rejected by keywords
        combined_text = f"{subject} test@example.com {body}".lower()
        
        has_financial_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.FINANCIAL_KEYWORDS
        )
        
        has_spam_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
        )
        
        # Only test ambiguous emails
        if not has_financial_keywords and not has_spam_keywords:
            # Act: Filter the email
            result = financial_filter.filter_email(email_data)
            
            # Assert: Email acceptance depends on API response
            if api_returns_true:
                # API returned True -> email must be accepted
                assert result is not None, (
                    f"Email should be accepted when API returns True, but got None"
                )
                assert result.get('is_financial') is True
                assert result.get('filter_method') == FilterMethod.AI_VERIFIED.value
            else:
                # API returned False -> email must be rejected
                assert result is None, (
                    f"Email should be rejected when API returns False, but got {result}"
                )
    
    # Feature: finmatcher-v2-upgrade, Property 33: Filter Method Logging
    @given(
        subject=st.text(min_size=0, max_size=200),
        body=st.text(min_size=0, max_size=500),
        email_type=st.sampled_from(['financial', 'spam', 'ambiguous_accept', 'ambiguous_reject'])
    )
    @settings(max_examples=20)
    def test_filter_method_logging(
        self, 
        subject: str, 
        body: str,
        email_type: str
    ):
        """
        **Validates: Requirements 13.7**
        
        Property 33: Filter Method Logging
        
        For any processed email, the log entry must contain the filtering method used
        (auto_reject, auto_accept, or ai_verified).
        
        This property verifies that:
        1. Every email that passes through the filter has a filter_method logged
        2. The filter_method is one of: auto_reject, auto_accept, or ai_verified
        3. The logged method matches the actual filtering path taken
        4. Auto-accepted emails have filter_method = AUTO_ACCEPT
        5. AI-verified emails have filter_method = AI_VERIFIED
        6. Auto-rejected emails don't return data (None), so no filter_method is needed
        """
        # Setup: Create mock DeepSeek client
        mock_deepseek_client = Mock(spec=DeepSeekClient)
        
        # Configure mock based on email type
        if email_type == 'ambiguous_accept':
            mock_deepseek_client.verify_financial_email.return_value = True
        else:
            mock_deepseek_client.verify_financial_email.return_value = False
        
        # Create filter with the mock client
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        # Construct email data based on type
        if email_type == 'financial':
            # Add financial keyword to trigger auto-accept
            # Use clean text to avoid accidental spam keywords
            clean_subject = ''.join(c for c in subject if c.isalnum() or c.isspace())
            clean_body = ''.join(c for c in body if c.isalnum() or c.isspace())
            email_data = {
                'subject': f"{clean_subject} invoice payment receipt",
                'sender': 'billing@example.com',
                'body': f"{clean_body} order confirmation"
            }
        elif email_type == 'spam':
            # Add spam keyword to trigger auto-reject
            clean_subject = ''.join(c for c in subject if c.isalnum() or c.isspace())
            clean_body = ''.join(c for c in body if c.isalnum() or c.isspace())
            email_data = {
                'subject': f"{clean_subject} unsubscribe newsletter",
                'sender': 'marketing@example.com',
                'body': f"{clean_body} click here"
            }
        else:
            # Ambiguous email (no clear keywords)
            # Use neutral text that doesn't contain financial or spam keywords
            clean_subject = ''.join(c for c in subject if c.isalnum() or c.isspace())
            clean_body = ''.join(c for c in body if c.isalnum() or c.isspace())
            email_data = {
                'subject': clean_subject,
                'sender': 'test@example.com',
                'body': clean_body
            }
        
        # Act: Filter the email
        result = financial_filter.filter_email(email_data)
        
        # Assert: Verify filter_method is logged correctly
        if email_type == 'financial':
            # Financial keywords -> auto-accept
            assert result is not None, (
                "Email with financial keywords should be auto-accepted"
            )
            assert 'filter_method' in result, (
                "Accepted email must have filter_method field"
            )
            assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value, (
                f"Financial keyword email should have filter_method=AUTO_ACCEPT, "
                f"but got {result['filter_method']}"
            )
            assert result.get('is_financial') is True, (
                "Accepted email must have is_financial=True"
            )
            
        elif email_type == 'spam':
            # Spam keywords -> auto-reject
            assert result is None, (
                "Email with spam keywords should be auto-rejected"
            )
            # Auto-rejected emails return None, so no filter_method is logged in the return value
            # This is correct behavior - rejected emails don't need filter_method in return
            
        elif email_type == 'ambiguous_accept':
            # Ambiguous email accepted by AI
            # Check if email actually reached AI layer (no keywords)
            combined_text = f"{email_data['subject']} {email_data['sender']} {email_data['body']}".lower()
            
            has_financial_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.FINANCIAL_KEYWORDS
            )
            
            has_spam_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
            )
            
            if not has_financial_keywords and not has_spam_keywords:
                # Truly ambiguous - should be AI verified
                assert result is not None, (
                    "Ambiguous email accepted by AI should return email data"
                )
                assert 'filter_method' in result, (
                    "AI-accepted email must have filter_method field"
                )
                assert result['filter_method'] == FilterMethod.AI_VERIFIED.value, (
                    f"AI-verified email should have filter_method=AI_VERIFIED, "
                    f"but got {result['filter_method']}"
                )
                assert result.get('is_financial') is True, (
                    "AI-accepted email must have is_financial=True"
                )
                
        elif email_type == 'ambiguous_reject':
            # Ambiguous email rejected by AI
            # Check if email actually reached AI layer (no keywords)
            combined_text = f"{email_data['subject']} {email_data['sender']} {email_data['body']}".lower()
            
            has_financial_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.FINANCIAL_KEYWORDS
            )
            
            has_spam_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
            )
            
            if not has_financial_keywords and not has_spam_keywords:
                # Truly ambiguous - should be AI rejected
                assert result is None, (
                    "Ambiguous email rejected by AI should return None"
                )
                # AI-rejected emails return None, so no filter_method in return value
    
    @given(
        financial_keyword=st.sampled_from([
            "receipt", "invoice", "bill", "payment", "transaction",
            "order confirmation", "purchase", "statement", "total amount", "amount due"
        ]),
        extra_text=st.text(min_size=0, max_size=100)
    )
    @settings(max_examples=20)
    def test_auto_accept_always_logs_filter_method(
        self, 
        financial_keyword: str, 
        extra_text: str
    ):
        """
        **Validates: Requirements 13.7**
        
        Property 33: Filter Method Logging (Auto-Accept Path)
        
        For any email that is auto-accepted (contains financial keywords and no marketing keywords),
        the returned email data must contain filter_method = AUTO_ACCEPT.
        
        This property verifies that:
        1. All auto-accepted emails have filter_method field
        2. The filter_method value is exactly AUTO_ACCEPT
        3. This is consistent across all financial keyword variations
        
        Note: If extra_text contains marketing keywords, the email will be auto-rejected
        (Layer 1 takes precedence), which is correct behavior per the three-layer design.
        """
        # Create filter
        financial_filter = FinancialFilter(deepseek_client=None)
        
        # Create email with financial keyword
        email_data = {
            'subject': f"{extra_text} {financial_keyword}",
            'sender': 'sender@example.com',
            'body': 'Email body content'
        }
        
        # Check if extra_text contains marketing keywords
        combined_text = f"{extra_text} {financial_keyword} sender@example.com Email body content".lower()
        has_marketing_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
        )
        
        # Act: Filter the email
        result = financial_filter.filter_email(email_data)
        
        # Assert: Behavior depends on whether marketing keywords are present
        if has_marketing_keywords:
            # Layer 1 (Auto-Reject) takes precedence over Layer 2 (Auto-Accept)
            assert result is None, (
                f"Email with both financial keyword '{financial_keyword}' and marketing keywords "
                f"should be auto-rejected (Layer 1 takes precedence)"
            )
        else:
            # No marketing keywords -> should be auto-accepted
            assert result is not None, (
                f"Email with financial keyword '{financial_keyword}' (and no marketing keywords) "
                f"should be auto-accepted"
            )
            
            assert 'filter_method' in result, (
                "Auto-accepted email must have filter_method field"
            )
            
            assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value, (
                f"Auto-accepted email should have filter_method=AUTO_ACCEPT, "
                f"but got {result['filter_method']}"
            )
            
            assert result.get('is_financial') is True, (
                "Auto-accepted email must have is_financial=True"
            )
    
    @given(
        subject=st.text(min_size=0, max_size=200),
        body=st.text(min_size=0, max_size=500)
    )
    @settings(max_examples=20)
    def test_ai_verified_always_logs_filter_method(
        self, 
        subject: str, 
        body: str
    ):
        """
        **Validates: Requirements 13.7**
        
        Property 33: Filter Method Logging (AI Verification Path)
        
        For any email that is accepted via AI verification,
        the returned email data must contain filter_method = AI_VERIFIED.
        
        This property verifies that:
        1. All AI-verified emails have filter_method field
        2. The filter_method value is exactly AI_VERIFIED
        3. This is consistent across all AI-verified emails
        """
        # Setup: Create mock that always returns True
        mock_deepseek_client = Mock(spec=DeepSeekClient)
        mock_deepseek_client.verify_financial_email.return_value = True
        
        # Create filter with the mock client
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        # Create ambiguous email (no clear keywords)
        email_data = {
            'subject': subject,
            'sender': 'test@example.com',
            'body': body
        }
        
        # Check if email would be auto-accepted or auto-rejected by keywords
        combined_text = f"{subject} test@example.com {body}".lower()
        
        has_financial_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.FINANCIAL_KEYWORDS
        )
        
        has_spam_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
        )
        
        # Only test truly ambiguous emails that reach AI layer
        if not has_financial_keywords and not has_spam_keywords:
            # Act: Filter the email
            result = financial_filter.filter_email(email_data)
            
            # Assert: Must be accepted with AI_VERIFIED filter_method
            assert result is not None, (
                "Email accepted by AI should return email data"
            )
            
            assert 'filter_method' in result, (
                "AI-verified email must have filter_method field"
            )
            
            assert result['filter_method'] == FilterMethod.AI_VERIFIED.value, (
                f"AI-verified email should have filter_method=AI_VERIFIED, "
                f"but got {result['filter_method']}"
            )
            
            assert result.get('is_financial') is True, (
                "AI-verified email must have is_financial=True"
            )

    # Feature: finmatcher-v2-upgrade, Property 34: Financial Email Processing
    @given(
        has_financial_keyword=st.booleans(),
        has_marketing_keyword=st.booleans()
    )
    @settings(max_examples=20)
    def test_financial_email_processing(
        self, 
        has_financial_keyword: bool, 
        has_marketing_keyword: bool
    ):
        """
        **Validates: Requirements 13.10**
        
        Property 34: Financial Email Processing
        
        For any email that passes the Financial_Filter, it must be sent to the matching engine;
        all rejected emails must be discarded.
        
        This property verifies that:
        1. Emails that pass the filter (return non-None) are processed
        2. Rejected emails (return None) are discarded
        3. The system never processes non-financial emails
        4. The filtering behavior is consistent across all email inputs
        """
        # Setup: Create mock DeepSeek client
        mock_deepseek_client = Mock(spec=DeepSeekClient)
        # For ambiguous emails, randomly accept or reject
        mock_deepseek_client.verify_financial_email.return_value = True
        
        # Create filter with the mock client
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        # Construct email subject based on keywords
        subject = ""
        if has_financial_keyword:
            subject += "invoice "
        if has_marketing_keyword:
            subject += "unsubscribe "
        if not has_financial_keyword and not has_marketing_keyword:
            subject = "ambiguous email subject"
        
        email_data = {
            'subject': subject,
            'sender': "test@example.com",
            'body': "Test email body"
        }
        
        # Act: Filter the email
        result = financial_filter.filter_email(email_data)
        
        # Assert: Verify processing behavior
        if has_marketing_keyword:
            # Marketing keyword present -> must be rejected (Layer 1: Auto-Reject)
            assert result is None, (
                "Marketing emails must be rejected and discarded, not processed"
            )
        elif has_financial_keyword:
            # Financial keyword present (and no marketing) -> must be accepted (Layer 2: Auto-Accept)
            assert result is not None, (
                "Financial emails must pass the filter and be processed"
            )
            assert result.get('is_financial') is True, (
                "Accepted emails must have is_financial=True"
            )
            # Verify the email data is returned for processing
            assert 'subject' in result, "Processed email must contain subject"
            assert 'sender' in result, "Processed email must contain sender"
            assert 'body' in result, "Processed email must contain body"
        else:
            # Ambiguous email -> depends on AI verification (Layer 3)
            # In this test, AI returns True, so email should be accepted
            assert result is not None, (
                "Ambiguous emails accepted by AI must be processed"
            )
            assert result.get('is_financial') is True, (
                "AI-accepted emails must have is_financial=True"
            )
            assert result.get('filter_method') == FilterMethod.AI_VERIFIED.value, (
                "AI-accepted emails must have filter_method=AI_VERIFIED"
            )
    
    @given(
        email_type=st.sampled_from(['financial', 'marketing', 'ambiguous_accept', 'ambiguous_reject']),
        subject_text=st.text(min_size=0, max_size=100),
        body_text=st.text(min_size=0, max_size=200)
    )
    @settings(max_examples=20)
    def test_only_passed_emails_are_processed(
        self, 
        email_type: str,
        subject_text: str,
        body_text: str
    ):
        """
        **Validates: Requirements 13.10**
        
        Property 34: Financial Email Processing (Comprehensive)
        
        For any email, only those that pass the Financial_Filter (return non-None)
        should be processed by the matching engine. All rejected emails (return None)
        must be discarded.
        
        This property verifies that:
        1. The filter returns non-None only for financial emails
        2. The filter returns None for all non-financial emails
        3. Returned email data contains all necessary fields for processing
        4. The is_financial flag is always True for passed emails
        """
        # Setup: Create mock DeepSeek client
        mock_deepseek_client = Mock(spec=DeepSeekClient)
        
        # Configure mock based on email type
        if email_type == 'ambiguous_accept':
            mock_deepseek_client.verify_financial_email.return_value = True
        else:
            mock_deepseek_client.verify_financial_email.return_value = False
        
        # Create filter with the mock client
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        # Construct email data based on type
        if email_type == 'financial':
            # Add financial keyword to trigger auto-accept
            clean_subject = ''.join(c for c in subject_text if c.isalnum() or c.isspace())
            clean_body = ''.join(c for c in body_text if c.isalnum() or c.isspace())
            email_data = {
                'subject': f"{clean_subject} invoice receipt",
                'sender': 'billing@example.com',
                'body': f"{clean_body} payment confirmation"
            }
        elif email_type == 'marketing':
            # Add marketing keyword to trigger auto-reject
            clean_subject = ''.join(c for c in subject_text if c.isalnum() or c.isspace())
            clean_body = ''.join(c for c in body_text if c.isalnum() or c.isspace())
            email_data = {
                'subject': f"{clean_subject} unsubscribe",
                'sender': 'marketing@example.com',
                'body': f"{clean_body} newsletter"
            }
        else:
            # Ambiguous email (no clear keywords)
            clean_subject = ''.join(c for c in subject_text if c.isalnum() or c.isspace())
            clean_body = ''.join(c for c in body_text if c.isalnum() or c.isspace())
            email_data = {
                'subject': clean_subject,
                'sender': 'test@example.com',
                'body': clean_body
            }
        
        # Act: Filter the email
        result = financial_filter.filter_email(email_data)
        
        # Assert: Verify processing behavior
        if email_type == 'financial':
            # Financial emails must pass the filter
            assert result is not None, (
                "Financial emails must pass the filter and be processed"
            )
            assert result.get('is_financial') is True, (
                "Passed emails must have is_financial=True"
            )
            # Verify all necessary fields are present for processing
            assert 'subject' in result, "Processed email must contain subject"
            assert 'sender' in result, "Processed email must contain sender"
            assert 'body' in result, "Processed email must contain body"
            assert 'filter_method' in result, "Processed email must contain filter_method"
            
        elif email_type == 'marketing':
            # Marketing emails must be rejected and discarded
            assert result is None, (
                "Marketing emails must be rejected and discarded, not processed"
            )
            
        elif email_type == 'ambiguous_accept':
            # Ambiguous emails accepted by AI must pass the filter
            # Check if email actually reached AI layer (no keywords)
            combined_text = f"{email_data['subject']} {email_data['sender']} {email_data['body']}".lower()
            
            has_financial_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.FINANCIAL_KEYWORDS
            )
            
            has_spam_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
            )
            
            if not has_financial_keywords and not has_spam_keywords:
                # Truly ambiguous - should be AI verified and accepted
                assert result is not None, (
                    "Ambiguous emails accepted by AI must be processed"
                )
                assert result.get('is_financial') is True, (
                    "AI-accepted emails must have is_financial=True"
                )
                assert result.get('filter_method') == FilterMethod.AI_VERIFIED.value, (
                    "AI-accepted emails must have filter_method=AI_VERIFIED"
                )
                
        elif email_type == 'ambiguous_reject':
            # Ambiguous emails rejected by AI must be discarded
            # Check if email actually reached AI layer (no keywords)
            combined_text = f"{email_data['subject']} {email_data['sender']} {email_data['body']}".lower()
            
            has_financial_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.FINANCIAL_KEYWORDS
            )
            
            has_spam_keywords = any(
                keyword.lower() in combined_text 
                for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
            )
            
            if not has_financial_keywords and not has_spam_keywords:
                # Truly ambiguous - should be AI rejected and discarded
                assert result is None, (
                    "Ambiguous emails rejected by AI must be discarded, not processed"
                )
    
    @given(
        financial_keyword=st.sampled_from([
            "receipt", "invoice", "bill", "payment", "transaction",
            "order confirmation", "purchase", "statement", "total amount", "amount due"
        ]),
        extra_text=st.text(min_size=0, max_size=100)
    )
    @settings(max_examples=20)
    def test_financial_emails_always_processed(
        self, 
        financial_keyword: str,
        extra_text: str
    ):
        """
        **Validates: Requirements 13.10**
        
        Property 34: Financial Email Processing (Financial Emails)
        
        For any email containing financial keywords (and no marketing keywords),
        the email must pass the filter and be available for processing by the matching engine.
        
        This property verifies that:
        1. All emails with financial keywords (without marketing keywords) pass the filter
        2. The returned data contains all necessary fields
        3. The is_financial flag is set to True
        4. The filter_method indicates the filtering path
        
        Note: If extra_text contains marketing keywords, the email will be auto-rejected
        (Layer 1 takes precedence), which is correct behavior per the three-layer design.
        """
        # Create filter without DeepSeek client (not needed for auto-accept)
        financial_filter = FinancialFilter(deepseek_client=None)
        
        # Create email with financial keyword
        email_data = {
            'subject': f"{extra_text} {financial_keyword}",
            'sender': 'sender@example.com',
            'body': 'Email body content'
        }
        
        # Check if extra_text contains marketing keywords
        combined_text = f"{extra_text} {financial_keyword} sender@example.com Email body content".lower()
        has_marketing_keywords = any(
            keyword.lower() in combined_text 
            for keyword in financial_filter.MARKETING_SPAM_KEYWORDS
        )
        
        # Act: Filter the email
        result = financial_filter.filter_email(email_data)
        
        # Assert: Behavior depends on whether marketing keywords are present
        if has_marketing_keywords:
            # Layer 1 (Auto-Reject) takes precedence over Layer 2 (Auto-Accept)
            # This is correct behavior per the three-layer design
            assert result is None, (
                f"Email with both financial keyword '{financial_keyword}' and marketing keywords "
                f"must be rejected (Layer 1 takes precedence)"
            )
        else:
            # No marketing keywords -> financial keyword should trigger auto-accept
            assert result is not None, (
                f"Email with financial keyword '{financial_keyword}' (and no marketing keywords) "
                f"must pass the filter"
            )
            
            assert result.get('is_financial') is True, (
                "Financial emails must have is_financial=True"
            )
            
            # Verify all necessary fields are present for processing
            assert 'subject' in result, "Processed email must contain subject"
            assert 'sender' in result, "Processed email must contain sender"
            assert 'body' in result, "Processed email must contain body"
            assert 'filter_method' in result, "Processed email must contain filter_method"
            
            assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value, (
                "Financial keyword emails must use AUTO_ACCEPT method"
            )
    
    @given(
        marketing_keyword=st.sampled_from([
            "unsubscribe", "newsletter", "discount", "sale", "offer",
            "limited time", "click here", "subscribe", "job offer", "resume", "meeting"
        ]),
        extra_text=st.text(min_size=0, max_size=100)
    )
    @settings(max_examples=20)
    def test_non_financial_emails_never_processed(
        self, 
        marketing_keyword: str,
        extra_text: str
    ):
        """
        **Validates: Requirements 13.10**
        
        Property 34: Financial Email Processing (Non-Financial Emails)
        
        For any email containing marketing/spam keywords, the email must be rejected
        and never processed by the matching engine.
        
        This property verifies that:
        1. All emails with marketing/spam keywords are rejected
        2. The filter returns None (discard)
        3. No email data is passed to the matching engine
        4. The system never processes non-financial emails
        """
        # Create filter without DeepSeek client (not needed for auto-reject)
        financial_filter = FinancialFilter(deepseek_client=None)
        
        # Create email with marketing keyword
        email_data = {
            'subject': f"{extra_text} {marketing_keyword}",
            'sender': 'marketing@example.com',
            'body': 'Email body content'
        }
        
        # Act: Filter the email
        result = financial_filter.filter_email(email_data)
        
        # Assert: Email must be rejected and discarded
        assert result is None, (
            f"Email with marketing keyword '{marketing_keyword}' must be rejected and discarded"
        )

