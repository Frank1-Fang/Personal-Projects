from PIL import Image
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from photo_organizer.metadata import get_photo_datetime

# 加载一个有 EXIF 的图片，另存为 PNG（Pillow 不保留 EXIF）
jpg_path = Path("sample_data/input/IMG_20250928_164432.jpg")
png_path = Path("sample_data/input/no_exif_test.png")

# 转换为 PNG
img = Image.open(jpg_path)
img.save(png_path)

# 用 get_photo_datetime() 测试新图片
dt = get_photo_datetime(png_path)

print(f"[INFO] {png_path.name} fallback 到文件创建时间：{dt}")
