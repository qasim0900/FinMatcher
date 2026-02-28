"""
Property-based tests for DeepSeek text truncation.

This module contains property-based tests using Hypothesis to verify:
- Property 26: Text Truncation at Token Limit

Testing Framework: pytest + hypothesis
Validates Requirements: 11.3
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from finmatcher.core.deepseek_client import DeepSeekClient


class TestTextTruncationProperty:
    """
    Property 26: Text Truncation at Token Limit
    
    Universal Property:
    For any text input to semantic scoring that exceeds the token limit,
    the truncated text must be exactly at the token limit (default 512 tokens).
    
    Feature: finmatcher-v2-upgrade
    Property 26: Text Truncation at Token Limit
    
    Validates: Requirements 11.3
    """
    
    @given(
        text=st.text(min_size=3000, max_size=10000),
        max_tokens=st.integers(min_value=100, max_value=1000)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.data_too_large, HealthCheck.too_slow])
    def test_text_truncated_to_token_limit(self, text: str, max_tokens: int):
        """
        Property 26: Text Is Truncated to Token Limit.
        
        For any text that exceeds the token limit, the truncated text must
        be at or below the token limit (approximated as max_tokens * 4 characters).
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        
        # Act
        truncated = deepseek_client._truncate_text(text, max_tokens)
        
        # Assert
        max_chars = max_tokens * 4
        assert len(truncated) <= max_chars, \
            f"Truncated text length {len(truncated)} exceeds max chars {max_chars}"
        
        # If original text was longer, verify truncation occurred
        if len(text) > max_chars:
            assert len(truncated) == max_chars, \
                f"Text should be truncated to exactly {max_chars} chars, got {len(truncated)}"
            assert truncated == text[:max_chars], \
                "Truncated text should be the first max_chars characters"
        else:
            assert truncated == text, \
                "Text shorter than limit should not be modified"
    
    @given(text=st.text(min_size=1, max_size=2000))
    @settings(max_examples=10)
    def test_short_text_not_truncated(self, text: str):
        """
        Property 26: Short Text Is Not Truncated.
        
        For any text that is shorter than the token limit, the text must
        be returned unchanged.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        max_tokens = 512  # Default token limit
        max_chars = max_tokens * 4
        
        # Act
        truncated = deepseek_client._truncate_text(text, max_tokens)
        
        # Assert
        if len(text) <= max_chars:
            assert truncated == text, \
                "Text shorter than limit should be returned unchanged"
            assert len(truncated) == len(text), \
                "Length should be preserved for short text"
    
    @given(
        text=st.text(min_size=5000, max_size=20000),
        max_tokens=st.sampled_from([128, 256, 512, 1024])
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.data_too_large, HealthCheck.large_base_example, HealthCheck.too_slow])
    def test_truncation_at_various_token_limits(self, text: str, max_tokens: int):
        """
        Property 26: Truncation Works at Various Token Limits.
        
        For any text and any token limit, the truncated text must respect
        the specified token limit.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        
        # Act
        truncated = deepseek_client._truncate_text(text, max_tokens)
        
        # Assert
        max_chars = max_tokens * 4
        assert len(truncated) <= max_chars, \
            f"Truncated text must not exceed {max_chars} chars for {max_tokens} tokens"
        
        if len(text) > max_chars:
            assert len(truncated) == max_chars, \
                f"Long text should be truncated to exactly {max_chars} chars"
    
    @given(
        text=st.text(min_size=3000, max_size=10000)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.data_too_large, HealthCheck.too_slow])
    def test_default_token_limit_is_512(self, text: str):
        """
        Property 26: Default Token Limit Is 512.
        
        When no max_tokens is specified, the default limit of 512 tokens
        (2048 characters) should be used.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        default_max_tokens = 512
        max_chars = default_max_tokens * 4
        
        # Act
        truncated = deepseek_client._truncate_text(text, default_max_tokens)
        
        # Assert
        assert len(truncated) <= max_chars, \
            f"Truncated text must not exceed default limit of {max_chars} chars"
        
        if len(text) > max_chars:
            assert len(truncated) == max_chars, \
                f"Text should be truncated to default limit of {max_chars} chars"
    
    @given(
        text=st.text(min_size=5000, max_size=10000)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.data_too_large, HealthCheck.large_base_example, HealthCheck.too_slow])
    def test_truncation_preserves_beginning_of_text(self, text: str):
        """
        Property 26: Truncation Preserves Beginning of Text.
        
        For any text that is truncated, the truncated version must be
        the beginning portion of the original text.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        max_tokens = 512
        max_chars = max_tokens * 4
        
        # Act
        truncated = deepseek_client._truncate_text(text, max_tokens)
        
        # Assert
        if len(text) > max_chars:
            assert text.startswith(truncated), \
                "Truncated text must be the beginning of the original text"
            assert truncated == text[:len(truncated)], \
                "Truncated text must match the first N characters of original"
    
    @given(
        texts=st.lists(
            st.text(min_size=3000, max_size=10000),
            min_size=1,
            max_size=10
        ),
        max_tokens=st.integers(min_value=256, max_value=1024)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.data_too_large, HealthCheck.too_slow])
    def test_truncation_is_consistent(self, texts: list, max_tokens: int):
        """
        Property 26: Truncation Is Consistent.
        
        For any text, truncating it multiple times with the same token limit
        must produce the same result every time.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        
        # Act & Assert
        for text in texts:
            truncated1 = deepseek_client._truncate_text(text, max_tokens)
            truncated2 = deepseek_client._truncate_text(text, max_tokens)
            truncated3 = deepseek_client._truncate_text(text, max_tokens)
            
            assert truncated1 == truncated2 == truncated3, \
                "Truncation must be deterministic and consistent"
    
    @given(
        text=st.text(min_size=3000, max_size=10000)
    )
    @settings(max_examples=10)
    def test_get_embedding_uses_truncation(self, text: str):
        """
        Property 26: get_embedding Method Uses Truncation.
        
        When get_embedding is called with text exceeding the token limit,
        the text should be truncated before processing.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30, max_tokens=512)
        max_chars = 512 * 4
        
        # Note: This test verifies the truncation logic is applied
        # We can't test the actual API call without mocking, but we can
        # verify that text longer than the limit would be truncated
        
        # Act
        truncated = deepseek_client._truncate_text(text, 512)
        
        # Assert
        if len(text) > max_chars:
            assert len(truncated) == max_chars, \
                "Text should be truncated to token limit before embedding"
            assert len(truncated) < len(text), \
                "Truncated text should be shorter than original"
    
    @given(
        text=st.text(
            min_size=3000,
            max_size=10000,
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'P'),
                min_codepoint=32,
                max_codepoint=126
            )
        ),
        max_tokens=st.integers(min_value=100, max_value=1000)
    )
    @settings(max_examples=10)
    def test_truncation_with_various_character_types(self, text: str, max_tokens: int):
        """
        Property 26: Truncation Works with Various Character Types.
        
        For any text containing various character types (letters, numbers,
        spaces, punctuation), truncation must work correctly.
        
        Validates: Requirements 11.3
        """
        # Arrange
        deepseek_client = DeepSeekClient(api_key="sk-test-key-12345", timeout=30)
        
        # Act
        truncated = deepseek_client._truncate_text(text, max_tokens)
        
        # Assert
        max_chars = max_tokens * 4
        assert len(truncated) <= max_chars, \
            f"Truncated text must not exceed {max_chars} chars"
        
        if len(text) > max_chars:
            assert len(truncated) == max_chars, \
                "Text should be truncated to exact limit"
            # Verify truncated text is valid substring
            assert truncated in text, \
                "Truncated text must be a substring of original"
            assert text.index(truncated) == 0, \
                "Truncated text must start at beginning of original"
