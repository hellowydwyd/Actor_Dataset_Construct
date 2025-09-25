#!/usr/bin/env python3
"""
长电影处理示例
展示如何处理长时长的电影文件，包括内存优化、并行处理和断点续传
"""

import sys
import os
from pathlib import Path
import time
import argparse

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.video_recognition.video_processor import VideoFaceRecognizer
from src.utils.logger import get_logger
from src.utils.config_loader import config

logger = get_logger(__name__)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='长电影人脸识别处理')
    parser.add_argument('input_path', help='输入视频文件路径')
    parser.add_argument('-o', '--output', help='输出视频文件路径')
    parser.add_argument('-m', '--movie', help='指定电影名称（限定识别范围）')
    parser.add_argument('-s', '--similarity', type=float, default=0.6,
                       help='相似度阈值 (0.0-1.0)')
    parser.add_argument('--mode', choices=['standard', 'long_video', 'parallel'],
                       default='auto', help='处理模式')
    parser.add_argument('--max-workers', type=int, default=2,
                       help='并行处理的最大工作线程数')
    parser.add_argument('--max-memory', type=float, default=0.8,
                       help='最大内存使用率 (0.0-1.0)')
    parser.add_argument('--no-checkpoint', action='store_true',
                       help='禁用断点续传功能')
    parser.add_argument('--force-restart', action='store_true',
                       help='强制重新开始处理（忽略检查点）')
    
    return parser.parse_args()


def get_video_duration(video_path: str) -> float:
    """获取视频时长（分钟）"""
    import cv2
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        
        duration_minutes = total_frames / fps / 60 if fps > 0 else 0
        return duration_minutes
    except Exception as e:
        logger.error(f"获取视频时长失败: {e}")
        return 0


def determine_processing_mode(video_path: str, mode: str) -> str:
    """确定处理模式"""
    if mode != 'auto':
        return mode
    
    duration = get_video_duration(video_path)
    
    if duration <= 30:
        return 'standard'
    elif duration <= 120:
        return 'long_video'
    else:
        return 'parallel'


def create_progress_callback():
    """创建进度回调函数"""
    last_update = [0]  # 使用列表来避免nonlocal
    
    def progress_callback(progress: float, current_frame: int, total_frames: int):
        current_time = time.time()
        if current_time - last_update[0] >= 5.0:  # 每5秒更新一次
            print(f"\r处理进度: {progress:.1f}% ({current_frame:,}/{total_frames:,} 帧)", 
                  end='', flush=True)
            last_update[0] = current_time
    
    return progress_callback


