"""
还原 PowerShell 重定向弄乱的中文输出。

问题出在 `python xxx.py 2>&1 | Out-File -Encoding utf8 out.txt` 这条链路：

    1. python 按 UTF-8 往 stdout 写字节
    2. PowerShell 收到字节后，用**系统编码（GBK/cp936）**把它解码成字符串
       —— 这一步就糊了
    3. Out-File 再把那个乱码字符串按 UTF-8 写进文件

于是文件里躺着的是「乱码字符串的 UTF-8 编码」，用任何 UTF-8 编辑器打开都是乱码。

本脚本做第 2 步的逆运算（UTF-8 解码 → GBK 编码 → UTF-8 解码），
并且**绕开 PowerShell 直接写文件**，避免再次被污染。

用法：
    python tools/fix_ps_output_encoding.py <源文件> <目标文件>
"""

import sys
from pathlib import Path


def recover(raw: bytes) -> str:
    """把「GBK 误解过的 UTF-8」还原成正常文本。"""
    if raw.startswith(b"\xef\xbb\xbf"):  # 去掉 BOM
        raw = raw[3:]
    mangled = raw.decode("utf-8", errors="replace")
    # 逆运算：编回 GBK 就得到 python 当初写的原始 UTF-8 字节
    original = mangled.encode("gbk", errors="replace")
    return original.decode("utf-8", errors="replace")


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: python tools/fix_ps_output_encoding.py <源文件> <目标文件>")
        return 1

    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = recover(src.read_bytes())
    dst.write_text(text, encoding="utf-8")
    print(f"OK  {src.name} -> {dst.name}  ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
