"""
视频人脸识别处理器
输入视频帧，识别并标记演员姓名
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time
import threading
import queue
import gc
import psutil
import json
from concurrent.futures import ThreadPoolExecutor

from ..face_recognition.face_processor import FaceProcessor
from ..database.vector_database import VectorDatabaseManager
from ..utils.logger import get_logger
from ..utils.chinese_text_renderer import draw_chinese_text

logger = get_logger(__name__)


class VideoFaceRecognizer:
    """视频人脸识别器"""
    
    def __init__(self, similarity_threshold: float = 0.6, movie_title: str = None,
                 long_video_mode: bool = False, max_memory_usage: float = 0.8):
        """
        初始化视频人脸识别器
        
        Args:
            similarity_threshold: 人脸相似度阈值
            movie_title: 目标电影名称，如果指定则只在该电影演员范围内识别
            long_video_mode: 是否启用长视频模式（内存优化）
            max_memory_usage: 最大内存使用率（0.0-1.0）
        """
        self.similarity_threshold = similarity_threshold
        self.movie_title = movie_title
        self.long_video_mode = long_video_mode
        self.max_memory_usage = max_memory_usage
        
        # 长视频处理相关配置
        self.chunk_size = 300 if long_video_mode else 1000  # 分块处理的帧数
        self.smart_skip_enabled = long_video_mode
        self.memory_check_interval = 100  # 每处理100帧检查一次内存
        self.last_memory_check = 0
        
        # 进度和状态管理
        self.processing_progress = 0.0
        self.is_processing = False
        self.should_stop = False
        self.checkpoint_file = None
        
        # 初始化组件
        logger.info("初始化视频人脸识别器...")
        logger.info(f"长视频模式: {'启用' if long_video_mode else '禁用'}")
        self.face_processor = FaceProcessor()
        self.vector_db = VectorDatabaseManager()
        
        # 初始化中文文字渲染器
        from ..utils.chinese_text_renderer import ChineseTextRenderer
        self.text_renderer = ChineseTextRenderer()
        
        # 检查数据库是否有数据
        stats = self.vector_db.get_database_stats()
        if stats.get('total_vectors', 0) == 0:
            logger.warning("数据库为空，请先构建演员数据集")
        else:
            logger.info(f"数据库加载成功，包含 {stats['total_vectors']} 个人脸向量")
        
        # 如果指定了电影，获取电影演员信息
        self.movie_actors = {}
        if movie_title:
            self.movie_actors = self._get_movie_actors()
            if self.movie_actors:
                logger.info(f"电影范围限定: '{movie_title}' - {len(self.movie_actors)} 位演员")
            else:
                logger.warning(f"未找到电影 '{movie_title}' 的演员数据，将使用全库搜索")
    
    def _get_movie_actors(self) -> dict:
        """获取指定电影的演员信息"""
        movie_actors = {}
        
        try:
            # 从数据库获取所有元数据
            if hasattr(self.vector_db, 'database') and hasattr(self.vector_db.database, 'metadata'):
                for idx, meta in enumerate(self.vector_db.database.metadata):
                    movie_title = meta.get('movie_title', '')
                    
                    # 检查是否属于目标电影
                    if movie_title.lower() == self.movie_title.lower():
                        actor_name = meta.get('actor_name', 'Unknown')
                        
                        if actor_name not in movie_actors:
                            movie_actors[actor_name] = {
                                'name': actor_name,
                                'face_count': 0,
                                'indices': []  # 存储在数据库中的索引
                            }
                        
                        movie_actors[actor_name]['face_count'] += 1
                        movie_actors[actor_name]['indices'].append(idx)
            
            return movie_actors
            
        except Exception as e:
            logger.error(f"获取电影演员信息失败: {e}")
            return {}
    
    def _check_memory_usage(self) -> float:
        """检查当前内存使用率"""
        try:
            memory_info = psutil.virtual_memory()
            usage_percent = memory_info.percent / 100.0
            return usage_percent
        except Exception as e:
            logger.warning(f"无法获取内存信息: {e}")
            return 0.5  # 返回保守值
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """获取详细的系统性能统计信息"""
        try:
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=None)
            
            return {
                'memory_usage': memory_info.percent / 100.0,
                'memory_available_gb': memory_info.available / (1024**3),
                'memory_total_gb': memory_info.total / (1024**3),
                'cpu_usage': cpu_percent / 100.0,
                'cpu_count': psutil.cpu_count()
            }
        except Exception as e:
            logger.warning(f"获取系统统计信息失败: {e}")
            return {
                'memory_usage': 0.5,
                'memory_available_gb': 8.0,
                'memory_total_gb': 16.0,
                'cpu_usage': 0.3,
                'cpu_count': 4
            }
    
    def _should_gc_collect(self, force: bool = False) -> bool:
        """判断是否应该进行垃圾回收"""
        if force:
            return True
        
        memory_usage = self._check_memory_usage()
        if memory_usage > self.max_memory_usage:
            logger.info(f"内存使用率过高 ({memory_usage:.1%})，触发垃圾回收")
            return True
        
        return False
    
    def _calculate_smart_skip(self, fps: float, total_frames: int, current_frame: int) -> int:
        """计算智能跳帧策略"""
        if not self.smart_skip_enabled:
            return 1
        
        # 基础跳帧策略：根据视频长度动态调整
        duration_minutes = total_frames / fps / 60
        
        if duration_minutes <= 30:  # 30分钟以内，每帧处理
            return 1
        elif duration_minutes <= 90:  # 30-90分钟，每2帧处理1帧
            return 2
        elif duration_minutes <= 180:  # 90-180分钟，每3帧处理1帧
            return 3
        else:  # 超过3小时，每5帧处理1帧
            return 5
    
    def _save_checkpoint(self, video_path: str, current_frame: int, stats: dict) -> None:
        """保存处理进度检查点"""
        if not self.checkpoint_file:
            checkpoint_dir = Path(video_path).parent / 'checkpoints'
            checkpoint_dir.mkdir(exist_ok=True)
            video_name = Path(video_path).stem
            self.checkpoint_file = checkpoint_dir / f"{video_name}_checkpoint.json"
        
        checkpoint_data = {
            'video_path': video_path,
            'current_frame': current_frame,
            'stats': stats,
            'timestamp': time.time(),
            'movie_title': self.movie_title,
            'similarity_threshold': self.similarity_threshold
        }
        
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"检查点已保存: 第{current_frame}帧")
        except Exception as e:
            logger.warning(f"保存检查点失败: {e}")
    
    def _load_checkpoint(self, video_path: str) -> Optional[dict]:
        """加载处理进度检查点"""
        checkpoint_dir = Path(video_path).parent / 'checkpoints'
        video_name = Path(video_path).stem
        checkpoint_file = checkpoint_dir / f"{video_name}_checkpoint.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # 验证检查点是否匹配当前配置
            if (checkpoint_data.get('movie_title') == self.movie_title and
                checkpoint_data.get('similarity_threshold') == self.similarity_threshold):
                logger.info(f"找到有效检查点，将从第{checkpoint_data['current_frame']}帧继续")
                return checkpoint_data
            else:
                logger.info("检查点配置不匹配，将重新开始处理")
                return None
                
        except Exception as e:
            logger.warning(f"加载检查点失败: {e}")
            return None
    
    def _is_main_actor(self, actor_name: str) -> bool:
        """
        判断是否为主要演员
        基于知名度和常见性进行判断
        """
        # 主要演员列表（可以根据需要扩展）
        main_actors = {
            '摩根·弗里曼', '蒂姆·罗宾斯',  # 肖申克的救赎主演
            '小罗伯特·唐尼', '格温妮斯·帕特洛', '杰夫·布里吉斯',  # 钢铁侠主演
            # 可以继续添加其他电影的主演
        }
        
        return actor_name in main_actors
    
    def _search_in_movie_scope(self, face_embedding: np.ndarray) -> list:
        """在电影范围内搜索相似人脸"""
        if not self.movie_title or not self.movie_actors:
            # 如果没有指定电影或没有电影数据，使用全库搜索
            return self.vector_db.search_similar_faces(
                face_embedding, 
                top_k=1, 
                min_similarity=self.similarity_threshold
            )
        
        results = []
        
        try:
            # 获取所有相似人脸
            all_results = self.vector_db.search_similar_faces(
                face_embedding, 
                top_k=50,  # 获取更多候选
                min_similarity=0.3  # 降低阈值获取更多候选
            )
            
            # 过滤出属于目标电影的结果
            for result in all_results:
                metadata = result.get('metadata', {})
                movie_title = metadata.get('movie_title', '')
                
                if movie_title.lower() == self.movie_title.lower():
                    # 重新检查相似度阈值
                    if result['similarity'] >= self.similarity_threshold:
                        results.append(result)
            
            # 如果有多个相同相似度的结果，选择最有可能的演员
            if len(results) > 1:
                # 按相似度排序，然后按演员名称排序（确保一致性）
                results.sort(key=lambda x: (-x['similarity'], x['metadata'].get('actor_name', '')))
                
                # 如果前几个结果相似度相同，优先选择主要演员
                top_similarity = results[0]['similarity']
                same_similarity_results = [r for r in results if abs(r['similarity'] - top_similarity) < 0.001]
                
                if len(same_similarity_results) > 1:
                    logger.debug(f"发现 {len(same_similarity_results)} 个相同相似度结果，进行智能选择")
                    
                    # 智能选择策略：优先考虑主要演员
                    actor_scores = {}
                    
                    for result in same_similarity_results:
                        actor_name = result['metadata'].get('actor_name', '')
                        if actor_name not in actor_scores:
                            actor_scores[actor_name] = {
                                'face_count': 0,
                                'similarity_sum': 0,
                                'is_main_actor': self._is_main_actor(actor_name),
                                'results': []
                            }
                        
                        actor_scores[actor_name]['face_count'] += 1
                        actor_scores[actor_name]['similarity_sum'] += result['similarity']
                        actor_scores[actor_name]['results'].append(result)
                    
                    # 计算综合得分
                    best_actor = None
                    best_score = -1
                    
                    for actor_name, score_info in actor_scores.items():
                        # 综合得分 = 主要演员加权 + 人脸数量 + 平均相似度
                        main_actor_bonus = 10 if score_info['is_main_actor'] else 0
                        face_count_score = min(score_info['face_count'], 5)  # 最多5分
                        avg_similarity = score_info['similarity_sum'] / score_info['face_count']
                        
                        total_score = main_actor_bonus + face_count_score + avg_similarity * 10
                        
                        if total_score > best_score:
                            best_score = total_score
                            best_actor = actor_name
                    
                    logger.debug(f"智能选择结果: {best_actor} (得分: {best_score:.2f})")
                    
                    # 选择最佳演员的结果
                    if best_actor:
                        results = actor_scores[best_actor]['results'][:1]
            
            return results[:1] if results else []  # 只返回最佳匹配
            
        except Exception as e:
            logger.error(f"电影范围搜索失败: {e}")
            return []
    
    def recognize_faces_in_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        在视频帧中识别人脸
        
        Args:
            frame: 视频帧 (numpy数组)
            
        Returns:
            识别结果列表，包含人脸位置和演员信息
        """
        try:
            # 检测人脸
            faces = self.face_processor.detect_faces(frame)
            
            if not faces:
                return []
            
            recognized_faces = []
            
            for i, face_info in enumerate(faces):
                try:
                    # 提取人脸特征
                    embedding = face_info['embedding']
                    
                    # 在电影范围内搜索相似人脸（如果指定了电影）
                    similar_results = self._search_in_movie_scope(embedding)
                    
                    # 构建识别结果
                    recognition_result = {
                        'face_id': i,
                        'bbox': face_info['bbox'],
                        'det_score': face_info['det_score'],
                        'age': face_info.get('age'),
                        'gender': face_info.get('gender'),
                        'recognized': False,
                        'actor_name': None,
                        'similarity': 0.0,
                        'confidence': 'low'
                    }
                    
                    # 如果找到相似人脸
                    if similar_results:
                        best_match = similar_results[0]
                        metadata = best_match['metadata']
                        similarity = best_match['similarity']
                        
                        recognition_result.update({
                            'recognized': True,
                            'actor_name': metadata.get('actor_name', 'Unknown'),
                            'similarity': similarity,
                            'confidence': self._get_confidence_level(similarity),
                            'movie_source': metadata.get('movie_title', 'Unknown'),
                            'movie_scoped': self.movie_title is not None,
                            'target_movie': self.movie_title,
                            'metadata': metadata  # 包含完整的元数据信息，包括角色名字
                        })
                    
                    recognized_faces.append(recognition_result)
                    
                except Exception as e:
                    logger.error(f"处理人脸 {i} 失败: {e}")
                    continue
            
            return recognized_faces
            
        except Exception as e:
            logger.error(f"视频帧人脸识别失败: {e}")
            return []
    
    def _get_confidence_level(self, similarity: float) -> str:
        """根据相似度获取置信度等级"""
        if similarity >= 0.85:
            return 'high'
        elif similarity >= 0.7:
            return 'medium'
        else:
            return 'low'
    
    def draw_face_annotations(self, frame: np.ndarray, 
                            recognition_results: List[Dict[str, Any]]) -> np.ndarray:
        """
        在视频帧上绘制人脸标注
        
        Args:
            frame: 原始视频帧
            recognition_results: 人脸识别结果
            
        Returns:
            标注后的视频帧
        """
        annotated_frame = frame.copy()
        
        for result in recognition_results:
            bbox = result['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # 根据识别状态和角色配置选择颜色
            if result['recognized']:
                # 优先使用角色的专属颜色
                metadata = result.get('metadata', {})
                color_bgr = metadata.get('color_bgr')
                shape_type = metadata.get('shape_type', 'rectangle')
                line_thickness = metadata.get('line_thickness', 2)
                
                if color_bgr:
                    # 使用角色专属颜色
                    color = tuple(color_bgr)
                else:
                    # 备用：根据置信度选择颜色
                    confidence = result['confidence']
                    if confidence == 'high':
                        color = (0, 255, 0)  # 绿色 - 高置信度
                    elif confidence == 'medium':
                        color = (0, 165, 255)  # 橙色 - 中等置信度
                    else:
                        color = (0, 255, 255)  # 黄色 - 低置信度
                
                # 根据框形类型绘制人脸框
                self._draw_face_shape(annotated_frame, (x1, y1, x2, y2), color, 
                                    shape_type, line_thickness)
                
                # 准备标签文本 - 优先使用角色名字
                metadata = result.get('metadata', {})
                character_name = metadata.get('character', '')
                actor_name = result['actor_name']
                similarity = result['similarity']
                
                # 优先显示角色名字，如果没有则显示演员名字
                display_name = character_name if character_name else actor_name
                label = f"{display_name} ({similarity:.2f})"
                
                # 使用中文文字渲染器绘制标签 - 使用描边而不是纯色背景
                annotated_frame = self.text_renderer.draw_text_with_outline(
                    annotated_frame, 
                    label, 
                    (x1 + 5, y1 - 5),
                    font_size=18,
                    text_color=color,  # 使用人物配色作为文字颜色
                    outline_color=(0, 0, 0),  # 黑色描边
                    outline_width=2
                )
            else:
                # 未识别的人脸 - 灰色框
                color = (128, 128, 128)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                
                # 标记为未知 - 使用描边而不是纯色背景
                label = "未知"
                annotated_frame = self.text_renderer.draw_text_with_outline(
                    annotated_frame, 
                    label, 
                    (x1 + 5, y1 - 5),
                    font_size=18,
                    text_color=(255, 255, 255),  # 白色文字
                    outline_color=(0, 0, 0),  # 黑色描边
                    outline_width=2
                )
        
        return annotated_frame
    
    def _draw_face_shape(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], 
                        color: Tuple[int, int, int], shape_type: str = 'rectangle', 
                        thickness: int = 2) -> None:
        """
        根据形状类型绘制人脸框
        
        Args:
            frame: 视频帧
            bbox: 边界框坐标 (x1, y1, x2, y2)
            color: 颜色 (BGR)
            shape_type: 形状类型
            thickness: 线条粗细
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        width = x2 - x1
        height = y2 - y1
        
        if shape_type == 'rectangle':
            # 矩形框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
        elif shape_type == 'rounded_rectangle':
            # 圆角矩形
            radius = min(width, height) // 10
            self._draw_rounded_rectangle(frame, (x1, y1), (x2, y2), radius, color, thickness)
            
        elif shape_type == 'circle':
            # 圆形框
            radius = min(width, height) // 2
            cv2.circle(frame, (center_x, center_y), radius, color, thickness)
            
        elif shape_type == 'ellipse':
            # 椭圆框
            axes = (width // 2, height // 2)
            cv2.ellipse(frame, (center_x, center_y), axes, 0, 0, 360, color, thickness)
            
        elif shape_type == 'diamond':
            # 菱形框
            points = np.array([
                [center_x, y1],           # 上
                [x2, center_y],           # 右
                [center_x, y2],           # 下
                [x1, center_y]            # 左
            ], np.int32)
            points = points.reshape((-1, 1, 2))
            cv2.polylines(frame, [points], True, color, thickness)
            
        else:
            # 默认矩形框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    
    def _draw_rounded_rectangle(self, frame: np.ndarray, pt1: Tuple[int, int], 
                              pt2: Tuple[int, int], radius: int, 
                              color: Tuple[int, int, int], thickness: int) -> None:
        """
        绘制圆角矩形
        
        Args:
            frame: 视频帧
            pt1: 左上角坐标
            pt2: 右下角坐标
            radius: 圆角半径
            color: 颜色
            thickness: 线条粗细
        """
        x1, y1 = pt1
        x2, y2 = pt2
        
        # 绘制四条边
        cv2.line(frame, (x1 + radius, y1), (x2 - radius, y1), color, thickness)  # 上边
        cv2.line(frame, (x1 + radius, y2), (x2 - radius, y2), color, thickness)  # 下边
        cv2.line(frame, (x1, y1 + radius), (x1, y2 - radius), color, thickness)  # 左边
        cv2.line(frame, (x2, y1 + radius), (x2, y2 - radius), color, thickness)  # 右边
        
        # 绘制四个圆角
        cv2.ellipse(frame, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
        cv2.ellipse(frame, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
        cv2.ellipse(frame, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)
        cv2.ellipse(frame, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
    
    def process_video_file(self, video_path: str, output_path: str = None, 
                          frame_skip: int = 1, progress_callback=None, 
                          resume_from_checkpoint: bool = True) -> Dict[str, Any]:
        """
        处理视频文件，识别并标注人脸
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径（可选）
            frame_skip: 跳帧数量（1=处理每帧，2=每2帧处理1帧）
            progress_callback: 进度回调函数
            resume_from_checkpoint: 是否从检查点恢复
            
        Returns:
            处理结果统计
        """
        try:
            self.is_processing = True
            self.should_stop = False
            
            # 尝试加载检查点
            checkpoint_data = None
            if resume_from_checkpoint:
                checkpoint_data = self._load_checkpoint(video_path)
            
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_minutes = total_frames / fps / 60
            
            logger.info(f"视频信息: {width}x{height}, {fps:.1f}fps, {total_frames}帧, 时长: {duration_minutes:.1f}分钟")
            
            # 检查是否为长视频，自动启用优化
            if duration_minutes > 60 and not self.long_video_mode:
                logger.info(f"检测到长视频({duration_minutes:.1f}分钟)，建议启用长视频模式以获得更好的性能")
            
            # 计算智能跳帧策略
            smart_skip = self._calculate_smart_skip(fps, total_frames, 0)
            effective_skip = max(frame_skip, smart_skip)
            if effective_skip > frame_skip:
                logger.info(f"智能跳帧: {frame_skip} -> {effective_skip} (视频时长: {duration_minutes:.1f}分钟)")
            
            # 准备输出视频
            writer = None
            if output_path:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 处理统计
            if checkpoint_data:
                stats = checkpoint_data['stats']
                start_frame = checkpoint_data['current_frame']
                logger.info(f"从检查点恢复，起始帧: {start_frame}")
            else:
                stats = {
                    'total_frames': total_frames,
                    'processed_frames': 0,
                    'faces_detected': 0,
                    'faces_recognized': 0,
                    'actors_found': set(),
                    'processing_time': 0,
                    'memory_warnings': 0,
                    'gc_collections': 0,
                    'effective_skip_rate': effective_skip
                }
                start_frame = 0
            
            # 如果从检查点恢复，跳转到指定帧
            if start_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            frame_count = start_frame
            start_time = time.time()
            
            logger.info("开始处理视频...")
            
            while not self.should_stop:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # 跳帧处理
                if frame_count % effective_skip != 0:
                    if writer:
                        writer.write(frame)
                    continue
                
                # 内存管理
                if frame_count % self.memory_check_interval == 0:
                    if self._should_gc_collect():
                        gc.collect()
                        stats['gc_collections'] += 1
                        memory_usage = self._check_memory_usage()
                        if memory_usage > 0.9:  # 警告阈值
                            stats['memory_warnings'] += 1
                            logger.warning(f"内存使用率过高: {memory_usage:.1%}")
                
                # 识别人脸
                recognition_results = self.recognize_faces_in_frame(frame)
                
                # 更新统计
                stats['processed_frames'] += 1
                stats['faces_detected'] += len(recognition_results)
                
                for result in recognition_results:
                    if result['recognized']:
                        stats['faces_recognized'] += 1
                        stats['actors_found'].add(result['actor_name'])
                
                # 绘制标注
                if recognition_results:
                    frame = self.draw_face_annotations(frame, recognition_results)
                
                # 写入输出视频
                if writer:
                    writer.write(frame)
                
                # 智能进度更新策略 - 根据视频长度动态调整更新频率
                progress_interval = max(1, min(int(fps * 3), 150))  # 3秒或150帧，取较小值
                percentage_interval = max(0.5, 100 / total_frames * 50)  # 至少每0.5%更新一次
                
                progress = frame_count / total_frames * 100
                should_update_progress = (
                    frame_count % progress_interval == 0 or  # 按时间间隔
                    progress - getattr(self, '_last_progress', 0) >= percentage_interval or  # 按百分比间隔
                    frame_count == total_frames  # 最后一帧
                )
                
                if should_update_progress:
                    elapsed_time = time.time() - start_time
                    processed_rate = (frame_count - start_frame + 1) / elapsed_time if elapsed_time > 0 else 0
                    eta = (total_frames - frame_count) / processed_rate if processed_rate > 0 else 0
                    
                    # 计算处理速度 (帧/秒)
                    current_fps = processed_rate
                    processing_speed_ratio = current_fps / fps if fps > 0 else 0
                    
                    # 调用进度回调函数
                    if progress_callback:
                        progress_info = {
                            'progress': progress,
                            'current_frame': frame_count,
                            'total_frames': total_frames,
                            'processed_frames': stats['processed_frames'],
                            'faces_detected': stats['faces_detected'],
                            'faces_recognized': stats['faces_recognized'],
                            'actors_found': len(stats['actors_found']),
                            'elapsed_time': elapsed_time,
                            'eta': eta,
                            'fps': fps,
                            'processing_fps': current_fps,
                            'speed_ratio': processing_speed_ratio,
                            'memory_usage': self._check_memory_usage(),
                            'frame_skip': frame_skip
                        }
                        progress_callback(progress_info)
                    
                    # 记录最后更新的进度
                    self._last_progress = progress
                    
                    # 每30秒显示详细日志
                    if frame_count % max(1, int(fps * 30)) == 0:
                        logger.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames}) "
                                  f"用时: {elapsed_time:.0f}s 预计剩余: {eta:.0f}s")
                        
                        # 保存检查点
                        if self.long_video_mode:
                            self._save_checkpoint(video_path, frame_count, stats)
            
            # 清理资源
            cap.release()
            if writer:
                writer.release()
            
            # 强制垃圾回收
            if self._should_gc_collect(force=True):
                gc.collect()
                stats['gc_collections'] += 1
            
            # 完成统计
            stats['processing_time'] = time.time() - start_time
            stats['actors_found'] = list(stats['actors_found'])
            
            # 删除检查点文件
            if self.checkpoint_file and self.checkpoint_file.exists():
                try:
                    self.checkpoint_file.unlink()
                    logger.info("检查点文件已清理")
                except Exception as e:
                    logger.warning(f"清理检查点文件失败: {e}")
            
            logger.info(f"视频处理完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"处理视频文件失败: {e}")
            return {'error': str(e)}
        finally:
            self.is_processing = False
    
    def process_single_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        处理单个视频帧
        
        Args:
            frame: 输入帧
            
        Returns:
            (标注后的帧, 识别结果列表)
        """
        try:
            # 识别人脸
            recognition_results = self.recognize_faces_in_frame(frame)
            
            # 绘制标注
            annotated_frame = self.draw_face_annotations(frame, recognition_results)
            
            return annotated_frame, recognition_results
            
        except Exception as e:
            logger.error(f"处理单帧失败: {e}")
            return frame, []
    
    def get_database_actors(self) -> List[Dict[str, Any]]:
        """获取数据库中的所有演员信息"""
        try:
            stats = self.vector_db.get_database_stats()
            
            if stats.get('total_vectors', 0) == 0:
                return []
            
            # 从metadata中提取演员信息
            actors_dict = {}
            if hasattr(self.vector_db, 'database') and hasattr(self.vector_db.database, 'metadata'):
                for meta in self.vector_db.database.metadata:
                    actor_name = meta.get('actor_name', 'Unknown')
                    if actor_name not in actors_dict:
                        actors_dict[actor_name] = {
                            'name': actor_name,
                            'face_count': 0,
                            'movies': set()
                        }
                    
                    actors_dict[actor_name]['face_count'] += 1
                    movie_title = meta.get('movie_title')
                    if movie_title:
                        actors_dict[actor_name]['movies'].add(movie_title)
                
                # 转换为列表
                actors_list = []
                for actor_data in actors_dict.values():
                    actor_data['movies'] = list(actor_data['movies'])
                    actors_list.append(actor_data)
                
                return actors_list
            
            return []
            
        except Exception as e:
            logger.error(f"获取演员信息失败: {e}")
            return []
    
    def stop_processing(self) -> None:
        """停止视频处理"""
        self.should_stop = True
        logger.info("已请求停止视频处理")
    
    def get_processing_status(self) -> dict:
        """获取处理状态"""
        return {
            'is_processing': self.is_processing,
            'progress': self.processing_progress,
            'should_stop': self.should_stop,
            'long_video_mode': self.long_video_mode,
            'max_memory_usage': self.max_memory_usage,
            'current_memory_usage': self._check_memory_usage()
        }
    
    def process_video_with_parallel_frames(self, video_path: str, output_path: str = None,
                                         max_workers: int = 2, progress_callback=None) -> Dict[str, Any]:
        """
        使用并行帧处理的方式处理视频（适用于长视频）
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            max_workers: 最大并行工作线程数
            progress_callback: 进度回调函数
            
        Returns:
            处理结果统计
        """
        try:
            self.is_processing = True
            self.should_stop = False
            
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_minutes = total_frames / fps / 60
            
            logger.info(f"并行处理模式 - 视频信息: {width}x{height}, {fps:.1f}fps, {total_frames}帧, "
                       f"时长: {duration_minutes:.1f}分钟")
            
            # 计算智能跳帧
            smart_skip = self._calculate_smart_skip(fps, total_frames, 0)
            
            # 准备输出视频
            writer = None
            if output_path:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 处理统计
            stats = {
                'total_frames': total_frames,
                'processed_frames': 0,
                'faces_detected': 0,
                'faces_recognized': 0,
                'actors_found': set(),
                'processing_time': 0,
                'parallel_workers': max_workers,
                'effective_skip_rate': smart_skip
            }
            
            # 帧队列和结果队列
            frame_queue = queue.Queue(maxsize=max_workers * 2)
            result_queue = queue.Queue()
            
            def frame_processor():
                """帧处理工作线程"""
                while not self.should_stop:
                    try:
                        frame_data = frame_queue.get(timeout=1.0)
                        if frame_data is None:  # 结束信号
                            break
                        
                        frame_index, frame = frame_data
                        
                        # 处理帧
                        recognition_results = self.recognize_faces_in_frame(frame)
                        annotated_frame = self.draw_face_annotations(frame, recognition_results)
                        
                        result_queue.put((frame_index, annotated_frame, recognition_results))
                        frame_queue.task_done()
                        
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"帧处理线程错误: {e}")
                        break
            
            # 启动工作线程
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交帧处理任务
                for _ in range(max_workers):
                    executor.submit(frame_processor)
                
                start_time = time.time()
                frame_count = 0
                processed_results = {}
                
                logger.info("开始并行处理视频...")
                
                # 读取和分发帧
                while not self.should_stop:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_count += 1
                    
                    # 智能跳帧
                    if frame_count % smart_skip != 0:
                        if writer:
                            writer.write(frame)
                        continue
                    
                    # 将帧加入处理队列
                    try:
                        frame_queue.put((frame_count, frame.copy()), timeout=2.0)
                    except queue.Full:
                        logger.warning("帧队列已满，跳过当前帧")
                        continue
                    
                    # 处理已完成的结果
                    while not result_queue.empty():
                        try:
                            result_index, annotated_frame, recognition_results = result_queue.get_nowait()
                            processed_results[result_index] = (annotated_frame, recognition_results)
                            
                            # 更新统计
                            stats['processed_frames'] += 1
                            stats['faces_detected'] += len(recognition_results)
                            
                            for result in recognition_results:
                                if result['recognized']:
                                    stats['faces_recognized'] += 1
                                    stats['actors_found'].add(result['actor_name'])
                            
                        except queue.Empty:
                            break
                    
                    # 写入已排序的帧到输出视频
                    if writer:
                        for i in sorted(processed_results.keys()):
                            if i <= frame_count - max_workers:  # 确保顺序
                                annotated_frame, _ = processed_results.pop(i)
                                writer.write(annotated_frame)
                    
                    # 进度报告
                    if frame_count % max(1, int(fps * 10)) == 0:  # 每10秒报告一次
                        progress = frame_count / total_frames * 100
                        elapsed_time = time.time() - start_time
                        eta = (elapsed_time / frame_count) * (total_frames - frame_count)
                        
                        logger.info(f"并行处理进度: {progress:.1f}% ({frame_count}/{total_frames}) "
                                  f"用时: {elapsed_time:.0f}s 预计剩余: {eta:.0f}s")
                        
                        if progress_callback:
                            # 为并行处理模式提供更详细的进度信息
                            progress_info = {
                                'progress': progress,
                                'current_frame': frame_count,
                                'total_frames': total_frames,
                                'processed_frames': frame_count,
                                'faces_detected': 0,  # 并行模式暂时无法统计
                                'faces_recognized': 0,  # 并行模式暂时无法统计
                                'actors_found': 0,  # 并行模式暂时无法统计
                                'elapsed_time': elapsed_time,
                                'eta': eta,
                                'fps': fps,
                                'processing_fps': frame_count / elapsed_time if elapsed_time > 0 else 0,
                                'speed_ratio': (frame_count / elapsed_time) / fps if elapsed_time > 0 and fps > 0 else 0,
                                'memory_usage': self._check_memory_usage(),
                                'frame_skip': 1,
                                'processing_mode': 'parallel'
                            }
                            progress_callback(progress_info)
                
                # 发送结束信号
                for _ in range(max_workers):
                    frame_queue.put(None)
                
                # 等待所有任务完成
                frame_queue.join()
                
                # 处理剩余结果
                while not result_queue.empty():
                    try:
                        result_index, annotated_frame, recognition_results = result_queue.get_nowait()
                        processed_results[result_index] = (annotated_frame, recognition_results)
                    except queue.Empty:
                        break
                
                # 写入剩余帧
                if writer:
                    for i in sorted(processed_results.keys()):
                        annotated_frame, _ = processed_results[i]
                        writer.write(annotated_frame)
            
            # 清理资源
            cap.release()
            if writer:
                writer.release()
            
            # 完成统计
            stats['processing_time'] = time.time() - start_time
            stats['actors_found'] = list(stats['actors_found'])
            
            logger.info(f"并行视频处理完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"并行处理视频文件失败: {e}")
            return {'error': str(e)}
        finally:
            self.is_processing = False