def process_long_movie(input_path: str, output_path: str = None, **kwargs) -> None:
    """处理长电影"""
    
    print("=" * 60)
    print("长电影人脸识别处理")
    print("=" * 60)
    
    # 获取配置
    # config对象已经在顶部导入，无需重新加载
    video_config = config.get_config().get('video_processing', {})
    
    # 确定处理模式
    mode = determine_processing_mode(input_path, kwargs.get('mode', 'auto'))
    print(f"处理模式: {mode}")
    
    # 获取视频信息
    duration = get_video_duration(input_path)
    print(f"视频时长: {duration:.1f} 分钟")
    
    # 初始化处理器
    long_video_mode = mode in ['long_video', 'parallel']
    max_memory_usage = kwargs.get('max_memory', 
                                 video_config.get('long_video_mode', {}).get('max_memory_usage', 0.8))
    
    recognizer = VideoFaceRecognizer(
        similarity_threshold=kwargs.get('similarity', 0.6),
        movie_title=kwargs.get('movie'),
        long_video_mode=long_video_mode,
        max_memory_usage=max_memory_usage
    )
    
    print(f"相似度阈值: {recognizer.similarity_threshold}")
    if recognizer.movie_title:
        print(f"电影范围限定: {recognizer.movie_title}")
    print(f"长视频模式: {'启用' if long_video_mode else '禁用'}")
    print(f"最大内存使用率: {max_memory_usage:.1%}")
    
    # 创建输出路径
    if not output_path:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"processed_{input_file.name}")
    
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")
    print()
    
    # 创建进度回调
    progress_callback = create_progress_callback()
    
    try:
        start_time = time.time()
        
        # 根据模式选择处理方法
        if mode == 'parallel':
            max_workers = kwargs.get('max_workers', 2)
            print(f"使用并行处理模式（{max_workers} 个工作线程）")
            print("开始处理...")
            
            stats = recognizer.process_video_with_parallel_frames(
                input_path,
                output_path,
                max_workers=max_workers,
                progress_callback=progress_callback
            )
        else:
            print("开始处理...")
            resume_from_checkpoint = not kwargs.get('no_checkpoint', False)
            if kwargs.get('force_restart', False):
                resume_from_checkpoint = False
                print("强制重新开始处理")
            
            stats = recognizer.process_video_file(
                input_path,
                output_path,
                frame_skip=1,
                progress_callback=progress_callback,
                resume_from_checkpoint=resume_from_checkpoint
            )
        
        print()  # 换行
        
        # 显示处理结果
        if 'error' in stats:
            print(f"❌ 处理失败: {stats['error']}")
            return
        
        elapsed_time = time.time() - start_time
        
        print("✅ 处理完成!")
        print()
        print("处理统计:")
        print(f"  总帧数: {stats.get('total_frames', 0):,}")
        print(f"  处理帧数: {stats.get('processed_frames', 0):,}")
        print(f"  检测人脸数: {stats.get('faces_detected', 0):,}")
        print(f"  识别人脸数: {stats.get('faces_recognized', 0):,}")
        print(f"  发现演员数: {len(stats.get('actors_found', []))}")
        print(f"  处理时间: {elapsed_time:.1f} 秒")
        
        if 'effective_skip_rate' in stats:
            print(f"  跳帧率: {stats['effective_skip_rate']}")
        
        if 'parallel_workers' in stats:
            print(f"  并行工作线程: {stats['parallel_workers']}")
        
        if 'memory_warnings' in stats:
            print(f"  内存警告次数: {stats['memory_warnings']}")
        
        if 'gc_collections' in stats:
            print(f"  垃圾回收次数: {stats['gc_collections']}")
        
        # 显示发现的演员
        actors = stats.get('actors_found', [])
        if actors:
            print()
            print("发现的演员:")
            for i, actor in enumerate(sorted(actors), 1):
                print(f"  {i}. {actor}")
        
        # 性能建议
        print()
        print("性能建议:")
        
        if duration > 180 and mode != 'parallel':
            print("  • 对于超过3小时的视频，建议使用 --mode parallel")
        
        if stats.get('memory_warnings', 0) > 0:
            print("  • 出现内存警告，建议降低 --max-memory 参数")
        
        if stats.get('gc_collections', 0) > 10:
            print("  • 垃圾回收频繁，建议启用长视频模式")
        
        processing_fps = stats.get('processed_frames', 0) / elapsed_time
        if processing_fps < 1.0:
            print(f"  • 处理速度较慢 ({processing_fps:.2f} fps)，建议检查系统性能")
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断处理")
        print("检查点已保存，可使用相同参数继续处理")
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        print(f"❌ 处理失败: {e}")


def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查输入文件
    if not os.path.exists(args.input_path):
        print(f"❌ 输入文件不存在: {args.input_path}")
        return 1
    
    # 构建参数字典
    kwargs = {
        'mode': args.mode,
        'similarity': args.similarity,
        'movie': args.movie,
        'max_workers': args.max_workers,
        'max_memory': args.max_memory,
        'no_checkpoint': args.no_checkpoint,
        'force_restart': args.force_restart
    }
    
    try:
        process_long_movie(args.input_path, args.output, **kwargs)
        return 0
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
