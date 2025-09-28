"""
配置文件加载器
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的config/config.yaml
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 加载环境变量
        env_path = self.config_path.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def get(self, key_path: str, default=None):
        """
        获取配置值，支持嵌套键访问
        
        Args:
            key_path: 配置键路径，如 'tmdb.api_key'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_tmdb_config(self) -> Dict[str, Any]:
        """获取TMDB配置"""
        tmdb_config = self.get('tmdb', {})
        
        # 从环境变量获取API密钥
        api_key = os.getenv('TMDB_API_KEY')
        if api_key:
            tmdb_config['api_key'] = api_key
            
        return tmdb_config
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """获取爬虫配置"""
        return self.get('crawler', {})
    
    def get_face_recognition_config(self) -> Dict[str, Any]:
        """获取人脸识别配置"""
        return self.get('face_recognition', {})
    
    def get_vector_database_config(self) -> Dict[str, Any]:
        """获取向量数据库配置"""
        return self.get('vector_database', {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        storage_config = self.get('storage', {})
        
        # 确保路径是绝对路径
        project_root = self.config_path.parent.parent
        for key in ['images_dir', 'embeddings_dir', 'metadata_dir']:
            if key in storage_config:
                path = Path(storage_config[key])
                if not path.is_absolute():
                    storage_config[key] = str(project_root / path)
        
        return storage_config
    
    def get_web_config(self) -> Dict[str, Any]:
        """获取Web配置"""
        return self.get('web', {})
    
    def get_video_processing_config(self) -> Dict[str, Any]:
        """获取视频处理配置"""
        return self.get('video_processing', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        logging_config = self.get('logging', {})
        
        # 确保日志文件路径是绝对路径
        if 'file' in logging_config:
            log_path = Path(logging_config['file'])
            if not log_path.is_absolute():
                project_root = self.config_path.parent.parent
                logging_config['file'] = str(project_root / log_path)
                
        return logging_config
    
    def update_config(self, key_path: str, value) -> bool:
        """
        更新配置值并保存到文件
        
        Args:
            key_path: 配置键路径，如 'face_recognition.max_faces_per_actor'
            value: 新的配置值
            
        Returns:
            是否成功更新
        """
        try:
            # 解析键路径
            keys = key_path.split('.')
            
            # 在内存中更新配置
            current_dict = self.config
            for key in keys[:-1]:
                if key not in current_dict:
                    current_dict[key] = {}
                current_dict = current_dict[key]
            
            # 设置最终值
            current_dict[keys[-1]] = value
            
            # 保存到文件
            return self.save_config()
            
        except Exception as e:
            print(f"更新配置失败 {key_path}={value}: {e}")
            return False
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            print(f"配置已保存到: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False


# 全局配置实例
config = ConfigLoader()
