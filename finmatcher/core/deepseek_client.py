"""
DeepSeek AI integration service for FinMatcher v2.0 Enterprise Upgrade.

This module provides semantic embedding generation and AI verification using
the DeepSeek V3 API with retry logic, text truncation, and error handling.

Validates Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 11.3
"""

import logging
import time
import json
import re
from typing import List, Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    Client for DeepSeek V3 API integration.
    
    Provides semantic embedding generation and AI verification with:
    - Retry logic with exponential backoff
    - Text truncation to token limits
    - Request/response sanitization
    - Error handling and fallback
    
    Validates Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 11.3
    """
    
    def __init__(self, api_key: str, timeout: int = 30, max_tokens: int = 512):
        """
        Initialize DeepSeek API client.
        
        Args:
            api_key: DeepSeek API key
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens for text truncation
            
        Validates Requirement: 2.1 - Use DeepSeek V3 for calculating high-dimensional vector embeddings
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.base_url = "https://api.deepseek.com/v1"
        
        if not api_key:
            logger.warning("DeepSeek API key not provided, AI features will be disabled")
        else:
            logger.info(f"DeepSeek client initialized (timeout: {timeout}s, max_tokens: {max_tokens})")
    
    def get_embedding(self, text: str, max_tokens: Optional[int] = None) -> Optional[List[float]]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
            max_tokens: Maximum token length (uses instance default if not specified)
            
        Returns:
            Embedding vector or None if API fails
            
        Validates Requirements:
        - 2.2: Send transaction and receipt text to DeepSeek API
        - 2.4: Log error and set semantic score to 0 if API fails
        - 11.3: Truncate input to 512 tokens
        """
        if not self.api_key:
            logger.debug("DeepSeek API key not available, returning None")
            return None
        
        # Truncate text to token limit
        max_tokens = max_tokens or self.max_tokens
        truncated_text = self._truncate_text(text, max_tokens)
        
        # Get embeddings with retry logic
        embeddings = self.get_embeddings_batch([truncated_text])
        
        if embeddings and embeddings[0] is not None:
            return embeddings[0]
        else:
            logger.error("Failed to get embedding from DeepSeek API")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in a single API call.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors (None for failed embeddings)
            
        Validates Requirements:
        - 2.1: Use DeepSeek V3 for calculating high-dimensional vector embeddings
        - 2.4: Implement retry logic with exponential backoff
        """
        if not self.api_key:
            return [None] * len(texts)
        
        # Truncate all texts
        truncated_texts = [self._truncate_text(text, self.max_tokens) for text in texts]
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-v3",
            "input": truncated_texts,
            "encoding_format": "float"
        }
        
        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Sanitize payload for logging
                sanitized_payload = self._sanitize_for_logging(payload.copy())
                logger.debug(f"DeepSeek API request (attempt {attempt + 1}): {sanitized_payload}")
                
                response = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(min(retry_after, 60))
                    continue
                
                # Handle authentication errors (no retry)
                if response.status_code == 401:
                    logger.error("Authentication error: Invalid API key")
                    return [None] * len(texts)
                
                # Handle server errors (retry)
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Server error {response.status_code}, retrying in {delay}s")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Server error {response.status_code} after {max_retries} retries")
                        return [None] * len(texts)
                
                # Success
                response.raise_for_status()
                data = response.json()
                
                # Extract embeddings
                embeddings = []
                for item in data.get('data', []):
                    embeddings.append(item.get('embedding'))
                
                logger.debug(f"Successfully retrieved {len(embeddings)} embeddings")
                return embeddings
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Request timeout, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    logger.error(f"Request timeout after {max_retries} retries")
                    return [None] * len(texts)
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Network error: {e}, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    logger.error(f"Network error after {max_retries} retries: {e}")
                    return [None] * len(texts)
                    
            except Exception as e:
                logger.error(f"Unexpected error getting embeddings: {e}")
                return [None] * len(texts)
        
        return [None] * len(texts)
    
    def verify_financial_email(self, subject: str, body: str) -> bool:
        """
        Verify if email is financial using DeepSeek AI.
        
        Args:
            subject: Email subject
            body: Email body (truncated to 500 chars)
            
        Returns:
            True if financial, False otherwise
            
        Validates Requirement: 13.4, 13.5 - AI verification for ambiguous emails
        """
        if not self.api_key:
            logger.debug("DeepSeek API key not available, returning False")
            return False
        
        # Truncate body to 500 characters
        body_snippet = body[:500] if body else ""
        
        prompt = f"""Analyze this email. Is it a financial document (Invoice, Receipt, Bill, Payment Confirmation)?

Subject: {subject}
Body: {body_snippet}...

Answer strictly in JSON:
{{"is_financial": true/false}}"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            content = data['choices'][0]['message']['content']
            result = json.loads(content)
            is_financial = result.get('is_financial', False)
            
            logger.debug(f"AI verification: {is_financial} for '{subject}'")
            return is_financial
            
        except Exception as e:
            logger.error(f"AI verification failed: {e}")
            return False  # Conservative: reject on error
    
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to maximum token count.
        
        Args:
            text: Input text
            max_tokens: Maximum token count
            
        Returns:
            Truncated text
            
        Validates Requirement: 11.3 - Truncate input to 512 tokens
        
        Note: This is a simple approximation. For exact token counting,
        use a tokenizer library like tiktoken.
        """
        # Approximate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        truncated = text[:max_chars]
        logger.debug(f"Text truncated from {len(text)} to {len(truncated)} characters")
        return truncated
    
    def _sanitize_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive data before logging.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary
            
        Validates Requirement: 2.6 - Sanitize all API request and response data before logging
        """
        sanitized = data.copy()
        
        # Sanitize API keys
        if 'api_key' in sanitized:
            sanitized['api_key'] = '***REDACTED***'
        
        # Sanitize authorization headers
        if 'headers' in sanitized and isinstance(sanitized['headers'], dict):
            if 'Authorization' in sanitized['headers']:
                sanitized['headers']['Authorization'] = 'Bearer ***REDACTED***'
        
        # Truncate long text inputs for logging
        if 'input' in sanitized:
            if isinstance(sanitized['input'], list):
                sanitized['input'] = [
                    text[:100] + '...' if len(text) > 100 else text
                    for text in sanitized['input']
                ]
            elif isinstance(sanitized['input'], str):
                if len(sanitized['input']) > 100:
                    sanitized['input'] = sanitized['input'][:100] + '...'
        
        return sanitized
