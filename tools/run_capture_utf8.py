"""在 Python 内部把 stdout / stderr 重定向到 UTF-8 文件，再运行目标脚本。

为什么要这么绕：
    让 PowerShell 去接 python 的输出（`python x.py | Out-File` 或 `> file`），
    PowerShell 会先用系统编码（GBK / cp936）解码 python 写出的 UTF-8 字节，
    再按 UTF-8 写出，落盘的就是「乱码字符串」；而且 GBK 解码产生的替换字符
    不可逆，事后再怎么转码都救不回来。
    在 Python 内部重定向就没有中间那一层解码，中文原样落盘。

用法：
    <venv>\\Scripts\\python.exe tools\\run_capture_utf8.py <目标脚本> <输出文件> [脚本参数...]

例：
    .venv\\Scripts\\python.exe tools\\run_capture_utf8.py chapter6/autogen_team.py _run.txt

行为：
    - 目标脚本以 __name__ == "__main__" 运行（等价于直接 python 跑它）
    - 脚本的退出码原样透传
    - 输出文件末尾会追加一行 [run_capture_utf8] EXIT=<code>，方便事后检索
    - 用 buffering=1（行缓冲）边跑边落盘，长时脚本可以中途 tail 看进度
"""

import runpy
import sys
import traceback
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    target = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    if not target.is_file():
        print(f"找不到目标脚本：{target}")
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    code = 0

    # buffering=1：行缓冲，输出不会卡在缓冲区里（长时脚本看起来像死锁）
    with open(out, "w", encoding="utf-8", buffering=1) as f:
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = f, f
        try:
            runpy.run_path(str(target), run_name="__main__")
        except SystemExit as e:
            # 目标脚本自己 sys.exit() 了，尊重它
            code = 0 if e.code is None else (e.code if isinstance(e.code, int) else 1)
        except BaseException:
            traceback.print_exc(file=f)
            code = 1
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            f.write(f"\n[run_capture_utf8] EXIT={code}\n")

    print(f"written: {out}  exit={code}")
    return code


if __name__ == "__main__":
    sys.exit(main())
