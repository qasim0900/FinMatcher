"""
Property-based tests for Matching Engine.

This module contains property-based tests using Hypothesis to verify
universal properties of the Matching Engine component.

Testing Framework: pytest + Hypothesis
Feature: finmatcher-v2-upgrade
Task: 7.2 - Write property test for candidate filtering
"""

import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List

from finmatcher.core.matcher_engine import MatcherEngine
from finmatcher.database.models import Transaction, Receipt


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher", max_examples=100)
settings.load_profile("finmatcher")


# Custom strategies for generating test data
@st.composite
def transaction_strategy(draw):
    """Generate a valid Transaction object."""
    txn_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    date = draw(st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date()))
    amount = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2))
    description = draw(st.text(min_size=1, max_size=100))
    
    return Transaction(
        transaction_id=txn_id,
        date=date.strftime('%Y-%m-%d'),
        description=description,
        amount=amount,
        status="UNMATCHED"
    )


@st.composite
def receipt_strategy(draw):
    """Generate a valid Receipt object."""
    receipt_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    email_id = draw(st.text(min_size=1, max_size=20))
    date = draw(st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date()))
    amount = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2))
    merchant = draw(st.text(min_size=1, max_size=50))
    
    return Receipt(
        receipt_id=receipt_id,
        email_id=email_id,
        sender_name="Test Sender",
        sender_email="test@example.com",
        subject=f"Receipt from {merchant}",
        received_date=date.strftime('%Y-%m-%d'),
        amount=amount,
        transaction_date=date.strftime('%Y-%m-%d'),
        merchant_name=merchant
    )


