from pathlib import Path
from PIL import Image
import piexif
import os
from datetime import datetime
from typing import Optional

def get_photo_datetime(path: Path) -> Optional[datetime]:
    """从 EXIF 中提取 DateTimeOriginal，否则 fallback 到文件创建时间"""
    try:
        img = Image.open(path)
        exif_dict = piexif.load(img.info.get("exif", b""))
        dt_raw = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
        if dt_raw:
            return datetime.strptime(dt_raw.decode(), "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        pass
    
    # fallback
    return datetime.fromtimestamp(os.path.getctime(path))
