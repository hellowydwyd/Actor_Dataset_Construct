"""
图片爬取模块
支持TMDB官方图片和百度剧照搜索
"""
import os
import requests
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import cv2
import numpy as np

from ..utils.config_loader import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImageCrawler:
    """图片爬取器类"""
    
    def __init__(self):
        """初始化图片爬取器"""
        self.crawler_config = config.get_crawler_config()
        self.storage_config = config.get_storage_config()
        
        self.max_images_per_actor = self.crawler_config.get('max_images_per_actor', 20)
        self.min_face_size = self.crawler_config.get('min_face_size', 112)
        self.image_quality_threshold = self.crawler_config.get('image_quality_threshold', 0.7)
        self.download_timeout = self.crawler_config.get('download_timeout', 30)
        self.concurrent_downloads = self.crawler_config.get('concurrent_downloads', 5)
        self.single_person_only = self.crawler_config.get('single_person_only', True)
        self.max_faces_per_image = self.crawler_config.get('max_faces_per_image', 1)
        
        self.images_dir = Path(self.storage_config.get('images_dir', './data/images'))
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def download_image(self, url: str, save_path: Path, max_retries: int = 3) -> bool:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            save_path: 保存路径
            max_retries: 最大重试次数
            
        Returns:
            是否下载成功
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=self.download_timeout, stream=True)
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL不是图片: {url}")
                    return False
                
                # 保存图片
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # 验证图片完整性
                if self._validate_image(save_path):
                    logger.debug(f"成功下载图片: {save_path.name}")
                    return True
                else:
                    save_path.unlink(missing_ok=True)
                    return False
                    
            except Exception as e:
                logger.warning(f"下载图片失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        return False
    
    def _validate_image(self, image_path: Path) -> bool:
        """
        验证图片文件的完整性和质量
        
        Args:
            image_path: 图片路径
            
        Returns:
            图片是否有效
        """
        try:
            # 使用PIL验证图片
            with Image.open(image_path) as img:
                img.verify()
            
            # 重新打开图片进行质量检查
            with Image.open(image_path) as img:
                width, height = img.size
                
                # 检查图片尺寸
                if width < self.min_face_size or height < self.min_face_size:
                    logger.debug(f"图片尺寸过小: {width}x{height}")
                    return False
                
                # 使用cv2.imdecode处理中文路径
                img_buffer = np.fromfile(str(image_path), dtype=np.uint8)
                img_cv = cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)
                
                if img_cv is not None:
                    # 检查图片质量 (模糊检测)
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                    
                    # 提高模糊阈值
                    blur_threshold = 200  # 提高清晰度要求
                    if laplacian_var < blur_threshold:
                        logger.debug(f"图片过于模糊: {laplacian_var:.1f}")
                        return False
                    
                    # 人脸检测验证
                    if not self._validate_face_content(img_cv):
                        logger.debug(f"图片人脸验证失败")
                        return False
                
                return True
                
        except Exception as e:
            logger.debug(f"图片验证失败: {e}")
            return False
    
    def _validate_face_content(self, img_cv) -> bool:
        """
        验证图片是否包含合适的人脸内容
        
        Args:
            img_cv: OpenCV图片对象
            
        Returns:
            是否包含合适的人脸
        """
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # 使用OpenCV的人脸检测器
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # 检测人脸
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(50, 50),  # 最小人脸尺寸
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            face_count = len(faces)
            
            # 没有人脸，直接拒绝
            if face_count == 0:
                return False
            
            # 如果启用单人照片筛选
            if self.single_person_only:
                if face_count != 1:
                    logger.debug(f"非单人照片，检测到{face_count}个人脸")
                    return False
            else:
                # 人脸过多（超过配置的最大值），可能是群体照
                if face_count > self.max_faces_per_image:
                    logger.debug(f"检测到过多人脸: {face_count}个")
                    return False
            
            # 检查最大人脸尺寸
            max_face_size = 0
            img_area = img_cv.shape[0] * img_cv.shape[1]
            
            for (x, y, w, h) in faces:
                face_size = w * h
                if face_size > max_face_size:
                    max_face_size = face_size
            
            # 计算人脸占比
            face_ratio = max_face_size / img_area if img_area > 0 else 0
            
            # 人脸太小，可能是远景照
            min_face_ratio = 0.01  # 人脸至少占图片1%
            if face_ratio < min_face_ratio:
                logger.debug(f"人脸过小，占比: {face_ratio:.3f}")
                return False
            
            # 人脸尺寸太小
            min_face_pixels = 2500  # 至少50x50像素
            if max_face_size < min_face_pixels:
                logger.debug(f"人脸像素过少: {max_face_size}")
                return False
            
            logger.debug(f"人脸验证通过: {face_count}个人脸, 最大人脸{max_face_size}像素, 占比{face_ratio:.3f}")
            return True
            
        except Exception as e:
            logger.debug(f"人脸验证出错: {e}")
            return False
    
    def _get_image_hash(self, image_path: Path) -> str:
        """
        计算图片的哈希值用于去重
        
        Args:
            image_path: 图片路径
            
        Returns:
            图片哈希值
        """
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"计算图片哈希失败: {e}")
            return ""
    
    
    
    
    
    
    
    def search_baidu_images(self, query: str, movie_title: str = None, max_results: int = 15) -> List[str]:
        """
        搜索百度图片 (免费，专门搜索剧照)
        
        Args:
            query: 演员姓名
            movie_title: 电影名称
            max_results: 最大结果数量
            
        Returns:
            图片URL列表
        """
        try:
            import urllib.parse
            import re
            import json
            
            # 优化搜索关键词 - 专注于高质量单人图片
            search_queries = []
            
            if movie_title:
                # 优先搜索高质量单人图片
                search_queries = [
                    f"{query} {movie_title} 单人 高清",  # 最优组合
                    f"{query} {movie_title} 剧照 人物",  # 人物剧照
                    f"{query} {movie_title} 个人 特写",  # 个人特写
                    f"{query} 单人 高清 肖像",           # 单人肖像
                    f"{query} 剧照 人物"                # 基础组合
                ]
            else:
                search_queries = [
                    f"{query} 单人 高清 肖像",           # 单人高清肖像
                    f"{query} 个人 特写 高清",           # 个人特写
                    f"{query} 剧照 人物 单人",           # 剧照人物
                    f"{query} 肖像 照片",               # 肖像照片
                    f"{query} 演员 个人"                # 演员个人
                ]
            
            all_image_urls = []
            
            for search_query in search_queries:
                if len(all_image_urls) >= max_results:
                    break
                    
                try:
                    encoded_query = urllib.parse.quote(search_query)
                    
                    # 百度图片搜索URL
                    baidu_url = f"https://image.baidu.com/search/index?tn=baiduimage&word={encoded_query}&pn=0&rn=20"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Referer': 'https://www.baidu.com/',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    response = self.session.get(baidu_url, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    image_urls = []
                    
                    # 新方法1: 提取JSON数据中的图片链接
                    json_pattern = r'<script type="application/json" id="image-search-data">(.*?)</script>'
                    json_match = re.search(json_pattern, response.text, re.DOTALL)
                    
                    if json_match:
                        try:
                            json_data = json.loads(json_match.group(1))
                            # 尝试从JSON结构中提取图片URL
                            if 'data' in json_data and 'imgData' in json_data['data']:
                                for img_item in json_data['data']['imgData']:
                                    if isinstance(img_item, dict):
                                        # 尝试不同的URL字段
                                        for url_field in ['objURL', 'middleURL', 'thumbURL', 'src', 'url']:
                                            if url_field in img_item and img_item[url_field]:
                                                url = img_item[url_field].replace('\\/', '/')
                                                if self._is_valid_image_url(url):
                                                    image_urls.append(url)
                                                    break
                        except json.JSONDecodeError:
                            pass
                    
                    # 传统方法2: 正则表达式提取
                    if not image_urls:
                        patterns = [
                            r'"objURL":"([^"]+)"',
                            r'"middleURL":"([^"]+)"', 
                            r'"thumbURL":"([^"]+)"',
                            r'data-src="([^"]*(?:jpg|jpeg|png|webp)[^"]*)"',
                            r'src="([^"]*(?:jpg|jpeg|png|webp)[^"]*)"'
                        ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, response.text, re.IGNORECASE)
                            for match in matches:
                                url = match.replace('\\/', '/')
                                if self._is_valid_image_url(url):
                                    image_urls.append(url)
                            
                            if image_urls:
                                break
                    
                    # 添加到总列表
                    all_image_urls.extend(image_urls)
                    logger.debug(f"搜索 '{search_query}' 找到 {len(image_urls)} 张图片")
                    
                    # 短暂延迟避免请求过快
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"搜索 '{search_query}' 失败: {e}")
                    continue
            
            # 去重并限制数量
            unique_urls = list(dict.fromkeys(all_image_urls))[:max_results]
            
            logger.info(f"百度图片搜索 '{query}' 总共找到 {len(unique_urls)} 张图片")
            return unique_urls
            
        except Exception as e:
            logger.error(f"百度图片搜索失败: {e}")
            return []
    
    def _is_valid_image_url(self, url: str) -> bool:
        """
        检查URL是否为有效的图片链接
        
        Args:
            url: 图片URL
            
        Returns:
            是否为有效图片URL
        """
        if not url or not isinstance(url, str):
            return False
        
        # 必须是HTTP/HTTPS链接
        if not url.startswith(('http://', 'https://')):
            return False
        
        # 必须包含图片扩展名
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        url_lower = url.lower()
        
        return any(ext in url_lower for ext in image_extensions)
    
    def collect_actor_images(self, actor_name: str, actor_id: int = None, 
                           tmdb_images: List[str] = None, movie_title: str = None) -> List[str]:
        """
        收集演员图片
        
        Args:
            actor_name: 演员姓名
            actor_id: 演员ID
            tmdb_images: TMDB图片URL列表
            movie_title: 电影名称 (用于百度搜索剧照)
            
        Returns:
            成功下载的图片路径列表
        """
        logger.info(f"开始收集演员图片: {actor_name} (电影: {movie_title})")
        
        # 按电影名称创建目录结构
        if movie_title:
            # 清理电影名称中的特殊字符
            safe_movie_title = "".join(c for c in movie_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            movie_dir = self.images_dir / safe_movie_title
            movie_dir.mkdir(exist_ok=True)
            
            # 在电影目录下创建演员子目录
            actor_dir = movie_dir / f"{actor_id}_{actor_name}" if actor_id else movie_dir / actor_name
        else:
            # 如果没有电影名称，使用默认的按演员分类（兼容旧逻辑）
            actor_dir = self.images_dir / "unknown_movie" / f"{actor_id}_{actor_name}" if actor_id else self.images_dir / "unknown_movie" / actor_name
        
        actor_dir.mkdir(parents=True, exist_ok=True)
        
        all_image_urls = []
        
        # 从TMDB获取图片
        if tmdb_images:
            all_image_urls.extend(tmdb_images)
            logger.info(f"TMDB提供 {len(tmdb_images)} 张图片")
        
        # 从配置的源收集图片
        sources = self.crawler_config.get('sources', [])
        for source in sources:
            if not source.get('enabled', True):
                continue
                
            source_name = source['name']
            max_results = source.get('max_results', 10)
            
            if source_name == 'baidu_images':
                # 百度图片搜索，传递电影名称以搜索单人剧照
                urls = self.search_baidu_images(actor_name, movie_title, max_results)
                all_image_urls.extend(urls)
                logger.info(f"百度搜索为 {actor_name} 找到 {len(urls)} 张剧照")
        
        # 去重
        unique_urls = list(set(all_image_urls))
        logger.info(f"去重后共 {len(unique_urls)} 张图片待下载")
        
        # 限制下载数量
        urls_to_download = unique_urls[:self.max_images_per_actor]
        
        # 并发下载图片
        downloaded_paths = []
        image_hashes = set()  # 用于去重
        
        with ThreadPoolExecutor(max_workers=self.concurrent_downloads) as executor:
            # 提交下载任务
            future_to_url = {}
            for i, url in enumerate(urls_to_download):
                # 根据URL生成文件名
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"{actor_name}_{i+1:03d}_{url_hash}.jpg"
                save_path = actor_dir / filename
                
                future = executor.submit(self.download_image, url, save_path)
                future_to_url[future] = (url, save_path)
            
            # 收集结果
            for future in as_completed(future_to_url):
                url, save_path = future_to_url[future]
                try:
                    success = future.result()
                    if success and save_path.exists():
                        # 检查图片是否重复
                        img_hash = self._get_image_hash(save_path)
                        if img_hash and img_hash not in image_hashes:
                            image_hashes.add(img_hash)
                            downloaded_paths.append(str(save_path))
                        else:
                            # 删除重复图片
                            save_path.unlink(missing_ok=True)
                            logger.debug(f"删除重复图片: {save_path.name}")
                            
                except Exception as e:
                    logger.error(f"处理下载结果失败: {e}")
        
        logger.info(f"成功下载 {len(downloaded_paths)} 张 {actor_name} 的图片")
        return downloaded_paths
    
    def batch_collect_images(self, actors: List[Dict[str, Any]], movie_title: str = None) -> Dict[str, List[str]]:
        """
        批量收集多个演员的图片
        
        Args:
            actors: 演员信息列表
            movie_title: 电影名称 (用于百度搜索剧照)
            
        Returns:
            演员名称到图片路径列表的映射
        """
        logger.info(f"开始批量收集 {len(actors)} 位演员的图片")
        
        results = {}
        
        for actor in actors:
            actor_name = actor['name']
            actor_id = actor.get('id')
            
            # 从TMDB获取图片URL (如果有API客户端的话)
            tmdb_images = []
            if 'profile_url' in actor and actor['profile_url']:
                tmdb_images.append(actor['profile_url'])
            
            try:
                image_paths = self.collect_actor_images(
                    actor_name=actor_name,
                    actor_id=actor_id,
                    tmdb_images=tmdb_images,
                    movie_title=movie_title
                )
                results[actor_name] = image_paths
                
                # 添加延迟避免被反爬
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"收集 {actor_name} 的图片失败: {e}")
                results[actor_name] = []
        
        total_images = sum(len(paths) for paths in results.values())
        logger.info(f"批量收集完成，共获得 {total_images} 张图片")
        
        return results
