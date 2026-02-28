"""
Vectorized scorer component for batch scoring implementation.

This module provides the VectorizedScorer class that accelerates batch scoring
from O(N*M) Python loops to O(N*M) vectorized operations with 100x throughput
improvement using NumPy.

Validates Requirements: 2.1, 7.3
"""

from typing import Optional
from finmatcher.storage.models import MatchingConfig
from finmatcher.core.deepseek_client import DeepSeekClient


class VectorizedScorer:
    """
    NumPy-based vectorized scorer for batch match scoring.
    
    Attributes:
        config: MatchingConfig with weights and decay parameters
        deepseek_client: Optional DeepSeekClient for semantic embeddings
        batch_size: Maximum batch size for vectorized operations
    
    Validates Requirements:
    - 2.1: Convert transaction and receipt data to NumPy_Array structures
    - 7.3: Load vectorization batch_size from configuration file (default: 100000)
    """
    
    def __init__(
        self,
        config: MatchingConfig,
        deepseek_client: Optional[DeepSeekClient] = None,
        batch_size: int = 100000
    ):
        """
        Initialize with matching configuration.
        
        Args:
            config: MatchingConfig with weights and decay parameters
            deepseek_client: Optional DeepSeekClient for semantic embeddings
            batch_size: Maximum batch size for vectorized operations (default: 100000)
        
        Validates Requirements:
        - 2.1: Initialize with MatchingConfig
        - 7.3: Initialize batch_size parameter (default: 100000)
        """
        self.config = config
        self.deepseek_client = deepseek_client
        self.batch_size = batch_size

    def _calculate_amount_scores(self, txn_amounts, rec_amounts):
        """
        Vectorized amount score calculation.
        
        Formula: S = exp(-λ * |A_txn - A_rec|)
        
        Implementation:
        1. Create 2D difference matrix using broadcasting:
           diffs = np.abs(txn_amounts[:, np.newaxis] - rec_amounts)
        2. Apply exponential decay element-wise:
           scores = np.exp(-lambda_decay * diffs)
        
        Args:
            txn_amounts: NumPy array of transaction amounts, shape (N,)
            rec_amounts: NumPy array of receipt amounts, shape (M,)
        
        Returns:
            Array of shape (N, M) with amount scores
        
        Validates Requirements:
        - 2.2: Create amount arrays from transactions and receipts
        - 2.3: Calculate amount differences using Broadcasting
        - 2.4: Apply exponential decay function element-wise
        """
        import numpy as np
        
        # Create 2D difference matrix using broadcasting
        # txn_amounts[:, np.newaxis] has shape (N, 1)
        # rec_amounts has shape (M,)
        # Broadcasting creates shape (N, M)
        diffs = np.abs(txn_amounts[:, np.newaxis] - rec_amounts)
        
        # Apply exponential decay element-wise
        # Get lambda decay parameter from config
        lambda_decay = self.config.lambda_decay
        scores = np.exp(-lambda_decay * diffs)
        
        return scores

    def _calculate_date_scores(self, txn_dates, rec_dates, tolerance_days):
        """
        Vectorized date score calculation.

        Formula: S = max(0, 1 - |Days_diff| / tolerance)

        Implementation:
        1. Convert dates to Unix timestamps
        2. Create 2D difference matrix in days:
           diffs = np.abs(txn_dates[:, np.newaxis] - rec_dates) / 86400
        3. Apply linear decay with clipping:
           scores = np.maximum(0, 1 - diffs / tolerance_days)

        Args:
            txn_dates: NumPy array of transaction dates (Unix timestamps), shape (N,)
            rec_dates: NumPy array of receipt dates (Unix timestamps), shape (M,)
            tolerance_days: Date tolerance in days

        Returns:
            Array of shape (N, M) with date scores

        Validates Requirements:
        - 2.5: Create date arrays with Unix timestamp representation
        - 2.6: Calculate date differences in days using Broadcasting
        - 2.7: Apply linear decay function element-wise
        """
        import numpy as np

        # Create 2D difference matrix in days using broadcasting
        # txn_dates[:, np.newaxis] has shape (N, 1)
        # rec_dates has shape (M,)
        # Broadcasting creates shape (N, M)
        # Divide by 86400 to convert seconds to days
        diffs = np.abs(txn_dates[:, np.newaxis] - rec_dates) / 86400

        # Apply linear decay with clipping
        # np.maximum ensures scores don't go below 0
        scores = np.maximum(0, 1 - diffs / tolerance_days)

        return scores

    def _calculate_semantic_scores(self, txn_texts, rec_texts):
        """
        Vectorized semantic score calculation.
        
        Formula: S = (V1 · V2) / (||V1|| × ||V2||)
        
        Implementation:
        1. Get embeddings for all texts via batch API call
        2. Convert to NumPy arrays: txn_vecs (N, D), rec_vecs (M, D)
        3. Calculate norms: norms_txn = np.linalg.norm(txn_vecs, axis=1)
        4. Calculate dot products using matrix multiplication:
           similarities = np.dot(txn_vecs, rec_vecs.T)
        5. Normalize using broadcasting:
           scores = similarities / (norms_txn[:, np.newaxis] * norms_rec)
        6. Map [-1, 1] to [0, 1]: scores = (scores + 1) / 2
        
        Args:
            txn_texts: List of transaction text descriptions, length N
            rec_texts: List of receipt text descriptions, length M
        
        Returns:
            Array of shape (N, M) with semantic scores in [0, 1] range
        
        Validates Requirements:
        - 2.8: Calculate cosine similarity using np.dot() and broadcasting,
               normalize using vector norms, map [-1, 1] to [0, 1] range
        """
        import numpy as np
        
        # Get embeddings for all texts via batch API call
        # This assumes the DeepSeekClient has a method to get embeddings
        if self.deepseek_client is None:
            # If no client available, return zeros
            return np.zeros((len(txn_texts), len(rec_texts)))
        
        # Get embeddings for transactions and receipts
        txn_embeddings = self.deepseek_client.get_embeddings(txn_texts)
        rec_embeddings = self.deepseek_client.get_embeddings(rec_texts)
        
        # Convert to NumPy arrays
        txn_vecs = np.array(txn_embeddings)  # shape: (N, D)
        rec_vecs = np.array(rec_embeddings)  # shape: (M, D)
        
        # Calculate norms for normalization
        norms_txn = np.linalg.norm(txn_vecs, axis=1)  # shape: (N,)
        norms_rec = np.linalg.norm(rec_vecs, axis=1)  # shape: (M,)
        
        # Calculate dot products using matrix multiplication
        # txn_vecs: (N, D), rec_vecs.T: (D, M) -> similarities: (N, M)
        similarities = np.dot(txn_vecs, rec_vecs.T)
        
        # Normalize using broadcasting
        # norms_txn[:, np.newaxis]: (N, 1), norms_rec: (M,)
        # Broadcasting creates (N, M) denominator matrix
        scores = similarities / (norms_txn[:, np.newaxis] * norms_rec)
        
        # Map [-1, 1] to [0, 1] range
        scores = (scores + 1) / 2
        
        return scores

    def _calculate_composite_scores(self, amount_scores, date_scores, semantic_scores):
        """
        Vectorized composite score calculation.

        Formula: S = w_a * S_a + w_d * S_d + w_s * S_s

        Implementation:
        Single element-wise operation with broadcasting:
        composite = (self.config.weight_amount * amount_scores +
                    self.config.weight_date * date_scores +
                    self.config.weight_semantic * semantic_scores)

        Args:
            amount_scores: NumPy array of amount scores, shape (N, M)
            date_scores: NumPy array of date scores, shape (N, M)
            semantic_scores: NumPy array of semantic scores, shape (N, M)

        Returns:
            Array of shape (N, M) with composite scores

        Validates Requirements:
        - 2.9: Calculate composite scores using Broadcasting with weighted sum
        """
        # Single vectorized operation with broadcasting
        # All input arrays have shape (N, M)
        # Element-wise multiplication and addition
        composite = (
            self.config.weight_amount * amount_scores +
            self.config.weight_date * date_scores +
            self.config.weight_semantic * semantic_scores
        )

        return composite

    def score_batch(self, transactions, receipts):
        """
        Calculate scores for all transaction-receipt pairs.
        
        Args:
            transactions: List of N transactions
            receipts: List of M receipts
            
        Returns:
            NumPy array of shape (N, M) with composite scores
            
        Steps:
        1. Convert data to NumPy arrays
        2. Calculate amount scores (vectorized exponential decay)
        3. Calculate date scores (vectorized linear decay)
        4. Calculate semantic scores (vectorized cosine similarity)
        5. Calculate composite scores (weighted sum with broadcasting)
        6. Return 2D score matrix
        
        Complexity: O(N*M) but with SIMD parallelism
        Memory: O(N*M) for score matrices
        
        Validates Requirements:
        - 2.1: Convert transaction and receipt data to NumPy_Array structures
        - 2.10: Process 100,000 transaction-receipt pairs in a single vectorized operation without Python loops
        - 2.11: Return a 2D NumPy_Array of shape (N_transactions, M_receipts) containing all composite scores
        """
        import numpy as np
        from datetime import datetime
        
        # Step 1: Convert data to NumPy arrays
        # Extract amounts from transactions and receipts
        txn_amounts = np.array([float(t.amount) for t in transactions])  # shape: (N,)
        rec_amounts = np.array([float(r.amount) if r.amount is not None else 0.0 for r in receipts])  # shape: (M,)
        
        # Extract dates and convert to Unix timestamps
        # Handle both storage.models and database.models Transaction/Receipt types
        txn_dates = np.array([
            t.transaction_date.timestamp() if hasattr(t.transaction_date, 'timestamp') 
            else datetime.strptime(t.transaction_date if isinstance(t.transaction_date, str) else str(t.transaction_date), '%Y-%m-%d').timestamp()
            for t in transactions
        ])  # shape: (N,)
        
        rec_dates = np.array([
            r.receipt_date.timestamp() if hasattr(r.receipt_date, 'timestamp')
            else (datetime.strptime(r.transaction_date if r.transaction_date else r.received_date, '%Y-%m-%d').timestamp() 
                  if hasattr(r, 'transaction_date') 
                  else datetime.strptime(str(r.receipt_date), '%Y-%m-%d').timestamp())
            for r in receipts
        ])  # shape: (M,)
        
        # Extract text descriptions for semantic scoring
        txn_texts = [t.description for t in transactions]
        rec_texts = [r.description if hasattr(r, 'description') else (r.merchant_name or r.subject) for r in receipts]
        
        # Step 2: Calculate amount scores (vectorized exponential decay)
        amount_scores = self._calculate_amount_scores(txn_amounts, rec_amounts)
        
        # Step 3: Calculate date scores (vectorized linear decay)
        # Use date_variance from config (same as v2.0 implementation)
        date_scores = self._calculate_date_scores(txn_dates, rec_dates, self.config.date_variance)
        
        # Step 4: Calculate semantic scores (vectorized cosine similarity)
        semantic_scores = self._calculate_semantic_scores(txn_texts, rec_texts)
        
        # Step 5: Calculate composite scores (weighted sum with broadcasting)
        composite_scores = self._calculate_composite_scores(amount_scores, date_scores, semantic_scores)
        
        # Step 6: Return 2D score matrix
        return composite_scores

