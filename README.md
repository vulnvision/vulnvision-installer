# Vulnvision Installer

The `vulnvision-installer` is a utility designed to set up, pull updates, and maintain the Vulnvision system. Follow the steps below to ensure proper installation and operation.

---

## Requirements

### Operating System
- **Ubuntu** (latest stable version recommended)

### Hardware Specifications
- **RAM**: Minimum 16 GB (Recommended: 64 GB)
- **Processor**: Minimum 12 threads

---

## Installation Instructions

1. **Create a New User for Vulnvision**  
   Before proceeding with the installation, create a dedicated user called `vulnvision` and switch to it:
   
   ```bash
   sudo adduser vulnvision
   sudo usermod -aG sudo vulnvision
   su - vulnvision
   ```

2. **Clone the Repository**  
   Ensure you have the required access rights to clone the repository.

   ```bash
   git clone https://github.com/S-Amine/vulnvision-installer.git
   ```

3. **Navigate to the Installer Directory**  

   ```bash
   cd vulnvision-installer
   ```

4. **Grant Execute Permissions**  

   ```bash
   chmod +x vulnvision-installer
   ```

5. **Run the Installer with Sudo Privileges**  

   ```bash
   sudo ./vulnvision-installer
   ```

6. **Follow the On-Screen Prompts**  
   - Provide your **License Key**, **Server IP**, and **Email** when prompted.
   - Enter your **Docker Hub Access Token** to log in and pull required Docker images.

---

## Updating the System

### **Important:** Always pull the latest changes before updating.

1. **Pull the Latest Changes**  

   Use the `-pull` flag to fetch updates from the repository:

   ```bash
   sudo ./vulnvision-installer -pull
   ```

2. **Update the System**  

   After pulling the changes, use the `-update` flag to apply the updates:

   ```bash
   sudo ./vulnvision-installer -update
   ```

---

## Additional Notes

- **Environment File**: Ensure the `.env` file is properly configured before running the installer.
- **Nginx Configuration**: The installer automatically generates and links the necessary Nginx configuration files.
- **Default Admin Password**: The installer creates an admin account with the password `Vulnvision2025`. It is strongly recommended to change this password after installation.

---

## Workflow Summary

1. **Create a New User and Log In**  
   ```bash
   sudo adduser vulnvision
   sudo usermod -aG sudo vulnvision
   su - vulnvision
   ```

2. **Install or Set Up**  
   ```bash
   sudo ./vulnvision-installer
   ```

3. **Pull Latest Changes (Before Update)**  
   ```bash
   sudo ./vulnvision-installer --pull
   ```

4. **Update the System**  
   ```bash
   sudo ./vulnvision-installer --update
   ```

---

## Troubleshooting

If you encounter any issues, check the logs for error details or contact support.

Happy installing!

