import PyInstaller.__main__
import os
import shutil

def build_executable():
    # Clean previous build
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("bootable-usb-creator.spec"):
        os.remove("bootable-usb-creator.spec")

    # PyInstaller arguments
    args = [
        "create_bootable_usb.py",
        "--onefile",
        "--name=bootable-usb-creator",
        "--hidden-import=distro",
        "--hidden-import=tkinter",
        "--collect-all=distro"
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    print("Executable created at: dist/bootable-usb-creator")

if __name__ == "__main__":
    build_executable()