"""
Unit tests for OptimizationConfig dataclass and configuration loading.

Validates Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import pytest
import os
import tempfile
import yaml
import json
from finmatcher.optimization.config import OptimizationConfig


class TestOptimizationConfigValidation:
    """Test suite for OptimizationConfig validation."""
    
    def test_default_config_is_valid(self):
        """Test that default configuration passes validation."""
        config = OptimizationConfig()
        errors = config.validate()
        assert errors == []
    
    def test_kdtree_leaf_size_validation(self):
        """Test K-D tree leaf_size parameter validation."""
        # Valid values
        config = OptimizationConfig(kdtree_leaf_size=10)
        assert config.validate() == []
        
        config = OptimizationConfig(kdtree_leaf_size=100)
        assert config.validate() == []
        
        config = OptimizationConfig(kdtree_leaf_size=40)
        assert config.validate() == []
        
        # Invalid values
        config = OptimizationConfig(kdtree_leaf_size=9)
        errors = config.validate()
        assert len(errors) == 1
        assert "kdtree_leaf_size must be between 10 and 100" in errors[0]
        
        config = OptimizationConfig(kdtree_leaf_size=101)
        errors = config.validate()
        assert len(errors) == 1
        assert "kdtree_leaf_size must be between 10 and 100" in errors[0]
    
    def test_vectorization_batch_size_validation(self):
        """Test vectorization batch_size parameter validation."""
        # Valid values
        config = OptimizationConfig(vectorization_batch_size=1000)
        assert config.validate() == []
        
        config = OptimizationConfig(vectorization_batch_size=1000000)
        assert config.validate() == []
        
        config = OptimizationConfig(vectorization_batch_size=100000)
        assert config.validate() == []
        
        # Invalid values
        config = OptimizationConfig(vectorization_batch_size=999)
        errors = config.validate()
        assert len(errors) == 1
        assert "vectorization_batch_size must be between 1000 and 1000000" in errors[0]
        
        config = OptimizationConfig(vectorization_batch_size=1000001)
        errors = config.validate()
        assert len(errors) == 1
        assert "vectorization_batch_size must be between 1000 and 1000000" in errors[0]
    
    def test_bloom_filter_error_rate_validation(self):
        """Test Bloom filter error_rate parameter validation."""
        # Valid values
        config = OptimizationConfig(bloom_filter_error_rate=0.0001)
        assert config.validate() == []
        
        config = OptimizationConfig(bloom_filter_error_rate=0.01)
        assert config.validate() == []
        
        config = OptimizationConfig(bloom_filter_error_rate=0.001)
        assert config.validate() == []
        
        # Invalid values
        config = OptimizationConfig(bloom_filter_error_rate=0.00009)
        errors = config.validate()
        assert len(errors) == 1
        assert "bloom_filter_error_rate must be between 0.0001 and 0.01" in errors[0]
        
        config = OptimizationConfig(bloom_filter_error_rate=0.011)
        errors = config.validate()
        assert len(errors) == 1
        assert "bloom_filter_error_rate must be between 0.0001 and 0.01" in errors[0]
    
    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are reported."""
        config = OptimizationConfig(
            kdtree_leaf_size=5,
            vectorization_batch_size=500,
            bloom_filter_error_rate=0.02
        )
        errors = config.validate()
        assert len(errors) == 3
        assert any("kdtree_leaf_size" in e for e in errors)
        assert any("vectorization_batch_size" in e for e in errors)
        assert any("bloom_filter_error_rate" in e for e in errors)


