# Third-Party Licenses

This document lists the third-party software packages used in this project and their respective licenses.

## Direct Dependencies

### PaddleOCR (v3.2)
- **License**: Apache License 2.0
- **Repository**: https://github.com/PaddlePaddle/PaddleOCR
- **License Text**: https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE

### PyMuPDF (v1.26.5)
- **License**: GNU Affero General Public License v3.0 (AGPL-3.0)
- **Repository**: https://github.com/pymupdf/PyMuPDF
- **License Text**: https://github.com/pymupdf/PyMuPDF/blob/main/COPYING
- **Important Note**: AGPL-3.0 is a copyleft license. If you modify PyMuPDF or distribute this software, you may need to comply with AGPL-3.0 requirements.

### OpenCV-Python (v4.12.0.88)
- **License**: Apache License 2.0
- **Repository**: https://github.com/opencv/opencv-python
- **License Text**: https://github.com/opencv/opencv-python/blob/main/LICENSE.txt

### NumPy (v2.2.6)
- **License**: BSD 3-Clause License
- **Repository**: https://github.com/numpy/numpy
- **License Text**: https://github.com/numpy/numpy/blob/main/LICENSE.txt

### pikepdf (v9.11.0)
- **License**: Mozilla Public License 2.0 (MPL-2.0)
- **Repository**: https://github.com/pikepdf/pikepdf
- **License Text**: https://github.com/pikepdf/pikepdf/blob/main/LICENSE

### PaddlePaddle (v3.2)
- **License**: Apache License 2.0
- **Repository**: https://github.com/PaddlePaddle/Paddle
- **License Text**: https://github.com/PaddlePaddle/Paddle/blob/develop/LICENSE

## License Compatibility

The MIT license used for this project is generally compatible with:
- Apache License 2.0 (PaddleOCR, OpenCV-Python, PaddlePaddle)
- BSD 3-Clause License (NumPy)
- Mozilla Public License 2.0 (pikepdf)

**Important**: PyMuPDF uses AGPL-3.0, which is a copyleft license. If you plan to:
- Modify PyMuPDF source code
- Distribute this software as a service
- Create derivative works

You should review the AGPL-3.0 license terms carefully and ensure compliance.

## Additional Notes

This project uses pre-trained models from PaddleOCR. These models may have their own licensing terms. Please refer to the PaddleOCR documentation for model-specific licensing information.

## How to Verify Licenses

You can verify the licenses of installed packages using:

```bash
pip-licenses --format=markdown --output-file=LICENSES.md
```

Or manually check each package:

```bash
pip show <package_name>
```

## License Texts

Full license texts for all dependencies are typically included in their respective package distributions. You can find them in:
- Python site-packages directory
- Package repositories on GitHub/PyPI
- Official project websites

