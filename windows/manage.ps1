# VLANVision Management Console
# Provides easy management of VLANVision on Windows

param(
    [Parameter(Position=0)]
    [ValidateSet('status', 'start', 'stop', 'restart', 'backup', 'restore', 'discover', 'monitor', 'update', 'logs')]
    [string]$Action = 'status'
)

$ErrorActionPreference = "Stop"

# Configuration
$InstallPath = "C:\Program Files\VLANVision"
$DataPath = "C:\ProgramData\VLANVision"
$ServiceName = "VLANVision"

# Check if running as Administrator for certain actions
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Header
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VLANVision Management Console" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

switch ($Action) {
    'status' {
        Write-Host "Service Status:" -ForegroundColor Yellow
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        
        if ($service) {
            $status = $service.Status
            $color = if ($status -eq 'Running') { 'Green' } else { 'Red' }
            Write-Host "  Status: $status" -ForegroundColor $color
            
            if ($status -eq 'Running') {
                # Get process info
                $process = Get-Process -Name "python" | Where-Object { $_.Path -like "*VLANVision*" } | Select-Object -First 1
                if ($process) {
                    Write-Host "  PID: $($process.Id)"
                    Write-Host "  Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB"
                    Write-Host "  CPU: $([math]::Round($process.CPU, 2)) seconds"
                }
                
                # Check if web interface is responding
                try {
                    $response = Invoke-WebRequest -Uri "http://localhost/api/health" -TimeoutSec 5 -UseBasicParsing
                    Write-Host "  Web Interface: Online" -ForegroundColor Green
                } catch {
                    Write-Host "  Web Interface: Not Responding" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "  Service not found!" -ForegroundColor Red
        }
        
        Write-Host "`nData Statistics:" -ForegroundColor Yellow
        
        # Database info
        $dbPath = "$DataPath\data\vlanvision.db"
        if (Test-Path $dbPath) {
            $dbSize = [math]::Round((Get-Item $dbPath).Length / 1MB, 2)
            Write-Host "  Database Size: $dbSize MB"
        }
        
        # Log info
        $logFiles = Get-ChildItem "$DataPath\logs" -Filter "*.log" -ErrorAction SilentlyContinue
        if ($logFiles) {
            $totalLogSize = [math]::Round(($logFiles | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
            Write-Host "  Log Files: $($logFiles.Count) files, $totalLogSize MB total"
        }
        
        # Backup info
        $backups = Get-ChildItem "$DataPath\backups" -Filter "*.backup" -ErrorAction SilentlyContinue
        if ($backups) {
            Write-Host "  Backups: $($backups.Count) backups available"
            Write-Host "  Latest: $(($backups | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime)"
        }
    }
    
    'start' {
        if (-not (Test-Administrator)) {
            Write-Host "Administrator privileges required to start service" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Starting VLANVision service..." -ForegroundColor Yellow
        Start-Service -Name $ServiceName
        Start-Sleep -Seconds 3
        
        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq 'Running') {
            Write-Host "✓ Service started successfully" -ForegroundColor Green
            Write-Host "`nOpening web interface..."
            Start-Process "http://localhost"
        } else {
            Write-Host "✗ Failed to start service" -ForegroundColor Red
        }
    }
    
    'stop' {
        if (-not (Test-Administrator)) {
            Write-Host "Administrator privileges required to stop service" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Stopping VLANVision service..." -ForegroundColor Yellow
        Stop-Service -Name $ServiceName
        Write-Host "✓ Service stopped" -ForegroundColor Green
    }
    
    'restart' {
        if (-not (Test-Administrator)) {
            Write-Host "Administrator privileges required to restart service" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Restarting VLANVision service..." -ForegroundColor Yellow
        Restart-Service -Name $ServiceName
        Write-Host "✓ Service restarted" -ForegroundColor Green
    }
    
    'backup' {
        Write-Host "Creating backup..." -ForegroundColor Yellow
        
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupDir = "$DataPath\backups\backup_$timestamp"
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        
        # Stop service for consistent backup
        $wasRunning = (Get-Service -Name $ServiceName).Status -eq 'Running'
        if ($wasRunning -and (Test-Administrator)) {
            Write-Host "  Stopping service for backup..."
            Stop-Service -Name $ServiceName
        }
        
        # Backup database
        Copy-Item "$DataPath\data\vlanvision.db" "$backupDir\" -ErrorAction SilentlyContinue
        
        # Backup configuration
        Copy-Item "$DataPath\config\.env" "$backupDir\" -ErrorAction SilentlyContinue
        
        # Create backup manifest
        @{
            Timestamp = Get-Date
            Version = "1.0"
            Files = @("vlanvision.db", ".env")
        } | ConvertTo-Json | Out-File "$backupDir\manifest.json"
        
        # Compress backup
        Compress-Archive -Path "$backupDir\*" -DestinationPath "$DataPath\backups\vlanvision_$timestamp.zip"
        Remove-Item $backupDir -Recurse -Force
        
        # Restart service if it was running
        if ($wasRunning -and (Test-Administrator)) {
            Start-Service -Name $ServiceName
        }
        
        Write-Host "✓ Backup created: vlanvision_$timestamp.zip" -ForegroundColor Green
    }
    
    'restore' {
        if (-not (Test-Administrator)) {
            Write-Host "Administrator privileges required to restore backup" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Available backups:" -ForegroundColor Yellow
        $backups = Get-ChildItem "$DataPath\backups" -Filter "*.zip" | Sort-Object LastWriteTime -Descending
        
        if ($backups.Count -eq 0) {
            Write-Host "No backups found!" -ForegroundColor Red
            exit 1
        }
        
        for ($i = 0; $i -lt $backups.Count; $i++) {
            Write-Host "  [$($i+1)] $($backups[$i].Name) - $($backups[$i].LastWriteTime)"
        }
        
        $selection = Read-Host "`nSelect backup to restore (1-$($backups.Count))"
        $backupFile = $backups[[int]$selection - 1]
        
        Write-Host "`nRestoring from $($backupFile.Name)..." -ForegroundColor Yellow
        
        # Stop service
        Stop-Service -Name $ServiceName
        
        # Extract backup
        $tempDir = "$env:TEMP\vlanvision_restore"
        Expand-Archive -Path $backupFile.FullName -DestinationPath $tempDir -Force
        
        # Restore files
        Copy-Item "$tempDir\vlanvision.db" "$DataPath\data\" -Force
        Copy-Item "$tempDir\.env" "$DataPath\config\" -Force
        
        # Cleanup
        Remove-Item $tempDir -Recurse -Force
        
        # Start service
        Start-Service -Name $ServiceName
        
        Write-Host "✓ Restore completed" -ForegroundColor Green
    }
    
    'discover' {
        Write-Host "Network Discovery" -ForegroundColor Yellow
        $network = Read-Host "Enter network range (e.g., 192.168.1.0/24)"
        
        Write-Host "`nStarting network discovery for $network..." -ForegroundColor Yellow
        Write-Host "(This will open in your web browser)`n"
        
        # Open discovery page in browser
        Start-Process "http://localhost/network/discover?range=$network"
    }
    
    'monitor' {
        Write-Host "Real-time Monitoring" -ForegroundColor Yellow
        Write-Host "Opening monitoring dashboard...`n"
        
        Start-Process "http://localhost/monitoring/dashboard"
    }
    
    'update' {
        if (-not (Test-Administrator)) {
            Write-Host "Administrator privileges required to update" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Checking for updates..." -ForegroundColor Yellow
        
        # Download latest version info
        try {
            $latestVersion = Invoke-RestMethod -Uri "https://api.github.com/repos/merknu/VLANVision/releases/latest"
            Write-Host "  Latest version: $($latestVersion.tag_name)"
            
            # Compare with current version
            $currentVersion = Get-Content "$InstallPath\VERSION" -ErrorAction SilentlyContinue
            if ($currentVersion -eq $latestVersion.tag_name) {
                Write-Host "✓ VLANVision is up to date" -ForegroundColor Green
            } else {
                Write-Host "  Update available!" -ForegroundColor Yellow
                $confirm = Read-Host "Do you want to update now? (Y/N)"
                
                if ($confirm -eq 'Y') {
                    Write-Host "`nDownloading update..."
                    # Run update process
                    & "$InstallPath\windows\update.ps1"
                }
            }
        } catch {
            Write-Host "✗ Failed to check for updates" -ForegroundColor Red
        }
    }
    
    'logs' {
        Write-Host "Recent Log Entries:" -ForegroundColor Yellow
        
        $logFile = "$DataPath\logs\vlanvision.log"
        if (Test-Path $logFile) {
            Get-Content $logFile -Tail 50 | ForEach-Object {
                if ($_ -match "ERROR") {
                    Write-Host $_ -ForegroundColor Red
                } elseif ($_ -match "WARNING") {
                    Write-Host $_ -ForegroundColor Yellow
                } else {
                    Write-Host $_
                }
            }
        } else {
            Write-Host "No log file found" -ForegroundColor Red
        }
    }
}

Write-Host "`nManagement Commands:" -ForegroundColor Gray
Write-Host "  .\manage.ps1 status   - Show service status"
Write-Host "  .\manage.ps1 start    - Start service"
Write-Host "  .\manage.ps1 stop     - Stop service"
Write-Host "  .\manage.ps1 restart  - Restart service"
Write-Host "  .\manage.ps1 backup   - Create backup"
Write-Host "  .\manage.ps1 restore  - Restore from backup"
Write-Host "  .\manage.ps1 discover - Network discovery"
Write-Host "  .\manage.ps1 monitor  - Open monitoring"
Write-Host "  .\manage.ps1 update   - Check for updates"
Write-Host "  .\manage.ps1 logs     - View recent logs"