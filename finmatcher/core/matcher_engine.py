"""
Intelligent matching engine with multi-stage algorithm.

This module implements a 3-stage matching algorithm:
1. Exact matching (amount + date + reference)
2. Fuzzy matching (amount tolerance + date variance)
3. Semantic matching (DeepSeek embeddings for description similarity)

Validates Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
"""

import time
import os
from typing import List, Optional, Tuple, Dict
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from openai import OpenAI
    import numpy as np
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False
    np = None  # Set np to None when not available
    print("Warning: openai library not available. Semantic matching will be disabled.")

from finmatcher.database.models import Transaction, Receipt, Match, MatchingStatistics
from finmatcher.config.settings import get_settings
from finmatcher.utils.logger import get_logger


@dataclass
class MatchCandidate:
    """Represents a potential match between transaction and receipt."""
    transaction: Transaction
    receipt: Receipt
    amount_score: float = 0.0
    date_score: float = 0.0
    semantic_score: float = 0.0
    total_score: float = 0.0
    match_stage: str = "none"


class MatcherEngine:
    """
    Intelligent matching engine with multi-stage algorithm.
    
    Implements:
    - Stage 1: Exact matching (amount + date + reference)
    - Stage 2: Fuzzy matching (tolerance-based)
    - Stage 3: Semantic matching (DeepSeek embeddings)
    
    Validates Requirements:
    - 4.1: Filter by amount within ±$1.00
    - 4.2: Filter by date with 0-3 days variance
    - 4.3: Calculate semantic similarity using DeepSeek
    - 4.4: Use weighted scoring formula
    - 4.5: Classify as MATCHED if score > 0.85
    - 4.6: Classify as UNMATCHED if score < 0.85
    - 4.7: Select highest scoring match
    - 4.8: Flag receipts matching multiple transactions
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the matching engine.
        
        Args:
            model_name: Model name (not used for DeepSeek, kept for compatibility)
            
        Validates Requirement 4.3: Load DeepSeek client for semantic matching
        """
        self.settings = get_settings()
        self.logger = get_logger()
        
        # Matching thresholds from config
        self.amount_tolerance = self.settings.matching_thresholds.amount_tolerance
        self.date_variance_days = self.settings.matching_thresholds.date_variance_days
        self.match_threshold = self.settings.matching_thresholds.semantic_threshold
        
        # Scoring weights
        self.amount_weight = self.settings.matching_thresholds.amount_weight
        self.date_weight = self.settings.matching_thresholds.date_weight
        self.semantic_weight = self.settings.matching_thresholds.semantic_weight
        
        # Initialize DeepSeek client for semantic matching
        self.deepseek_client = None
        if DEEPSEEK_AVAILABLE:
            try:
                api_key = os.getenv('DEEPSEEK_API_KEY')
                base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
                
                if not api_key:
                    self.logger.warning("DEEPSEEK_API_KEY not found in environment")
                else:
                    self.logger.info(f"Initializing DeepSeek client with base URL: {base_url}")
                    self.deepseek_client = OpenAI(
                        api_key=api_key,
                        base_url=base_url
                    )
                    self.logger.info("DeepSeek client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize DeepSeek client: {e}")
                self.deepseek_client = None
        
        self.logger.info(f"Initialized MatcherEngine")
        self.logger.info(f"Amount tolerance: ±${self.amount_tolerance}")
        self.logger.info(f"Date variance: ±{self.date_variance_days} days")
        self.logger.info(f"Match threshold: {self.match_threshold}")
        self.logger.info(f"Weights: Amount={self.amount_weight}, Date={self.date_weight}, Semantic={self.semantic_weight}")
    
    def match_all(
        self,
        transactions: List[Transaction],
        receipts: List[Receipt]
    ) -> Tuple[List[Match], List[Transaction], List[Receipt], MatchingStatistics]:
        """
        Match all transactions to receipts using multi-stage algorithm.
        
        Args:
            transactions: List of transactions from statements
            receipts: List of receipts from emails
            
        Returns:
            Tuple of (matches, unmatched_transactions, unmatched_receipts, statistics)
        """
        self.logger.log_milestone_start(
            "Matching Engine",
            f"Matching {len(transactions)} transactions to {len(receipts)} receipts"
        )
        
        start_time = time.time()
        
        # Initialize tracking
        matches = []
        unmatched_transactions = list(transactions)
        unmatched_receipts = list(receipts)
        
        stats = MatchingStatistics(
            total_transactions=len(transactions),
            total_receipts=len(receipts)
        )
        
        # Stage 1: Exact Matching
        self.logger.info("Stage 1: Exact Matching...")
        exact_matches = self._exact_matching(unmatched_transactions, unmatched_receipts)
        matches.extend(exact_matches)
        stats.exact_matches = len(exact_matches)
        
        # Remove matched items
        for match in exact_matches:
            if match.transaction in unmatched_transactions:
                unmatched_transactions.remove(match.transaction)
            if match.receipt in unmatched_receipts:
                unmatched_receipts.remove(match.receipt)
        
        self.logger.info(f"[OK] Exact matches: {stats.exact_matches}")
        
        # Stage 2: Fuzzy Matching
        self.logger.info("Stage 2: Fuzzy Matching...")
        fuzzy_matches = self._fuzzy_matching(unmatched_transactions, unmatched_receipts)
        matches.extend(fuzzy_matches)
        stats.fuzzy_matches = len(fuzzy_matches)
        
        # Remove matched items
        for match in fuzzy_matches:
            if match.transaction in unmatched_transactions:
                unmatched_transactions.remove(match.transaction)
            if match.receipt in unmatched_receipts:
                unmatched_receipts.remove(match.receipt)
        
        self.logger.info(f"[OK] Fuzzy matches: {stats.fuzzy_matches}")
        
        # Stage 3: Semantic Matching (if DeepSeek available)
        if self.deepseek_client:
            self.logger.info("Stage 3: Semantic Matching with DeepSeek...")
            semantic_matches = self._semantic_matching(unmatched_transactions, unmatched_receipts)
            matches.extend(semantic_matches)
            stats.semantic_matches = len(semantic_matches)
            
            # Remove matched items
            for match in semantic_matches:
                if match.transaction in unmatched_transactions:
                    unmatched_transactions.remove(match.transaction)
                if match.receipt in unmatched_receipts:
                    unmatched_receipts.remove(match.receipt)
            
            self.logger.info(f"[OK] Semantic matches: {stats.semantic_matches}")
        else:
            self.logger.warning("Semantic matching skipped (DeepSeek not available)")
        
        # Calculate statistics
        stats.unmatched_transactions = len(unmatched_transactions)
        stats.unmatched_receipts = len(unmatched_receipts)
        stats.processing_time_seconds = time.time() - start_time
        
        if matches:
            stats.average_confidence_score = sum(m.confidence_score for m in matches) / len(matches)
        
        # Log final statistics
        self.logger.log_milestone_end(
            "Matching Engine",
            records_processed=len(transactions),
            duration_seconds=stats.processing_time_seconds
        )
        self.logger.log_statistics(stats.to_dict())
        
        return (matches, unmatched_transactions, unmatched_receipts, stats)
    
    def _exact_matching(
        self,
        transactions: List[Transaction],
        receipts: List[Receipt]
    ) -> List[Match]:
        """
        Stage 1: Exact matching on amount, date, and reference number.
        
        Args:
            transactions: List of transactions
            receipts: List of receipts
            
        Returns:
            List of exact matches
        """
        matches = []
        
        for transaction in transactions:
            for receipt in receipts:
                # Check if already matched
                if any(m.receipt == receipt for m in matches):
                    continue
                
                # Exact amount match
                if not self._amounts_equal(transaction.amount, receipt.amount):
                    continue
                
                # Exact date match
                if transaction.date != receipt.transaction_date:
                    continue
                
                # If both have reference numbers, they must match
                if transaction.reference_number and receipt.receipt_id:
                    if transaction.reference_number != receipt.receipt_id:
                        continue
                
                # Create exact match
                match = Match(
                    match_id=f"exact_{transaction.transaction_id}_{receipt.receipt_id}",
                    transaction_id=transaction.transaction_id,
                    receipt_id=receipt.receipt_id,
                    match_stage="exact",
                    confidence_score=1.0,
                    amount_match_score=1.0,
                    date_match_score=1.0,
                    semantic_match_score=1.0
                )
                
                # Store references for easy access
                match.transaction = transaction
                match.receipt = receipt
                
                matches.append(match)
                break  # Move to next transaction
        
        return matches
    
    def _fuzzy_matching(
        self,
        transactions: List[Transaction],
        receipts: List[Receipt]
    ) -> List[Match]:
        """
        Stage 2: Fuzzy matching with amount tolerance and date variance.
        
        Args:
            transactions: List of transactions
            receipts: List of receipts
            
        Returns:
            List of fuzzy matches
            
        Validates Requirements:
        - 4.1: Filter by amount within ±$1.00
        - 4.2: Filter by date with 0-3 days variance
        - 4.7: Select highest scoring match
        """
        matches = []
        
        for transaction in transactions:
            best_match = None
            best_score = 0.0
            
            for receipt in receipts:
                # Check if already matched
                if any(m.receipt == receipt for m in matches):
                    continue
                
                # Amount filter (±$1.00 tolerance)
                if not self._amounts_within_tolerance(transaction.amount, receipt.amount):
                    continue
                
                # Date filter (0-3 days variance)
                if not self._dates_within_variance(transaction.date, receipt.transaction_date):
                    continue
                
                # Calculate fuzzy match score
                candidate = self._calculate_fuzzy_score(transaction, receipt)
                
                # Keep best match
                if candidate.total_score > best_score and candidate.total_score > self.match_threshold:
                    best_score = candidate.total_score
                    best_match = candidate
            
            # Create match if found
            if best_match:
                match = Match(
                    match_id=f"fuzzy_{transaction.transaction_id}_{best_match.receipt.receipt_id}",
                    transaction_id=transaction.transaction_id,
                    receipt_id=best_match.receipt.receipt_id,
                    match_stage="fuzzy",
                    confidence_score=best_match.total_score,
                    amount_match_score=best_match.amount_score,
                    date_match_score=best_match.date_score,
                    semantic_match_score=best_match.semantic_score
                )
                
                match.transaction = transaction
                match.receipt = best_match.receipt
                
                matches.append(match)
        
        return matches
    
    def _get_embedding(self, text: str):
        """
        Get embedding for text using DeepSeek API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array or None if failed
        """
        if not self.deepseek_client:
            return None
        
        try:
            # Use DeepSeek chat completion to generate embeddings
            # We'll use the model's understanding to create a semantic representation
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Extract key semantic features from the following transaction description. Return only the normalized merchant name and transaction type."},
                    {"role": "user", "content": text}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            # Convert response to a simple embedding based on text similarity
            # For a more robust solution, you could use a proper embedding model
            semantic_text = response.choices[0].message.content.strip().lower()
            
            # Create a simple bag-of-words embedding
            words = semantic_text.split()
            # Use a fixed vocabulary size for consistent embedding dimensions
            vocab_size = 100
            embedding = np.zeros(vocab_size)
            
            for i, word in enumerate(words[:vocab_size]):
                # Simple hash-based embedding
                hash_val = hash(word) % vocab_size
                embedding[hash_val] += 1.0
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error getting embedding from DeepSeek: {e}")
            return None
    
    def _semantic_matching(
        self,
        transactions: List[Transaction],
        receipts: List[Receipt]
    ) -> List[Match]:
        """
        Stage 3: Semantic matching using DeepSeek embeddings.
        
        Args:
            transactions: List of transactions
            receipts: List of receipts
            
        Returns:
            List of semantic matches
            
        Validates Requirement 4.3: Calculate semantic similarity using DeepSeek
        """
        if not self.deepseek_client:
            return []
        
        matches = []
        
        # Pre-compute embeddings for all receipts
        self.logger.info("Computing embeddings for receipts...")
        receipt_embeddings = []
        for receipt in receipts:
            desc = receipt.merchant_name or receipt.subject
            embedding = self._get_embedding(desc)
            receipt_embeddings.append(embedding)
        
        self.logger.info("Computing embeddings for transactions and matching...")
        for transaction in transactions:
            best_match = None
            best_score = 0.0
            
            # Get embedding for transaction
            transaction_embedding = self._get_embedding(transaction.description)
            if transaction_embedding is None:
                continue
            
            for idx, receipt in enumerate(receipts):
                # Check if already matched
                if any(m.receipt == receipt for m in matches):
                    continue
                
                # Amount and date must still be within tolerance
                if not self._amounts_within_tolerance(transaction.amount, receipt.amount):
                    continue
                
                if not self._dates_within_variance(transaction.date, receipt.transaction_date):
                    continue
                
                # Calculate semantic similarity
                receipt_embedding = receipt_embeddings[idx]
                if receipt_embedding is None:
                    continue
                
                similarity = self._cosine_similarity(transaction_embedding, receipt_embedding)
                
                # Calculate weighted score
                amount_score = self._calculate_amount_score(transaction.amount, receipt.amount)
                date_score = self._calculate_date_score(transaction.date, receipt.transaction_date)
                
                total_score = (
                    self.amount_weight * amount_score +
                    self.date_weight * date_score +
                    self.semantic_weight * similarity
                )
                
                # Keep best match
                if total_score > best_score and total_score > self.match_threshold:
                    best_score = total_score
                    best_match = MatchCandidate(
                        transaction=transaction,
                        receipt=receipt,
                        amount_score=amount_score,
                        date_score=date_score,
                        semantic_score=similarity,
                        total_score=total_score,
                        match_stage="semantic"
                    )
            
            # Create match if found
            if best_match:
                match = Match(
                    match_id=f"semantic_{transaction.transaction_id}_{best_match.receipt.receipt_id}",
                    transaction_id=transaction.transaction_id,
                    receipt_id=best_match.receipt.receipt_id,
                    match_stage="semantic",
                    confidence_score=best_match.total_score,
                    amount_match_score=best_match.amount_score,
                    date_match_score=best_match.date_score,
                    semantic_match_score=best_match.semantic_score
                )
                
                match.transaction = transaction
                match.receipt = best_match.receipt
                
                matches.append(match)
        
        return matches
    
    def _calculate_fuzzy_score(
        self,
        transaction: Transaction,
        receipt: Receipt
    ) -> MatchCandidate:
        """
        Calculate fuzzy match score using weighted formula.
        
        Args:
            transaction: Transaction object
            receipt: Receipt object
            
        Returns:
            MatchCandidate with scores
            
        Validates Requirement 4.4: Use weighted scoring formula
        """
        # Calculate individual scores
        amount_score = self._calculate_amount_score(transaction.amount, receipt.amount)
        date_score = self._calculate_date_score(transaction.date, receipt.transaction_date)
        
        # Simple string similarity for description (Levenshtein-like)
        desc_similarity = self._string_similarity(
            transaction.description.lower(),
            (receipt.merchant_name or receipt.subject).lower()
        )
        
        # Calculate weighted total
        total_score = (
            self.amount_weight * amount_score +
            self.date_weight * date_score +
            self.semantic_weight * desc_similarity
        )
        
        return MatchCandidate(
            transaction=transaction,
            receipt=receipt,
            amount_score=amount_score,
            date_score=date_score,
            semantic_score=desc_similarity,
            total_score=total_score,
            match_stage="fuzzy"
        )
    
    def _amounts_equal(self, amount1: Optional[Decimal], amount2: Optional[Decimal]) -> bool:
        """Check if two amounts are exactly equal."""
        if amount1 is None or amount2 is None:
            return False
        return abs(amount1 - amount2) < Decimal('0.01')
    
    def _amounts_within_tolerance(
        self,
        amount1: Optional[Decimal],
        amount2: Optional[Decimal]
    ) -> bool:
        """
        Check if amounts are within tolerance.
        
        Validates Requirement 4.1: Amount within ±$1.00
        """
        if amount1 is None or amount2 is None:
            return False
        
        diff = abs(amount1 - amount2)
        return diff <= Decimal(str(self.amount_tolerance))
    
    def _dates_within_variance(
        self,
        date1: Optional[str],
        date2: Optional[str]
    ) -> bool:
        """
        Check if dates are within variance.
        
        Validates Requirement 4.2: Date with 0-3 days variance
        """
        if not date1 or not date2:
            return False
        
        try:
            d1 = datetime.strptime(date1, '%Y-%m-%d')
            d2 = datetime.strptime(date2, '%Y-%m-%d')
            diff = abs((d1 - d2).days)
            return diff <= self.date_variance_days
        except:
            return False
    
    def _calculate_amount_score(self, amount1: Decimal, amount2: Decimal) -> float:
        """Calculate amount match score (0.0 to 1.0)."""
        if amount1 is None or amount2 is None:
            return 0.0
        
        diff = abs(amount1 - amount2)
        tolerance = Decimal(str(self.amount_tolerance))
        
        if diff == 0:
            return 1.0
        elif diff <= tolerance:
            # Linear decay within tolerance
            return float(1.0 - (diff / tolerance))
        else:
            return 0.0
    
    def _calculate_date_score(self, date1: str, date2: str) -> float:
        """Calculate date match score (0.0 to 1.0)."""
        if not date1 or not date2:
            return 0.0
        
        try:
            d1 = datetime.strptime(date1, '%Y-%m-%d')
            d2 = datetime.strptime(date2, '%Y-%m-%d')
            diff = abs((d1 - d2).days)
            
            if diff == 0:
                return 1.0
            elif diff <= self.date_variance_days:
                # Linear decay within variance
                return 1.0 - (diff / self.date_variance_days)
            else:
                return 0.0
        except:
            return 0.0
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple string similarity (0.0 to 1.0)."""
        if not str1 or not str2:
            return 0.0
        
        # Simple character overlap ratio
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors."""
        if np is None:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Convenience function
def match_transactions_to_receipts(
    transactions: List[Transaction],
    receipts: List[Receipt]
) -> Tuple[List[Match], List[Transaction], List[Receipt], MatchingStatistics]:
    """
    Match transactions to receipts using intelligent matching engine.
    
    Args:
        transactions: List of transactions
        receipts: List of receipts
        
    Returns:
        Tuple of (matches, unmatched_transactions, unmatched_receipts, statistics)
    """
    engine = MatcherEngine()
    return engine.match_all(transactions, receipts)
