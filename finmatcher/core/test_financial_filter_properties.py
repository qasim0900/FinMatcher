"""
Property-based tests for Financial Filter.

This module contains property-based tests using Hypothesis to verify
universal properties of the financial email filtering system.

Testing Framework: Hypothesis (Python)
Feature: finmatcher-v2-upgrade
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any

from finmatcher.core.financial_filter import FinancialFilter, FilterMethod


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=20)
settings.load_profile("finmatcher")


# Strategy for generating email data
def email_data_strategy(keyword: str, extra_text: str) -> Dict[str, Any]:
    """Generate email data with keyword in subject, sender, or body."""
    return {
        'subject': f"{extra_text} {keyword} {extra_text}",
        'sender': "sender@example.com",
        'body': "Email body content"
    }


class TestFinancialFilterAutoReject:
    """
    Property tests for auto-reject functionality.
    
    Feature: finmatcher-v2-upgrade
    Property 28: Auto-Reject for Marketing/Spam Keywords
    Validates: Requirements 13.2
    """
    
    @given(
        keyword=st.sampled_from([
            "unsubscribe",
            "newsletter",
            "discount",
            "sale",
            "offer",
            "limited time",
            "click here",
            "subscribe",
            "job offer",
            "resume",
            "meeting"
        ]),
        extra_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
            min_size=0,
            max_size=50
        )
    )
    @settings(max_examples=20)
    def test_auto_reject_marketing_keywords_in_subject(self, keyword: str, extra_text: str):
        """
        Property 28: Auto-Reject for Marketing/Spam Keywords (Subject).
        
        For any email where the subject contains a marketing/spam keyword,
        the Financial_Filter must reject it without calling the DeepSeek_API.
        
        Validates: Requirements 13.2
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': f"{extra_text} {keyword} {extra_text}",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            f"Email with marketing/spam keyword '{keyword}' in subject "
            f"should be auto-rejected but was accepted"
        )
        
        # Verify no API call was made (auto-reject should be fast)
        stats = financial_filter.get_statistics()
        assert stats['auto_rejected'] == 1, (
            f"Email should be counted as auto-rejected"
        )
        assert stats['ai_verified'] == 0, (
            f"No AI verification should occur for marketing/spam keywords"
        )
    
    @given(
        keyword=st.sampled_from([
            "unsubscribe",
            "newsletter",
            "discount",
            "sale",
            "offer",
            "limited time",
            "click here",
            "subscribe",
            "job offer",
            "resume",
            "meeting"
        ]),
        extra_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
            min_size=0,
            max_size=50
        )
    )
    @settings(max_examples=20)
    def test_auto_reject_marketing_keywords_in_sender(self, keyword: str, extra_text: str):
        """
        Property 28: Auto-Reject for Marketing/Spam Keywords (Sender).
        
        For any email where the sender contains a marketing/spam keyword,
        the Financial_Filter must reject it without calling the DeepSeek_API.
        
        Validates: Requirements 13.2
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Regular subject",
            'sender': f"{extra_text}{keyword}{extra_text}@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            f"Email with marketing/spam keyword '{keyword}' in sender "
            f"should be auto-rejected but was accepted"
        )
        
        # Verify no API call was made
        stats = financial_filter.get_statistics()
        assert stats['auto_rejected'] == 1
        assert stats['ai_verified'] == 0
    
    @given(
        keyword=st.sampled_from([
            "unsubscribe",
            "newsletter",
            "discount",
            "sale",
            "offer",
            "limited time",
            "click here",
            "subscribe",
            "job offer",
            "resume",
            "meeting"
        ]),
        extra_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
            min_size=0,
            max_size=50
        )
    )
    @settings(max_examples=20)
    def test_auto_reject_marketing_keywords_in_body(self, keyword: str, extra_text: str):
        """
        Property 28: Auto-Reject for Marketing/Spam Keywords (Body).
        
        For any email where the body contains a marketing/spam keyword,
        the Financial_Filter must reject it without calling the DeepSeek_API.
        
        Validates: Requirements 13.2
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Regular subject",
            'sender': "sender@example.com",
            'body': f"{extra_text} {keyword} {extra_text}"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            f"Email with marketing/spam keyword '{keyword}' in body "
            f"should be auto-rejected but was accepted"
        )
        
        # Verify no API call was made
        stats = financial_filter.get_statistics()
        assert stats['auto_rejected'] == 1
        assert stats['ai_verified'] == 0
    
    @given(
        keyword=st.sampled_from([
            "unsubscribe",
            "newsletter",
            "discount",
            "sale",
            "offer",
            "limited time",
            "click here",
            "subscribe",
            "job offer",
            "resume",
            "meeting"
        ]),
        case_variant=st.sampled_from([
            lambda k: k.upper(),
            lambda k: k.lower(),
            lambda k: k.title(),
            lambda k: k.capitalize()
        ])
    )
    @settings(max_examples=20)
    def test_auto_reject_case_insensitive(self, keyword: str, case_variant):
        """
        Property 28: Auto-Reject is Case-Insensitive.
        
        For any email with marketing/spam keywords in any case variation,
        the Financial_Filter must reject it.
        
        Validates: Requirements 13.2
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        keyword_variant = case_variant(keyword)
        email_data = {
            'subject': f"Check this {keyword_variant} out",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            f"Email with marketing/spam keyword '{keyword_variant}' "
            f"(case variant of '{keyword}') should be auto-rejected"
        )
    
    @given(
        keywords=st.lists(
            st.sampled_from([
                "unsubscribe",
                "newsletter",
                "discount",
                "sale",
                "offer",
                "limited time",
                "click here",
                "subscribe",
                "job offer",
                "resume",
                "meeting"
            ]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=20)
    def test_auto_reject_multiple_keywords(self, keywords):
        """
        Property 28: Auto-Reject with Multiple Keywords.
        
        For any email containing one or more marketing/spam keywords,
        the Financial_Filter must reject it.
        
        Validates: Requirements 13.2
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        subject = " ".join(keywords)
        email_data = {
            'subject': subject,
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            f"Email with multiple marketing/spam keywords {keywords} "
            f"should be auto-rejected"
        )
        
        # Verify statistics
        stats = financial_filter.get_statistics()
        assert stats['auto_rejected'] == 1
        assert stats['ai_verified'] == 0
    
    def test_auto_reject_returns_none(self):
        """
        Property 28: Auto-Reject Returns None.
        
        For any email that is auto-rejected, the filter must return None
        (not the email data).
        
        Validates: Requirements 13.2, 13.9
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Unsubscribe from our newsletter",
            'sender': "marketing@example.com",
            'body': "Click here for a limited time offer"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            "Auto-rejected emails must return None"
        )
    
    def test_auto_reject_logs_filter_method(self):
        """
        Property 28: Auto-Reject Logs Filter Method.
        
        For any email that is auto-rejected, the filter must log the
        rejection with filter_method = "auto_reject".
        
        Validates: Requirements 13.2, 13.7
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Newsletter subscription",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None
        
        # Verify statistics show auto-reject
        stats = financial_filter.get_statistics()
        assert stats['auto_rejected'] == 1, (
            "Auto-rejected email must be logged in statistics"
        )


