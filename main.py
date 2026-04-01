"""项目启动入口：启动交互式教学 Shell。"""

from __future__ import annotations

from shell import start_shell


def main() -> None:
    """
    功能:
        作为程序主入口执行对话流程，并在启动失败时输出错误信息。
    参数:
        无。
    返回值:
        None: 该函数负责流程调度，不返回额外结果。
    """
    try:
        start_shell()
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"程序启动失败: {exc}")


if __name__ == "__main__":
    main()
