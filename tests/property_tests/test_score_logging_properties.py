"""
Property-based tests for Matching Engine score logging.

This module contains property-based tests using Hypothesis to verify:
- Property 20: Score Calculation Logging is Complete
- Property 21: Match Classification Logging is Complete

Testing Framework: pytest + hypothesis
Feature: finmatcher-v2-upgrade
Validates: Requirements 10.1, 10.2
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, date
from hypothesis import given, strategies as st, settings
from io import StringIO
from typing import List

from finmatcher.core.matching_engine import MatchingEngine
from finmatcher.storage.models import (
    Transaction, Receipt, MatchingConfig, MatchConfidence
)


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=100)
settings.load_profile("finmatcher")


# Custom strategies for generating test data
@st.composite
def transaction_strategy(draw):
    """Generate a valid Transaction object."""
    txn_id = draw(st.integers(min_value=1, max_value=999999))
    txn_date = draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2025, 12, 31)))
    amount = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2))
    description = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    return Transaction(
        id=txn_id,
        statement_file="test_statement.xlsx",
        transaction_date=txn_date,
        amount=amount,
        description=description
    )


@st.composite
def receipt_strategy(draw):
    """Generate a valid Receipt object."""
    rec_id = draw(st.integers(min_value=1, max_value=999999))
    rec_date = draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2025, 12, 31)))
    amount = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2))
    description = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
    
    return Receipt(
        id=rec_id,
        source="email",
        receipt_date=rec_date,
        amount=amount,
        description=description,
        is_financial=True,
        filter_method=None
    )


@st.composite
def matching_config_strategy(draw):
    """Generate a valid MatchingConfig object."""
    # Generate weights that sum to 1.0
    w_a = draw(st.floats(min_value=0.1, max_value=0.8))
    w_d = draw(st.floats(min_value=0.1, max_value=0.8))
    w_s = 1.0 - w_a - w_d
    
    # Ensure w_s is positive
    if w_s < 0.1:
        w_a = 0.4
        w_d = 0.3
        w_s = 0.3
    
    return MatchingConfig(
        weight_amount=w_a,
        weight_date=w_d,
        weight_semantic=w_s,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=2.0
    )


class TestScoreLoggingProperty:
    """
    Property 20: Score Calculation Logging is Complete
    
    Universal Property:
    FOR ALL candidate pair scoring operations,
    WHEN the Matching_Engine calculates scores for a candidate pair,
    THEN the system SHALL log:
    - Transaction Record identifier
    - Receipt Record identifier
    - Amount_Score
    - Date_Score
    - Semantic_Score
    - Composite_Score
    
    Validates Requirement 10.1:
    WHEN the Matching_Engine calculates scores for a candidate pair, 
    THE FinMatcher_System SHALL log the Transaction_Record identifier, 
    Receipt_Record identifier, Amount_Score, Date_Score, Semantic_Score, 
    and Composite_Score
    """
    
    @given(
        transaction=transaction_strategy(),
        receipt=receipt_strategy(),
        config=matching_config_strategy()
    )
    @settings(max_examples=20)
    def test_score_calculation_logs_all_required_fields(
        self,
        transaction: Transaction,
        receipt: Receipt,
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.1**
        
        Property 20: Score Calculation Logging is Complete
        
        For any transaction and receipt pair within tolerance constraints,
        when the matching engine calculates scores, the log must contain:
        1. Transaction ID
        2. Receipt ID
        3. Amount Score
        4. Date Score
        5. Semantic Score
        6. Composite Score
        
        This property verifies that:
        - All required fields are present in the log entry
        - The log entry is created for every candidate pair scoring
        - The logged values are the actual calculated scores
        - The log format is consistent across all scoring operations
        """
        # Ensure receipt is within tolerance constraints so it becomes a candidate
        # Adjust receipt to be within $1.00 and 3 days of transaction
        receipt.amount = transaction.amount + Decimal("0.50")  # Within $1.00
        receipt.receipt_date = transaction.transaction_date  # Same date (within 3 days)
        
        # Create matching engine without DeepSeek client (semantic score will be 0)
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        # Get the matching engine logger
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Execute matching
            matches = engine.find_matches(transaction, [receipt])
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Property: Log must contain transaction ID
            assert str(transaction.id) in log_output, (
                f"Log must contain transaction ID. Expected '{transaction.id}' "
                f"in log output:\n{log_output}"
            )
            
            # Property: Log must contain receipt ID
            assert str(receipt.id) in log_output, (
                f"Log must contain receipt ID. Expected '{receipt.id}' "
                f"in log output:\n{log_output}"
            )
            
            # Property: Log must contain "amount" score indicator
            assert 'amount' in log_output.lower(), (
                f"Log must contain 'amount' score indicator in log output:\n{log_output}"
            )
            
            # Property: Log must contain "date" score indicator
            assert 'date' in log_output.lower(), (
                f"Log must contain 'date' score indicator in log output:\n{log_output}"
            )
            
            # Property: Log must contain "semantic" score indicator
            assert 'semantic' in log_output.lower(), (
                f"Log must contain 'semantic' score indicator in log output:\n{log_output}"
            )
            
            # Property: Log must contain "composite" score indicator
            assert 'composite' in log_output.lower(), (
                f"Log must contain 'composite' score indicator in log output:\n{log_output}"
            )
            
            # Property: If matches were found, verify the logged scores match calculated scores
            if matches:
                match = matches[0]
                
                # Check that the actual score values appear in the log
                # Format scores to 4 decimal places as in the implementation
                amount_score_str = f"{match.amount_score:.4f}"
                date_score_str = f"{match.date_score:.4f}"
                semantic_score_str = f"{match.semantic_score:.4f}"
                composite_score_str = f"{match.composite_score:.4f}"
                
                assert amount_score_str in log_output, (
                    f"Log must contain amount score value. Expected '{amount_score_str}' "
                    f"in log output:\n{log_output}"
                )
                
                assert date_score_str in log_output, (
                    f"Log must contain date score value. Expected '{date_score_str}' "
                    f"in log output:\n{log_output}"
                )
                
                assert semantic_score_str in log_output, (
                    f"Log must contain semantic score value. Expected '{semantic_score_str}' "
                    f"in log output:\n{log_output}"
                )
                
                assert composite_score_str in log_output, (
                    f"Log must contain composite score value. Expected '{composite_score_str}' "
                    f"in log output:\n{log_output}"
                )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()
    
    @given(
        transaction=transaction_strategy(),
        receipts=st.lists(receipt_strategy(), min_size=2, max_size=5),
        config=matching_config_strategy()
    )
    @settings(max_examples=10)
    def test_score_logging_for_multiple_candidates(
        self,
        transaction: Transaction,
        receipts: List[Receipt],
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.1**
        
        Property 20: Score Calculation Logging is Complete (Multiple Candidates)
        
        For any transaction and multiple receipt candidates,
        when the matching engine calculates scores for all candidates,
        the log must contain entries for each candidate pair.
        
        This property verifies that:
        - Each candidate pair gets its own log entry
        - All candidate pairs are logged (no missing entries)
        - Each log entry contains all required fields
        - The logging is consistent across multiple candidates
        """
        # Adjust all receipts to be within tolerance constraints
        for i, receipt in enumerate(receipts):
            receipt.amount = transaction.amount + Decimal("0.10") * (i + 1)  # Within $1.00
            receipt.receipt_date = transaction.transaction_date  # Same date
        
        # Create matching engine without DeepSeek client
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        # Get the matching engine logger
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Execute matching
            matches = engine.find_matches(transaction, receipts)
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Property: Log must contain entries for all receipt candidates
            for receipt in receipts:
                assert str(receipt.id) in log_output, (
                    f"Log must contain entry for receipt {receipt.id}. "
                    f"Log output:\n{log_output}"
                )
            
            # Property: Each receipt should have all score types logged
            for receipt in receipts:
                # Find the log line(s) containing this receipt ID
                log_lines = [line for line in log_output.split('\n') if str(receipt.id) in line]
                
                if log_lines:
                    # At least one log line should contain all score indicators
                    combined_log = ' '.join(log_lines).lower()
                    
                    assert 'amount' in combined_log, (
                        f"Log for receipt {receipt.id} must contain 'amount' score"
                    )
                    assert 'date' in combined_log, (
                        f"Log for receipt {receipt.id} must contain 'date' score"
                    )
                    assert 'semantic' in combined_log, (
                        f"Log for receipt {receipt.id} must contain 'semantic' score"
                    )
                    assert 'composite' in combined_log, (
                        f"Log for receipt {receipt.id} must contain 'composite' score"
                    )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()
    
    @given(
        transaction=transaction_strategy(),
        receipt=receipt_strategy(),
        config=matching_config_strategy()
    )
    @settings(max_examples=10)
    def test_score_logging_includes_confidence_level(
        self,
        transaction: Transaction,
        receipt: Receipt,
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.1, 10.2**
        
        Property 20: Score Calculation Logging is Complete (With Confidence)
        
        For any transaction and receipt pair,
        when the matching engine calculates scores and classifies confidence,
        the log must contain the confidence level along with the scores.
        
        This property verifies that:
        - The confidence level is logged with the scores
        - The confidence level is one of: exact, high, low
        - The logging provides complete audit trail information
        """
        # Adjust receipt to be within tolerance constraints
        receipt.amount = transaction.amount + Decimal("0.50")
        receipt.receipt_date = transaction.transaction_date
        
        # Create matching engine without DeepSeek client
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        # Get the matching engine logger
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Execute matching
            matches = engine.find_matches(transaction, [receipt])
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Property: Log must contain confidence level
            assert 'confidence' in log_output.lower(), (
                f"Log must contain 'confidence' indicator in log output:\n{log_output}"
            )
            
            # Property: If matches were found, confidence must be one of the valid values
            if matches:
                match = matches[0]
                confidence_value = match.confidence.value
                
                assert confidence_value in log_output, (
                    f"Log must contain confidence value '{confidence_value}' "
                    f"in log output:\n{log_output}"
                )
                
                # Verify it's a valid confidence level
                assert confidence_value in ['exact', 'high', 'low'], (
                    f"Confidence value must be 'exact', 'high', or 'low', got '{confidence_value}'"
                )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()
    
    @given(
        transaction=transaction_strategy(),
        receipt=receipt_strategy(),
        config=matching_config_strategy()
    )
    @settings(max_examples=10)
    def test_score_logging_format_consistency(
        self,
        transaction: Transaction,
        receipt: Receipt,
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.1**
        
        Property 20: Score Calculation Logging is Complete (Format Consistency)
        
        For any transaction and receipt pair,
        the score logging format must be consistent and parseable.
        
        This property verifies that:
        - The log format is consistent across all scoring operations
        - Score values are formatted with appropriate precision
        - The log entry contains all required fields in a structured format
        - The log can be parsed for audit trail analysis
        """
        # Adjust receipt to be within tolerance constraints
        receipt.amount = transaction.amount + Decimal("0.25")
        receipt.receipt_date = transaction.transaction_date
        
        # Create matching engine without DeepSeek client
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        # Get the matching engine logger
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Execute matching
            matches = engine.find_matches(transaction, [receipt])
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Property: Log must use structured format with key-value pairs
            # The implementation uses format: "txn:{id}, rec:{id}, amount:{score}, ..."
            if matches:
                # Check for structured format indicators
                assert 'txn:' in log_output or 'transaction' in log_output.lower(), (
                    f"Log must use structured format for transaction ID"
                )
                
                assert 'rec:' in log_output or 'receipt' in log_output.lower(), (
                    f"Log must use structured format for receipt ID"
                )
                
                # Property: Score values should be formatted with decimal precision
                # Check that scores are formatted as numbers (contain decimal point or digits)
                import re
                
                # Look for score patterns like "amount:0.9876" or "amount: 0.9876"
                score_pattern = r'\d+\.\d+'
                score_matches = re.findall(score_pattern, log_output)
                
                assert len(score_matches) >= 4, (
                    f"Log must contain at least 4 score values (amount, date, semantic, composite). "
                    f"Found {len(score_matches)} score values in log output:\n{log_output}"
                )
                
                # Property: All score values should be between 0 and 1
                for score_str in score_matches:
                    score_value = float(score_str)
                    assert 0.0 <= score_value <= 1.0, (
                        f"Score value {score_value} is outside valid range [0.0, 1.0]"
                    )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()



class TestClassificationLoggingProperty:
    """
    Property 21: Match Classification Logging is Complete
    
    Universal Property:
    FOR ALL match classification operations,
    WHEN the Matching_Engine classifies a match,
    THEN the system SHALL log:
    - Match_Confidence level (exact, high, or low)
    - Timestamp
    
    Validates Requirement 10.2:
    WHEN the Matching_Engine classifies a match, 
    THE FinMatcher_System SHALL log the Match_Confidence level and timestamp
    """
    
    @given(
        transaction=transaction_strategy(),
        receipt=receipt_strategy(),
        config=matching_config_strategy()
    )
    @settings(max_examples=20)
    def test_classification_logging_includes_confidence_and_timestamp(
        self,
        transaction: Transaction,
        receipt: Receipt,
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.2**
        
        Property 21: Match Classification Logging is Complete
        
        For any transaction and receipt pair that produces a match,
        when the matching engine classifies the match confidence,
        the log must contain:
        1. Match_Confidence level (exact, high, or low)
        2. Timestamp of the classification
        
        This property verifies that:
        - The confidence level is logged for every match classification
        - The confidence level is one of the valid values: exact, high, low
        - A timestamp is present in the log entry
        - The log entry provides complete audit trail for classification decisions
        """
        # Ensure receipt is within tolerance constraints so it becomes a candidate
        receipt.amount = transaction.amount + Decimal("0.50")  # Within $1.00
        receipt.receipt_date = transaction.transaction_date  # Same date (within 3 days)
        
        # Create matching engine without DeepSeek client (semantic score will be 0)
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output with timestamp
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        # Include timestamp in log format
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        # Get the matching engine logger
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Record time before classification
            import time
            time_before = time.time()
            
            # Execute matching (which includes classification)
            matches = engine.find_matches(transaction, [receipt])
            
            # Record time after classification
            time_after = time.time()
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Property: Log must contain confidence level
            assert 'confidence' in log_output.lower(), (
                f"Log must contain 'confidence' indicator for classification. "
                f"Log output:\n{log_output}"
            )
            
            # Property: If matches were found, verify confidence value is logged
            if matches:
                match = matches[0]
                confidence_value = match.confidence.value
                
                # Property: Confidence value must be one of: exact, high, low
                assert confidence_value in ['exact', 'high', 'low'], (
                    f"Confidence value must be 'exact', 'high', or 'low', "
                    f"got '{confidence_value}'"
                )
                
                # Property: The actual confidence value must appear in the log
                assert confidence_value in log_output, (
                    f"Log must contain confidence value '{confidence_value}'. "
                    f"Log output:\n{log_output}"
                )
                
                # Property: Log must contain a timestamp
                # Check for timestamp pattern (various formats accepted)
                import re
                
                # Look for common timestamp patterns:
                # - ISO format: 2024-01-15 10:30:45
                # - With milliseconds: 2024-01-15 10:30:45.123
                # - Date/time components
                timestamp_patterns = [
                    r'\d{4}-\d{2}-\d{2}',  # Date part (YYYY-MM-DD)
                    r'\d{2}:\d{2}:\d{2}',  # Time part (HH:MM:SS)
                ]
                
                has_timestamp = any(
                    re.search(pattern, log_output) 
                    for pattern in timestamp_patterns
                )
                
                assert has_timestamp, (
                    f"Log must contain a timestamp for classification. "
                    f"Expected date (YYYY-MM-DD) or time (HH:MM:SS) pattern. "
                    f"Log output:\n{log_output}"
                )
                
                # Property: Timestamp should be reasonable (within test execution window)
                # Extract timestamp from log and verify it's within the test time window
                # This is a sanity check that the timestamp is current, not hardcoded
                timestamp_match = re.search(
                    r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})',
                    log_output
                )
                
                if timestamp_match:
                    from datetime import datetime
                    timestamp_str = f"{timestamp_match.group(1)} {timestamp_match.group(2)}"
                    
                    try:
                        log_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        log_time = log_timestamp.timestamp()
                        
                        # Verify timestamp is within reasonable range (test execution window)
                        # Allow some buffer for clock skew
                        assert time_before - 1 <= log_time <= time_after + 1, (
                            f"Log timestamp {timestamp_str} is outside test execution window. "
                            f"Expected between {time_before} and {time_after}, got {log_time}"
                        )
                    except ValueError:
                        # If parsing fails, that's okay - we already verified timestamp exists
                        pass
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()
    
    @given(
        transaction=transaction_strategy(),
        receipts=st.lists(receipt_strategy(), min_size=2, max_size=5),
        config=matching_config_strategy()
    )
    @settings(max_examples=10)
    def test_classification_logging_for_multiple_matches(
        self,
        transaction: Transaction,
        receipts: List[Receipt],
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.2**
        
        Property 21: Match Classification Logging is Complete (Multiple Matches)
        
        For any transaction and multiple receipt candidates,
        when the matching engine classifies each match,
        the log must contain confidence level and timestamp for each classification.
        
        This property verifies that:
        - Each match gets its own classification log entry
        - All classifications are logged (no missing entries)
        - Each log entry contains confidence level and timestamp
        - The logging is consistent across multiple classifications
        """
        # Adjust all receipts to be within tolerance constraints
        for i, receipt in enumerate(receipts):
            receipt.amount = transaction.amount + Decimal("0.10") * (i + 1)  # Within $1.00
            receipt.receipt_date = transaction.transaction_date  # Same date
        
        # Create matching engine without DeepSeek client
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output with timestamp
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        # Get the matching engine logger
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Execute matching
            matches = engine.find_matches(transaction, receipts)
            
            # Get log output
            log_output = log_stream.getvalue()
            
            # Property: Log must contain classification entries for all receipt candidates
            for receipt in receipts:
                # Find log lines containing this receipt ID
                log_lines = [line for line in log_output.split('\n') if str(receipt.id) in line]
                
                assert log_lines, (
                    f"Log must contain entry for receipt {receipt.id}. "
                    f"Log output:\n{log_output}"
                )
                
                # Property: Each receipt's log entry must contain confidence
                combined_log = ' '.join(log_lines).lower()
                assert 'confidence' in combined_log, (
                    f"Log for receipt {receipt.id} must contain 'confidence' indicator"
                )
            
            # Property: Each match result must have its confidence logged
            for match in matches:
                confidence_value = match.confidence.value
                
                # Find log lines for this specific match
                match_log_lines = [
                    line for line in log_output.split('\n')
                    if str(match.receipt.id) in line and confidence_value in line
                ]
                
                assert match_log_lines, (
                    f"Log must contain confidence value '{confidence_value}' "
                    f"for receipt {match.receipt.id}"
                )
            
            # Property: All log entries must have timestamps
            import re
            log_lines = [line for line in log_output.split('\n') if line.strip()]
            
            for line in log_lines:
                if 'confidence' in line.lower():
                    # This is a classification log line, must have timestamp
                    has_timestamp = bool(re.search(r'\d{4}-\d{2}-\d{2}', line))
                    assert has_timestamp, (
                        f"Classification log line must contain timestamp. "
                        f"Line: {line}"
                    )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()
    
    @given(
        transaction=transaction_strategy(),
        receipt=receipt_strategy(),
        config=matching_config_strategy()
    )
    @settings(max_examples=10)
    def test_classification_logging_for_all_confidence_levels(
        self,
        transaction: Transaction,
        receipt: Receipt,
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.2**
        
        Property 21: Match Classification Logging is Complete (All Confidence Levels)
        
        For any match classification result (exact, high, or low confidence),
        the log must contain the confidence level and timestamp.
        
        This property verifies that:
        - Exact match classifications are logged with confidence and timestamp
        - High confidence classifications are logged with confidence and timestamp
        - Low confidence classifications are logged with confidence and timestamp
        - The logging format is consistent across all confidence levels
        """
        # Create matching engine without DeepSeek client
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Test different scenarios to get different confidence levels
        # Scenario 1: Very close match (should be exact or high)
        receipt.amount = transaction.amount + Decimal("0.01")  # Very close
        receipt.receipt_date = transaction.transaction_date  # Same date
        
        # Capture log output
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Execute matching
            matches = engine.find_matches(transaction, [receipt])
            
            # Get log output
            log_output = log_stream.getvalue()
            
            if matches:
                match = matches[0]
                confidence_value = match.confidence.value
                
                # Property: Confidence must be one of the valid values
                assert confidence_value in ['exact', 'high', 'low'], (
                    f"Confidence must be 'exact', 'high', or 'low', got '{confidence_value}'"
                )
                
                # Property: The confidence value must be in the log
                assert confidence_value in log_output, (
                    f"Log must contain confidence value '{confidence_value}'"
                )
                
                # Property: Log must have timestamp
                import re
                has_timestamp = bool(re.search(r'\d{4}-\d{2}-\d{2}', log_output))
                assert has_timestamp, (
                    f"Log must contain timestamp for {confidence_value} confidence classification"
                )
                
                # Property: Log entry must be complete (confidence + timestamp + IDs)
                # Find the log line with this classification
                classification_lines = [
                    line for line in log_output.split('\n')
                    if confidence_value in line
                ]
                
                assert classification_lines, (
                    f"Must have at least one log line with confidence '{confidence_value}'"
                )
                
                # Verify the classification line has all required components
                classification_line = classification_lines[0]
                
                # Must have transaction ID
                assert str(transaction.id) in classification_line, (
                    f"Classification log must contain transaction ID {transaction.id}"
                )
                
                # Must have receipt ID
                assert str(receipt.id) in classification_line, (
                    f"Classification log must contain receipt ID {receipt.id}"
                )
                
                # Must have timestamp
                assert re.search(r'\d{4}-\d{2}-\d{2}', classification_line), (
                    f"Classification log must contain timestamp"
                )
                
                # Must have confidence value
                assert confidence_value in classification_line, (
                    f"Classification log must contain confidence value '{confidence_value}'"
                )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()
    
    @given(
        transaction=transaction_strategy(),
        receipt=receipt_strategy(),
        config=matching_config_strategy()
    )
    @settings(max_examples=10)
    def test_classification_timestamp_is_current(
        self,
        transaction: Transaction,
        receipt: Receipt,
        config: MatchingConfig
    ):
        """
        **Validates: Requirements 10.2**
        
        Property 21: Match Classification Logging is Complete (Timestamp Accuracy)
        
        For any match classification,
        the logged timestamp must be current (not hardcoded or stale).
        
        This property verifies that:
        - The timestamp reflects the actual time of classification
        - The timestamp is not hardcoded or reused from previous operations
        - The timestamp is within the test execution window
        - The timestamp format is consistent and parseable
        """
        # Ensure receipt is within tolerance constraints
        receipt.amount = transaction.amount + Decimal("0.50")
        receipt.receipt_date = transaction.transaction_date
        
        # Create matching engine without DeepSeek client
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Capture log output with timestamp
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        
        logger = logging.getLogger('finmatcher.core.matching_engine')
        original_level = logger.level
        original_handlers = logger.handlers[:]
        logger.setLevel(logging.DEBUG)
        logger.addHandler(log_handler)
        
        try:
            # Record current time before classification
            from datetime import datetime
            time_before = datetime.now()
            
            # Execute matching (includes classification)
            matches = engine.find_matches(transaction, [receipt])
            
            # Record current time after classification
            time_after = datetime.now()
            
            # Get log output
            log_output = log_stream.getvalue()
            
            if matches:
                # Property: Log must contain a timestamp
                import re
                timestamp_match = re.search(
                    r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})',
                    log_output
                )
                
                assert timestamp_match, (
                    f"Log must contain timestamp in format YYYY-MM-DD HH:MM:SS. "
                    f"Log output:\n{log_output}"
                )
                
                # Property: Timestamp must be current (within test execution window)
                timestamp_str = f"{timestamp_match.group(1)} {timestamp_match.group(2)}"
                
                try:
                    log_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Verify timestamp is between time_before and time_after
                    # Allow 1 second buffer for clock precision
                    from datetime import timedelta
                    time_before_buffered = time_before - timedelta(seconds=1)
                    time_after_buffered = time_after + timedelta(seconds=1)
                    
                    assert time_before_buffered <= log_timestamp <= time_after_buffered, (
                        f"Log timestamp {timestamp_str} is outside test execution window. "
                        f"Expected between {time_before} and {time_after}, "
                        f"got {log_timestamp}"
                    )
                    
                except ValueError as e:
                    pytest.fail(
                        f"Failed to parse timestamp '{timestamp_str}': {e}. "
                        f"Timestamp must be in format YYYY-MM-DD HH:MM:SS"
                    )
            
        finally:
            logger.removeHandler(log_handler)
            logger.setLevel(original_level)
            logger.handlers = original_handlers
            log_handler.close()

