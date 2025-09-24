"""
TMDB API客户端
用于获取电影信息和演员数据
"""
import requests
import time
from typing import List, Dict, Any, Optional
from ..utils.config_loader import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TMDBClient:
    """TMDB API客户端类"""
    
    def __init__(self):
        """初始化TMDB客户端"""
        self.tmdb_config = config.get_tmdb_config()
        self.api_key = self.tmdb_config.get('api_key')
        self.base_url = self.tmdb_config.get('base_url', 'https://api.themoviedb.org/3')
        self.image_base_url = self.tmdb_config.get('image_base_url', 'https://image.tmdb.org/t/p/')
        
        if not self.api_key or self.api_key == 'your_tmdb_api_key_here':
            raise ValueError("请在配置文件中设置有效的TMDB API密钥")
        
        self.session = requests.Session()
        self.session.params = {'api_key': self.api_key}
        
        # 请求限制：每秒最多40次请求
        self.last_request_time = 0
        self.min_request_interval = 0.025  # 25毫秒
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        发起API请求
        
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
            response = self.session.get(url, params=params)
            self.last_request_time = time.time()
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TMDB API请求失败: {e}")
            raise
        except ValueError as e:
            logger.error(f"TMDB API响应解析失败: {e}")
            raise
    
    def search_movie(self, query: str, year: int = None, language: str = 'zh-CN') -> List[Dict[str, Any]]:
        """
        搜索电影
        
        Args:
            query: 电影名称
            year: 上映年份
            language: 语言代码
            
        Returns:
            电影搜索结果列表
        """
        params = {
            'query': query,
            'language': language,
            'include_adult': False
        }
        
        if year:
            params['year'] = year
        
        logger.info(f"搜索电影: {query}")
        response = self._make_request('/search/movie', params)
        
        movies = response.get('results', [])
        logger.info(f"找到 {len(movies)} 部相关电影")
        
        return movies
    
    def get_movie_details(self, movie_id: int, language: str = 'zh-CN') -> Dict[str, Any]:
        """
        获取电影详细信息
        
        Args:
            movie_id: 电影ID
            language: 语言代码
            
        Returns:
            电影详细信息
        """
        params = {'language': language}
        
        logger.info(f"获取电影详情: {movie_id}")
        return self._make_request(f'/movie/{movie_id}', params)
    
    def get_movie_credits(self, movie_id: int, language: str = 'zh-CN') -> Dict[str, Any]:
        """
        获取电影演职员信息
        
        Args:
            movie_id: 电影ID
            language: 语言代码
            
        Returns:
            演职员信息
        """
        params = {'language': language}
        
        logger.info(f"获取电影演员信息: {movie_id}")
        return self._make_request(f'/movie/{movie_id}/credits', params)
    
    def get_person_details(self, person_id: int, language: str = 'zh-CN') -> Dict[str, Any]:
        """
        获取人物详细信息
        
        Args:
            person_id: 人物ID
            language: 语言代码
            
        Returns:
            人物详细信息
        """
        params = {'language': language}
        
        logger.info(f"获取人物详情: {person_id}")
        return self._make_request(f'/person/{person_id}', params)
    
    def get_person_images(self, person_id: int) -> Dict[str, Any]:
        """
        获取人物图片
        
        Args:
            person_id: 人物ID
            
        Returns:
            人物图片信息
        """
        logger.info(f"获取人物图片: {person_id}")
        return self._make_request(f'/person/{person_id}/images')
    
    def get_full_image_url(self, image_path: str, size: str = 'w500') -> str:
        """
        获取完整的图片URL
        
        Args:
            image_path: 图片路径
            size: 图片尺寸 (w92, w154, w185, w342, w500, w780, original)
            
        Returns:
            完整的图片URL
        """
        if not image_path:
            return ""
        
        return f"{self.image_base_url}{size}{image_path}"
    
    def get_movie_actors(self, movie_title: str, year: int = None, max_actors: int = 20) -> List[Dict[str, Any]]:
        """
        获取电影的主要演员列表
        
        Args:
            movie_title: 电影标题
            year: 上映年份
            max_actors: 最多返回的演员数量
            
        Returns:
            演员信息列表
        """
        # 搜索电影
        movies = self.search_movie(movie_title, year)
        if not movies:
            logger.warning(f"未找到电影: {movie_title}")
            return []
        
        # 选择第一个搜索结果
        movie = movies[0]
        movie_id = movie['id']
        
        logger.info(f"选择电影: {movie['title']} ({movie.get('release_date', 'N/A')[:4]})")
        
        # 获取演员信息
        credits = self.get_movie_credits(movie_id)
        cast = credits.get('cast', [])
        
        # 只返回主要演员
        main_actors = cast[:max_actors]
        
        # 丰富演员信息
        actors = []
        for actor in main_actors:
            actor_info = {
                'id': actor['id'],
                'name': actor['name'],
                'character': actor.get('character', ''),
                'order': actor.get('order', 999),
                'profile_path': actor.get('profile_path'),
                'profile_url': self.get_full_image_url(actor.get('profile_path'), 'w500') if actor.get('profile_path') else None
            }
            actors.append(actor_info)
        
        logger.info(f"获取到 {len(actors)} 位主要演员")
        return actors
    
    def get_actor_images_from_tmdb(self, person_id: int, max_images: int = 5, 
                                 min_resolution: int = 500) -> List[str]:
        """
        从TMDB获取演员图片URL列表（增强版）
        
        Args:
            person_id: 演员ID
            max_images: 最多返回的图片数量
            min_resolution: 最小分辨率要求
            
        Returns:
            图片URL列表
        """
        try:
            images_data = self.get_person_images(person_id)
            profiles = images_data.get('profiles', [])
            
            if not profiles:
                logger.info(f"演员 {person_id} 没有个人照片")
                return []
            
            # 过滤高质量图片
            quality_profiles = []
            for profile in profiles:
                width = profile.get('width', 0)
                height = profile.get('height', 0)
                vote_avg = profile.get('vote_average', 0)
                
                # 质量筛选条件
                if (width >= min_resolution and height >= min_resolution and
                    width * height >= min_resolution * min_resolution):
                    quality_profiles.append({
                        **profile,
                        'quality_score': vote_avg * 10 + (width * height) / 10000  # 综合评分
                    })
            
            # 按质量评分排序
            quality_profiles.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            
            # 生成不同尺寸的图片URL
            image_urls = []
            for profile in quality_profiles[:max_images]:
                # 优先使用高分辨率，如果太大则使用中等分辨率
                width = profile.get('width', 0)
                height = profile.get('height', 0)
                
                if width > 1500 and height > 1500:
                    size = 'w780'  # 高分辨率图片使用中等尺寸
                elif width > 1000 and height > 1000:
                    size = 'w500'  # 中等分辨率图片
                else:
                    size = 'original'  # 小图片使用原始尺寸
                
                image_url = self.get_full_image_url(profile['file_path'], size)
                image_urls.append(image_url)
                
                logger.debug(f"TMDB图片: {width}x{height}, 评分: {profile.get('vote_average', 0):.1f}, 使用尺寸: {size}")
            
            logger.info(f"从TMDB获取到 {len(image_urls)} 张高质量演员图片")
            return image_urls
            
        except Exception as e:
            logger.error(f"获取TMDB演员图片失败: {e}")
            return []
    
    def get_detailed_person_info(self, person_id: int) -> Dict[str, Any]:
        """
        获取演员的详细信息（包括图片统计）
        
        Args:
            person_id: 演员ID
            
        Returns:
            详细的演员信息
        """
        try:
            # 获取基本信息
            person_details = self.get_person_details(person_id)
            
            # 获取图片信息
            images_data = self.get_person_images(person_id)
            profiles = images_data.get('profiles', [])
            
            # 统计图片信息
            total_images = len(profiles)
            high_res_count = sum(1 for p in profiles if p.get('width', 0) >= 1000 and p.get('height', 0) >= 1000)
            avg_rating = sum(p.get('vote_average', 0) for p in profiles) / total_images if total_images > 0 else 0
            
            # 组合详细信息
            detailed_info = {
                **person_details,
                'images_stats': {
                    'total_profiles': total_images,
                    'high_resolution_count': high_res_count,
                    'average_rating': avg_rating,
                    'has_sufficient_images': total_images >= 3
                }
            }
            
            return detailed_info
            
        except Exception as e:
            logger.error(f"获取演员详细信息失败: {e}")
            return {}
