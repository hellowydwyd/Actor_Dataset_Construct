"""
日志管理模块
"""
import os
from pathlib import Path
from loguru import logger
from .config_loader import config


def setup_logger():
    """设置日志配置"""
    logging_config = config.get_logging_config()
    
    # 移除默认处理器
    logger.remove()
    
    # 获取日志级别
    log_level = logging_config.get('level', 'INFO')
    
    # 控制台输出
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )
    
    # 文件输出
    log_file = logging_config.get('file')
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            sink=log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=logging_config.get('max_size', '10MB'),
            retention=logging_config.get('backup_count', 5),
            encoding='utf-8'
        )
    
    return logger


# 初始化日志器
setup_logger()


def get_logger(name: str = None):
    """
    获取日志器实例
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器实例
    """
    if name:
        return logger.bind(name=name)
    return logger
