# Bugfix Requirements Document

## Introduction

The FinMatcher project currently has a fragmented setup and migration system with multiple redundant files and conflicting migration approaches. This creates confusion during deployment and makes it difficult to set up the database correctly on Ubuntu servers. The bug manifests as:

- Multiple migration systems that don't work together cohesively
- Redundant test and setup files cluttering the project
- No single unified script to perform complete database setup and migration
- Unclear which files are actually needed vs obsolete

This bugfix will consolidate the migration system, remove unused files, and create a single unified setup script for Ubuntu servers.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a developer tries to set up the database THEN the system has three different migration approaches (migrate.py, schema/migrate.py, complete_setup.sh) that don't integrate with each other

1.2 WHEN looking at the project root THEN the system contains multiple redundant test files (comprehensive_project_test.py, comprehensive_validation_test.py, test_phase1_integration.py) that create confusion about which tests to run

1.3 WHEN looking at setup scripts THEN the system has multiple overlapping scripts (complete_setup.sh, setup_linux.sh, reset_and_migrate.sh, fix_database.sh) with unclear purposes

1.4 WHEN looking at cleanup scripts THEN the system has multiple cleanup files (cleanup.py, cleanup.bat, deep_cleanup.bat) for different platforms without clear organization

1.5 WHEN trying to deploy on Ubuntu server THEN there is no single unified script that handles database creation, table setup, and migration execution in one command

1.6 WHEN migrations need to be run THEN the schema/migrations directory exists but the migration files are not properly integrated with the main migration system

### Expected Behavior (Correct)

2.1 WHEN a developer needs to set up the database THEN the system SHALL provide one unified migration approach that handles all database setup tasks

2.2 WHEN looking at the project root THEN the system SHALL contain only essential test files with clear purposes, removing redundant test scripts

2.3 WHEN looking at setup scripts THEN the system SHALL have one primary setup script for Ubuntu that consolidates all setup functionality

2.4 WHEN looking at cleanup scripts THEN the system SHALL have organized cleanup utilities without redundant platform-specific duplicates

2.5 WHEN deploying on Ubuntu server THEN the system SHALL provide a single Python script that creates the database, sets up tables, runs all migrations, and validates the setup

2.6 WHEN migrations need to be run THEN the system SHALL use the migrate.py system with schema/migrations directory as the single source of truth for all migrations

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the migration system runs existing migration files (001_initial_schema.sql, 002_add_optimization_fields.sql, 003_add_performance_indexes.sql) THEN the system SHALL CONTINUE TO execute them correctly without any schema changes

3.2 WHEN the database schema is created THEN the system SHALL CONTINUE TO create all required tables (processed_emails, transactions, receipts, matches, jobs, reports, audit_log, metrics, schema_migrations) with the same structure

3.3 WHEN the main application (main.py) runs THEN the system SHALL CONTINUE TO function correctly with the consolidated migration system

3.4 WHEN existing configuration files (.env, config.yaml) are used THEN the system SHALL CONTINUE TO read database credentials and settings correctly

3.5 WHEN the finmatcher package modules are imported THEN the system SHALL CONTINUE TO work without any import errors after file cleanup
