from pathlib import Path
import hashlib
from datetime import datetime
from collections import defaultdict
import imagehash
from PIL import Image
from photo_organizer.metadata import get_photo_datetime

def md5sum(path: Path, block_size: int = 1 << 20) -> str:
    """分块读取文件，计算 MD5 摘要"""
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            h.update(chunk)
    return h.hexdigest()

def head_block(path: Path, length: int = 512) -> bytes:
    """读取文件前 length 字节（用于头部对比）"""
    with path.open("rb") as f:
        return f.read(length)
    
def perceptual_hash(path: Path) -> str:
    """计算图像的感知哈希（dHash）"""
    try:
        img = Image.open(path).convert("RGB")
        return str(imagehash.dhash(img))
    except Exception as e:
        print(f"[WARN] Cannot compute perceptual hash for {path.name}: {e}")
        return ""

class DigestIndex:
    def __init__(self):
        self.map = defaultdict(list)  # MD5 → list of (path, date)
        self.pmap = defaultdict(list) # pHash → list of path

    def add_md5(self, path: Path, digest: str, date: datetime):
        self.map[digest].append((path, date))

    def add_phash(self, path: Path):
        phash = perceptual_hash(path)
        if phash:
            self.pmap[phash].append(path)

    def get_deduplicated(self):
        results = []
        for _, files in self.map.items():
            if len(files) == 1:
                results.append((files[0][0], []))
                continue
            sorted_files = sorted(files, key=lambda x: x[1])
            keep = sorted_files[0][0]
            keep_head = head_block(keep)

            duplicates = []
            for f, _ in sorted_files[1:]:
                if f.stat().st_size != keep.stat().st_size:
                    continue
                if head_block(f) == keep_head:
                    duplicates.append(f)
                else:
                    print(f"[WARN] Same digest but head differs: {f.name}")
            results.append((keep, duplicates))
        return results

    def get_visual_duplicates_map(self):
        result = {}
        for _, paths in self.pmap.items():
            if len(paths) > 1:
                sorted_group = sorted(paths, key=lambda p: get_photo_datetime(p))
                keep = sorted_group[0]
                dupes = sorted_group[1:]
                result[keep] = dupes
        return result
