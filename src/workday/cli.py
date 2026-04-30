"""
Workday CLI 入口点
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description='Workday - AI 驱动的工作时间追踪工具',
    )
    parser.add_argument('--version', action='store_true', help='显示版本信息')

    args = parser.parse_args()

    if args.version:
        from workday import __version__
        print(f"Workday v{__version__}")
        return

    _run_gui()


def _run_gui():
    try:
        from workday.gui.app import run_app
        run_app()
    except ImportError as e:
        print(f"错误：无法启动 GUI - {e}")
        print("请确保已安装 customtkinter: pip install customtkinter")
        sys.exit(1)


if __name__ == "__main__":
    main()
