# VLANVision Windows Server Installation

## 🚀 One-Line Installation (Recommended)

Open **PowerShell as Administrator** and run:

```powershell
iex ((New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/merknu/VLANVision/main/windows/quick-install.ps1'))
```

**That's it!** VLANVision will be installed and running in under 5 minutes.

## 📋 What Gets Installed

- Python 3.11 (if not already installed)
- VLANVision application and all dependencies
- Windows Service (auto-starts on boot)
- Firewall rules for web access
- Desktop shortcut

## 🖥️ System Requirements

- Windows Server 2016/2019/2022 or Windows 10/11
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Administrator privileges

## 🔧 Post-Installation

After installation:
1. Open http://localhost in your browser
2. Login with: **admin** / **admin**
3. Change the default password immediately

## 📁 Installation Locations

- Application: `C:\VLANVision`
- Data: `C:\VLANVision\data`
- Logs: `C:\VLANVision\logs`

## 🛠️ Management Commands

Open PowerShell as Administrator:

```powershell
# Check service status
Get-Service VLANVision

# Stop service
Stop-Service VLANVision

# Start service
Start-Service VLANVision

# View logs
Get-Content C:\VLANVision\logs\vlanvision.log -Tail 50

# Uninstall
C:\VLANVision\windows\uninstall.ps1
```

## 🔄 Alternative Installation Methods

### Method 1: Download and Run Installer

1. Download: [VLANVision-Setup.bat](https://github.com/merknu/VLANVision/raw/main/windows/VLANVision-Setup.bat)
2. Right-click → Run as Administrator
3. Follow the prompts

### Method 2: Manual Installation

1. Download the latest release
2. Extract to `C:\VLANVision`
3. Run as Administrator:
   ```powershell
   cd C:\VLANVision\windows
   .\install.ps1
   ```

## 🐛 Troubleshooting

### Service Won't Start
```powershell
# Check Python installation
python --version

# Reinstall dependencies
cd C:\VLANVision
.\venv\Scripts\pip install -r requirements.txt

# Check service logs
Get-EventLog -LogName Application -Source VLANVision -Newest 10
```

### Port 80 Already in Use
```powershell
# Find what's using port 80
netstat -ano | findstr :80

# Change VLANVision port in C:\VLANVision\.env
SERVER_PORT=8080

# Restart service
Restart-Service VLANVision
```

### Firewall Issues
```powershell
# Check firewall rule
Get-NetFirewallRule -DisplayName "VLANVision"

# Re-add firewall rule
New-NetFirewallRule -DisplayName "VLANVision" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

## 🔒 Security Recommendations

1. **Change default password immediately**
2. **Enable HTTPS** - Edit `.env` and add:
   ```
   SSL_CERT=C:\VLANVision\cert.pem
   SSL_KEY=C:\VLANVision\key.pem
   ```
3. **Restrict network access** - Configure Windows Firewall
4. **Enable Windows authentication** - Integrate with Active Directory

## 📊 Performance Tuning

For large networks (>1000 devices):

1. Edit `C:\VLANVision\.env`:
   ```
   DISCOVERY_THREADS=100
   MONITORING_WORKERS=50
   DATABASE_URL=postgresql://user:pass@localhost/vlanvision
   ```

2. Install PostgreSQL for better performance
3. Increase service memory allocation

## 🆘 Support

- **Documentation**: https://github.com/merknu/VLANVision/wiki
- **Issues**: https://github.com/merknu/VLANVision/issues
- **Email**: support@vlanvision.io