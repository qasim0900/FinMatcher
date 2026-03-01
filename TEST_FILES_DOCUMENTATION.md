# Test Files Documentation

This document lists all active test files in the FinMatcher project and their purposes.

## Active Test Files

### Root Level Test Files

1. **test_bug_condition_exploration.py**
   - Purpose: Bug condition exploration tests for the project cleanup and migration fix
   - Type: Property-based testing
   - Validates: Multiple migration systems fragmentation bug
   - Status: Active - Part of bugfix spec validation

2. **test_preservation_properties.py**
   - Purpose: Preservation property tests to ensure existing functionality remains intact
   - Type: Property-based testing
   - Validates: Migration execution, application functionality, configuration reading, module imports
   - Status: Active - Part of bugfix spec validation

3. **test_receipts.py**
   - Purpose: Tests for receipt processing functionality
   - Type: Unit tests
   - Validates: Receipt parsing, validation, and storage
   - Status: Active - Core functionality testing

4. **test_fast_processor.py**
   - Purpose: Tests for the optimized fast email processor
   - Type: Unit/Integration tests
   - Validates: Email processing performance and correctness
   - Status: Active - Performance validation

### Service-Level Test Files

5. **services/common/test_infrastructure.py**
   - Purpose: Infrastructure testing utilities and helpers
   - Type: Test infrastructure
   - Validates: Common testing patterns and utilities
   - Status: Active - Testing support

6. **schema/test_schema.py**
   - Purpose: Database schema validation tests
   - Type: Schema tests
   - Validates: Database table structures and migrations
   - Status: Active - Database validation

## Removed Test Files (Cleanup)

The following test files were removed as part of the project cleanup (Task 3.3):

1. **comprehensive_project_test.py** (REMOVED)
   - Reason: Redundant - from initial testing phase, functionality covered by newer test files
   - Replaced by: test_preservation_properties.py, test_receipts.py, test_fast_processor.py

2. **comprehensive_validation_test.py** (REMOVED)
   - Reason: Redundant - from validation phase, performance testing now handled by test_fast_processor.py
   - Replaced by: test_fast_processor.py

3. **test_phase1_integration.py** (REMOVED)
   - Reason: Obsolete - Phase 1 is complete, integration tests now in active test files
   - Replaced by: Current integration tests in test_fast_processor.py

## Running Tests

### Run All Tests
```bash
python -m pytest
```

### Run Specific Test File
```bash
python -m pytest test_receipts.py
python -m pytest test_fast_processor.py
```

### Run Property-Based Tests
```bash
python -m pytest test_bug_condition_exploration.py
python -m pytest test_preservation_properties.py
```

## Test Organization

- **Root level**: Main functional and property-based tests
- **services/**: Service-specific tests
- **schema/**: Database schema tests

All test files follow the naming convention `test_*.py` for automatic discovery by pytest.

---

**Last Updated:** 2024 (Task 3.3 - Project Cleanup)
**Status:** Active test suite maintained and documented
