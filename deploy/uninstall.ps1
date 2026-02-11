# Nexus - Intune Uninstall Script
# Removes Nexus application, shared browsers, and environment variable
#
# Intune Win32 app configuration:
#   Uninstall command: powershell.exe -ExecutionPolicy Bypass -File uninstall.ps1

param(
    [string]$InstallDir = "C:\Program Files\Nexus",
    [string]$BrowserDir = "C:\ProgramData\Nexus\browsers"
)

$ErrorActionPreference = "Stop"
$LogFile = "$env:TEMP\Nexus_Uninstall.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "$timestamp - $Message"
    Add-Content -Path $LogFile -Value $entry
    Write-Host $entry
}

try {
    Write-Log "=== Nexus Uninstall Started ==="

    # Remove install directory
    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
        Write-Log "Removed install directory: $InstallDir"
    }

    # Remove shared browser directory
    if (Test-Path $BrowserDir) {
        Remove-Item -Path $BrowserDir -Recurse -Force
        Write-Log "Removed browser directory: $BrowserDir"
    }
    # Clean up parent if empty
    $BrowserParent = Split-Path $BrowserDir -Parent
    if ((Test-Path $BrowserParent) -and @(Get-ChildItem $BrowserParent).Count -eq 0) {
        Remove-Item -Path $BrowserParent -Force
        Write-Log "Removed empty parent directory: $BrowserParent"
    }

    # Remove machine-wide environment variable
    [System.Environment]::SetEnvironmentVariable("PLAYWRIGHT_BROWSERS_PATH", $null, "Machine")
    Write-Log "Removed PLAYWRIGHT_BROWSERS_PATH environment variable"

    # Remove Start Menu shortcut
    $StartMenuPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Nexus.lnk"
    if (Test-Path $StartMenuPath) {
        Remove-Item -Path $StartMenuPath -Force
        Write-Log "Removed Start Menu shortcut"
    }

    Write-Log "=== Nexus Uninstall Completed Successfully ==="
    exit 0

} catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
