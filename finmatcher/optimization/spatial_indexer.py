"""
Spatial indexer component for K-D tree based receipt candidate filtering.

This module implements the SpatialIndexer class which accelerates candidate
filtering from O(M) to O(log M) using geometric nearest neighbor search with
K-D trees.

Validates Requirements: 1.1, 6.6
"""

from typing import Optional, Tuple
import logging

from finmatcher.optimization.config import OptimizationConfig

logger = logging.getLogger(__name__)


class SpatialIndexer:
    """
    K-D tree based spatial indexer for receipt candidate filtering.
    
    Accelerates candidate filtering from O(M) to O(log M) using geometric
    nearest neighbor search. Normalizes receipt coordinates to [0,1]^2 unit
    space and constructs scipy.spatial.KDTree for efficient spatial queries.
    
    Attributes:
        kdtree: scipy.spatial.KDTree instance (None until build_index called)
        feature_vectors: NumPy array of shape (M, 2) with normalized coordinates
        normalization_params: NormalizationParams storing min/max values
        weights: Tuple (w_amount, w_date) for weighted Euclidean distance
        config: OptimizationConfig with K-D tree parameters
    
    Validates Requirements: 1.1, 6.6
    """
    
    def __init__(self, config: OptimizationConfig):
        """
        Initialize with configuration parameters.
        
        Sets up the spatial indexer with configuration settings and initializes
        attributes to None. The K-D tree is built later via build_index() method.
        
        Args:
            config: OptimizationConfig instance with K-D tree settings including
                   leaf_size, cache_path, and cache_enabled parameters
        
        Validates Requirements: 1.1, 6.6
        
        Example:
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> config = OptimizationConfig(kdtree_leaf_size=40)
            >>> indexer = SpatialIndexer(config)
            >>> indexer.kdtree is None
            True
        """
        self.config = config
        self.kdtree: Optional[object] = None  # scipy.spatial.KDTree instance
        self.feature_vectors: Optional[object] = None  # NumPy array (M, 2)
        self.normalization_params: Optional[object] = None  # NormalizationParams
        self.weights: Tuple[float, float] = (1.0, 1.0)  # Default equal weights
        
        logger.info(
            f"SpatialIndexer initialized with leaf_size={config.kdtree_leaf_size}, "
            f"cache_enabled={config.kdtree_cache_enabled}"
        )


    def _normalize_features(self, amounts: 'np.ndarray', dates: 'np.ndarray') -> 'np.ndarray':
        """
        Apply min-max normalization to map values to [0,1] space.
        
        Applies the min-max scaling formula to transform raw amount and date
        values into normalized coordinates in the [0,1] unit interval. This
        normalization is essential for K-D tree construction as it ensures
        both dimensions have comparable scales.
        
        Formula: x_norm = (x - x_min) / (x_max - x_min)
        
        Args:
            amounts: NumPy array of raw amount values
            dates: NumPy array of raw date values (Unix timestamps)
        
        Returns:
            NumPy array of shape (N, 2) with normalized coordinates where
            column 0 is normalized amounts and column 1 is normalized dates
        
        Validates Requirements: 1.2, 1.3, 1.4
        
        Example:
            >>> import numpy as np
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> amounts = np.array([10.0, 50.0, 100.0])
            >>> dates = np.array([1000, 2000, 3000])
            >>> normalized = indexer._normalize_features(amounts, dates)
            >>> normalized.shape
            (3, 2)
            >>> normalized[0]  # First receipt: min values -> 0.0
            array([0., 0.])
            >>> normalized[2]  # Last receipt: max values -> 1.0
            array([1., 1.])
        """
        import numpy as np
        
        # Calculate min and max for amounts
        amount_min = np.min(amounts)
        amount_max = np.max(amounts)
        
        # Calculate min and max for dates
        date_min = np.min(dates)
        date_max = np.max(dates)
        
        # Handle edge case: if all values are the same, normalize to 0.5
        if amount_max == amount_min:
            amount_normalized = np.full_like(amounts, 0.5, dtype=float)
        else:
            amount_normalized = (amounts - amount_min) / (amount_max - amount_min)
        
        if date_max == date_min:
            date_normalized = np.full_like(dates, 0.5, dtype=float)
        else:
            date_normalized = (dates - date_min) / (date_max - date_min)
        
        # Stack into (N, 2) array
        normalized = np.column_stack([amount_normalized, date_normalized])
        
        return normalized

    def _extract_features(self, receipts: list) -> tuple:
        """
        Extract amount and date values from receipts.
        
        Extracts raw amount and date values from a list of Receipt objects
        and converts them to NumPy arrays for normalization. Dates are
        converted to Unix timestamps for numerical processing.
        
        Args:
            receipts: List of Receipt objects with amount and receipt_date fields
        
        Returns:
            Tuple of (amounts_array, dates_array) where:
            - amounts_array: NumPy array of float amounts
            - dates_array: NumPy array of Unix timestamps (int)
        
        Validates Requirements: 1.1, 1.2, 1.3
        
        Example:
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> from finmatcher.storage.models import Receipt
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> receipts = [
            ...     Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None),
            ...     Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test', True, None)
            ... ]
            >>> amounts, dates = indexer._extract_features(receipts)
            >>> amounts.shape
            (2,)
            >>> dates.shape
            (2,)
        """
        import numpy as np
        from datetime import datetime
        
        amounts = []
        dates = []
        
        for receipt in receipts:
            # Extract amount (convert Decimal to float)
            if receipt.amount is not None:
                amounts.append(float(receipt.amount))
            else:
                # Handle receipts without amounts (use 0.0 as placeholder)
                amounts.append(0.0)
            
            # Extract date (convert to Unix timestamp)
            timestamp = int(datetime.combine(receipt.receipt_date, datetime.min.time()).timestamp())
            dates.append(timestamp)
        
        return np.array(amounts, dtype=float), np.array(dates, dtype=int)
    
    def _calculate_normalization_params(self, amounts: 'np.ndarray', dates: 'np.ndarray', 
                                       receipts: list) -> 'NormalizationParams':
        """
        Calculate normalization parameters (min/max for each dimension).
        
        Computes the minimum and maximum values for amounts and dates,
        which are used for min-max scaling. Also calculates a dataset
        hash for cache validation.
        
        Args:
            amounts: NumPy array of raw amount values
            dates: NumPy array of raw date values (Unix timestamps)
            receipts: List of Receipt objects for hash calculation
        
        Returns:
            NormalizationParams object with min/max values and dataset hash
        
        Validates Requirements: 1.2, 1.3, 8.3
        
        Example:
            >>> import numpy as np
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> amounts = np.array([10.0, 50.0, 100.0])
            >>> dates = np.array([1000, 2000, 3000])
            >>> receipts = []
            >>> params = indexer._calculate_normalization_params(amounts, dates, receipts)
            >>> params.amount_min
            Decimal('10.0')
            >>> params.amount_max
            Decimal('100.0')
        """
        from decimal import Decimal
        from finmatcher.optimization.data_models import NormalizationParams
        
        # Calculate min/max for amounts
        amount_min = Decimal(str(float(amounts.min())))
        amount_max = Decimal(str(float(amounts.max())))
        
        # Calculate min/max for dates
        date_min = int(dates.min())
        date_max = int(dates.max())
        
        # Calculate dataset hash
        dataset_hash = self._calculate_dataset_hash(receipts)
        
        return NormalizationParams(
            amount_min=amount_min,
            amount_max=amount_max,
            date_min=date_min,
            date_max=date_max,
            dataset_hash=dataset_hash
        )
    
    def _calculate_dataset_hash(self, receipts: list) -> str:
        """
        Calculate SHA-256 hash of receipt IDs and timestamps.
        
        Generates a unique hash for the receipt dataset based on receipt
        IDs and dates. This hash is used for cache validation to ensure
        the cached K-D tree matches the current dataset.
        
        Args:
            receipts: List of Receipt objects
        
        Returns:
            SHA-256 hash string (hexadecimal)
        
        Validates Requirements: 8.3
        
        Example:
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> from finmatcher.storage.models import Receipt
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> receipts = [
            ...     Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None)
            ... ]
            >>> hash_val = indexer._calculate_dataset_hash(receipts)
            >>> len(hash_val)
            64
        """
        import hashlib
        
        # Create a string representation of receipt IDs and dates
        data_str = ""
        for receipt in receipts:
            data_str += f"{receipt.id}:{receipt.receipt_date}:"
        
        # Calculate SHA-256 hash
        hash_obj = hashlib.sha256(data_str.encode('utf-8'))
        return hash_obj.hexdigest()

    def _is_cache_valid(self, cache_path: str) -> bool:
        """
        Check if cache file exists and is not expired.
        
        Implements cache expiration policy by checking if the cache file
        exists and was modified within the expiration window (default 7 days).
        
        Args:
            cache_path: Path to the cache file
        
        Returns:
            True if cache exists and is not expired, False otherwise
        
        Validates Requirements: 8.9
        
        Example:
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> is_valid = indexer._is_cache_valid('.kiro/cache/kdtree_test.pkl')
            >>> isinstance(is_valid, bool)
            True
        """
        import os
        import time
        
        # Check if file exists
        if not os.path.exists(cache_path):
            return False
        
        # Get file modification time
        try:
            file_mtime = os.path.getmtime(cache_path)
            current_time = time.time()
            
            # Calculate age in days
            age_seconds = current_time - file_mtime
            age_days = age_seconds / 86400  # 86400 seconds per day
            
            # Check if cache is expired (older than configured expiration days)
            if age_days > self.config.kdtree_cache_expiration_days:
                logger.info(
                    f"Cache expired: {cache_path} is {age_days:.1f} days old "
                    f"(expiration: {self.config.kdtree_cache_expiration_days} days)"
                )
                return False
            
            logger.debug(
                f"Cache valid: {cache_path} is {age_days:.1f} days old "
                f"(expiration: {self.config.kdtree_cache_expiration_days} days)"
            )
            return True
            
        except Exception as e:
            logger.warning(f"Failed to check cache validity for {cache_path}: {e}")
            return False

    def build_index(self, receipts: list) -> None:
        """
        Build K-D tree from receipt dataset.
        
        Constructs a scipy.spatial.KDTree from the receipt dataset by:
        1. Checking for cached K-D tree matching current dataset
        2. Extracting amount and date from each receipt
        3. Calculating normalization parameters (min/max for each dimension)
        4. Applying min-max scaling to create feature vectors
        5. Constructing scipy.spatial.KDTree with leaf_size parameter
        6. Storing normalization params for query-time normalization
        7. Optionally serializing to cache if caching enabled
        
        Args:
            receipts: List of Receipt objects to index
        
        Raises:
            ValueError: If receipts list is empty
            ImportError: If scipy is not installed
        
        Complexity: O(M log M) for tree construction
        Memory: O(M) for feature vectors and tree nodes
        
        Validates Requirements: 1.5, 7.1, 8.4, 8.5, 8.6, 8.8
        
        Example:
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> from finmatcher.storage.models import Receipt
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> receipts = [
            ...     Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None),
            ...     Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test', True, None)
            ... ]
            >>> indexer.build_index(receipts)
            >>> indexer.kdtree is not None
            True
        """
        import numpy as np
        from scipy.spatial import KDTree
        import time
        
        if not receipts:
            raise ValueError("Cannot build index from empty receipt list")
        
        logger.info(f"Building K-D tree index for {len(receipts)} receipts")
        
        # Step 1: Check for cached K-D tree on initialization
        if self.config.kdtree_cache_enabled:
            # Calculate dataset hash first to check for cache
            dataset_hash = self._calculate_dataset_hash(receipts)
            cache_path = f"{self.config.kdtree_cache_path}/kdtree_{dataset_hash}.pkl"
            
            # Check if cache file exists and is not expired
            if self._is_cache_valid(cache_path):
                logger.info(f"Checking for cached K-D tree at {cache_path}")
                
                # Try to deserialize cached structure
                if self.deserialize(cache_path):
                    # Validate cached structure matches current dataset hash
                    if self.normalization_params.dataset_hash == dataset_hash:
                        logger.info(
                            f"Cache HIT: Loaded K-D tree from cache "
                            f"({self.feature_vectors.shape[0]} receipts)"
                        )
                        return
                    else:
                        logger.warning(
                            f"Cache MISS: Dataset hash mismatch "
                            f"(cached: {self.normalization_params.dataset_hash}, "
                            f"current: {dataset_hash})"
                        )
                else:
                    logger.info("Cache MISS: Failed to deserialize cached K-D tree")
            else:
                logger.info("Cache MISS: No valid cache found or cache expired")
        
        # Cache miss or caching disabled - build new index
        start_time = time.perf_counter()
        
        # Step 2: Extract amount and date from each receipt
        amounts, dates = self._extract_features(receipts)
        
        # Step 3: Calculate normalization parameters (min/max for each dimension)
        self.normalization_params = self._calculate_normalization_params(
            amounts, dates, receipts
        )
        
        logger.debug(
            f"Normalization params: amount=[{self.normalization_params.amount_min}, "
            f"{self.normalization_params.amount_max}], "
            f"date=[{self.normalization_params.date_min}, "
            f"{self.normalization_params.date_max}]"
        )
        
        # Step 4: Apply min-max scaling to create feature vectors
        self.feature_vectors = self._normalize_features(amounts, dates)
        
        logger.debug(
            f"Created {self.feature_vectors.shape[0]} feature vectors "
            f"with shape {self.feature_vectors.shape}"
        )
        
        # Step 5: Construct scipy.spatial.KDTree with configurable leaf_size
        self.kdtree = KDTree(
            self.feature_vectors,
            leafsize=self.config.kdtree_leaf_size
        )
        
        build_time_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"K-D tree built successfully in {build_time_ms:.2f}ms "
            f"with leaf_size={self.config.kdtree_leaf_size}"
        )
        
        # Step 6: Normalization params already stored in step 3
        
        # Step 7: Serialize to cache if caching enabled
        if self.config.kdtree_cache_enabled:
            cache_path = f"{self.config.kdtree_cache_path}/kdtree_{self.normalization_params.dataset_hash}.pkl"
            try:
                self.serialize(cache_path)
                logger.info(f"K-D tree cached to {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to cache K-D tree: {e}")
    
    def serialize(self, path: str) -> None:
        """
        Serialize K-D tree and normalization params to disk.

        Saves the K-D tree structure, feature vectors, and normalization
        parameters to a pickle file for later deserialization. This enables
        caching to avoid rebuilding the index on system restart.

        Args:
            path: File path where serialized data should be stored

        Raises:
            IOError: If file cannot be written

        Validates Requirements: 8.1, 8.2

        Example:
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> from finmatcher.storage.models import Receipt
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> receipts = [
            ...     Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None)
            ... ]
            >>> indexer.build_index(receipts)
            >>> indexer.serialize('.kiro/cache/test_kdtree.pkl')
        """
        import pickle
        import os

        if self.kdtree is None or self.normalization_params is None:
            raise ValueError(
                "Cannot serialize: K-D tree has not been built. Call build_index() first."
            )

        # Ensure directory exists
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created cache directory: {directory}")

        # Prepare serialization data
        serialization_data = {
            'kdtree': self.kdtree,
            'feature_vectors': self.feature_vectors,
            'normalization_params': self.normalization_params,
            'weights': self.weights,
            'config': {
                'kdtree_leaf_size': self.config.kdtree_leaf_size
            }
        }

        # Serialize to pickle file
        try:
            with open(path, 'wb') as f:
                pickle.dump(serialization_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"K-D tree serialized successfully to {path}")

        except Exception as e:
            logger.error(f"Failed to serialize K-D tree to {path}: {e}")
            raise IOError(f"Failed to serialize K-D tree: {e}") from e

    def deserialize(self, path: str) -> bool:
        """
        Deserialize K-D tree from disk.

        Loads a previously serialized K-D tree structure from a pickle file
        and validates that it matches the expected format. Returns True if
        successful, False if cache is invalid or missing.

        Args:
            path: File path to the serialized K-D tree

        Returns:
            True if deserialization successful, False if cache invalid/missing

        Validates Requirements: 8.5, 8.7

        Example:
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> success = indexer.deserialize('.kiro/cache/test_kdtree.pkl')
            >>> if success:
            ...     print("K-D tree loaded from cache")
        """
        import pickle
        import os

        # Check if file exists
        if not os.path.exists(path):
            logger.debug(f"Cache file not found: {path}")
            return False

        try:
            # Load serialized data
            with open(path, 'rb') as f:
                serialization_data = pickle.load(f)

            # Validate structure
            required_keys = ['kdtree', 'feature_vectors', 'normalization_params', 'weights']
            for key in required_keys:
                if key not in serialization_data:
                    logger.warning(f"Invalid cache: missing key '{key}'")
                    return False

            # Validate data shape and types
            if serialization_data['feature_vectors'] is None:
                logger.warning("Invalid cache: feature_vectors is None")
                return False

            if serialization_data['normalization_params'] is None:
                logger.warning("Invalid cache: normalization_params is None")
                return False

            # Validate feature vectors shape (should be (M, 2))
            feature_shape = serialization_data['feature_vectors'].shape
            if len(feature_shape) != 2 or feature_shape[1] != 2:
                logger.warning(
                    f"Invalid cache: feature_vectors has invalid shape {feature_shape}, "
                    f"expected (M, 2)"
                )
                return False

            # Load data into instance
            self.kdtree = serialization_data['kdtree']
            self.feature_vectors = serialization_data['feature_vectors']
            self.normalization_params = serialization_data['normalization_params']
            self.weights = serialization_data['weights']

            logger.info(
                f"K-D tree deserialized successfully from {path} "
                f"({feature_shape[0]} receipts)"
            )

            return True

        except Exception as e:
            logger.warning(f"Failed to deserialize K-D tree from {path}: {e}")
            return False


    def query_candidates(self, transaction, tolerance_amount, tolerance_days: int) -> list:
        """
        Query K-D tree for receipts within tolerance radius.

        Performs O(log M) nearest neighbor search to find all receipts within
        the specified tolerance radius in normalized space. Uses weighted
        Euclidean distance metric matching v2.0 scoring weights.

        Args:
            transaction: Transaction object to match with amount and transaction_date
            tolerance_amount: Amount tolerance in dollars (Decimal or float)
            tolerance_days: Date tolerance in days (int)

        Returns:
            List of receipt indices within tolerance radius

        Raises:
            ValueError: If K-D tree has not been built (call build_index first)

        Steps:
        1. Normalize transaction amount and date using stored params
        2. Calculate tolerance radius in normalized space:
           r = sqrt(w_a * (tol_amt / amt_range)^2 + w_d * (tol_days / date_range)^2)
        3. Call kdtree.query_ball_point(normalized_point, r)
        4. Return list of indices

        Complexity: O(log M) average case, O(M^(1-1/k)) worst case

        Validates Requirements: 1.6, 1.7, 1.8, 1.9, 1.10

        Example:
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> from finmatcher.storage.models import Transaction, Receipt
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> receipts = [
            ...     Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None),
            ...     Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test', True, None)
            ... ]
            >>> indexer.build_index(receipts)
            >>> txn = Transaction(1, 'stmt', date(2024, 1, 5), Decimal('105.00'), 'Test')
            >>> candidates = indexer.query_candidates(txn, Decimal('10.00'), 7)
            >>> isinstance(candidates, list)
            True
        """
        import numpy as np
        from datetime import datetime
        from decimal import Decimal

        # Validate that K-D tree has been built
        if self.kdtree is None or self.normalization_params is None:
            raise ValueError(
                "K-D tree has not been built. Call build_index() before querying."
            )

        # Step 1: Normalize transaction amount and date using stored params
        txn_amount = float(transaction.amount)
        txn_timestamp = int(datetime.combine(
            transaction.transaction_date,
            datetime.min.time()
        ).timestamp())

        # Normalize amount
        amount_range = float(
            self.normalization_params.amount_max -
            self.normalization_params.amount_min
        )
        if amount_range == 0:
            txn_amount_norm = 0.5
        else:
            txn_amount_norm = (
                txn_amount - float(self.normalization_params.amount_min)
            ) / amount_range

        # Normalize date
        date_range = (
            self.normalization_params.date_max -
            self.normalization_params.date_min
        )
        if date_range == 0:
            txn_date_norm = 0.5
        else:
            txn_date_norm = (
                txn_timestamp - self.normalization_params.date_min
            ) / date_range

        # Create normalized point
        normalized_point = np.array([txn_amount_norm, txn_date_norm])

        logger.debug(
            f"Normalized transaction: amount={txn_amount} -> {txn_amount_norm:.4f}, "
            f"date={transaction.transaction_date} -> {txn_date_norm:.4f}"
        )

        # Step 2: Calculate tolerance radius in normalized space
        # r = sqrt(w_a * (tol_amt / amt_range)^2 + w_d * (tol_days / date_range)^2)

        # Convert tolerance_amount to float
        tolerance_amount_float = float(tolerance_amount)

        # Calculate normalized tolerances
        if amount_range == 0:
            tolerance_amount_norm = 0.0
        else:
            tolerance_amount_norm = tolerance_amount_float / amount_range

        # Convert tolerance_days to seconds for date range comparison
        tolerance_days_seconds = tolerance_days * 86400  # 86400 seconds per day
        if date_range == 0:
            tolerance_days_norm = 0.0
        else:
            tolerance_days_norm = tolerance_days_seconds / date_range

        # Calculate weighted Euclidean distance radius
        # Using weights from self.weights (w_amount, w_date)
        w_amount, w_date = self.weights

        radius = np.sqrt(
            w_amount * (tolerance_amount_norm ** 2) +
            w_date * (tolerance_days_norm ** 2)
        )

        logger.debug(
            f"Tolerance radius: amount_tol={tolerance_amount_float} -> "
            f"{tolerance_amount_norm:.4f}, date_tol={tolerance_days}days -> "
            f"{tolerance_days_norm:.4f}, radius={radius:.4f}"
        )

        # Step 3: Call kdtree.query_ball_point() with normalized point and radius
        indices = self.kdtree.query_ball_point(normalized_point, radius)

        logger.debug(
            f"K-D tree query returned {len(indices)} candidates within radius {radius:.4f}"
        )

        # Step 4: Return list of receipt indices
        return indices


    def query_candidates(self, transaction, tolerance_amount, tolerance_days: int) -> list:
        """
        Query K-D tree for receipts within tolerance radius.
        
        Performs O(log M) nearest neighbor search to find all receipts within
        the specified tolerance radius in normalized space. Uses weighted
        Euclidean distance metric matching v2.0 scoring weights.
        
        Args:
            transaction: Transaction object to match with amount and transaction_date
            tolerance_amount: Amount tolerance in dollars (Decimal or float)
            tolerance_days: Date tolerance in days (int)
            
        Returns:
            List of receipt indices within tolerance radius
            
        Raises:
            ValueError: If K-D tree has not been built (call build_index first)
            
        Steps:
        1. Normalize transaction amount and date using stored params
        2. Calculate tolerance radius in normalized space:
           r = sqrt(w_a * (tol_amt / amt_range)^2 + w_d * (tol_days / date_range)^2)
        3. Call kdtree.query_ball_point(normalized_point, r)
        4. Return list of indices
        
        Complexity: O(log M) average case, O(M^(1-1/k)) worst case
        
        Validates Requirements: 1.6, 1.7, 1.8, 1.9, 1.10
        
        Example:
            >>> from datetime import date
            >>> from decimal import Decimal
            >>> from finmatcher.storage.models import Transaction, Receipt
            >>> from finmatcher.optimization.config import OptimizationConfig
            >>> indexer = SpatialIndexer(OptimizationConfig())
            >>> receipts = [
            ...     Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None),
            ...     Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test', True, None)
            ... ]
            >>> indexer.build_index(receipts)
            >>> txn = Transaction(1, 'stmt', date(2024, 1, 5), Decimal('105.00'), 'Test')
            >>> candidates = indexer.query_candidates(txn, Decimal('10.00'), 7)
            >>> isinstance(candidates, list)
            True
        """
        import numpy as np
        from datetime import datetime
        from decimal import Decimal
        
        # Validate that K-D tree has been built
        if self.kdtree is None or self.normalization_params is None:
            raise ValueError(
                "K-D tree has not been built. Call build_index() before querying."
            )
        
        # Step 1: Normalize transaction amount and date using stored params
        txn_amount = float(transaction.amount)
        txn_timestamp = int(datetime.combine(
            transaction.transaction_date, 
            datetime.min.time()
        ).timestamp())
        
        # Normalize amount
        amount_range = float(
            self.normalization_params.amount_max - 
            self.normalization_params.amount_min
        )
        if amount_range == 0:
            txn_amount_norm = 0.5
        else:
            txn_amount_norm = (
                txn_amount - float(self.normalization_params.amount_min)
            ) / amount_range
        
        # Normalize date
        date_range = (
            self.normalization_params.date_max - 
            self.normalization_params.date_min
        )
        if date_range == 0:
            txn_date_norm = 0.5
        else:
            txn_date_norm = (
                txn_timestamp - self.normalization_params.date_min
            ) / date_range
        
        # Create normalized point
        normalized_point = np.array([txn_amount_norm, txn_date_norm])
        
        logger.debug(
            f"Normalized transaction: amount={txn_amount} -> {txn_amount_norm:.4f}, "
            f"date={transaction.transaction_date} -> {txn_date_norm:.4f}"
        )
        
        # Step 2: Calculate tolerance radius in normalized space
        # r = sqrt(w_a * (tol_amt / amt_range)^2 + w_d * (tol_days / date_range)^2)
        
        # Convert tolerance_amount to float
        tolerance_amount_float = float(tolerance_amount)
        
        # Calculate normalized tolerances
        if amount_range == 0:
            tolerance_amount_norm = 0.0
        else:
            tolerance_amount_norm = tolerance_amount_float / amount_range
        
        # Convert tolerance_days to seconds for date range comparison
        tolerance_days_seconds = tolerance_days * 86400  # 86400 seconds per day
        if date_range == 0:
            tolerance_days_norm = 0.0
        else:
            tolerance_days_norm = tolerance_days_seconds / date_range
        
        # Calculate weighted Euclidean distance radius
        # Using weights from self.weights (w_amount, w_date)
        w_amount, w_date = self.weights
        
        radius = np.sqrt(
            w_amount * (tolerance_amount_norm ** 2) +
            w_date * (tolerance_days_norm ** 2)
        )
        
        logger.debug(
            f"Tolerance radius: amount_tol={tolerance_amount_float} -> "
            f"{tolerance_amount_norm:.4f}, date_tol={tolerance_days}days -> "
            f"{tolerance_days_norm:.4f}, radius={radius:.4f}"
        )
        
        # Step 3: Call kdtree.query_ball_point() with normalized point and radius
        indices = self.kdtree.query_ball_point(normalized_point, radius)
        
        logger.debug(
            f"K-D tree query returned {len(indices)} candidates within radius {radius:.4f}"
        )
        
        # Step 4: Return list of receipt indices
        return indices
