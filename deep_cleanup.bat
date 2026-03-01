@echo off
REM FinMatcher - Deep Cleanup Script
REM Removes EVERYTHING including database records (USE WITH CAUTION!)

echo ========================================
echo FinMatcher - DEEP CLEANUP (DANGEROUS!)
echo ========================================
echo.
echo WARNING: This will delete:
echo   - All cache and logs
echo   - All temporary files
echo   - All reports and outputs
echo   - PostgreSQL database records
echo   - SQLite database
echo   - Downloaded attachments
echo.
echo Configuration files (.env, config.yaml) will be preserved.
echo.

set /p confirm="Are you sure you want to continue? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo Cleanup cancelled.
    pause
    exit /b 0
)

echo.
echo Starting deep cleanup...
echo.

REM Run regular cleanup first
call cleanup.bat

echo.
echo [EXTRA] Cleaning PostgreSQL database...
psql -U postgres -d FinMatcher -h localhost -c "TRUNCATE TABLE processed_emails, transactions, receipts, matches, matching_statistics CASCADE;" 2>nul
if %errorlevel% equ 0 (
    echo     ✓ PostgreSQL database tables truncated
) else (
    echo     ⚠ Could not truncate PostgreSQL tables (may not exist or connection failed)
)

echo.
echo [EXTRA] Removing SQLite database...
if exist "finmatcher.db" (
    del /q finmatcher.db
    echo     ✓ SQLite database removed
) else (
    echo     ℹ No SQLite database found
)

echo.
echo [EXTRA] Cleaning downloaded attachments...
if exist "attachments" (
    del /q attachments\*.* 2>nul
    echo     ✓ Downloaded attachments cleaned
) else (
    echo     ℹ No attachments directory found
)

echo.
echo [EXTRA] Cleaning Gmail token...
if exist "finmatcher\auth_files\token.json" (
    del /q finmatcher\auth_files\token.json
    echo     ✓ Gmail token removed (will need to re-authenticate)
) else (
    echo     ℹ No Gmail token found
)

echo.
echo ========================================
echo ✓ Deep Cleanup Complete!
echo ========================================
echo.
echo All data has been removed. The system is now in a fresh state.
echo You will need to:
echo   1. Re-authenticate with Gmail
echo   2. Re-run database migrations if needed
echo   3. Process emails from scratch
echo.
pause
