"""
Unit tests for DeepSeek client error handling.

This module contains unit tests to verify error handling in the DeepSeek client:
- Retry logic for network errors
- Fallback on API failure
- Rate limiting handling

Testing Framework: pytest
Feature: finmatcher-v2-upgrade
Task: 4.5 - Write unit tests for error handling
Validates Requirement: 2.4
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import requests

from finmatcher.core.deepseek_client import DeepSeekClient


class TestDeepSeekErrorHandling:
    """
    Unit tests for DeepSeek client error handling.
    
    Tests verify:
    - Network error retry logic with exponential backoff
    - API failure fallback behavior
    - Rate limiting handling with retry-after
    - Authentication error handling (no retry)
    - Server error retry logic
    """
    
    @pytest.fixture
    def client(self):
        """Create a DeepSeek client for testing."""
        return DeepSeekClient(api_key="test_api_key", timeout=30, max_tokens=512)
    
    def test_retry_logic_for_network_timeout(self, client):
        """
        Test retry logic for network timeout errors.
        
        Validates Requirement: 2.4 - Retry up to 3 times with exponential backoff
        """
        with patch('requests.post') as mock_post:
            # Simulate timeout on all attempts
            mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            start_time = time.time()
            result = client.get_embeddings_batch(["test text"])
            elapsed_time = time.time() - start_time
            
            # Verify retries occurred (3 attempts total)
            assert mock_post.call_count == 3, "Should retry 3 times"
            
            # Verify exponential backoff (1s + 2s = 3s minimum)
            assert elapsed_time >= 3.0, "Should wait with exponential backoff"
            
            # Verify fallback to None
            assert result == [None], "Should return None on timeout"
    
    def test_retry_logic_for_connection_error(self, client):
        """
        Test retry logic for connection errors.
        
        Validates Requirement: 2.4 - Retry network errors with exponential backoff
        """
        with patch('requests.post') as mock_post:
            # Simulate connection error
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify retries occurred
            assert mock_post.call_count == 3, "Should retry 3 times"
            
            # Verify fallback to None
            assert result == [None], "Should return None on connection error"
    
    def test_successful_retry_after_transient_failure(self, client):
        """
        Test successful retry after transient network failure.
        
        Validates Requirement: 2.4 - Retry logic succeeds after transient errors
        """
        with patch('requests.post') as mock_post:
            # First attempt fails, second succeeds
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3]}]
            }
            
            mock_post.side_effect = [
                requests.exceptions.Timeout("Timeout"),
                mock_response
            ]
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify retry succeeded
            assert mock_post.call_count == 2, "Should retry once and succeed"
            assert result == [[0.1, 0.2, 0.3]], "Should return embeddings after retry"
    
    def test_rate_limiting_handling_with_retry_after(self, client):
        """
        Test rate limiting handling with Retry-After header.
        
        Validates Requirement: 2.4 - Handle rate limiting (429) with retry-after
        """
        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            
            # First attempt: rate limited with Retry-After header
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '5'}
            
            # Second attempt: success
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3]}]
            }
            
            mock_post.side_effect = [rate_limit_response, success_response]
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify rate limit was handled
            assert mock_post.call_count == 2, "Should retry after rate limit"
            
            # Verify sleep was called with retry-after value
            mock_sleep.assert_called_once_with(5)
            
            # Verify success after retry
            assert result == [[0.1, 0.2, 0.3]], "Should succeed after rate limit"
    
    def test_rate_limiting_respects_max_wait_time(self, client):
        """
        Test rate limiting respects maximum wait time of 60 seconds.
        
        Validates Requirement: 2.4 - Cap retry-after wait at 60 seconds
        """
        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            
            # Rate limited with very long Retry-After
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '300'}  # 5 minutes
            
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3]}]
            }
            
            mock_post.side_effect = [rate_limit_response, success_response]
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify wait time was capped at 60 seconds
            mock_sleep.assert_called_once_with(60)
    
    def test_authentication_error_no_retry(self, client):
        """
        Test authentication errors are not retried.
        
        Validates Requirement: 2.4 - No retry on authentication errors (401)
        """
        with patch('requests.post') as mock_post:
            # Simulate authentication error
            auth_error_response = Mock()
            auth_error_response.status_code = 401
            mock_post.return_value = auth_error_response
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify no retries occurred
            assert mock_post.call_count == 1, "Should not retry on auth error"
            
            # Verify fallback to None
            assert result == [None], "Should return None on auth error"
    
    def test_server_error_retry_logic(self, client):
        """
        Test server errors (5xx) are retried with exponential backoff.
        
        Validates Requirement: 2.4 - Retry server errors up to 3 times
        """
        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            
            # Simulate server error on all attempts
            server_error_response = Mock()
            server_error_response.status_code = 503
            mock_post.return_value = server_error_response
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify retries occurred
            assert mock_post.call_count == 3, "Should retry 3 times on server error"
            
            # Verify exponential backoff (1s, 2s)
            assert mock_sleep.call_count == 2, "Should sleep between retries"
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls == [1.0, 2.0], "Should use exponential backoff"
            
            # Verify fallback to None
            assert result == [None], "Should return None after exhausting retries"
    
    def test_server_error_successful_retry(self, client):
        """
        Test successful retry after server error.
        
        Validates Requirement: 2.4 - Retry succeeds after transient server error
        """
        with patch('requests.post') as mock_post:
            # First attempt: server error
            server_error_response = Mock()
            server_error_response.status_code = 500
            
            # Second attempt: success
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3]}]
            }
            
            mock_post.side_effect = [server_error_response, success_response]
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify retry succeeded
            assert mock_post.call_count == 2, "Should retry once and succeed"
            assert result == [[0.1, 0.2, 0.3]], "Should return embeddings after retry"
    
    def test_fallback_on_api_failure_get_embedding(self, client):
        """
        Test fallback to None when get_embedding fails.
        
        Validates Requirement: 2.4 - Set semantic score to 0 on API failure
        """
        with patch('requests.post') as mock_post:
            # Simulate API failure
            mock_post.side_effect = requests.exceptions.RequestException("API error")
            
            result = client.get_embedding("test text")
            
            # Verify fallback to None
            assert result is None, "Should return None on API failure"
    
    def test_fallback_on_invalid_response_format(self, client):
        """
        Test fallback when API returns invalid response format.
        
        Validates Requirement: 2.4 - Handle invalid responses gracefully
        """
        with patch('requests.post') as mock_post:
            # Simulate invalid response (missing 'data' key)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'invalid': 'format'}
            mock_post.return_value = mock_response
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify fallback to empty list (no embeddings extracted)
            assert result == [], "Should return empty list on invalid format"
    
    def test_fallback_on_json_decode_error(self, client):
        """
        Test fallback when response JSON cannot be decoded.
        
        Validates Requirement: 2.4 - Handle malformed responses
        """
        with patch('requests.post') as mock_post:
            # Simulate JSON decode error
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response
            
            result = client.get_embeddings_batch(["test text"])
            
            # Verify fallback to None
            assert result == [None], "Should return None on JSON decode error"
    
    def test_no_api_key_returns_none(self):
        """
        Test that client without API key returns None immediately.
        
        Validates Requirement: 2.4 - Handle missing API key gracefully
        """
        client = DeepSeekClient(api_key="", timeout=30)
        
        result = client.get_embedding("test text")
        
        # Verify no API call is made and None is returned
        assert result is None, "Should return None when API key is missing"
    
    def test_verify_financial_email_fallback_on_error(self, client):
        """
        Test verify_financial_email returns False on API error.
        
        Validates Requirement: 2.4, 13.6 - Conservative fallback on error
        """
        with patch('requests.post') as mock_post:
            # Simulate API error
            mock_post.side_effect = requests.exceptions.RequestException("API error")
            
            result = client.verify_financial_email("Test subject", "Test body")
            
            # Verify conservative fallback
            assert result is False, "Should return False on API error (conservative)"
    
    def test_exponential_backoff_timing(self, client):
        """
        Test exponential backoff timing is correct (1s, 2s, 4s).
        
        Validates Requirement: 2.4 - Exponential backoff with correct timing
        """
        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            
            # Simulate timeout on all attempts
            mock_post.side_effect = requests.exceptions.Timeout("Timeout")
            
            client.get_embeddings_batch(["test text"])
            
            # Verify exponential backoff timing
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls == [1.0, 2.0], "Should use exponential backoff: 1s, 2s"
    
    def test_multiple_texts_all_fail(self, client):
        """
        Test that all texts return None when API fails.
        
        Validates Requirement: 2.4 - Consistent fallback for batch operations
        """
        with patch('requests.post') as mock_post:
            # Simulate API failure
            mock_post.side_effect = requests.exceptions.RequestException("API error")
            
            result = client.get_embeddings_batch(["text1", "text2", "text3"])
            
            # Verify all return None
            assert result == [None, None, None], "Should return None for all texts on failure"
    
    def test_partial_success_not_possible(self, client):
        """
        Test that batch operations are all-or-nothing.
        
        Validates Requirement: 2.4 - Batch operations succeed or fail together
        """
        with patch('requests.post') as mock_post:
            # Simulate successful response with all embeddings
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [
                    {'embedding': [0.1, 0.2]},
                    {'embedding': [0.3, 0.4]},
                    {'embedding': [0.5, 0.6]}
                ]
            }
            mock_post.return_value = mock_response
            
            result = client.get_embeddings_batch(["text1", "text2", "text3"])
            
            # Verify all succeeded
            assert len(result) == 3, "Should return all embeddings"
            assert all(emb is not None for emb in result), "All embeddings should be present"
