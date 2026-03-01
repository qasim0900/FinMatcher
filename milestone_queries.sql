-- ===========================
-- FinMatcher Milestone Verification Queries
-- Direct PostgreSQL Commands
-- ===========================

-- Connect to database first:
-- psql -h localhost -p 5432 -U postgres -d FinMatcher

-- ===========================
-- MILESTONE 1: Meriwest Transactions
-- ===========================

-- Total Meriwest transactions
SELECT 
    COUNT(*) as total_transactions,
    SUM(amount) as total_amount,
    MIN(transaction_date) as earliest_date,
    MAX(transaction_date) as latest_date
FROM receipts
WHERE payment_method = 'Meriwest';

-- Sample Meriwest transactions
SELECT 
    merchant_name,
    amount,
    transaction_date,
    payment_method
FROM receipts
WHERE payment_method = 'Meriwest'
ORDER BY transaction_date DESC
LIMIT 10;

-- ===========================
-- MILESTONE 2: Amex Transactions
-- ===========================

-- Total Amex transactions
SELECT 
    COUNT(*) as total_transactions,
    SUM(amount) as total_amount,
    MIN(transaction_date) as earliest_date,
    MAX(transaction_date) as latest_date
FROM receipts
WHERE payment_method = 'Amex';

-- Sample Amex transactions
SELECT 
    merchant_name,
    amount,
    transaction_date,
    payment_method
FROM receipts
WHERE payment_method = 'Amex'
ORDER BY transaction_date DESC
LIMIT 10;

-- ===========================
-- MILESTONE 3: Chase Transactions
-- ===========================

-- Total Chase transactions
SELECT 
    COUNT(*) as total_transactions,
    SUM(amount) as total_amount,
    MIN(transaction_date) as earliest_date,
    MAX(transaction_date) as latest_date
FROM receipts
WHERE payment_method = 'Chase';

-- Sample Chase transactions
SELECT 
    merchant_name,
    amount,
    transaction_date,
    payment_method
FROM receipts
WHERE payment_method = 'Chase'
ORDER BY transaction_date DESC
LIMIT 10;

-- ===========================
-- MILESTONE 4: Unified Reconciliation
-- ===========================

-- All cards summary
SELECT 
    payment_method,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    MIN(transaction_date) as earliest_date,
    MAX(transaction_date) as latest_date
FROM receipts
GROUP BY payment_method
ORDER BY transaction_count DESC;

-- Email receipts summary
SELECT 
    COUNT(*) as total_emails,
    COUNT(CASE WHEN amount IS NOT NULL THEN 1 END) as emails_with_amount,
    COUNT(CASE WHEN attachment_file_path IS NOT NULL OR attachment_image_path IS NOT NULL THEN 1 END) as emails_with_attachments,
    SUM(amount) as total_email_amount
FROM emails;

-- Matching statistics
SELECT 
    confidence_level,
    COUNT(*) as match_count,
    AVG(match_score) as avg_score,
    MIN(match_score) as min_score,
    MAX(match_score) as max_score
FROM matches
GROUP BY confidence_level
ORDER BY match_count DESC;

-- Overall reconciliation status
SELECT 
    (SELECT COUNT(*) FROM receipts) as total_transactions,
    (SELECT COUNT(*) FROM emails WHERE amount IS NOT NULL) as total_email_receipts,
    (SELECT COUNT(*) FROM matches) as total_matches,
    ROUND(
        (SELECT COUNT(*) FROM matches)::numeric / 
        NULLIF((SELECT COUNT(*) FROM receipts), 0) * 100, 
        2
    ) as match_percentage;

-- ===========================
-- ADDITIONAL VERIFICATION QUERIES
-- ===========================

-- Unmatched transactions by card
SELECT 
    payment_method,
    COUNT(*) as unmatched_count,
    SUM(amount) as unmatched_amount
FROM receipts r
WHERE NOT EXISTS (
    SELECT 1 FROM matches m WHERE m.receipt_id = r.receipt_id
)
GROUP BY payment_method;

-- Matched transactions by card
SELECT 
    r.payment_method,
    COUNT(*) as matched_count,
    SUM(r.amount) as matched_amount,
    AVG(m.match_score) as avg_match_score
FROM receipts r
INNER JOIN matches m ON r.receipt_id = m.receipt_id
GROUP BY r.payment_method;

-- Recent activity (last 20 transactions)
SELECT 
    r.merchant_name,
    r.amount,
    r.transaction_date,
    r.payment_method,
    CASE 
        WHEN EXISTS (SELECT 1 FROM matches m WHERE m.receipt_id = r.receipt_id) 
        THEN '✓ Matched' 
        ELSE '✗ Unmatched' 
    END as status,
    COALESCE(m.confidence_level, 'N/A') as confidence
FROM receipts r
LEFT JOIN matches m ON r.receipt_id = m.receipt_id
ORDER BY r.transaction_date DESC
LIMIT 20;

-- Top merchants by transaction count
SELECT 
    merchant_name,
    payment_method,
    COUNT(*) as transaction_count,
    SUM(amount) as total_spent
FROM receipts
GROUP BY merchant_name, payment_method
ORDER BY transaction_count DESC
LIMIT 15;

-- Transactions by month
SELECT 
    TO_CHAR(transaction_date, 'YYYY-MM') as month,
    payment_method,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount
FROM receipts
GROUP BY TO_CHAR(transaction_date, 'YYYY-MM'), payment_method
ORDER BY month DESC, payment_method;

-- Match quality distribution
SELECT 
    CASE 
        WHEN match_score >= 0.95 THEN 'Excellent (0.95-1.0)'
        WHEN match_score >= 0.85 THEN 'Good (0.85-0.95)'
        WHEN match_score >= 0.75 THEN 'Fair (0.75-0.85)'
        ELSE 'Poor (<0.75)'
    END as match_quality,
    COUNT(*) as count,
    ROUND(AVG(match_score)::numeric, 4) as avg_score
FROM matches
GROUP BY 
    CASE 
        WHEN match_score >= 0.95 THEN 'Excellent (0.95-1.0)'
        WHEN match_score >= 0.85 THEN 'Good (0.85-0.95)'
        WHEN match_score >= 0.75 THEN 'Fair (0.75-0.85)'
        ELSE 'Poor (<0.75)'
    END
ORDER BY avg_score DESC;

-- Database size and table statistics
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- ===========================
-- TROUBLESHOOTING QUERIES
-- ===========================

-- Check for duplicate transactions
SELECT 
    merchant_name,
    amount,
    transaction_date,
    payment_method,
    COUNT(*) as duplicate_count
FROM receipts
GROUP BY merchant_name, amount, transaction_date, payment_method
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Check for transactions with missing data
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN merchant_name IS NULL OR merchant_name = '' THEN 1 END) as missing_merchant,
    COUNT(CASE WHEN amount IS NULL OR amount = 0 THEN 1 END) as missing_amount,
    COUNT(CASE WHEN transaction_date IS NULL THEN 1 END) as missing_date
FROM receipts;

-- Check email processing status
SELECT 
    COUNT(*) as total_emails,
    COUNT(CASE WHEN amount IS NOT NULL THEN 1 END) as processed_emails,
    COUNT(CASE WHEN amount IS NULL THEN 1 END) as unprocessed_emails,
    ROUND(
        COUNT(CASE WHEN amount IS NOT NULL THEN 1 END)::numeric / 
        NULLIF(COUNT(*), 0) * 100, 
        2
    ) as processing_percentage
FROM emails;

-- ===========================
-- END OF QUERIES
-- ===========================