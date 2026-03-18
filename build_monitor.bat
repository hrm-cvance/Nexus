@echo off
REM ============================================================
REM Nexus Monitor Build Script
REM Produces: dist\NexusMonitor.exe
REM ============================================================

echo.
echo ========================================
echo   Nexus Monitor Build
echo ========================================
echo.

REM Step 1: Pre-flight checks
echo [1/4] Pre-flight checks...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not installed. Run: pip install pyinstaller
    exit /b 1
)

REM Step 2: Clean previous monitor build
echo [2/4] Cleaning previous build...
if exist "dist\NexusMonitor.exe" del "dist\NexusMonitor.exe"

REM Step 3: Build
echo [3/4] Building NexusMonitor.exe...
pyinstaller ^
    --onefile ^
    --name NexusMonitor ^
    --console ^
    --add-data "config\app_config.json;config" ^
    --add-data "services;services" ^
    --add-data "utils;utils" ^
    --add-data "monitor;monitor" ^
    --hidden-import msal ^
    --hidden-import pikepdf ^
    --hidden-import azure.keyvault.secrets ^
    --hidden-import azure.identity ^
    --hidden-import azure.core ^
    monitor.py

if not exist "dist\NexusMonitor.exe" (
    echo ERROR: Build failed - NexusMonitor.exe not found
    exit /b 1
)

REM Step 4: Verify
echo [4/4] Verifying build...
echo.
echo Build successful!
echo   Output: dist\NexusMonitor.exe
for %%I in ("dist\NexusMonitor.exe") do echo   Size: %%~zI bytes
echo.
echo Deploy:
echo   1. Copy NexusMonitor.exe to server
echo   2. Place monitor_config.json alongside the exe
echo   3. Install as service: nssm install NexusMonitor "C:\path\to\NexusMonitor.exe"
echo.
