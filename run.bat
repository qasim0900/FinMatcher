@echo off
REM FinMatcher v3.0 - Credit Card Reconciliation Runner
REM This script runs the reconciliation process

echo ================================================================================
echo FinMatcher v3.0 - Starting Credit Card Reconciliation
echo ================================================================================
echo.

REM Set Python path to include finmatcher directory
set PYTHONPATH=%CD%\finmatcher

REM Run the reconciliation script
python run_reconciliation.py

echo.
echo ================================================================================
echo Reconciliation process completed
echo ================================================================================
pause
