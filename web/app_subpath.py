"""
支持子路径部署的Flask应用
适配 http://灵织.cn/actor/ 子路径访问
"""
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort, Response, url_for
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


class SubpathFlask(Flask):
    """支持子路径的Flask应用类"""
    
    def __init__(self, *args, **kwargs):
        self.subpath = kwargs.pop('subpath', '/actor')
        super().__init__(*args, **kwargs)
        
        # 设置应用根路径
        self.config['APPLICATION_ROOT'] = self.subpath
        
    def url_for_subpath(self, endpoint, **values):
        """生成带子路径的URL"""
        url = url_for(endpoint, **values)
        if not url.startswith(self.subpath):
            url = self.subpath.rstrip('/') + url
        return url


def create_subpath_app(subpath='/actor'):
    """创建支持子路径的Flask应用"""
    
    # 使用自定义Flask类
    app = SubpathFlask(__name__, subpath=subpath)
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
        video_recognizer = VideoFaceRecognizer()
        logger.info("子路径Web应用组件初始化成功")
    except Exception as e:
        logger.error(f"子路径Web应用组件初始化失败: {e}")
        tmdb_client = image_crawler = face_processor = vector_db = video_recognizer = None
    
    # 自定义模板全局函数
    @app.template_global()
    def subpath_url_for(endpoint, **values):
        """模板中使用的子路径URL生成函数"""
        return app.url_for_subpath(endpoint, **values)
    
    @app.template_global()
    def subpath_static(filename):
        """生成子路径静态文件URL"""
        return f"{subpath}/static/{filename}"
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html', subpath=subpath)
    
    @app.route('/api/search_movie', methods=['POST'])
    def search_movie():
        """搜索电影API"""
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
    
    @app.route('/api/database_stats')
    def database_stats():
        """获取数据库统计信息"""
        try:
            if not vector_db:
                return jsonify({'success': False, 'error': '系统未初始化'}), 500
                
            stats = vector_db.get_database_stats()
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/search_face', methods=['POST'])
    def search_face():
        """人脸搜索API"""
        try:
            if 'image' not in request.files:
                return jsonify({'error': '请上传图片'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': '请选择图片文件'}), 400
            
            top_k = int(request.form.get('top_k', 10))
            
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
                results = vector_db.search_similar_faces(query_embedding, top_k)
                
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
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '页面未找到'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '服务器内部错误'}), 500
    
    return app


if __name__ == '__main__':
    # 创建子路径应用
    app = create_subpath_app('/actor')
    
    # 启动配置
    host = '127.0.0.1'  # 只监听本地，通过Nginx代理
    port = 5000
    
    print(f"🚀 启动子路径Flask应用...")
    print(f"   本地地址: http://{host}:{port}")
    print(f"   子路径: /actor")
    print(f"   通过Nginx访问: http://灵织.cn/actor/")
    
    app.run(host=host, port=port, debug=False)
