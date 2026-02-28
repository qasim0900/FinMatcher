"""
Unit tests for FeatureVector and NormalizationParams data classes.

Validates Requirements: 1.4, 10.11
"""

import pytest
import numpy as np
from datetime import date, datetime
from decimal import Decimal

from finmatcher.optimization.data_models import FeatureVector, NormalizationParams


def date_to_timestamp(date_val: date) -> int:
    """Helper function to convert date to Unix timestamp."""
    return int(datetime.combine(date_val, datetime.min.time()).timestamp())


class TestFeatureVector:
    """Test suite for FeatureVector dataclass."""
    
    def test_feature_vector_creation(self):
        """Test basic FeatureVector instantiation."""
        fv = FeatureVector(
            amount_normalized=0.5,
            date_normalized=0.75,
            receipt_id=1,
            original_amount=Decimal("100.00"),
            original_date=date(2024, 1, 1)
        )
        
        assert fv.amount_normalized == 0.5
        assert fv.date_normalized == 0.75
        assert fv.receipt_id == 1
        assert fv.original_amount == Decimal("100.00")
        assert fv.original_date == date(2024, 1, 1)
    
    def test_to_array(self):
        """Test conversion to NumPy array."""
        fv = FeatureVector(
            amount_normalized=0.5,
            date_normalized=0.75,
            receipt_id=1,
            original_amount=Decimal("100.00"),
            original_date=date(2024, 1, 1)
        )
        
        arr = fv.to_array()
        
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (2,)
        assert arr[0] == 0.5
        assert arr[1] == 0.75
    
    def test_str_representation(self):
        """Test pretty printing for debugging."""
        fv = FeatureVector(
            amount_normalized=0.5,
            date_normalized=0.75,
            receipt_id=1,
            original_amount=Decimal("100.00"),
            original_date=date(2024, 1, 1)
        )
        
        str_repr = str(fv)
        
        assert "FeatureVector" in str_repr
        assert "id=1" in str_repr
        assert "100.00" in str_repr
        assert "0.5000" in str_repr
        assert "2024-01-01" in str_repr
        assert "0.7500" in str_repr
    
    def test_normalized_values_in_range(self):
        """Test that normalized values are in [0,1] range."""
        fv = FeatureVector(
            amount_normalized=0.0,
            date_normalized=1.0,
            receipt_id=1,
            original_amount=Decimal("0.00"),
            original_date=date(2024, 1, 1)
        )
        
        assert 0.0 <= fv.amount_normalized <= 1.0
        assert 0.0 <= fv.date_normalized <= 1.0


