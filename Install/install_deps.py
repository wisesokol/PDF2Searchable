import subprocess
import sys
import os
from pathlib import Path

# Required packages and versions
REQUIRED_PACKAGES = {
    "paddleocr": "3.2",
    "PyMuPDF": "1.26.5",
    "numpy": "2.2.6",
    "opencv-python": "4.12.0.88",
    "pikepdf": "9.11.0",
    "paddlepaddle": "3.2",
    }


def run_cmd(cmd: list[str]):
    """Run a command and exit on failure"""
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Exit code: {e.returncode}")
        sys.exit(1)


def ensure_pip():
    """Ensure pip is installed"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("⚠️ pip not found, installing...")
        run_cmd([sys.executable, "-m", "ensurepip"])
        run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])


def check_local_packages():
    """Check if local packages exist"""
    # Get path relative to this script's directory
    script_dir = Path(__file__).parent
    localpackages_dir = script_dir / "LocalPackages"
    if localpackages_dir.exists():
        files = list(localpackages_dir.glob("*.whl")) + list(localpackages_dir.glob("*.tar.gz"))
        return len(files) > 0, localpackages_dir
    return False, None

def install_packages_from_local(localpackages_dir):
    """Install packages from local directory"""
    print(f"\n📦 Installing packages from local directory: {localpackages_dir.absolute()}")
    
    # Build package list with versions
    packages_list = []
    for pkg, version in REQUIRED_PACKAGES.items():
        packages_list.append(f"{pkg}=={version}")
    
    # Install from local directory
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--find-links", str(localpackages_dir),
        "--no-index",  # Не использовать PyPI
        "--upgrade"
    ] + packages_list
    
    print(f"🔄 Command: {' '.join(cmd)}")
    run_cmd(cmd)

def install_packages_from_pypi():
    """Install packages from PyPI"""
    print("\n📦 Installing packages from PyPI...")
    for pkg, version in REQUIRED_PACKAGES.items():
        print(f"\n📦 Installing {pkg}=={version} ...")
        run_cmd([sys.executable, "-m", "pip", "install", f"{pkg}=={version}", "--upgrade"])

def install_packages():
    """Install all required libraries with source selection"""
    # Check for local packages
    has_local, localpackages_dir = check_local_packages()
    
    if has_local:
        print(f"\n🔍 Local packages found in: {localpackages_dir.absolute()}")
        print("Choose installation source:")
        print("1. Install from LocalPackages directory")
        print("2. Install from PyPI (internet)")
        
        while True:
            choice = input("\nEnter number (1 or 2): ").strip()
            if choice == "1":
                install_packages_from_local(localpackages_dir)
                break
            elif choice == "2":
                install_packages_from_pypi()
                break
            else:
                print("❌ Invalid choice. Enter 1 or 2.")
    else:
        print("\n📦 No local packages found, installing from PyPI...")
        install_packages_from_pypi()


def verify_installation():
    """Verify installed packages"""
    print("\n🔍 Checking installed versions:")
    for pkg in REQUIRED_PACKAGES.keys():
        try:
            import importlib.metadata as importlib_metadata
            ver = importlib_metadata.version(pkg)
            print(f"✅ {pkg} — version {ver}")
        except Exception:
            print(f"⚠️ {pkg} is not installed or not found.")


if __name__ == "__main__":
    print("🚀 Installing dependencies for the PaddleOCR environment\n")
    ensure_pip()
    install_packages()
    verify_installation()
    print("\n✅ All operations completed.")
