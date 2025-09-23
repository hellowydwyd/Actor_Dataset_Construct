"""
电影演员人脸数据库构建系统主程序
"""
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.tmdb_client import TMDBClient
from src.crawler.image_crawler import ImageCrawler
from src.face_recognition.face_processor import FaceProcessor
from src.database.vector_database import VectorDatabaseManager
from src.utils.color_manager import ColorManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ActorDatasetBuilder:
    """演员数据集构建器"""
    
    def __init__(self):
        """初始化构建器"""
        logger.info("初始化演员数据集构建器...")
        
        try:
            self.tmdb_client = TMDBClient()
            self.image_crawler = ImageCrawler()
            self.face_processor = FaceProcessor()
            self.vector_db = VectorDatabaseManager()
            self.color_manager = ColorManager()
            
            logger.info("所有模块初始化成功")
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            raise
    
    def build_dataset_from_movie(self, movie_title: str, year: int = None, 
                               max_actors: int = 20, shape_type: str = 'rectangle') -> Dict[str, Any]:
        """
        从电影构建演员数据集
        
        Args:
            movie_title: 电影标题
            year: 上映年份
            max_actors: 最大演员数量
            shape_type: 人脸框形状类型
            
        Returns:
            构建结果统计
        """
        logger.info(f"开始为电影 '{movie_title}' 构建演员数据集")
        
        results = {
            'movie_title': movie_title,
            'actors_found': 0,
            'images_collected': 0,
            'faces_processed': 0,
            'embeddings_added': 0,
            'errors': []
        }
        
        try:
            # 1. 获取电影演员信息
            logger.info("步骤1: 获取电影演员信息...")
            actors = self.tmdb_client.get_movie_actors(movie_title, year, max_actors)
            
            if not actors:
                error_msg = f"未找到电影 '{movie_title}' 的演员信息"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
            
            results['actors_found'] = len(actors)
            logger.info(f"找到 {len(actors)} 位演员")
            
            # 2. 为角色分配颜色和框形
            logger.info("步骤2: 分配角色颜色和框形...")
            characters = [actor.get('character', actor['name']) for actor in actors]
            color_config = self.color_manager.assign_colors_for_movie(
                movie_title, characters, shape_type
            )
            logger.info(f"为 {len(color_config)} 个角色分配了颜色")
            
            # 3. 收集演员图片
            logger.info("步骤3: 收集演员图片...")
            image_results = self.image_crawler.batch_collect_images(actors, movie_title)
            
            # 统计图片数量
            total_images = sum(len(paths) for paths in image_results.values())
            results['images_collected'] = total_images
            logger.info(f"共收集 {total_images} 张图片")
            
            if total_images == 0:
                error_msg = "未收集到任何图片"
                logger.warning(error_msg)
                results['errors'].append(error_msg)
                return results
            
            # 4. 处理人脸并提取特征
            logger.info("步骤4: 处理人脸并提取特征...")
            all_faces = []
            
            for actor in actors:
                actor_name = actor['name']
                image_paths = image_results.get(actor_name, [])
                
                if not image_paths:
                    logger.warning(f"演员 {actor_name} 没有图片，跳过")
                    continue
                
                logger.info(f"处理演员 {actor_name} 的 {len(image_paths)} 张图片")
                
                # 批量处理图片
                faces = self.face_processor.batch_process_images(image_paths)
                
                # 为每张人脸添加演员和角色信息
                for face in faces:
                    face['actor_name'] = actor_name
                    face['actor_id'] = actor.get('id')
                    face['character'] = actor.get('character', actor_name)  # 优先使用角色名，备用演员名
                    face['movie_title'] = movie_title
                    
                    # 添加颜色和框形信息
                    character_name = face['character']
                    character_color_config = color_config.get(character_name, {})
                    if character_color_config:
                        face['color_bgr'] = character_color_config.get('color_bgr')
                        face['color_rgb'] = character_color_config.get('color_rgb')
                        face['color_hex'] = character_color_config.get('color_hex')
                        face['color_index'] = character_color_config.get('color_index')
                        face['shape_type'] = character_color_config.get('shape_type', shape_type)
                        face['line_thickness'] = character_color_config.get('line_thickness', 2)
                        face['character_priority'] = character_color_config.get('priority', 0)
                    
                    # 生成唯一的face_id（基于角色和电影）
                    face_id = f"{movie_title}_{character_name}_{face['face_id']}_{hash(face['image_path']) % 10000}"
                    face['face_id'] = face_id
                
                # 筛选最佳人脸
                best_faces = self.face_processor.filter_best_faces(faces, max_faces=5)
                all_faces.extend(best_faces)
                
                logger.info(f"从 {actor_name} 的图片中提取 {len(best_faces)} 张高质量人脸")
            
            results['faces_processed'] = len(all_faces)
            logger.info(f"共处理 {len(all_faces)} 张人脸")
            
            if not all_faces:
                error_msg = "未检测到任何人脸"
                logger.warning(error_msg)
                results['errors'].append(error_msg)
                return results
            
            # 5. 添加到向量数据库
            logger.info("步骤5: 添加到向量数据库...")
            success = self.vector_db.add_face_embeddings(all_faces)
            
            if success:
                results['embeddings_added'] = len(all_faces)
                logger.info(f"成功添加 {len(all_faces)} 个人脸嵌入向量到数据库")
            else:
                error_msg = "添加到向量数据库失败"
                logger.error(error_msg)
                results['errors'].append(error_msg)
            
            # 5. 显示统计信息
            db_stats = self.vector_db.get_database_stats()
            logger.info(f"数据库统计: {db_stats}")
            
            logger.info(f"电影 '{movie_title}' 数据集构建完成!")
            
        except Exception as e:
            error_msg = f"构建数据集时发生错误: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def search_similar_face(self, image_path: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        搜索相似人脸
        
        Args:
            image_path: 查询图片路径
            top_k: 返回结果数量
            
        Returns:
            相似人脸列表
        """
        logger.info(f"搜索与 {image_path} 相似的人脸")
        
        try:
            # 处理查询图片
            faces = self.face_processor.process_image(image_path)
            
            if not faces:
                logger.warning("查询图片中未检测到人脸")
                return []
            
            # 使用第一张人脸进行搜索
            query_embedding = faces[0]['embedding']
            
            # 搜索相似人脸
            results = self.vector_db.search_similar_faces(query_embedding, top_k)
            
            logger.info(f"找到 {len(results)} 个相似结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索相似人脸失败: {e}")
            return []
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        return self.vector_db.get_database_stats()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="电影演员人脸数据库构建系统")
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 构建数据集命令
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'build':
            # 构建数据集
            builder = ActorDatasetBuilder()
            results = builder.build_dataset_from_movie(
                movie_title=args.movie,
                year=args.year,
                max_actors=args.max_actors
            )
            
            print("\n=== 构建结果 ===")
            print(f"电影: {results['movie_title']}")
            print(f"演员数量: {results['actors_found']}")
            print(f"收集图片: {results['images_collected']}")
            print(f"处理人脸: {results['faces_processed']}")
            print(f"添加向量: {results['embeddings_added']}")
            
            if results['errors']:
                print(f"错误信息: {', '.join(results['errors'])}")
        
        elif args.command == 'search':
            # 搜索相似人脸
            builder = ActorDatasetBuilder()
            results = builder.search_similar_face(args.image, args.top_k)
            
            print(f"\n=== 相似人脸搜索结果 ===")
            print(f"查询图片: {args.image}")
            print(f"找到 {len(results)} 个相似结果:\n")
            
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                print(f"{i}. 演员: {metadata.get('actor_name', 'Unknown')}")
                print(f"   相似度: {result['similarity']:.3f}")
                print(f"   图片: {metadata.get('image_path', 'Unknown')}")
                print(f"   检测分数: {metadata.get('det_score', 0):.3f}")
                print()
        
        elif args.command == 'info':
            # 显示数据库信息
            builder = ActorDatasetBuilder()
            info = builder.get_database_info()
            
            print("\n=== 数据库信息 ===")
            for key, value in info.items():
                print(f"{key}: {value}")
        
        elif args.command == 'web':
            # 启动Web界面
            import os
            from web.app import create_app
            
            # 从环境变量获取配置，命令行参数优先
            host = os.getenv('WEB_HOST', args.host)
            port = int(os.getenv('WEB_PORT', os.getenv('PORT', args.port)))
            debug = os.getenv('WEB_DEBUG', 'true').lower() == 'true'
            
            logger.info(f"启动Web界面... (Host: {host}, Port: {port}, Debug: {debug})")
            app = create_app()
            app.run(host=host, port=port, debug=debug)
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
