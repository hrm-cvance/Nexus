@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo  Nexus Build Script v1.0
echo  Highland Mortgage Services
echo ==========================================
echo.

REM ── Configuration ──────────────────────────
set APP_NAME=Nexus
set APP_VERSION=1.0.1
set ENTRY_POINT=main.py
set DIST_DIR=dist
set BUILD_DIR=build

REM ── Pre-flight checks ─────────────────────
echo [1/8] Running pre-flight checks...

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

set INTUNE_TOOL=C:\PrepTool\IntuneWinAppUtil.exe
set INTUNE_SOURCE=%DIST_DIR%\intune_source
set INTUNE_OUTPUT=%DIST_DIR%\intune_output

REM ── Clean previous builds ──────────────────
echo [2/8] Cleaning previous builds...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%APP_NAME%.spec" del "%APP_NAME%.spec"

REM ── Resolve customtkinter path ─────────────
echo [3/8] Resolving package paths...
for /f "delims=" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

if "!CTK_PATH!"=="" (
    echo [ERROR] customtkinter not found. Run: pip install customtkinter
    exit /b 1
)
echo        customtkinter: !CTK_PATH!

REM ── Generate version info ─────────────────
echo [4/8] Generating version info...
python version_info.py
if errorlevel 1 (
    echo [ERROR] Failed to generate version info.
    exit /b 1
)

REM ── Build executable ───────────────────────
echo [5/8] Building %APP_NAME% v%APP_VERSION%...
echo        This may take several minutes...
echo.

pyinstaller --onefile ^
    --name "%APP_NAME%" ^
    --windowed ^
    --icon "assets\nexus.ico" ^
    --version-file "version_info.txt" ^
    --add-data "config;config" ^
    --add-data "vendors;vendors" ^
    --add-data "assets;assets" ^
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

REM ── Post-build verification ──────────────────
echo.
echo [6/8] Verifying build output...

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

REM ── Prepare Intune source folder ─────────────
echo.
echo [7/8] Preparing Intune package source...

if exist "%INTUNE_SOURCE%" rmdir /s /q "%INTUNE_SOURCE%"
if exist "%INTUNE_OUTPUT%" rmdir /s /q "%INTUNE_OUTPUT%"
mkdir "%INTUNE_SOURCE%"
mkdir "%INTUNE_OUTPUT%"

copy "%DIST_DIR%\%APP_NAME%.exe" "%INTUNE_SOURCE%\" >nul
copy "deploy\install.ps1" "%INTUNE_SOURCE%\" >nul
copy "deploy\uninstall.ps1" "%INTUNE_SOURCE%\" >nul
echo        Copied Nexus.exe, install.ps1, uninstall.ps1 to %INTUNE_SOURCE%

REM ── Create .intunewin package ────────────────
echo.
echo [8/8] Creating .intunewin package...

if not exist "%INTUNE_TOOL%" (
    echo [WARNING] IntuneWinAppUtil.exe not found at %INTUNE_TOOL%
    echo          Skipping .intunewin packaging. Create it manually:
    echo          IntuneWinAppUtil.exe -c %INTUNE_SOURCE% -s install.ps1 -o %INTUNE_OUTPUT% -q
    goto :summary
)

"%INTUNE_TOOL%" -c "%INTUNE_SOURCE%" -s install.ps1 -o "%INTUNE_OUTPUT%" -q

if errorlevel 1 (
    echo [WARNING] .intunewin packaging failed. Check IntuneWinAppUtil output above.
) else (
    echo  Package: %INTUNE_OUTPUT%\install.intunewin
)

:summary
echo.
echo ==========================================
echo  BUILD COMPLETE - %APP_NAME% v%APP_VERSION%
echo ==========================================
echo.
echo  Exe:      %DIST_DIR%\%APP_NAME%.exe
if exist "%INTUNE_OUTPUT%\install.intunewin" (
echo  Intune:   %INTUNE_OUTPUT%\install.intunewin
)
echo.
echo  Notes:
echo  - Playwright Chromium is NOT bundled (~150MB).
echo    install.ps1 handles browser installation.
echo  - Config is bundled in the exe.
echo  - Logs: %%APPDATA%%\Nexus\logs\
echo.
echo ==========================================

endlocal