class TestMatchingEngineProperties:
    """
    Property-based tests for Matching Engine.
    
    Tests verify universal properties that should hold across all inputs.
    """
    
    # Feature: finmatcher-v2-upgrade, Property 1: Candidate Filtering Enforces Tolerances
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date()),
        receipts=st.lists(
            st.tuples(
                st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
                st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())
            ),
            min_size=0,
            max_size=50
        )
    )
    @settings(max_examples=20)
    def test_candidate_filtering_enforces_tolerances(
        self,
        txn_amount: Decimal,
        txn_date,
        receipts: List[tuple]
    ):
        """
        **Validates: Requirements 1.1**
        
        Property 1: Candidate Filtering Enforces Tolerances
        
        For any transaction and receipt pool, all candidates returned by the filter
        must satisfy both the amount tolerance constraint (|A_txn - A_rec| ≤ $1.00)
        and the date variance constraint (|Days_diff| ≤ 3 days).
        
        This property verifies that:
        1. All filtered candidates have amounts within $1.00 of the transaction amount
        2. All filtered candidates have dates within 3 days of the transaction date
        3. No candidates outside these tolerances are included in the filtered pool
        4. The filtering is consistent across all transaction and receipt combinations
        """
        # Create matching engine
        engine = MatcherEngine()
        
        # Create transaction
        transaction = Transaction(
            transaction_id="test_txn_001",
            date=txn_date.strftime('%Y-%m-%d'),
            description="Test Transaction",
            amount=txn_amount,
            status="UNMATCHED"
        )
        
        # Create receipt objects from the generated data
        receipt_objects = []
        for idx, (rec_amount, rec_date) in enumerate(receipts):
            receipt = Receipt(
                receipt_id=f"test_rec_{idx:03d}",
                email_id=f"email_{idx:03d}",
                sender_name="Test Sender",
                sender_email="test@example.com",
                subject=f"Receipt {idx}",
                received_date=rec_date.strftime('%Y-%m-%d'),
                amount=rec_amount,
                transaction_date=rec_date.strftime('%Y-%m-%d'),
                merchant_name=f"Merchant {idx}"
            )
            receipt_objects.append(receipt)
        
        # Filter candidates using the fuzzy matching logic
        # We'll test the internal filtering by checking which receipts would pass
        candidates = []
        for receipt in receipt_objects:
            # Check amount tolerance
            if engine._amounts_within_tolerance(transaction.amount, receipt.amount):
                # Check date variance
                if engine._dates_within_variance(transaction.date, receipt.transaction_date):
                    candidates.append(receipt)
        
        # Assert: All candidates must satisfy both constraints
        for candidate in candidates:
            # Verify amount tolerance (≤ $1.00)
            amount_diff = abs(transaction.amount - candidate.amount)
            assert amount_diff <= Decimal("1.00"), (
                f"Candidate filtering failed: Amount difference {amount_diff} exceeds "
                f"tolerance of $1.00 for transaction amount {transaction.amount} "
                f"and receipt amount {candidate.amount}"
            )
            
            # Verify date variance (≤ 3 days)
            txn_date_obj = datetime.strptime(transaction.date, '%Y-%m-%d')
            rec_date_obj = datetime.strptime(candidate.transaction_date, '%Y-%m-%d')
            date_diff = abs((txn_date_obj - rec_date_obj).days)
            assert date_diff <= 3, (
                f"Candidate filtering failed: Date difference {date_diff} days exceeds "
                f"variance of 3 days for transaction date {transaction.date} "
                f"and receipt date {candidate.transaction_date}"
            )
        
        # Assert: No receipts outside tolerances should be in candidates
        for receipt in receipt_objects:
            amount_diff = abs(transaction.amount - receipt.amount)
            txn_date_obj = datetime.strptime(transaction.date, '%Y-%m-%d')
            rec_date_obj = datetime.strptime(receipt.transaction_date, '%Y-%m-%d')
            date_diff = abs((txn_date_obj - rec_date_obj).days)
            
            is_within_amount_tolerance = amount_diff <= Decimal("1.00")
            is_within_date_variance = date_diff <= 3
            
            if is_within_amount_tolerance and is_within_date_variance:
                # Should be in candidates
                assert receipt in candidates, (
                    f"Receipt {receipt.receipt_id} should be in candidates: "
                    f"amount_diff={amount_diff}, date_diff={date_diff}"
                )
            else:
                # Should NOT be in candidates
                assert receipt not in candidates, (
                    f"Receipt {receipt.receipt_id} should NOT be in candidates: "
                    f"amount_diff={amount_diff}, date_diff={date_diff}"
                )
    
    @given(
        transaction=transaction_strategy(),
        receipts=st.lists(receipt_strategy(), min_size=0, max_size=30)
    )
    @settings(max_examples=20)
    def test_candidate_filtering_with_complex_transactions(
        self,
        transaction: Transaction,
        receipts: List[Receipt]
    ):
        """
        **Validates: Requirements 1.1**
        
        Property 1: Candidate Filtering Enforces Tolerances (Complex Transactions)
        
        For any complex transaction and receipt pool with realistic data,
        all candidates returned by the filter must satisfy both tolerance constraints.
        
        This property verifies that:
        1. The filtering works correctly with realistic transaction and receipt objects
        2. All filtered candidates satisfy the $1.00 amount tolerance
        3. All filtered candidates satisfy the 3-day date variance
        4. The filtering is robust across diverse transaction descriptions and amounts
        """
        # Create matching engine
        engine = MatcherEngine()
        
        # Filter candidates using the fuzzy matching logic
        candidates = []
        for receipt in receipts:
            # Check amount tolerance
            if engine._amounts_within_tolerance(transaction.amount, receipt.amount):
                # Check date variance
                if engine._dates_within_variance(transaction.date, receipt.transaction_date):
                    candidates.append(receipt)
        
        # Assert: All candidates must satisfy both constraints
        for candidate in candidates:
            # Verify amount tolerance (≤ $1.00)
            amount_diff = abs(transaction.amount - candidate.amount)
            assert amount_diff <= Decimal("1.00"), (
                f"Candidate filtering failed: Amount difference {amount_diff} exceeds "
                f"tolerance of $1.00 for transaction {transaction.transaction_id} "
                f"(amount={transaction.amount}) and receipt {candidate.receipt_id} "
                f"(amount={candidate.amount})"
            )
            
            # Verify date variance (≤ 3 days)
            txn_date_obj = datetime.strptime(transaction.date, '%Y-%m-%d')
            rec_date_obj = datetime.strptime(candidate.transaction_date, '%Y-%m-%d')
            date_diff = abs((txn_date_obj - rec_date_obj).days)
            assert date_diff <= 3, (
                f"Candidate filtering failed: Date difference {date_diff} days exceeds "
                f"variance of 3 days for transaction {transaction.transaction_id} "
                f"(date={transaction.date}) and receipt {candidate.receipt_id} "
                f"(date={candidate.transaction_date})"
            )
    
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())
    )
    @settings(max_examples=20)
    def test_candidate_filtering_excludes_out_of_tolerance_amounts(
        self,
        txn_amount: Decimal,
        txn_date
    ):
        """
        **Validates: Requirements 1.1**
        
        Property 1: Candidate Filtering Enforces Tolerances (Amount Boundary)
        
        For any transaction, receipts with amounts outside the $1.00 tolerance
        must be excluded from the candidate pool.
        
        This property verifies that:
        1. Receipts with amount difference > $1.00 are excluded
        2. Receipts with amount difference ≤ $1.00 are included (if date is within variance)
        3. The boundary condition at exactly $1.00 is handled correctly
        """
        # Create matching engine
        engine = MatcherEngine()
        
        # Create transaction
        transaction = Transaction(
            transaction_id="test_txn_boundary",
            date=txn_date.strftime('%Y-%m-%d'),
            description="Test Transaction",
            amount=txn_amount,
            status="UNMATCHED"
        )
        
        # Create receipts at various amount differences
        receipts = [
            # Within tolerance (should be included if date is within variance)
            Receipt(
                receipt_id="rec_within_1",
                email_id="email_1",
                sender_name="Test",
                sender_email="test@example.com",
                subject="Receipt 1",
                received_date=txn_date.strftime('%Y-%m-%d'),  # Same date
                amount=txn_amount + Decimal("0.50"),  # +$0.50
                transaction_date=txn_date.strftime('%Y-%m-%d'),
                merchant_name="Merchant 1"
            ),
            # At boundary (should be included if date is within variance)
            Receipt(
                receipt_id="rec_boundary",
                email_id="email_2",
                sender_name="Test",
                sender_email="test@example.com",
                subject="Receipt 2",
                received_date=txn_date.strftime('%Y-%m-%d'),  # Same date
                amount=txn_amount + Decimal("1.00"),  # +$1.00 (boundary)
                transaction_date=txn_date.strftime('%Y-%m-%d'),
                merchant_name="Merchant 2"
            ),
            # Outside tolerance (should be excluded)
            Receipt(
                receipt_id="rec_outside",
                email_id="email_3",
                sender_name="Test",
                sender_email="test@example.com",
                subject="Receipt 3",
                received_date=txn_date.strftime('%Y-%m-%d'),  # Same date
                amount=txn_amount + Decimal("1.01"),  # +$1.01 (outside)
                transaction_date=txn_date.strftime('%Y-%m-%d'),
                merchant_name="Merchant 3"
            )
        ]
        
        # Filter candidates
        candidates = []
        for receipt in receipts:
            if engine._amounts_within_tolerance(transaction.amount, receipt.amount):
                if engine._dates_within_variance(transaction.date, receipt.transaction_date):
                    candidates.append(receipt)
        
        # Assert: Receipts within tolerance should be included
        assert any(c.receipt_id == "rec_within_1" for c in candidates), (
            "Receipt with amount difference $0.50 should be included in candidates"
        )
        
        assert any(c.receipt_id == "rec_boundary" for c in candidates), (
            "Receipt with amount difference $1.00 (boundary) should be included in candidates"
        )
        
        # Assert: Receipt outside tolerance should be excluded
        assert not any(c.receipt_id == "rec_outside" for c in candidates), (
            "Receipt with amount difference $1.01 should be excluded from candidates"
        )
    
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())
    )
    @settings(max_examples=20)
    def test_candidate_filtering_excludes_out_of_variance_dates(
        self,
        txn_amount: Decimal,
        txn_date
    ):
        """
        **Validates: Requirements 1.1**
        
        Property 1: Candidate Filtering Enforces Tolerances (Date Boundary)
        
        For any transaction, receipts with dates outside the 3-day variance
        must be excluded from the candidate pool.
        
        This property verifies that:
        1. Receipts with date difference > 3 days are excluded
        2. Receipts with date difference ≤ 3 days are included (if amount is within tolerance)
        3. The boundary condition at exactly 3 days is handled correctly
        """
        # Create matching engine
        engine = MatcherEngine()
        
        # Create transaction
        transaction = Transaction(
            transaction_id="test_txn_date_boundary",
            date=txn_date.strftime('%Y-%m-%d'),
            description="Test Transaction",
            amount=txn_amount,
            status="UNMATCHED"
        )
        
        # Create receipts at various date differences
        receipts = [
            # Within variance (should be included if amount is within tolerance)
            Receipt(
                receipt_id="rec_date_within",
                email_id="email_1",
                sender_name="Test",
                sender_email="test@example.com",
                subject="Receipt 1",
                received_date=(txn_date + timedelta(days=2)).strftime('%Y-%m-%d'),
                amount=txn_amount,  # Same amount
                transaction_date=(txn_date + timedelta(days=2)).strftime('%Y-%m-%d'),  # +2 days
                merchant_name="Merchant 1"
            ),
            # At boundary (should be included if amount is within tolerance)
            Receipt(
                receipt_id="rec_date_boundary",
                email_id="email_2",
                sender_name="Test",
                sender_email="test@example.com",
                subject="Receipt 2",
                received_date=(txn_date + timedelta(days=3)).strftime('%Y-%m-%d'),
                amount=txn_amount,  # Same amount
                transaction_date=(txn_date + timedelta(days=3)).strftime('%Y-%m-%d'),  # +3 days (boundary)
                merchant_name="Merchant 2"
            ),
            # Outside variance (should be excluded)
            Receipt(
                receipt_id="rec_date_outside",
                email_id="email_3",
                sender_name="Test",
                sender_email="test@example.com",
                subject="Receipt 3",
                received_date=(txn_date + timedelta(days=4)).strftime('%Y-%m-%d'),
                amount=txn_amount,  # Same amount
                transaction_date=(txn_date + timedelta(days=4)).strftime('%Y-%m-%d'),  # +4 days (outside)
                merchant_name="Merchant 3"
            )
        ]
        
        # Filter candidates
        candidates = []
        for receipt in receipts:
            if engine._amounts_within_tolerance(transaction.amount, receipt.amount):
                if engine._dates_within_variance(transaction.date, receipt.transaction_date):
                    candidates.append(receipt)
        
        # Assert: Receipts within variance should be included
        assert any(c.receipt_id == "rec_date_within" for c in candidates), (
            "Receipt with date difference 2 days should be included in candidates"
        )
        
        assert any(c.receipt_id == "rec_date_boundary" for c in candidates), (
            "Receipt with date difference 3 days (boundary) should be included in candidates"
        )
        
        # Assert: Receipt outside variance should be excluded
        assert not any(c.receipt_id == "rec_date_outside" for c in candidates), (
            "Receipt with date difference 4 days should be excluded from candidates"
        )

    # Feature: finmatcher-v2-upgrade, Property 2: Amount Score Follows Exponential Decay Formula
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
        amount_diff=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("1.00"), places=2)
    )
    @settings(max_examples=20)
    def test_amount_score_exponential_decay(
        self,
        txn_amount: Decimal,
        amount_diff: Decimal
    ):
        """
        **Validates: Requirements 1.2**
        
        Property 2: Amount Score Follows Exponential Decay Formula
        
        For any transaction amount and receipt amount within tolerance,
        the calculated amount score must equal e^(-λ |A_txn - A_rec|)
        where λ is the configured decay rate.
        
        This property verifies that:
        1. The amount score follows the exponential decay formula S = e^(-λ * diff)
        2. The score is always between 0 and 1
        3. The score decreases as the amount difference increases
        4. When amounts are equal (diff = 0), the score is 1.0
        5. The formula is applied consistently across all amount pairs
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration with known lambda_decay
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0  # Default decay rate
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate receipt amount
        rec_amount = txn_amount + amount_diff
        
        # Calculate amount score using the engine
        calculated_score = engine._calculate_amount_score(txn_amount, rec_amount)
        
        # Calculate expected score using the exponential decay formula
        # S = e^(-λ * |A_txn - A_rec|)
        expected_score = math.exp(-config.lambda_decay * float(amount_diff))
        
        # Assert: Calculated score must match the formula (within floating-point tolerance)
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Amount score calculation failed: "
            f"calculated={calculated_score:.6f}, expected={expected_score:.6f} "
            f"for txn_amount={txn_amount}, rec_amount={rec_amount}, "
            f"diff={amount_diff}, lambda={config.lambda_decay}"
        )
        
        # Assert: Score must be between 0 and 1
        assert 0.0 <= calculated_score <= 1.0, (
            f"Amount score {calculated_score} is outside valid range [0.0, 1.0]"
        )
        
        # Assert: When amounts are equal (diff = 0), score should be 1.0
        if amount_diff == Decimal("0.00"):
            assert abs(calculated_score - 1.0) < 0.0001, (
                f"Amount score should be 1.0 when amounts are equal, got {calculated_score}"
            )
    
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2)
    )
    @settings(max_examples=20)
    def test_amount_score_decreases_with_difference(
        self,
        txn_amount: Decimal
    ):
        """
        **Validates: Requirements 1.2**
        
        Property 2: Amount Score Follows Exponential Decay Formula (Monotonic Decrease)
        
        For any transaction amount, as the amount difference increases,
        the amount score must decrease monotonically.
        
        This property verifies that:
        1. Score at diff=0 > Score at diff=0.5 > Score at diff=1.0
        2. The exponential decay produces a monotonically decreasing function
        3. The decay rate is consistent across all amount values
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Test at different amount differences
        score_at_0 = engine._calculate_amount_score(txn_amount, txn_amount)
        score_at_0_25 = engine._calculate_amount_score(txn_amount, txn_amount + Decimal("0.25"))
        score_at_0_5 = engine._calculate_amount_score(txn_amount, txn_amount + Decimal("0.50"))
        score_at_0_75 = engine._calculate_amount_score(txn_amount, txn_amount + Decimal("0.75"))
        score_at_1_0 = engine._calculate_amount_score(txn_amount, txn_amount + Decimal("1.00"))
        
        # Assert: Scores must decrease monotonically
        assert score_at_0 > score_at_0_25, (
            f"Score should decrease from diff=0 to diff=0.25: "
            f"score_at_0={score_at_0:.6f}, score_at_0.25={score_at_0_25:.6f}"
        )
        
        assert score_at_0_25 > score_at_0_5, (
            f"Score should decrease from diff=0.25 to diff=0.5: "
            f"score_at_0.25={score_at_0_25:.6f}, score_at_0.5={score_at_0_5:.6f}"
        )
        
        assert score_at_0_5 > score_at_0_75, (
            f"Score should decrease from diff=0.5 to diff=0.75: "
            f"score_at_0.5={score_at_0_5:.6f}, score_at_0.75={score_at_0_75:.6f}"
        )
        
        assert score_at_0_75 > score_at_1_0, (
            f"Score should decrease from diff=0.75 to diff=1.0: "
            f"score_at_0.75={score_at_0_75:.6f}, score_at_1.0={score_at_1_0:.6f}"
        )
        
        # Assert: Score at diff=0 should be 1.0
        assert abs(score_at_0 - 1.0) < 0.0001, (
            f"Score at diff=0 should be 1.0, got {score_at_0:.6f}"
        )
    
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
        amount_diff=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("1.00"), places=2),
        lambda_decay=st.floats(min_value=0.5, max_value=5.0)
    )
    @settings(max_examples=20)
    def test_amount_score_with_different_lambda_values(
        self,
        txn_amount: Decimal,
        amount_diff: Decimal,
        lambda_decay: float
    ):
        """
        **Validates: Requirements 1.2**
        
        Property 2: Amount Score Follows Exponential Decay Formula (Lambda Variation)
        
        For any transaction amount, receipt amount, and lambda decay rate,
        the calculated amount score must equal e^(-λ |A_txn - A_rec|).
        
        This property verifies that:
        1. The formula works correctly with different lambda values
        2. Higher lambda values produce faster decay (lower scores for same diff)
        3. The formula is mathematically consistent across all parameter combinations
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration with the given lambda_decay
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=lambda_decay
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate receipt amount
        rec_amount = txn_amount + amount_diff
        
        # Calculate amount score using the engine
        calculated_score = engine._calculate_amount_score(txn_amount, rec_amount)
        
        # Calculate expected score using the exponential decay formula
        expected_score = math.exp(-lambda_decay * float(amount_diff))
        
        # Assert: Calculated score must match the formula
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Amount score calculation failed with lambda={lambda_decay:.2f}: "
            f"calculated={calculated_score:.6f}, expected={expected_score:.6f} "
            f"for diff={amount_diff}"
        )
        
        # Assert: Score must be between 0 and 1
        assert 0.0 <= calculated_score <= 1.0, (
            f"Amount score {calculated_score} is outside valid range [0.0, 1.0]"
        )
    
    @given(
        txn_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2),
        amount_diff=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("1.00"), places=2)
    )
    @settings(max_examples=20)
    def test_amount_score_boundary_conditions(
        self,
        txn_amount: Decimal,
        amount_diff: Decimal
    ):
        """
        **Validates: Requirements 1.2**
        
        Property 2: Amount Score Follows Exponential Decay Formula (Boundary Conditions)
        
        For any transaction amount and receipt amount within tolerance,
        the amount score must handle boundary conditions correctly.
        
        This property verifies that:
        1. Score at diff=0 is exactly 1.0
        2. Score at diff=1.0 (boundary) is calculated correctly
        3. Score is always positive and never exceeds 1.0
        4. The formula handles edge cases (very small amounts, very large amounts)
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Test with positive difference
        rec_amount_positive = txn_amount + amount_diff
        score_positive = engine._calculate_amount_score(txn_amount, rec_amount_positive)
        
        # Test with negative difference (should give same score due to absolute value)
        rec_amount_negative = txn_amount - amount_diff
        score_negative = engine._calculate_amount_score(txn_amount, rec_amount_negative)
        
        # Calculate expected score
        expected_score = math.exp(-config.lambda_decay * float(amount_diff))
        
        # Assert: Both positive and negative differences should give same score
        assert abs(score_positive - score_negative) < 0.0001, (
            f"Amount score should be symmetric: "
            f"score_positive={score_positive:.6f}, score_negative={score_negative:.6f}"
        )
        
        # Assert: Both should match the expected formula
        assert abs(score_positive - expected_score) < 0.0001, (
            f"Amount score (positive diff) doesn't match formula: "
            f"calculated={score_positive:.6f}, expected={expected_score:.6f}"
        )
        
        assert abs(score_negative - expected_score) < 0.0001, (
            f"Amount score (negative diff) doesn't match formula: "
            f"calculated={score_negative:.6f}, expected={expected_score:.6f}"
        )
        
        # Assert: Scores must be in valid range
        assert 0.0 <= score_positive <= 1.0, (
            f"Amount score {score_positive} is outside valid range [0.0, 1.0]"
        )
        
        assert 0.0 <= score_negative <= 1.0, (
            f"Amount score {score_negative} is outside valid range [0.0, 1.0]"
        )
        
        # Special case: When diff is 0, score should be exactly 1.0
        if amount_diff == Decimal("0.00"):
            score_zero = engine._calculate_amount_score(txn_amount, txn_amount)
            assert abs(score_zero - 1.0) < 0.0001, (
                f"Amount score at diff=0 should be 1.0, got {score_zero:.6f}"
            )

    # Feature: finmatcher-v2-upgrade, Property 3: Date Score Follows Linear Decay Formula
    @given(
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date()),
        days_diff=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=20)
    def test_date_score_linear_decay(
        self,
        txn_date,
        days_diff: int
    ):
        """
        **Validates: Requirements 1.3**
        
        Property 3: Date Score Follows Linear Decay Formula
        
        For any transaction date and receipt date within variance,
        the calculated date score must equal max(0, 1 - |Days_diff|/3).
        
        This property verifies that:
        1. The date score follows the linear decay formula S = max(0, 1 - |Days_diff|/3)
        2. The score is always between 0 and 1
        3. The score decreases linearly as the date difference increases
        4. When dates are equal (diff = 0), the score is 1.0
        5. When dates are 3 days apart, the score is 0.0
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration with date_variance = 3
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate receipt date (add days_diff to transaction date)
        rec_date = txn_date + timedelta(days=days_diff)
        
        # Calculate date score using the engine
        calculated_score = engine._calculate_date_score(txn_date, rec_date)
        
        # Calculate expected score using the linear decay formula
        # S = max(0, 1 - |Days_diff|/3)
        expected_score = max(0.0, 1.0 - (days_diff / 3.0))
        
        # Assert: Calculated score must match the formula (within floating-point tolerance)
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Date score calculation failed: "
            f"calculated={calculated_score:.6f}, expected={expected_score:.6f} "
            f"for txn_date={txn_date}, rec_date={rec_date}, "
            f"days_diff={days_diff}"
        )
        
        # Assert: Score must be between 0 and 1
        assert 0.0 <= calculated_score <= 1.0, (
            f"Date score {calculated_score} is outside valid range [0.0, 1.0]"
        )
        
        # Assert: When dates are equal (diff = 0), score should be 1.0
        if days_diff == 0:
            assert abs(calculated_score - 1.0) < 0.0001, (
                f"Date score should be 1.0 when dates are equal, got {calculated_score}"
            )
        
        # Assert: When dates are 3 days apart (diff = 3), score should be 0.0
        if days_diff == 3:
            assert abs(calculated_score - 0.0) < 0.0001, (
                f"Date score should be 0.0 when dates are 3 days apart, got {calculated_score}"
            )
    
    @given(
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())
    )
    @settings(max_examples=20)
    def test_date_score_decreases_linearly(
        self,
        txn_date
    ):
        """
        **Validates: Requirements 1.3**
        
        Property 3: Date Score Follows Linear Decay Formula (Linear Decrease)
        
        For any transaction date, as the date difference increases,
        the date score must decrease linearly.
        
        This property verifies that:
        1. Score at diff=0 > Score at diff=1 > Score at diff=2 > Score at diff=3
        2. The linear decay produces a monotonically decreasing function
        3. The rate of decrease is constant (linear, not exponential)
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Test at different date differences
        score_at_0 = engine._calculate_date_score(txn_date, txn_date)
        score_at_1 = engine._calculate_date_score(txn_date, txn_date + timedelta(days=1))
        score_at_2 = engine._calculate_date_score(txn_date, txn_date + timedelta(days=2))
        score_at_3 = engine._calculate_date_score(txn_date, txn_date + timedelta(days=3))
        
        # Assert: Scores must decrease monotonically
        assert score_at_0 > score_at_1, (
            f"Score should decrease from diff=0 to diff=1: "
            f"score_at_0={score_at_0:.6f}, score_at_1={score_at_1:.6f}"
        )
        
        assert score_at_1 > score_at_2, (
            f"Score should decrease from diff=1 to diff=2: "
            f"score_at_1={score_at_1:.6f}, score_at_2={score_at_2:.6f}"
        )
        
        assert score_at_2 > score_at_3, (
            f"Score should decrease from diff=2 to diff=3: "
            f"score_at_2={score_at_2:.6f}, score_at_3={score_at_3:.6f}"
        )
        
        # Assert: Score at diff=0 should be 1.0
        assert abs(score_at_0 - 1.0) < 0.0001, (
            f"Score at diff=0 should be 1.0, got {score_at_0:.6f}"
        )
        
        # Assert: Score at diff=3 should be 0.0
        assert abs(score_at_3 - 0.0) < 0.0001, (
            f"Score at diff=3 should be 0.0, got {score_at_3:.6f}"
        )
        
        # Assert: Linear decay means equal differences produce equal score changes
        # Change from 0 to 1 should equal change from 1 to 2 and from 2 to 3
        change_0_to_1 = score_at_0 - score_at_1
        change_1_to_2 = score_at_1 - score_at_2
        change_2_to_3 = score_at_2 - score_at_3
        
        assert abs(change_0_to_1 - change_1_to_2) < 0.0001, (
            f"Linear decay should produce equal changes: "
            f"change_0_to_1={change_0_to_1:.6f}, change_1_to_2={change_1_to_2:.6f}"
        )
        
        assert abs(change_1_to_2 - change_2_to_3) < 0.0001, (
            f"Linear decay should produce equal changes: "
            f"change_1_to_2={change_1_to_2:.6f}, change_2_to_3={change_2_to_3:.6f}"
        )
    
    @given(
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date()),
        days_diff=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=20)
    def test_date_score_symmetric_for_positive_negative_diff(
        self,
        txn_date,
        days_diff: int
    ):
        """
        **Validates: Requirements 1.3**
        
        Property 3: Date Score Follows Linear Decay Formula (Symmetry)
        
        For any transaction date and date difference, the date score should be
        symmetric - adding or subtracting the same number of days should produce
        the same score (due to absolute value in the formula).
        
        This property verifies that:
        1. Score for (txn_date, txn_date + N) equals score for (txn_date, txn_date - N)
        2. The absolute value in the formula is correctly applied
        3. The direction of the date difference doesn't matter
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate scores for positive and negative differences
        rec_date_positive = txn_date + timedelta(days=days_diff)
        rec_date_negative = txn_date - timedelta(days=days_diff)
        
        score_positive = engine._calculate_date_score(txn_date, rec_date_positive)
        score_negative = engine._calculate_date_score(txn_date, rec_date_negative)
        
        # Calculate expected score
        expected_score = max(0.0, 1.0 - (days_diff / 3.0))
        
        # Assert: Both positive and negative differences should give same score
        assert abs(score_positive - score_negative) < 0.0001, (
            f"Date score should be symmetric: "
            f"score_positive={score_positive:.6f}, score_negative={score_negative:.6f} "
            f"for days_diff={days_diff}"
        )
        
        # Assert: Both should match the expected formula
        assert abs(score_positive - expected_score) < 0.0001, (
            f"Date score (positive diff) doesn't match formula: "
            f"calculated={score_positive:.6f}, expected={expected_score:.6f}"
        )
        
        assert abs(score_negative - expected_score) < 0.0001, (
            f"Date score (negative diff) doesn't match formula: "
            f"calculated={score_negative:.6f}, expected={expected_score:.6f}"
        )
    
    @given(
        txn_date=st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date()),
        days_diff=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=20)
    def test_date_score_boundary_conditions(
        self,
        txn_date,
        days_diff: int
    ):
        """
        **Validates: Requirements 1.3**
        
        Property 3: Date Score Follows Linear Decay Formula (Boundary Conditions)
        
        For any transaction date and receipt date within variance,
        the date score must handle boundary conditions correctly.
        
        This property verifies that:
        1. Score at diff=0 is exactly 1.0
        2. Score at diff=3 (boundary) is exactly 0.0
        3. Score is always non-negative (max(0, ...) is applied)
        4. Score never exceeds 1.0
        5. The formula handles edge cases correctly
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate receipt date
        rec_date = txn_date + timedelta(days=days_diff)
        
        # Calculate date score
        calculated_score = engine._calculate_date_score(txn_date, rec_date)
        
        # Calculate expected score
        expected_score = max(0.0, 1.0 - (days_diff / 3.0))
        
        # Assert: Score matches formula
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Date score doesn't match formula: "
            f"calculated={calculated_score:.6f}, expected={expected_score:.6f}"
        )
        
        # Assert: Score is in valid range [0.0, 1.0]
        assert 0.0 <= calculated_score <= 1.0, (
            f"Date score {calculated_score} is outside valid range [0.0, 1.0]"
        )
        
        # Assert: Score is non-negative (max(0, ...) is applied)
        assert calculated_score >= 0.0, (
            f"Date score {calculated_score} should be non-negative"
        )
        
        # Boundary conditions
        if days_diff == 0:
            # At diff=0, score should be exactly 1.0
            assert abs(calculated_score - 1.0) < 0.0001, (
                f"Date score at diff=0 should be 1.0, got {calculated_score:.6f}"
            )
        
        if days_diff == 3:
            # At diff=3 (boundary), score should be exactly 0.0
            assert abs(calculated_score - 0.0) < 0.0001, (
                f"Date score at diff=3 should be 0.0, got {calculated_score:.6f}"
            )
        
        if 0 < days_diff < 3:
            # Between boundaries, score should be strictly between 0 and 1
            assert 0.0 < calculated_score < 1.0, (
                f"Date score at diff={days_diff} should be between 0 and 1, "
                f"got {calculated_score:.6f}"
            )

    # Feature: finmatcher-v2-upgrade, Property 4: Semantic Score Follows Cosine Similarity Formula
    @given(
        vec1=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        ),
        vec2=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=20)
    def test_semantic_score_cosine_similarity_formula(
        self,
        vec1: List[float],
        vec2: List[float]
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula
        
        For any pair of embedding vectors, the calculated semantic score must equal
        (V1 · V2) / (||V1|| × ||V2||).
        
        This property verifies that:
        1. The cosine similarity follows the formula: cos(θ) = (A·B) / (||A|| × ||B||)
        2. The score is always between -1 and 1 (or 0 and 1 for normalized vectors)
        3. Identical vectors produce a score of 1.0
        4. Orthogonal vectors produce a score of 0.0
        5. The formula is applied consistently across all vector pairs
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine (without DeepSeek client for direct testing)
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Ensure vectors have the same length for valid comparison
        min_len = min(len(vec1), len(vec2))
        vec1_trimmed = vec1[:min_len]
        vec2_trimmed = vec2[:min_len]
        
        # Skip if vectors are too short or all zeros
        if min_len < 2:
            return
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1_trimmed))
        magnitude2 = math.sqrt(sum(b * b for b in vec2_trimmed))
        
        # Skip if either vector has zero magnitude (undefined cosine similarity)
        if magnitude1 < 0.0001 or magnitude2 < 0.0001:
            return
        
        # Calculate cosine similarity using the engine's method
        calculated_score = engine._cosine_similarity(vec1_trimmed, vec2_trimmed)
        
        # Calculate expected cosine similarity using the formula
        # cos(θ) = (V1 · V2) / (||V1|| × ||V2||)
        dot_product = sum(a * b for a, b in zip(vec1_trimmed, vec2_trimmed))
        expected_cosine = dot_product / (magnitude1 * magnitude2)
        
        # The engine normalizes to 0-1 range: (similarity + 1) / 2
        expected_normalized = (expected_cosine + 1.0) / 2.0
        
        # Assert: Calculated score must match the formula (within floating-point tolerance)
        assert abs(calculated_score - expected_normalized) < 0.0001, (
            f"Cosine similarity calculation failed: "
            f"calculated={calculated_score:.6f}, expected={expected_normalized:.6f} "
            f"(raw cosine={expected_cosine:.6f})"
        )
        
        # Assert: Score must be between 0 and 1 (normalized range)
        assert 0.0 <= calculated_score <= 1.0, (
            f"Cosine similarity {calculated_score} is outside valid range [0.0, 1.0]"
        )
    
    @given(
        vec_size=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=20)
    def test_semantic_score_identical_vectors_produce_one(
        self,
        vec_size: int
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula (Identical Vectors)
        
        For any vector, the cosine similarity with itself must be 1.0.
        
        This property verifies that:
        1. Identical texts produce a semantic score of 1.0
        2. The formula correctly handles the case where vec1 == vec2
        3. The normalization preserves the maximum similarity value
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Create a non-zero vector
        vec = [1.0] * vec_size
        
        # Calculate cosine similarity with itself
        calculated_score = engine._cosine_similarity(vec, vec)
        
        # Assert: Identical vectors should produce score of 1.0
        assert abs(calculated_score - 1.0) < 0.0001, (
            f"Cosine similarity of identical vectors should be 1.0, got {calculated_score:.6f}"
        )
    
    @given(
        vec_size=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=20)
    def test_semantic_score_orthogonal_vectors_produce_half(
        self,
        vec_size: int
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula (Orthogonal Vectors)
        
        For any pair of orthogonal vectors (dot product = 0), the cosine similarity
        must be 0.0, which normalizes to 0.5 in the 0-1 range.
        
        This property verifies that:
        1. Orthogonal vectors produce a raw cosine similarity of 0.0
        2. After normalization to 0-1 range, the score is 0.5
        3. The formula correctly handles perpendicular vectors
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Create orthogonal vectors (dot product = 0)
        # vec1 = [1, 0, 0, 0, ...]
        # vec2 = [0, 1, 0, 0, ...]
        vec1 = [1.0] + [0.0] * (vec_size - 1)
        vec2 = [0.0, 1.0] + [0.0] * (vec_size - 2)
        
        # Calculate cosine similarity
        calculated_score = engine._cosine_similarity(vec1, vec2)
        
        # For orthogonal vectors:
        # - Dot product = 0
        # - Raw cosine similarity = 0
        # - Normalized score = (0 + 1) / 2 = 0.5
        expected_score = 0.5
        
        # Assert: Orthogonal vectors should produce normalized score of 0.5
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Cosine similarity of orthogonal vectors should be 0.5 (normalized), "
            f"got {calculated_score:.6f}"
        )
    
    @given(
        vec1=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=20)
    def test_semantic_score_opposite_vectors_produce_zero(
        self,
        vec1: List[float]
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula (Opposite Vectors)
        
        For any vector and its negative, the cosine similarity must be -1.0,
        which normalizes to 0.0 in the 0-1 range.
        
        This property verifies that:
        1. Opposite vectors produce a raw cosine similarity of -1.0
        2. After normalization to 0-1 range, the score is 0.0
        3. The formula correctly handles maximally dissimilar vectors
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Skip if vector has zero magnitude
        magnitude = math.sqrt(sum(a * a for a in vec1))
        if magnitude < 0.0001:
            return
        
        # Create opposite vector (vec2 = -vec1)
        vec2 = [-a for a in vec1]
        
        # Calculate cosine similarity
        calculated_score = engine._cosine_similarity(vec1, vec2)
        
        # For opposite vectors:
        # - Dot product = -||vec1||²
        # - Raw cosine similarity = -1.0
        # - Normalized score = (-1 + 1) / 2 = 0.0
        expected_score = 0.0
        
        # Assert: Opposite vectors should produce normalized score of 0.0
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Cosine similarity of opposite vectors should be 0.0 (normalized), "
            f"got {calculated_score:.6f}"
        )
    
    @given(
        vec1=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        ),
        vec2=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=20)
    def test_semantic_score_symmetric(
        self,
        vec1: List[float],
        vec2: List[float]
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula (Symmetry)
        
        For any pair of vectors, the cosine similarity must be symmetric:
        similarity(vec1, vec2) == similarity(vec2, vec1).
        
        This property verifies that:
        1. The order of vectors doesn't affect the result
        2. The dot product and magnitude calculations are commutative
        3. The formula is correctly implemented without order dependencies
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Ensure vectors have the same length
        min_len = min(len(vec1), len(vec2))
        vec1_trimmed = vec1[:min_len]
        vec2_trimmed = vec2[:min_len]
        
        # Skip if vectors are too short or have zero magnitude
        if min_len < 2:
            return
        
        magnitude1 = math.sqrt(sum(a * a for a in vec1_trimmed))
        magnitude2 = math.sqrt(sum(b * b for b in vec2_trimmed))
        
        if magnitude1 < 0.0001 or magnitude2 < 0.0001:
            return
        
        # Calculate cosine similarity in both orders
        score_1_2 = engine._cosine_similarity(vec1_trimmed, vec2_trimmed)
        score_2_1 = engine._cosine_similarity(vec2_trimmed, vec1_trimmed)
        
        # Assert: Cosine similarity must be symmetric
        assert abs(score_1_2 - score_2_1) < 0.0001, (
            f"Cosine similarity should be symmetric: "
            f"similarity(vec1, vec2)={score_1_2:.6f}, "
            f"similarity(vec2, vec1)={score_2_1:.6f}"
        )
    
    @given(
        vec1=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        ),
        vec2=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=20)
    def test_semantic_score_handles_zero_vectors(
        self,
        vec1: List[float],
        vec2: List[float]
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula (Zero Vectors)
        
        For any vector paired with a zero vector, the cosine similarity must be 0.0
        (to avoid division by zero).
        
        This property verifies that:
        1. Zero vectors are handled gracefully without errors
        2. Division by zero is avoided
        3. The result is 0.0 when either vector has zero magnitude
        """
        import math
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Ensure vectors have the same length
        min_len = min(len(vec1), len(vec2))
        vec1_trimmed = vec1[:min_len]
        
        # Create a zero vector
        zero_vec = [0.0] * min_len
        
        # Skip if vec1 is also a zero vector (both zero is a special case)
        magnitude1 = math.sqrt(sum(a * a for a in vec1_trimmed))
        if magnitude1 < 0.0001:
            # Both vectors are zero - should return 0.0
            score = engine._cosine_similarity(zero_vec, zero_vec)
            assert score == 0.0, (
                f"Cosine similarity of two zero vectors should be 0.0, got {score:.6f}"
            )
            return
        
        # Calculate cosine similarity with zero vector
        score = engine._cosine_similarity(vec1_trimmed, zero_vec)
        
        # Assert: Cosine similarity with zero vector should be 0.0
        assert score == 0.0, (
            f"Cosine similarity with zero vector should be 0.0, got {score:.6f}"
        )
    
    @given(
        vec1=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        ),
        vec2=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=100
        )
    )
    @settings(max_examples=20)
    def test_semantic_score_handles_mismatched_lengths(
        self,
        vec1: List[float],
        vec2: List[float]
    ):
        """
        **Validates: Requirements 1.4, 2.3**
        
        Property 4: Semantic Score Follows Cosine Similarity Formula (Mismatched Lengths)
        
        For any pair of vectors with different lengths, the cosine similarity
        calculation must handle the mismatch gracefully (return 0.0).
        
        This property verifies that:
        1. Mismatched vector lengths are detected
        2. The function returns 0.0 instead of crashing
        3. Error handling is robust
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Only test if vectors have different lengths
        if len(vec1) == len(vec2):
            return
        
        # Calculate cosine similarity with mismatched lengths
        score = engine._cosine_similarity(vec1, vec2)
        
        # Assert: Mismatched lengths should return 0.0
        assert score == 0.0, (
            f"Cosine similarity with mismatched lengths should be 0.0, "
            f"got {score:.6f} for lengths {len(vec1)} and {len(vec2)}"
        )

    # Feature: finmatcher-v2-upgrade, Property 5: Composite Score is Weighted Sum
    @given(
        amount_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        date_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        semantic_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=500)
    def test_composite_score_is_weighted_sum(
        self,
        amount_score: float,
        date_score: float,
        semantic_score: float
    ):
        """
        **Validates: Requirements 1.5**
        
        Property 5: Composite Score is Weighted Sum
        
        For any amount score, date score, and semantic score, the composite score
        must equal W_a · S_amount + W_d · S_date + W_s · S_semantic where weights
        are normalized to sum to 1.0.
        
        This property verifies that:
        1. The composite score follows the weighted sum formula
        2. The weights sum to 1.0
        3. The composite score is always between 0 and 1
        4. The formula is applied consistently across all score combinations
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration with known weights
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate composite score using the engine
        calculated_score = engine._calculate_composite_score(
            amount_score, date_score, semantic_score
        )
        
        # Calculate expected score using the weighted sum formula
        # S_total = W_a · S_amount + W_d · S_date + W_s · S_semantic
        expected_score = (
            config.weight_amount * amount_score +
            config.weight_date * date_score +
            config.weight_semantic * semantic_score
        )
        
        # Assert: Calculated score must match the formula (within floating-point tolerance)
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Composite score calculation failed: "
            f"calculated={calculated_score:.6f}, expected={expected_score:.6f} "
            f"for amount_score={amount_score:.4f}, date_score={date_score:.4f}, "
            f"semantic_score={semantic_score:.4f}, "
            f"weights=(amount={config.weight_amount}, date={config.weight_date}, "
            f"semantic={config.weight_semantic})"
        )
        
        # Assert: Composite score must be between 0 and 1
        assert 0.0 <= calculated_score <= 1.0, (
            f"Composite score {calculated_score} is outside valid range [0.0, 1.0]"
        )
        
        # Assert: Weights sum to 1.0 (within tolerance)
        weight_sum = config.weight_amount + config.weight_date + config.weight_semantic
        assert abs(weight_sum - 1.0) < 0.001, (
            f"Weights must sum to 1.0, got {weight_sum}"
        )
    
    @given(
        amount_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        date_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        semantic_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_d=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        w_s=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=500)
    def test_composite_score_with_various_weights(
        self,
        amount_score: float,
        date_score: float,
        semantic_score: float,
        w_a: float,
        w_d: float,
        w_s: float
    ):
        """
        **Validates: Requirements 1.5**
        
        Property 5: Composite Score is Weighted Sum (Various Weights)
        
        For any amount score, date score, semantic score, and weight combination,
        the composite score must equal the weighted sum formula after normalizing
        weights to sum to 1.0.
        
        This property verifies that:
        1. The formula works correctly with different weight combinations
        2. Weights are normalized to sum to 1.0
        3. The composite score is always between 0 and 1
        4. The formula is mathematically consistent across all parameter combinations
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Skip if all weights are zero (cannot normalize)
        weight_sum = w_a + w_d + w_s
        if weight_sum < 0.0001:
            return
        
        # Normalize weights to sum to 1.0
        w_a_normalized = w_a / weight_sum
        w_d_normalized = w_d / weight_sum
        w_s_normalized = w_s / weight_sum
        
        # Create matching configuration with normalized weights
        config = MatchingConfig(
            weight_amount=w_a_normalized,
            weight_date=w_d_normalized,
            weight_semantic=w_s_normalized,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate composite score using the engine
        calculated_score = engine._calculate_composite_score(
            amount_score, date_score, semantic_score
        )
        
        # Calculate expected score using the weighted sum formula
        expected_score = (
            w_a_normalized * amount_score +
            w_d_normalized * date_score +
            w_s_normalized * semantic_score
        )
        
        # Assert: Calculated score must match the formula
        assert abs(calculated_score - expected_score) < 0.0001, (
            f"Composite score calculation failed with weights "
            f"(amount={w_a_normalized:.4f}, date={w_d_normalized:.4f}, "
            f"semantic={w_s_normalized:.4f}): "
            f"calculated={calculated_score:.6f}, expected={expected_score:.6f}"
        )
        
        # Assert: Composite score must be between 0 and 1
        assert 0.0 <= calculated_score <= 1.0, (
            f"Composite score {calculated_score} is outside valid range [0.0, 1.0]"
        )
    
    @given(
        base_amount_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        date_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        semantic_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        delta=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=500)
    def test_composite_score_changes_proportionally_with_individual_scores(
        self,
        base_amount_score: float,
        date_score: float,
        semantic_score: float,
        delta: float
    ):
        """
        **Validates: Requirements 1.5**
        
        Property 5: Composite Score is Weighted Sum (Proportional Changes)
        
        For any set of scores, changing an individual score should affect the
        composite score proportionally to its weight.
        
        This property verifies that:
        1. Changing the amount score by delta changes composite by W_a * delta
        2. Changing the date score by delta changes composite by W_d * delta
        3. Changing the semantic score by delta changes composite by W_s * delta
        4. The relationship is linear and proportional to the weights
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate base composite score
        base_composite = engine._calculate_composite_score(
            base_amount_score, date_score, semantic_score
        )
        
        # Test 1: Change amount score by delta
        new_amount_score = max(0.0, min(1.0, base_amount_score + delta))
        actual_delta_amount = new_amount_score - base_amount_score
        
        new_composite_amount = engine._calculate_composite_score(
            new_amount_score, date_score, semantic_score
        )
        
        expected_change_amount = config.weight_amount * actual_delta_amount
        actual_change_amount = new_composite_amount - base_composite
        
        # Assert: Change in composite should be proportional to weight_amount
        assert abs(actual_change_amount - expected_change_amount) < 0.0001, (
            f"Composite score change not proportional to amount weight: "
            f"expected_change={expected_change_amount:.6f}, "
            f"actual_change={actual_change_amount:.6f}, "
            f"weight_amount={config.weight_amount}, delta={actual_delta_amount:.6f}"
        )
        
        # Test 2: Change date score by delta
        new_date_score = max(0.0, min(1.0, date_score + delta))
        actual_delta_date = new_date_score - date_score
        
        new_composite_date = engine._calculate_composite_score(
            base_amount_score, new_date_score, semantic_score
        )
        
        expected_change_date = config.weight_date * actual_delta_date
        actual_change_date = new_composite_date - base_composite
        
        # Assert: Change in composite should be proportional to weight_date
        assert abs(actual_change_date - expected_change_date) < 0.0001, (
            f"Composite score change not proportional to date weight: "
            f"expected_change={expected_change_date:.6f}, "
            f"actual_change={actual_change_date:.6f}, "
            f"weight_date={config.weight_date}, delta={actual_delta_date:.6f}"
        )
        
        # Test 3: Change semantic score by delta
        new_semantic_score = max(0.0, min(1.0, semantic_score + delta))
        actual_delta_semantic = new_semantic_score - semantic_score
        
        new_composite_semantic = engine._calculate_composite_score(
            base_amount_score, date_score, new_semantic_score
        )
        
        expected_change_semantic = config.weight_semantic * actual_delta_semantic
        actual_change_semantic = new_composite_semantic - base_composite
        
        # Assert: Change in composite should be proportional to weight_semantic
        assert abs(actual_change_semantic - expected_change_semantic) < 0.0001, (
            f"Composite score change not proportional to semantic weight: "
            f"expected_change={expected_change_semantic:.6f}, "
            f"actual_change={actual_change_semantic:.6f}, "
            f"weight_semantic={config.weight_semantic}, delta={actual_delta_semantic:.6f}"
        )
    
    @given(
        amount_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        date_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        semantic_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=500)
    def test_composite_score_boundary_conditions(
        self,
        amount_score: float,
        date_score: float,
        semantic_score: float
    ):
        """
        **Validates: Requirements 1.5**
        
        Property 5: Composite Score is Weighted Sum (Boundary Conditions)
        
        For any set of scores, the composite score must handle boundary conditions
        correctly.
        
        This property verifies that:
        1. When all scores are 0.0, composite is 0.0
        2. When all scores are 1.0, composite is 1.0
        3. Composite is always between 0 and 1 for valid inputs
        4. The formula handles edge cases correctly
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Calculate composite score
        composite = engine._calculate_composite_score(
            amount_score, date_score, semantic_score
        )
        
        # Assert: Composite must be between 0 and 1
        assert 0.0 <= composite <= 1.0, (
            f"Composite score {composite} is outside valid range [0.0, 1.0] "
            f"for scores (amount={amount_score:.4f}, date={date_score:.4f}, "
            f"semantic={semantic_score:.4f})"
        )
        
        # Test boundary: All scores are 0.0
        composite_all_zero = engine._calculate_composite_score(0.0, 0.0, 0.0)
        assert abs(composite_all_zero - 0.0) < 0.0001, (
            f"Composite score should be 0.0 when all scores are 0.0, got {composite_all_zero:.6f}"
        )
        
        # Test boundary: All scores are 1.0
        composite_all_one = engine._calculate_composite_score(1.0, 1.0, 1.0)
        assert abs(composite_all_one - 1.0) < 0.0001, (
            f"Composite score should be 1.0 when all scores are 1.0, got {composite_all_one:.6f}"
        )
        
        # Test boundary: Only amount score is 1.0, others are 0.0
        composite_amount_only = engine._calculate_composite_score(1.0, 0.0, 0.0)
        expected_amount_only = config.weight_amount
        assert abs(composite_amount_only - expected_amount_only) < 0.0001, (
            f"Composite score should be {expected_amount_only:.4f} when only amount score is 1.0, "
            f"got {composite_amount_only:.6f}"
        )
        
        # Test boundary: Only date score is 1.0, others are 0.0
        composite_date_only = engine._calculate_composite_score(0.0, 1.0, 0.0)
        expected_date_only = config.weight_date
        assert abs(composite_date_only - expected_date_only) < 0.0001, (
            f"Composite score should be {expected_date_only:.4f} when only date score is 1.0, "
            f"got {composite_date_only:.6f}"
        )
        
        # Test boundary: Only semantic score is 1.0, others are 0.0
        composite_semantic_only = engine._calculate_composite_score(0.0, 0.0, 1.0)
        expected_semantic_only = config.weight_semantic
        assert abs(composite_semantic_only - expected_semantic_only) < 0.0001, (
            f"Composite score should be {expected_semantic_only:.4f} when only semantic score is 1.0, "
            f"got {composite_semantic_only:.6f}"
        )


    # Feature: finmatcher-v2-upgrade, Property 6: Confidence Classification is Correct for All Scores
    @given(composite_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_confidence_classification_correct_for_all_scores(
        self,
        composite_score: float
    ):
        """
        **Validates: Requirements 1.6, 1.7, 1.8**
        
        Property 6: Confidence Classification is Correct for All Scores
        
        For any composite score, the classification must be:
        - Exact Match if score >= 0.98
        - High Confidence if 0.85 <= score < 0.98
        - Low Confidence if score < 0.85
        
        This property verifies that:
        1. All scores >= 0.98 are classified as EXACT
        2. All scores in [0.85, 0.98) are classified as HIGH
        3. All scores < 0.85 are classified as LOW
        4. The classification boundaries are precise and consistent
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig, MatchConfidence
        
        # Create matching configuration with standard thresholds
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Classify the composite score
        confidence = engine._classify_confidence(composite_score)
        
        # Assert: Classification must match the threshold rules
        if composite_score >= 0.98:
            assert confidence == MatchConfidence.EXACT, (
                f"Score {composite_score:.6f} >= 0.98 should be classified as EXACT, "
                f"but got {confidence.value}"
            )
        elif composite_score >= 0.85:
            assert confidence == MatchConfidence.HIGH, (
                f"Score {composite_score:.6f} in [0.85, 0.98) should be classified as HIGH, "
                f"but got {confidence.value}"
            )
        else:
            assert confidence == MatchConfidence.LOW, (
                f"Score {composite_score:.6f} < 0.85 should be classified as LOW, "
                f"but got {confidence.value}"
            )
    
    @given(
        exact_threshold=st.floats(min_value=0.90, max_value=0.99, allow_nan=False, allow_infinity=False),
        high_threshold=st.floats(min_value=0.70, max_value=0.89, allow_nan=False, allow_infinity=False),
        composite_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_confidence_classification_with_custom_thresholds(
        self,
        exact_threshold: float,
        high_threshold: float,
        composite_score: float
    ):
        """
        **Validates: Requirements 1.6, 1.7, 1.8**
        
        Property 6: Confidence Classification with Custom Thresholds
        
        For any composite score and custom threshold configuration, the classification
        must correctly apply the configured thresholds.
        
        This property verifies that:
        1. The classification logic adapts to custom thresholds
        2. The boundary conditions are respected for any valid threshold values
        3. The classification is consistent with the configured thresholds
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig, MatchConfidence
        
        # Ensure exact_threshold > high_threshold
        if exact_threshold <= high_threshold:
            exact_threshold = high_threshold + 0.01
        
        # Create matching configuration with custom thresholds
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=exact_threshold,
            high_threshold=high_threshold,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Classify the composite score
        confidence = engine._classify_confidence(composite_score)
        
        # Assert: Classification must match the custom threshold rules
        if composite_score >= exact_threshold:
            assert confidence == MatchConfidence.EXACT, (
                f"Score {composite_score:.6f} >= {exact_threshold:.6f} should be classified as EXACT, "
                f"but got {confidence.value}"
            )
        elif composite_score >= high_threshold:
            assert confidence == MatchConfidence.HIGH, (
                f"Score {composite_score:.6f} in [{high_threshold:.6f}, {exact_threshold:.6f}) "
                f"should be classified as HIGH, but got {confidence.value}"
            )
        else:
            assert confidence == MatchConfidence.LOW, (
                f"Score {composite_score:.6f} < {high_threshold:.6f} should be classified as LOW, "
                f"but got {confidence.value}"
            )
    
    @given(
        score_offset=st.floats(min_value=-0.001, max_value=0.001, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20)
    def test_confidence_classification_boundary_precision(
        self,
        score_offset: float
    ):
        """
        **Validates: Requirements 1.6, 1.7, 1.8**
        
        Property 6: Confidence Classification Boundary Precision
        
        For scores at or near the classification boundaries (0.98 and 0.85),
        the classification must be precise and consistent.
        
        This property verifies that:
        1. Scores exactly at 0.98 are classified as EXACT
        2. Scores just below 0.98 are classified as HIGH
        3. Scores exactly at 0.85 are classified as HIGH
        4. Scores just below 0.85 are classified as LOW
        5. The boundaries are handled with floating-point precision
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig, MatchConfidence
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Test boundary at 0.98
        score_at_exact_boundary = 0.98 + score_offset
        if 0.0 <= score_at_exact_boundary <= 1.0:
            confidence = engine._classify_confidence(score_at_exact_boundary)
            
            if score_at_exact_boundary >= 0.98:
                assert confidence == MatchConfidence.EXACT, (
                    f"Score {score_at_exact_boundary:.10f} >= 0.98 should be EXACT, "
                    f"but got {confidence.value}"
                )
            elif score_at_exact_boundary >= 0.85:
                assert confidence == MatchConfidence.HIGH, (
                    f"Score {score_at_exact_boundary:.10f} in [0.85, 0.98) should be HIGH, "
                    f"but got {confidence.value}"
                )
        
        # Test boundary at 0.85
        score_at_high_boundary = 0.85 + score_offset
        if 0.0 <= score_at_high_boundary <= 1.0:
            confidence = engine._classify_confidence(score_at_high_boundary)
            
            if score_at_high_boundary >= 0.98:
                assert confidence == MatchConfidence.EXACT, (
                    f"Score {score_at_high_boundary:.10f} >= 0.98 should be EXACT, "
                    f"but got {confidence.value}"
                )
            elif score_at_high_boundary >= 0.85:
                assert confidence == MatchConfidence.HIGH, (
                    f"Score {score_at_high_boundary:.10f} >= 0.85 should be HIGH, "
                    f"but got {confidence.value}"
                )
            else:
                assert confidence == MatchConfidence.LOW, (
                    f"Score {score_at_high_boundary:.10f} < 0.85 should be LOW, "
                    f"but got {confidence.value}"
                )
    
    @given(
        scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=20)
    def test_confidence_classification_monotonicity(
        self,
        scores: List[float]
    ):
        """
        **Validates: Requirements 1.6, 1.7, 1.8**
        
        Property 6: Confidence Classification Monotonicity
        
        For any set of composite scores, the classification must be monotonic:
        higher scores should never result in lower confidence classifications.
        
        This property verifies that:
        1. If score_a > score_b, then confidence(score_a) >= confidence(score_b)
        2. The confidence levels form a total order: LOW < HIGH < EXACT
        3. The classification is consistent across all score comparisons
        """
        from finmatcher.core.matching_engine import MatchingEngine
        from finmatcher.storage.models import MatchingConfig, MatchConfidence
        
        # Create matching configuration
        config = MatchingConfig(
            weight_amount=0.4,
            weight_date=0.3,
            weight_semantic=0.3,
            amount_tolerance=Decimal("1.00"),
            date_variance=3,
            exact_threshold=0.98,
            high_threshold=0.85,
            lambda_decay=2.0
        )
        
        # Create matching engine
        engine = MatchingEngine(config=config, deepseek_client=None)
        
        # Define confidence ordering
        confidence_order = {
            MatchConfidence.LOW: 0,
            MatchConfidence.HIGH: 1,
            MatchConfidence.EXACT: 2
        }
        
        # Sort scores
        sorted_scores = sorted(scores)
        
        # Classify all scores
        classifications = [engine._classify_confidence(score) for score in sorted_scores]
        
        # Assert: Classifications should be monotonically non-decreasing
        for i in range(len(classifications) - 1):
            current_confidence = confidence_order[classifications[i]]
            next_confidence = confidence_order[classifications[i + 1]]
            
            assert current_confidence <= next_confidence, (
                f"Classification is not monotonic: score {sorted_scores[i]:.6f} "
                f"classified as {classifications[i].value}, but higher score "
                f"{sorted_scores[i + 1]:.6f} classified as {classifications[i + 1].value}"
            )

