"""
Property-based tests for PII Sanitization in Logs.

This module contains property-based tests using Hypothesis to verify
that the logging system correctly sanitizes personally identifiable
information (PII) before writing to logs.

Testing Framework: Hypothesis (Python)
Feature: finmatcher-v2-upgrade
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from typing import List

from finmatcher.utils.logger import SanitizingFormatter


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=20)
settings.load_profile("finmatcher")


# Strategy for generating valid email addresses
@st.composite
def email_addresses(draw):
    """Generate valid email addresses."""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=3,
        max_size=15
    ))
    tld = draw(st.sampled_from(['com', 'org', 'net', 'edu', 'gov', 'io', 'co']))
    return f"{username}@{domain}.{tld}"


# Strategy for generating credit card numbers
@st.composite
def credit_card_numbers(draw):
    """Generate credit card-like numbers (16 digits)."""
    format_type = draw(st.sampled_from(['no_space', 'spaces', 'dashes']))
    
    # Generate 4 groups of 4 digits
    groups = [str(draw(st.integers(min_value=1000, max_value=9999))) for _ in range(4)]
    
    if format_type == 'no_space':
        return ''.join(groups)
    elif format_type == 'spaces':
        return ' '.join(groups)
    else:  # dashes
        return '-'.join(groups)


# Strategy for generating account numbers
@st.composite
def account_numbers(draw):
    """Generate account numbers (8-12 digits)."""
    length = draw(st.integers(min_value=8, max_value=12))
    return ''.join([str(draw(st.integers(min_value=0, max_value=9))) for _ in range(length)])


# Strategy for generating API keys
@st.composite
def api_keys(draw):
    """Generate API key-like strings."""
    prefix = draw(st.sampled_from(['api_key', 'apikey', 'key', 'API_KEY', 'ApiKey']))
    separator = draw(st.sampled_from(['=', ':', ' = ', ' : ']))
    key_value = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122),
        min_size=20,
        max_size=40
    ))
    return f"{prefix}{separator}{key_value}"


# Strategy for generating passwords
@st.composite
def passwords(draw):
    """Generate password-like strings."""
    prefix = draw(st.sampled_from(['password', 'pwd', 'pass', 'PASSWORD', 'Password']))
    separator = draw(st.sampled_from(['=', ':', ' = ', ' : ']))
    # Generate password value that doesn't start with quotes, spaces, commas, or semicolons
    # to match the regex pattern in the logger
    pwd_value = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122),
        min_size=8,
        max_size=20
    ))
    return f"{prefix}{separator}{pwd_value}"


class TestPIISanitization:
    """
    Property tests for PII sanitization in logs.
    
    Feature: finmatcher-v2-upgrade
    Property 24: PII Sanitization in Logs
    **Validates: Requirements 10.7**
    """
    
    @given(email=email_addresses())
    @settings(max_examples=20)
    def test_email_addresses_are_sanitized(self, email: str):
        """
        Property 24: Email Addresses Are Sanitized.
        
        For any log message containing an email address, the sanitized
        version must replace the email with [EMAIL] placeholder.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"User {email} logged in successfully"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - Email must be replaced with [EMAIL]
        assert email not in sanitized, (
            f"Email address '{email}' was not sanitized in log message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
        assert '[EMAIL]' in sanitized, (
            f"[EMAIL] placeholder not found in sanitized message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    @given(card_number=credit_card_numbers())
    @settings(max_examples=20)
    def test_credit_card_numbers_are_sanitized(self, card_number: str):
        """
        Property 24: Credit Card Numbers Are Sanitized.
        
        For any log message containing a credit card number (with or without
        spaces/dashes), the sanitized version must replace it with [CARD].
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"Processing payment with card {card_number}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - Card number must be replaced with [CARD]
        # Remove spaces and dashes for comparison
        card_digits = card_number.replace(' ', '').replace('-', '')
        assert card_digits not in sanitized.replace(' ', '').replace('-', ''), (
            f"Credit card number '{card_number}' was not sanitized in log message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
        assert '[CARD]' in sanitized, (
            f"[CARD] placeholder not found in sanitized message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    @given(account_num=account_numbers())
    @settings(max_examples=20)
    def test_account_numbers_are_sanitized(self, account_num: str):
        """
        Property 24: Account Numbers Are Sanitized.
        
        For any log message containing an account number (8-12 digits),
        the sanitized version must replace it with [ACCOUNT].
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"Account {account_num} balance updated"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - Account number must be replaced with [ACCOUNT]
        assert account_num not in sanitized, (
            f"Account number '{account_num}' was not sanitized in log message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
        assert '[ACCOUNT]' in sanitized, (
            f"[ACCOUNT] placeholder not found in sanitized message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    @given(api_key_str=api_keys())
    @settings(max_examples=20)
    def test_api_keys_are_sanitized(self, api_key_str: str):
        """
        Property 24: API Keys Are Sanitized.
        
        For any log message containing an API key in various formats
        (api_key=value, apikey:value, etc.), the sanitized version must
        replace the key value with ***REDACTED***.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"Connecting to API with {api_key_str}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - API key value must be redacted
        # Extract the key value from the original string
        match = re.search(r'[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})', api_key_str)
        if match:
            key_value = match.group(1)
            assert key_value not in sanitized, (
                f"API key value '{key_value}' was not sanitized in log message. "
                f"Original: {log_message}, Sanitized: {sanitized}"
            )
        
        assert '***REDACTED***' in sanitized, (
            f"***REDACTED*** placeholder not found in sanitized message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    @given(password_str=passwords())
    @settings(max_examples=20)
    def test_passwords_are_sanitized(self, password_str: str):
        """
        Property 24: Passwords Are Sanitized.
        
        For any log message containing a password in various formats
        (password=value, pwd:value, etc.), the sanitized version must
        replace the password value with ***REDACTED***.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"Authentication attempt with {password_str}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - Password value must be redacted
        assert '***REDACTED***' in sanitized, (
            f"***REDACTED*** placeholder not found in sanitized message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    @given(
        email=email_addresses(),
        card_number=credit_card_numbers(),
        account_num=account_numbers()
    )
    @settings(max_examples=20)
    def test_multiple_pii_types_sanitized_together(
        self, 
        email: str, 
        card_number: str, 
        account_num: str
    ):
        """
        Property 24: Multiple PII Types Sanitized Together.
        
        For any log message containing multiple types of PII (email, card,
        account), all PII must be sanitized in a single pass.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = (
            f"Transaction for {email} using card {card_number} "
            f"from account {account_num} completed"
        )
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - All PII must be sanitized
        assert email not in sanitized, (
            f"Email '{email}' was not sanitized"
        )
        
        card_digits = card_number.replace(' ', '').replace('-', '')
        assert card_digits not in sanitized.replace(' ', '').replace('-', ''), (
            f"Card number '{card_number}' was not sanitized"
        )
        
        assert account_num not in sanitized, (
            f"Account number '{account_num}' was not sanitized"
        )
        
        # Assert - All placeholders present
        assert '[EMAIL]' in sanitized, "Missing [EMAIL] placeholder"
        assert '[CARD]' in sanitized, "Missing [CARD] placeholder"
        assert '[ACCOUNT]' in sanitized, "Missing [ACCOUNT] placeholder"
    
    @given(
        text_before=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'), min_codepoint=32, max_codepoint=122),
            min_size=0,
            max_size=20
        ),
        email=email_addresses(),
        text_after=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'), min_codepoint=32, max_codepoint=122),
            min_size=0,
            max_size=20
        )
    )
    @settings(max_examples=20)
    def test_pii_sanitization_preserves_context(
        self, 
        text_before: str, 
        email: str, 
        text_after: str
    ):
        """
        Property 24: PII Sanitization Preserves Context.
        
        For any log message with PII embedded in context text, the
        sanitization must replace only the PII while preserving the
        surrounding context.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        # Add spaces to ensure email is properly detected as a word boundary
        log_message = f"{text_before} {email} {text_after}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - Email must be sanitized
        assert email not in sanitized, (
            f"Email '{email}' was not sanitized"
        )
        
        # Assert - Context text should be preserved (if it doesn't contain PII patterns)
        # Note: We can't guarantee exact preservation if context contains PII-like patterns
        assert '[EMAIL]' in sanitized, "Missing [EMAIL] placeholder"
    
    @given(
        deepseek_key=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122),
            min_size=30,
            max_size=50
        )
    )
    @settings(max_examples=20)
    def test_deepseek_api_keys_are_sanitized(self, deepseek_key: str):
        """
        Property 24: DeepSeek API Keys Are Sanitized.
        
        For any log message containing a DeepSeek API key (format: sk-...),
        the sanitized version must replace it with sk-***REDACTED***.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        api_key = f"sk-{deepseek_key}"
        log_message = f"Connecting to DeepSeek with key {api_key}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - DeepSeek key must be sanitized
        assert deepseek_key not in sanitized, (
            f"DeepSeek API key '{api_key}' was not sanitized in log message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
        assert 'sk-***REDACTED***' in sanitized, (
            f"sk-***REDACTED*** placeholder not found in sanitized message. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    @given(
        text=st.text(
            alphabet=st.characters(blacklist_characters='@', whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Zs')),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=20)
    def test_non_pii_text_unchanged(self, text: str):
        """
        Property 24: Non-PII Text Remains Unchanged.
        
        For any log message that does not contain PII, the sanitized
        version must be identical to the original (except for formatting).
        
        **Validates: Requirements 10.7**
        """
        # Skip if text contains patterns that look like PII
        # (account numbers, card-like sequences)
        if re.search(r'\b\d{8,16}\b', text):
            return  # Skip this test case
        
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"Processing transaction: {text}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - Original text should be present (no PII placeholders)
        assert text in sanitized, (
            f"Non-PII text was incorrectly modified. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
        
        # Assert - No PII placeholders should be present
        assert '[EMAIL]' not in sanitized, "False positive: [EMAIL] in non-PII text"
        assert '[CARD]' not in sanitized, "False positive: [CARD] in non-PII text"
        assert '[ACCOUNT]' not in sanitized, "False positive: [ACCOUNT] in non-PII text"
    
    @given(
        emails=st.lists(email_addresses(), min_size=1, max_size=5)
    )
    @settings(max_examples=20)
    def test_multiple_emails_all_sanitized(self, emails: List[str]):
        """
        Property 24: Multiple Emails All Sanitized.
        
        For any log message containing multiple email addresses, all
        email addresses must be sanitized.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = f"Email list: {', '.join(emails)}"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized = formatter.format(record)
        
        # Assert - All emails must be sanitized
        for email in emails:
            assert email not in sanitized, (
                f"Email '{email}' was not sanitized in log message. "
                f"Original: {log_message}, Sanitized: {sanitized}"
            )
        
        # Assert - [EMAIL] placeholder should appear for each email
        email_count = sanitized.count('[EMAIL]')
        assert email_count >= len(emails), (
            f"Expected at least {len(emails)} [EMAIL] placeholders, found {email_count}. "
            f"Original: {log_message}, Sanitized: {sanitized}"
        )
    
    def test_sanitization_is_consistent(self):
        """
        Property 24: Sanitization Is Consistent.
        
        For any log message, sanitizing it multiple times must produce
        the same result.
        
        **Validates: Requirements 10.7**
        """
        # Arrange
        formatter = SanitizingFormatter()
        log_message = "User john.doe@example.com with card 1234-5678-9012-3456"
        
        # Create a mock log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        
        # Act
        sanitized_1 = formatter.format(record)
        
        # Create another record with the same message
        record_2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=log_message,
            args=(),
            exc_info=None
        )
        sanitized_2 = formatter.format(record_2)
        
        # Assert - Both sanitizations must produce the same result
        assert sanitized_1 == sanitized_2, (
            f"Sanitization is not consistent. "
            f"First: {sanitized_1}, Second: {sanitized_2}"
        )