class TestOptimizationConfigLoading:
    """Test suite for configuration file loading."""
    
    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        # Create temporary YAML config file
        config_data = {
            'optimization': {
                'enabled': False,
                'kdtree': {
                    'leaf_size': 50,
                    'cache_enabled': False,
                    'cache_path': '/tmp/cache',
                    'cache_expiration_days': 14
                },
                'vectorization': {
                    'batch_size': 50000,
                    'enabled': False
                },
                'bloom_filter': {
                    'enabled': False,
                    'initial_capacity': 200000,
                    'error_rate': 0.0005
                },
                'performance': {
                    'query_timeout_seconds': 10,
                    'memory_limit_mb': 2048
                },
                'monitoring': {
                    'enabled': False,
                    'persist_interval': 500
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = OptimizationConfig.from_file(temp_path)
            
            # Verify all values were loaded correctly
            assert config.optimization_enabled == False
            assert config.kdtree_leaf_size == 50
            assert config.kdtree_cache_enabled == False
            assert config.kdtree_cache_path == '/tmp/cache'
            assert config.kdtree_cache_expiration_days == 14
            assert config.vectorization_batch_size == 50000
            assert config.vectorization_enabled == False
            assert config.bloom_filter_enabled == False
            assert config.bloom_filter_initial_capacity == 200000
            assert config.bloom_filter_error_rate == 0.0005
            assert config.query_timeout_seconds == 10
            assert config.memory_limit_mb == 2048
            assert config.metrics_enabled == False
            assert config.metrics_persist_interval == 500
        finally:
            os.unlink(temp_path)
    
    def test_load_from_json_file(self):
        """Test loading configuration from JSON file."""
        config_data = {
            'optimization': {
                'enabled': True,
                'kdtree': {
                    'leaf_size': 30
                },
                'vectorization': {
                    'batch_size': 75000
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = OptimizationConfig.from_file(temp_path)
            
            assert config.optimization_enabled == True
            assert config.kdtree_leaf_size == 30
            assert config.vectorization_batch_size == 75000
            # Other values should use defaults
            assert config.kdtree_cache_enabled == True
            assert config.bloom_filter_enabled == True
        finally:
            os.unlink(temp_path)
    
    def test_load_missing_file_uses_defaults(self):
        """Test that missing config file returns default configuration."""
        config = OptimizationConfig.from_file('/nonexistent/path/config.yaml')
        
        # Should return default config
        assert config.optimization_enabled == True
        assert config.kdtree_leaf_size == 40
        assert config.vectorization_batch_size == 100000
        assert config.bloom_filter_error_rate == 0.001
    
    def test_load_empty_optimization_section_uses_defaults(self):
        """Test that empty optimization section uses defaults."""
        config_data = {
            'matching': {
                'weights': {
                    'amount': 0.4
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = OptimizationConfig.from_file(temp_path)
            
            # Should use defaults
            assert config.optimization_enabled == True
            assert config.kdtree_leaf_size == 40
            assert config.vectorization_batch_size == 100000
        finally:
            os.unlink(temp_path)
    
    def test_load_partial_config_uses_defaults_for_missing(self):
        """Test that partial config uses defaults for missing values."""
        config_data = {
            'optimization': {
                'enabled': False,
                'kdtree': {
                    'leaf_size': 25
                }
                # Other sections missing
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = OptimizationConfig.from_file(temp_path)
            
            # Loaded values
            assert config.optimization_enabled == False
            assert config.kdtree_leaf_size == 25
            
            # Default values for missing sections
            assert config.kdtree_cache_enabled == True
            assert config.vectorization_batch_size == 100000
            assert config.bloom_filter_enabled == True
        finally:
            os.unlink(temp_path)
    
    def test_load_invalid_config_returns_defaults(self):
        """Test that invalid configuration returns defaults."""
        config_data = {
            'optimization': {
                'kdtree': {
                    'leaf_size': 5  # Invalid: too small
                },
                'vectorization': {
                    'batch_size': 500  # Invalid: too small
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = OptimizationConfig.from_file(temp_path)
            
            # Should return defaults due to validation errors
            assert config.kdtree_leaf_size == 40
            assert config.vectorization_batch_size == 100000
        finally:
            os.unlink(temp_path)
    
    def test_load_malformed_yaml_returns_defaults(self):
        """Test that malformed YAML returns defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [[[")
            temp_path = f.name
        
        try:
            config = OptimizationConfig.from_file(temp_path)
            
            # Should return defaults
            assert config.optimization_enabled == True
            assert config.kdtree_leaf_size == 40
        finally:
            os.unlink(temp_path)


class TestOptimizationConfigSerialization:
    """Test suite for configuration serialization."""
    
    def test_to_dict(self):
        """Test conversion to dictionary format."""
        config = OptimizationConfig(
            optimization_enabled=False,
            kdtree_leaf_size=50,
            vectorization_batch_size=50000,
            bloom_filter_error_rate=0.0005
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['enabled'] == False
        assert config_dict['kdtree']['leaf_size'] == 50
        assert config_dict['vectorization']['batch_size'] == 50000
        assert config_dict['bloom_filter']['error_rate'] == 0.0005
    
    def test_to_dict_structure(self):
        """Test that to_dict returns proper nested structure."""
        config = OptimizationConfig()
        config_dict = config.to_dict()
        
        # Verify structure
        assert 'enabled' in config_dict
        assert 'kdtree' in config_dict
        assert 'vectorization' in config_dict
        assert 'bloom_filter' in config_dict
        assert 'performance' in config_dict
        assert 'monitoring' in config_dict
        
        # Verify nested structure
        assert 'leaf_size' in config_dict['kdtree']
        assert 'cache_enabled' in config_dict['kdtree']
        assert 'batch_size' in config_dict['vectorization']
        assert 'enabled' in config_dict['vectorization']
        assert 'initial_capacity' in config_dict['bloom_filter']
        assert 'error_rate' in config_dict['bloom_filter']