class TestFinancialFilterAutoAccept:
    """
    Property tests for auto-accept functionality.
    
    Feature: finmatcher-v2-upgrade
    Property 29: Auto-Accept for Financial Keywords
    Validates: Requirements 13.3
    """
    
    # Spam keywords to exclude from generated text
    SPAM_KEYWORDS_LOWER = [
        'unsubscribe', 'newsletter', 'discount', 'sale', 'offer',
        'limited', 'time', 'subscribe', 'click', 'here', 'job', 
        'resume', 'meeting', 'promotion', 'deal', 'coupon',
        'free', 'shipping', 'off'
    ]
    
    @staticmethod
    def text_without_spam():
        """Generate text that doesn't contain spam keywords."""
        return st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=0,
            max_size=20
        ).filter(lambda t: not any(
            spam in t.lower() 
            for spam in TestFinancialFilterAutoAccept.SPAM_KEYWORDS_LOWER
        ))
    
    @given(
        keyword=st.sampled_from([
            "receipt",
            "invoice",
            "bill",
            "payment",
            "transaction",
            "purchase",
            "statement"
        ]),
        prefix=text_without_spam(),
        suffix=text_without_spam()
    )
    @settings(max_examples=20)
    def test_auto_accept_financial_keywords_in_subject(self, keyword: str, prefix: str, suffix: str):
        """
        Property 29: Auto-Accept for Financial Keywords (Subject).
        
        For any email where the subject contains a financial keyword,
        the Financial_Filter must accept it without calling the DeepSeek_API.
        
        Validates: Requirements 13.3
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': f"{prefix} {keyword} {suffix}",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            f"Email with financial keyword '{keyword}' in subject "
            f"should be auto-accepted but was rejected"
        )
        assert result['is_financial'] is True, (
            f"Auto-accepted email must be marked as financial"
        )
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value, (
            f"Filter method must be 'auto_accept' for financial keywords"
        )
        
        # Verify no API call was made (auto-accept should be fast)
        stats = financial_filter.get_statistics()
        assert stats['auto_accepted'] == 1, (
            f"Email should be counted as auto-accepted"
        )
        assert stats['ai_verified'] == 0, (
            f"No AI verification should occur for financial keywords"
        )
    
    @given(
        keyword=st.sampled_from([
            "receipt",
            "invoice",
            "bill",
            "payment",
            "transaction",
            "purchase",
            "statement"
        ]),
        prefix=text_without_spam(),
        suffix=text_without_spam()
    )
    @settings(max_examples=20)
    def test_auto_accept_financial_keywords_in_sender(self, keyword: str, prefix: str, suffix: str):
        """
        Property 29: Auto-Accept for Financial Keywords (Sender).
        
        For any email where the sender contains a financial keyword,
        the Financial_Filter must accept it without calling the DeepSeek_API.
        
        Validates: Requirements 13.3
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Regular subject",
            'sender': f"{prefix}{keyword}{suffix}@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            f"Email with financial keyword '{keyword}' in sender "
            f"should be auto-accepted but was rejected"
        )
        assert result['is_financial'] is True
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value
        
        # Verify no API call was made
        stats = financial_filter.get_statistics()
        assert stats['auto_accepted'] == 1
        assert stats['ai_verified'] == 0
    
    @given(
        keyword=st.sampled_from([
            "receipt",
            "invoice",
            "bill",
            "payment",
            "transaction",
            "purchase",
            "statement"
        ]),
        prefix=text_without_spam(),
        suffix=text_without_spam()
    )
    @settings(max_examples=20)
    def test_auto_accept_financial_keywords_in_body(self, keyword: str, prefix: str, suffix: str):
        """
        Property 29: Auto-Accept for Financial Keywords (Body).
        
        For any email where the body contains a financial keyword,
        the Financial_Filter must accept it without calling the DeepSeek_API.
        
        Validates: Requirements 13.3
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Regular subject",
            'sender': "sender@example.com",
            'body': f"{prefix} {keyword} {suffix}"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            f"Email with financial keyword '{keyword}' in body "
            f"should be auto-accepted but was rejected"
        )
        assert result['is_financial'] is True
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value
        
        # Verify no API call was made
        stats = financial_filter.get_statistics()
        assert stats['auto_accepted'] == 1
        assert stats['ai_verified'] == 0
    
    @given(
        keyword=st.sampled_from([
            "receipt",
            "invoice",
            "bill",
            "payment",
            "transaction",
            "order confirmation",
            "purchase",
            "statement",
            "total amount",
            "amount due"
        ]),
        case_variant=st.sampled_from([
            lambda k: k.upper(),
            lambda k: k.lower(),
            lambda k: k.title(),
            lambda k: k.capitalize()
        ])
    )
    @settings(max_examples=20)
    def test_auto_accept_case_insensitive(self, keyword: str, case_variant):
        """
        Property 29: Auto-Accept is Case-Insensitive.
        
        For any email with financial keywords in any case variation,
        the Financial_Filter must accept it.
        
        Validates: Requirements 13.3
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        keyword_variant = case_variant(keyword)
        email_data = {
            'subject': f"Your {keyword_variant} is ready",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            f"Email with financial keyword '{keyword_variant}' "
            f"(case variant of '{keyword}') should be auto-accepted"
        )
        assert result['is_financial'] is True
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value
    
    @given(
        keywords=st.lists(
            st.sampled_from([
                "receipt",
                "invoice",
                "bill",
                "payment",
                "transaction",
                "order confirmation",
                "purchase",
                "statement",
                "total amount",
                "amount due"
            ]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=20)
    def test_auto_accept_multiple_keywords(self, keywords):
        """
        Property 29: Auto-Accept with Multiple Keywords.
        
        For any email containing one or more financial keywords,
        the Financial_Filter must accept it.
        
        Validates: Requirements 13.3
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        subject = " ".join(keywords)
        email_data = {
            'subject': subject,
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            f"Email with multiple financial keywords {keywords} "
            f"should be auto-accepted"
        )
        assert result['is_financial'] is True
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value
        
        # Verify statistics
        stats = financial_filter.get_statistics()
        assert stats['auto_accepted'] == 1
        assert stats['ai_verified'] == 0
    
    def test_auto_accept_returns_email_data(self):
        """
        Property 29: Auto-Accept Returns Email Data.
        
        For any email that is auto-accepted, the filter must return the
        email data dict (not None).
        
        Validates: Requirements 13.3, 13.9
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Your receipt from Amazon",
            'sender': "orders@amazon.com",
            'body': "Thank you for your purchase"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            "Auto-accepted emails must return email data dict"
        )
        assert isinstance(result, dict), (
            "Result must be a dictionary"
        )
        assert 'subject' in result
        assert 'sender' in result
        assert 'body' in result
    
    def test_auto_accept_marks_as_financial(self):
        """
        Property 29: Auto-Accept Marks Email as Financial.
        
        For any email that is auto-accepted, the filter must set
        is_financial = True in the returned data.
        
        Validates: Requirements 13.3, 13.9
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Invoice #12345",
            'sender': "billing@company.com",
            'body': "Your invoice is attached"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None
        assert 'is_financial' in result, (
            "Result must contain 'is_financial' field"
        )
        assert result['is_financial'] is True, (
            "Auto-accepted emails must be marked as financial"
        )
    
    def test_auto_accept_logs_filter_method(self):
        """
        Property 29: Auto-Accept Logs Filter Method.
        
        For any email that is auto-accepted, the filter must log the
        acceptance with filter_method = "auto_accept".
        
        Validates: Requirements 13.3, 13.7
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Payment confirmation",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None
        assert 'filter_method' in result, (
            "Result must contain 'filter_method' field"
        )
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value, (
            "Filter method must be 'auto_accept'"
        )
        
        # Verify statistics show auto-accept
        stats = financial_filter.get_statistics()
        assert stats['auto_accepted'] == 1, (
            "Auto-accepted email must be logged in statistics"
        )
    
    def test_auto_accept_no_api_call(self):
        """
        Property 29: Auto-Accept Does Not Call API.
        
        For any email that is auto-accepted, the filter must NOT call
        the DeepSeek API (cost optimization).
        
        Validates: Requirements 13.3, 13.8
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': "Your bill is ready",
            'sender': "billing@example.com",
            'body': "Please review your statement"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None
        
        # Verify no AI verification occurred
        stats = financial_filter.get_statistics()
        assert stats['ai_verified'] == 0, (
            "Auto-accept must not trigger AI verification"
        )
        assert stats['auto_accepted'] == 1, (
            "Email must be counted as auto-accepted"
        )
    
    @given(
        financial_keyword=st.sampled_from([
            "receipt",
            "invoice",
            "bill",
            "payment"
        ]),
        spam_keyword=st.sampled_from([
            "unsubscribe",
            "newsletter",
            "discount"
        ])
    )
    @settings(max_examples=50)
    def test_auto_reject_takes_precedence_over_auto_accept(
        self, 
        financial_keyword: str, 
        spam_keyword: str
    ):
        """
        Property 29: Auto-Reject Takes Precedence.
        
        When an email contains both financial and spam keywords,
        auto-reject must take precedence (Layer 1 before Layer 2).
        
        Validates: Requirements 13.1, 13.2, 13.3
        """
        # Arrange
        financial_filter = FinancialFilter(deepseek_client=None)
        email_data = {
            'subject': f"Your {financial_keyword} - {spam_keyword} now!",
            'sender': "sender@example.com",
            'body': "Email body content"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is None, (
            f"Email with both financial keyword '{financial_keyword}' "
            f"and spam keyword '{spam_keyword}' should be auto-rejected "
            f"(Layer 1 takes precedence over Layer 2)"
        )
        
        # Verify it was auto-rejected, not auto-accepted
        stats = financial_filter.get_statistics()
        assert stats['auto_rejected'] == 1
        assert stats['auto_accepted'] == 0


class TestFinancialFilterAIVerification:
    """
    Property tests for AI verification functionality.
    
    Feature: finmatcher-v2-upgrade
    Property 30: AI Verification for Ambiguous Emails
    Validates: Requirements 13.4
    """
    
    # All keywords to exclude from ambiguous text generation
    ALL_KEYWORDS_LOWER = [
        # Financial keywords
        'receipt', 'invoice', 'bill', 'payment', 'transaction',
        'order', 'confirmation', 'purchase', 'statement', 'total',
        'amount', 'due', 'received', 'account',
        # Spam keywords
        'unsubscribe', 'newsletter', 'discount', 'sale', 'offer',
        'limited', 'time', 'subscribe', 'click', 'here', 'job',
        'resume', 'meeting', 'promotion', 'deal', 'coupon',
        'free', 'shipping', 'off', '%'
    ]
    
    @staticmethod
    def ambiguous_text_strategy():
        """
        Generate text that doesn't contain financial or spam keywords.
        
        This ensures the email is truly ambiguous and will trigger AI verification.
        """
        return st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                blacklist_characters='%'
            ),
            min_size=5,
            max_size=50
        ).filter(lambda t: not any(
            keyword in t.lower()
            for keyword in TestFinancialFilterAIVerification.ALL_KEYWORDS_LOWER
        ))
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy(),
        ai_decision=st.booleans()
    )
    @settings(max_examples=20)
    def test_ai_verification_for_ambiguous_emails(
        self,
        subject: str,
        body: str,
        ai_decision: bool
    ):
        """
        Property 30: AI Verification for Ambiguous Emails.
        
        For any email that cannot be filtered by rules (no financial or
        marketing keywords), the Financial_Filter must send the email to
        the DeepSeek_API for verification.
        
        Validates: Requirements 13.4
        """
        # Arrange - Create mock DeepSeek client
        from unittest.mock import Mock
        
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(return_value=ai_decision)
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        email_data = {
            'subject': subject,
            'sender': "sender@example.com",
            'body': body
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert - AI verification must be called for ambiguous emails
        mock_deepseek.verify_financial_email.assert_called_once()
        
        # Verify the call was made with subject and body
        call_args = mock_deepseek.verify_financial_email.call_args
        assert call_args[0][0] == subject or call_args[1].get('subject') == subject, (
            "AI verification must be called with email subject"
        )
        assert call_args[0][1] == body or call_args[1].get('body') == body, (
            "AI verification must be called with email body"
        )
        
        # Verify the filter respects AI decision
        if ai_decision:
            # AI says it's financial - should be accepted
            assert result is not None, (
                f"Email verified as financial by AI should be accepted"
            )
            assert result['is_financial'] is True, (
                "AI-verified email must be marked as financial"
            )
            assert result['filter_method'] == FilterMethod.AI_VERIFIED.value, (
                "Filter method must be 'ai_verified' for AI-verified emails"
            )
            
            # Verify statistics
            stats = financial_filter.get_statistics()
            assert stats['ai_verified'] == 1, (
                "Email should be counted as AI-verified"
            )
            assert stats['auto_accepted'] == 0, (
                "Ambiguous email should not be auto-accepted"
            )
            assert stats['auto_rejected'] == 0, (
                "Ambiguous email should not be auto-rejected"
            )
        else:
            # AI says it's not financial - should be rejected
            assert result is None, (
                f"Email rejected by AI should return None"
            )
            
            # Verify statistics
            stats = financial_filter.get_statistics()
            assert stats['ai_rejected'] == 1, (
                "Email should be counted as AI-rejected"
            )
            assert stats['ai_verified'] == 0, (
                "Rejected email should not be counted as verified"
            )
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=50)
    def test_ai_verification_called_only_for_ambiguous(
        self,
        subject: str,
        body: str
    ):
        """
        Property 30: AI Verification Only for Ambiguous Emails.
        
        For any email that contains clear financial or spam keywords,
        AI verification must NOT be called (cost optimization).
        
        Validates: Requirements 13.4, 13.8
        """
        from unittest.mock import Mock
        
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(return_value=True)
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        # Test 1: Email with financial keyword should NOT call AI
        email_with_financial = {
            'subject': f"{subject} receipt {subject}",
            'sender': "sender@example.com",
            'body': body
        }
        
        result = financial_filter.filter_email(email_with_financial)
        
        # Should be auto-accepted without AI call
        assert result is not None
        assert result['filter_method'] == FilterMethod.AUTO_ACCEPT.value
        assert mock_deepseek.verify_financial_email.call_count == 0, (
            "AI verification should not be called for emails with financial keywords"
        )
        
        # Reset mock
        mock_deepseek.verify_financial_email.reset_mock()
        
        # Test 2: Email with spam keyword should NOT call AI
        email_with_spam = {
            'subject': f"{subject} unsubscribe {subject}",
            'sender': "sender@example.com",
            'body': body
        }
        
        result = financial_filter.filter_email(email_with_spam)
        
        # Should be auto-rejected without AI call
        assert result is None
        assert mock_deepseek.verify_financial_email.call_count == 0, (
            "AI verification should not be called for emails with spam keywords"
        )
    
    def test_ai_verification_without_client_rejects(self):
        """
        Property 30: Conservative Fallback Without AI Client.
        
        For any ambiguous email when no DeepSeek client is available,
        the filter must reject the email (conservative approach).
        
        Validates: Requirements 13.4, 13.6
        """
        # Arrange - No DeepSeek client
        financial_filter = FinancialFilter(deepseek_client=None)
        
        # Ambiguous email (no clear keywords)
        email_data = {
            'subject': "Hello there",
            'sender': "sender@example.com",
            'body': "This is a message about something"
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert - Should be rejected (conservative)
        assert result is None, (
            "Ambiguous email without AI client should be rejected"
        )
        
        # Verify statistics
        stats = financial_filter.get_statistics()
        assert stats['ai_verified'] == 0, (
            "No AI verification should occur without client"
        )
        assert stats['ai_rejected'] == 0, (
            "AI rejection count should be 0 without client"
        )
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=50)
    def test_ai_verification_handles_api_failure(
        self,
        subject: str,
        body: str
    ):
        """
        Property 30: Conservative Fallback on API Failure.
        
        For any ambiguous email where the DeepSeek API fails,
        the filter must reject the email (conservative approach).
        
        Validates: Requirements 13.4, 13.6
        """
        from unittest.mock import Mock
        
        # Arrange - Mock DeepSeek client that raises exception
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(
            side_effect=Exception("API connection failed")
        )
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        email_data = {
            'subject': subject,
            'sender': "sender@example.com",
            'body': body
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert - Should be rejected on API failure
        assert result is None, (
            "Ambiguous email with API failure should be rejected (conservative)"
        )
        
        # Verify AI was attempted
        mock_deepseek.verify_financial_email.assert_called_once()
        
        # Verify statistics
        stats = financial_filter.get_statistics()
        assert stats['ai_verified'] == 0, (
            "Failed AI verification should not count as verified"
        )
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=50)
    def test_ai_verification_logs_filter_method(
        self,
        subject: str,
        body: str
    ):
        """
        Property 30: AI Verification Logs Filter Method.
        
        For any email verified by AI, the filter must set
        filter_method = "ai_verified" in the returned data.
        
        Validates: Requirements 13.4, 13.7
        """
        from unittest.mock import Mock
        
        # Arrange - Mock DeepSeek client that accepts email
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(return_value=True)
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        email_data = {
            'subject': subject,
            'sender': "sender@example.com",
            'body': body
        }
        
        # Act
        result = financial_filter.filter_email(email_data)
        
        # Assert
        assert result is not None, (
            "AI-verified financial email should be accepted"
        )
        assert 'filter_method' in result, (
            "Result must contain 'filter_method' field"
        )
        assert result['filter_method'] == FilterMethod.AI_VERIFIED.value, (
            "Filter method must be 'ai_verified' for AI-verified emails"
        )
        
        # Verify statistics
        stats = financial_filter.get_statistics()
        assert stats['ai_verified'] == 1, (
            "AI-verified email must be logged in statistics"
        )


class TestFinancialFilterBinaryAIResponse:
    """
    Property tests for binary AI response.
    
    Feature: finmatcher-v2-upgrade
    Property 31: Binary AI Response
    Validates: Requirements 13.5
    """
    
    # All keywords to exclude from ambiguous text generation
    ALL_KEYWORDS_LOWER = [
        # Financial keywords
        'receipt', 'invoice', 'bill', 'payment', 'transaction',
        'order', 'confirmation', 'purchase', 'statement', 'total',
        'amount', 'due', 'received', 'account',
        # Spam keywords
        'unsubscribe', 'newsletter', 'discount', 'sale', 'offer',
        'limited', 'time', 'subscribe', 'click', 'here', 'job',
        'resume', 'meeting', 'promotion', 'deal', 'coupon',
        'free', 'shipping', 'off', '%'
    ]
    
    @staticmethod
    def ambiguous_text_strategy():
        """
        Generate text that doesn't contain financial or spam keywords.
        
        This ensures the email is truly ambiguous and will trigger AI verification.
        """
        return st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                blacklist_characters='%'
            ),
            min_size=5,
            max_size=100
        ).filter(lambda t: not any(
            keyword in t.lower()
            for keyword in TestFinancialFilterBinaryAIResponse.ALL_KEYWORDS_LOWER
        ))
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=100)
    def test_binary_ai_response_returns_boolean(
        self,
        subject: str,
        body: str
    ):
        """
        Property 31: Binary AI Response.
        
        For any AI verification request, the DeepSeek_API response must
        contain a boolean is_financial field. The AI verification method
        must always return a boolean value (True or False), never None,
        empty, or any other non-boolean type.
        
        Validates: Requirements 13.5
        """
        from unittest.mock import Mock
        
        # Test with both possible boolean values
        for expected_boolean in [True, False]:
            # Arrange - Mock DeepSeek client
            mock_deepseek = Mock()
            mock_deepseek.verify_financial_email = Mock(return_value=expected_boolean)
            
            financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
            
            email_data = {
                'subject': subject,
                'sender': "sender@example.com",
                'body': body
            }
            
            # Act
            result = financial_filter.filter_email(email_data)
            
            # Assert - Verify the internal _ai_verification method returns boolean
            ai_result = financial_filter._ai_verification(subject, body)
            
            assert isinstance(ai_result, bool), (
                f"AI verification must return boolean, got {type(ai_result).__name__}"
            )
            
            assert ai_result in [True, False], (
                f"AI verification must return True or False, got {ai_result}"
            )
            
            # Verify the result matches the expected boolean
            assert ai_result == expected_boolean, (
                f"AI verification returned {ai_result}, expected {expected_boolean}"
            )
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=100)
    def test_binary_ai_response_never_none(
        self,
        subject: str,
        body: str
    ):
        """
        Property 31: Binary AI Response Never None.
        
        For any AI verification request, the response must never be None.
        It must always be a boolean value.
        
        Validates: Requirements 13.5
        """
        from unittest.mock import Mock
        
        # Arrange - Mock DeepSeek client
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(return_value=True)
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        # Act
        ai_result = financial_filter._ai_verification(subject, body)
        
        # Assert
        assert ai_result is not None, (
            "AI verification must never return None"
        )
        
        assert isinstance(ai_result, bool), (
            f"AI verification must return boolean, not {type(ai_result).__name__}"
        )
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=100)
    def test_binary_ai_response_never_empty(
        self,
        subject: str,
        body: str
    ):
        """
        Property 31: Binary AI Response Never Empty.
        
        For any AI verification request, the response must never be an
        empty string, empty list, or any other empty value. It must
        always be a boolean.
        
        Validates: Requirements 13.5
        """
        from unittest.mock import Mock
        
        # Arrange - Mock DeepSeek client
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(return_value=False)
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        # Act
        ai_result = financial_filter._ai_verification(subject, body)
        
        # Assert - Must not be empty or falsy non-boolean values
        assert ai_result is not "", (
            "AI verification must not return empty string"
        )
        
        assert ai_result is not [], (
            "AI verification must not return empty list"
        )
        
        assert ai_result is not {}, (
            "AI verification must not return empty dict"
        )
        
        # Must be exactly True or False
        assert ai_result is True or ai_result is False, (
            f"AI verification must return True or False, got {ai_result}"
        )
    
    @given(
        subject=ambiguous_text_strategy(),
        body=ambiguous_text_strategy()
    )
    @settings(max_examples=100)
    def test_binary_ai_response_consistent_type(
        self,
        subject: str,
        body: str
    ):
        """
        Property 31: Binary AI Response Consistent Type.
        
        For any AI verification request, the response type must be
        consistently boolean regardless of input complexity.
        
        Validates: Requirements 13.5
        """
        from unittest.mock import Mock
        
        # Test with various return values
        for return_value in [True, False]:
            # Arrange
            mock_deepseek = Mock()
            mock_deepseek.verify_financial_email = Mock(return_value=return_value)
            
            financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
            
            # Act
            ai_result = financial_filter._ai_verification(subject, body)
            
            # Assert - Type must always be bool
            assert type(ai_result) is bool, (
                f"AI verification must return bool type, got {type(ai_result)}"
            )
            
            # Verify it's not a truthy/falsy value that's not boolean
            assert not isinstance(ai_result, int) or isinstance(ai_result, bool), (
                "AI verification must not return integer (0/1) instead of boolean"
            )
            
            assert not isinstance(ai_result, str), (
                "AI verification must not return string ('true'/'false') instead of boolean"
            )
    
    def test_binary_ai_response_on_api_failure(self):
        """
        Property 31: Binary AI Response on API Failure.
        
        Even when the API fails, the _ai_verification method must return
        a boolean value (False for conservative rejection).
        
        Validates: Requirements 13.5, 13.6
        """
        from unittest.mock import Mock
        
        # Arrange - Mock DeepSeek client that raises exception
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(
            side_effect=Exception("API connection failed")
        )
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        # Act
        ai_result = financial_filter._ai_verification("Test subject", "Test body")
        
        # Assert - Must still return boolean (False for conservative rejection)
        assert isinstance(ai_result, bool), (
            f"AI verification must return boolean even on failure, got {type(ai_result).__name__}"
        )
        
        assert ai_result is False, (
            "AI verification must return False on API failure (conservative approach)"
        )
    
    @given(
        subject=st.text(min_size=1, max_size=100),
        body=st.text(min_size=0, max_size=500)
    )
    @settings(max_examples=100)
    def test_binary_ai_response_for_any_input(
        self,
        subject: str,
        body: str
    ):
        """
        Property 31: Binary AI Response for Any Input.
        
        For any email subject and body (including edge cases like very
        short, very long, special characters), the AI verification must
        return a boolean value.
        
        Validates: Requirements 13.5
        """
        from unittest.mock import Mock
        
        # Arrange - Mock DeepSeek client
        mock_deepseek = Mock()
        mock_deepseek.verify_financial_email = Mock(return_value=True)
        
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek)
        
        # Act
        ai_result = financial_filter._ai_verification(subject, body)
        
        # Assert
        assert isinstance(ai_result, bool), (
            f"AI verification must return boolean for any input, got {type(ai_result).__name__}"
        )
        
        assert ai_result in [True, False], (
            f"AI verification must return True or False, got {ai_result}"
        )
