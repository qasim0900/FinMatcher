#!/usr/bin/env python3
"""
Test Core Infrastructure
Tests config, database pool, and logging
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import get_config
from common.db_pool import get_db_pool
from common.logger import get_logger, get_metrics_logger
from common.metrics import MetricsCollector, PerformanceTimer, BatchMetrics


def test_config():
    """Test configuration loading"""
    print("\n" + "=" * 60)
    print("Testing Configuration")
    print("=" * 60)
    
    try:
        config = get_config("test-service")
        
        print("\n✓ Configuration loaded successfully")
        print(f"  Service: {config.service.service_name}")
        print(f"  Worker ID: {config.service.worker_id}")
        print(f"  Database URL: {config.database.url[:50]}...")
        print(f"  IMAP Accounts: {len(config.imap.accounts)}")
        print(f"  Max Threads: {config.service.max_threads}")
        print(f"  Batch Size: {config.service.batch_size}")
        
        # Validate
        config.validate()
        print("\n✓ Configuration validation passed")
        
        return True
    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        return False


def test_database_pool():
    """Test database connection pool"""
    print("\n" + "=" * 60)
    print("Testing Database Pool")
    print("=" * 60)
    
    try:
        config = get_config()
        db_pool = get_db_pool(config.database)
        
        print("\n✓ Database pool initialized")
        
        # Test health check
        if db_pool.health_check():
            print("✓ Database health check passed")
        else:
            print("✗ Database health check failed")
            return False
        
        # Test simple query
        result = db_pool.fetchone("SELECT version()")
        print(f"✓ PostgreSQL version: {result[0][:50]}...")
        
        # Test connection context manager
        with db_pool.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM emails")
            count = cur.fetchone()[0]
            print(f"✓ Emails table count: {count}")
            cur.close()
        
        # Test cursor context manager
        with db_pool.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM jobs")
            count = cur.fetchone()[0]
            print(f"✓ Jobs table count: {count}")
        
        # Test state transition function
        result = db_pool.call_function('is_valid_transition', ('pending', 'downloaded'))
        print(f"✓ State transition function: pending → downloaded = {result}")
        
        print("\n✓ Database pool tests passed")
        return True
        
    except Exception as e:
        print(f"\n✗ Database pool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging():
    """Test logging infrastructure"""
    print("\n" + "=" * 60)
    print("Testing Logging")
    print("=" * 60)
    
    try:
        # Get logger
        logger = get_logger("test-service", level="INFO", json_format=False)
        
        print("\n✓ Logger initialized")
        
        # Test different log levels
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        
        # Get metrics logger
        metrics_logger = get_metrics_logger("test-service")
        
        print("✓ Metrics logger initialized")
        
        # Test metric logging
        metrics_logger.log_metric("test_metric", 123.45, "units")
        metrics_logger.log_latency("test_operation", 50.5)
        metrics_logger.log_throughput("test_operation", 1000, 10.0)
        
        print("✓ Logging tests passed")
        return True
        
    except Exception as e:
        print(f"\n✗ Logging test failed: {e}")
        return False


def test_metrics_collection():
    """Test metrics collection"""
    print("\n" + "=" * 60)
    print("Testing Metrics Collection")
    print("=" * 60)
    
    try:
        config = get_config()
        db_pool = get_db_pool(config.database)
        
        # Create metrics collector
        collector = MetricsCollector(
            db_pool=db_pool,
            service_name="test-service",
            worker_id="test-worker-1"
        )
        
        print("\n✓ Metrics collector initialized")
        
        # Record some metrics
        collector.record_metric("test_metric", 100.0, "units")
        collector.record_latency("test_operation", 25.5)
        collector.record_throughput("test_operation", 500, 5.0)
        
        print("✓ Metrics recorded")
        
        # Test performance timer
        with PerformanceTimer(collector, "test_timer_operation"):
            import time
            time.sleep(0.1)
        
        print("✓ Performance timer tested")
        
        # Test batch metrics
        batch = BatchMetrics(collector, "test_batch")
        batch.increment(100)
        batch.increment_errors(5)
        batch.finish()
        
        print("✓ Batch metrics tested")
        
        # Flush to database
        collector.flush()
        print("✓ Metrics flushed to database")
        
        # Verify metrics in database
        count = db_pool.fetchone(
            "SELECT COUNT(*) FROM metrics WHERE service_name = %s",
            ("test-service",)
        )[0]
        print(f"✓ Metrics in database: {count}")
        
        print("\n✓ Metrics collection tests passed")
        return True
        
    except Exception as e:
        print(f"\n✗ Metrics collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all infrastructure tests"""
    print("\n" + "=" * 60)
    print("FinMatcher v3.0 Infrastructure Tests")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_config),
        ("Database Pool", test_database_pool),
        ("Logging", test_logging),
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
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
