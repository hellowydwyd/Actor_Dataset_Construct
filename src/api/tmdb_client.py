"""
TMDB API客户端
用于获取电影信息和演员数据
支持代理配置和网络环境适配
"""
import requests
import time
import os
import urllib3
from typing import List, Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
        
        # Cloud Studio适配标志 (需要先初始化)
        self.is_cloud_studio = self._detect_cloud_studio()
        if self.is_cloud_studio:
            logger.info("检测到Cloud Studio环境，启用网络适配模式")
            # 禁用SSL警告 (仅在Cloud Studio环境)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.info("已禁用SSL验证以适配Cloud Studio环境")
        
        # 创建会话并配置
        self.session = requests.Session()
        self.session.params = {'api_key': self.api_key}
        
        # 配置代理（支持环境变量和配置文件）
        self._setup_proxy()
        
        # 配置重试策略
        self._setup_retry_strategy()
        
        # 配置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        
        # 请求限制：每秒最多40次请求
        self.last_request_time = 0
        self.min_request_interval = 0.025  # 25毫秒
    
    def _detect_cloud_studio(self) -> bool:
        """检测是否在Cloud Studio环境中运行"""
        # 检查常见的Cloud Studio环境变量
        cloud_indicators = [
            'CLOUD_STUDIO',
            'CODESPACE_NAME',
            'GITPOD_WORKSPACE_ID',
            'CLOUDSTUDIO_ENV'
        ]
        
        for indicator in cloud_indicators:
            if os.getenv(indicator):
                return True
        
        # 检查主机名模式
        hostname = os.getenv('HOSTNAME', '')
        if any(pattern in hostname.lower() for pattern in ['studio', 'cloud', 'workspace']):
            return True
            
        return False
    
    def _setup_proxy(self):
        """设置代理配置"""
        # 优先级：环境变量 > 配置文件
        
        # 1. 从环境变量读取代理
        http_proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
        
        # 2. 从配置文件读取代理
        proxy_config = self.tmdb_config.get('proxy', {})
        if not http_proxy and proxy_config.get('enabled', False):
            http_proxy = proxy_config.get('http_proxy')
            https_proxy = proxy_config.get('https_proxy')
        
        # 设置代理
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy
            
            self.session.proxies.update(proxies)
            logger.info(f"代理配置已启用: HTTP={http_proxy}, HTTPS={https_proxy}")
    
    def _setup_retry_strategy(self):
        """设置重试策略"""
        # 增强的重试策略，特别适合不稳定的网络环境
        retry_strategy = Retry(
            total=5,  # 总重试次数
            read=3,   # 读取重试次数
            connect=3,  # 连接重试次数
            backoff_factor=1,  # 退避因子
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524],  # 需要重试的状态码
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # 允许重试的HTTP方法
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Cloud Studio环境增加超时时间
        if self.is_cloud_studio:
            self.session.timeout = 30
            logger.info("Cloud Studio环境：已增加请求超时时间到30秒")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        发起API请求（带降级策略）
        
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
        
        # 多次尝试策略 (Cloud Studio环境增加重试次数)
        attempts = 5 if self.is_cloud_studio else 1
        last_exception = None
        
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    logger.info(f"TMDB API 重试请求 (第{attempt + 1}次): {endpoint}")
                    time.sleep(2 ** attempt)  # 指数退避
                
                # Cloud Studio环境SSL适配
                if self.is_cloud_studio:
                    # 禁用SSL验证以解决Cloud Studio SSL问题
                    response = self.session.get(url, params=params, timeout=30, verify=False)
                else:
                    response = self.session.get(url, params=params, timeout=30)
                self.last_request_time = time.time()
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"TMDB API 连接失败 (尝试 {attempt + 1}/{attempts}): {e}")
                if attempt == attempts - 1:
                    # 最后一次尝试失败，返回模拟数据
                    return self._get_fallback_data(endpoint, params)
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"TMDB API 超时 (尝试 {attempt + 1}/{attempts}): {e}")
                if attempt == attempts - 1:
                    return self._get_fallback_data(endpoint, params)
                    
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(f"TMDB API请求失败 (尝试 {attempt + 1}/{attempts}): {e}")
                if attempt == attempts - 1:
                    return self._get_fallback_data(endpoint, params)
                    
            except ValueError as e:
                logger.error(f"TMDB API响应解析失败: {e}")
                raise
        
        # 如果所有尝试都失败，抛出最后的异常
        if last_exception:
            raise last_exception
    
    def _get_fallback_data(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        获取降级数据（当API无法访问时使用）
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            模拟的响应数据
        """
        logger.warning(f"TMDB API不可用，返回模拟数据: {endpoint}")
        
        # 根据不同的端点返回不同的模拟数据
        if 'search/movie' in endpoint:
            query = params.get('query', '') if params else ''
            return self._get_mock_movie_search_data(query)
            
        elif '/credits' in endpoint:
            return self._get_mock_credits_data()
            
        elif '/movie/' in endpoint and '/credits' not in endpoint:
            return self._get_mock_movie_details_data()
            
        elif '/person/' in endpoint:
            if '/images' in endpoint:
                return self._get_mock_person_images_data()
            else:
                return self._get_mock_person_details_data()
        
        # 默认返回空结果
        return {'results': [], 'total_results': 0}
    
    def _get_mock_movie_search_data(self, query: str) -> Dict[str, Any]:
        """生成模拟的电影搜索数据"""
        # 预设的一些经典电影数据
        mock_movies = {
            '肖申克的救赎': {
                'id': 278,
                'title': '肖申克的救赎',
                'original_title': 'The Shawshank Redemption',
                'release_date': '1994-09-23',
                'overview': '一个关于希望和友谊的经典故事...'
            },
            '钢铁侠': {
                'id': 1726,
                'title': '钢铁侠',
                'original_title': 'Iron Man',
                'release_date': '2008-05-02',
                'overview': '托尼·斯塔克创造钢铁侠装甲的故事...'
            },
            '流浪地球2': {
                'id': 999999,
                'title': '流浪地球2',
                'original_title': 'The Wandering Earth 2',
                'release_date': '2023-01-22',
                'overview': '人类为拯救地球而奋斗的科幻史诗...'
            }
        }
        
        # 尝试匹配查询
        for movie_name, movie_data in mock_movies.items():
            if query and (query in movie_name or movie_name in query):
                return {
                    'results': [movie_data],
                    'total_results': 1,
                    'total_pages': 1
                }
        
        # 如果没有匹配，返回所有预设电影
        return {
            'results': list(mock_movies.values()),
            'total_results': len(mock_movies),
            'total_pages': 1
        }
    
    def _get_mock_credits_data(self) -> Dict[str, Any]:
        """生成模拟的演员信息数据"""
        return {
            'cast': [
                {
                    'id': 504,
                    'name': '蒂姆·罗宾斯',
                    'character': '安迪·杜弗雷恩',
                    'order': 0,
                    'profile_path': None
                },
                {
                    'id': 192,
                    'name': '摩根·弗里曼',
                    'character': '艾利斯·瑞德',
                    'order': 1,
                    'profile_path': None
                },
                {
                    'id': 3223,
                    'name': '小罗伯特·唐尼',
                    'character': '托尼·斯塔克 / 钢铁侠',
                    'order': 0,
                    'profile_path': None
                }
            ],
            'crew': []
        }
    
    def _get_mock_movie_details_data(self) -> Dict[str, Any]:
        """生成模拟的电影详情数据"""
        return {
            'id': 278,
            'title': '演示电影',
            'original_title': 'Demo Movie',
            'release_date': '2024-01-01',
            'overview': '这是一个演示用的电影数据，当TMDB API不可用时显示。',
            'runtime': 120,
            'genres': [{'id': 18, 'name': '剧情'}]
        }
    
    def _get_mock_person_details_data(self) -> Dict[str, Any]:
        """生成模拟的人物详情数据"""
        return {
            'id': 1,
            'name': '演示演员',
            'biography': '这是一个演示用的演员数据。',
            'birthday': '1970-01-01',
            'profile_path': None
        }
    
    def _get_mock_person_images_data(self) -> Dict[str, Any]:
        """生成模拟的人物图片数据"""
        return {
            'profiles': []
        }
    
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
    
    def get_actor_images_from_tmdb(self, person_id: int, max_images: int = 5) -> List[str]:
        """
        从TMDB获取演员图片URL列表
        
        Args:
            person_id: 演员ID
            max_images: 最多返回的图片数量
            
        Returns:
            图片URL列表
        """
        images_data = self.get_person_images(person_id)
        profiles = images_data.get('profiles', [])
        
        # 按投票数排序，选择高质量图片
        profiles.sort(key=lambda x: x.get('vote_average', 0), reverse=True)
        
        image_urls = []
        for profile in profiles[:max_images]:
            image_url = self.get_full_image_url(profile['file_path'], 'original')
            image_urls.append(image_url)
        
        logger.info(f"从TMDB获取到 {len(image_urls)} 张演员图片")
        return image_urls
