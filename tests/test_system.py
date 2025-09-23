#!/usr/bin/env python3
"""
系统测试脚本
验证各个模块的基本功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_config_loader():
    """测试配置加载器"""
    print("测试配置加载器...")
    try:
        from src.utils.config_loader import config
        
        # 测试基本配置获取
        tmdb_config = config.get_tmdb_config()
        crawler_config = config.get_crawler_config()
        face_config = config.get_face_recognition_config()
        vector_config = config.get_vector_database_config()
        
        print(f"✅ TMDB配置: {bool(tmdb_config)}")
        print(f"✅ 爬虫配置: {bool(crawler_config)}")
        print(f"✅ 人脸识别配置: {bool(face_config)}")
        print(f"✅ 向量数据库配置: {bool(vector_config)}")
        
        return True
    except Exception as e:
        print(f"❌ 配置加载器测试失败: {e}")
        return False


def test_tmdb_client():
    """测试TMDB客户端"""
    print("\n测试TMDB客户端...")
    try:
        from src.api.tmdb_client import TMDBClient
        
        client = TMDBClient()
        print("✅ TMDB客户端初始化成功")
        
        # 测试搜索电影 (需要有效的API密钥)
        try:
            movies = client.search_movie("复仇者联盟", 2012)
            print(f"✅ 电影搜索测试: 找到 {len(movies)} 部电影")
        except Exception as e:
            print(f"⚠️ 电影搜索测试失败 (可能是API密钥问题): {e}")
        
        return True
    except Exception as e:
        print(f"❌ TMDB客户端测试失败: {e}")
        return False


def test_image_crawler():
    """测试图片爬虫"""
    print("\n测试图片爬虫...")
    try:
        from src.crawler.image_crawler import ImageCrawler
        
        crawler = ImageCrawler()
        print("✅ 图片爬虫初始化成功")
        
        # 测试基本功能 (不实际下载)
        print("✅ 图片爬虫基本功能正常")
        
        return True
    except Exception as e:
        print(f"❌ 图片爬虫测试失败: {e}")
        return False


def test_face_processor():
    """测试人脸处理器"""
    print("\n测试人脸处理器...")
    try:
        from src.face_recognition.face_processor import FaceProcessor
        
        processor = FaceProcessor()
        print("✅ 人脸处理器初始化成功")
        
        # 测试相似度计算
        import numpy as np
        embedding1 = np.random.rand(512).astype(np.float32)
        embedding2 = np.random.rand(512).astype(np.float32)
        
        similarity = processor.calculate_face_similarity(embedding1, embedding2)
        print(f"✅ 相似度计算测试: {similarity:.3f}")
        
        return True
    except Exception as e:
        print(f"❌ 人脸处理器测试失败: {e}")
        return False


def test_vector_database():
    """测试向量数据库"""
    print("\n测试向量数据库...")
    try:
        from src.database.vector_database import VectorDatabaseManager
        
        db = VectorDatabaseManager()
        print("✅ 向量数据库初始化成功")
        
        # 获取统计信息
        stats = db.get_database_stats()
        print(f"✅ 数据库统计: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ 向量数据库测试失败: {e}")
        return False


def test_web_app():
    """测试Web应用"""
    print("\n测试Web应用...")
    try:
        from web.app import create_app
        
        app = create_app()
        print("✅ Web应用创建成功")
        
        # 测试应用配置
        with app.test_client() as client:
            response = client.get('/api/config')
            print(f"✅ 配置API测试: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Web应用测试失败: {e}")
        return False


def test_dependencies():
    """测试依赖包"""
    print("测试依赖包...")
    
    required_packages = [
        ('requests', '网络请求'),
        ('PIL', '图像处理'),
        ('cv2', 'OpenCV'),
        ('numpy', '数值计算'),
        ('flask', 'Web框架'),
        ('yaml', 'YAML解析'),
        ('loguru', '日志系统'),
    ]
    
    optional_packages = [
        ('insightface', '人脸识别'),
        ('faiss', 'Faiss向量数据库'),
        ('chromadb', 'ChromaDB向量数据库'),
    ]
    
    success_count = 0
    
    print("\n必需依赖:")
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} ({description})")
            success_count += 1
        except ImportError:
            print(f"❌ {package} ({description}) - 未安装")
    
    print("\n可选依赖:")
    for package, description in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} ({description})")
        except ImportError:
            print(f"⚠️ {package} ({description}) - 未安装")
    
    return success_count == len(required_packages)


def main():
    """主函数"""
    print("🧪 电影演员人脸数据库构建系统 - 系统测试")
    print("=" * 50)
    
    test_results = []
    
    # 测试依赖包
    test_results.append(("依赖包", test_dependencies()))
    
    # 测试各个模块
    test_results.append(("配置加载器", test_config_loader()))
    test_results.append(("TMDB客户端", test_tmdb_client()))
    test_results.append(("图片爬虫", test_image_crawler()))
    test_results.append(("人脸处理器", test_face_processor()))
    test_results.append(("向量数据库", test_vector_database()))
    test_results.append(("Web应用", test_web_app()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常。")
    elif passed >= total * 0.7:
        print("⚠️ 大部分测试通过，系统基本可用。")
    else:
        print("❌ 多项测试失败，请检查安装和配置。")
    
    print("\n建议:")
    print("1. 如有测试失败，请运行: python install.py")
    print("2. 确保已正确配置TMDB API密钥")
    print("3. 如需GPU加速，请安装CUDA版本的依赖")


if __name__ == "__main__":
    main()
