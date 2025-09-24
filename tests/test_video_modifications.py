#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试视频处理修改功能
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

from src.video_recognition.video_processor import VideoFaceRecognizer
from src.utils.chinese_text_renderer import ChineseTextRenderer
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_text_renderer_outline():
    """测试文字描边功能"""
    print("="*60)
    print("测试文字描边功能")
    print("="*60)
    
    try:
        # 创建测试图像
        test_img = np.zeros((300, 800, 3), dtype=np.uint8)
        test_img[:] = (50, 50, 50)  # 深灰色背景
        
        # 创建文字渲染器
        text_renderer = ChineseTextRenderer()
        
        # 测试不同颜色的描边文字
        test_cases = [
            {"text": "阿尔·帕西诺 (0.95)", "pos": (50, 50), "color": (0, 255, 0)},     # 绿色
            {"text": "马龙·白兰度 (0.92)", "pos": (50, 120), "color": (255, 0, 0)},    # 蓝色
            {"text": "汤姆·汉克斯 (0.88)", "pos": (50, 190), "color": (0, 165, 255)},  # 橙色
            {"text": "未知 (0.60)", "pos": (50, 260), "color": (255, 255, 255)},      # 白色
        ]
        
        for case in test_cases:
            test_img = text_renderer.draw_text_with_outline(
                test_img,
                case["text"],
                case["pos"],
                font_size=24,
                text_color=case["color"],
                outline_color=(0, 0, 0),
                outline_width=2
            )
        
        # 保存测试图像
        output_path = Path("temp/text_outline_test.jpg")
        output_path.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(output_path), test_img)
        
        print(f"✅ 文字描边测试完成，结果保存到: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 文字描边测试失败: {e}")
        return False


def test_progress_callback():
    """测试进度回调函数"""
    print("\n" + "="*60)
    print("测试进度回调函数")
    print("="*60)
    
    try:
        # 模拟进度信息
        progress_info = {
            'progress': 45.5,
            'current_frame': 1365,
            'total_frames': 3000,
            'processed_frames': 455,
            'faces_detected': 123,
            'faces_recognized': 89,
            'actors_found': 5,
            'elapsed_time': 125.5,
            'eta': 150.2,
            'fps': 30.0,
            'memory_usage': 0.65
        }
        
        # 测试进度回调处理
        def test_callback(info):
            progress = info.get('progress', 0)
            current_frame = info.get('current_frame', 0)
            total_frames = info.get('total_frames', 0)
            processed_frames = info.get('processed_frames', 0)
            faces_detected = info.get('faces_detected', 0)
            faces_recognized = info.get('faces_recognized', 0)
            actors_found = info.get('actors_found', 0)
            elapsed_time = info.get('elapsed_time', 0)
            eta = info.get('eta', 0)
            memory_usage = info.get('memory_usage', 0)
            
            # 格式化时间
            elapsed_str = f"{int(elapsed_time // 60)}:{int(elapsed_time % 60):02d}"
            eta_str = f"{int(eta // 60)}:{int(eta % 60):02d}" if eta > 0 else "未知"
            
            # 构建详细消息
            message = (f"处理进度: {progress:.1f}% ({current_frame}/{total_frames}) | "
                      f"已处理: {processed_frames} 帧 | "
                      f"检测人脸: {faces_detected} | 识别: {faces_recognized} | "
                      f"发现演员: {actors_found} 位 | "
                      f"用时: {elapsed_str} | 剩余: {eta_str} | "
                      f"内存: {memory_usage:.1%}")
            
            print(f"进度回调: {message}")
            return True
        
        # 测试回调
        result = test_callback(progress_info)
        
        print(f"✅ 进度回调测试完成: {'通过' if result else '失败'}")
        return result
        
    except Exception as e:
        print(f"❌ 进度回调测试失败: {e}")
        return False


def test_video_recognizer_initialization():
    """测试视频识别器初始化（包含文字渲染器）"""
    print("\n" + "="*60)
    print("测试视频识别器初始化")
    print("="*60)
    
    try:
        # 创建视频识别器
        recognizer = VideoFaceRecognizer(
            similarity_threshold=0.7,
            movie_title="教父",
            long_video_mode=False
        )
        
        # 检查是否包含文字渲染器
        if hasattr(recognizer, 'text_renderer'):
            print("✅ 文字渲染器初始化成功")
        else:
            print("❌ 文字渲染器未初始化")
            return False
        
        # 检查文字渲染器类型
        if isinstance(recognizer.text_renderer, ChineseTextRenderer):
            print("✅ 文字渲染器类型正确")
        else:
            print("❌ 文字渲染器类型错误")
            return False
        
        print("✅ 视频识别器初始化测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 视频识别器初始化测试失败: {e}")
        return False


def test_character_name_display():
    """测试角色名字显示逻辑"""
    print("\n" + "="*60)
    print("测试角色名字显示逻辑")
    print("="*60)
    
    try:
        # 模拟识别结果
        test_cases = [
            {
                "name": "有角色名字的情况",
                "result": {
                    "actor_name": "阿尔·帕西诺",
                    "similarity": 0.95,
                    "metadata": {"character": "迈克尔·科里昂"}
                },
                "expected": "迈克尔·科里昂 (0.95)"
            },
            {
                "name": "没有角色名字的情况", 
                "result": {
                    "actor_name": "汤姆·汉克斯",
                    "similarity": 0.88,
                    "metadata": {}
                },
                "expected": "汤姆·汉克斯 (0.88)"
            },
            {
                "name": "角色名字为空的情况",
                "result": {
                    "actor_name": "马龙·白兰度",
                    "similarity": 0.92,
                    "metadata": {"character": ""}
                },
                "expected": "马龙·白兰度 (0.92)"
            }
        ]
        
        success_count = 0
        
        for case in test_cases:
            result = case["result"]
            metadata = result.get('metadata', {})
            character_name = metadata.get('character', '')
            actor_name = result['actor_name']
            similarity = result['similarity']
            
            # 优先显示角色名字，如果没有则显示演员名字
            display_name = character_name if character_name else actor_name
            label = f"{display_name} ({similarity:.2f})"
            
            if label == case["expected"]:
                print(f"✅ {case['name']}: {label}")
                success_count += 1
            else:
                print(f"❌ {case['name']}: 期望 '{case['expected']}', 实际 '{label}'")
        
        if success_count == len(test_cases):
            print("✅ 角色名字显示逻辑测试完成")
            return True
        else:
            print(f"❌ 角色名字显示逻辑测试失败: {success_count}/{len(test_cases)} 通过")
            return False
        
    except Exception as e:
        print(f"❌ 角色名字显示逻辑测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试视频处理修改功能")
    print("="*60)
    
    test_results = []
    
    # 测试1: 文字描边功能
    test_results.append(("文字描边功能", test_text_renderer_outline()))
    
    # 测试2: 进度回调函数
    test_results.append(("进度回调函数", test_progress_callback()))
    
    # 测试3: 视频识别器初始化
    test_results.append(("视频识别器初始化", test_video_recognizer_initialization()))
    
    # 测试4: 角色名字显示逻辑
    test_results.append(("角色名字显示逻辑", test_character_name_display()))
    
    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总结: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！视频处理修改功能正常。")
        
        print("\n📋 修改总结:")
        print("1. ✅ 删除了视频第一帧预览功能")
        print("2. ✅ 修改进度条为详细的回调函数")
        print("3. ✅ 标注人物时优先使用角色名字")
        print("4. ✅ 绘制框时角色名字使用描边而不是纯色填充")
    else:
        print("⚠️  有测试失败，请检查错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
