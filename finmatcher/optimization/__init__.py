"""
FinMatcher v2.1 Mathematical Performance Optimization Layer

This module provides advanced mathematical optimization techniques to enhance
the performance of the v2.0 probabilistic matching engine:

- Spatial Indexing: K-D tree structures for O(log M) nearest neighbor search
- Vectorized Computation: NumPy SIMD operations for batch scoring
- Probabilistic Deduplication: Bloom filters for O(1) duplicate detection

Target: 50-100x speedup on large datasets (100K+ records) while maintaining
99.9% accuracy compatibility with v2.0 baseline.
"""

__version__ = "2.1.0"

from finmatcher.optimization.spatial_indexer import SpatialIndexer
from finmatcher.optimization.vectorized_scorer import VectorizedScorer
from finmatcher.optimization.bloom_filter_cache import BloomFilterCache
from finmatcher.optimization.monitoring_service import MonitoringService
from finmatcher.optimization.optimization_layer import OptimizationLayer
from finmatcher.optimization.config import OptimizationConfig
from finmatcher.optimization.data_models import FeatureVector, NormalizationParams

__all__ = [
    "SpatialIndexer",
    "VectorizedScorer",
    "BloomFilterCache",
    "MonitoringService",
    "OptimizationLayer",
    "OptimizationConfig",
    "FeatureVector",
    "NormalizationParams",
]
