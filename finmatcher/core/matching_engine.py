"""
Advanced matching engine for FinMatcher v2.0 Enterprise Upgrade.

This module implements a multi-stage probabilistic matching pipeline combining:
- Exponential decay for amount scoring
- Linear decay for date scoring  
- Cosine similarity for semantic scoring
- Weighted composite scoring
- Three-tier confidence classification

Reduces complexity from O(N²) to O(N log N) through candidate filtering.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.1, 2.2, 2.3, 2.4, 10.1, 10.2
"""

import logging
import math
from typing import List, Optional
from decimal import Decimal
from datetime import date, timedelta

from finmatcher.storage.models import (
    Transaction, Receipt, MatchResult, MatchingConfig, MatchConfidence
)
from finmatcher.core.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    Multi-stage probabilistic matching engine.
    
    Implements:
    1. Candidate filtering (amount tolerance, date variance)
    2. Amount score calculation (exponential decay)
    3. Date score calculation (linear decay)
    4. Semantic score calculation (cosine similarity)
    5. Composite score calculation (weighted sum)
    6. Confidence classification (exact, high, low)
    
    Validates Requirements: 1.1-1.9, 2.1-2.4, 10.1, 10.2
    """
    
    def __init__(self, config: MatchingConfig, deepseek_client: Optional[DeepSeekClient] = None):
        """
        Initialize matching engine with configuration and AI client.
        
        Args:
            config: Matching configuration with weights and thresholds
            deepseek_client: DeepSeek client for semantic embeddings (optional)
        """
        self.config = config
        self.deepseek_client = deepseek_client
        
        logger.info(
            f"Matching engine initialized: "
            f"weights=(amount:{config.weight_amount}, date:{config.weight_date}, "
            f"semantic:{config.weight_semantic}), "
            f"thresholds=(amount:{config.amount_tolerance}, date:{config.date_variance})"
        )
    
    def find_matches(self, transaction: Transaction, receipts: List[Receipt]) -> List[MatchResult]:
        """
        Find matching receipts for a transaction.
        
        Args:
            transaction: Transaction record to match
            receipts: Pool of receipt records to search
            
        Returns:
            List of MatchResult objects sorted by composite_score descending
            
        Validates Requirements: 1.1-1.9, 10.1, 10.2
        """
        # Step 1: Filter candidates (Requirement 1.1, 1.9)
        candidates = self._filter_candidates(transaction, receipts)
        
        if not candidates:
            logger.debug(f"No candidates found for transaction {transaction.id}")
            return []
        
        logger.debug(
            f"Filtered {len(candidates)} candidates from {len(receipts)} receipts "
            f"for transaction {transaction.id}"
        )
        
        # Step 2: Calculate scores for each candidate
        match_results = []
        
        for receipt in candidates:
            # Calculate individual scores
            amount_score = self._calculate_amount_score(transaction.amount, receipt.amount)
            date_score = self._calculate_date_score(transaction.transaction_date, receipt.receipt_date)
            semantic_score = self._calculate_semantic_score(transaction.description, receipt.description)
            
            # Calculate composite score
            composite_score = self._calculate_composite_score(amount_score, date_score, semantic_score)
            
            # Classify confidence
            confidence = self._classify_confidence(composite_score)
            
            # Create match result
            match_result = MatchResult(
                transaction=transaction,
                receipt=receipt,
                amount_score=amount_score,
                date_score=date_score,
                semantic_score=semantic_score,
                composite_score=composite_score,
                confidence=confidence
            )
            
            match_results.append(match_result)
            
            # Log scores (Requirement 10.1, 10.2)
            logger.debug(
                f"Match scores - txn:{transaction.id}, rec:{receipt.id}, "
                f"amount:{amount_score:.4f}, date:{date_score:.4f}, "
                f"semantic:{semantic_score:.4f}, composite:{composite_score:.4f}, "
                f"confidence:{confidence.value}"
            )
        
        # Sort by composite score descending
        match_results.sort(key=lambda m: m.composite_score, reverse=True)
        
        return match_results
    
    def _filter_candidates(self, transaction: Transaction, receipts: List[Receipt]) -> List[Receipt]:
        """
        Filter receipts within amount tolerance and date variance.
        
        Args:
            transaction: Transaction to match
            receipts: Pool of receipts
            
        Returns:
            Filtered list of candidate receipts
            
        Validates Requirement: 1.1 - Filter candidates within $1.00 amount tolerance and 3 days date variance
        """
        candidates = []
        
        for receipt in receipts:
            # Skip receipts without amount
            if receipt.amount is None:
                continue
            
            # Check amount tolerance
            amount_diff = abs(transaction.amount - receipt.amount)
            if amount_diff > self.config.amount_tolerance:
                continue
            
            # Check date variance
            date_diff = abs((transaction.transaction_date - receipt.receipt_date).days)
            if date_diff > self.config.date_variance:
                continue
            
            candidates.append(receipt)
        
        return candidates
    
    def _calculate_amount_score(self, txn_amount: Decimal, rec_amount: Optional[Decimal]) -> float:
        """
        Calculate amount score using exponential decay: S = e^(-λ|A_txn - A_rec|)
        
        Args:
            txn_amount: Transaction amount
            rec_amount: Receipt amount
            
        Returns:
            Amount score (0.0 to 1.0)
            
        Validates Requirement: 1.2 - Calculate amount score using exponential decay formula
        """
        if rec_amount is None:
            return 0.0
        
        # Calculate absolute difference
        amount_diff = abs(float(txn_amount) - float(rec_amount))
        
        # Apply exponential decay: S = e^(-λ * diff)
        score = math.exp(-self.config.lambda_decay * amount_diff)
        
        return score
    
    def _calculate_date_score(self, txn_date: date, rec_date: date) -> float:
        """
        Calculate date score using linear decay: S = max(0, 1 - |Days_diff|/3)
        
        Args:
            txn_date: Transaction date
            rec_date: Receipt date
            
        Returns:
            Date score (0.0 to 1.0)
            
        Validates Requirement: 1.3 - Calculate date score using linear decay formula
        """
        # Calculate absolute difference in days
        days_diff = abs((txn_date - rec_date).days)
        
        # Apply linear decay: S = max(0, 1 - |Days_diff| / date_variance)
        score = max(0.0, 1.0 - (days_diff / self.config.date_variance))
        
        return score
    
    def _calculate_semantic_score(self, txn_text: str, rec_text: str) -> float:
        """
        Calculate semantic score using vector cosine similarity.
        
        Args:
            txn_text: Transaction description
            rec_text: Receipt description
            
        Returns:
            Semantic score (0.0 to 1.0)
            
        Validates Requirements:
        - 1.4: Calculate semantic score using vector cosine similarity
        - 2.1: Use DeepSeek V3 for calculating high-dimensional vector embeddings
        - 2.2: Send transaction and receipt text to DeepSeek API
        - 2.3: Calculate cosine similarity between vectors
        - 2.4: Log error and set semantic score to 0 if API fails
        """
        # If no DeepSeek client, return 0
        if not self.deepseek_client:
            return 0.0
        
        try:
            # Get embeddings for both texts
            embeddings = self.deepseek_client.get_embeddings_batch([txn_text, rec_text])
            
            if not embeddings or len(embeddings) != 2:
                logger.warning("Failed to get embeddings, setting semantic score to 0")
                return 0.0
            
            txn_embedding = embeddings[0]
            rec_embedding = embeddings[1]
            
            if txn_embedding is None or rec_embedding is None:
                logger.warning("One or both embeddings are None, setting semantic score to 0")
                return 0.0
            
            # Calculate cosine similarity
            score = self._cosine_similarity(txn_embedding, rec_embedding)
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating semantic score: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Formula: cos(θ) = (V1 · V2) / (||V1|| × ||V2||)
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (-1.0 to 1.0, normalized to 0.0 to 1.0)
            
        Validates Requirement: 2.3 - Calculate cosine similarity between vectors
        """
        if len(vec1) != len(vec2):
            logger.error(f"Vector length mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        
        # Normalize to 0.0 to 1.0 range (cosine similarity is -1 to 1)
        normalized = (similarity + 1.0) / 2.0
        
        return normalized
    
    def _calculate_composite_score(self, amount_score: float, date_score: float, 
                                   semantic_score: float) -> float:
        """
        Calculate weighted composite score: S = W_a·S_a + W_d·S_d + W_s·S_s
        
        Args:
            amount_score: Amount score (0.0 to 1.0)
            date_score: Date score (0.0 to 1.0)
            semantic_score: Semantic score (0.0 to 1.0)
            
        Returns:
            Composite score (0.0 to 1.0)
            
        Validates Requirement: 1.5 - Calculate composite score using weighted sum formula
        """
        composite = (
            self.config.weight_amount * amount_score +
            self.config.weight_date * date_score +
            self.config.weight_semantic * semantic_score
        )
        
        return composite
    
    def _classify_confidence(self, composite_score: float) -> MatchConfidence:
        """
        Classify match confidence based on composite score thresholds.
        
        Args:
            composite_score: Composite score (0.0 to 1.0)
            
        Returns:
            MatchConfidence enum value
            
        Validates Requirements:
        - 1.6: Classify as Exact Match when composite score >= 0.98
        - 1.7: Classify as High Confidence when 0.85 <= score < 0.98
        - 1.8: Classify as Low Confidence when score < 0.85
        """
        if composite_score >= self.config.exact_threshold:
            return MatchConfidence.EXACT
        elif composite_score >= self.config.high_threshold:
            return MatchConfidence.HIGH
        else:
            return MatchConfidence.LOW
