"""
中文文字渲染工具
解决OpenCV不支持中文显示的问题
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import platform
from typing import Tuple, Optional

from .logger import get_logger

logger = get_logger(__name__)


class ChineseTextRenderer:
    """中文文字渲染器"""
    
    def __init__(self):
        """初始化中文文字渲染器"""
        self.font_cache = {}
        self.default_font_path = self._find_system_font()
        
    def _find_system_font(self) -> Optional[str]:
        """查找系统中文字体"""
        font_paths = []
        
        system = platform.system()
        if system == "Windows":
            # Windows系统字体路径
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
                "C:/Windows/Fonts/simhei.ttf",    # 黑体
                "C:/Windows/Fonts/simsun.ttc",    # 宋体
                "C:/Windows/Fonts/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
            ]
        elif system == "Linux":
            # Linux系统字体路径
            font_paths = [
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]
        elif system == "Darwin":  # macOS
            # macOS系统字体路径
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf",
            ]
        
        # 查找第一个存在的字体文件
        for font_path in font_paths:
            if Path(font_path).exists():
                logger.info(f"找到系统字体: {font_path}")
                return font_path
        
        logger.warning("未找到系统中文字体，将使用默认字体（可能不支持中文）")
        return None
    
    def _get_font(self, font_size: int, font_path: str = None) -> ImageFont.FreeTypeFont:
        """获取字体对象（带缓存）"""
        if font_path is None:
            font_path = self.default_font_path
        
        cache_key = f"{font_path}_{font_size}"
        
        if cache_key not in self.font_cache:
            try:
                if font_path and Path(font_path).exists():
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    # 使用PIL默认字体
                    font = ImageFont.load_default()
                
                self.font_cache[cache_key] = font
                logger.debug(f"加载字体: {font_path}, 大小: {font_size}")
                
            except Exception as e:
                logger.error(f"加载字体失败: {e}")
                # 使用默认字体作为后备
                font = ImageFont.load_default()
                self.font_cache[cache_key] = font
        
        return self.font_cache[cache_key]
    
    def get_text_size(self, text: str, font_size: int, font_path: str = None) -> Tuple[int, int]:
        """
        获取文字尺寸
        
        Args:
            text: 要测量的文字
            font_size: 字体大小
            font_path: 字体文件路径
            
        Returns:
            (width, height) 文字尺寸
        """
        try:
            font = self._get_font(font_size, font_path)
            
            # 创建临时图片来测量文字尺寸
            temp_img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(temp_img)
            
            # 使用textbbox获取更准确的尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            return (width, height)
            
        except Exception as e:
            logger.error(f"获取文字尺寸失败: {e}")
            # 返回估算尺寸
            return (len(text) * font_size, font_size)
    
    def draw_text_on_image(self, img: np.ndarray, text: str, position: Tuple[int, int], 
                          font_size: int = 20, color: Tuple[int, int, int] = (255, 255, 255),
                          background_color: Tuple[int, int, int] = None,
                          background_padding: int = 5, font_path: str = None) -> np.ndarray:
        """
        在图像上绘制中文文字
        
        Args:
            img: 输入图像 (BGR格式)
            text: 要绘制的文字
            position: 文字位置 (x, y)
            font_size: 字体大小
            color: 文字颜色 (RGB)
            background_color: 背景颜色 (RGB)，None表示不绘制背景
            background_padding: 背景内边距
            font_path: 字体文件路径
            
        Returns:
            绘制文字后的图像
        """
        try:
            # 将BGR转换为RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(img_pil)
            
            # 获取字体
            font = self._get_font(font_size, font_path)
            
            x, y = position
            
            # 绘制背景
            if background_color is not None:
                text_width, text_height = self.get_text_size(text, font_size, font_path)
                
                # 背景矩形坐标
                bg_x1 = x - background_padding
                bg_y1 = y - text_height - background_padding
                bg_x2 = x + text_width + background_padding
                bg_y2 = y + background_padding
                
                # 绘制背景矩形
                draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=background_color)
            
            # 绘制文字
            draw.text((x, y - font_size), text, font=font, fill=color)
            
            # 转换回BGR格式
            img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            return img_bgr
            
        except Exception as e:
            logger.error(f"绘制中文文字失败: {e}")
            # 如果失败，返回原图
            return img
    
    def draw_text_with_outline(self, img: np.ndarray, text: str, position: Tuple[int, int],
                              font_size: int = 20, text_color: Tuple[int, int, int] = (255, 255, 255),
                              outline_color: Tuple[int, int, int] = (0, 0, 0),
                              outline_width: int = 2, font_path: str = None) -> np.ndarray:
        """
        绘制带描边的中文文字
        
        Args:
            img: 输入图像 (BGR格式)
            text: 要绘制的文字
            position: 文字位置 (x, y)
            font_size: 字体大小
            text_color: 文字颜色 (RGB)
            outline_color: 描边颜色 (RGB)
            outline_width: 描边宽度
            font_path: 字体文件路径
            
        Returns:
            绘制文字后的图像
        """
        try:
            # 将BGR转换为RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(img_pil)
            
            # 获取字体
            font = self._get_font(font_size, font_path)
            
            x, y = position
            text_y = y - font_size
            
            # 绘制描边
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, text_y + dy), text, font=font, fill=outline_color)
            
            # 绘制主文字
            draw.text((x, text_y), text, font=font, fill=text_color)
            
            # 转换回BGR格式
            img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
            return img_bgr
            
        except Exception as e:
            logger.error(f"绘制带描边中文文字失败: {e}")
            # 如果失败，返回原图
            return img


# 创建全局实例
chinese_renderer = ChineseTextRenderer()


def draw_chinese_text(img: np.ndarray, text: str, position: Tuple[int, int],
                     font_size: int = 20, color: Tuple[int, int, int] = (255, 255, 255),
                     background_color: Tuple[int, int, int] = None,
                     background_padding: int = 5) -> np.ndarray:
    """
    便捷函数：在图像上绘制中文文字
    
    Args:
        img: 输入图像 (BGR格式)
        text: 要绘制的文字
        position: 文字位置 (x, y)
        font_size: 字体大小
        color: 文字颜色 (RGB)
        background_color: 背景颜色 (RGB)，None表示不绘制背景
        background_padding: 背景内边距
        
    Returns:
        绘制文字后的图像
    """
    return chinese_renderer.draw_text_on_image(
        img, text, position, font_size, color, background_color, background_padding
    )


def draw_chinese_text_with_outline(img: np.ndarray, text: str, position: Tuple[int, int],
                                  font_size: int = 20, text_color: Tuple[int, int, int] = (255, 255, 255),
                                  outline_color: Tuple[int, int, int] = (0, 0, 0),
                                  outline_width: int = 2) -> np.ndarray:
    """
    便捷函数：绘制带描边的中文文字
    
    Args:
        img: 输入图像 (BGR格式)
        text: 要绘制的文字
        position: 文字位置 (x, y)
        font_size: 字体大小
        text_color: 文字颜色 (RGB)
        outline_color: 描边颜色 (RGB)
        outline_width: 描边宽度
        
    Returns:
        绘制文字后的图像
    """
    return chinese_renderer.draw_text_with_outline(
        img, text, position, font_size, text_color, outline_color, outline_width
    )
