# Nexus Monitor - Installation Script
# Installs NexusMonitor.exe and registers it as a scheduled task that runs at startup
#
# Usage: Run as Administrator
#   powershell -ExecutionPolicy Bypass -File install_monitor.ps1

$ErrorActionPreference = "Stop"

$AppName = "NexusMonitor"
$InstallDir = "C:\Scripts\NexusMonitor"
$ExeName = "NexusMonitor.exe"
$ConfigName = "monitor_config.json"
$TaskName = "NexusMonitor"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Nexus Monitor Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check for admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

# Step 2: Check source files exist
$exeSource = Join-Path $ScriptDir $ExeName
$configSource = Join-Path $ScriptDir $ConfigName

if (-not (Test-Path $exeSource)) {
    Write-Host "ERROR: $ExeName not found in $ScriptDir" -ForegroundColor Red
    Write-Host "Place $ExeName alongside this script and try again." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $configSource)) {
    Write-Host "ERROR: $ConfigName not found in $ScriptDir" -ForegroundColor Red
    Write-Host "Place $ConfigName alongside this script and try again." -ForegroundColor Yellow
    exit 1
}

# Step 3: Stop existing task if running
Write-Host "[1/5] Stopping existing task (if running)..."
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  Removed existing scheduled task."
}

# Step 4: Install files
Write-Host "[2/5] Installing to $InstallDir..."
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
$exeDest = Join-Path $InstallDir $ExeName
$configDest = Join-Path $InstallDir $ConfigName
if ($exeSource -ne $exeDest) {
    Copy-Item $exeSource -Destination $InstallDir -Force
    Write-Host "  Copied $ExeName"
} else {
    Write-Host "  $ExeName already in place"
}
if ($configSource -ne $configDest) {
    Copy-Item $configSource -Destination $InstallDir -Force
    Write-Host "  Copied $ConfigName"
} else {
    Write-Host "  $ConfigName already in place"
}

# Step 5: Create data directories
Write-Host "[3/5] Creating data directories..."
$dataDir = $InstallDir
New-Item -ItemType Directory -Path "$dataDir\logs" -Force | Out-Null
Write-Host "  Created $dataDir\logs"

# Step 6: Register scheduled task
Write-Host "[4/5] Registering scheduled task..."
$exePath = Join-Path $InstallDir $ExeName
$action = New-ScheduledTaskAction -Execute $exePath -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Nexus Monitor - Background polling service for automated tasks" | Out-Null

Write-Host "  Task registered: $TaskName (runs at startup as SYSTEM)"

# Step 7: Start the task now
Write-Host "[5/5] Starting task..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2

$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Status:    $($task.State)"
Write-Host "  Exe:       $exePath"
Write-Host "  Config:    $(Join-Path $InstallDir $ConfigName)"
Write-Host "  Logs:      $dataDir\logs\"
Write-Host "  State:     $dataDir\state.json"
Write-Host ""
Write-Host "  To check:  Get-ScheduledTask -TaskName $TaskName"
Write-Host "  To stop:   Stop-ScheduledTask -TaskName $TaskName"
Write-Host "  To start:  Start-ScheduledTask -TaskName $TaskName"
Write-Host ""
