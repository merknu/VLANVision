@echo off
REM VLANVision One-Click Installer for Windows Server
REM This will install VLANVision with all dependencies

echo ========================================
echo VLANVision Network Management System
echo One-Click Windows Installer
echo ========================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This installer requires Administrator privileges.
    echo Right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo This will install VLANVision on your Windows Server.
echo.
echo Installation includes:
echo   - Python 3.11 (if not installed)
echo   - VLANVision application files
echo   - Windows Service registration
echo   - Firewall rules for web access
echo   - Automatic startup configuration
echo.
echo Default installation path: C:\Program Files\VLANVision
echo Default web port: 80
echo.

set /p continue="Continue with installation? (Y/N): "
if /i "%continue%" neq "Y" (
    echo Installation cancelled.
    pause
    exit /b 0
)

echo.
echo Starting installation...
echo.

REM Download install script if not present
if not exist "install.ps1" (
    echo Downloading installation script...
    powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/merknu/VLANVision/main/windows/install.ps1' -OutFile 'install.ps1'"
)

REM Run PowerShell installer
powershell -ExecutionPolicy Bypass -File install.ps1

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo VLANVision is now running on this server.
echo.
echo Web Interface: http://localhost
echo Default Login: admin / admin
echo.
echo To manage VLANVision:
echo   - Use Start Menu shortcuts
echo   - Or run: C:\Program Files\VLANVision\windows\manage.ps1
echo.
pause