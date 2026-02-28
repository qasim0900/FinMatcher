#!/usr/bin/env python3
"""
FinMatcher v3.0 Schema Test Script
Tests database functions and state transitions
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    db_url = os.getenv('DATABASE_URL').strip('"')
    return psycopg2.connect(db_url)

def test_state_transitions():
    """Test state transition validation"""
    print("\n" + "=" * 60)
    print("Testing State Transition Functions")
    print("=" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Test valid transitions
    valid_transitions = [
        ('pending', 'downloaded'),
        ('downloaded', 'matched'),
        ('matched', 'report_generated'),
        ('report_generated', 'uploaded'),
        ('failed', 'pending'),
        ('failed', 'dead_letter'),
    ]
    
    print("\n✓ Testing valid transitions:")
    for old_status, new_status in valid_transitions:
        cur.execute("SELECT is_valid_transition(%s, %s)", (old_status, new_status))
        result = cur.fetchone()[0]
        status = "✓" if result else "✗"
        print(f"  {status} {old_status} → {new_status}: {result}")
    
    # Test invalid transitions
    invalid_transitions = [
        ('pending', 'matched'),
        ('downloaded', 'uploaded'),
        ('matched', 'downloaded'),
        ('uploaded', 'pending'),
    ]
    
    print("\n✓ Testing invalid transitions (should be False):")
    for old_status, new_status in invalid_transitions:
        cur.execute("SELECT is_valid_transition(%s, %s)", (old_status, new_status))
        result = cur.fetchone()[0]
        status = "✓" if not result else "✗"
        print(f"  {status} {old_status} → {new_status}: {result}")
    
    cur.close()
    conn.close()

def test_job_workflow():
    """Test complete job workflow"""
    print("\n" + "=" * 60)
    print("Testing Job Workflow")
    print("=" * 60)
    
    conn = get_db_connection()
    conn.autocommit = False
    cur = conn.cursor()
    
    try:
        # Create test email
        print("\n✓ Creating test email...")
        cur.execute("""
            INSERT INTO emails (
                message_id, account_email, subject, sender, 
                received_date, amount, merchant_name, transaction_date
            )
            VALUES (
                'test-' || NOW()::TEXT, 
                'test@example.com',
                'Test Transaction',
                'merchant@example.com',
                NOW(),
                99.99,
                'Test Merchant',
                NOW()
            )
            RETURNING email_id
        """)
        email_id = cur.fetchone()[0]
        print(f"  Created email_id: {email_id}")
        
        # Create test job
        print("\n✓ Creating test job...")
        cur.execute("""
            INSERT INTO jobs (email_id, status, stage)
            VALUES (%s, 'pending', 'ingestion')
            RETURNING job_id
        """, (email_id,))
        job_id = cur.fetchone()[0]
        print(f"  Created job_id: {job_id}")
        
        # Test job status update
        print("\n✓ Testing job status updates...")
        transitions = [
            ('downloaded', 'worker-1'),
            ('matched', 'worker-2'),
            ('report_generated', 'worker-3'),
            ('uploaded', 'worker-4'),
        ]
        
        for new_status, worker_id in transitions:
            cur.execute("""
                SELECT update_job_status(%s, %s, %s, NULL)
            """, (job_id, new_status, worker_id))
            result = cur.fetchone()[0]
            print(f"  ✓ Updated to '{new_status}' by {worker_id}: {result}")
        
        # Verify audit log
        print("\n✓ Verifying audit log...")
        cur.execute("""
            SELECT event_type, old_status, new_status, worker_id
            FROM audit_log
            WHERE job_id = %s
            ORDER BY created_at
        """, (job_id,))
        
        audit_entries = cur.fetchall()
        print(f"  Found {len(audit_entries)} audit log entries:")
        for entry in audit_entries:
            print(f"    - {entry[0]}: {entry[1]} → {entry[2]} (worker: {entry[3]})")
        
        # Test get_next_jobs function
        print("\n✓ Testing get_next_jobs function...")
        
        # Create another test job
        cur.execute("""
            INSERT INTO emails (message_id, account_email, subject, received_date)
            VALUES ('test-2-' || NOW()::TEXT, 'test@example.com', 'Test 2', NOW())
            RETURNING email_id
        """)
        email_id_2 = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO jobs (email_id, status, stage)
            VALUES (%s, 'downloaded', 'matching')
            RETURNING job_id
        """, (email_id_2,))
        job_id_2 = cur.fetchone()[0]
        
        # Poll for jobs
        cur.execute("""
            SELECT * FROM get_next_jobs('matching', 'downloaded', 'test-worker', 10)
        """)
        jobs = cur.fetchall()
        print(f"  Polled {len(jobs)} jobs for matching stage:")
        for job in jobs:
            print(f"    - job_id: {job[0]}, email_id: {job[1]}")
        
        # Rollback test data
        conn.rollback()
        print("\n✓ Test data rolled back (not persisted)")
        
        cur.close()
        conn.close()
        
        print("\n✓ Job workflow test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error during job workflow test: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def test_metrics_collection():
    """Test metrics collection"""
    print("\n" + "=" * 60)
    print("Testing Metrics Collection")
    print("=" * 60)
    
    conn = get_db_connection()
    conn.autocommit = False
    cur = conn.cursor()
    
    try:
        # Insert test metrics
        print("\n✓ Inserting test metrics...")
        test_metrics = [
            ('ingestion', 'emails_per_second', 150.5, 'emails/sec', 'worker-1'),
            ('matching', 'matches_per_second', 2500.0, 'matches/sec', 'worker-2'),
            ('reporting', 'report_generation_time', 3.2, 'seconds', 'worker-3'),
        ]
        
        for service, metric, value, unit, worker in test_metrics:
            cur.execute("""
                INSERT INTO metrics (service_name, metric_name, metric_value, metric_unit, worker_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (service, metric, value, unit, worker))
            print(f"  ✓ {service}.{metric}: {value} {unit}")
        
        # Query metrics
        print("\n✓ Querying metrics...")
        cur.execute("""
            SELECT service_name, metric_name, metric_value, metric_unit
            FROM metrics
            WHERE recorded_at > NOW() - INTERVAL '1 minute'
            ORDER BY recorded_at DESC
        """)
        
        metrics = cur.fetchall()
        print(f"  Found {len(metrics)} recent metrics")
        
        # Rollback test data
        conn.rollback()
        print("\n✓ Test data rolled back")
        
        cur.close()
        conn.close()
        
        print("\n✓ Metrics collection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error during metrics test: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def run_all_tests():
    """Run all schema tests"""
    print("\n" + "=" * 60)
    print("FinMatcher v3.0 Schema Tests")
    print("=" * 60)
    
    tests = [
        ("State Transitions", test_state_transitions),
        ("Job Workflow", test_job_workflow),
        ("Metrics Collection", test_metrics_collection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        exit(1)
