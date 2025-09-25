# organizer.py
from pathlib import Path
import shutil
from typing import Iterable, Dict, List, Optional
import os

from photo_organizer.metadata import get_photo_datetime
from photo_organizer.digest import md5sum, DigestIndex
from photo_organizer.renamer import build_new_filename


# ---------- 基础工具 ----------

def _is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def files_same(a: Path, b: Path) -> bool:
    """快速判断两文件是否相同：先比大小，相同则比 MD5。"""
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        # 大小一样再算 MD5，避免无谓开销
        return md5sum(a) == md5sum(b)
    except Exception:
        return False


def unique_target_path(target: Path) -> Path:
    """
    若目标已存在，则在文件名后追加 -1, -2, ...，直到找到一个不存在的路径。
    """
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    i = 1
    while True:
        cand = target.with_name(f"{stem}-{i}{suffix}")
        if not cand.exists():
            return cand
        i += 1


def resolve_target_for_copy(src: Path, dst_folder: Path, dst_name: str) -> Optional[Path]:
    """
    生成复制目标路径（幂等）：
    - 若 dst_folder/dst_name 不存在：直接返回该路径；
    - 若已存在且内容相同：返回 None（跳过复制）；
    - 若已存在但内容不同：返回追加 -1/-2… 的唯一路径。
    """
    dst_folder.mkdir(parents=True, exist_ok=True)
    target = dst_folder / dst_name
    if target.exists():
        if files_same(src, target):
            # 完全一样 → 跳过
            return None
        # 不同 → 生成唯一名称
        return unique_target_path(target)
    return target


def iter_images(input_dir: Path, exts: Iterable[str], exclude: Iterable[Path]) -> List[Path]:
    """
    递归获取输入目录下的所有图片（大小写不敏感），并排除 exclude 列表中的子树。
    """
    exts = {e.lower() for e in exts}
    exclude = [p.resolve() for p in exclude]
    results = []
    for p in input_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue
        # 排除 output 与 duplicates（避免二次扫描产物）
        if any(_is_under(p, ex) for ex in exclude):
            continue
        results.append(p)
    return results


# ---------- 主流程 ----------

