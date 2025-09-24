"""
TMDB图片爬取模块
专门使用TMDB API获取演员的所有高质量图片
"""
import os
import requests
import hashlib
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.config_loader import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImageCrawler:
    """TMDB图片爬取器类"""
    
    def __init__(self):
        """初始化TMDB图片爬取器"""
        self.storage_config = config.get_storage_config()
        self.tmdb_config = config.get_tmdb_config()
        
        # TMDB API配置
        self.api_key = self.tmdb_config.get('api_key')
        self.base_url = self.tmdb_config.get('base_url', 'https://api.themoviedb.org/3')
        self.image_base_url = self.tmdb_config.get('image_base_url', 'https://image.tmdb.org/t/p/')
        
        if not self.api_key or self.api_key == 'your_tmdb_api_key_here':
            raise ValueError("请在配置文件中设置有效的TMDB API密钥")
        
        # 存储配置
        self.images_dir = Path(self.storage_config.get('images_dir', './data/images'))
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建session
        self.session = requests.Session()
        self.session.params = {'api_key': self.api_key}
        
        # 下载配置
        self.download_timeout = 30
        self.concurrent_downloads = 3
        
        # 图片尺寸选项（从大到小）
        self.image_sizes = ['original', 'w780', 'w500', 'w342', 'w185', 'w154', 'w92']
        
        # 统计信息
        self.download_stats = {
            'total_attempts': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'api_calls': 0
        }
        
        # 请求限制：每秒最多40次请求
        self.last_request_time = 0
        self.min_request_interval = 0.025  # 25毫秒
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        发起TMDB API请求
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            响应数据
        """
        # 请求限流
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.download_timeout)
            self.last_request_time = time.time()
            self.download_stats['api_calls'] += 1
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TMDB API请求失败: {e}")
            raise
        except ValueError as e:
            logger.error(f"TMDB API响应解析失败: {e}")
            raise
    
    def search_person(self, actor_name: str) -> List[Dict[str, Any]]:
        """
        搜索演员
        
        Args:
            actor_name: 演员姓名
            
        Returns:
            演员搜索结果列表
        """
        try:
            params = {
                'query': actor_name,
                'language': 'zh-CN',
                'include_adult': False
            }
            
            logger.info(f"搜索演员: {actor_name}")
            response = self._make_request('/search/person', params)
            
            results = response.get('results', [])
            logger.info(f"找到 {len(results)} 个匹配结果")
            
            return results
            
        except Exception as e:
            logger.error(f"搜索演员失败: {e}")
            return []
    
    def get_person_details(self, person_id: int) -> Dict[str, Any]:
        """
        获取演员详细信息
        
        Args:
            person_id: 演员ID
            
        Returns:
            演员详细信息
        """
        try:
            params = {'language': 'zh-CN'}
            
            logger.info(f"获取演员详情: {person_id}")
            return self._make_request(f'/person/{person_id}', params)
            
        except Exception as e:
            logger.error(f"获取演员详情失败: {e}")
            return {}
    
    def get_person_images(self, person_id: int) -> Dict[str, Any]:
        """
        获取演员所有图片
        
        Args:
            person_id: 演员ID
            
        Returns:
            演员图片信息
        """
        try:
            logger.info(f"获取演员图片: {person_id}")
            return self._make_request(f'/person/{person_id}/images')
            
        except Exception as e:
            logger.error(f"获取演员图片失败: {e}")
            return {}
    
    def get_full_image_url(self, image_path: str, size: str = 'original') -> str:
        """
        构建完整的图片URL
        
        Args:
            image_path: 图片路径
            size: 图片尺寸
            
        Returns:
            完整的图片URL
        """
        if not image_path:
            return ""
        return f"{self.image_base_url}{size}{image_path}"
    
    def download_image(self, url: str, save_path: Path) -> bool:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            save_path: 保存路径
            
        Returns:
            是否下载成功
        """
        self.download_stats['total_attempts'] += 1
        
        try:
            response = requests.get(url, timeout=self.download_timeout, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                logger.debug(f"内容类型不是图片: {content_type}")
                return False
            
            # 下载图片
            total_size = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        
                        # 防止下载过大的文件
                        if total_size > 20 * 1024 * 1024:  # 20MB限制
                            logger.debug(f"图片文件过大，中止下载")
                            f.close()
                            save_path.unlink(missing_ok=True)
                            return False
            
            # 验证图片完整性
            if self._validate_image(save_path):
                logger.debug(f"成功下载图片: {save_path.name} ({total_size} bytes)")
                self.download_stats['successful_downloads'] += 1
                return True
            else:
                save_path.unlink(missing_ok=True)
                logger.debug(f"图片验证失败，删除文件")
                self.download_stats['failed_downloads'] += 1
                return False
                
        except Exception as e:
            logger.debug(f"下载图片失败: {e}")
            self.download_stats['failed_downloads'] += 1
            return False
    
    def _validate_image(self, image_path: Path) -> bool:
        """
        验证图片文件的完整性
        
        Args:
            image_path: 图片路径
            
        Returns:
            图片是否有效
        """
        try:
            # 检查文件大小
            if not image_path.exists() or image_path.stat().st_size < 1000:
                return False
            
            # 尝试使用PIL验证
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    img.verify()
                return True
            except ImportError:
                # 如果没有PIL，简单验证文件头
                with open(image_path, 'rb') as f:
                    header = f.read(10)
                    # 检查常见图片格式的文件头
                    return (header.startswith(b'\xff\xd8\xff') or  # JPEG
                           header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                           header.startswith(b'GIF87a') or header.startswith(b'GIF89a'))  # GIF
            except:
                return False
            
        except Exception:
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
    
    def get_actor_all_images_from_tmdb(self, person_id: int) -> List[Dict[str, Any]]:
        """
        从TMDB获取演员的所有图片信息
        
        Args:
            person_id: 演员ID
            
        Returns:
            图片信息列表
        """
        try:
            images_data = self.get_person_images(person_id)
            profiles = images_data.get('profiles', [])
            
            if not profiles:
                logger.info(f"演员 {person_id} 没有可用图片")
                return []
            
            # 为每张图片添加质量评分
            enhanced_profiles = []
            for profile in profiles:
                width = profile.get('width', 0)
                height = profile.get('height', 0)
                vote_avg = profile.get('vote_average', 0)
                vote_count = profile.get('vote_count', 0)
                
                # 计算综合质量评分
                resolution_score = (width * height) / 1000000  # 百万像素
                user_score = vote_avg * (1 + vote_count / 100)  # 评分权重
                quality_score = resolution_score + user_score
                
                enhanced_profile = {
                    **profile,
                    'quality_score': quality_score,
                    'resolution_score': resolution_score,
                    'user_score': user_score
                }
                enhanced_profiles.append(enhanced_profile)
            
            # 按质量评分排序
            enhanced_profiles.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            
            logger.info(f"从TMDB获取到演员 {person_id} 的 {len(enhanced_profiles)} 张图片")
            return enhanced_profiles
            
        except Exception as e:
            logger.error(f"获取TMDB演员图片失败: {e}")
            return []
    
    def collect_actor_images(self, actor_name: str, actor_id: int = None, 
                           movie_title: str = None) -> List[str]:
        """
        收集演员的所有TMDB图片
        
        Args:
            actor_name: 演员姓名
            actor_id: 演员ID（可选）
            movie_title: 电影名称（用于目录结构）
            
        Returns:
            成功下载的图片路径列表
        """
        logger.info(f"开始收集演员图片: {actor_name} (电影: {movie_title})")
        
        # 如果没有提供演员ID，先搜索
        if not actor_id:
            search_results = self.search_person(actor_name)
            if not search_results:
                logger.warning(f"未找到演员: {actor_name}")
                return []
            
            # 选择第一个匹配结果
            person = search_results[0]
            actor_id = person['id']
            person_name = person['name']
            popularity = person.get('popularity', 0)
            
            logger.info(f"找到演员: {person_name} (ID: {actor_id}, 人气度: {popularity:.1f})")
        
        # 创建目录结构
        if movie_title:
            # 清理电影名称中的特殊字符
            safe_movie_title = "".join(c for c in movie_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            movie_dir = self.images_dir / safe_movie_title
            movie_dir.mkdir(exist_ok=True)
            actor_dir = movie_dir / f"{actor_id}_{actor_name}"
        else:
            actor_dir = self.images_dir / "tmdb_actors" / f"{actor_id}_{actor_name}"
        
        actor_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取演员的所有图片
        image_profiles = self.get_actor_all_images_from_tmdb(actor_id)
        
        if not image_profiles:
            logger.warning(f"演员 {actor_name} 没有可用的TMDB图片")
            return []
        
        # 显示图片质量分析
        logger.info(f"\n演员 {actor_name} 的图片质量分析:")
        logger.info(f"{'序号':<4} {'尺寸':<12} {'比例':<8} {'评分':<6} {'投票数':<6} {'质量分':<8}")
        logger.info("-" * 55)
        
        for i, profile in enumerate(image_profiles, 1):
            width = profile.get('width', 0)
            height = profile.get('height', 0)
            aspect_ratio = round(width / height, 2) if height > 0 else 0
            vote_average = profile.get('vote_average', 0)
            vote_count = profile.get('vote_count', 0)
            quality_score = profile.get('quality_score', 0)
            
            logger.info(f"{i:<4} {width}x{height:<6} {aspect_ratio:<8} {vote_average:<6} {vote_count:<6} {quality_score:<8.2f}")
        
        # 并发下载所有图片
        downloaded_paths = []
        image_hashes = set()  # 用于去重
        
        logger.info(f"\n开始下载演员 {actor_name} 的所有 {len(image_profiles)} 张图片...")
        
        with ThreadPoolExecutor(max_workers=self.concurrent_downloads) as executor:
            # 提交下载任务
            future_to_info = {}
            
            for i, profile in enumerate(image_profiles, 1):
                file_path = profile['file_path']
                width = profile.get('width', 0)
                height = profile.get('height', 0)
                vote_average = profile.get('vote_average', 0)
                quality_score = profile.get('quality_score', 0)
                
                # 选择合适的图片尺寸
                if width >= 1500 and height >= 1500:
                    size = 'w780'  # 超高分辨率用中等尺寸
                elif width >= 1000 and height >= 1000:
                    size = 'w500'  # 高分辨率用中等尺寸
                elif width >= 500 and height >= 500:
                    size = 'original'  # 中等分辨率用原始尺寸
                else:
                    size = 'original'  # 小图片用原始尺寸
                
                # 构建URL和保存路径
                image_url = self.get_full_image_url(file_path, size)
                save_filename = f"{actor_name}_{i:03d}_{width}x{height}_score{quality_score:.1f}.jpg"
                save_path = actor_dir / save_filename
                
                future = executor.submit(self.download_image, image_url, save_path)
                future_to_info[future] = {
                    'index': i,
                    'url': image_url,
                    'save_path': save_path,
                    'dimensions': f"{width}x{height}",
                    'vote_average': vote_average,
                    'quality_score': quality_score,
                    'size_used': size
                }
            
            # 收集下载结果
            for future in as_completed(future_to_info):
                info = future_to_info[future]
                try:
                    success = future.result()
                    
                    if success and info['save_path'].exists():
                        # 检查图片是否重复
                        img_hash = self._get_image_hash(info['save_path'])
                        if img_hash and img_hash not in image_hashes:
                            image_hashes.add(img_hash)
                            downloaded_paths.append(str(info['save_path']))
                            
                            file_size = info['save_path'].stat().st_size
                            logger.info(f"  ✓ 下载 {info['index']}/{len(image_profiles)}: "
                                      f"{info['dimensions']} (评分:{info['vote_average']:.1f}, "
                                      f"质量分:{info['quality_score']:.1f}, 尺寸:{info['size_used']}, "
                                      f"大小:{file_size} bytes)")
                        else:
                            # 删除重复图片
                            info['save_path'].unlink(missing_ok=True)
                            logger.debug(f"  - 删除重复图片: {info['save_path'].name}")
                    else:
                        logger.warning(f"  ✗ 下载失败 {info['index']}/{len(image_profiles)}: "
                                     f"{info['dimensions']} - {info['url']}")
                            
                except Exception as e:
                    logger.error(f"处理下载结果失败: {e}")
        
                # 添加小延迟避免请求过快
                time.sleep(0.1)
        
        # 输出统计信息
        success_rate = (len(downloaded_paths) / len(image_profiles) * 100) if image_profiles else 0
        total_size = sum(Path(path).stat().st_size for path in downloaded_paths)
        avg_size = total_size / len(downloaded_paths) if downloaded_paths else 0
        
        logger.info(f"\n✅ 演员 {actor_name} 图片收集完成:")
        logger.info(f"   📊 TMDB可用: {len(image_profiles)} 张")
        logger.info(f"   📥 成功下载: {len(downloaded_paths)} 张")
        logger.info(f"   📈 成功率: {success_rate:.1f}%")
        logger.info(f"   💾 总大小: {total_size / 1024 / 1024:.2f} MB")
        logger.info(f"   📏 平均大小: {avg_size / 1024:.1f} KB")
        logger.info(f"   📁 保存目录: {actor_dir}")
        
        return downloaded_paths
    
    def batch_collect_images(self, actors: List[Dict[str, Any]], movie_title: str = None) -> Dict[str, List[str]]:
        """
        批量收集多个演员的所有TMDB图片
        
        Args:
            actors: 演员信息列表
            movie_title: 电影名称
            
        Returns:
            演员名称到图片路径列表的映射
        """
        logger.info(f"开始批量收集 {len(actors)} 位演员的所有TMDB图片")
        
        results = {}
        total_images = 0
        
        for i, actor in enumerate(actors, 1):
            actor_name = actor['name']
            actor_id = actor.get('id')
            
            logger.info(f"\n处理演员 {i}/{len(actors)}: {actor_name}")
            
            try:
                image_paths = self.collect_actor_images(
                    actor_name=actor_name,
                    actor_id=actor_id,
                    movie_title=movie_title
                )
                results[actor_name] = image_paths
                total_images += len(image_paths)
                
                logger.info(f"演员 {actor_name} 完成: {len(image_paths)} 张图片")
                
                # 添加延迟避免API请求过快
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"收集演员 {actor_name} 的图片失败: {e}")
                results[actor_name] = []
        
        # 生成总结报告
        successful_actors = len([name for name, paths in results.items() if paths])
        
        logger.info(f"\n🎉 批量收集完成:")
        logger.info(f"   👥 处理演员: {len(actors)} 位")
        logger.info(f"   ✅ 成功演员: {successful_actors} 位")
        logger.info(f"   📸 总图片数: {total_images} 张")
        logger.info(f"   🔧 API调用: {self.download_stats['api_calls']} 次")
        logger.info(f"   📥 下载尝试: {self.download_stats['total_attempts']} 次")
        logger.info(f"   ✅ 下载成功: {self.download_stats['successful_downloads']} 次")
        logger.info(f"   ❌ 下载失败: {self.download_stats['failed_downloads']} 次")
        
        if successful_actors > 0:
            logger.info(f"\n📋 详细结果:")
            for actor_name, image_paths in results.items():
                if image_paths:
                    logger.info(f"   {actor_name}: {len(image_paths)} 张图片")
        
        return results

    def get_crawler_stats(self) -> dict:
        """获取爬虫统计信息"""
        total_attempts = self.download_stats['total_attempts']
        success_rate = (self.download_stats['successful_downloads'] / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'api_calls': self.download_stats['api_calls'],
            'total_attempts': total_attempts,
            'successful_downloads': self.download_stats['successful_downloads'],
            'failed_downloads': self.download_stats['failed_downloads'],
            'success_rate': f"{success_rate:.1f}%"
        }