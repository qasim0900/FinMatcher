"""
Unit tests for VectorizedScorer initialization.

Validates Requirements: 2.1, 7.3
"""

import pytest
from decimal import Decimal
from finmatcher.optimization.vectorized_scorer import VectorizedScorer
from finmatcher.storage.models import MatchingConfig
from finmatcher.core.deepseek_client import DeepSeekClient


def test_vectorized_scorer_init_with_config():
    """Test VectorizedScorer initialization with MatchingConfig."""
    # Create a valid MatchingConfig
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    # Initialize VectorizedScorer
    scorer = VectorizedScorer(config)
    
    # Verify attributes
    assert scorer.config == config
    assert scorer.deepseek_client is None
    assert scorer.batch_size == 100000


def test_vectorized_scorer_init_with_deepseek_client():
    """Test VectorizedScorer initialization with DeepSeekClient."""
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    # Create DeepSeekClient
    deepseek_client = DeepSeekClient(api_key="test_key")
    
    # Initialize VectorizedScorer with DeepSeekClient
    scorer = VectorizedScorer(config, deepseek_client=deepseek_client)
    
    # Verify attributes
    assert scorer.config == config
    assert scorer.deepseek_client == deepseek_client
    assert scorer.batch_size == 100000


def test_vectorized_scorer_init_with_custom_batch_size():
    """Test VectorizedScorer initialization with custom batch_size."""
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    # Initialize with custom batch_size
    custom_batch_size = 50000
    scorer = VectorizedScorer(config, batch_size=custom_batch_size)
    
    # Verify attributes
    assert scorer.config == config
    assert scorer.deepseek_client is None
    assert scorer.batch_size == custom_batch_size


def test_vectorized_scorer_init_all_parameters():
    """Test VectorizedScorer initialization with all parameters."""
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    deepseek_client = DeepSeekClient(api_key="test_key")
    custom_batch_size = 75000
    
    # Initialize with all parameters
    scorer = VectorizedScorer(
        config=config,
        deepseek_client=deepseek_client,
        batch_size=custom_batch_size
    )
    
    # Verify all attributes
    assert scorer.config == config
    assert scorer.deepseek_client == deepseek_client
    assert scorer.batch_size == custom_batch_size
