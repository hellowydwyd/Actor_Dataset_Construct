#!/usr/bin/env python3
"""
测试中文文字渲染功能
"""

import cv2
import numpy as np
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.chinese_text_renderer import draw_chinese_text, draw_chinese_text_with_outline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_chinese_text_rendering():
    """测试中文文字渲染功能"""
    logger.info("开始测试中文文字渲染...")
    
    # 创建测试图像
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    img.fill(50)  # 深灰色背景
    
    # 测试数据
    test_texts = [
        "摩根·弗里曼 (0.95)",
        "蒂姆·罗宾斯 (0.87)",
        "小罗伯特·唐尼 (0.92)",
        "格温妮斯·帕特洛 (0.88)",
        "李雪健 (0.93)",
        "王智 (0.86)",
        "未知",
    ]
    
    colors = [
        (255, 255, 255),  # 白色
        (0, 255, 0),      # 绿色
        (255, 0, 0),      # 蓝色
        (0, 255, 255),    # 黄色
        (255, 0, 255),    # 紫色
        (0, 165, 255),    # 橙色
        (128, 128, 128),  # 灰色
    ]
    
    background_colors = [
        (0, 0, 255),      # 红色背景
        (0, 128, 0),      # 绿色背景
        (128, 0, 0),      # 蓝色背景
        (0, 128, 128),    # 青色背景
        (128, 0, 128),    # 紫色背景
        (0, 82, 128),     # 橙色背景
        (64, 64, 64),     # 深灰背景
    ]
    
    # 绘制测试文字
    y_position = 50
    for i, text in enumerate(test_texts):
        x_position = 50
        
        # 普通文字
        img = draw_chinese_text(
            img, text, (x_position, y_position),
            font_size=20,
            color=colors[i],
            background_color=background_colors[i],
            background_padding=5
        )
        
        # 带描边的文字
        x_position = 350
        img = draw_chinese_text_with_outline(
            img, text, (x_position, y_position),
            font_size=20,
            text_color=colors[i],
            outline_color=(0, 0, 0),
            outline_width=2
        )
        
        y_position += 45
    
    # 保存测试结果
    output_path = project_root / "temp" / "chinese_text_test.jpg"
    output_path.parent.mkdir(exist_ok=True)
    
    success = cv2.imwrite(str(output_path), img)
    
    if success:
        logger.info(f"中文文字测试图片已保存到: {output_path}")
        print(f"测试完成！请查看图片: {output_path}")
        
        # 显示图片（如果在支持的环境中）
        try:
            cv2.imshow("Chinese Text Test", img)
            print("按任意键关闭窗口...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except Exception as e:
            logger.info(f"无法显示图片窗口: {e}")
    else:
        logger.error("保存测试图片失败")


def test_system_font_detection():
    """测试系统字体检测"""
    from src.utils.chinese_text_renderer import ChineseTextRenderer
    
    renderer = ChineseTextRenderer()
    font_path = renderer.default_font_path
    
    if font_path:
        logger.info(f"检测到系统字体: {font_path}")
        print(f"系统字体: {font_path}")
    else:
        logger.warning("未检测到中文系统字体")
        print("警告: 未检测到中文系统字体，可能会影响中文显示效果")


if __name__ == '__main__':
    test_system_font_detection()
    test_chinese_text_rendering()
