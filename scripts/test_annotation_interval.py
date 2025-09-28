#!/usr/bin/env python3
"""
测试标注间隔功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.video_recognition.video_processor import VideoFaceRecognizer
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_annotation_interval():
    """测试不同标注间隔设置"""
    logger.info("🧪 开始测试标注间隔功能")
    
    # 测试不同的标注间隔设置
    test_intervals = [1, 2, 3, 5]
    
    for interval in test_intervals:
        logger.info(f"\n📋 测试标注间隔: {interval}")
        
        try:
            # 创建视频识别器
            recognizer = VideoFaceRecognizer(
                similarity_threshold=0.6,
                annotation_frame_interval=interval
            )
            
            logger.info(f"✅ 成功创建视频识别器，标注间隔: {recognizer.annotation_frame_interval}")
            
            # 验证间隔值是否正确设置
            assert recognizer.annotation_frame_interval == interval, f"标注间隔设置错误: 期望{interval}, 实际{recognizer.annotation_frame_interval}"
            
        except Exception as e:
            logger.error(f"❌ 标注间隔 {interval} 测试失败: {e}")
            return False
    
    # 测试边界值
    logger.info(f"\n📋 测试边界值")
    
    # 测试最小值（应该被调整为1）
    try:
        recognizer = VideoFaceRecognizer(annotation_frame_interval=0)
        assert recognizer.annotation_frame_interval == 1, "最小值边界测试失败"
        logger.info("✅ 最小值边界测试通过（0 -> 1）")
    except Exception as e:
        logger.error(f"❌ 最小值边界测试失败: {e}")
        return False
    
    # 测试负值（应该被调整为1）
    try:
        recognizer = VideoFaceRecognizer(annotation_frame_interval=-5)
        assert recognizer.annotation_frame_interval == 1, "负值边界测试失败"
        logger.info("✅ 负值边界测试通过（-5 -> 1）")
    except Exception as e:
        logger.error(f"❌ 负值边界测试失败: {e}")
        return False
    
    logger.info("🎉 所有标注间隔测试通过！")
    return True


def test_config_loading():
    """测试配置文件中的标注间隔参数"""
    logger.info("🧪 开始测试配置文件加载")
    
    try:
        from src.utils.config_loader import config
        
        # 获取视频处理配置
        video_config = config.get_video_processing_config()
        
        if 'annotation' in video_config:
            annotation_config = video_config['annotation']
            frame_interval = annotation_config.get('frame_interval', 1)
            logger.info(f"✅ 配置文件中的标注间隔: {frame_interval}")
            
            # 验证描述信息
            description = annotation_config.get('description', '')
            if description:
                logger.info(f"📝 配置描述: {description}")
        else:
            logger.warning("⚠️ 配置文件中未找到annotation配置")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置文件测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始标注间隔功能测试")
    logger.info("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    # 测试标注间隔功能
    if test_annotation_interval():
        success_count += 1
        logger.info("✅ 标注间隔功能测试通过")
    else:
        logger.error("❌ 标注间隔功能测试失败")
    
    logger.info("\n" + "=" * 50)
    
    # 测试配置文件加载
    if test_config_loading():
        success_count += 1
        logger.info("✅ 配置文件加载测试通过")
    else:
        logger.error("❌ 配置文件加载测试失败")
    
    logger.info("\n" + "=" * 50)
    logger.info("📊 测试结果汇总:")
    logger.info(f"通过测试: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        logger.info("🎉 所有测试通过！标注间隔功能正常工作。")
        return True
    else:
        logger.error("❌ 部分测试失败，请检查实现。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
