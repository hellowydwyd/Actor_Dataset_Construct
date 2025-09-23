#!/usr/bin/env python3
"""
完整视频处理演示
"""
import sys
from pathlib import Path
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.video_recognition.video_processor import VideoFaceRecognizer


def process_video_demo(input_path: str, output_path: str = None, frame_skip: int = 1):
    """演示完整视频处理"""
    try:
        print("🎬 初始化视频人脸识别器...")
        recognizer = VideoFaceRecognizer(similarity_threshold=0.6)
        
        # 检查数据库
        actors = recognizer.get_database_actors()
        if not actors:
            print("❌ 数据库为空，请先构建演员数据集")
            return False
        
        print(f"✅ 数据库包含 {len(actors)} 位演员:")
        for actor in actors:
            print(f"   • {actor['name']}: {actor['face_count']} 张人脸")
        
        # 设置输出路径
        input_file = Path(input_path)
        if not output_path:
            output_path = input_file.parent / f"processed_{input_file.name}"
        
        print(f"\n🎥 开始处理视频:")
        print(f"   输入: {input_path}")
        print(f"   输出: {output_path}")
        print(f"   跳帧: {frame_skip} (1=处理每帧)")
        
        # 进度回调函数
        def progress_callback(progress, current_frame, total_frames):
            print(f"   进度: {progress:.1f}% ({current_frame}/{total_frames})")
        
        # 处理视频
        results = recognizer.process_video_file(
            video_path=input_path,
            output_path=str(output_path),
            frame_skip=frame_skip,
            progress_callback=progress_callback
        )
        
        if 'error' in results:
            print(f"❌ 处理失败: {results['error']}")
            return False
        
        # 显示结果
        print(f"\n🎉 处理完成!")
        print(f"📊 统计结果:")
        print(f"   总帧数: {results['total_frames']}")
        print(f"   处理帧数: {results['processed_frames']}")
        print(f"   检测人脸: {results['faces_detected']}")
        print(f"   识别成功: {results['faces_recognized']}")
        print(f"   处理时间: {results['processing_time']:.1f} 秒")
        
        if results['actors_found']:
            print(f"   发现演员: {', '.join(results['actors_found'])}")
        
        print(f"\n✅ 标注视频已保存到: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="视频人脸识别处理工具")
    parser.add_argument('--input', '-i', required=True, help='输入视频路径')
    parser.add_argument('--output', '-o', help='输出视频路径（可选）')
    parser.add_argument('--skip', '-s', type=int, default=1, help='跳帧数量（1=每帧处理）')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not Path(args.input).exists():
        print(f"❌ 输入文件不存在: {args.input}")
        return
    
    # 处理视频
    success = process_video_demo(args.input, args.output, args.skip)
    
    if success:
        print("\n🎊 视频处理演示完成!")
        print("\n💡 您也可以使用Web界面:")
        print("   1. 启动: python main.py web")
        print("   2. 访问: http://127.0.0.1:5000")
        print("   3. 选择'🎥 视频识别' → '完整视频'模式")
    else:
        print("\n❌ 演示失败!")


if __name__ == "__main__":
    main()
