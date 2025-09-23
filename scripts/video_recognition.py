#!/usr/bin/env python3
"""
视频人脸识别命令行工具
"""
import argparse
import sys
import cv2
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.video_recognition.video_processor import VideoFaceRecognizer
from src.utils.logger import get_logger

logger = get_logger(__name__)


def process_image_file(image_path: str, output_path: str = None, 
                      similarity_threshold: float = 0.6, movie_title: str = None):
    """处理图片文件"""
    try:
        recognizer = VideoFaceRecognizer(similarity_threshold=similarity_threshold, movie_title=movie_title)
        
        # 读取图片
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"❌ 无法读取图片: {image_path}")
            return False
        
        print(f"📷 处理图片: {image_path}")
        print(f"🎯 相似度阈值: {similarity_threshold}")
        if movie_title:
            print(f"🎬 电影范围限定: {movie_title}")
        
        # 处理帧
        annotated_frame, recognition_results = recognizer.process_single_frame(frame)
        
        # 保存结果
        if output_path:
            cv2.imwrite(output_path, annotated_frame)
            print(f"✅ 标注结果已保存到: {output_path}")
        
        # 显示识别结果
        print(f"\n🔍 识别结果:")
        print(f"  检测到人脸: {len(recognition_results)} 张")
        
        recognized_count = 0
        for i, result in enumerate(recognition_results, 1):
            if result['recognized']:
                recognized_count += 1
                print(f"  人脸 {i}: {result['actor_name']} (相似度: {result['similarity']:.3f}, 置信度: {result['confidence']})")
            else:
                print(f"  人脸 {i}: 未识别 (检测分数: {result['det_score']:.3f})")
        
        print(f"  成功识别: {recognized_count} 张")
        
        if recognized_count > 0:
            actors_found = list(set(r['actor_name'] for r in recognition_results if r['recognized']))
            print(f"  发现演员: {', '.join(actors_found)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return False


def show_database_info():
    """显示数据库信息"""
    try:
        recognizer = VideoFaceRecognizer()
        actors = recognizer.get_database_actors()
        
        print("📊 数据库信息:")
        print(f"  可识别演员数量: {len(actors)}")
        
        if actors:
            print("\n👥 演员列表:")
            for actor in actors:
                movies_str = ", ".join(actor['movies']) if actor['movies'] else "未知电影"
                print(f"  • {actor['name']}: {actor['face_count']} 张人脸 ({movies_str})")
        else:
            print("  ⚠️ 数据库为空，请先构建演员数据集")
        
    except Exception as e:
        print(f"❌ 获取数据库信息失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="视频人脸识别工具")
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 处理图片命令
    process_parser = subparsers.add_parser('process', help='处理图片进行人脸识别')
    process_parser.add_argument('--input', '-i', required=True, help='输入图片路径')
    process_parser.add_argument('--output', '-o', help='输出图片路径（可选）')
    process_parser.add_argument('--threshold', '-t', type=float, default=0.6, help='相似度阈值 (0.4-0.9)')
    process_parser.add_argument('--movie', '-m', help='电影名称，限定识别范围（可选）')
    
    # 数据库信息命令
    info_parser = subparsers.add_parser('info', help='显示数据库信息')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🎬 视频人脸识别系统")
    print("=" * 50)
    
    if args.command == 'process':
        # 检查输入文件
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ 输入文件不存在: {args.input}")
            return
        
        # 设置输出路径
        output_path = args.output
        if not output_path:
            output_path = input_path.parent / f"annotated_{input_path.name}"
        
        # 处理图片
        success = process_image_file(
            image_path=str(input_path),
            output_path=str(output_path),
            similarity_threshold=args.threshold,
            movie_title=args.movie
        )
        
        if success:
            print("\n🎉 处理完成!")
        else:
            print("\n❌ 处理失败!")
    
    elif args.command == 'info':
        show_database_info()


if __name__ == "__main__":
    main()
