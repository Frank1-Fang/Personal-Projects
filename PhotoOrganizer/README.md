# PhotoOrganizer

A Python tool to organize photos by creation date, detect duplicates using MD5 and perceptual hash (pHash), and rename files based on source and timestamp.

---

## Features

- Organize images into folders by year and month
- Extract creation time via EXIF metadata (fallback to filesystem timestamp)
- Detect exact duplicates using MD5 hash
- Detect visual duplicates using perceptual hash (dHash)
- Rename images using structured filenames (e.g. `20250801-dcim-img_20250701.jpg`)
- Separate folder for duplicates

---

## Project Structure
```
PhotoOrganizer/
├── src/            # Core logic: EXIF, hashing, renaming, organizing
├── script/         # CLI entry
├── gui_app.py      # PySide6 GUI
├── sample_data/    # Example input/output files
├── tests/          # Manual test scripts
├── requirements.txt
└── README.md
```
---

## Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run from command line
You can specify any valid folder paths for input, output, and duplicates. For example:
```bash
python script/run_organize.py \
  --input /path/to/your/raw_photos \
  --output /path/to/organized_photos \
  --duplicates /path/to/duplicates
```
Or use the included sample data:
```bash
python script/run_organize.py \
  --input sample_data/input \
  --output sample_data/output \
  --duplicates sample_data/duplicates
```
The input directory must exist and contain supported image files (`.jpg`, `.jpeg`, `.png`, etc.).
The output and duplicate directories will be created automatically if they don't exist.

### 3. Output structure
Organized photos will be placed into folders by year and month, with meaningful filenames:
```
output/
├── 2025/
│   └── 09/
│       ├── 20250928-dcim-img_20250928_164432.jpg
│       └── 20250929-screenshot-屏幕截图2025-09-28165416.png
```
Duplicate files will be moved to:
```
duplicates/
```
Each filename includes the photo date, source type, and a short version of the original name to help with sorting and identification.

---

## CLI Parameters

| Argument       | Description                      | Required |
| -------------- | -------------------------------- | -------- |
| `--input`      | Path to folder containing images | ✅        |
| `--output`     | Path to save organized files     | ✅        |
| `--duplicates` | Path to store duplicate files    | ✅        |

---

## Supported Formats
- `.jpg`, `.jpeg`, `.png`

- Automatically recognizes:

    - WeChat: 微信图片_\*.jpg

    - Screenshots: 屏幕截图 \*.png, Screenshot\*.png

    - DCIM: IMG_\*.jpg, etc.

- You can extend this in `renamer.py > extract_source_hint()`.

---

## Tests
This project provides several simple test scripts in the `tests/` folder to verify core features.

Run them manually using:

```bash
python tests/test_digest.py
python tests/test_exif.py
python tests/test_fallback_png.py
```

Test Description:
| Script                 | Purpose                                                   |
| ---------------------- | --------------------------------------------------------- |
| `test_digest.py`       | Build MD5 and pHash index to detect duplicates            |
| `test_exif.py`         | Print EXIF datetime vs. fallback file creation datetime   |
| `test_fallback_png.py` | Verify PNG fallback to file system time if no EXIF exists |
- Note: These are plain test scripts and do not require pytest. You can run them directly.

---

## Requirements

This project relies on the following Python packages:
- ImageHash 4.3.2
- iniconfig 2.1.0
- numpy 2.3.1
- packaging 25.0
- piexif 1.1.3
- pillow 11.3.0
- pluggy 1.6.0
- Pygments 2.19.2
- PySide6 6.9.2
- PySide6_Addons 6.9.2
- PyWavelets 1.8.0
- scipy 1.16.0
- shiboken6 6.9.2
- tqdm 4.67.1

