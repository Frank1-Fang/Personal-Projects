from pathlib import Path
from datetime import datetime
import re

import re

def extract_source_hint(name: str) -> str:
    name = name.lower()

    # 中文识别
    if "微信图片" in name:
        return "wechat"
    elif "屏幕截图" in name:
        return "screenshot"

    # 英文标记识别
    elif "mmexport" in name:
        return "mmexport"
    elif "dcim" in name or "img" in name:
        return "dcim"
    elif "screenshot" in name:
        return "screenshot"
    elif "wechat" in name:
        return "wechat"
    
    # fallback
    else:
        return "file"


def build_new_filename(date: datetime, original_name: str, ext: str = ".jpg") -> str:
    """
    生成重命名后的新文件名：20250701-dcim-abc.jpg
    """
    ymd = date.strftime("%Y%m%d")
    hint = extract_source_hint(original_name)
    base_name = re.sub(r"[^\w\-]", "", Path(original_name).stem).lower()[:20]  # 清理非法字符（只要不是字母和'-'）并限制长度
    return f"{ymd}-{hint}-{base_name}{ext}"
