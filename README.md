# windows_to_USB_Ubuntu
An AI assisted code created to write Windows ISO to USB

This Python script creates a bootable USB drive from a Windows ISO file on Linux systems. It provides a graphical user interface (GUI) to select the ISO and USB drive, partitions and formats the USB, and copies the ISO contents to make it bootable for installing Windows. The tool is designed for ease of use and supports multiple Linux distributions.

**Features**

- GUI Interface: Built with Tkinter for selecting ISO files and USB drives.
- Automatic Dependency Installation: Installs required system tools (e.g., parted, rsync) based on the Linux distribution (Ubuntu, Fedora, Arch, etc.).
- Optimized File Copying: Uses rsync for faster file transfers and parallelizes copying of large files.
- Cross-Distro Support: Detects package managers (apt, dnf, pacman) for broader Linux compatibility.
- Standalone Executable: Can be built into a single executable using PyInstaller for easy distribution.

**Requirements**
**System**
- Operating System: Linux (tested on Pop!_OS 22.04, compatible with Ubuntu, Debian, Fedora, Arch)
- Root Privileges: Required for USB partitioning, formatting, and mounting
- USB Drive: At least 8 GB, will be erased during the process
- Windows ISO File: A valid Windows installation ISO (Tested and working with Win11_24H2_EnglishInternational_x64.iso)

**Software**
- Python 3: Version 3.6 or higher
- System Tools: lsb-release, parted, ntfs-3g, rsync, curl, p7zip-full, udisks2, dosfstools, pv, xterm, python3-tk (automatically installed by the script if missing)
- Python Modules: distro (install with pip install distro)
- PyInstaller: For building the standalone executable (install with pip install pyinstaller)

**Installation and Usage**
**Option 1: Run the Python Script Directly**
- Clone the Repository:
```
git clone https://github.com/vrmgervais/windows_to_USB_Ubuntu.git
cd windows-bootable-usb-creator
```
**Install Python Dependencies:**
```
pip install distro
```
**Run the Script:**
```
sudo python3 create_bootable_usb.py
```
- The sudo command is required for USB operations.
- The script will automatically install missing system tools.

**Use the GUI:**
- Click "Browse" to select a Windows ISO file.
- Click "Auto-Detect USB" to select the target USB drive (e.g., /dev/sdX).
- Click "Create Bootable USB" to start the process.
- Warning: The USB drive will be erased.

**Option 2: Build and Run the Standalone Executable**
**Clone the Repository (if not already done):**
```
git clone https://github.com/vrmgervais/windows_to_USB_Ubuntu.git
cd windows-bootable-usb-creator
```
**Install Build Dependencies:**
```
pip install distro pyinstaller
```
**Build the Executable:**
```
python3 setup.py
```
The executable will be created at dist/bootable-usb-creator.

**Run the Executable:**
```
chmod +x dist/bootable-usb-creator
sudo ./dist/bootable-usb-creator
```
The GUI will appear, and usage is the same as above.

**Expected Outcome**

- The script formats the USB drive with a GPT partition table, creating a FAT32 boot partition and an NTFS partition for the Windows installer.
- The Windows ISO contents are copied to the USB drive, with the boot.wim file placed in the boot partition.
- Upon completion, a success message is displayed, and the USB drive is ready to boot a computer for Windows installation (ensure the system is set to boot from USB in BIOS/UEFI).
- The process may take 10-30 minutes, depending on the USB drive's speed (USB 3.0 recommended for faster writes).

**Notes**
- Backup USB Data: The USB drive will be completely erased during the process.
- Cross-Distro Compatibility: The script supports Debian-based (Ubuntu, Pop!_OS), Fedora, and Arch-based distros. Other Linux distros may require manual dependency installation.
- System Tools: The script installs required tools automatically, but ensure internet access for package downloads.
**Troubleshooting:**
- If the GUI doesn’t appear, verify python3-tk is installed: sudo apt-get install python3-tk.
- If the executable fails, run the Python script directly to debug: sudo python3 create_bootable_usb.py.
- For build issues, check PyInstaller logs or ensure distro is installed.

**Contributing**
Contributions are welcome! Please open an issue or submit a pull request for bug fixes, feature enhancements, or additional distro support.

**License**
This project is licensed under the MIT License. See the LICENSE file for details.

**Acknowledgments**
Built with Python and Tkinter for a user-friendly experience.
Inspired by the need for a simple, Linux-based tool to create Windows bootable USBs.
