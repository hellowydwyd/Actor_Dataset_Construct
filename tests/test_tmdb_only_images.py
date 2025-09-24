#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
纯TMDB API演员图片获取测试脚本
只使用TMDB API获取演员的所有可用图片
"""

import os
import sys
import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config_loader import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TMDBOnlyImageTester:
    """纯TMDB API图片测试器"""
    
    def __init__(self):
        """初始化测试器"""
        # 从配置获取TMDB信息
        tmdb_config = config.get_tmdb_config()
        self.api_key = tmdb_config.get('api_key')
        self.base_url = tmdb_config.get('base_url', 'https://api.themoviedb.org/3')
        self.image_base_url = tmdb_config.get('image_base_url', 'https://image.tmdb.org/t/p/')
        
        if not self.api_key or self.api_key == 'your_tmdb_api_key_here':
            raise ValueError("请在配置文件中设置有效的TMDB API密钥")
        
        # 创建session
        self.session = requests.Session()
        self.session.params = {'api_key': self.api_key}
        
        # 输出目录
        self.test_output_dir = Path("temp/tmdb_only_images")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 测试结果
        self.test_results = {
            "actors_processed": [],
            "images_downloaded": [],
            "errors": [],
            "summary": {}
        }
        
        # 图片尺寸选项（从大到小）
        self.image_sizes = ['original', 'w780', 'w500', 'w342', 'w185', 'w154', 'w92']
    
    def get_image_configuration(self) -> Dict[str, Any]:
        """获取TMDB图片配置信息"""
        try:
            url = f"{self.base_url}/configuration"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            config_data = response.json()
            images_config = config_data.get('images', {})
            
            print("TMDB图片配置信息:")
            print(f"  基础URL: {images_config.get('base_url', 'N/A')}")
            print(f"  安全基础URL: {images_config.get('secure_base_url', 'N/A')}")
            print(f"  头像尺寸: {images_config.get('profile_sizes', [])}")
            
            return images_config
            
        except Exception as e:
            print(f"获取配置失败: {e}")
            return {}
    
    def search_person(self, actor_name: str) -> List[Dict[str, Any]]:
        """搜索演员"""
        try:
            url = f"{self.base_url}/search/person"
            params = {
                'query': actor_name,
                'language': 'zh-CN',
                'include_adult': False
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            search_results = response.json()
            return search_results.get('results', [])
            
        except Exception as e:
            print(f"搜索演员失败: {e}")
            return []
    
    def get_person_details(self, person_id: int) -> Dict[str, Any]:
        """获取演员详细信息"""
        try:
            url = f"{self.base_url}/person/{person_id}"
            params = {'language': 'zh-CN'}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"获取演员详情失败: {e}")
            return {}
    
    def get_person_images(self, person_id: int) -> Dict[str, Any]:
        """获取演员所有图片"""
        try:
            url = f"{self.base_url}/person/{person_id}/images"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"获取演员图片失败: {e}")
            return {}
    
    def get_full_image_url(self, image_path: str, size: str = 'original') -> str:
        """构建完整的图片URL"""
        if not image_path:
            return ""
        return f"{self.image_base_url}{size}{image_path}"
    
    def download_image(self, url: str, save_path: Path) -> bool:
        """下载图片"""
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                print(f"      警告: 内容类型不是图片: {content_type}")
            
            # 下载图片
            total_size = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            # 验证图片
            if self.validate_image_file(save_path):
                return True
            else:
                save_path.unlink(missing_ok=True)
                return False
                
        except Exception as e:
            print(f"      下载失败: {e}")
            return False
    
    def validate_image_file(self, file_path: Path) -> bool:
        """验证图片文件"""
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            # 如果PIL不可用，简单检查文件大小
            return file_path.exists() and file_path.stat().st_size > 1000
    
    def process_actor_images(self, actor_name: str, download_all: bool = True) -> Dict[str, Any]:
        """处理单个演员的所有图片"""
        print(f"\n{'='*60}")
        print(f"处理演员: {actor_name}")
        print(f"{'='*60}")
        
        # 搜索演员
        search_results = self.search_person(actor_name)
        if not search_results:
            print(f"✗ 未找到演员: {actor_name}")
            return {"status": "not_found", "actor": actor_name}
        
        # 选择第一个匹配结果
        person = search_results[0]
        person_id = person['id']
        person_name = person['name']
        profile_path = person.get('profile_path')
        popularity = person.get('popularity', 0)
        
        print(f"✓ 找到演员: {person_name}")
        print(f"  TMDB ID: {person_id}")
        print(f"  人气度: {popularity:.1f}")
        print(f"  默认头像: {profile_path}")
        
        # 获取详细信息
        person_details = self.get_person_details(person_id)
        if person_details:
            birthday = person_details.get('birthday', 'N/A')
            place_of_birth = person_details.get('place_of_birth', 'N/A')
            biography = person_details.get('biography', '')[:100] + '...' if person_details.get('biography') else 'N/A'
            
            print(f"  生日: {birthday}")
            print(f"  出生地: {place_of_birth}")
            print(f"  简介: {biography}")
        
        # 获取所有图片
        images_data = self.get_person_images(person_id)
        profiles = images_data.get('profiles', [])
        
        print(f"\n✓ 发现 {len(profiles)} 张可用图片")
        
        if not profiles:
            print("  没有可用的图片")
            return {"status": "no_images", "actor": actor_name, "person_id": person_id}
        
        # 分析图片质量
        print("\n图片质量分析:")
        print(f"{'序号':<4} {'尺寸':<12} {'比例':<8} {'评分':<6} {'投票数':<6} {'语言':<6}")
        print("-" * 50)
        
        for i, profile in enumerate(profiles, 1):
            width = profile.get('width', 0)
            height = profile.get('height', 0)
            aspect_ratio = round(width / height, 2) if height > 0 else 0
            vote_average = profile.get('vote_average', 0)
            vote_count = profile.get('vote_count', 0)
            iso_639_1 = profile.get('iso_639_1') or 'null'
            
            print(f"{i:<4} {width}x{height:<6} {aspect_ratio:<8} {vote_average:<6} {vote_count:<6} {iso_639_1:<6}")
        
        # 下载图片
        if download_all:
            return self.download_all_images(actor_name, person_id, profiles)
        else:
            return self.download_best_images(actor_name, person_id, profiles, max_images=5)
    
    def download_all_images(self, actor_name: str, person_id: int, profiles: List[Dict]) -> Dict[str, Any]:
        """下载演员的所有图片"""
        print(f"\n开始下载 {actor_name} 的所有 {len(profiles)} 张图片...")
        
        # 创建演员专用目录
        actor_dir = self.test_output_dir / f"{person_id}_{actor_name}"
        actor_dir.mkdir(exist_ok=True)
        
        successful_downloads = []
        failed_downloads = []
        
        for i, profile in enumerate(profiles, 1):
            file_path = profile['file_path']
            width = profile.get('width', 0)
            height = profile.get('height', 0)
            vote_average = profile.get('vote_average', 0)
            
            # 选择合适的尺寸
            if width >= 1000 and height >= 1000:
                size = 'w780'  # 高分辨率用中等尺寸
            elif width >= 500 and height >= 500:
                size = 'w500'  # 中等分辨率
            else:
                size = 'original'  # 小图片用原始尺寸
            
            # 构建URL和保存路径
            image_url = self.get_full_image_url(file_path, size)
            save_filename = f"{actor_name}_{i:03d}_{width}x{height}_{vote_average:.1f}.jpg"
            save_path = actor_dir / save_filename
            
            print(f"  下载 {i}/{len(profiles)}: {width}x{height} (评分:{vote_average:.1f}) -> {save_filename}")
            
            # 下载图片
            if self.download_image(image_url, save_path):
                file_size = save_path.stat().st_size
                print(f"    ✓ 成功 ({file_size} bytes)")
                successful_downloads.append({
                    "filename": save_filename,
                    "url": image_url,
                    "size": file_size,
                    "dimensions": f"{width}x{height}",
                    "vote_average": vote_average
                })
            else:
                print(f"    ✗ 失败")
                failed_downloads.append({
                    "url": image_url,
                    "reason": "download_failed"
                })
            
            # 添加延迟避免请求过快
            time.sleep(0.1)
        
        print(f"\n下载完成: {len(successful_downloads)}/{len(profiles)} 成功")
        
        return {
            "status": "completed",
            "actor": actor_name,
            "person_id": person_id,
            "total_images": len(profiles),
            "successful_downloads": len(successful_downloads),
            "failed_downloads": len(failed_downloads),
            "download_details": successful_downloads,
            "failed_details": failed_downloads,
            "save_directory": str(actor_dir)
        }
    
    def download_best_images(self, actor_name: str, person_id: int, profiles: List[Dict], max_images: int = 5) -> Dict[str, Any]:
        """下载演员的最佳图片"""
        print(f"\n开始下载 {actor_name} 的最佳 {max_images} 张图片...")
        
        # 按质量评分排序
        def quality_score(profile):
            width = profile.get('width', 0)
            height = profile.get('height', 0)
            vote_avg = profile.get('vote_average', 0)
            vote_count = profile.get('vote_count', 0)
            
            # 综合评分：图片分辨率 + 用户评分 + 投票数
            resolution_score = (width * height) / 1000000  # 百万像素
            user_score = vote_avg * (1 + vote_count / 100)  # 评分权重
            
            return resolution_score + user_score
        
        # 排序并选择最佳图片
        sorted_profiles = sorted(profiles, key=quality_score, reverse=True)
        best_profiles = sorted_profiles[:max_images]
        
        # 创建演员专用目录
        actor_dir = self.test_output_dir / f"{person_id}_{actor_name}_best"
        actor_dir.mkdir(exist_ok=True)
        
        successful_downloads = []
        
        for i, profile in enumerate(best_profiles, 1):
            file_path = profile['file_path']
            width = profile.get('width', 0)
            height = profile.get('height', 0)
            vote_average = profile.get('vote_average', 0)
            score = quality_score(profile)
            
            # 选择最佳尺寸
            size = 'w780' if width > 1000 else 'original'
            
            # 构建URL和保存路径
            image_url = self.get_full_image_url(file_path, size)
            save_filename = f"{actor_name}_best_{i:02d}_{width}x{height}_score{score:.1f}.jpg"
            save_path = actor_dir / save_filename
            
            print(f"  下载最佳图片 {i}/{len(best_profiles)}: {width}x{height} (评分:{vote_average:.1f}, 质量分:{score:.1f})")
            
            # 下载图片
            if self.download_image(image_url, save_path):
                file_size = save_path.stat().st_size
                print(f"    ✓ 成功 ({file_size} bytes)")
                successful_downloads.append({
                    "filename": save_filename,
                    "url": image_url,
                    "size": file_size,
                    "dimensions": f"{width}x{height}",
                    "vote_average": vote_average,
                    "quality_score": score
                })
            else:
                print(f"    ✗ 失败")
            
            time.sleep(0.1)
        
        print(f"\n最佳图片下载完成: {len(successful_downloads)}/{len(best_profiles)} 成功")
        
        return {
            "status": "completed",
            "actor": actor_name,
            "person_id": person_id,
            "mode": "best_only",
            "max_images": max_images,
            "successful_downloads": len(successful_downloads),
            "download_details": successful_downloads,
            "save_directory": str(actor_dir)
        }
    
    def test_multiple_actors(self, actor_names: List[str], download_all: bool = True):
        """测试多个演员"""
        print(f"开始处理 {len(actor_names)} 位演员的图片")
        print(f"模式: {'下载所有图片' if download_all else '仅下载最佳图片'}")
        
        # 获取TMDB配置信息
        self.get_image_configuration()
        
        for actor_name in actor_names:
            try:
                result = self.process_actor_images(actor_name, download_all)
                self.test_results["actors_processed"].append(result)
                
                if result.get("status") == "completed":
                    self.test_results["images_downloaded"].extend(result.get("download_details", []))
                
            except Exception as e:
                error_msg = f"处理演员 {actor_name} 时出错: {e}"
                print(f"✗ {error_msg}")
                self.test_results["errors"].append(error_msg)
        
        # 生成总结
        self.generate_summary()
    
    def generate_summary(self):
        """生成测试总结"""
        print(f"\n{'='*60}")
        print("测试总结")
        print(f"{'='*60}")
        
        total_actors = len(self.test_results["actors_processed"])
        successful_actors = len([r for r in self.test_results["actors_processed"] if r.get("status") == "completed"])
        total_images = len(self.test_results["images_downloaded"])
        total_errors = len(self.test_results["errors"])
        
        print(f"处理演员数: {successful_actors}/{total_actors}")
        print(f"下载图片数: {total_images}")
        print(f"错误数量: {total_errors}")
        
        if successful_actors > 0:
            print(f"\n成功处理的演员:")
            for result in self.test_results["actors_processed"]:
                if result.get("status") == "completed":
                    actor = result["actor"]
                    downloads = result.get("successful_downloads", 0)
                    save_dir = result.get("save_directory", "")
                    print(f"  {actor}: {downloads} 张图片 -> {save_dir}")
        
        if total_errors > 0:
            print(f"\n错误详情:")
            for i, error in enumerate(self.test_results["errors"], 1):
                print(f"  {i}. {error}")
        
        # 保存详细结果
        results_file = self.test_output_dir / "tmdb_only_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细结果已保存到: {results_file}")
        print(f"图片保存目录: {self.test_output_dir}")
        
        # 统计所有下载的图片文件
        all_images = list(self.test_output_dir.rglob("*.jpg"))
        total_size = sum(img.stat().st_size for img in all_images)
        
        print(f"\n文件统计:")
        print(f"  图片文件: {len(all_images)} 个")
        print(f"  总大小: {total_size / 1024 / 1024:.2f} MB")


def main():
    """主函数"""
    try:
        tester = TMDBOnlyImageTester()
        
        # 测试演员列表
        test_actors = [
            "阿尔·帕西诺",
            "马龙·白兰度", 
            "汤姆·汉克斯",
            "摩根·弗里曼",
            "罗伯特·德尼罗"
        ]
        
        print("TMDB纯API演员图片获取测试")
        print("="*60)
        
        # 询问下载模式
        print("\n选择下载模式:")
        print("1. 下载所有可用图片 (推荐)")
        print("2. 仅下载最佳5张图片")
        
        try:
            choice = input("\n请选择 (1/2, 默认1): ").strip()
            download_all = choice != "2"
        except:
            download_all = True
        
        # 开始测试
        tester.test_multiple_actors(test_actors, download_all)
        
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    main()
