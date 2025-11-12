import subprocess
import sys
import os
from pathlib import Path

# Импортируем список пакетов из install_deps.py
from install_deps import REQUIRED_PACKAGES

def create_localpackages_dir():
    """Create LocalPackages directory if it does not exist"""
    localpackages_dir = Path("LocalPackages")
    localpackages_dir.mkdir(exist_ok=True)
    print(f"📁 Created directory: {localpackages_dir.absolute()}")
    return localpackages_dir

def run_cmd(cmd: list[str], cwd=None):
    """Run a command and print output"""
    try:
        print(f"🔄 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"📤 Output: {result.stdout}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Exit code: {e.returncode}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        sys.exit(1)

def download_packages():
    """Download all packages and dependencies to local directory"""
    localpackages_dir = create_localpackages_dir()
    
    print(f"\n📦 Starting package download into: {localpackages_dir.absolute()}")
    
    # Build full list of packages with versions
    packages_list = []
    for pkg, version in REQUIRED_PACKAGES.items():
        packages_list.append(f"{pkg}=={version}")
    
    # Download all packages and dependencies
    print(f"\n🔄 Downloading: {', '.join(packages_list)}")
    
    # Command to download packages and all dependencies
    download_cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(localpackages_dir),
        "--prefer-binary"  # Prefer binary wheels, allow source
    ] + packages_list
    
    try:
        run_cmd(download_cmd)
        print(f"\n✅ All packages downloaded to: {localpackages_dir.absolute()}")
    except Exception as e:
        print(f"❌ Download error: {e}")
        # Try a simpler command
        print("🔄 Trying simplified command...")
        simple_cmd = [
            sys.executable, "-m", "pip", "download",
            "--dest", str(localpackages_dir)
        ] + packages_list
        run_cmd(simple_cmd)

def list_downloaded_packages():
    """List downloaded files"""
    localpackages_dir = Path("LocalPackages")
    if localpackages_dir.exists():
        files = list(localpackages_dir.glob("*.whl")) + list(localpackages_dir.glob("*.tar.gz"))
        if files:
            print(f"\n📋 Downloaded files ({len(files)}):")
            for file in sorted(files):
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"  📄 {file.name} ({size_mb:.2f} MB)")
        else:
            print("\n⚠️ No package files found in LocalPackages")
    else:
        print("\n⚠️ LocalPackages directory does not exist")

def create_requirements_file():
    """Create requirements.txt from downloaded packages"""
    localpackages_dir = Path("LocalPackages")
    requirements_file = localpackages_dir / "requirements.txt"
    
    with open(requirements_file, 'w', encoding='utf-8') as f:
        f.write("# Requirements for installing from local packages\n")
        f.write("# Generated automatically\n\n")
        for pkg, version in REQUIRED_PACKAGES.items():
            f.write(f"{pkg}=={version}\n")
    
    print(f"📄 Created requirements.txt: {requirements_file.absolute()}")

def main():
    """Main entry point"""
    print("🚀 Downloading packages and dependencies to local folder\n")
    
    # Ensure pip is available
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ pip not found. Install pip and try again.")
        sys.exit(1)
    
    # Download packages
    download_packages()
    
    # Show downloaded files
    list_downloaded_packages()
    
    # Create requirements.txt
    create_requirements_file()
    
    print(f"\n✅ All operations completed!")
    print(f"📁 Packages saved to: {Path('LocalPackages').absolute()}")
    print(f"💡 To install from local packages use:")
    print(f"   pip install --find-links LocalPackages -r LocalPackages/requirements.txt")

if __name__ == "__main__":
    main()
