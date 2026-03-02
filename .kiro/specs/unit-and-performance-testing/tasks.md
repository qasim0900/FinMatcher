# Implementation Plan: Unit and Performance Testing Framework

## Overview

This implementation plan creates a comprehensive testing framework for the finmatcher application using pytest. The framework includes unit tests for all components, property-based tests using Hypothesis, performance benchmarks with pytest-benchmark, memory profiling, and end-to-end integration tests. The implementation follows a layered approach: first establishing the test infrastructure and fixtures, then building unit tests for each component, adding property-based tests for invariants, implementing performance benchmarks, and finally creating integration tests for complete workflows.

## Tasks

- [x] 1. Set up test framework infrastructure and configuration
  - Create directory structure (tests/unit, tests/property, tests/performance, tests/integration, tests/fixtures, tests/data)
  - Create pytest.ini with test discovery, markers (unit, property, performance, integration, slow), and execution parameters
  - Create .coveragerc for coverage configuration
  - Install dependencies: pytest, pytest-cov, pytest-html, pytest-xdist, pytest-timeout, pytest-benchmark, pytest-mock, hypothesis, memory-profiler, faker
  - Create tests/conftest.py for root pytest configuration
  - _Requirements: 1.1, 9.5, 10.6, 11.1, 11.2_

- [x] 2. Create test fixtures and support infrastructure
  - [x] 2.1 Implement database fixtures
    - Create tests/fixtures/conftest.py with temp_db fixture (function-scoped, isolated database)
    - Create shared_test_db fixture (session-scoped, read-only test data)
    - Implement guaranteed cleanup with finalizers
    - _Requirements: 8.5, 9.3_
  
  - [x] 2.2 Implement file system fixtures
    - Create temp_dir fixture using tempfile.TemporaryDirectory
    - Create sample_email_files fixture that copies test emails to temp directory
    - Create sample_statement_files fixture that copies test statements to temp directory
    - _Requirements: 8.6, 9.4_
  
  - [x] 2.3 Implement mock service fixtures
    - Create tests/fixtures/mock_services.py
    - Implement mock_gmail_service fixture with messages().list() and messages().get() mocked responses
    - Implement mock_drive_service fixture with files().create() and files().list() mocked responses
    - Implement mock_ocr_engine fixture using patch for pytesseract.image_to_string
    - _Requirements: 1.2, 9.1, 9.2, 9.5_
  
  - [x] 2.4 Implement test data generators
    - Create tests/fixtures/generators.py
    - Implement TransactionGenerator class with generate_transaction(), generate_transactions(), and generate_matching_pair() methods
    - Implement ReceiptGenerator class with generate_receipt() and generate_receipts() methods
    - Use Faker library for realistic synthetic data
    - _Requirements: 8.4_
  
  - [x] 2.5 Create sample test data files
    - Create tests/data/emails/ directory with sample .eml files (3-5 samples with various formats)
    - Create tests/data/statements/ directory with sample PDF and Excel files (3-5 samples)
    - Create tests/data/expected_results/ directory with expected match results in JSON format
    - Create tests/data/README.md documenting test data characteristics
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 3. Implement unit tests for core components
  - [x] 3.1 Create unit tests for Email_Fetcher
    - Create tests/unit/core/test_email_fetcher.py
    - Test email retrieval with mock_gmail_service
    - Test email filtering by date range and sender
    - Test attachment handling and extraction
    - Test error handling for API failures
    - _Requirements: 1.2_
  
  - [x] 3.2 Create unit tests for Statement_Parser
    - Create tests/unit/core/test_statement_parser.py
    - Test PDF statement parsing with sample files
    - Test Excel statement parsing with sample files
    - Test transaction field extraction (date, amount, description)
    - Test handling of malformed statements
    - Include round-trip tests: parse → serialize → parse produces equivalent objects
    - _Requirements: 1.3, 1.7_
  
  - [x] 3.3 Create unit tests for OCR_Engine
    - Create tests/unit/core/test_ocr_engine.py
    - Test text extraction from images using mock_ocr_engine
    - Test handling of OCR errors and low-quality images
    - Test extraction of structured data from OCR text
    - _Requirements: 1.4_
  
  - [x] 3.4 Create unit tests for Matcher_Engine
    - Create tests/unit/core/test_matcher_engine.py
    - Test fuzzy matching logic with exact matches (should produce confidence ≥ 0.9)
    - Test confidence scoring with partial matches
    - Test duplicate detection
    - Test edge cases: empty descriptions, large amount differences, date mismatches
    - _Requirements: 1.5_
  
  - [x] 3.5 Create unit tests for Cache_Manager
    - Create tests/unit/database/test_cache_manager.py
    - Test database operations (insert, update, query) using temp_db fixture
    - Test cache hits and cache misses
    - Test data persistence across sessions
    - Test handling of database errors
    - _Requirements: 1.6_

