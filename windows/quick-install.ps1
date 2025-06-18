# VLANVision Quick Installer for Windows Server
# Downloads and installs VLANVision in under 5 minutes

param(
    [switch]$Silent = $false,
    [switch]$SkipPython = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$VLANVISION_VERSION = "latest"
$PYTHON_VERSION = "3.11.0"
$INSTALL_PATH = "C:\VLANVision"
$SERVICE_NAME = "VLANVision"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Cyan "====================================="
Write-ColorOutput Cyan "VLANVision Quick Installer"
Write-ColorOutput Cyan "Network Management in 5 Minutes"
Write-ColorOutput Cyan "====================================="
Write-Host ""

# Check admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-ColorOutput Red "ERROR: Administrator privileges required!"
    Write-Host "Please run PowerShell as Administrator"
    exit 1
}

# Quick Python check/install
if (-not $SkipPython) {
    Write-Host "Checking Python..." -NoNewline
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        Write-ColorOutput Green " Found!"
    } else {
        Write-ColorOutput Yellow " Not found. Installing..."
        
        # Download Python silently
        $pythonUrl = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-amd64.exe"
        $pythonInstaller = "$env:TEMP\python-installer.exe"
        
        Write-Host "  Downloading Python..."
        (New-Object Net.WebClient).DownloadFile($pythonUrl, $pythonInstaller)
        
        Write-Host "  Installing Python (this may take 2-3 minutes)..."
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-ColorOutput Green "  Python installed!"
    }
}

# Create installation directory
Write-Host "Creating directories..." -NoNewline
New-Item -ItemType Directory -Path $INSTALL_PATH -Force | Out-Null
New-Item -ItemType Directory -Path "$INSTALL_PATH\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$INSTALL_PATH\logs" -Force | Out-Null
Write-ColorOutput Green " Done!"

# Download VLANVision
Write-Host "Downloading VLANVision..." -NoNewline
$zipUrl = "https://github.com/merknu/VLANVision/archive/refs/heads/main.zip"
$zipFile = "$INSTALL_PATH\vlanvision.zip"
(New-Object Net.WebClient).DownloadFile($zipUrl, $zipFile)
Write-ColorOutput Green " Done!"

# Extract
Write-Host "Extracting files..." -NoNewline
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($zipFile, $INSTALL_PATH)
Move-Item "$INSTALL_PATH\VLANVision-main\*" $INSTALL_PATH -Force
Remove-Item "$INSTALL_PATH\VLANVision-main" -Recurse -Force
Remove-Item $zipFile
Write-ColorOutput Green " Done!"

# Install dependencies
Write-Host "Installing dependencies (this may take 2-3 minutes)..."
Set-Location $INSTALL_PATH
& python -m venv venv 2>&1 | Out-Null
& "$INSTALL_PATH\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$INSTALL_PATH\venv\Scripts\pip.exe" install -r requirements.txt --quiet
& "$INSTALL_PATH\venv\Scripts\pip.exe" install pywin32 waitress --quiet
Write-ColorOutput Green "Dependencies installed!"

# Create minimal config
Write-Host "Configuring VLANVision..." -NoNewline
$config = @"
SECRET_KEY=$(([System.Guid]::NewGuid()).ToString())
FLASK_ENV=production
DATABASE_URL=sqlite:///$INSTALL_PATH/data/vlanvision.db
SERVER_PORT=80
SNMP_COMMUNITY=public
"@
$config | Out-File -FilePath "$INSTALL_PATH\.env" -Encoding UTF8
Write-ColorOutput Green " Done!"

# Create Windows service
Write-Host "Creating Windows service..." -NoNewline

$serviceCode = @'
import win32serviceutil
import win32service
import win32event
import os
import sys

sys.path.insert(0, r"C:\VLANVision")

class VLANVisionService(win32serviceutil.ServiceFramework):
    _svc_name_ = "VLANVision"
    _svc_display_name_ = "VLANVision Network Management"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
    
    def SvcDoRun(self):
        from dotenv import load_dotenv
        load_dotenv(r"C:\VLANVision\.env")
        
        from waitress import serve
        from src.ui.app import create_app
        
        app = create_app()
        serve(app, host="0.0.0.0", port=80, threads=6)

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(VLANVisionService)
'@

$serviceCode | Out-File -FilePath "$INSTALL_PATH\service.py" -Encoding UTF8

# Install service
& "$INSTALL_PATH\venv\Scripts\python.exe" "$INSTALL_PATH\service.py" --startup auto install 2>&1 | Out-Null
Write-ColorOutput Green " Done!"

# Configure firewall
Write-Host "Configuring firewall..." -NoNewline
New-NetFirewallRule -DisplayName "VLANVision" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Profile Any 2>&1 | Out-Null
Write-ColorOutput Green " Done!"

# Start service
Write-Host "Starting VLANVision..." -NoNewline
Start-Service -Name $SERVICE_NAME
Start-Sleep -Seconds 3
Write-ColorOutput Green " Started!"

# Create desktop shortcut
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\VLANVision.lnk")
$Shortcut.TargetPath = "http://localhost"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,13"
$Shortcut.Save()

Write-Host ""
Write-ColorOutput Green "====================================="
Write-ColorOutput Green "Installation Complete!"
Write-ColorOutput Green "====================================="
Write-Host ""
Write-Host "VLANVision is now running at: " -NoNewline
Write-ColorOutput Cyan "http://localhost"
Write-Host ""
Write-Host "Default login: " -NoNewline
Write-ColorOutput Yellow "admin / admin"
Write-Host ""
Write-Host "A shortcut has been created on your desktop."
Write-Host ""
Write-Host "Total installation time: " -NoNewline
Write-Host "$([int]((Get-Date) - $start).TotalSeconds) seconds"
Write-Host ""

if (-not $Silent) {
    Write-Host "Press any key to open VLANVision in your browser..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Start-Process "http://localhost"
}