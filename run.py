#!/usr/bin/env python3
"""
快速启动脚本
提供便捷的系统启动方式
"""
import os
import sys
import argparse
from pathlib import Path


def activate_venv():
    """激活虚拟环境"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("❌ 虚拟环境不存在，请先运行: python install.py")
        return False
    
    # 设置虚拟环境路径
    if sys.platform.startswith('win'):
        venv_python = venv_path / "Scripts" / "python.exe"
        venv_bin = venv_path / "Scripts"
    else:
        venv_python = venv_path / "bin" / "python"
        venv_bin = venv_path / "bin"
    
    if not venv_python.exists():
        print("❌ 虚拟环境Python解释器不存在")
        return False
    
    # 更新环境变量
    os.environ["VIRTUAL_ENV"] = str(venv_path.absolute())
    os.environ["PATH"] = str(venv_bin) + os.pathsep + os.environ.get("PATH", "")
    
    # 更新sys.executable
    sys.executable = str(venv_python)
    
    return True


def check_config():
    """检查配置"""
    try:
        # 临时添加项目路径
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        from src.utils.config_loader import config
        
        # 检查TMDB API密钥
        tmdb_config = config.get_tmdb_config()
        api_key = tmdb_config.get('api_key')
        
        if not api_key or api_key == 'your_tmdb_api_key_here':
            print("⚠️ TMDB API密钥未配置")
            print("请编辑 config/config.yaml 或创建 .env 文件")
            print("设置 TMDB_API_KEY=你的API密钥")
            return False
        
        print("✅ 配置检查通过")
        return True
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保已安装所有依赖: python install.py")
        return False
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False


def run_command(cmd_args):
    """运行主程序命令"""
    try:
        # 导入主程序
        from main import main as main_func
        
        # 备份原始argv
        original_argv = sys.argv
        
        # 设置新的argv
        sys.argv = ['main.py'] + cmd_args
        
        try:
            main_func()
        finally:
            # 恢复原始argv
            sys.argv = original_argv
            
    except ImportError as e:
        print(f"❌ 导入主程序失败: {e}")
        return False
    except SystemExit:
        # main函数可能调用sys.exit()
        pass
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        return False
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="电影演员人脸数据库构建系统 - 快速启动")
    
    # 添加所有可能的参数
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 构建命令
    build_parser = subparsers.add_parser('build', help='构建演员数据集')
    build_parser.add_argument('--movie', '-m', required=True, help='电影名称')
    build_parser.add_argument('--year', '-y', type=int, help='上映年份')
    build_parser.add_argument('--max-actors', type=int, default=20, help='最大演员数量')
    
    # 搜索命令
    search_parser = subparsers.add_parser('search', help='搜索相似人脸')
    search_parser.add_argument('--image', '-i', required=True, help='查询图片路径')
    search_parser.add_argument('--top-k', '-k', type=int, default=10, help='返回结果数量')
    
    # 信息命令
    info_parser = subparsers.add_parser('info', help='显示数据库信息')
    
    # Web界面命令
    web_parser = subparsers.add_parser('web', help='启动Web界面')
    web_parser.add_argument('--host', default='0.0.0.0', help='主机地址')
    web_parser.add_argument('--port', type=int, default=5000, help='端口号')
    
    # 示例命令
    example_parser = subparsers.add_parser('example', help='运行使用示例')
    
    # 安装命令
    install_parser = subparsers.add_parser('install', help='安装系统依赖')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🎬 电影演员人脸数据库构建系统")
    print("=" * 40)
    
    # 特殊命令处理
    if args.command == 'install':
        print("运行安装脚本...")
        import subprocess
        subprocess.run([sys.executable, 'install.py'])
        return
    
    if args.command == 'example':
        print("运行使用示例...")
        import subprocess
        subprocess.run([sys.executable, 'example.py'])
        return
    
    # 激活虚拟环境 [[memory:6286680]]
    print("激活虚拟环境...")
    if not activate_venv():
        return
    
    # 检查配置
    print("检查系统配置...")
    if not check_config():
        return
    
    # 构建命令参数
    cmd_args = [args.command]
    
    if args.command == 'build':
        cmd_args.extend(['--movie', args.movie])
        if args.year:
            cmd_args.extend(['--year', str(args.year)])
        cmd_args.extend(['--max-actors', str(args.max_actors)])
    
    elif args.command == 'search':
        cmd_args.extend(['--image', args.image])
        cmd_args.extend(['--top-k', str(args.top_k)])
    
    elif args.command == 'web':
        cmd_args.extend(['--host', args.host])
        cmd_args.extend(['--port', str(args.port)])
    
    # 运行命令
    print(f"执行命令: {' '.join(cmd_args)}")
    print("-" * 40)
    
    run_command(cmd_args)


if __name__ == "__main__":
    main()
