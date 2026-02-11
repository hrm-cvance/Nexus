@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo  Nexus Build Script v1.0
echo  Highland Mortgage Services
echo ==========================================
echo.

REM ── Configuration ──────────────────────────
set APP_NAME=Nexus
set APP_VERSION=1.0.0
set ENTRY_POINT=main.py
set DIST_DIR=dist
set BUILD_DIR=build

REM ── Pre-flight checks ─────────────────────
echo [1/5] Running pre-flight checks...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python 3.8+ and try again.
    exit /b 1
)

pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        exit /b 1
    )
)

REM ── Clean previous builds ──────────────────
echo [2/5] Cleaning previous builds...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%APP_NAME%.spec" del "%APP_NAME%.spec"

REM ── Resolve customtkinter path ─────────────
echo [3/5] Resolving package paths...
for /f "delims=" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

if "!CTK_PATH!"=="" (
    echo [ERROR] customtkinter not found. Run: pip install customtkinter
    exit /b 1
)
echo        customtkinter: !CTK_PATH!

REM ── Build executable ───────────────────────
echo [4/5] Building %APP_NAME% v%APP_VERSION%...
echo        This may take several minutes...
echo.

pyinstaller --onefile ^
    --name "%APP_NAME%" ^
    --windowed ^
    --add-data "config;config" ^
    --add-data "vendors;vendors" ^
    --add-data "!CTK_PATH!;customtkinter" ^
    --collect-all playwright ^
    --hidden-import "msal" ^
    --hidden-import "msal.application" ^
    --hidden-import "msal.token_cache" ^
    --hidden-import "azure.keyvault.secrets" ^
    --hidden-import "azure.identity" ^
    --hidden-import "azure.identity._credentials" ^
    --hidden-import "azure.core" ^
    --hidden-import "azure.core.pipeline" ^
    --hidden-import "reportlab" ^
    --hidden-import "reportlab.lib" ^
    --hidden-import "reportlab.platypus" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "jsonschema" ^
    --hidden-import "colorlog" ^
    --hidden-import "dateutil" ^
    --hidden-import "anthropic" ^
    --hidden-import "automation.vendors.accountchek" ^
    --hidden-import "automation.vendors.bankvod" ^
    --hidden-import "automation.vendors.clearcapital" ^
    --hidden-import "automation.vendors.dataverify" ^
    --hidden-import "automation.vendors.certifiedcredit" ^
    --hidden-import "automation.vendors.partnerscredit" ^
    --hidden-import "automation.vendors.theworknumber" ^
    --hidden-import "automation.vendors.mmi" ^
    --hidden-import "automation.vendors.experience" ^
    --exclude-module "pytest" ^
    --exclude-module "_pytest" ^
    --noconfirm ^
    "%ENTRY_POINT%"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check output above for details.
    exit /b 1
)

REM ── Post-build summary ─────────────────────
echo.
echo [5/5] Build complete!
echo.

if exist "%DIST_DIR%\%APP_NAME%.exe" (
    for %%A in ("%DIST_DIR%\%APP_NAME%.exe") do (
        set FILE_SIZE=%%~zA
        set /a FILE_SIZE_MB=!FILE_SIZE! / 1048576
        echo  Output:  %DIST_DIR%\%APP_NAME%.exe
        echo  Size:    ~!FILE_SIZE_MB! MB
    )
) else (
    echo [ERROR] Expected output not found at %DIST_DIR%\%APP_NAME%.exe
    exit /b 1
)

echo.
echo ==========================================
echo  DEPLOYMENT NOTES
echo ==========================================
echo.
echo  1. The exe bundles all Python dependencies.
echo.
echo  2. Playwright Chromium browser is NOT bundled
echo     in the exe (it would add ~150MB). The Intune
echo     deploy\install.ps1 script handles browser
echo     installation to C:\ProgramData\Nexus\browsers.
echo.
echo  3. Config is bundled in the exe. Logs are
echo     written to %%APPDATA%%\Nexus\logs\.
echo.
echo  4. For Intune deployment, wrap the exe in an
echo     .intunewin package with the install script.
echo.
echo ==========================================

endlocal
