"""
视频转码工具 - 将 mp4v 编码的视频转换为 H.264 编码

用途：
- 修复旧的无法在浏览器播放的mp4v视频
- 将其转码为浏览器支持的H.264格式
"""
import cv2
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows UTF-8 支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def convert_video_to_h264(input_path, output_path=None, overwrite=False):
    """
    将视频转换为H.264编码

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径（可选，默认添加_h264后缀）
        overwrite: 是否覆盖原文件
    """
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return False

    # 确定输出路径
    if output_path is None:
        if overwrite:
            output_path = input_path.parent / f"{input_path.stem}_temp.mp4"
            should_replace = True
        else:
            output_path = input_path.parent / f"{input_path.stem}_h264.mp4"
            should_replace = False
    else:
        output_path = Path(output_path)
        should_replace = False

    print(f"📹 输入: {input_path.name}")
    print(f"📹 输出: {output_path.name}")
    print()

    # 打开输入视频
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"❌ 无法打开视频: {input_path}")
        return False

    # 获取视频属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 获取原始编码
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_bytes = fourcc_int.to_bytes(4, byteorder='little')
    fourcc_str = fourcc_bytes.decode('ascii', errors='ignore')

    print(f"原始编码: {fourcc_str}")
    print(f"分辨率: {width}x{height}")
    print(f"帧率: {fps:.2f} FPS")
    print(f"总帧数: {frame_count}")
    print()

    # 创建H.264编码器
    # 尝试不同的H.264编码器
    encoders = ['avc1', 'H264', 'X264']
    out = None

    for encoder in encoders:
        print(f"尝试编码器: {encoder}...", end=' ')
        fourcc = cv2.VideoWriter_fourcc(*encoder)
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if out.isOpened():
            print("✅ 成功")
            break
        else:
            print("❌ 失败")
            out.release()
            out = None

    if out is None or not out.isOpened():
        print()
        print("❌ 无法创建H.264编码器")
        print("💡 可能的原因:")
        print("  - 系统缺少H.264编解码器")
        print("  - OpenCV编译时未启用H.264支持")
        cap.release()
        return False

    print()
    print("⏳ 开始转码...")
    start_time = datetime.now()

    # 逐帧转码
    processed = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        out.write(frame)
        processed += 1

        # 进度显示
        if processed % 30 == 0 or processed == frame_count:
            progress = (processed / frame_count * 100) if frame_count > 0 else 0
            print(f"\r进度: {processed}/{frame_count} ({progress:.1f}%)", end='')

    print()
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ 转码完成！耗时: {elapsed:.2f}秒")

    # 释放资源
    cap.release()
    out.release()

    # 验证输出文件
    test_cap = cv2.VideoCapture(str(output_path))
    if test_cap.isOpened():
        test_fourcc = int(test_cap.get(cv2.CAP_PROP_FOURCC))
        test_fourcc_bytes = test_fourcc.to_bytes(4, byteorder='little')
        test_fourcc_str = test_fourcc_bytes.decode('ascii', errors='ignore')

        input_size = input_path.stat().st_size / (1024 * 1024)
        output_size = output_path.stat().st_size / (1024 * 1024)

        print()
        print("📊 转码结果:")
        print(f"  输入大小: {input_size:.2f} MB ({fourcc_str})")
        print(f"  输出大小: {output_size:.2f} MB ({test_fourcc_str})")
        print(f"  压缩率: {(output_size/input_size*100):.1f}%")
        test_cap.release()

        # 如果需要覆盖原文件
        if should_replace:
            backup_path = input_path.parent / f"{input_path.stem}_backup.mp4"
            print()
            print(f"💾 备份原文件: {backup_path.name}")
            input_path.rename(backup_path)
            output_path.rename(input_path)
            print(f"✅ 已替换原文件")
            print(f"   原文件已备份为: {backup_path.name}")

        return True
    else:
        print()
        print("❌ 输出文件验证失败")
        test_cap.release()
        return False


def convert_batch_videos(pattern="recordings/batch*.mp4", overwrite=False):
    """批量转码视频文件"""
    from glob import glob

    files = sorted(glob(pattern))

    if not files:
        print(f"❌ 没有找到匹配的文件: {pattern}")
        return

    print(f"找到 {len(files)} 个文件")
    print("=" * 80)
    print()

    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] 处理: {Path(file_path).name}")
        print("-" * 80)

        if convert_video_to_h264(file_path, overwrite=overwrite):
            success_count += 1
        else:
            fail_count += 1

        print()
        print("=" * 80)
        print()

    print()
    print("📊 转码统计:")
    print(f"  ✅ 成功: {success_count} 个")
    print(f"  ❌ 失败: {fail_count} 个")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 80)
        print("视频转码工具 - mp4v → H.264")
        print("=" * 80)
        print()
        print("用法:")
        print("  1. 转码单个文件:")
        print("     python convert_video.py <input.mp4>")
        print()
        print("  2. 转码单个文件并覆盖原文件:")
        print("     python convert_video.py <input.mp4> --overwrite")
        print()
        print("  3. 批量转码所有batch视频:")
        print("     python convert_video.py --batch")
        print()
        print("  4. 批量转码并覆盖原文件:")
        print("     python convert_video.py --batch --overwrite")
        print()
        print("示例:")
        print("  python convert_video.py recordings/batch_20251120_103327.mp4")
        print("  python convert_video.py --batch")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        overwrite = '--overwrite' in sys.argv
        convert_batch_videos(overwrite=overwrite)
    else:
        input_file = sys.argv[1]
        overwrite = '--overwrite' in sys.argv
        convert_video_to_h264(input_file, overwrite=overwrite)
