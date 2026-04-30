"""
视频转码工具 - 将 mp4v 编码的视频转换为 H.264 编码
"""
import cv2
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def convert_video_to_h264(input_path, output_path=None, overwrite=False):
    """将视频转换为H.264编码"""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"文件不存在: {input_path}")
        return False

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

    print(f"输入: {input_path.name}")
    print(f"输出: {output_path.name}")

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"无法打开视频: {input_path}")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"分辨率: {width}x{height}, 帧率: {fps:.2f} FPS, 总帧数: {frame_count}")

    out = None
    for encoder in ['avc1', 'H264', 'X264']:
        print(f"尝试编码器: {encoder}...", end=' ')
        fourcc = cv2.VideoWriter_fourcc(*encoder)
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        if out.isOpened():
            print("成功")
            break
        else:
            print("失败")
            out.release()
            out = None

    if out is None or not out.isOpened():
        print("无法创建H.264编码器")
        cap.release()
        return False

    print("开始转码...")
    start_time = datetime.now()

    processed = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        processed += 1
        if processed % 30 == 0 or processed == frame_count:
            progress = (processed / frame_count * 100) if frame_count > 0 else 0
            print(f"\r进度: {processed}/{frame_count} ({progress:.1f}%)", end='')

    print()
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"转码完成！耗时: {elapsed:.2f}秒")

    cap.release()
    out.release()

    test_cap = cv2.VideoCapture(str(output_path))
    if test_cap.isOpened():
        input_size = input_path.stat().st_size / (1024 * 1024)
        output_size = output_path.stat().st_size / (1024 * 1024)
        print(f"输入: {input_size:.2f} MB -> 输出: {output_size:.2f} MB ({(output_size/input_size*100):.1f}%)")
        test_cap.release()

        if should_replace:
            backup_path = input_path.parent / f"{input_path.stem}_backup.mp4"
            input_path.rename(backup_path)
            output_path.rename(input_path)
            print(f"已替换原文件，备份: {backup_path.name}")

        return True
    else:
        print("输出文件验证失败")
        test_cap.release()
        return False


def convert_batch_videos(pattern="recordings/batch*.mp4", overwrite=False):
    """批量转码视频文件"""
    from glob import glob

    files = sorted(glob(pattern))
    if not files:
        print(f"没有找到匹配的文件: {pattern}")
        return

    print(f"找到 {len(files)} 个文件")
    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 处理: {Path(file_path).name}")
        if convert_video_to_h264(file_path, overwrite=overwrite):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n成功: {success_count} 个, 失败: {fail_count} 个")


def main():
    if len(sys.argv) < 2:
        print("用法: workday-convert <input.mp4> [--overwrite] | --batch [--overwrite]")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        overwrite = '--overwrite' in sys.argv
        convert_batch_videos(overwrite=overwrite)
    else:
        input_file = sys.argv[1]
        overwrite = '--overwrite' in sys.argv
        convert_video_to_h264(input_file, overwrite=overwrite)


if __name__ == "__main__":
    main()
