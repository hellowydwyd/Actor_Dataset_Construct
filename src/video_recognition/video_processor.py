"""
视频人脸识别处理器
输入视频帧，识别并标记演员姓名
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time

from ..face_recognition.face_processor import FaceProcessor
from ..database.vector_database import VectorDatabaseManager
from ..utils.logger import get_logger
from ..utils.chinese_text_renderer import draw_chinese_text

logger = get_logger(__name__)


class VideoFaceRecognizer:
    """视频人脸识别器"""
    
    def __init__(self, similarity_threshold: float = 0.6, movie_title: str = None):
        """
        初始化视频人脸识别器
        
        Args:
            similarity_threshold: 人脸相似度阈值
            movie_title: 目标电影名称，如果指定则只在该电影演员范围内识别
        """
        self.similarity_threshold = similarity_threshold
        self.movie_title = movie_title
        
        # 初始化组件
        logger.info("初始化视频人脸识别器...")
        self.face_processor = FaceProcessor()
        self.vector_db = VectorDatabaseManager()
        
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
                            'target_movie': self.movie_title
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
                
                # 准备标签文本
                actor_name = result['actor_name']
                similarity = result['similarity']
                label = f"{actor_name} ({similarity:.2f})"
                
                # 使用中文文字渲染器绘制标签
                annotated_frame = draw_chinese_text(
                    annotated_frame, 
                    label, 
                    (x1 + 5, y1 - 5),
                    font_size=18,
                    color=(255, 255, 255),  # 白色文字
                    background_color=color,  # 使用人物配色作为背景
                    background_padding=8
                )
            else:
                # 未识别的人脸 - 灰色框
                color = (128, 128, 128)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                
                # 标记为未知
                label = "未知"
                annotated_frame = draw_chinese_text(
                    annotated_frame, 
                    label, 
                    (x1 + 5, y1 - 5),
                    font_size=18,
                    color=(255, 255, 255),  # 白色文字
                    background_color=color,  # 灰色背景
                    background_padding=8
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
                          frame_skip: int = 1, progress_callback=None) -> Dict[str, Any]:
        """
        处理视频文件，识别并标注人脸
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径（可选）
            frame_skip: 跳帧数量（1=处理每帧，2=每2帧处理1帧）
            
        Returns:
            处理结果统计
        """
        try:
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"视频信息: {width}x{height}, {fps}fps, {total_frames}帧")
            
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
                'processing_time': 0
            }
            
            frame_count = 0
            start_time = time.time()
            
            logger.info("开始处理视频...")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # 跳帧处理
                if frame_count % frame_skip != 0:
                    if writer:
                        writer.write(frame)
                    continue
                
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
                
                # 显示处理进度
                if frame_count % max(1, fps) == 0:  # 每秒显示一次进度
                    progress = frame_count / total_frames * 100
                    logger.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames})")
                    
                    # 调用进度回调函数
                    if progress_callback:
                        progress_callback(progress, frame_count, total_frames)
            
            # 清理资源
            cap.release()
            if writer:
                writer.release()
            
            # 完成统计
            stats['processing_time'] = time.time() - start_time
            stats['actors_found'] = list(stats['actors_found'])
            
            logger.info(f"视频处理完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"处理视频文件失败: {e}")
            return {'error': str(e)}
    
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
