"""
Property-based tests for Weight Normalization.

This module contains property-based tests using Hypothesis to verify
universal properties of the weight validation and normalization system.

Testing Framework: Hypothesis (Python)
Feature: finmatcher-v2-upgrade
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict

from finmatcher.config.configuration_manager import ConfigurationManager


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=20)
settings.load_profile("finmatcher")


class TestWeightNormalization:
    """
    Property tests for weight validation and normalization.
    
    Feature: finmatcher-v2-upgrade
    Property 27: Weight Validation and Normalization
    **Validates: Requirements 12.2, 12.3**
    """
    
    @given(
        w_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_s=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_normalized_weights_sum_to_one(self, w_a: float, w_d: float, w_s: float):
        """
        Property 27: Normalized Weights Sum to 1.0.
        
        For any set of scoring weights (W_a, W_d, W_s), the normalized weights
        must sum to 1.0 (within floating-point tolerance).
        
        **Validates: Requirements 12.2, 12.3**
        """
        # Arrange
        config_manager = ConfigurationManager()
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - Normalized weights must sum to 1.0
        total = normalized['amount'] + normalized['date'] + normalized['semantic']
        assert abs(total - 1.0) < 0.0001, (
            f"Normalized weights must sum to 1.0, got {total}. "
            f"Input: {weights}, Output: {normalized}"
        )
    
    @given(
        w_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_s=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_proportions_maintained_after_normalization(
        self, 
        w_a: float, 
        w_d: float, 
        w_s: float
    ):
        """
        Property 27: Proportions Maintained After Normalization.
        
        For any set of non-zero weights, the normalized weights must maintain
        the same proportional relationships as the original weights.
        
        **Validates: Requirements 12.3**
        """
        # Arrange
        config_manager = ConfigurationManager()
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Skip if all weights are zero (special case)
        total_input = w_a + w_d + w_s
        assume(total_input > 0.0001)
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - Proportions must be maintained
        original_ratio_a = w_a / total_input
        original_ratio_d = w_d / total_input
        original_ratio_s = w_s / total_input
        
        normalized_ratio_a = normalized['amount']
        normalized_ratio_d = normalized['date']
        normalized_ratio_s = normalized['semantic']
        
        assert abs(original_ratio_a - normalized_ratio_a) < 0.001, (
            f"Amount weight proportion not maintained. "
            f"Original: {original_ratio_a}, Normalized: {normalized_ratio_a}"
        )
        assert abs(original_ratio_d - normalized_ratio_d) < 0.001, (
            f"Date weight proportion not maintained. "
            f"Original: {original_ratio_d}, Normalized: {normalized_ratio_d}"
        )
        assert abs(original_ratio_s - normalized_ratio_s) < 0.001, (
            f"Semantic weight proportion not maintained. "
            f"Original: {original_ratio_s}, Normalized: {normalized_ratio_s}"
        )
    
    @given(
        base_weight=st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_weights_already_normalized_unchanged(self, base_weight: float):
        """
        Property 27: Weights Already Summing to 1.0 Are Unchanged.
        
        For any set of weights that already sum to 1.0 (within tolerance),
        the normalization function must return them unchanged.
        
        **Validates: Requirements 12.2**
        """
        # Arrange
        config_manager = ConfigurationManager()
        
        # Create weights that sum to 1.0
        w_a = base_weight
        w_d = (1.0 - base_weight) / 2
        w_s = (1.0 - base_weight) / 2
        
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Verify they sum to 1.0
        total = w_a + w_d + w_s
        assume(abs(total - 1.0) < 0.001)
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - Weights should be unchanged (within tolerance)
        assert abs(normalized['amount'] - w_a) < 0.0001, (
            f"Amount weight changed unnecessarily. "
            f"Original: {w_a}, Normalized: {normalized['amount']}"
        )
        assert abs(normalized['date'] - w_d) < 0.0001, (
            f"Date weight changed unnecessarily. "
            f"Original: {w_d}, Normalized: {normalized['date']}"
        )
        assert abs(normalized['semantic'] - w_s) < 0.0001, (
            f"Semantic weight changed unnecessarily. "
            f"Original: {w_s}, Normalized: {normalized['semantic']}"
        )
    
    @given(
        w_a=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        w_s=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_normalization_handles_any_positive_weights(
        self, 
        w_a: float, 
        w_d: float, 
        w_s: float
    ):
        """
        Property 27: Normalization Handles Any Positive Weights.
        
        For any set of positive weights (even if they sum to values > 1.0),
        the normalization function must produce valid normalized weights.
        
        **Validates: Requirements 12.3**
        """
        # Arrange
        config_manager = ConfigurationManager()
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Skip if all weights are zero
        total_input = w_a + w_d + w_s
        assume(total_input > 0.0001)
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - All normalized weights must be non-negative
        assert normalized['amount'] >= 0, (
            f"Amount weight must be non-negative, got {normalized['amount']}"
        )
        assert normalized['date'] >= 0, (
            f"Date weight must be non-negative, got {normalized['date']}"
        )
        assert normalized['semantic'] >= 0, (
            f"Semantic weight must be non-negative, got {normalized['semantic']}"
        )
        
        # Assert - Normalized weights must sum to 1.0
        total = normalized['amount'] + normalized['date'] + normalized['semantic']
        assert abs(total - 1.0) < 0.0001, (
            f"Normalized weights must sum to 1.0, got {total}"
        )
    
    def test_all_zero_weights_handled_gracefully(self):
        """
        Property 27: All Zero Weights Handled Gracefully.
        
        When all weights are zero (edge case), the normalization function
        must handle it gracefully by returning equal weights (1/3 each).
        
        **Validates: Requirements 12.3**
        """
        # Arrange
        config_manager = ConfigurationManager()
        weights = {'amount': 0.0, 'date': 0.0, 'semantic': 0.0}
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - Should return equal weights
        assert abs(normalized['amount'] - 1/3) < 0.0001, (
            f"Amount weight should be 1/3 for zero input, got {normalized['amount']}"
        )
        assert abs(normalized['date'] - 1/3) < 0.0001, (
            f"Date weight should be 1/3 for zero input, got {normalized['date']}"
        )
        assert abs(normalized['semantic'] - 1/3) < 0.0001, (
            f"Semantic weight should be 1/3 for zero input, got {normalized['semantic']}"
        )
        
        # Assert - Must still sum to 1.0
        total = normalized['amount'] + normalized['date'] + normalized['semantic']
        assert abs(total - 1.0) < 0.0001, (
            f"Normalized weights must sum to 1.0, got {total}"
        )
    
    @given(
        w_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_s=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_normalization_is_idempotent(
        self, 
        w_a: float, 
        w_d: float, 
        w_s: float
    ):
        """
        Property 27: Normalization is Idempotent.
        
        For any set of weights, normalizing them twice must produce the
        same result as normalizing them once.
        
        **Validates: Requirements 12.3**
        """
        # Arrange
        config_manager = ConfigurationManager()
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Act
        normalized_once = config_manager.validate_and_normalize_weights(weights)
        normalized_twice = config_manager.validate_and_normalize_weights(normalized_once)
        
        # Assert - Second normalization should produce same result
        assert abs(normalized_once['amount'] - normalized_twice['amount']) < 0.0001, (
            f"Amount weight changed on second normalization. "
            f"First: {normalized_once['amount']}, Second: {normalized_twice['amount']}"
        )
        assert abs(normalized_once['date'] - normalized_twice['date']) < 0.0001, (
            f"Date weight changed on second normalization. "
            f"First: {normalized_once['date']}, Second: {normalized_twice['date']}"
        )
        assert abs(normalized_once['semantic'] - normalized_twice['semantic']) < 0.0001, (
            f"Semantic weight changed on second normalization. "
            f"First: {normalized_once['semantic']}, Second: {normalized_twice['semantic']}"
        )
    
    @given(
        w_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_s=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_normalized_weights_are_valid_probabilities(
        self, 
        w_a: float, 
        w_d: float, 
        w_s: float
    ):
        """
        Property 27: Normalized Weights Are Valid Probabilities.
        
        For any set of weights, the normalized weights must be valid
        probabilities (between 0 and 1, inclusive).
        
        **Validates: Requirements 12.2, 12.3**
        """
        # Arrange
        config_manager = ConfigurationManager()
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - Each weight must be between 0 and 1
        assert 0.0 <= normalized['amount'] <= 1.0, (
            f"Amount weight must be in [0, 1], got {normalized['amount']}"
        )
        assert 0.0 <= normalized['date'] <= 1.0, (
            f"Date weight must be in [0, 1], got {normalized['date']}"
        )
        assert 0.0 <= normalized['semantic'] <= 1.0, (
            f"Semantic weight must be in [0, 1], got {normalized['semantic']}"
        )
    
    @given(
        w_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_two_weights_determine_third(self, w_a: float, w_d: float):
        """
        Property 27: Two Weights Determine the Third.
        
        For any two weights, the third weight is determined by the constraint
        that all three must sum to 1.0 after normalization.
        
        **Validates: Requirements 12.2**
        """
        # Arrange
        config_manager = ConfigurationManager()
        
        # Create weights where third is derived
        w_s = 1.0 - w_a - w_d
        
        # Only test when all weights are non-negative
        assume(w_s >= 0.0)
        
        weights = {'amount': w_a, 'date': w_d, 'semantic': w_s}
        
        # Act
        normalized = config_manager.validate_and_normalize_weights(weights)
        
        # Assert - Must sum to 1.0
        total = normalized['amount'] + normalized['date'] + normalized['semantic']
        assert abs(total - 1.0) < 0.0001, (
            f"Normalized weights must sum to 1.0, got {total}"
        )
        
        # Assert - If input already sums to 1.0, output should match input
        input_total = w_a + w_d + w_s
        if abs(input_total - 1.0) < 0.001:
            assert abs(normalized['amount'] - w_a) < 0.0001
            assert abs(normalized['date'] - w_d) < 0.0001
            assert abs(normalized['semantic'] - w_s) < 0.0001
