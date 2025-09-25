from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from photo_organizer.metadata import get_photo_datetime
from photo_organizer.digest import md5sum, DigestIndex

input_dir = Path("sample_data/input")
index = DigestIndex()

for path in input_dir.glob("*.*"):
    dt = get_photo_datetime(path)
    digest = md5sum(path)
    index.add_md5(path, digest, dt)
    index.add_phash(path)

print("去重判断（保留 + 重复）")
for keep, dupes in index.get_deduplicated():
    print(f"KEEP: {keep.name}")
    for d in dupes:
        print(f"----REPEAT: {d.name}")