#!/usr/bin/env python3
"""
Workday - 工作时间记录和分析工具
"""
import sys
import argparse
from recorder import ScreenRecorder
from logger import get_logger

logger = get_logger(__name__)


def list_monitors():
    """列出所有可用的显示器"""
    monitors = ScreenRecorder.list_monitors()

    if not monitors:
        print("❌ 无法获取显示器信息")
        return

    print("\n📺 可用的显示器：\n")
    print(f"{'索引':<8} {'描述':<25} {'分辨率':<15} {'位置'}")
    print("-" * 70)

    for monitor in monitors:
        index = monitor['index']
        desc = monitor['description']
        resolution = f"{monitor['width']}x{monitor['height']}"
        position = f"({monitor['left']}, {monitor['top']})"

        print(f"{index:<8} {desc:<25} {resolution:<15} {position}")

    print("\n💡 使用说明：")
    print("  - 在 config.yaml 中设置 'recording.monitor_index' 来选择要录制的显示器")
    print("  - 索引 0：录制所有显示器（默认）")
    print("  - 索引 1：主显示器")
    print("  - 索引 2+：其他显示器")
    print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Workday - 工作时间记录和分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--list-monitors',
        action='store_true',
        help='列出所有可用的显示器'
    )

    parser.add_argument(
        '--version',
        action='store_true',
        help='显示版本信息'
    )

    args = parser.parse_args()

    if args.list_monitors:
        list_monitors()
        return

    if args.version:
        print("Workday v0.1.0")
        return

    # 默认：显示帮助信息
    print("Workday - 工作时间记录和分析工具")
    print("\n使用方法：")
    print("  python main.py --list-monitors    # 列出所有可用显示器")
    print("  python api.py                     # 启动 API 服务")
    print("\n更多信息请查看 README.md")


if __name__ == "__main__":
    main()
