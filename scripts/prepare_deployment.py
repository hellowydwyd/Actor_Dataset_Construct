#!/usr/bin/env python3
"""
部署前优化脚本
清理不必要的文件，优化项目结构
"""

import os
import shutil
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger(__name__)


def clean_pycache():
    """清理Python缓存文件"""
    logger.info("清理Python缓存文件...")
    
    for root, dirs, files in os.walk(project_root):
        # 删除__pycache__目录
        if '__pycache__' in dirs:
            pycache_path = Path(root) / '__pycache__'
            shutil.rmtree(pycache_path)
            logger.info(f"删除: {pycache_path}")
        
        # 删除.pyc文件
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = Path(root) / file
                pyc_path.unlink()
                logger.info(f"删除: {pyc_path}")


def clean_temp_files():
    """清理临时文件"""
    logger.info("清理临时文件...")
    
    temp_dirs = [
        project_root / 'temp',
        project_root / 'logs'
    ]
    
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            for file in temp_dir.iterdir():
                if file.is_file():
                    file.unlink()
                    logger.info(f"删除临时文件: {file}")


def optimize_requirements():
    """生成优化的依赖文件"""
    logger.info("生成生产环境依赖文件...")
    
    # 生产环境精简依赖
    prod_requirements = [
        "requests==2.31.0",
        "beautifulsoup4==4.12.2", 
        "pillow==10.0.1",
        "numpy==1.24.3",
        "opencv-python-headless==4.8.1.78",  # 无GUI版本
        "insightface==0.7.3",
        "onnxruntime==1.16.3",
        "scikit-learn==1.3.0",
        "faiss-cpu==1.7.4",
        "flask==3.0.0",
        "flask-cors==4.0.0",
        "tmdbv3api==1.9.0",
        "wget==3.2",
        "tqdm==4.66.1",
        "python-dotenv==1.0.0",
        "pyyaml==6.0.1",
        "loguru==0.7.2"
    ]
    
    # 写入生产环境要求文件
    prod_req_file = project_root / "requirements.prod.txt"
    with open(prod_req_file, 'w') as f:
        f.write('\n'.join(prod_requirements))
    
    logger.info(f"生成生产环境依赖: {prod_req_file}")


def create_deployment_info():
    """创建部署信息文件"""
    logger.info("创建部署信息文件...")
    
    deploy_info = {
        "app_name": "Actor Dataset Construct",
        "version": "1.0.0",
        "python_version": "3.9+",
        "memory_requirement": "2GB+",
        "storage_requirement": "5GB+",
        "start_command": "python run_web.py",
        "health_check": "/",
        "environment_variables": [
            "TMDB_API_KEY",
            "WEB_HOST",
            "WEB_PORT", 
            "WEB_DEBUG"
        ]
    }
    
    import json
    deploy_info_file = project_root / "deploy_info.json"
    with open(deploy_info_file, 'w', encoding='utf-8') as f:
        json.dump(deploy_info, f, indent=2, ensure_ascii=False)
    
    logger.info(f"创建部署信息: {deploy_info_file}")


def check_large_files():
    """检查大文件"""
    logger.info("检查大文件...")
    
    large_files = []
    for root, dirs, files in os.walk(project_root):
        for file in files:
            file_path = Path(root) / file
            try:
                size = file_path.stat().st_size
                if size > 50 * 1024 * 1024:  # 50MB
                    large_files.append((file_path, size / 1024 / 1024))
            except:
                continue
    
    if large_files:
        logger.warning("发现大文件 (>50MB):")
        for file_path, size_mb in large_files:
            logger.warning(f"  {file_path}: {size_mb:.1f}MB")
        logger.warning("考虑将大文件移至云存储或排除部署")
    else:
        logger.info("未发现过大文件")


def generate_gitignore():
    """生成或更新.gitignore"""
    logger.info("更新.gitignore文件...")
    
    gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Project specific
data/images/*
data/embeddings/*
data/metadata/*.db
logs/*.log
temp/*
.env

# OS
.DS_Store
Thumbs.db

# Large files
*.mp4
*.avi
*.mov
*.mkv
*.flv
*.wmv
"""
    
    gitignore_file = project_root / ".gitignore"
    with open(gitignore_file, 'w') as f:
        f.write(gitignore_content.strip())
    
    logger.info(f"更新.gitignore: {gitignore_file}")


def main():
    """主函数"""
    logger.info("开始准备部署...")
    
    try:
        clean_pycache()
        clean_temp_files()
        optimize_requirements()
        create_deployment_info()
        check_large_files()
        generate_gitignore()
        
        logger.info("部署准备完成！")
        print("\n🎉 部署准备完成！")
        print("\n📋 下一步操作:")
        print("1. 检查并提交代码到GitHub")
        print("2. 在Railway/Render创建新项目")  
        print("3. 连接GitHub仓库")
        print("4. 配置环境变量")
        print("5. 等待自动部署完成")
        
    except Exception as e:
        logger.error(f"准备部署失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
