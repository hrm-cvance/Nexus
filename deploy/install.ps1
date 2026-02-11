# Nexus - Intune Install Script
# Deploys Nexus.exe and installs Playwright Chromium browser
#
# Intune Win32 app configuration:
#   Install command:   powershell.exe -ExecutionPolicy Bypass -File install.ps1
#   Uninstall command: powershell.exe -ExecutionPolicy Bypass -File uninstall.ps1
#   Detection rule:    File exists - C:\Program Files\Nexus\Nexus.exe
#
# Notes:
#   - Runs as SYSTEM via Intune, so browsers are installed to a shared
#     machine-wide path (C:\ProgramData\Nexus\browsers) instead of per-user.
#   - A system environment variable PLAYWRIGHT_BROWSERS_PATH is set so
#     Nexus (and Playwright) find the browsers regardless of which user runs it.
#   - No admin rights are required for end users to run Nexus.

param(
    [string]$InstallDir = "C:\Program Files\Nexus",
    [string]$BrowserDir = "C:\ProgramData\Nexus\browsers"
)

$ErrorActionPreference = "Stop"
$LogFile = "$env:TEMP\Nexus_Install.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "$timestamp - $Message"
    Add-Content -Path $LogFile -Value $entry
    Write-Host $entry
}

try {
    Write-Log "=== Nexus Installation Started ==="
    Write-Log "Install directory: $InstallDir"
    Write-Log "Browser directory: $BrowserDir"

    # Create install directory
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        Write-Log "Created install directory"
    }

    # Create shared browser directory (readable by all users)
    if (-not (Test-Path $BrowserDir)) {
        New-Item -ItemType Directory -Path $BrowserDir -Force | Out-Null
        Write-Log "Created browser directory"
    }

    # Copy Nexus.exe (expects it in the same directory as this script)
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $SourceExe = Join-Path $ScriptDir "Nexus.exe"

    if (-not (Test-Path $SourceExe)) {
        Write-Log "ERROR: Nexus.exe not found at $SourceExe"
        exit 1
    }

    Copy-Item -Path $SourceExe -Destination "$InstallDir\Nexus.exe" -Force
    Write-Log "Copied Nexus.exe to $InstallDir"

    # Set machine-wide PLAYWRIGHT_BROWSERS_PATH so all users share one browser install.
    # This persists across reboots and is visible to all user sessions.
    [System.Environment]::SetEnvironmentVariable(
        "PLAYWRIGHT_BROWSERS_PATH", $BrowserDir, "Machine"
    )
    # Also set it for the current process so the install command picks it up
    $env:PLAYWRIGHT_BROWSERS_PATH = $BrowserDir
    Write-Log "Set PLAYWRIGHT_BROWSERS_PATH = $BrowserDir (Machine scope)"

    # Install Playwright Chromium browser using the bundled driver
    Write-Log "Installing Playwright Chromium browser to shared path..."
    $process = Start-Process -FilePath "$InstallDir\Nexus.exe" `
        -ArgumentList "--install-browsers" `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput "$env:TEMP\Nexus_browser_install.log" `
        -RedirectStandardError "$env:TEMP\Nexus_browser_install_err.log"

    $stdout = Get-Content "$env:TEMP\Nexus_browser_install.log" -ErrorAction SilentlyContinue
    $stderr = Get-Content "$env:TEMP\Nexus_browser_install_err.log" -ErrorAction SilentlyContinue

    if ($stdout) { Write-Log "Browser install output: $stdout" }
    if ($stderr) { Write-Log "Browser install errors: $stderr" }

    if ($process.ExitCode -ne 0) {
        Write-Log "WARNING: Browser install exited with code $($process.ExitCode). Users may need to install manually."
    } else {
        Write-Log "Playwright Chromium installed successfully to $BrowserDir"
    }

    # Create Start Menu shortcut
    $StartMenuPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Nexus.lnk"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($StartMenuPath)
    $Shortcut.TargetPath = "$InstallDir\Nexus.exe"
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = "Nexus - Vendor Account Provisioning"
    $Shortcut.Save()
    Write-Log "Created Start Menu shortcut"

    Write-Log "=== Nexus Installation Completed Successfully ==="
    exit 0

} catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
