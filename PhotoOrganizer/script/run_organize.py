import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from photo_organizer.organizer import organize_photos

def main():
    parser = argparse.ArgumentParser(description=(
        "Organize photos by EXIF or file creation time, "
        "remove exact duplicates via MD5 hash, "
        "detect visual duplicates via perceptual hash, "
        "and rename files with structured filenames."
    ))
    parser.add_argument("--input", required=True, help="Path to input folder with images")
    parser.add_argument("--output", required=True, help="Path to output folder for organized photos")
    parser.add_argument("--duplicates", required=True, help="Path to folder to store duplicates")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    duplicate_dir = Path(args.duplicates)

    duplicate_dir.mkdir(parents=True, exist_ok=True)

    organize_photos(input_dir, output_dir, duplicate_dir)

if __name__ == "__main__":
    main()
