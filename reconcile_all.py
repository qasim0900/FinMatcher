#!/usr/bin/env python3
"""
FinMatcher v3.0 - Complete Reconciliation Script
Handles all 4 milestones:
1. Reconcile Meriwest statement
2. Reconcile Amex statement
3. Reconcile Chase statement
4. Identify unmatched receipts
"""

import sys
import os
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent / 'services'))

from common.config import get_config
from common.db_pool import get_db_pool
from common.logger import get_logger
from statement_parser.parser import StatementParser

logger = get_logger("reconciliation", level="INFO", json_format=False)


def main():
    """Main reconciliation workflow"""
    print("=" * 80)
    print("FinMatcher v3.0 - Credit Card Reconciliation")
    print("=" * 80)
    
    try:
        # Initialize
        logger.info("Initializing configuration...")
        config = get_config("reconciliation")
        db_pool = get_db_pool(config.database)
        
        # Step 1: Parse all credit card statements
        print("\n" + "=" * 80)
        print("STEP 1: Parsing Credit Card Statements")
        print("=" * 80)
        
        parser = StatementParser(statements_dir="statements")
        transactions_by_card = parser.parse_all()
        
        # Display summary
        print("\n✓ Statement Parsing Summary:")
        for card_type, transactions in transactions_by_card.items():
            print(f"  - {card_type.upper()}: {len(transactions)} transactions")
            if transactions:
                total_amount = sum(t.amount for t in transactions)
                print(f"    Total: ${total_amount:,.2f}")
        
        # Step 2: Save to database
        print("\n" + "=" * 80)
        print("STEP 2: Saving Transactions to Database")
        print("=" * 80)
        
        parser.save_to_database(transactions_by_card, db_pool)
        print("✓ Transactions saved to receipts table")
        
        # Step 3: Check emails in database
        print("\n" + "=" * 80)
        print("STEP 3: Checking Email Receipts")
        print("=" * 80)
        
        email_count = db_pool.fetchone("SELECT COUNT(*) FROM emails")[0]
        print(f"✓ Total emails in database: {email_count}")
        
        if email_count == 0:
            print("\n⚠ WARNING: No emails found in database!")
            print("  Please run email ingestion first:")
            print("  python main.py  # or your email ingestion script")
            print("\n  Then run this script again.")
            return
        
        # Step 4: Run matching for each card
        print("\n" + "=" * 80)
        print("STEP 4: Matching Transactions to Receipts")
        print("=" * 80)
        
        # Import matching engine
        sys.path.insert(0, str(Path(__file__).parent / 'finmatcher'))
        from optimization.spatial_indexer import SpatialIndexer
        from optimization.vectorized_scorer import VectorizedScorer
        
        # Load receipts (credit card transactions)
        receipts_query = """
            SELECT receipt_id, amount, transaction_date, merchant_name, payment_method
            FROM receipts
            ORDER BY transaction_date DESC
        """
        receipts = db_pool.fetchall(receipts_query)
        print(f"✓ Loaded {len(receipts)} credit card transactions")
        
        # Load emails
        emails_query = """
            SELECT email_id, amount, transaction_date, merchant_name, subject
            FROM emails
            WHERE amount IS NOT NULL
            ORDER BY transaction_date DESC
        """
        emails = db_pool.fetchall(emails_query)
        print(f"✓ Loaded {len(emails)} email receipts with amounts")
        
        if not emails:
            print("\n⚠ WARNING: No emails with extracted amounts found!")
            print("  The system needs to extract transaction data from emails first.")
            return
        
        # Build spatial index
        print("\n✓ Building KDTree spatial index...")
        indexer = SpatialIndexer()
        
        # Prepare receipt data for indexing
        receipt_data = []
        for r in receipts:
            receipt_data.append({
                'receipt_id': r[0],
                'amount': float(r[1]) if r[1] else 0.0,
                'transaction_date': r[2],
                'merchant_name': r[3] or '',
                'payment_method': r[4] or ''
            })
        
        indexer.build_index(receipt_data)
        print(f"✓ Index built with {len(receipt_data)} receipts")
        
        # Match each email to receipts
        print("\n✓ Matching emails to credit card transactions...")
        scorer = VectorizedScorer()
        
        matches_by_card = {
            'meriwest': [],
            'amex': [],
            'chase': [],
            'unmatched': []
        }
        
        matched_email_ids = set()
        
        for email in emails:
            email_id, amount, date, merchant, subject = email
            
            # Query candidates
            email_data = {
                'amount': float(amount) if amount else 0.0,
                'transaction_date': date,
                'merchant_name': merchant or subject or ''
            }
            
            candidates = indexer.query_candidates(email_data)
            
            if candidates:
                # Score candidates
                best_match = None
                best_score = 0.0
                
                for candidate_idx in candidates:
                    receipt = receipt_data[candidate_idx]
                    score = scorer.compute_similarity(email_data, receipt)
                    
                    if score > best_score:
                        best_score = score
                        best_match = receipt
                
                if best_match and best_score > 0.75:  # Threshold
                    # Determine card type
                    card_type = best_match.get('payment_method', '').lower()
                    
                    if 'meriwest' in card_type:
                        matches_by_card['meriwest'].append((email_id, best_match['receipt_id'], best_score))
                    elif 'amex' in card_type:
                        matches_by_card['amex'].append((email_id, best_match['receipt_id'], best_score))
                    elif 'chase' in card_type:
                        matches_by_card['chase'].append((email_id, best_match['receipt_id'], best_score))
                    else:
                        matches_by_card['unmatched'].append((email_id, None, 0.0))
                    
                    matched_email_ids.add(email_id)
                else:
                    matches_by_card['unmatched'].append((email_id, None, 0.0))
            else:
                matches_by_card['unmatched'].append((email_id, None, 0.0))
        
        # Display matching results
        print("\n✓ Matching Results:")
        print(f"  - Meriwest matches: {len(matches_by_card['meriwest'])}")
        print(f"  - Amex matches: {len(matches_by_card['amex'])}")
        print(f"  - Chase matches: {len(matches_by_card['chase'])}")
        print(f"  - Unmatched receipts: {len(matches_by_card['unmatched'])}")
        
        # Step 5: Save matches to database
        print("\n" + "=" * 80)
        print("STEP 5: Saving Matches to Database")
        print("=" * 80)
        
        all_matches = []
        for card_type in ['meriwest', 'amex', 'chase']:
            for email_id, receipt_id, score in matches_by_card[card_type]:
                all_matches.append((
                    email_id,
                    receipt_id,
                    score,
                    'fuzzy',  # match_type
                    'high' if score > 0.9 else 'medium',  # confidence_level
                    card_type
                ))
        
        if all_matches:
            db_pool.execute_values(
                """
                INSERT INTO matches (
                    email_id, receipt_id, match_score, match_type,
                    confidence_level, metadata
                )
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                [(m[0], m[1], m[2], m[3], m[4], f'{{"card_type": "{m[5]}"}}') for m in all_matches]
            )
            print(f"✓ Saved {len(all_matches)} matches to database")
        
        # Step 6: Generate reports
        print("\n" + "=" * 80)
        print("STEP 6: Generating Reconciliation Reports")
        print("=" * 80)
        
        # TODO: Generate Excel reports for each card
        # TODO: Upload to Google Drive
        
        print("\n✓ Reconciliation completed successfully!")
        print("\nNext steps:")
        print("1. Review matches in the database")
        print("2. Generate Excel reports")
        print("3. Upload to Google Drive")
        print("4. Label receipts in Gmail")
        
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