- [ ] 4. Implement unit tests for optimization components
  - [x] 4.1 Create unit tests for Bloom_Filter_Cache
    - Create tests/unit/optimization/test_bloom_filter.py
    - Test item insertion and membership queries
    - Test false positive rate measurement (should be < 1% for typical workloads)
    - Test handling of empty filter and large datasets
    - _Requirements: 2.1_
  
  - [x] 4.2 Create unit tests for Spatial_Indexer
    - Create tests/unit/optimization/test_spatial_indexer.py
    - Test spatial indexing of transactions
    - Test query results for range queries
    - Test boundary conditions and edge cases
    - _Requirements: 2.2_
  
  - [x] 4.3 Create unit tests for Vectorized_Scorer
    - Create tests/unit/optimization/test_vectorized_scorer.py
    - Test batch scoring produces identical results to sequential scoring
    - Test performance improvement over sequential approach
    - Test handling of empty batches and single-item batches
    - _Requirements: 2.3_

- [ ] 5. Implement unit tests for orchestration and reporting
  - [x] 5.1 Create unit tests for Workflow_Manager
    - Create tests/unit/orchestration/test_workflow_manager.py
    - Test workflow state transitions
    - Test error handling and recovery
    - Test checkpoint creation and restoration
    - _Requirements: 3.1_
  
  - [x] 5.2 Create unit tests for Excel_Generator
    - Create tests/unit/reports/test_excel_generator.py
    - Test report structure and sheet creation
    - Test data formatting (dates, amounts, percentages)
    - Test formula correctness
    - Test handling of empty data
    - _Requirements: 3.2_
  
  - [x] 5.3 Create unit tests for Drive_Sync
    - Create tests/unit/reports/test_drive_sync.py
    - Test file upload using mock_drive_service
    - Test authentication handling
    - Test error handling for upload failures
    - _Requirements: 3.3_

- [x] 6. Checkpoint - Ensure all unit tests pass
  - Run pytest -m unit -n auto to execute all unit tests in parallel
  - Verify coverage meets 80% threshold using pytest --cov=finmatcher --cov-report=term-missing
  - Ensure all tests pass, ask the user if questions arise

- [ ] 7. Implement property-based tests for core algorithms
  - [x] 7.1 Configure Hypothesis settings
    - Create tests/property/conftest.py
    - Register profiles: default (100 examples), ci (500 examples), debug (10 examples, verbose)
    - Load profile from HYPOTHESIS_PROFILE environment variable
    - _Requirements: 4.6_
  
  - [x] 7.2 Write property test for confidence score bounds
    - Create tests/property/test_matching_properties.py
    - **Property 1: Confidence Score Bounds Invariant**
    - **Validates: Requirements 4.1**
    - Use @given with Hypothesis strategies for Transaction and Receipt
    - Assert 0.0 ≤ confidence_score ≤ 1.0 for all generated pairs
  
  - [ ] 7.3 Write property test for date parsing validity
    - Add to tests/property/test_parsing_properties.py
    - **Property 2: Date Parsing Validity**
    - **Validates: Requirements 4.2**
    - Use @given with text strategy for date strings
    - Assert parsed dates represent valid calendar dates
  
  - [ ] 7.4 Write property test for amount precision preservation
    - Add to tests/property/test_parsing_properties.py
    - **Property 3: Amount Precision Preservation**
    - **Validates: Requirements 4.3**
    - Use @given with text strategy for amount strings with varying decimal places
    - Assert extracted amounts preserve at least N decimal places
  
  - [ ] 7.5 Write property test for identity matching perfection
    - Add to tests/property/test_matching_properties.py
    - **Property 4: Identity Matching Perfection**
    - **Validates: Requirements 4.4**
    - Use @given with text strategy for non-empty strings
    - Assert fuzzy matching a string to itself produces confidence = 1.0
  
  - [ ] 7.6 Write property test for bloom filter no false negatives
    - Create tests/property/test_bloom_filter_properties.py
    - **Property 5: Bloom Filter No False Negatives**
    - **Validates: Requirements 4.5**
    - Use @given with lists strategy for items to add
    - Assert all added items are detected as present

