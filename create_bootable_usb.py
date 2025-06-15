import os
import sys
import subprocess
import re
import tempfile
import time
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread
import traceback

class WindowsUSBApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Create Windows Bootable USB")
        self.root.geometry("700x500")
        self.iso_mountpoint = None
        self.usb_mountpoint = None

        # Check for root privileges
        if os.geteuid() != 0:
            messagebox.showerror("Error", "This program must be run with sudo.\nRun as: sudo python3 create_windows_usb_gui.py")
            self.root.destroy()
            return

        # Variables
        self.iso_path = tk.StringVar()
        self.usb_device = tk.StringVar()
        self.confirmation = tk.BooleanVar(value=False)
        self.progress_value = tk.DoubleVar(value=0)

        # GUI Elements
        tk.Label(root, text="Windows ISO File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(root, textvariable=self.iso_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(root, text="Browse", command=self.browse_iso).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(root, text="USB Device:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.usb_menu = tk.OptionMenu(root, self.usb_device, "Loading USB devices...")
        self.usb_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        tk.Button(root, text="Refresh", command=self.refresh_usb_devices).grid(row=1, column=2, padx=5, pady=5)

        tk.Label(root, text="WARNING: All data on the selected USB will be erased!", fg="red").grid(row=2, column=0, columnspan=3, padx=5, pady=5)
        tk.Checkbutton(root, text="I understand and want to proceed", variable=self.confirmation).grid(row=3, column=0, columnspan=3, padx=5, pady=5)

        tk.Label(root, text="Progress:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_value, maximum=100, length=500)
        self.progress_bar.grid(row=4, column=1, columnspan=2, padx=5, pady=5)

        self.start_button = tk.Button(root, text="Start", command=self.start_process)
        self.start_button.grid(row=5, column=0, columnspan=3, pady=10)

        self.log_text = tk.Text(root, height=15, width=80, state="disabled")
        self.log_text.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

        # Initialize after GUI setup
        self.check_dependencies()
        self.refresh_usb_devices()

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update()

    def run_command(self, cmd, capture_output=False, silent=False, check=True):
        if not silent:
            self.log(f"Executing command: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True, check=check)
            if capture_output and result.stdout and not silent:
                self.log(f"Command output: {result.stdout.strip()}")
            if capture_output and result.stderr and not silent:
                self.log(f"Command stderr: {result.stderr.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            if not silent:
                self.log(f"Error: Command '{cmd}' failed with exit code {e.returncode}")
                if capture_output:
                    if e.stdout:
                        self.log(f"Command stdout: {e.stdout.strip()}")
                    if e.stderr:
                        self.log(f"Command stderr: {e.stderr.strip()}")
            raise
        except Exception as e:
            if not silent:
                self.log(f"Unexpected error in command '{cmd}': {str(e)}")
            raise

    def check_dependencies(self):
        self.log("Checking dependencies...")
        required_commands = ["lsblk", "parted", "mkfs.vfat", "mkfs.ntfs", "partprobe", "wipefs", "mount", "rsync"]
        for cmd in required_commands:
            if shutil.which(cmd) is None:
                messagebox.showerror("Error", f"Dependency '{cmd}' is not installed.\nInstall with: sudo apt install {self.get_package(cmd)}")
                self.root.destroy()
                return
        self.log("All dependencies are installed.")

    def get_package(self, cmd):
        packages = {
            "lsblk": "util-linux", "parted": "parted", "mkfs.vfat": "dosfstools",
            "mkfs.ntfs": "ntfs-3g", "partprobe": "parted", "wipefs": "util-linux",
            "mount": "util-linux", "rsync": "rsync"
        }
        return packages.get(cmd, cmd)

    def get_usb_devices(self):
        self.log("Detecting USB devices...")
        try:
            result = self.run_command("lsblk -d -o NAME,SIZE,TYPE,MODEL,TRAN,RM", capture_output=True, silent=True)
            devices = []
            for line in result.stdout.splitlines():
                if "usb" in line and "1" in line.split()[-1]:  # Check TRAN=usb and RM=1 (removable)
                    parts = line.split()
                    if len(parts) >= 6:
                        name, size, _, model = parts[:4]
                        devices.append(f"{name} ({size}, {model})")
            self.log(f"Found {len(devices)} removable USB device(s)")
            return devices if devices else ["No USB devices found"]
        except subprocess.CalledProcessError as e:
            self.log(f"Error detecting USB devices: {str(e)}")
            return ["Error detecting USB devices"]

    def refresh_usb_devices(self):
        self.log("Refreshing USB device list...")
        menu = self.usb_menu["menu"]
        menu.delete(0, "end")
        devices = self.get_usb_devices()
        for device in devices:
            menu.add_command(label=device, command=lambda value=device: self.usb_device.set(value))
        self.usb_device.set(devices[0] if devices else "No USB devices found")
        self.log("USB device list refreshed.")

    def browse_iso(self):
        self.log("Opening file dialog for ISO selection...")
        file_path = filedialog.askopenfilename(filetypes=[("ISO files", "*.iso")])
        if file_path:
            self.iso_path.set(file_path)
            self.log(f"Selected ISO: {file_path}")

    def validate_iso_file(self, iso_path):
        self.log(f"Validating ISO file: {iso_path}")
        if not os.path.isfile(iso_path):
            raise Exception(f"ISO file not found at {iso_path}")
        if not os.access(iso_path, os.R_OK):
            raise Exception(f"ISO file is not readable: {iso_path}")
        result = self.run_command(f"file {iso_path}", capture_output=True, silent=True)
        if "ISO 9660" not in result.stdout:
            raise Exception(f"{iso_path} is not a valid ISO file")

    def check_usb_writable(self, usb_device):
        self.log(f"Checking if /dev/{usb_device} is writable...")
        try:
            test_file = f"/dev/{usb_device}"
            if not os.access(test_file, os.W_OK):
                raise Exception(f"USB device /dev/{usb_device} is not writable")
            self.run_command(f"lsblk -o NAME /dev/{usb_device}", capture_output=True)
            self.log(f"USB device /dev/{usb_device} is accessible.")
        except Exception as e:
            raise Exception(f"Cannot access USB device /dev/{usb_device}: {str(e)}")

    def start_process(self):
        self.log("Starting USB creation process...")
        if not self.confirmation.get():
            messagebox.showwarning("Warning", "Please confirm you understand the USB will be erased.")
            self.log("Process aborted: Confirmation not checked.")
            return
        if not self.iso_path.get():
            messagebox.showerror("Error", "Please select a Windows ISO file.")
            self.log("Process aborted: No ISO file selected.")
            return
        usb_selection = self.usb_device.get()
        if "No USB devices found" in usb_selection or "Error" in usb_selection:
            messagebox.showerror("Error", "No valid USB device selected.")
            self.log("Process aborted: Invalid USB device selected.")
            return
        match = re.match(r"(\w+)", usb_selection)
        if not match:
            messagebox.showerror("Error", "Invalid USB device format.")
            self.log("Process aborted: Invalid USB device format.")
            return
        self.usb_device_name = match.group(1)
        if self.usb_device_name == "sda":
            if not messagebox.askyesno("Warning", f"Device /dev/sda is likely an internal drive. Continuing will erase ALL data on it. Are you sure you want to proceed?"):
                self.log("Process aborted: User canceled /dev/sda selection.")
                return
        if not os.path.exists(f"/dev/{self.usb_device_name}"):
            messagebox.showerror("Error", f"USB device /dev/{self.usb_device_name} does not exist.")
            self.log(f"Process aborted: USB device /dev/{self.usb_device_name} does not exist.")
            return
        try:
            self.validate_iso_file(self.iso_path.get())
            self.check_usb_writable(self.usb_device_name)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log(f"Process aborted: {str(e)}")
            return
        self.start_button.config(state="disabled")
        self.progress_value.set(0)
        self.log("Starting USB creation thread...")
        Thread(target=self.run_usb_creation, daemon=True).start()

    def run_usb_creation(self):
        try:
            self.log(f"Starting USB creation for /dev/{self.usb_device_name} with ISO {self.iso_path.get()}")
            self.progress_value.set(5)
            self.list_usb_devices()
            self.progress_value.set(7)
            self.confirm_usb_selection()
            self.progress_value.set(10)
            self.unmount_partitions()
            self.progress_value.set(20)
            self.wipe_filesystem()
            self.progress_value.set(30)
            self.create_partitions()
            self.progress_value.set(40)
            self.refresh_partitions()
            self.progress_value.set(50)
            self.format_partitions()
            self.progress_value.set(60)
            self.verify_partitions()
            self.progress_value.set(65)
            self.iso_mountpoint = self.mount_iso()
            self.progress_value.set(70)
            self.validate_iso()
            self.progress_value.set(75)
            self.usb_mountpoint = self.mount_usb_partitions()
            self.progress_value.set(80)
            self.copy_files()
            self.progress_value.set(90)
            self.verify_files()
            self.progress_value.set(95)
            self.sync_filesystems()
            self.progress_value.set(100)
            self.log("\nOperation completed successfully!")
            self.log(f"Windows installation media created on /dev/{self.usb_device_name}")
            messagebox.showinfo("Success", f"Bootable USB created successfully on /dev/{self.usb_device_name}!\n\n" +
                                "To ensure the Windows bootloader is installed on the internal drive:\n" +
                                "1. Set the internal drive as the first boot device in BIOS/UEFI.\n" +
                                "2. Disconnect other drives if possible.\n" +
                                "3. Install to unallocated space on the internal drive.")
        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", "Failed to create bootable USB. Check the log for details.")
        finally:
            self.log("Cleaning up resources...")
            self.cleanup()
            self.start_button.config(state="normal")
            self.log("Process ended.")

    def list_usb_devices(self):
        self.log("Listing USB devices...")
        result = self.run_command("lsblk -d -o NAME,SIZE,TYPE,MODEL,TRAN,RM", capture_output=True)
        self.log("\nUSB devices connected to the host:")
        self.log(result.stdout.strip())

    def confirm_usb_selection(self):
        self.log(f"Confirming USB selection: /dev/{self.usb_device_name}")
        self.log(f"\nWARNING: All data on /dev/{self.usb_device_name} will be erased!")
        self.log("Selected device details:")
        result = self.run_command(f"lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL /dev/{self.usb_device_name}", capture_output=True)
        self.log(result.stdout.strip())
        if not self.confirmation.get():
            raise Exception("User confirmation required.")

    def unmount_partitions(self):
        self.log(f"\nUnmounting any existing partitions on /dev/{self.usb_device_name}...")
        result = self.run_command(f"lsblk -ln -o NAME /dev/{self.usb_device_name}", capture_output=True, check=False)
        partitions = [line.strip() for line in result.stdout.splitlines() if re.match(rf"^{self.usb_device_name}[0-9]+$", line.strip())]
        for partition in partitions:
            if subprocess.run(f"mount | grep /dev/{partition}", shell=True, capture_output=True, text=True).returncode == 0:
                self.log(f"Unmounting /dev/{partition}...")
                self.run_command(f"umount /dev/{partition}")

    def wipe_filesystem(self):
        self.log("\nWiping existing filesystem signatures...")
        self.run_command(f"wipefs -a /dev/{self.usb_device_name}")

    def create_partitions(self):
        self.log(f"\nCreating new GPT partition table on /dev/{self.usb_device_name}...")
        self.run_command(f"parted -s /dev/{self.usb_device_name} mklabel gpt")
        self.log("\nCreating BOOT partition (1024 MiB, FAT32)...")
        self.run_command(f"parted -s /dev/{self.usb_device_name} mkpart primary fat32 1MiB 1025MiB")
        self.run_command(f"parted -s /dev/{self.usb_device_name} set 1 msftdata on")
        self.log("\nCreating INSTALL partition (remaining space, NTFS)...")
        self.run_command(f"parted -s /dev/{self.usb_device_name} mkpart primary ntfs 1025MiB 100%")
        self.run_command(f"parted -s /dev/{self.usb_device_name} set 2 msftdata on")

    def refresh_partitions(self):
        self.log("\nRefreshing partition table...")
        self.run_command(f"partprobe /dev/{self.usb_device_name}")
        time.sleep(2)
        if not os.path.exists(f"/dev/{self.usb_device_name}1") or not os.path.exists(f"/dev/{self.usb_device_name}2"):
            raise Exception(f"Partitions were not created correctly on /dev/{self.usb_device_name}")

    def format_partitions(self):
        self.log("\nFormatting BOOT partition as FAT32...")
        self.run_command(f"mkfs.vfat -F32 -n BOOT /dev/{self.usb_device_name}1")
        self.log("\nFormatting INSTALL partition as NTFS...")
        self.run_command(f"mkfs.ntfs -f -L INSTALL /dev/{self.usb_device_name}2")

    def verify_partitions(self):
        self.log("\nVerifying partition layout...")
        result = self.run_command(f"lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL /dev/{self.usb_device_name}", capture_output=True)
        self.log("Partition layout:")
        self.log(result.stdout.strip())

    def mount_iso(self):
        self.log(f"\nMounting Windows ISO: {self.iso_path.get()}")
        iso_mountpoint = tempfile.mkdtemp(prefix="winiso.")
        self.run_command(f"mount -o ro,loop {self.iso_path.get()} {iso_mountpoint}")
        self.log(f"ISO mounted at {iso_mountpoint}")
        return iso_mountpoint

    def validate_iso(self):
        self.log("Validating ISO contents...")
        required_paths = [
            f"{self.iso_mountpoint}/efi",
            f"{self.iso_mountpoint}/boot",
            f"{self.iso_mountpoint}/sources/install.wim"
        ]
        for path in required_paths:
            if not os.path.exists(path):
                raise Exception(f"Missing required path in ISO: {path}")
        self.log("ISO validation passed.")

    def mount_usb_partitions(self):
        self.log("\nMounting USB partitions...")
        usb_mountpoint = tempfile.mkdtemp(prefix="usbmount.")
        boot_dir = f"{usb_mountpoint}/boot"
        install_dir = f"{usb_mountpoint}/install"
        os.makedirs(boot_dir)
        os.makedirs(install_dir)
        self.run_command(f"mount /dev/{self.usb_device_name}1 {boot_dir}")
        self.run_command(f"mount /dev/{self.usb_device_name}2 {install_dir}")
        self.log(f"USB partitions mounted at {usb_mountpoint}")
        return usb_mountpoint

    def copy_files(self):
        self.log("\nStarting file copy operations...")
        self.log("\nCopying files to BOOT partition (excluding sources folder)...")
        self.run_command(f"rsync -rltD --no-owner --no-group --no-perms --exclude='sources/' --info=progress2 {self.iso_mountpoint}/ {self.usb_mountpoint}/boot/")
        self.log("\nCreating sources directory in BOOT partition...")
        os.makedirs(f"{self.usb_mountpoint}/boot/sources", exist_ok=True)
        if os.path.isfile(f"{self.iso_mountpoint}/sources/boot.wim"):
            self.log("\nCopying boot.wim to BOOT partition...")
            if shutil.which("pv"):
                self.run_command(f"pv {self.iso_mountpoint}/sources/boot.wim > {self.usb_mountpoint}/boot/sources/boot.wim")
            else:
                self.run_command(f"cp -v {self.iso_mountpoint}/sources/boot.wim {self.usb_mountpoint}/boot/sources/")
        else:
            raise Exception("boot.wim not found in ISO sources folder")
        self.log("\nCopying all files to INSTALL partition...")
        self.run_command(f"rsync -a --info=progress2 {self.iso_mountpoint}/ {self.usb_mountpoint}/install/")

    def verify_files(self):
        self.log("\nVerifying critical files...")
        critical_files = [
            f"{self.usb_mountpoint}/boot/sources/boot.wim",
            f"{self.usb_mountpoint}/install/sources/install.wim"
        ]
        for file in critical_files:
            if not os.path.isfile(file):
                raise Exception(f"Critical file missing: {file}")
        self.log("Critical files verified.")

    def sync_filesystems(self):
        self.log("\nSyncing filesystems...")
        self.run_command("sync")
        self.log("Filesystems synced.")

    def cleanup(self):
        if self.iso_mountpoint and os.path.isdir(self.iso_mountpoint) and subprocess.run(f"mountpoint -q {self.iso_mountpoint}", shell=True).returncode == 0:
            self.log(f"Unmounting ISO from {self.iso_mountpoint}...")
            self.run_command(f"umount {self.iso_mountpoint}")
            os.rmdir(self.iso_mountpoint)
        if self.usb_mountpoint and os.path.isdir(self.usb_mountpoint):
            if subprocess.run(f"mountpoint -q {self.usb_mountpoint}/boot", shell=True).returncode == 0:
                self.log(f"Unmounting USB boot from {self.usb_mountpoint}/boot...")
                self.run_command(f"umount {self.usb_mountpoint}/boot")
            if subprocess.run(f"mountpoint -q {self.usb_mountpoint}/install", shell=True).returncode == 0:
                self.log(f"Unmounting USB install from {self.usb_mountpoint}/install...")
                self.run_command(f"umount {self.usb_mountpoint}/install")
            shutil.rmtree(self.usb_mountpoint, ignore_errors=True)
        self.iso_mountpoint = None
        self.usb_mountpoint = None

if __name__ == "__main__":
    root = tk.Tk()
    app = WindowsUSBApp(root)
    root.mainloop()
