from pathlib import Path
from PIL import Image
import piexif
import os
from datetime import datetime

def get_exif_datetime(path: Path) -> datetime | None:
    try:
        img = Image.open(path)
        exif_dict = piexif.load(img.info['exif'])
        dt_str = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if dt_str:
            return datetime.strptime(dt_str.decode(), "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"[WARN] EXIF not found or invalid for {path.name}: {e}")
        return None

def get_file_created_datetime(path: Path) -> datetime:
    return datetime.fromtimestamp(os.path.getctime(path))

# 测试读取 sample_data/input 目录
input_dir = Path("sample_data/input")
for img_path in input_dir.glob("*.[jJ][pP][gG]"):  # 匹配 jpg/JPG
    exif_time = get_exif_datetime(img_path)
    fs_time = get_file_created_datetime(img_path)
    print(f"{img_path.name}")
    print(f"   EXIF Time      : {exif_time}")
    print(f"   Created Time   : {fs_time}")
    print("-" * 40)
