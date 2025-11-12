@echo off
chcp 65001 >nul

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Install Python 3.8+ and add it to PATH.
    pause
    exit /b 1
)

echo Checking dependencies...
rem Required modules: fitz(PyMuPDF), opencv-python, numpy, paddleocr, paddlepaddle, pikepdf, tkinter
python -c "import fitz, cv2, numpy, paddleocr, paddle, pikepdf, tkinter" >nul 2>&1
if errorlevel 1 (
    echo Some dependencies are missing. Running install_deps.py...
    python Install\install_deps.py
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

echo Launching GUI...
pythonw.exe gui_windowsv2.py

if errorlevel 1 (
    echo Application failed to start. See messages above.
    pause
)
