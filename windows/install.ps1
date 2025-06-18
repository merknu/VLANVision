# VLANVision Windows Installer Script
# Run as Administrator: powershell -ExecutionPolicy Bypass -File install.ps1

param(
    [string]$InstallPath = "C:\Program Files\VLANVision",
    [string]$DataPath = "C:\ProgramData\VLANVision",
    [int]$Port = 80,
    [switch]$StartService = $true,
    [switch]$OpenFirewall = $true
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VLANVision Network Management System" -ForegroundColor Cyan
Write-Host "Windows Server Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script must be run as Administrator. Exiting..." -ForegroundColor Red
    exit 1
}

# Function to test if a command exists
function Test-CommandExists {
    param($command)
    $null = Get-Command $command -ErrorAction SilentlyContinue
    return $?
}

Write-Host "`n[1/10] Checking prerequisites..." -ForegroundColor Yellow

# Check Python installation
$pythonVersion = $null
if (Test-CommandExists python) {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        if ($majorVersion -eq 3 -and $minorVersion -ge 8) {
            Write-Host "✓ Python $pythonVersion found" -ForegroundColor Green
        } else {
            Write-Host "✗ Python 3.8+ required. Found: $pythonVersion" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "✗ Python not found. Installing Python 3.11..." -ForegroundColor Yellow
    
    # Download and install Python
    $pythonInstaller = "$env:TEMP\python-3.11.0-amd64.exe"
    Write-Host "  Downloading Python installer..."
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe" -OutFile $pythonInstaller
    
    Write-Host "  Installing Python..."
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Check Git installation (optional but recommended)
if (Test-CommandExists git) {
    Write-Host "✓ Git found" -ForegroundColor Green
} else {
    Write-Host "⚠ Git not found (optional)" -ForegroundColor Yellow
}

Write-Host "`n[2/10] Creating directory structure..." -ForegroundColor Yellow

# Create directories
@($InstallPath, $DataPath, "$DataPath\logs", "$DataPath\config", "$DataPath\data", "$DataPath\backups") | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
        Write-Host "✓ Created $_" -ForegroundColor Green
    }
}

Write-Host "`n[3/10] Downloading VLANVision..." -ForegroundColor Yellow

# Download latest release
$downloadUrl = "https://github.com/merknu/VLANVision/archive/refs/heads/main.zip"
$zipFile = "$env:TEMP\vlanvision.zip"

Write-Host "  Downloading from GitHub..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile

Write-Host "  Extracting files..."
Expand-Archive -Path $zipFile -DestinationPath $env:TEMP -Force

# Copy files to installation directory
$sourceDir = "$env:TEMP\VLANVision-main\*"
Copy-Item -Path $sourceDir -Destination $InstallPath -Recurse -Force

Write-Host "✓ VLANVision files installed" -ForegroundColor Green

Write-Host "`n[4/10] Creating Python virtual environment..." -ForegroundColor Yellow

Set-Location $InstallPath
python -m venv venv

Write-Host "✓ Virtual environment created" -ForegroundColor Green

Write-Host "`n[5/10] Installing Python dependencies..." -ForegroundColor Yellow

# Activate virtual environment and install dependencies
& "$InstallPath\venv\Scripts\python.exe" -m pip install --upgrade pip
& "$InstallPath\venv\Scripts\pip.exe" install -r requirements.txt
& "$InstallPath\venv\Scripts\pip.exe" install pywin32 waitress

Write-Host "✓ Dependencies installed" -ForegroundColor Green

Write-Host "`n[6/10] Configuring VLANVision..." -ForegroundColor Yellow

# Create configuration file
$config = @"
# VLANVision Configuration
SECRET_KEY=$(([System.Guid]::NewGuid()).ToString())
FLASK_ENV=production
DATABASE_URL=sqlite:///$($DataPath -replace '\\', '/')/data/vlanvision.db
LOG_PATH=$($DataPath -replace '\\', '/')/logs
BACKUP_PATH=$($DataPath -replace '\\', '/')/backups

# Network settings
SNMP_COMMUNITY=public
DEFAULT_NETWORK_RANGE=10.0.0.0/8
DISCOVERY_THREADS=50

# Server settings
SERVER_HOST=0.0.0.0
SERVER_PORT=$Port

# Windows specific
WINDOWS_SERVICE=true
"@

$config | Out-File -FilePath "$DataPath\config\.env" -Encoding UTF8
Write-Host "✓ Configuration created" -ForegroundColor Green

# Create Windows-specific run script
$runScript = @"
import os
import sys
sys.path.insert(0, r'$InstallPath')

# Load configuration
from dotenv import load_dotenv
load_dotenv(r'$DataPath\config\.env')