- [ ] 8. Implement performance benchmarks for critical paths
  - [ ] 8.1 Create benchmark infrastructure
    - Create tests/performance/baseline_model.py with PerformanceBaseline class
    - Implement save(), load(), and compare() methods for baseline management
    - Create tests/performance/baselines/ directory for storing baseline metrics
    - _Requirements: 5.1, 12.1, 12.2_
  
  - [ ] 8.2 Create email processing benchmark
    - Create tests/performance/test_email_processing_benchmark.py
    - Benchmark email fetching and parsing throughput (emails per second)
    - Use pytest-benchmark with @pytest.mark.performance marker
    - _Requirements: 5.2_
  
  - [ ] 8.3 Create statement parsing benchmark
    - Create tests/performance/test_parsing_benchmark.py
    - Benchmark PDF parsing time for files of varying sizes (small, medium, large)
    - Benchmark Excel parsing time for files of varying sizes
    - _Requirements: 5.3_
  
  - [ ] 8.4 Create OCR processing benchmark
    - Create tests/performance/test_ocr_benchmark.py
    - Benchmark OCR processing time for images of varying sizes and quality
    - Measure OCR accuracy metrics
    - _Requirements: 5.4_
  
  - [ ] 8.5 Create transaction matching benchmark
    - Create tests/performance/test_matching_benchmark.py
    - Benchmark matching time for datasets of 100, 1000, and 10000 transactions
    - Measure throughput (matches per second)
    - _Requirements: 5.5_
  
  - [ ] 8.6 Implement performance regression detection
    - Create tests/performance/check_regressions.py script
    - Compare current benchmark results against baseline
    - Fail if performance degrades by more than 20%
    - Generate performance comparison reports
    - _Requirements: 5.6, 12.3, 12.4_

- [ ] 9. Implement memory profiling tests
  - [ ] 9.1 Create memory profiling infrastructure
    - Create tests/performance/test_memory_profiling.py
    - Import memory_profiler for memory usage tracking
    - _Requirements: 6.5_
  
  - [ ] 9.2 Write memory stability test for repeated operations
    - **Property 6: Memory Stability Under Repeated Operations**
    - **Validates: Requirements 6.4**
    - Measure memory at iteration 10 (baseline) and iteration 100 (final)
    - Assert memory growth ≤ 10%
  
  - [ ] 9.3 Write memory limit test for 1000 emails
    - Test that processing 1000 emails stays below 2GB memory usage
    - _Requirements: 6.2_
  
  - [ ] 9.4 Write memory limit test for statement parsing
    - Test that parsing a single statement stays below 500MB memory usage
    - _Requirements: 6.3_
  
  - [ ] 9.5 Write memory profiling test for peak usage tracking
    - Measure peak memory usage for each component (email fetcher, parser, matcher, OCR)
    - Generate memory usage reports
    - _Requirements: 6.1_

- [ ] 10. Checkpoint - Ensure all performance tests pass
  - Run pytest -m performance --benchmark-only to execute benchmarks
  - Verify no performance regressions detected
  - Ensure all tests pass, ask the user if questions arise

