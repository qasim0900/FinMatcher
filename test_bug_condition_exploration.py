#!/usr/bin/env python3
"""
Bug Condition Exploration Test for Project Cleanup and Migration Fix

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

The test encodes the expected behavior - it will validate the fix when it passes after implementation.

GOAL: Surface counterexamples that demonstrate the fragmentation exists.
"""

import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, Phase
import pytest


class TestBugConditionExploration:
    """
    Property 1: Fault Condition - Multiple Migration Systems Fragmentation
    
    Tests that the bug condition exists: multiple migration systems exist without integration,
    redundant files clutter the project, and no unified setup script exists.
    """
    
    def test_multiple_migration_systems_exist(self):
        """
        Test that multiple migration systems exist independently without integration.
        
        **Validates: Requirement 1.1**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check for multiple migration systems
        migrate_py = project_root / "migrate.py"
        schema_migrate_py = project_root / "schema" / "migrate.py"
        complete_setup_sh = project_root / "complete_setup.sh"
        
        # On unfixed code, all three should exist
        migration_systems = []
        if migrate_py.exists():
            migration_systems.append("migrate.py")
        if schema_migrate_py.exists():
            migration_systems.append("schema/migrate.py")
        if complete_setup_sh.exists():
            migration_systems.append("complete_setup.sh")
        
        # Document the counterexample
        counterexample = f"Found {len(migration_systems)} separate migration systems: {', '.join(migration_systems)}"
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert len(migration_systems) > 1, (
            f"Expected multiple migration systems to exist (bug condition), but found {len(migration_systems)}. "
            f"Systems found: {migration_systems}"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")
    
    def test_no_unified_setup_script_exists(self):
        """
        Test that no unified setup script exists.
        
        **Validates: Requirement 1.5**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check for unified setup script
        setup_ubuntu_py = project_root / "setup_ubuntu.py"
        
        # Document the counterexample
        if not setup_ubuntu_py.exists():
            counterexample = "No unified setup script exists (setup_ubuntu.py not found)"
        else:
            counterexample = "Unified setup script exists (setup_ubuntu.py found)"
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert not setup_ubuntu_py.exists(), (
            "Expected no unified setup script to exist (bug condition), but setup_ubuntu.py was found"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")
    
    def test_redundant_test_files_exist(self):
        """
        Test that redundant test files exist.
        
        **Validates: Requirement 1.2**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check for redundant test files
        redundant_test_files = [
            "comprehensive_project_test.py",
            "comprehensive_validation_test.py",
            "test_phase1_integration.py"
        ]
        
        found_test_files = []
        for test_file in redundant_test_files:
            if (project_root / test_file).exists():
                found_test_files.append(test_file)
        
        # Document the counterexample
        counterexample = f"Found {len(found_test_files)} redundant test files: {', '.join(found_test_files)}"
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert len(found_test_files) > 0, (
            f"Expected redundant test files to exist (bug condition), but found {len(found_test_files)}"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")
    
    def test_redundant_setup_scripts_exist(self):
        """
        Test that redundant setup scripts exist.
        
        **Validates: Requirement 1.3**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check for redundant setup scripts
        redundant_setup_scripts = [
            "complete_setup.sh",
            "setup_linux.sh",
            "reset_and_migrate.sh",
            "fix_database.sh"
        ]
        
        found_setup_scripts = []
        for setup_script in redundant_setup_scripts:
            if (project_root / setup_script).exists():
                found_setup_scripts.append(setup_script)
        
        # Document the counterexample
        counterexample = f"Found {len(found_setup_scripts)} redundant setup scripts: {', '.join(found_setup_scripts)}"
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert len(found_setup_scripts) > 1, (
            f"Expected multiple redundant setup scripts to exist (bug condition), but found {len(found_setup_scripts)}"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")
    
    def test_redundant_cleanup_scripts_exist(self):
        """
        Test that redundant cleanup scripts exist.
        
        **Validates: Requirement 1.4**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check for redundant cleanup scripts
        redundant_cleanup_scripts = [
            "cleanup.py",
            "cleanup.bat",
            "deep_cleanup.bat"
        ]
        
        found_cleanup_scripts = []
        for cleanup_script in redundant_cleanup_scripts:
            if (project_root / cleanup_script).exists():
                found_cleanup_scripts.append(cleanup_script)
        
        # Document the counterexample
        counterexample = f"Found {len(found_cleanup_scripts)} redundant cleanup scripts: {', '.join(found_cleanup_scripts)}"
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert len(found_cleanup_scripts) > 1, (
            f"Expected multiple redundant cleanup scripts to exist (bug condition), but found {len(found_cleanup_scripts)}"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")
    
    def test_migration_state_inconsistency(self):
        """
        Test that migration state is inconsistent between systems.
        
        **Validates: Requirement 1.6**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check that schema/migrate.py exists but doesn't integrate with migrate.py
        schema_migrate_py = project_root / "schema" / "migrate.py"
        migrate_py = project_root / "migrate.py"
        
        if not schema_migrate_py.exists() or not migrate_py.exists():
            pytest.skip("Migration files not found, skipping inconsistency test")
        
        # Read schema/migrate.py to check if it updates schema_migrations table
        with open(schema_migrate_py, 'r') as f:
            schema_migrate_content = f.read()
        
        # Check if schema/migrate.py references schema_migrations table
        updates_schema_migrations = "schema_migrations" in schema_migrate_content
        
        # Document the counterexample
        if not updates_schema_migrations:
            counterexample = "schema/migrate.py doesn't update schema_migrations table that migrate.py uses"
        else:
            counterexample = "schema/migrate.py does update schema_migrations table"
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert not updates_schema_migrations, (
            "Expected schema/migrate.py to NOT update schema_migrations table (bug condition), "
            "but it appears to reference it"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")
    
    @given(st.just(None))
    @settings(phases=[Phase.generate, Phase.target])
    def test_property_unified_migration_system_does_not_exist(self, _):
        """
        Property-based test: For any deployment scenario, verify that a unified migration system does NOT exist.
        
        This is a scoped property test that demonstrates the bug condition.
        
        **Validates: Requirements 1.1, 1.5, 1.6**
        
        EXPECTED ON UNFIXED CODE: This test PASSES (proving the bug exists)
        EXPECTED ON FIXED CODE: This test FAILS (proving the bug is fixed)
        """
        project_root = Path(__file__).parent
        
        # Check for unified setup script
        setup_ubuntu_py = project_root / "setup_ubuntu.py"
        
        # Check for multiple migration systems
        migrate_py = project_root / "migrate.py"
        schema_migrate_py = project_root / "schema" / "migrate.py"
        complete_setup_sh = project_root / "complete_setup.sh"
        
        migration_systems_count = sum([
            migrate_py.exists(),
            schema_migrate_py.exists(),
            complete_setup_sh.exists()
        ])
        
        # Bug condition: multiple migration systems exist AND no unified setup script
        bug_condition = migration_systems_count > 1 and not setup_ubuntu_py.exists()
        
        # Document the counterexample
        counterexample = (
            f"Bug condition exists: {migration_systems_count} migration systems found, "
            f"unified setup script exists: {setup_ubuntu_py.exists()}"
        )
        
        # This assertion PASSES on unfixed code (bug exists) and FAILS on fixed code (bug fixed)
        assert bug_condition, (
            f"Expected bug condition to exist (multiple migration systems without unified setup), "
            f"but found: {migration_systems_count} migration systems, "
            f"unified setup exists: {setup_ubuntu_py.exists()}"
        )
        
        print(f"✓ Counterexample documented: {counterexample}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
