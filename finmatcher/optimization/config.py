"""
Configuration for optimization layer.
"""

import os
import yaml
import json
from dataclasses import dataclass
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """
    Configuration for optimization layer.
    
    Attributes:
        # Global Settings
        optimization_enabled: bool
        
        # K-D Tree Settings
        kdtree_leaf_size: int  # 10-100, default 40
        kdtree_cache_enabled: bool
        kdtree_cache_path: str
        kdtree_cache_expiration_days: int
        
        # Vectorization Settings
        vectorization_batch_size: int  # 1K-1M, default 100K
        vectorization_enabled: bool
        
        # Bloom Filter Settings
        bloom_filter_enabled: bool
        bloom_filter_initial_capacity: int  # default 100K
        bloom_filter_error_rate: float  # 0.0001-0.01, default 0.001
        
        # Performance Settings
        query_timeout_seconds: int  # default 5
        memory_limit_mb: int  # default 1024
        
        # Monitoring Settings
        metrics_enabled: bool
        metrics_persist_interval: int  # operations between DB writes
    """
    # Global
    optimization_enabled: bool = True
    
    # K-D Tree
    kdtree_leaf_size: int = 40
    kdtree_cache_enabled: bool = True
    kdtree_cache_path: str = ".kiro/cache"
    kdtree_cache_expiration_days: int = 7
    
    # Vectorization
    vectorization_batch_size: int = 100000
    vectorization_enabled: bool = True
    
    # Bloom Filter
    bloom_filter_enabled: bool = True
    bloom_filter_initial_capacity: int = 100000
    bloom_filter_error_rate: float = 0.001
    
    # Performance
    query_timeout_seconds: int = 5
    memory_limit_mb: int = 1024
    
    # Monitoring
    metrics_enabled: bool = True
    metrics_persist_interval: int = 1000
    
    def validate(self) -> List[str]:
        """
        Validate configuration parameters.
        
        Returns: List of validation error messages (empty if valid)
        """
        errors = []
        
        if not (10 <= self.kdtree_leaf_size <= 100):
            errors.append("kdtree_leaf_size must be between 10 and 100")
        
        if not (1000 <= self.vectorization_batch_size <= 1000000):
            errors.append("vectorization_batch_size must be between 1000 and 1000000")
        
        if not (0.0001 <= self.bloom_filter_error_rate <= 0.01):
            errors.append("bloom_filter_error_rate must be between 0.0001 and 0.01")
        
        return errors
    
    @classmethod
    def from_file(cls, config_path: str = "config.yaml") -> 'OptimizationConfig':
        """
        Load optimization configuration from file.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
            
        Returns:
            OptimizationConfig instance with loaded parameters
            
        Validates Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
        """
        try:
            # Load configuration file
            if not os.path.exists(config_path):
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return cls()
            
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    config_data = json.load(f)
                else:  # YAML
                    config_data = yaml.safe_load(f)
            
            # Extract optimization section
            optimization_section = config_data.get('optimization', {})
            
            if not optimization_section:
                logger.info("No optimization section found in config, using defaults")
                return cls()
            
            # Create config with loaded values (use defaults for missing values)
            config = cls(
                # Global
                optimization_enabled=optimization_section.get('enabled', True),
                
                # K-D Tree
                kdtree_leaf_size=optimization_section.get('kdtree', {}).get('leaf_size', 40),
                kdtree_cache_enabled=optimization_section.get('kdtree', {}).get('cache_enabled', True),
                kdtree_cache_path=optimization_section.get('kdtree', {}).get('cache_path', '.kiro/cache'),
                kdtree_cache_expiration_days=optimization_section.get('kdtree', {}).get('cache_expiration_days', 7),
                
                # Vectorization
                vectorization_batch_size=optimization_section.get('vectorization', {}).get('batch_size', 100000),
                vectorization_enabled=optimization_section.get('vectorization', {}).get('enabled', True),
                
                # Bloom Filter
                bloom_filter_enabled=optimization_section.get('bloom_filter', {}).get('enabled', True),
                bloom_filter_initial_capacity=optimization_section.get('bloom_filter', {}).get('initial_capacity', 100000),
                bloom_filter_error_rate=optimization_section.get('bloom_filter', {}).get('error_rate', 0.001),
                
                # Performance
                query_timeout_seconds=optimization_section.get('performance', {}).get('query_timeout_seconds', 5),
                memory_limit_mb=optimization_section.get('performance', {}).get('memory_limit_mb', 1024),
                
                # Monitoring
                metrics_enabled=optimization_section.get('monitoring', {}).get('enabled', True),
                metrics_persist_interval=optimization_section.get('monitoring', {}).get('persist_interval', 1000),
            )
            
            # Validate loaded configuration
            errors = config.validate()
            if errors:
                logger.error(f"Configuration validation errors: {errors}")
                logger.warning("Using default configuration due to validation errors")
                return cls()
            
            logger.info(f"Optimization configuration loaded successfully from {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading optimization configuration: {e}")
            logger.warning("Using default configuration")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dictionary representation suitable for serialization
        """
        return {
            'enabled': self.optimization_enabled,
            'kdtree': {
                'leaf_size': self.kdtree_leaf_size,
                'cache_enabled': self.kdtree_cache_enabled,
                'cache_path': self.kdtree_cache_path,
                'cache_expiration_days': self.kdtree_cache_expiration_days,
            },
            'vectorization': {
                'batch_size': self.vectorization_batch_size,
                'enabled': self.vectorization_enabled,
            },
            'bloom_filter': {
                'enabled': self.bloom_filter_enabled,
                'initial_capacity': self.bloom_filter_initial_capacity,
                'error_rate': self.bloom_filter_error_rate,
            },
            'performance': {
                'query_timeout_seconds': self.query_timeout_seconds,
                'memory_limit_mb': self.memory_limit_mb,
            },
            'monitoring': {
                'enabled': self.metrics_enabled,
                'persist_interval': self.metrics_persist_interval,
            },
        }