- [ ] 11. Implement end-to-end integration tests
  - [ ] 11.1 Create full reconciliation flow test
    - Create tests/integration/test_full_reconciliation_flow.py
    - Test complete workflow: email fetching → statement parsing → transaction matching → report generation
    - Verify emails processed, statements parsed, matches found, and report generated
    - Verify report file exists and contains expected data
    - Verify confidence scores are within valid range [0.0, 1.0]
    - _Requirements: 7.1, 7.2, 7.6_
  
  - [ ] 11.2 Create incremental processing flow test
    - Create tests/integration/test_incremental_processing_flow.py
    - **Property 7: Incremental Processing Idempotence**
    - **Validates: Requirements 7.3**
    - Test first run processes initial emails
    - Test second run with no new emails processes zero emails
    - Assert cache is utilized correctly
  
  - [ ] 11.3 Create error recovery flow test
    - Create tests/integration/test_error_recovery_flow.py
    - **Property 8: Checkpoint Recovery Completeness**
    - **Validates: Requirements 7.4**
    - Simulate workflow interruption at 50% progress
    - Resume from checkpoint and verify completion
    - Compare results with uninterrupted workflow (should be equivalent)

- [ ] 12. Implement test reporting and coverage analysis
  - [ ] 12.1 Configure HTML coverage reporting
    - Update pytest.ini to generate HTML coverage reports
    - Configure coverage report to show missing lines and untested code paths
    - _Requirements: 10.1, 10.4_
  
  - [ ] 12.2 Configure HTML test reporting
    - Add pytest-html plugin configuration
    - Generate test reports showing pass/fail status and execution time
    - _Requirements: 10.2_
  
  - [ ] 12.3 Implement coverage threshold enforcement
    - Configure pytest to fail if coverage falls below 80%
    - Highlight modules with coverage below 80% in reports
    - _Requirements: 10.3, 10.5_
  
  - [ ] 12.4 Create test runner utility
    - Create tests/runner.py with TestRunner class
    - Implement run_unit_tests(), run_property_tests(), run_performance_tests(), run_integration_tests(), and run_all_tests() methods
    - Support parallel execution with pytest-xdist
    - _Requirements: 11.1_

- [ ] 13. Configure CI/CD integration
  - [ ] 13.1 Create GitHub Actions workflow
    - Create .github/workflows/test.yml
    - Define jobs: unit-tests, property-tests, performance-tests, integration-tests, coverage-report
    - Configure parallel test execution with pytest-xdist
    - _Requirements: 11.1_
  
  - [ ] 13.2 Configure JUnit XML output for CI
    - Add --junitxml parameter to pytest commands in CI workflow
    - Upload test results as artifacts
    - _Requirements: 11.3_
  
  - [ ] 13.3 Configure test markers for CI
    - Use pytest markers to separate fast unit tests from slow integration tests
    - Configure CI to run fast tests first, then slow tests
    - _Requirements: 11.4_
  
  - [ ] 13.4 Configure timeout protection
    - Add pytest-timeout configuration to prevent hanging tests
    - Set default timeout to 300 seconds (5 minutes)
    - Allow individual tests to override timeout
    - _Requirements: 11.2_
  
  - [ ] 13.5 Configure coverage upload to Codecov
    - Add Codecov action to CI workflow
    - Upload coverage.xml after test execution
    - _Requirements: 10.1_

- [ ] 14. Final checkpoint - Ensure complete test suite passes
  - Run pytest to execute all tests (unit, property, performance, integration)
  - Verify overall coverage meets 80% threshold
  - Verify all performance benchmarks pass without regressions
  - Verify all integration tests pass
  - Generate final test report and coverage report
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional property-based and memory profiling tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- Performance tests establish baselines and detect regressions
- Integration tests verify end-to-end workflows with realistic data
- The framework uses Python with pytest as the core test runner
- All external dependencies (Gmail API, Drive API) are mocked for fast, isolated testing
- Tests are organized by type (unit, property, performance, integration) for selective execution
- CI/CD integration enables automated testing on every commit
