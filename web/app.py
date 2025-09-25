"""
Web应用程序
提供可视化的管理和查询界面
"""
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort, Response
from flask_cors import CORS
import threading
import queue
import json
import base64
import io
from PIL import Image
import numpy as np
import cv2
import mimetypes
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.tmdb_client import TMDBClient
from src.crawler.image_crawler import ImageCrawler
from src.face_recognition.face_processor import FaceProcessor
from src.database.vector_database import VectorDatabaseManager
from src.video_recognition.video_processor import VideoFaceRecognizer
from src.utils.config_loader import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    CORS(app)
    
    # 全局进度队列
    progress_queues = {}
    
    # 配置
    web_config = config.get_web_config()
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
    
    # 初始化组件
    try:
        tmdb_client = TMDBClient()
        image_crawler = ImageCrawler()
        face_processor = FaceProcessor()
        vector_db = VectorDatabaseManager()
        video_recognizer = VideoFaceRecognizer(long_video_mode=True)  # 默认启用长视频模式
        logger.info("Web应用组件初始化成功")
    except Exception as e:
        logger.error(f"Web应用组件初始化失败: {e}")
        tmdb_client = image_crawler = face_processor = vector_db = video_recognizer = None
    
    def process_single_frame_with_compression(frame):
        """处理单帧并进行必要的压缩"""
        # 如果图片太大，进行压缩
        height, width = frame.shape[:2]
        max_size = 1920  # 最大边长
        
        if max(height, width) > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"图片已压缩: {width}x{height} -> {new_width}x{new_height}")
        
        # 处理帧
        return video_recognizer.process_single_frame(frame)
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    @app.route('/api/search_movie', methods=['POST'])
    def search_movie():
        """搜索电影"""
        try:
            data = request.get_json()
            movie_title = data.get('movie_title', '').strip()
            year = data.get('year')
            
            if not movie_title:
                return jsonify({'error': '请输入电影名称'}), 400
            
            if not tmdb_client:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 搜索电影
            movies = tmdb_client.search_movie(movie_title, year)
            
            return jsonify({
                'success': True,
                'movies': movies[:10]  # 限制返回数量
            })
            
        except Exception as e:
            logger.error(f"搜索电影失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/get_movie_actors', methods=['POST'])
    def get_movie_actors():
        """获取电影演员"""
        try:
            data = request.get_json()
            movie_title = data.get('movie_title', '').strip()
            year = data.get('year')
            max_actors = data.get('max_actors', 20)
            
            if not movie_title:
                return jsonify({'error': '请输入电影名称'}), 400
            
            if not tmdb_client:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 获取演员信息
            actors = tmdb_client.get_movie_actors(movie_title, year, max_actors)
            
            return jsonify({
                'success': True,
                'actors': actors
            })
            
        except Exception as e:
            logger.error(f"获取演员信息失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/build_dataset', methods=['POST'])
    def build_dataset():
        """构建数据集"""
        try:
            data = request.get_json()
            movie_title = data.get('movie_title', '').strip()
            year = data.get('year')
            max_actors = data.get('max_actors', 20)
            shape_type = data.get('shape_type', 'rectangle')
            
            if not movie_title:
                return jsonify({'error': '请输入电影名称'}), 400
            
            if not all([tmdb_client, image_crawler, face_processor, vector_db]):
                return jsonify({'error': '系统未初始化'}), 500
            
            # 这里应该使用异步任务处理，简化起见直接处理
            from main import ActorDatasetBuilder
            builder = ActorDatasetBuilder()
            
            results = builder.build_dataset_from_movie(movie_title, year, max_actors, shape_type)
            
            return jsonify({
                'success': True,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"构建数据集失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/search_face', methods=['POST'])
    def search_face():
        """人脸搜索"""
        try:
            if 'image' not in request.files:
                return jsonify({'error': '请上传图片'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': '请选择图片文件'}), 400
            
            top_k = int(request.form.get('top_k', 10))
            similarity_threshold = float(request.form.get('similarity_threshold', 0.6))
            
            if not face_processor or not vector_db:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 保存临时文件
            temp_dir = Path('./temp')
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"query_{file.filename}"
            file.save(temp_path)
            
            try:
                # 处理查询图片
                faces = face_processor.process_image(str(temp_path))
                
                if not faces:
                    return jsonify({'error': '图片中未检测到人脸'}), 400
                
                # 使用第一张人脸搜索
                query_embedding = faces[0]['embedding']
                results = vector_db.search_similar_faces(query_embedding, top_k, similarity_threshold)
                
                return jsonify({
                    'success': True,
                    'results': results,
                    'query_face_info': {
                        'det_score': faces[0]['det_score'],
                        'bbox': faces[0]['bbox']
                    }
                })
                
            finally:
                # 清理临时文件
                if temp_path.exists():
                    temp_path.unlink()
            
        except Exception as e:
            logger.error(f"人脸搜索失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/database_stats')
    def database_stats():
        """获取数据库统计信息"""
        try:
            # 重新创建vector_db实例以获取最新数据
            try:
                from src.database.vector_database import VectorDatabaseManager
                fresh_vector_db = VectorDatabaseManager()
                stats = fresh_vector_db.get_database_stats()
                logger.info(f'获取数据库统计信息成功: {stats}')
            except Exception as init_error:
                logger.warning(f'重新初始化向量数据库失败，使用现有实例: {init_error}')
                if not vector_db:
                    logger.error('向量数据库未初始化')
                    return jsonify({'success': False, 'error': '系统未初始化'}), 500
                stats = vector_db.get_database_stats()
                logger.info(f'使用现有实例获取统计信息: {stats}')
            
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/config')
    def get_config():
        """获取配置信息"""
        try:
            return jsonify({
                'success': True,
                'config': {
                    'tmdb_configured': bool(config.get_tmdb_config().get('api_key') and 
                                          config.get_tmdb_config().get('api_key') != 'your_tmdb_api_key_here'),
                    'face_recognition_model': config.get_face_recognition_config().get('model_name', 'buffalo_l'),
                    'vector_database_type': config.get_vector_database_config().get('type', 'faiss'),
                    'max_images_per_actor': config.get_crawler_config().get('max_images_per_actor', 20)
                }
            })
            
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/database_preview')
    def database_preview():
        """获取数据库内容预览"""
        try:
            logger.info('获取数据库内容预览请求')
            
            # 重新创建vector_db实例以获取最新数据
            try:
                from src.database.vector_database import VectorDatabaseManager
                current_vector_db = VectorDatabaseManager()
                stats = current_vector_db.get_database_stats()
                logger.info(f'使用新实例获取数据库统计信息: {stats}')
            except Exception as init_error:
                logger.warning(f'重新初始化向量数据库失败，使用现有实例: {init_error}')
                if not vector_db:
                    logger.error('向量数据库未初始化')
                    return jsonify({'success': False, 'error': '系统未初始化'}), 500
                current_vector_db = vector_db
                stats = vector_db.get_database_stats()
                logger.info(f'使用现有实例获取统计信息: {stats}')
            
            # 初始化变量
            movies_list = []
            movies_stats = []
            quality_stats = {'high': 0, 'medium': 0, 'low': 0}
            total_characters = 0
            
            # 如果有数据，按电影-角色分组解析metadata
            if hasattr(current_vector_db, 'database') and hasattr(current_vector_db.database, 'metadata') and current_vector_db.database.metadata:
                logger.info(f'开始处理 {len(current_vector_db.database.metadata)} 条metadata记录')
                # 按电影分组，再按角色分组
                movies_dict = {}
                
                for meta in current_vector_db.database.metadata:
                    movie_title = meta.get('movie_title', '未知电影')
                    character_name = meta.get('character', meta.get('actor_name', 'Unknown Character'))
                    actor_name = meta.get('actor_name', 'Unknown Actor')
                    actor_id = meta.get('actor_id')
                    det_score = meta.get('det_score', 0)
                    
                    # 初始化电影数据
                    if movie_title not in movies_dict:
                        movies_dict[movie_title] = {
                            'title': movie_title,
                            'characters': {},
                            'total_faces': 0,
                            'total_quality': 0
                        }
                    
                    movie_data = movies_dict[movie_title]
                    
                    # 初始化角色数据
                    if character_name not in movie_data['characters']:
                        # 查找角色头像（使用演员头像）
                        avatar_path = find_actor_avatar(actor_name, actor_id)
                        
                        movie_data['characters'][character_name] = {
                            'character_name': character_name,
                            'actor_name': actor_name,
                            'actor_id': actor_id,
                            'face_count': 0,
                            'total_quality': 0,
                            'embedding_count': 0,
                            'avatar_path': avatar_path
                        }
                    
                    character_data = movie_data['characters'][character_name]
                    character_data['face_count'] += 1
                    character_data['total_quality'] += det_score
                    character_data['embedding_count'] += 1
                    
                    movie_data['total_faces'] += 1
                    movie_data['total_quality'] += det_score
                
                # 计算平均质量并转换为列表结构
                movies_list = []
                total_characters = 0
                
                for movie_title, movie_data in movies_dict.items():
                    # 计算电影的平均质量
                    movie_data['avg_quality'] = movie_data['total_quality'] / movie_data['total_faces'] if movie_data['total_faces'] > 0 else 0
                    
                    # 转换角色字典为列表
                    characters_list = []
                    for character_name, character_data in movie_data['characters'].items():
                        character_data['avg_quality'] = character_data['total_quality'] / character_data['face_count'] if character_data['face_count'] > 0 else 0
                        
                        # 质量分布统计
                        quality_score = character_data['avg_quality']
                        if quality_score >= 0.8:
                            quality_stats['high'] += 1
                        elif quality_score >= 0.6:
                            quality_stats['medium'] += 1
                        else:
                            quality_stats['low'] += 1
                        
                        characters_list.append(character_data)
                        total_characters += 1
                    
                    movie_data['characters'] = characters_list
                    movie_data['character_count'] = len(characters_list)
                    movies_list.append(movie_data)
                
                # 按角色数量排序
                movies_list.sort(key=lambda x: x['character_count'], reverse=True)
                
                # 电影统计
                movies_stats = [{'name': movie['title'], 'character_count': movie['character_count']} for movie in movies_list]
            else:
                # 数据库为空时的默认值
                logger.info('数据库为空，使用默认值')
                movies_list = []
                movies_stats = []
                total_characters = 0
            
            overview = {
                'total_movies': len(movies_list),
                'total_characters': total_characters,
                'total_faces': stats.get('total_vectors', 0),
                'avg_quality': sum(movie['avg_quality'] for movie in movies_list) / len(movies_list) if movies_list else 0
            }
            
            return jsonify({
                'success': True,
                'movies': movies_list,
                'movies_stats': movies_stats,
                'quality_stats': quality_stats,
                'overview': overview
            })
            
        except Exception as e:
            logger.error(f"获取数据库预览失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/database_content')
    def database_content():
        """获取完整数据库内容"""
        try:
            # 重用database_preview的逻辑，但返回所有数据
            logger.info('获取完整数据库内容请求')
            return database_preview()
            
        except Exception as e:
            logger.error(f"获取数据库内容失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/export_metadata')
    def export_metadata():
        """导出原始metadata数据"""
        try:
            logger.info('导出metadata数据请求')
            
            # 重新创建vector_db实例以获取最新数据
            try:
                from src.database.vector_database import VectorDatabaseManager
                current_vector_db = VectorDatabaseManager()
                logger.info('使用新实例进行metadata导出')
            except Exception as init_error:
                logger.warning(f'重新初始化向量数据库失败，使用现有实例: {init_error}')
                if not vector_db:
                    return jsonify({'success': False, 'error': '向量数据库未初始化'}), 500
                current_vector_db = vector_db
            
            # 获取原始metadata数据
            metadata_list = []
            if hasattr(current_vector_db, 'database') and hasattr(current_vector_db.database, 'metadata') and current_vector_db.database.metadata:
                metadata_list = current_vector_db.database.metadata
                logger.info(f'获取到 {len(metadata_list)} 条metadata记录')
            else:
                logger.warning('数据库中没有metadata数据')
            
            # 获取颜色字典
            try:
                from src.utils.color_manager import ColorManager
                color_manager = ColorManager()
                color_dictionary = color_manager.export_color_dictionary()
            except Exception as e:
                logger.warning(f"获取颜色字典失败: {e}")
                color_dictionary = {'color_dictionary': {}}
            
            # 构建导出数据
            export_data = {
                'export_time': datetime.now().isoformat(),
                'export_type': 'metadata',
                'database_type': current_vector_db.get_database_stats().get('database_type', 'Unknown'),
                'total_records': len(metadata_list),
                'metadata': metadata_list,
                **color_dictionary  # 合并颜色字典
            }
            
            return jsonify({
                'success': True,
                'data': export_data
            })
            
        except Exception as e:
            logger.error(f"导出metadata失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/refresh_database', methods=['POST'])
    def refresh_database():
        """强制刷新数据库实例"""
        try:
            logger.info('强制刷新数据库实例请求')
            
            # 重新初始化全局vector_db实例
            nonlocal vector_db
            from src.database.vector_database import VectorDatabaseManager
            vector_db = VectorDatabaseManager()
            
            # 获取最新统计信息
            stats = vector_db.get_database_stats()
            logger.info(f'数据库实例刷新成功: {stats}')
            
            return jsonify({
                'success': True,
                'message': '数据库实例已刷新',
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"刷新数据库实例失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/free_crawler_status')
    def free_crawler_status():
        """获取免费爬虫配置状态"""
        try:
            from src.utils.config_loader import config
            crawler_config = config.get_crawler_config()
            sources = crawler_config.get('sources', [])
            
            # 分类爬虫源
            free_sources = []
            paid_sources = []
            
            for source in sources:
                source_info = {
                    'name': source.get('name', ''),
                    'enabled': source.get('enabled', False),
                    'max_results': source.get('max_results', 10),
                    'description': source.get('description', ''),
                    'status': 'ready' if source.get('enabled') else 'disabled'
                }
                
                # 根据名称分类
                if source['name'] in ['tmdb_images', 'baidu_images']:
                    source_info['type'] = 'free'
                    free_sources.append(source_info)
                else:
                    source_info['type'] = 'disabled'
                    paid_sources.append(source_info)
            
            # 统计启用的免费源
            enabled_free_sources = [s for s in free_sources if s['enabled']]
            total_max_images = sum(s['max_results'] for s in enabled_free_sources)
            
            return jsonify({
                'success': True,
                'crawler_status': {
                    'free_sources': free_sources,
                    'paid_sources': paid_sources,
                    'total_free_enabled': len(enabled_free_sources),
                    'total_paid_enabled': len([s for s in paid_sources if s['enabled']]),
                    'max_images_per_actor': total_max_images,
                    'recommendation': '当前配置：TMDB官方图片 + 百度剧照搜索，专注高质量剧照收集'
                }
            })
            
        except Exception as e:
            logger.error(f"获取爬虫状态失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/movie_preview')
    def movie_preview():
        """预览电影演员信息"""
        try:
            movie_title = request.args.get('movie', '').strip()
            year = request.args.get('year', '').strip()
            
            if not movie_title:
                return jsonify({'success': False, 'error': '电影名称不能为空'}), 400
            
            logger.info(f'预览电影演员: {movie_title} ({year if year else "未指定年份"})')
            
            # 初始化TMDB客户端
            from src.api.tmdb_client import TMDBClient
            tmdb_client = TMDBClient()
            
            # 获取电影演员信息
            year_int = int(year) if year and year.isdigit() else None
            actors = tmdb_client.get_movie_actors(movie_title, year_int, max_actors=50)  # 获取更多演员用于预览
            
            if not actors:
                return jsonify({
                    'success': False, 
                    'error': f'未找到电影 "{movie_title}" 的演员信息，请检查电影名称和年份'
                })
            
            # 构建预览数据
            preview_data = {
                'movie_title': movie_title,
                'year': year_int,
                'total_actors': len(actors),
                'actors': [
                    {
                        'name': actor.get('name', 'Unknown'),
                        'character': actor.get('character', 'Unknown Character'),
                        'actor_id': actor.get('id'),
                        'profile_path': actor.get('profile_path'),
                        'popularity': actor.get('popularity', 0),
                        'order': actor.get('order', 999)
                    }
                    for actor in actors
                ]
            }
            
            logger.info(f'成功获取 {len(actors)} 位演员信息')
            
            return jsonify({
                'success': True,
                'data': preview_data
            })
            
        except Exception as e:
            logger.error(f"预览电影演员失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/delete_actor/<actor_name>', methods=['DELETE'])
    def delete_actor(actor_name):
        """删除指定演员的所有数据"""
        try:
            if not vector_db:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 找到要删除的演员的所有face_id和图片路径
            face_ids_to_delete = []
            image_paths_to_delete = []
            actor_dirs_to_delete = set()
            
            if hasattr(vector_db, 'database') and hasattr(vector_db.database, 'metadata'):
                for meta in vector_db.database.metadata:
                    if meta.get('actor_name') == actor_name:
                        face_ids_to_delete.append(meta.get('face_id'))
                        
                        # 收集图片路径
                        image_path = meta.get('image_path')
                        if image_path:
                            image_paths_to_delete.append(image_path)
                            # 提取演员目录
                            from pathlib import Path
                            actor_dir = Path(image_path).parent
                            actor_dirs_to_delete.add(str(actor_dir))
            
            if not face_ids_to_delete:
                return jsonify({'error': f'未找到演员 {actor_name} 的数据'}), 404
            
            # 删除向量和元数据
            deleted_count = 0
            for face_id in face_ids_to_delete:
                if vector_db.delete_face(face_id):
                    deleted_count += 1
            
            # 删除图片文件
            deleted_images = 0
            for image_path in image_paths_to_delete:
                try:
                    from pathlib import Path
                    img_file = Path(image_path)
                    if img_file.exists():
                        img_file.unlink()
                        deleted_images += 1
                        logger.info(f"删除图片文件: {image_path}")
                except Exception as e:
                    logger.error(f"删除图片文件失败 {image_path}: {e}")
            
            # 删除空的演员目录，并检查是否需要删除空的电影目录
            deleted_dirs = 0
            movie_dirs_to_check = set()
            
            for actor_dir_path in actor_dirs_to_delete:
                try:
                    from pathlib import Path
                    import shutil
                    actor_dir = Path(actor_dir_path)
                    if actor_dir.exists() and actor_dir.is_dir():
                        # 记录电影目录，稍后检查是否为空
                        movie_dir = actor_dir.parent
                        if movie_dir.name != 'images':  # 不是根images目录
                            movie_dirs_to_check.add(str(movie_dir))
                        
                        # 检查演员目录是否为空或只包含少量文件
                        remaining_files = list(actor_dir.glob('*'))
                        if len(remaining_files) <= 2:  # 如果只剩少量文件，删除整个目录
                            shutil.rmtree(actor_dir)
                            deleted_dirs += 1
                            logger.info(f"删除演员目录: {actor_dir}")
                except Exception as e:
                    logger.error(f"删除演员目录失败 {actor_dir_path}: {e}")
            
            # 检查并删除空的电影目录
            for movie_dir_path in movie_dirs_to_check:
                try:
                    movie_dir = Path(movie_dir_path)
                    if movie_dir.exists() and movie_dir.is_dir():
                        # 检查电影目录是否为空
                        remaining_items = list(movie_dir.iterdir())
                        if len(remaining_items) == 0:
                            movie_dir.rmdir()
                            logger.info(f"删除空电影目录: {movie_dir.name}")
                except Exception as e:
                    logger.error(f"删除空电影目录失败 {movie_dir_path}: {e}")
            
            # 保存数据库
            vector_db.save_database()
            
            message = f'成功删除演员 {actor_name}：{deleted_count} 条向量数据，{deleted_images} 张图片'
            if deleted_dirs > 0:
                message += f'，{deleted_dirs} 个目录'
            
            return jsonify({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            logger.error(f"删除演员数据失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clear_database', methods=['DELETE'])
    def clear_database():
        """清空整个数据库"""
        try:
            if not vector_db:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 清理图片文件
            from pathlib import Path
            import shutil
            
            # 获取图片目录路径
            config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            images_dir = Path(config_data['storage']['images_dir'])
            aligned_faces_dir = images_dir / 'aligned_faces'
            
            deleted_actors = 0
            deleted_images = 0
            
            # 删除所有电影目录和演员图片（除了aligned_faces）
            if images_dir.exists():
                for item in images_dir.iterdir():
                    if item.is_dir() and item.name != 'aligned_faces':
                        try:
                            # 计算要删除的图片数量
                            image_count = 0
                            
                            if item.name == 'unknown_movie' or any(actor_dir.is_dir() for actor_dir in item.iterdir() if actor_dir.is_dir()):
                                # 这是电影目录或未知电影目录，遍历其中的演员子目录
                                for actor_dir in item.iterdir():
                                    if actor_dir.is_dir():
                                        count = len(list(actor_dir.glob('*.jpg'))) + len(list(actor_dir.glob('*.png')))
                                        image_count += count
                                        deleted_actors += 1
                            else:
                                # 这是旧格式的直接演员目录
                                image_count = len(list(item.glob('*.jpg'))) + len(list(item.glob('*.png')))
                                deleted_actors += 1
                            
                            deleted_images += image_count
                            
                            # 删除整个目录
                            shutil.rmtree(item)
                            logger.info(f"删除目录: {item.name} ({image_count} 张图片)")
                        except Exception as e:
                            logger.error(f"删除目录失败 {item}: {e}")
                            continue
            
            # 清理aligned_faces目录中的图片
            if aligned_faces_dir.exists():
                aligned_count = 0
                for image_file in aligned_faces_dir.glob('*.jpg'):
                    try:
                        image_file.unlink()
                        aligned_count += 1
                    except Exception as e:
                        logger.error(f"删除对齐人脸图片失败 {image_file}: {e}")
                
                for image_file in aligned_faces_dir.glob('*.png'):
                    try:
                        image_file.unlink()
                        aligned_count += 1
                    except Exception as e:
                        logger.error(f"删除对齐人脸图片失败 {image_file}: {e}")
                
                deleted_images += aligned_count
                logger.info(f"删除对齐人脸图片: {aligned_count} 张")
            
            # 清理元数据文件
            metadata_dir = Path(config_data['storage']['images_dir']).parent / 'metadata'
            if metadata_dir.exists():
                try:
                    for meta_file in metadata_dir.glob('*.json'):
                        if meta_file.name == 'color_config.json':
                            # 重置颜色配置文件而不是删除
                            empty_color_config = {
                                "version": "1.0",
                                "created_at": "",
                                "movies": {},
                                "global_settings": {
                                    "default_shape": "rectangle",
                                    "line_thickness": 2,
                                    "font_scale": 0.6,
                                    "font_thickness": 2
                                }
                            }
                            with open(meta_file, 'w', encoding='utf-8') as f:
                                import json
                                json.dump(empty_color_config, f, ensure_ascii=False, indent=2)
                            logger.info(f"重置颜色配置文件: {meta_file.name}")
                        else:
                            # 删除其他元数据文件
                            meta_file.unlink()
                            logger.info(f"删除元数据文件: {meta_file.name}")
                except Exception as e:
                    logger.error(f"清理元数据文件失败: {e}")
            
            # 重新创建空的数据库
            vector_db.database = vector_db.database.__class__(
                dimension=vector_db.database.dimension,
                index_type=vector_db.database.index_type
            )
            
            # 保存空数据库
            vector_db.save_database()
            
            return jsonify({
                'success': True,
                'message': f'数据库已完全清空：删除了 {deleted_actors} 位演员，{deleted_images} 张图片'
            })
            
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/get_movies', methods=['GET'])
    def get_movies():
        """获取数据库中的电影列表"""
        try:
            if not vector_db:
                return jsonify({'error': '系统未初始化'}), 500
            
            movies = set()
            movie_stats = {}
            
            # 从数据库获取电影信息
            if hasattr(vector_db, 'database') and hasattr(vector_db.database, 'metadata'):
                for meta in vector_db.database.metadata:
                    movie_title = meta.get('movie_title', '').strip()
                    if movie_title:
                        movies.add(movie_title)
                        if movie_title not in movie_stats:
                            movie_stats[movie_title] = {'actors': set(), 'faces': 0}
                        
                        actor_name = meta.get('actor_name', '')
                        if actor_name:
                            movie_stats[movie_title]['actors'].add(actor_name)
                        movie_stats[movie_title]['faces'] += 1
            
            # 转换为列表格式
            movie_list = []
            for movie in sorted(movies):
                stats = movie_stats[movie]
                movie_list.append({
                    'title': movie,
                    'actor_count': len(stats['actors']),
                    'face_count': stats['faces'],
                    'actors': sorted(list(stats['actors']))
                })
            
            return jsonify({
                'success': True,
                'movies': movie_list,
                'total_movies': len(movie_list)
            })
            
        except Exception as e:
            logger.error(f"获取电影列表失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/video_progress/<task_id>')
    def video_progress(task_id):
        """视频处理进度SSE端点"""
        def generate():
            if task_id not in progress_queues:
                yield "data: {\"error\": \"任务不存在\"}\n\n"
                return
            
            progress_queue = progress_queues[task_id]
            completed = False
            
            try:
                while not completed:
                    try:
                        # 等待进度更新
                        progress_data = progress_queue.get(timeout=2)
                        
                        if progress_data is None:  # 结束信号
                            break
                        
                        # 发送进度数据
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        logger.info(f"发送进度数据: {progress_data.get('type', 'unknown')}")
                        
                        # 检查是否完成
                        if progress_data.get('type') in ['complete', 'error']:
                            completed = True
                            logger.info(f"视频处理完成，发送完成信号: {progress_data.get('type')}")
                            # 稍微延迟以确保客户端收到完成信号
                            import time
                            time.sleep(0.1)
                        
                    except queue.Empty:
                        # 发送心跳
                        yield "data: {\"type\": \"heartbeat\"}\n\n"
                        
            except GeneratorExit:
                pass
            finally:
                # 清理队列
                if task_id in progress_queues:
                    del progress_queues[task_id]
                logger.info(f"视频处理进度监听结束: {task_id}")
        
        return Response(generate(), mimetype='text/event-stream')
    
    @app.route('/api/extract_video_frame', methods=['POST'])
    def extract_video_frame():
        """专门用于提取视频帧的API"""
        try:
            if 'video' not in request.files:
                return jsonify({'error': '请上传视频文件'}), 400
            
            file = request.files['video']
            if file.filename == '':
                return jsonify({'error': '请选择视频文件'}), 400
            
            # 获取时间参数
            time_position = float(request.form.get('time_position', 0.1))  # 默认0.1秒
            quality = request.form.get('quality', 'high')  # high, medium, low
            
            # 检查文件类型
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
                return jsonify({'error': '不支持的视频格式'}), 400
            
            # 保存临时文件
            temp_dir = Path(__file__).parent.parent / 'temp'
            temp_dir.mkdir(exist_ok=True)
            import time as time_module
            temp_path = temp_dir / f"temp_video_{int(time_module.time())}_{file.filename}"
            
            file.save(temp_path)
            
            try:
                import cv2
                
                # 打开视频
                cap = cv2.VideoCapture(str(temp_path))
                if not cap.isOpened():
                    return jsonify({'error': '无法打开视频文件'}), 400
                
                # 获取视频信息
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / fps if fps > 0 else 0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # 设置到指定时间
                frame_number = int(min(time_position * fps, total_frames - 1))
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                # 读取帧
                ret, frame = cap.read()
                cap.release()
                
                if not ret:
                    return jsonify({'error': '无法提取视频帧'}), 400
                
                # 根据质量设置调整图片
                if quality == 'high':
                    encode_quality = 95
                    max_size = 1920
                elif quality == 'medium':
                    encode_quality = 85
                    max_size = 1280
                else:  # low
                    encode_quality = 70
                    max_size = 854
                
                # 调整尺寸
                h, w = frame.shape[:2]
                if max(h, w) > max_size:
                    if w > h:
                        new_w, new_h = max_size, int(h * max_size / w)
                    else:
                        new_w, new_h = int(w * max_size / h), max_size
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                # 编码为JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, encode_quality])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                return jsonify({
                    'success': True,
                    'frame_data': f"data:image/jpeg;base64,{frame_base64}",
                    'video_info': {
                        'duration': duration,
                        'fps': fps,
                        'total_frames': total_frames,
                        'width': width,
                        'height': height,
                        'extracted_time': time_position,
                        'extracted_frame': frame_number
                    }
                })
                
            finally:
                # 清理临时文件
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            logger.error(f"提取视频帧失败: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/process_frame', methods=['POST'])
    def process_frame():
        """处理视频帧或图片进行人脸识别"""
        try:
            if 'image' not in request.files:
                return jsonify({'error': '请上传文件'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': '请选择文件'}), 400
            
            if not video_recognizer:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 获取电影范围参数
            movie_title = request.form.get('movie_title', '').strip()
            similarity_threshold = float(request.form.get('similarity_threshold', 0.6))
            
            # 检查文件类型
            file_ext = Path(file.filename).suffix.lower()
            is_video = file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
            is_image = file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
            
            if not (is_video or is_image):
                return jsonify({'error': '不支持的文件格式，请上传图片或视频文件'}), 400
            
            # 保存临时文件
            temp_dir = Path(__file__).parent.parent / 'temp'
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"input_{file.filename}"
            output_path = temp_dir / f"annotated_{file.filename.rsplit('.', 1)[0]}.jpg"
            
            file.save(temp_path)
            
            try:
                # 创建电影范围识别器（如果指定了电影）
                if movie_title:
                    current_recognizer = VideoFaceRecognizer(
                        similarity_threshold=similarity_threshold,
                        movie_title=movie_title
                    )
                    logger.info(f"使用电影范围识别: {movie_title}")
                else:
                    current_recognizer = VideoFaceRecognizer(similarity_threshold=similarity_threshold)
                    logger.info("使用全库识别")
                
                if is_image:
                    # 处理图片
                    frame = cv2.imread(str(temp_path))
                    if frame is None:
                        return jsonify({'error': '无法读取图片文件'}), 400
                    
                    # 处理单帧
                    annotated_frame, recognition_results = current_recognizer.process_single_frame(frame)
                    
                elif is_video:
                    # 处理视频 - 提取第一帧
                    cap = cv2.VideoCapture(str(temp_path))
                    
                    if not cap.isOpened():
                        return jsonify({'error': '无法打开视频文件'}), 400
                    
                    # 读取第一帧
                    ret, frame = cap.read()
                    cap.release()
                    
                    if not ret:
                        return jsonify({'error': '无法读取视频帧'}), 400
                    
                    # 处理单帧
                    annotated_frame, recognition_results = current_recognizer.process_single_frame(frame)
                
                # 保存标注后的图片
                cv2.imwrite(str(output_path), annotated_frame)
                
                # 转换为base64返回
                with open(output_path, 'rb') as f:
                    encoded_image = base64.b64encode(f.read()).decode('utf-8')
                
                return jsonify({
                    'success': True,
                    'file_type': 'video' if is_video else 'image',
                    'annotated_image': f"data:image/jpeg;base64,{encoded_image}",
                    'recognition_results': recognition_results,
                    'movie_scoped': bool(movie_title),
                    'target_movie': movie_title,
                    'similarity_threshold': similarity_threshold,
                    'stats': {
                        'faces_detected': len(recognition_results),
                        'faces_recognized': sum(1 for r in recognition_results if r['recognized']),
                        'actors_found': list(set(r['actor_name'] for r in recognition_results if r['recognized']))
                    }
                })
                
            finally:
                # 清理临时文件
                for temp_file in [temp_path, output_path]:
                    if temp_file.exists():
                        temp_file.unlink()
            
        except Exception as e:
            logger.error(f"处理文件失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/process_video', methods=['POST'])
    def process_video():
        """处理完整视频文件"""
        try:
            if 'video' not in request.files:
                return jsonify({'error': '请上传视频文件'}), 400
            
            file = request.files['video']
            if file.filename == '':
                return jsonify({'error': '请选择视频文件'}), 400
            
            if not video_recognizer:
                return jsonify({'error': '系统未初始化'}), 500
            
            # 获取电影范围和相似度参数
            movie_title = request.form.get('movie_title', '').strip()
            similarity_threshold = float(request.form.get('similarity_threshold', 0.6))
            
            # 获取长视频处理参数
            processing_mode = request.form.get('processing_mode', 'auto')  # auto, standard, long_video, parallel
            max_workers = int(request.form.get('max_workers', 2))
            max_memory_usage = float(request.form.get('max_memory_usage', 0.8))
            
            # 检查文件类型
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
                return jsonify({'error': '不支持的视频格式'}), 400
            
            # 保存临时文件
            temp_dir = Path(__file__).parent.parent / 'temp'
            temp_dir.mkdir(exist_ok=True)
            input_path = temp_dir / f"input_{file.filename}"
            output_path = temp_dir / f"processed_{file.filename.rsplit('.', 1)[0]}.mp4"
            
            file.save(input_path)
            
            # 生成任务ID
            import uuid
            task_id = str(uuid.uuid4())
            
            # 创建进度队列
            progress_queue = queue.Queue()
            progress_queues[task_id] = progress_queue
            
            # 定义进度回调函数
            def progress_callback(progress_info):
                """
                处理视频处理进度回调
                
                Args:
                    progress_info: 包含详细进度信息的字典
                """
                # 构建详细的进度消息
                progress = progress_info.get('progress', 0)
                current_frame = progress_info.get('current_frame', 0)
                total_frames = progress_info.get('total_frames', 0)
                processed_frames = progress_info.get('processed_frames', 0)
                faces_detected = progress_info.get('faces_detected', 0)
                faces_recognized = progress_info.get('faces_recognized', 0)
                actors_found = progress_info.get('actors_found', 0)
                elapsed_time = progress_info.get('elapsed_time', 0)
                eta = progress_info.get('eta', 0)
                memory_usage = progress_info.get('memory_usage', 0)
                
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
                
                progress_data = {
                    'type': 'progress',
                    'progress': progress,
                    'current_frame': current_frame,
                    'total_frames': total_frames,
                    'processed_frames': processed_frames,
                    'faces_detected': faces_detected,
                    'faces_recognized': faces_recognized,
                    'actors_found': actors_found,
                    'elapsed_time': elapsed_time,
                    'eta': eta,
                    'memory_usage': memory_usage,
                    'message': message
                }
                
                try:
                    progress_queue.put(progress_data, block=False)
                except queue.Full:
                    pass  # 如果队列满了就跳过
            
            # 检测视频时长并确定处理模式
            def get_video_duration_minutes(video_path):
                import cv2
                try:
                    cap = cv2.VideoCapture(str(video_path))
                    if not cap.isOpened():
                        return 0
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    cap.release()
                    return total_frames / fps / 60 if fps > 0 else 0
                except:
                    return 0
            
            # 确定处理模式
            video_duration = get_video_duration_minutes(input_path)
            if processing_mode == 'auto':
                if video_duration <= 30:
                    final_mode = 'standard'
                elif video_duration <= 120:
                    final_mode = 'long_video'
                else:
                    final_mode = 'parallel'
            else:
                final_mode = processing_mode
            
            logger.info(f"视频时长: {video_duration:.1f}分钟，处理模式: {final_mode}")
            
            # 定义视频处理函数
            def process_video_async():
                try:
                    # 创建识别器
                    long_video_mode = final_mode in ['long_video', 'parallel']
                    current_recognizer = VideoFaceRecognizer(
                        similarity_threshold=similarity_threshold,
                        movie_title=movie_title if movie_title else None,
                        long_video_mode=long_video_mode,
                        max_memory_usage=max_memory_usage
                    )
                    
                    if movie_title:
                        logger.info(f"使用电影范围视频处理: {movie_title}")
                    else:
                        logger.info("使用全库视频处理")
                    
                    logger.info(f"处理配置: 模式={final_mode}, 长视频模式={'启用' if long_video_mode else '禁用'}, "
                              f"最大内存使用率={max_memory_usage:.1%}")
                    
                    # 根据模式选择处理方法
                    if final_mode == 'parallel':
                        results = current_recognizer.process_video_with_parallel_frames(
                            video_path=str(input_path),
                            output_path=str(output_path),
                            max_workers=max_workers,
                            progress_callback=progress_callback
                        )
                    else:
                        results = current_recognizer.process_video_file(
                            video_path=str(input_path),
                            output_path=str(output_path),
                            frame_skip=1,
                            progress_callback=progress_callback,
                            resume_from_checkpoint=True
                        )
                    
                    # 发送完成信号
                    complete_data = {
                        'type': 'complete',
                        'results': results,
                        'success': 'error' not in results
                    }
                    
                    # 如果视频处理成功，添加下载信息
                    if output_path.exists() and 'error' not in results:
                        complete_data['output_filename'] = output_path.name
                        complete_data['download_url'] = f'/api/download_video/{output_path.name}'
                    
                    progress_queue.put(complete_data)
                    
                except Exception as e:
                    logger.error(f"视频处理异步任务失败: {e}")
                    # 发送错误信号
                    progress_queue.put({
                        'type': 'error',
                        'error': str(e)
                    })
                finally:
                    # 延迟发送结束信号，确保完成信号被处理
                    import time
                    time.sleep(0.1)
                    progress_queue.put(None)
            
            # 启动异步处理
            thread = threading.Thread(target=process_video_async)
            thread.daemon = True
            thread.start()
            
            # 立即返回任务ID
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': '视频处理已开始，请通过进度接口获取状态'
            })
            
        except Exception as e:
            logger.error(f"处理视频请求失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/download_video/<filename>')
    def download_video(filename):
        """下载处理后的视频"""
        try:
            # 使用绝对路径
            temp_dir = Path(__file__).parent.parent / 'temp'
            file_path = temp_dir / filename
            
            logger.info(f"尝试下载文件: {file_path}")
            
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return jsonify({'error': f'文件不存在: {filename}'}), 404
            
            return send_file(
                str(file_path),
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4'
            )
            
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/video_actors')
    def video_actors():
        """获取可识别的演员列表"""
        try:
            if not video_recognizer:
                return jsonify({'error': '系统未初始化'}), 500
            
            actors = video_recognizer.get_database_actors()
            
            return jsonify({
                'success': True,
                'actors': actors,
                'total_count': len(actors)
            })
            
        except Exception as e:
            logger.error(f"获取演员列表失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/image/<path:image_path>')
    def serve_image(image_path):
        """提供图片服务"""
        try:
            # 解码图片路径
            from urllib.parse import unquote
            image_path = unquote(image_path)
            
            # 构建完整的图片路径
            images_dir = project_root / 'data' / 'images'
            full_path = images_dir / image_path
            
            # 安全检查：确保路径在images目录内
            try:
                full_path.resolve().relative_to(images_dir.resolve())
            except ValueError:
                logger.warning(f"非法图片路径访问尝试: {image_path}")
                abort(403)
            
            # 检查文件是否存在
            if not full_path.exists() or not full_path.is_file():
                logger.warning(f"图片文件不存在: {full_path}")
                abort(404)
            
            # 检查文件类型
            mime_type, _ = mimetypes.guess_type(str(full_path))
            if not mime_type or not mime_type.startswith('image/'):
                logger.warning(f"非图片文件类型: {full_path}, MIME: {mime_type}")
                abort(400)
            
            logger.info(f"提供图片服务: {full_path}")
            return send_file(str(full_path), mimetype=mime_type)
            
        except Exception as e:
            logger.error(f"图片服务失败: {e}")
            abort(500)
    
    @app.route('/api/debug/metadata')
    def debug_metadata():
        """调试：查看原始metadata"""
        try:
            if not vector_db:
                return jsonify({'error': '系统未初始化'}), 500
            
            stats = vector_db.get_database_stats()
            metadata_sample = []
            all_metadata = []
            
            if hasattr(vector_db, 'database') and hasattr(vector_db.database, 'metadata'):
                all_metadata = vector_db.database.metadata
                metadata_sample = all_metadata[:10]  # 前10个metadata
                
                # 统计字段信息
                field_stats = {}
                for meta in all_metadata:
                    for key in meta.keys():
                        field_stats[key] = field_stats.get(key, 0) + 1
            
            return jsonify({
                'success': True,
                'stats': stats,
                'metadata_sample': metadata_sample,
                'metadata_count': len(all_metadata),
                'field_stats': field_stats,
                'all_metadata': all_metadata  # 临时添加，用于调试
            })
            
        except Exception as e:
            logger.error(f"调试metadata失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '页面未找到'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '服务器内部错误'}), 500
    
    def find_actor_avatar(actor_name: str, actor_id: str = None) -> str:
        """
        查找演员头像图片
        
        Args:
            actor_name: 演员姓名
            actor_id: 演员ID
            
        Returns:
            头像图片的相对路径，如果没有找到则返回None
        """
        try:
            images_dir = project_root / 'data' / 'images'
            
            # 在新的目录结构中查找演员图片
            # 新结构: images/电影名/演员目录/
            # 旧结构: images/演员目录/ (兼容)
            
            # 可能的演员目录名格式
            possible_actor_dirs = []
            if actor_id:
                possible_actor_dirs.append(f"{actor_id}_{actor_name}")
            possible_actor_dirs.append(actor_name)
            
            # 搜索所有可能的位置
            def search_in_directory(search_dir):
                for actor_dir_name in possible_actor_dirs:
                    actor_dir = search_dir / actor_dir_name
                    if actor_dir.exists() and actor_dir.is_dir():
                        # 查找图片文件
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
                        for ext in image_extensions:
                            # 查找第一张图片作为头像
                            for image_file in actor_dir.glob(f'*{ext}'):
                                if image_file.is_file():
                                    # 返回相对于images目录的路径
                                    relative_path = str(image_file.relative_to(images_dir))
                                    logger.info(f"找到演员 {actor_name} 的头像: {relative_path}")
                                    return relative_path
                return None
            
            # 1. 在各个电影目录中查找
            if images_dir.exists():
                for movie_dir in images_dir.iterdir():
                    if movie_dir.is_dir() and movie_dir.name != 'aligned_faces':
                        result = search_in_directory(movie_dir)
                        if result:
                            return result
            
            # 2. 在根目录下查找（兼容旧格式）
            result = search_in_directory(images_dir)
            if result:
                return result
            
            logger.debug(f"未找到演员 {actor_name} 的头像图片")
            return None
            
        except Exception as e:
            logger.error(f"查找演员头像失败: {e}")
            return None
    
    return app


if __name__ == '__main__':
    app = create_app()
    web_config = config.get_web_config()
    app.run(
        host=web_config.get('host', '0.0.0.0'),
        port=web_config.get('port', 5000),
        debug=web_config.get('debug', True)
    )
