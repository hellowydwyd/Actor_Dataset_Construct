"""
角色颜色和框形管理器
为每个电影的角色分配独特的颜色和框形
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ColorManager:
    """角色颜色和框形管理器"""
    
    # 预定义的颜色调色板 (BGR格式，适用于OpenCV)
    COLOR_PALETTE = [
        (0, 255, 0),      # 绿色 - 主角
        (255, 0, 0),      # 蓝色 - 重要角色
        (0, 165, 255),    # 橙色 - 配角
        (255, 255, 0),    # 青色 - 次要角色
        (255, 0, 255),    # 洋红色
        (0, 255, 255),    # 黄色
        (128, 0, 128),    # 紫色
        (255, 165, 0),    # 蓝橙色
        (0, 128, 255),    # 橙红色
        (255, 20, 147),   # 深粉色
        (50, 205, 50),    # 酸橙绿
        (255, 69, 0),     # 红橙色
        (138, 43, 226),   # 蓝紫色
        (255, 215, 0),    # 金色
        (220, 20, 60),    # 深红色
        (0, 191, 255),    # 深天蓝色
        (255, 105, 180),  # 热粉色
        (124, 252, 0),    # 草绿色
        (255, 140, 0),    # 深橙色
        (72, 61, 139),    # 深石板蓝
    ]
    
    # 框形类型
    SHAPE_TYPES = {
        'rectangle': '矩形框',
        'rounded_rectangle': '圆角矩形',
        'circle': '圆形框',
        'ellipse': '椭圆框',
        'diamond': '菱形框'
    }
    
    def __init__(self, storage_dir: str = "./data/metadata"):
        """
        初始化颜色管理器
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.color_config_file = self.storage_dir / "color_config.json"
        self.color_config = self._load_color_config()
        
        logger.info("颜色管理器初始化完成")
    
    def _load_color_config(self) -> Dict[str, Any]:
        """加载颜色配置"""
        if self.color_config_file.exists():
            try:
                with open(self.color_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"加载颜色配置成功，包含 {len(config.get('movies', {}))} 部电影")
                return config
            except Exception as e:
                logger.error(f"加载颜色配置失败: {e}")
        
        # 返回默认配置
        return {
            'version': '1.0',
            'created_at': '',
            'movies': {},
            'global_settings': {
                'default_shape': 'rectangle',
                'line_thickness': 2,
                'font_scale': 0.6,
                'font_thickness': 2
            }
        }
    
    def _save_color_config(self) -> bool:
        """保存颜色配置"""
        try:
            with open(self.color_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.color_config, f, ensure_ascii=False, indent=2)
            logger.info("颜色配置保存成功")
            return True
        except Exception as e:
            logger.error(f"保存颜色配置失败: {e}")
            return False
    
    def assign_colors_for_movie(self, movie_title: str, characters: List[str], 
                               shape_type: str = 'rectangle') -> Dict[str, Dict[str, Any]]:
        """
        为电影的角色分配颜色和框形
        
        Args:
            movie_title: 电影标题
            characters: 角色列表
            shape_type: 框形类型
            
        Returns:
            角色颜色配置字典
        """
        logger.info(f"为电影 '{movie_title}' 的 {len(characters)} 个角色分配颜色")
        
        # 如果电影已存在配置，先检查是否需要更新
        if movie_title in self.color_config['movies']:
            existing_config = self.color_config['movies'][movie_title]
            existing_characters = set(existing_config.get('characters', {}).keys())
            new_characters = set(characters)
            
            # 如果角色列表完全相同，直接返回现有配置
            if existing_characters == new_characters:
                logger.info(f"电影 '{movie_title}' 已有完整的颜色配置")
                return existing_config['characters']
            
            # 如果有新角色，为新角色分配颜色
            characters_to_assign = list(new_characters - existing_characters)
            if characters_to_assign:
                logger.info(f"为电影 '{movie_title}' 的 {len(characters_to_assign)} 个新角色分配颜色")
        else:
            characters_to_assign = characters
            self.color_config['movies'][movie_title] = {
                'characters': {},
                'shape_type': shape_type,
                'created_at': '',
                'updated_at': ''
            }
        
        # 获取已使用的颜色索引
        used_color_indices = set()
        if movie_title in self.color_config['movies']:
            for char_config in self.color_config['movies'][movie_title]['characters'].values():
                used_color_indices.add(char_config.get('color_index', 0))
        
        # 为角色分配颜色
        character_configs = {}
        available_colors = [i for i in range(len(self.COLOR_PALETTE)) if i not in used_color_indices]
        
        # 如果可用颜色不足，重新开始使用颜色
        if len(available_colors) < len(characters_to_assign):
            available_colors = list(range(len(self.COLOR_PALETTE)))
            random.shuffle(available_colors)
        
        for i, character in enumerate(characters_to_assign):
            color_index = available_colors[i % len(available_colors)]
            color_bgr = self.COLOR_PALETTE[color_index]
            
            character_config = {
                'character_name': character,
                'color_bgr': color_bgr,
                'color_rgb': (color_bgr[2], color_bgr[1], color_bgr[0]),  # 转换为RGB
                'color_hex': f"#{color_bgr[2]:02x}{color_bgr[1]:02x}{color_bgr[0]:02x}",
                'color_index': color_index,
                'shape_type': shape_type,
                'line_thickness': self.color_config['global_settings']['line_thickness'],
                'priority': i,  # 角色优先级，0为最高
            }
            
            character_configs[character] = character_config
            self.color_config['movies'][movie_title]['characters'][character] = character_config
        
        # 更新电影配置
        self.color_config['movies'][movie_title]['shape_type'] = shape_type
        self.color_config['movies'][movie_title]['updated_at'] = ''
        
        # 保存配置
        self._save_color_config()
        
        # 返回完整的角色配置
        return self.color_config['movies'][movie_title]['characters']
    
    def get_character_color(self, movie_title: str, character_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定角色的颜色配置
        
        Args:
            movie_title: 电影标题
            character_name: 角色名称
            
        Returns:
            颜色配置字典或None
        """
        if movie_title in self.color_config['movies']:
            characters = self.color_config['movies'][movie_title].get('characters', {})
            return characters.get(character_name)
        return None
    
    def get_movie_color_config(self, movie_title: str) -> Optional[Dict[str, Any]]:
        """
        获取电影的完整颜色配置
        
        Args:
            movie_title: 电影标题
            
        Returns:
            电影颜色配置字典或None
        """
        return self.color_config['movies'].get(movie_title)
    
    def get_all_color_configs(self) -> Dict[str, Any]:
        """获取所有颜色配置"""
        return self.color_config
    
    def update_character_shape(self, movie_title: str, character_name: str, 
                             shape_type: str) -> bool:
        """
        更新角色的框形类型
        
        Args:
            movie_title: 电影标题
            character_name: 角色名称
            shape_type: 新的框形类型
            
        Returns:
            是否更新成功
        """
        if movie_title in self.color_config['movies']:
            characters = self.color_config['movies'][movie_title].get('characters', {})
            if character_name in characters:
                characters[character_name]['shape_type'] = shape_type
                self.color_config['movies'][movie_title]['updated_at'] = ''
                return self._save_color_config()
        
        logger.warning(f"未找到角色配置: {movie_title} - {character_name}")
        return False
    
    def delete_movie_config(self, movie_title: str) -> bool:
        """
        删除电影的颜色配置
        
        Args:
            movie_title: 电影标题
            
        Returns:
            是否删除成功
        """
        if movie_title in self.color_config['movies']:
            del self.color_config['movies'][movie_title]
            logger.info(f"删除电影 '{movie_title}' 的颜色配置")
            return self._save_color_config()
        return False
    
    def get_color_palette_info(self) -> List[Dict[str, Any]]:
        """获取颜色调色板信息"""
        palette_info = []
        for i, color_bgr in enumerate(self.COLOR_PALETTE):
            color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
            color_hex = f"#{color_rgb[0]:02x}{color_rgb[1]:02x}{color_rgb[2]:02x}"
            
            palette_info.append({
                'index': i,
                'color_bgr': color_bgr,
                'color_rgb': color_rgb,
                'color_hex': color_hex,
                'name': f"Color {i+1}"
            })
        
        return palette_info
    
    def export_color_dictionary(self) -> Dict[str, Any]:
        """
        导出颜色字典，用于数据导出
        
        Returns:
            包含所有电影和角色颜色信息的字典
        """
        export_data = {
            'color_dictionary': {
                'version': self.color_config.get('version', '1.0'),
                'export_time': '',
                'movies': {},
                'color_palette': self.get_color_palette_info(),
                'shape_types': self.SHAPE_TYPES
            }
        }
        
        # 处理每部电影的颜色配置
        for movie_title, movie_config in self.color_config['movies'].items():
            export_data['color_dictionary']['movies'][movie_title] = {
                'title': movie_title,
                'shape_type': movie_config.get('shape_type', 'rectangle'),
                'character_count': len(movie_config.get('characters', {})),
                'characters': movie_config.get('characters', {}),
                'created_at': movie_config.get('created_at', ''),
                'updated_at': movie_config.get('updated_at', '')
            }
        
        return export_data
