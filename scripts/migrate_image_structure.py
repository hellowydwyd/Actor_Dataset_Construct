#!/usr/bin/env python3
"""
图片目录结构迁移脚本
将现有的按演员分类的图片目录迁移到按电影分类的新结构

使用方法:
python scripts/migrate_image_structure.py
"""

import os
import shutil
import json
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger
from src.utils.config_loader import config

logger = get_logger(__name__)


def load_metadata():
    """加载现有的元数据信息"""
    try:
        # 尝试从向量数据库获取元数据
        embeddings_dir = Path(config.get_storage_config()['embeddings_dir'])
        metadata_file = embeddings_dir / 'metadata.pkl'
        
        if metadata_file.exists():
            import pickle
            with open(metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            return metadata
        
        logger.warning("未找到metadata.pkl文件，将使用默认的未知电影分类")
        return []
        
    except Exception as e:
        logger.error(f"加载元数据失败: {e}")
        return []


def migrate_image_structure(dry_run=True):
    """
    迁移图片目录结构
    
    Args:
        dry_run: 是否只是预览操作，不实际移动文件
    """
    logger.info("开始迁移图片目录结构...")
    
    # 获取配置
    storage_config = config.get_storage_config()
    images_dir = Path(storage_config['images_dir'])
    
    if not images_dir.exists():
        logger.error(f"图片目录不存在: {images_dir}")
        return
    
    # 加载元数据
    metadata = load_metadata()
    
    # 构建演员到电影的映射
    actor_to_movie = {}
    for meta in metadata:
        actor_name = meta.get('actor_name')
        movie_title = meta.get('movie_title')
        if actor_name and movie_title:
            actor_to_movie[actor_name] = movie_title
    
    logger.info(f"从元数据中找到 {len(actor_to_movie)} 个演员的电影信息")
    
    # 找出需要迁移的演员目录
    migration_plan = []
    
    for item in images_dir.iterdir():
        if item.is_dir() and item.name != 'aligned_faces':
            # 检查是否是演员目录（旧格式）
            if '_' in item.name:
                # 可能的格式: "123_演员名"
                parts = item.name.split('_', 1)
                if len(parts) == 2 and parts[0].isdigit():
                    actor_name = parts[1]
                else:
                    actor_name = item.name
            else:
                actor_name = item.name
            
            # 查找对应的电影
            movie_title = actor_to_movie.get(actor_name, "unknown_movie")
            
            # 清理电影名称
            safe_movie_title = "".join(c for c in movie_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # 新的目录路径
            new_path = images_dir / safe_movie_title / item.name
            
            migration_plan.append({
                'old_path': item,
                'new_path': new_path,
                'actor_name': actor_name,
                'movie_title': movie_title
            })
    
    logger.info(f"计划迁移 {len(migration_plan)} 个演员目录")
    
    # 执行迁移
    migrated_count = 0
    error_count = 0
    
    for plan in migration_plan:
        old_path = plan['old_path']
        new_path = plan['new_path']
        actor_name = plan['actor_name']
        movie_title = plan['movie_title']
        
        try:
            if dry_run:
                logger.info(f"[预览] 将移动: {old_path.name} -> {movie_title}/{old_path.name}")
            else:
                # 创建电影目录
                new_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 移动演员目录
                shutil.move(str(old_path), str(new_path))
                logger.info(f"已移动: {old_path.name} -> {movie_title}/{old_path.name}")
                migrated_count += 1
                
        except Exception as e:
            logger.error(f"迁移失败 {old_path.name}: {e}")
            error_count += 1
    
    # 输出结果
    if dry_run:
        logger.info(f"预览完成: 计划迁移 {len(migration_plan)} 个目录")
        logger.info("如需执行实际迁移，请使用 --execute 参数")
    else:
        logger.info(f"迁移完成: 成功 {migrated_count} 个，失败 {error_count} 个")
        
        # 清理空目录
        cleanup_empty_directories(images_dir)


def cleanup_empty_directories(images_dir):
    """清理空目录"""
    try:
        for item in images_dir.iterdir():
            if item.is_dir() and item.name != 'aligned_faces':
                # 检查是否为空目录
                if not any(item.iterdir()):
                    item.rmdir()
                    logger.info(f"删除空目录: {item.name}")
    except Exception as e:
        logger.error(f"清理空目录失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移图片目录结构')
    parser.add_argument('--execute', action='store_true', 
                       help='执行实际迁移（默认只预览）')
    
    args = parser.parse_args()
    
    if args.execute:
        logger.info("执行实际迁移...")
        migrate_image_structure(dry_run=False)
    else:
        logger.info("预览模式，不会实际移动文件...")
        migrate_image_structure(dry_run=True)


if __name__ == '__main__':
    main()
