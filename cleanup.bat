@echo off
REM FinMatcher - Complete Cleanup Script
REM Removes all cache, logs, temporary files, and Python cache

echo ========================================
echo FinMatcher - Complete Cleanup
echo ========================================
echo.

REM Check if running from project directory
if not exist "finmatcher" (
    echo ERROR: Please run this script from the FinMatcher project root directory
    pause
    exit /b 1
)

echo [1/8] Cleaning Python cache files...
REM Remove __pycache__ directories
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
REM Remove .pyc files
del /s /q *.pyc 2>nul
REM Remove .pyo files
del /s /q *.pyo 2>nul
echo     ✓ Python cache cleaned

echo.
echo [2/8] Cleaning logs directory...
if exist "logs" (
    del /q logs\*.log 2>nul
    echo     ✓ Logs cleaned
) else (
    echo     ℹ No logs directory found
)

echo.
echo [3/8] Cleaning temporary attachments...
if exist "temp_attachments" (
    del /q temp_attachments\*.* 2>nul
    echo     ✓ Temporary attachments cleaned
) else (
    echo     ℹ No temp_attachments directory found
)

echo.
echo [4/8] Cleaning output directory...
if exist "output" (
    del /q output\*.* 2>nul
    echo     ✓ Output directory cleaned
) else (
    echo     ℹ No output directory found
)

echo.
echo [5/8] Cleaning reports directory...
if exist "reports" (
    del /q reports\*.xlsx 2>nul
    del /q reports\*.xls 2>nul
    del /q reports\*.csv 2>nul
    echo     ✓ Reports cleaned
) else (
    echo     ℹ No reports directory found
)

echo.
echo [6/8] Cleaning .kiro cache...
if exist ".kiro\cache" (
    rd /s /q .kiro\cache 2>nul
    mkdir .kiro\cache
    echo     ✓ Kiro cache cleaned
) else (
    echo     ℹ No .kiro cache found
)

echo.
echo [7/8] Cleaning pytest cache...
if exist ".pytest_cache" (
    rd /s /q .pytest_cache
    echo     ✓ Pytest cache cleaned
) else (
    echo     ℹ No pytest cache found
)

echo.
echo [8/8] Cleaning coverage reports...
if exist "htmlcov" (
    rd /s /q htmlcov
    echo     ✓ Coverage reports cleaned
) else (
    echo     ℹ No coverage reports found
)
if exist ".coverage" (
    del /q .coverage
)

echo.
echo ========================================
echo ✓ Cleanup Complete!
echo ========================================
echo.
echo Cleaned:
echo   - Python cache (__pycache__, .pyc, .pyo)
echo   - Log files (logs/*.log)
echo   - Temporary attachments (temp_attachments/*)
echo   - Output files (output/*)
echo   - Excel reports (reports/*.xlsx)
echo   - Kiro cache (.kiro/cache)
echo   - Test cache (.pytest_cache)
echo   - Coverage reports (htmlcov, .coverage)
echo.
echo Note: Database records and configuration files are preserved.
echo.
pause