# Set paths
os.environ['VLANVISION_DATA'] = r'$DataPath'

# Run with Waitress (Windows-friendly WSGI server)
from waitress import serve
from src.ui.app import create_app

app = create_app()
print(f"VLANVision running on http://0.0.0.0:$Port")
serve(app, host='0.0.0.0', port=$Port, threads=6)
"@

$runScript | Out-File -FilePath "$InstallPath\run_windows.py" -Encoding UTF8

Write-Host "`n[7/10] Creating Windows Service..." -ForegroundColor Yellow

# Create Windows service script
$serviceScript = @"
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import threading

sys.path.insert(0, r'$InstallPath')

class VLANVisionService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'VLANVision'
    _svc_display_name_ = 'VLANVision Network Management'
    _svc_description_ = 'Enterprise Network Management and Monitoring System'
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
    
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        # Load configuration
        from dotenv import load_dotenv
        load_dotenv(r'$DataPath\config\.env')
        
        os.environ['VLANVISION_DATA'] = r'$DataPath'
        
        # Start the application
        from waitress import serve
        from src.ui.app import create_app
        
        app = create_app()
        
        # Run in a separate thread
        def run_server():
            serve(app, host='0.0.0.0', port=$Port, threads=6)
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(VLANVisionService)
"@

$serviceScript | Out-File -FilePath "$InstallPath\vlanvision_service.py" -Encoding UTF8

# Install the Windows service
Write-Host "  Installing Windows service..."
& "$InstallPath\venv\Scripts\python.exe" "$InstallPath\vlanvision_service.py" install

Write-Host "✓ Windows service created" -ForegroundColor Green

Write-Host "`n[8/10] Configuring Windows Firewall..." -ForegroundColor Yellow

if ($OpenFirewall) {
    # Add firewall rules
    New-NetFirewallRule -DisplayName "VLANVision Web Interface" `
        -Direction Inbound -Protocol TCP -LocalPort $Port `
        -Action Allow -Profile Any | Out-Null
    
    New-NetFirewallRule -DisplayName "VLANVision SNMP" `
        -Direction Inbound -Protocol UDP -LocalPort 161 `
        -Action Allow -Profile Any | Out-Null
    
    Write-Host "✓ Firewall rules added" -ForegroundColor Green
} else {
    Write-Host "⚠ Firewall rules skipped" -ForegroundColor Yellow
}

Write-Host "`n[9/10] Creating shortcuts..." -ForegroundColor Yellow

# Create Start Menu shortcuts
$startMenuPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\VLANVision"
New-Item -ItemType Directory -Path $startMenuPath -Force | Out-Null

# Web interface shortcut
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$startMenuPath\VLANVision Web Interface.lnk")
$Shortcut.TargetPath = "http://localhost:$Port"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,13"
$Shortcut.Save()

# Management shortcut
$Shortcut = $WshShell.CreateShortcut("$startMenuPath\VLANVision Management.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\windows\manage.ps1`""
$Shortcut.WorkingDirectory = $InstallPath
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,1"
$Shortcut.Save()

Write-Host "✓ Shortcuts created" -ForegroundColor Green

Write-Host "`n[10/10] Starting VLANVision service..." -ForegroundColor Yellow

if ($StartService) {
    Start-Service -Name "VLANVision"
    Write-Host "✓ VLANVision service started" -ForegroundColor Green
}

# Create uninstaller
$uninstaller = @"
# VLANVision Uninstaller
Write-Host "Uninstalling VLANVision..." -ForegroundColor Yellow

# Stop and remove service
Stop-Service -Name "VLANVision" -ErrorAction SilentlyContinue
& "$InstallPath\venv\Scripts\python.exe" "$InstallPath\vlanvision_service.py" remove

# Remove firewall rules
Remove-NetFirewallRule -DisplayName "VLANVision*" -ErrorAction SilentlyContinue

# Remove directories
Remove-Item -Path "$InstallPath" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$DataPath" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\VLANVision" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "VLANVision has been uninstalled." -ForegroundColor Green
"@

$uninstaller | Out-File -FilePath "$InstallPath\windows\uninstall.ps1" -Encoding UTF8

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "VLANVision is now installed and running as a Windows service."
Write-Host ""
Write-Host "Access the web interface at: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Default credentials: admin / admin" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation directory: $InstallPath" -ForegroundColor Gray
Write-Host "Data directory: $DataPath" -ForegroundColor Gray
Write-Host ""
Write-Host "To manage the service:" -ForegroundColor Yellow
Write-Host "  Start:   Start-Service VLANVision"
Write-Host "  Stop:    Stop-Service VLANVision"
Write-Host "  Status:  Get-Service VLANVision"
Write-Host ""

# Open web browser
Start-Process "http://localhost:$Port"