def organize_photos(input_dir: Path, output_dir: Path, duplicate_dir: Path, progress_callback=None):
    """
    Phase 1: 构建 MD5 索引（精确去重候选）
    Phase 2: 精确去重 & 输出“主图”；重复图移动到 duplicates/
    Phase 3: 对所有主图计算感知哈希（视觉去重）
    Phase 4: 视觉去重（保留拍摄时间最早者），其余移入 duplicates/
    """
    visual_dupe_map = {}

    review_groups = []  # 新增：用于 GUI 回顾

    # 目录规范化
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    duplicate_dir = duplicate_dir.resolve()

    # 递归遍历图片，排除 output_dir 与 duplicate_dir
    all_images = iter_images(
        input_dir,
        exts=(".jpg", ".jpeg", ".png"),
        exclude=[output_dir, duplicate_dir],
    )
    print(f"[INFO] Found {len(all_images)} images in {input_dir}")
    
    index = DigestIndex()

    # 映射：原始路径 -> 实际输出路径（便于视觉去重时回收）
    output_map: Dict[Path, Path] = {}

    # 统计
    stat_total = len(all_images)
    stat_kept_md5 = 0
    stat_dupe_md5 = 0
    stat_dupe_visual = 0
    stat_skip_same = 0  # 幂等跳过次数（同名同内容）

    # ---------- 累计百分比进度条配置 ----------
    WEIGHTS = {"md5": 0.40, "copy": 0.40, "phash": 0.10, "visual": 0.10}
    ORDER = ["md5", "copy", "phash", "visual"]
    prefix = {}
    acc = 0.0
    for ph in ORDER:
        prefix[ph] = acc
        acc += WEIGHTS[ph]

    def report(phase: str, done: int, total: int):
        """把各阶段进度折算到 0..100 的累计百分比"""
        if not progress_callback or total <= 0:
            return
        frac = min(max(done / total, 0.0), 1.0)  # 0..1
        percent = int(round((prefix[phase] + WEIGHTS[phase] * frac) * 100))
        percent = max(0, min(100, percent))
        progress_callback(percent)

    # -----------------------------
    # Phase 1: 构建 MD5 索引
    # -----------------------------
    n_md5_total = len(all_images)
    n_md5_done = 0

    for path in all_images:
        try:
            date = get_photo_datetime(path)
            digest = md5sum(path)
            index.add_md5(path, digest, date)
        except Exception as e:
            print(f"[ERROR] Failed to process MD5 for {path}: {e}")
    
        n_md5_done += 1
        report("md5", n_md5_done, n_md5_total)

    # -----------------------------
    # Phase 2: 精确去重（输出主图）
    # -----------------------------
    md5_keep_paths: List[Path] = []
    dedup_groups = index.get_deduplicated()
    n_copy_total = len(dedup_groups)
    n_copy_done = 0

    for keep_path, dupes in index.get_deduplicated():
        try:
            date = get_photo_datetime(keep_path)
            y, m = date.year, date.month
            new_name = build_new_filename(date, keep_path.name, keep_path.suffix.lower())
            target_folder = output_dir / f"{y:04d}" / f"{m:02d}"

            # 幂等：若已有同名同内容 → 跳过；否则按需生成唯一文件名
            target_path = resolve_target_for_copy(keep_path, target_folder, new_name)
            if target_path is None:
                stat_skip_same += 1
                # 已经存在且内容一致，不再记录到 output_map（但它确实在输出目录）
                print(f"[SKIP] already organized: {keep_path.name} → {y:04d}/{m:02d}/{new_name}")

            else:
                shutil.copy2(keep_path, target_path)
                output_map[keep_path] = target_path
                stat_kept_md5 += 1
                print(f"[OK] {keep_path.name} → {target_path.relative_to(output_dir)}")

            # 重复图移动到 duplicates（同样做幂等判断）
            for dup_path in dupes:
                dup_target = resolve_target_for_copy(dup_path, duplicate_dir, dup_path.name)

                if dup_target is None:
                    stat_skip_same += 1
                    print(f"[SKIP] duplicate already saved: {dup_path.name}")

                else:
                    shutil.copy2(dup_path, dup_target)
                    stat_dupe_md5 += 1
                    print(f"[DUPLICATE] {dup_path.name} → {dup_target.relative_to(duplicate_dir)}")
            
            # 新增：为 GUI 回顾收集 MD5 重复分组
            if dupes:
                keep_output_path = output_map.get(keep_path)
                if keep_output_path is None:
                    keep_output_path = (output_dir / f"{y:04d}" / f"{m:02d}" / new_name)
                group = {
                    "kind": "md5",
                    "keep": str(keep_output_path),
                    "keep_src": str(keep_path),
                    "dupes": []
                }
                for dup_path in dupes:
                    # 推断 duplicates 内的展示路径；幂等跳过时用默认位置
                    dup_target = resolve_target_for_copy(dup_path, duplicate_dir, dup_path.name)
                    if dup_target is None:
                        dup_target = duplicate_dir / dup_path.name
                    group["dupes"].append(str(dup_target))
                review_groups.append(group)

            # 记录“主图”用于视觉去重
            md5_keep_paths.append(keep_path)

        except Exception as e:
            print(f"[ERROR] Failed to process main photo {keep_path.name}: {e}")
        
        n_copy_done += 1
        report("copy", n_copy_done, n_copy_total)

        

    # -----------------------------
    # Phase 3: 对 MD5 主图做感知哈希
    # -----------------------------
    n_phash_total = len(md5_keep_paths)
    n_phash_done = 0

    for path in md5_keep_paths:
        try:
            index.add_phash(path)
        except Exception as e:
            print(f"[ERROR] Failed to process pHash for {path.name}: {e}")
        
        n_phash_done += 1
        report("phash", n_phash_done, n_phash_total)

    # -----------------------------
    # Phase 4: 视觉去重
    # -----------------------------
    visual_groups = list(visual_dupe_map.items())
    n_visual_total = len(visual_groups)
    n_visual_done = 0

    visual_dupe_map = index.get_visual_duplicates_map()
    for keep, dupes in visual_dupe_map.items():
        # 在同组中按“拍摄时间”排序，选择最早的为保留
        all_group = [keep] + dupes
        sorted_group = sorted(all_group, key=lambda p: get_photo_datetime(p))
        new_keep = sorted_group[0]

        for p in all_group:
            if p == new_keep:
                continue

            # 若该图片已在输出目录里（作为主图），删除输出文件并从映射中移除
            out = output_map.pop(p, None)
            if out:
                try:
                    out.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[WARN] Failed to delete existing output file: {out} - {e}")

            # 将其放入 duplicates（幂等判断）
            dup_target = resolve_target_for_copy(p, duplicate_dir, p.name)
            if dup_target is None:
                stat_skip_same += 1
                print(f"[SKIP] Visual duplicate already saved: {p.name}")
            else:
                try:
                    shutil.copy2(p, dup_target)
                    stat_dupe_visual += 1
                    print(f"[VISUAL DUPLICATE] {p.name} → {dup_target.relative_to(duplicate_dir)}")
                except Exception as e:
                    print(f"[ERROR] Failed to move visual duplicate {p.name}: {e}")

        print(f"[VISUAL KEEP] {new_keep.name}")

        # 新增：为 GUI 回顾收集视觉重复分组
        group = {
            "kind": "visual",
            "keep": str(output_map.get(new_keep, output_dir / f"{get_photo_datetime(new_keep).year:04d}" / f"{get_photo_datetime(new_keep).month:02d}" / build_new_filename(get_photo_datetime(new_keep), new_keep.name, new_keep.suffix.lower()))),
            "keep_src": str(new_keep),
            "dupes": []
        }
        for p in all_group:
            if p == new_keep: 
                continue
            # 和上面逻辑一致，推断或记录 duplicates 内的目标展示路径
            dup_target = resolve_target_for_copy(p, duplicate_dir, p.name)
            if dup_target is None:
                dup_target = duplicate_dir / p.name
            group["dupes"].append(str(dup_target))
        review_groups.append(group)

        n_visual_done += 1
        report("visual", n_visual_done, n_visual_total)

    if progress_callback:
        progress_callback(100)
    
    # -----------------------------
    # Summary
    # -----------------------------
    print(
        "[SUMMARY] "
        f"total={stat_total}, "
        f"kept_md5={stat_kept_md5}, "
        f"dupe_md5={stat_dupe_md5}, "
        f"dupe_visual={stat_dupe_visual}, "
        f"skipped_same={stat_skip_same}, "
        f"output_dir={output_dir}, duplicates_dir={duplicate_dir}"
    )

    return review_groups
