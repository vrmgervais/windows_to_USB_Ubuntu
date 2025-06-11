#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import time
import shutil
import platform
import distro
import threading

def check_and_install_dependencies():
    """Check and install required dependencies based on the Linux distribution."""
    packages = [
        "lsb-release", "parted", "ntfs-3g", "rsync",
        "curl", "p7zip-full", "udisks2", "dosfstools",
        "pv", "xterm", "python3-tk"
    ]
    package_manager = None
    install_cmd = None

    # Detect package manager
    dist = distro.id().lower()
    if dist in ["ubuntu", "debian", "pop"]:
        package_manager = "apt"
        install_cmd = ["sudo", "apt-get", "install", "-y"]
        update_cmd = ["sudo", "apt-get", "update"]
    elif dist in ["fedora"]:
        package_manager = "dnf"
        install_cmd = ["sudo", "dnf", "install", "-y"]
        update_cmd = ["sudo", "dnf", "check-update"]
    elif dist in ["arch"]:
        package_manager = "pacman"
        install_cmd = ["sudo", "pacman", "-S", "--noconfirm"]
        update_cmd = ["sudo", "pacman", "-Syu", "--noconfirm"]
    else:
        messagebox.showerror("Error", f"Unsupported distribution: {dist}")
        return False

    # Check if packages are installed
    missing_packages = []
    for pkg in packages:
        try:
            subprocess.run(["dpkg", "-l", pkg], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            missing_packages.append(pkg)

    if missing_packages:
        try:
            subprocess.run(update_cmd, check=True)
            subprocess.run(install_cmd + missing_packages, check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to install dependencies: {e}")
            return False
    return True

def select_iso():
    path = filedialog.askopenfilename(filetypes=[("ISO files", "*.iso")])
    if path:
        iso_entry.delete(0, tk.END)
        iso_entry.insert(0, path)

def list_usb_drives():
    result = subprocess.run(
        ["lsblk", "-dpno", "NAME,SIZE,MODEL"],
        stdout=subprocess.PIPE,
        text=True
    )
    drives = [line for line in result.stdout.strip().split("\n") if "/dev/sd" in line]
    return drives

def select_usb():
    drives = list_usb_drives()
    if not drives:
        messagebox.showerror("Error", "No USB drives found.")
        return
    drive = drives[0].split()[0]
    usb_entry.delete(0, tk.END)
    usb_entry.insert(0, drive)

def unmount_partitions(device):
    result = subprocess.run(["lsblk", "-lnpo", "NAME", device], stdout=subprocess.PIPE, text=True)
    for line in result.stdout.strip().split("\n")[1:]:
        subprocess.run(["sudo", "umount", line], check=False)

def create_partitions(device):
    subprocess.run(["sudo", "parted", device, "--script", "mklabel", "gpt"], check=True)
    subprocess.run(["sudo", "parted", device, "--script", "mkpart", "primary", "fat32", "1MiB", "1025MiB"], check=True)
    subprocess.run(["sudo", "parted", device, "--script", "set", "1", "boot", "on"], check=True)
    subprocess.run(["sudo", "parted", device, "--script", "mkpart", "primary", "ntfs", "1025MiB", "100%"], check=True)
    subprocess.run(["udevadm", "settle"])
    time.sleep(1)  # Reduced sleep time

def format_partitions(boot_part, install_part):
    subprocess.run(["sudo", "umount", boot_part], check=False)
    subprocess.run(["sudo", "umount", install_part], check=False)
    subprocess.run(["udevadm", "settle"])
    time.sleep(1)  # Reduced sleep time
    subprocess.run(["sudo", "mkfs.vfat", "-F32", "-n", "BOOT", boot_part], check=True)
    subprocess.run(["sudo", "mkfs.ntfs", "-f", "-L", "INSTALL", install_part], check=True)

def mount_iso(iso_path):
    subprocess.run(["sudo", "mkdir", "-p", "/mnt/iso"], check=False)
    subprocess.run(["sudo", "mount", "-o", "loop", iso_path, "/mnt/iso"], check=True)

def mount_usb_parts(boot_part, install_part):
    subprocess.run(["sudo", "mkdir", "-p", "/mnt/boot", "/mnt/install"], check=False)
    subprocess.run(["sudo", "mount", boot_part, "/mnt/boot"], check=True)
    subprocess.run(["sudo", "mount", install_part, "/mnt/install"], check=True)

def copy_with_rsync():
    """Use rsync for faster file copying with progress."""
    subprocess.run([
        "rsync", "-avh", "--progress", "/mnt/iso/", "/mnt/install/"
    ], check=True)

def copy_boot_wim():
    """Copy boot.wim in a separate thread for parallelization."""
    subprocess.run(["sudo", "mkdir", "-p", "/mnt/boot/sources"], check=False)
    subprocess.run(["sudo", "cp", "/mnt/iso/sources/boot.wim", "/mnt/boot/sources/"], check=True)

def cleanup():
    subprocess.run(["sync"])
    time.sleep(1)  # Reduced sleep time
    subprocess.run(["sudo", "umount", "/mnt/iso"], check=False)
    subprocess.run(["sudo", "umount", "/mnt/boot"], check=False)
    subprocess.run(["sudo", "umount", "/mnt/install"], check=False)
    subprocess.run(["sudo", "rm", "-rf", "/mnt/iso", "/mnt/boot", "/mnt/install"], check=False)

def create_bootable_usb():
    iso_path = iso_entry.get()
    usb_drive = usb_entry.get()

    if not iso_path or not usb_drive:
        messagebox.showerror("Error", "ISO path and USB drive are required.")
        return

    try:
        # Install dependencies if not already installed
        if not check_and_install_dependencies():
            return

        unmount_partitions(usb_drive)
        create_partitions(usb_drive)
        boot_part = usb_drive + "1"
        install_part = usb_drive + "2"
        format_partitions(boot_part, install_part)
        mount_iso(iso_path)
        mount_usb_parts(boot_part, install_part)

        # Run boot.wim copy in a separate thread
        boot_wim_thread = threading.Thread(target=copy_boot_wim)
        boot_wim_thread.start()

        # Copy main ISO content with rsync
        copy_with_rsync()

        # Wait for boot.wim copy to complete
        boot_wim_thread.join()

        cleanup()
        messagebox.showinfo("Success", "✅ Bootable USB created successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Something went wrong: {e}")

# Initialize GUI
root = tk.Tk()
root.title("Create Windows Bootable USB")
root.geometry("500x220")

tk.Label(root, text="ISO File:").pack(pady=(10,0))
iso_entry = tk.Entry(root, width=60)
iso_entry.pack()
tk.Button(root, text="Browse", command=select_iso).pack(pady=(0,10))

tk.Label(root, text="USB Drive (e.g. /dev/sdX):").pack()
usb_entry = tk.Entry(root, width=30)
usb_entry.pack()
tk.Button(root, text="Auto-Detect USB", command=select_usb).pack(pady=(0,10))

tk.Button(root, text="Create Bootable USB", command=create_bootable_usb, bg="green", fg="white").pack(pady=10)

# Check dependencies at startup
if not check_and_install_dependencies():
    root.destroy()
else:
    root.mainloop()