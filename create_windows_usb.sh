#!/bin/bash

# Check if script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root or using sudo" >&2
    exit 1
fi

# Check if required arguments are provided
if [ $# -ne 2 ]; then
    echo "Error: Usage: $0 <iso_path> <usb_device>" >&2
    exit 1
fi

iso_path="$1"
usb_device="$2"

# Check if required commands are installed
required_commands=(lsblk parted mkfs.vfat mkfs.ntfs partprobe wipefs mount rsync pv)
for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: $cmd is not installed. Please install it and try again." >&2
        exit 1
    fi
done

# Initialize variables
iso_mountpoint=""
usb_mountpoint=""

# Function to clean up mounts on exit
cleanup() {
    if [ -n "$iso_mountpoint" ] && mountpoint -q "$iso_mountpoint"; then
        echo "Unmounting ISO from $iso_mountpoint..."
        umount "$iso_mountpoint"
        rmdir "$iso_mountpoint"
    fi
    if [ -n "$usb_mountpoint" ] && mountpoint -q "$usb_mountpoint"; then
        echo "Unmounting USB from $usb_mountpoint..."
        umount "$usb_mountpoint/boot" 2>/dev/null
        umount "$usb_mountpoint/install" 2>/dev/null
        rmdir "$usb_mountpoint"
    fi
}
trap cleanup EXIT

# Validate the selected device
if [ -z "$usb_device" ]; then
    echo "Error: No USB device specified." >&2
    exit 1
fi

if [ ! -b "/dev/$usb_device" ]; then
    echo "Error: /dev/$usb_device is not a valid block device." >&2
    exit 1
fi

# Validate ISO path
if [ ! -f "$iso_path" ]; then
    echo "Error: ISO file not found at $iso_path" >&2
    exit 1
fi

if ! file "$iso_path" | grep -q "ISO 9660"; then
    echo "Error: $iso_path doesn't appear to be a valid ISO file" >&2
    exit 1
fi

# Unmount any existing partitions
echo "Unmounting any existing partitions on /dev/$usb_device..."
partitions=$(lsblk -ln -o NAME "/dev/$usb_device" | grep -E "^${usb_device}[0-9]+$" || true)
if [ -n "$partitions" ]; then
    for partition in $partitions; do
        if mount | grep "/dev/$partition" >/dev/null; then
            echo "Unmounting /dev/$partition..."
            umount "/dev/$partition" || {
                echo "Error: Failed to unmount /dev/$partition" >&2
                exit 1
            }
        fi
    done
fi

# Wipe existing filesystem signatures
echo "Wiping existing filesystem signatures..."
wipefs -a "/dev/$usb_device" || {
    echo "Error: Failed to wipe filesystem signatures" >&2
    exit 1
}

# Create GPT partition table
echo "Creating new GPT partition table on /dev/$usb_device..."
parted -s "/dev/$usb_device" mklabel gpt || {
    echo "Error: Failed to create GPT partition table." >&2
    exit 1
}

# Create BOOT partition (1024 MiB, FAT32, msftdata type)
echo "Creating BOOT partition (1024 MiB, FAT32)..."
parted -s "/dev/$usb_device" mkpart primary fat32 1MiB 1025MiB || {
    echo "Error: Failed to create BOOT partition." >&2
    exit 1
}

# Set partition type to Microsoft basic data (not ESP)
parted -s "/dev/$usb_device" set 1 msftdata on || {
    echo "Error: Failed to set partition type on BOOT partition." >&2
    exit 1
}

# Create INSTALL partition (remainder, NTFS)
echo "Creating INSTALL partition (remaining space, NTFS)..."
parted -s "/dev/$usb_device" mkpart primary ntfs 1025MiB 100% || {
    echo "Error: Failed to create INSTALL partition." >&2
    exit 1
}

# Set partition type to Microsoft basic data
parted -s "/dev/$usb_device" set 2 msftdata on || {
    echo "Error: Failed to set partition type on INSTALL partition." >&2
    exit 1
}

# Refresh partition table
echo "Refreshing partition table..."
partprobe "/dev/$usb_device" || {
    echo "Error: Failed to refresh partition table." >&2
    exit 1
}
sleep 2  # Give the system time to register partitions

# Verify partitions exist
if [ ! -b "/dev/${usb_device}1" ] || [ ! -b "/dev/${usb_device}2" ]; then
    echo "Error: Partitions were not created correctly." >&2
    exit 1
fi

# Format BOOT partition
echo "Formatting BOOT partition as FAT32..."
mkfs.vfat -F32 -n BOOT "/dev/${usb_device}1" || {
    echo "Error: Failed to format BOOT partition as FAT32." >&2
    exit 1
}

# Format INSTALL partition
echo "Formatting INSTALL partition as NTFS..."
mkfs.ntfs -f -L INSTALL "/dev/${usb_device}2" || {
    echo "Error: Failed to format INSTALL partition as NTFS." >&2
    exit 1
}

# Final verification
echo "Partitioning completed successfully! Final layout:"
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL "/dev/$usb_device"

# Create mount point and mount ISO
iso_mountpoint=$(mktemp -d /tmp/winiso.XXXXXX)
echo "Mounting Windows ISO to $iso_mountpoint..."
mount -o ro,loop "$iso_path" "$iso_mountpoint" || {
    echo "Error: Failed to mount ISO file" >&2
    exit 1
}

# Validate ISO contents
if [ ! -d "$iso_mountpoint/efi" ] || [ ! -d "$iso_mountpoint/boot" ] || [ ! -f "$iso_mountpoint/sources/install.wim" ]; then
    echo "Error: ISO does not contain expected Windows installation files (missing efi, boot, or sources/install.wim)" >&2
    umount "$iso_mountpoint"
    rmdir "$iso_mountpoint"
    exit 1
fi

# Mount USB partitions
usb_mountpoint=$(mktemp -d /tmp/usbmount.XXXXXX)
echo "Mounting USB partitions..."
mkdir -p "${usb_mountpoint}/boot"
mount "/dev/${usb_device}1" "${usb_mountpoint}/boot" || {
    echo "Error: Failed to mount BOOT partition" >&2
    exit 1
}

mkdir -p "${usb_mountpoint}/install"
mount "/dev/${usb_device}2" "${usb_mountpoint}/install" || {
    echo "Error: Failed to mount INSTALL partition" >&2
    exit 1
}

# File Copy Operations
echo "Starting file copy operations..."

# 1) Copy all files except sources folder to BOOT partition
echo "Copying files to BOOT partition (excluding sources folder)..."
rsync -a --exclude='sources/' --info=progress2 "$iso_mountpoint/" "${usb_mountpoint}/boot/"

# 2) Create sources folder in BOOT partition
echo "Creating sources directory in BOOT partition..."
mkdir -p "${usb_mountpoint}/boot/sources"

# 3) Copy boot.wim from ISO sources to USB BOOT sources
if [ -f "$iso_mountpoint/sources/boot.wim" ]; then
    echo "Copying boot.wim to BOOT partition..."
    if command -v pv >/dev/null 2>&1; then
        pv "$iso_mountpoint/sources/boot.wim" > "${usb_mountpoint}/boot/sources/boot.wim"
    else
        cp -v "$iso_mountpoint/sources/boot.wim" "${usb_mountpoint}/boot/sources/"
    fi
else
    echo "Error: boot.wim not found in ISO sources folder" >&2
    exit 1
fi

# 4) Copy all files to INSTALL partition
echo "Copying all files to INSTALL partition..."
rsync -a --info=progress2 "$iso_mountpoint/" "${usb_mountpoint}/install/"

# Verify critical files were copied
echo "Verifying critical files..."
critical_files=(
    "${usb_mountpoint}/boot/sources/boot.wim"
    "${usb_mountpoint}/install/sources/install.wim"
)

for file in "${critical_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: Critical file missing - $file" >&2
        exit 1
    fi
done

# Sync filesystems
echo "Syncing filesystems..."
sync

echo "Operation completed successfully!"
echo "Windows installation media has been created on /dev/${usb_device}"
echo "BOOT partition: /dev/${usb_device}1"
echo "INSTALL partition: /dev/${usb_device}2"
echo "IMPORTANT: To ensure the Windows bootloader is installed on the internal drive:"
echo "1. Before starting the Windows installation, enter your BIOS/UEFI settings."
echo "2. Set the internal drive as the first boot device."
echo "3. If possible, disconnect all other drives except the target internal drive."
echo "4. During installation, delete all partitions on the internal drive and select the unallocated space to let Windows create the necessary partitions."
