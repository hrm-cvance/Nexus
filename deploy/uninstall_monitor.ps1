# Nexus Monitor - Uninstall Script
# Removes the scheduled task, exe, and optionally data
#
# Usage: Run as Administrator
#   powershell -ExecutionPolicy Bypass -File uninstall_monitor.ps1

$ErrorActionPreference = "Stop"

$TaskName = "NexusMonitor"
$InstallDir = "C:\Scripts\NexusMonitor"
$DataDir = $InstallDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Nexus Monitor Uninstall" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

# Stop and remove scheduled task
Write-Host "[1/3] Removing scheduled task..."
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  Task removed."
} else {
    Write-Host "  No task found."
}

# Remove install directory
Write-Host "[2/3] Removing installation..."
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force
    Write-Host "  Removed $InstallDir"
} else {
    Write-Host "  Not found."
}

# Remove data directory
Write-Host "[3/3] Removing data..."
if (Test-Path $DataDir) {
    Remove-Item -Path $DataDir -Recurse -Force
    Write-Host "  Removed $DataDir"
} else {
    Write-Host "  Not found."
}

Write-Host ""
Write-Host "Uninstall complete." -ForegroundColor Green
Write-Host ""
