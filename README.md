# Vulnvision Installer

The `vulnvision-installer` utility automates the setup, updates, and maintenance of the Vulnvision system.

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Operating System** | Ubuntu (Latest Stable) | Ubuntu (Latest Stable) |
| **RAM** | 8GB | 16GB+ |
| **CPU** | 4 cores | 8+ cores |
| **Disk Space** | 50GB+ | 100GB+ |
| **User Privileges** | Non-root user with `sudo` access | Non-root user with `sudo` access |

## Quick Start

### 1. Setup
```bash
git clone https://github.com/vulnvision/vulnvision-installer.git
cd vulnvision-installer
chmod +x vulnvision-installer
```

### 2. Install
Run the installer (do **not** use sudo):
```bash
./vulnvision-installer
```
*Follow the on-screen prompts for License Key, Server IP, Email, and Docker Hub Token.*

## Maintenance & Operations

| Task | Command | Description |
|------|---------|-------------|
| **Update System** | `./vulnvision-installer -pull`<br>`./vulnvision-installer -update` | Pulls latest code and updates the system. |
| **Download Feeds** | `./vulnvision-installer -download-feeds` | Downloads enterprise feeds (Requires `LICENSE_KEY`). |
| **Sync Feeds** | `./vulnvision-installer -sync-feed` | Manually syncs Vulnvision assessment feeds. |
| **Reset Config** | `./vulnvision-installer -reset` | Resets system services and permissions. |
| **Create Admin** | `./vulnvision-installer -create-user -email <email> -password <pass>` | Creates a new superuser manually. |

## Important Notes
*   **Permissions**: The installer handles privilege escalation internally. You will be asked for your sudo password.
*   **Default Password**: The default admin password is `Vulnvision2025`. **Change this immediately.**
*   **Environment**: ensure `env_files/vulnvision.env` is populated if running without the interactive wizard.