class TestNormalizationParams:
    """Test suite for NormalizationParams dataclass."""
    
    def test_normalization_params_creation(self):
        """Test basic NormalizationParams instantiation."""
        params = NormalizationParams(
            amount_min=Decimal("0.00"),
            amount_max=Decimal("100.00"),
            date_min=date_to_timestamp(date(2024, 1, 1)),
            date_max=date_to_timestamp(date(2024, 12, 31)),
            dataset_hash="abc123"
        )
        
        assert params.amount_min == Decimal("0.00")
        assert params.amount_max == Decimal("100.00")
        assert params.dataset_hash == "abc123"
    
    def test_normalize_amount_basic(self):
        """Test amount normalization with basic values."""
        params = NormalizationParams(
            amount_min=Decimal("0.00"),
            amount_max=Decimal("100.00"),
            date_min=0,
            date_max=100,
            dataset_hash="hash"
        )
        
        # Test min value
        assert params.normalize_amount(Decimal("0.00")) == 0.0
        
        # Test max value
        assert params.normalize_amount(Decimal("100.00")) == 1.0
        
        # Test mid value
        assert params.normalize_amount(Decimal("50.00")) == 0.5
        
        # Test quarter value
        assert params.normalize_amount(Decimal("25.00")) == 0.25
    
    def test_normalize_amount_edge_case_single_value(self):
        """Test amount normalization when min equals max."""
        params = NormalizationParams(
            amount_min=Decimal("50.00"),
            amount_max=Decimal("50.00"),
            date_min=0,
            date_max=100,
            dataset_hash="hash"
        )
        
        # Should return 0.5 for edge case
        assert params.normalize_amount(Decimal("50.00")) == 0.5
    
    def test_normalize_date_basic(self):
        """Test date normalization with basic values."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)
        
        params = NormalizationParams(
            amount_min=Decimal("0.00"),
            amount_max=Decimal("100.00"),
            date_min=date_to_timestamp(start_date),
            date_max=date_to_timestamp(end_date),
            dataset_hash="hash"
        )
        
        # Test min date
        normalized_min = params.normalize_date(start_date)
        assert normalized_min == 0.0
        
        # Test max date
        normalized_max = params.normalize_date(end_date)
        assert normalized_max == 1.0
        
        # Test mid-year date (approximately 0.5)
        mid_date = date(2024, 7, 1)
        normalized_mid = params.normalize_date(mid_date)
        assert 0.4 < normalized_mid < 0.6  # Approximately 0.5
    
    def test_normalize_date_edge_case_single_value(self):
        """Test date normalization when min equals max."""
        single_date = date(2024, 6, 15)
        
        params = NormalizationParams(
            amount_min=Decimal("0.00"),
            amount_max=Decimal("100.00"),
            date_min=date_to_timestamp(single_date),
            date_max=date_to_timestamp(single_date),
            dataset_hash="hash"
        )
        
        # Should return 0.5 for edge case
        assert params.normalize_date(single_date) == 0.5
    
    def test_normalization_produces_valid_range(self):
        """Test that normalization always produces values in [0,1]."""
        params = NormalizationParams(
            amount_min=Decimal("10.00"),
            amount_max=Decimal("1000.00"),
            date_min=date_to_timestamp(date(2024, 1, 1)),
            date_max=date_to_timestamp(date(2024, 12, 31)),
            dataset_hash="hash"
        )
        
        # Test various amounts
        for amount in [Decimal("10.00"), Decimal("100.00"), Decimal("500.00"), Decimal("1000.00")]:
            normalized = params.normalize_amount(amount)
            assert 0.0 <= normalized <= 1.0
        
        # Test various dates
        for month in range(1, 13):
            test_date = date(2024, month, 1)
            normalized = params.normalize_date(test_date)
            assert 0.0 <= normalized <= 1.0


class TestIntegration:
    """Integration tests for FeatureVector and NormalizationParams."""
    
    def test_round_trip_normalization(self):
        """Test creating FeatureVector using NormalizationParams."""
        # Setup normalization parameters
        params = NormalizationParams(
            amount_min=Decimal("0.00"),
            amount_max=Decimal("100.00"),
            date_min=date_to_timestamp(date(2024, 1, 1)),
            date_max=date_to_timestamp(date(2024, 12, 31)),
            dataset_hash="test_hash"
        )
        
        # Create a receipt with raw values
        receipt_amount = Decimal("50.00")
        receipt_date = date(2024, 7, 1)
        receipt_id = 42
        
        # Normalize using params
        amount_norm = params.normalize_amount(receipt_amount)
        date_norm = params.normalize_date(receipt_date)
        
        # Create FeatureVector
        fv = FeatureVector(
            amount_normalized=amount_norm,
            date_normalized=date_norm,
            receipt_id=receipt_id,
            original_amount=receipt_amount,
            original_date=receipt_date
        )
        
        # Verify the feature vector
        assert fv.receipt_id == receipt_id
        assert fv.original_amount == receipt_amount
        assert fv.original_date == receipt_date
        assert 0.0 <= fv.amount_normalized <= 1.0
        assert 0.0 <= fv.date_normalized <= 1.0
        
        # Verify array conversion
        arr = fv.to_array()
        assert arr.shape == (2,)
        assert arr[0] == amount_norm
        assert arr[1] == date_norm


class TestSerialization:
    """Test suite for serialization and round-trip properties."""
    
    def test_feature_vector_pickle_serialization(self):
        """Test FeatureVector pickle serialization round-trip."""
        import pickle
        
        # Create original FeatureVector
        original = FeatureVector(
            amount_normalized=0.5,
            date_normalized=0.75,
            receipt_id=42,
            original_amount=Decimal("100.00"),
            original_date=date(2024, 6, 15)
        )
        
        # Serialize and deserialize
        serialized = pickle.dumps(original)
        deserialized = pickle.loads(serialized)
        
        # Verify all fields match
        assert deserialized.amount_normalized == original.amount_normalized
        assert deserialized.date_normalized == original.date_normalized
        assert deserialized.receipt_id == original.receipt_id
        assert deserialized.original_amount == original.original_amount
        assert deserialized.original_date == original.original_date
        
        # Verify array conversion still works
        assert np.array_equal(deserialized.to_array(), original.to_array())
    
    def test_normalization_params_pickle_serialization(self):
        """Test NormalizationParams pickle serialization round-trip."""
        import pickle
        
        # Create original NormalizationParams
        original = NormalizationParams(
            amount_min=Decimal("10.00"),
            amount_max=Decimal("1000.00"),
            date_min=date_to_timestamp(date(2024, 1, 1)),
            date_max=date_to_timestamp(date(2024, 12, 31)),
            dataset_hash="abc123def456"
        )
        
        # Serialize and deserialize
        serialized = pickle.dumps(original)
        deserialized = pickle.loads(serialized)
        
        # Verify all fields match
        assert deserialized.amount_min == original.amount_min
        assert deserialized.amount_max == original.amount_max
        assert deserialized.date_min == original.date_min
        assert deserialized.date_max == original.date_max
        assert deserialized.dataset_hash == original.dataset_hash
        
        # Verify normalization methods still work correctly
        test_amount = Decimal("505.00")
        assert deserialized.normalize_amount(test_amount) == original.normalize_amount(test_amount)
        
        test_date = date(2024, 7, 1)
        assert deserialized.normalize_date(test_date) == original.normalize_date(test_date)
    
    def test_feature_vector_array_round_trip(self):
        """
        Test FeatureVector array round-trip property.
        
        Validates Requirement 1.11: "FOR ALL valid Feature_Vector arrays,
        parsing then printing then parsing SHALL produce an equivalent array"
        """
        # Create original FeatureVector
        original = FeatureVector(
            amount_normalized=0.3,
            date_normalized=0.8,
            receipt_id=123,
            original_amount=Decimal("75.50"),
            original_date=date(2024, 3, 15)
        )
        
        # Convert to array
        array1 = original.to_array()
        
        # Create new FeatureVector from array values
        reconstructed = FeatureVector(
            amount_normalized=float(array1[0]),
            date_normalized=float(array1[1]),
            receipt_id=original.receipt_id,
            original_amount=original.original_amount,
            original_date=original.original_date
        )
        
        # Convert reconstructed to array
        array2 = reconstructed.to_array()
        
        # Verify arrays are equivalent
        assert np.array_equal(array1, array2)
        assert array1.shape == array2.shape
        assert array1[0] == array2[0]
        assert array1[1] == array2[1]
    
    def test_multiple_feature_vectors_serialization(self):
        """Test serialization of multiple FeatureVectors (as used in K-D tree)."""
        import pickle
        
        # Create list of FeatureVectors
        original_vectors = [
            FeatureVector(0.1, 0.2, 1, Decimal("10.00"), date(2024, 1, 1)),
            FeatureVector(0.5, 0.5, 2, Decimal("50.00"), date(2024, 6, 1)),
            FeatureVector(0.9, 0.8, 3, Decimal("90.00"), date(2024, 11, 1)),
        ]
        
        # Serialize and deserialize
        serialized = pickle.dumps(original_vectors)
        deserialized_vectors = pickle.loads(serialized)
        
        # Verify all vectors match
        assert len(deserialized_vectors) == len(original_vectors)
        for original, deserialized in zip(original_vectors, deserialized_vectors):
            assert deserialized.receipt_id == original.receipt_id
            assert deserialized.amount_normalized == original.amount_normalized
            assert deserialized.date_normalized == original.date_normalized
            assert np.array_equal(deserialized.to_array(), original.to_array())
    
    def test_normalization_params_with_zero_range(self):
        """Test serialization with edge case of zero range (single value dataset)."""
        import pickle
        
        # Create params with zero range (edge case)
        original = NormalizationParams(
            amount_min=Decimal("50.00"),
            amount_max=Decimal("50.00"),  # Same as min
            date_min=date_to_timestamp(date(2024, 6, 15)),
            date_max=date_to_timestamp(date(2024, 6, 15)),  # Same as min
            dataset_hash="single_value_hash"
        )
        
        # Serialize and deserialize
        serialized = pickle.dumps(original)
        deserialized = pickle.loads(serialized)
        
        # Verify edge case handling is preserved
        assert deserialized.normalize_amount(Decimal("50.00")) == 0.5
        assert deserialized.normalize_date(date(2024, 6, 15)) == 0.5
    
    def test_feature_vector_numpy_array_serialization(self):
        """Test that NumPy arrays from FeatureVectors can be serialized."""
        import pickle
        
        # Create FeatureVectors and convert to array
        vectors = [
            FeatureVector(0.2, 0.3, 1, Decimal("20.00"), date(2024, 2, 1)),
            FeatureVector(0.6, 0.7, 2, Decimal("60.00"), date(2024, 8, 1)),
        ]
        
        # Create NumPy array (as used in K-D tree construction)
        original_array = np.array([v.to_array() for v in vectors])
        
        # Serialize and deserialize the NumPy array
        serialized = pickle.dumps(original_array)
        deserialized_array = pickle.loads(serialized)
        
        # Verify array is equivalent
        assert np.array_equal(original_array, deserialized_array)
        assert original_array.shape == deserialized_array.shape
        assert deserialized_array.shape == (2, 2)  # 2 vectors, 2 dimensions each
