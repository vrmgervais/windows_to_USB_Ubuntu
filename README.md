# NOTE: The bash script (create_windows_usb.sh) is working as expected. The content of this README can be applied to the bash script functionality #
# The Python script runs a GUI to do the same as the bash script #

# windows_to_USB_Ubuntu
An AI assisted code created to write Windows ISO to USB

**Requirements and Instructions for Creating a Bootable Windows USB**

**Overview**
This document describes the requirements, dependencies, and steps to run the iso-to-usb.py Python script, which creates a bootable Windows USB drive from a Windows ISO file on a Linux system. The script features a graphical user interface (GUI) for selecting the ISO and USB device, ensures UEFI compatibility, and includes safeguards to prevent the Windows bootloader from installing on the USB.

**System Requirements**
- Operating System: Linux distribution (tested on Ubuntu/Debian-based systems).
- User Privileges: Root access (script must be run with sudo).
- Hardware:
    - A USB drive with at least 8 GB capacity (16 GB recommended).
    - Sufficient disk space for the Windows ISO file (typically 4–8 GB).
    - Windows ISO: A valid Windows ISO file (e.g., Windows 11 24H2) containing /efi, /boot, and /sources/install.wim.

**Dependencies**
The script requires the following software packages, available in Ubuntu/Debian repositories:
- Python 3: For running the script ---> Package: python3
- Tkinter: Python’s GUI library for the interface.
    ◦ Package: python3-tk
- lsblk: Lists block devices (USB detection).
    - Package: util-linux
- parted: Manages disk partitions.
    ◦ Package: parted
- mkfs.vfat: Formats FAT32 partitions.
    ◦ Package: dosfstools
- mkfs.ntfs: Formats NTFS partitions.
    ◦ Package: ntfs-3g
- partprobe: Updates partition table.
    ◦ Package: parted
- wipefs: Wipes filesystem signatures.
    ◦ Package: util-linux
- mount: Mounts ISO and USB partitions.
    ◦ Package: util-linux
- rsync: Copies files to USB.
    ◦ Package: rsync
- pv (optional): Displays file copy progress.
    ◦ Package: pv
        
**Install Dependencies**
Run the following command to install all required packages:
`sudo apt update`
`sudo apt install python3 python3-tk util-linux parted dosfstools ntfs-3g rsync pv`

Verify Tkinter:
`python3 -c "import tkinter"`

If no errors appear, Tkinter is installed.

**Script Setup**
    - **Save the Script:**
        ◦ Copy the iso-to-usb.py script to a directory (e.g., /home/user/win-to-usb/).
        ◦ Example filename: iso-to-usb.py.
        ◦ Ensure the script is executable:
        `chmod +x /home/user/win-to-usb/iso-to-usb.py`
    - **Prepare ISO and USB:**
        ◦ Download a Windows ISO file (e.g., Win11_24H2_EnglishInternational_x64.iso) and note its path.
        ◦ Insert a USB drive (e.g., /dev/sda or /dev/sdb etc) with sufficient capacity. Warning: All data on the USB will be erased.
        
**Running the Script**
    - **Launch the Script:**
        ◦ Open a terminal and run the script with sudo:
          `sudo python3 /home/user/win-to-usb/iso-to-usb.py`
    - **Using the GUI:**
        ◦ Select ISO: Click “Browse” to choose the Windows ISO file.
        ◦ Select USB: Choose a USB device from the dropdown (e.g., sdb (14.8G, Flash Disk)). Click “Refresh” if the device doesn’t appear.
            - Note: Be careful when selecting devices. /dev/sda, is typically an internal drive. Make sure the USB drive you select is NOT the
            internal drive of your PC and in fact the USB drive you intent to write to. A warning dialog will appear if /dev/sda is selected.
        ◦ Confirm: Check “I understand and want to proceed” to acknowledge data loss on the USB.
        ◦ Start: Click “Start” to begin the process.
        ◦ Monitor the progress bar and log area (below the progress bar) for status updates.
    - **Output:**
        - On success, a popup confirms the USB is ready. You may have to unmount the drive(s) if still mounted in your system. The popup displays              instructions to ensure the Windows bootloader installs on the internal drive.:
            - Set the internal drive as the first boot device in BIOS/UEFI.
            - Disconnect other drives if possible.
            - Install to unallocated space.
        ◦ On failure, a popup displays “Failed to create bootable USB. Check the log for details.” Copy the log text for troubleshooting.

**Troubleshooting**
    - No USB Devices in Dropdown:
        ◦ Run: lsblk -d -o NAME,SIZE,TYPE,MODEL,TRAN,RM | grep usb
        ◦ Ensure the USB is inserted and removable (RM=1).
    - Error in Log:
        ◦ Copy the log area text, especially “Error:” or “Traceback:” lines, and review for issues (e.g., invalid ISO, USB in use).
    - Invalid ISO:
        ◦ Verify: file /path/to/iso (should show ISO 9660)
        ◦ Check contents: sudo mount -o loop /path/to/iso /mnt; ls /mnt/efi /mnt/boot /mnt/sources/install.wim; sudo umount /mnt.
    - USB Issues:
        ◦ Check mounts: mount | grep /dev/sdb.
        ◦ Unmount if needed: sudo umount /dev/sdb1 /dev/sdb2.

**Notes**
    - The script creates two partitions: a 1 GB FAT32 BOOT partition and an NTFS INSTALL partition for the remaining space.
    - It uses rsync with specific flags (-rltD --no-owner --no-group --no-perms) to handle FAT32 compatibility.
    - The script filters USB devices to show only removable drives (TRAN=usb, RM=1) to prevent internal drive selection.

For support, provide the log output and details of the ISO and USB used.


**Contributing**
Contributions are welcome! Please open an issue or submit a pull request for bug fixes, feature enhancements, or additional distro support.

**License**
This project is licensed under the MIT License. See the LICENSE file for details.

**Acknowledgments**
Bash script works, tested on Ubuntu (PopOS 22.04)
GUI built with Python and Tkinter for a user-friendly experience.
Inspired by the need for a simple, Linux-based tool to create Windows bootable USBs.
