"""
人脸处理模块
使用InsightFace进行人脸检测、对齐和特征提取
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import insightface
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

from ..utils.config_loader import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FaceProcessor:
    """人脸处理器类"""
    
    def __init__(self):
        """初始化人脸处理器"""
        self.face_config = config.get_face_recognition_config()
        
        self.model_name = self.face_config.get('model_name', 'buffalo_l')
        self.detection_threshold = self.face_config.get('detection_threshold', 0.6)
        self.embedding_dim = self.face_config.get('embedding_dim', 512)
        self.face_alignment = self.face_config.get('face_alignment', True)
        
        # 新增的配置项
        self.max_faces_per_actor = self.face_config.get('max_faces_per_actor', 5)
        self.min_face_score = self.face_config.get('min_face_score', 0.8)
        
        # 初始化InsightFace应用
        self.app = None
        self._init_face_analysis()
    
    def _init_face_analysis(self):
        """初始化人脸分析应用"""
        try:
            logger.info(f"初始化InsightFace模型: {self.model_name}")
            
            # 创建人脸分析应用
            self.app = FaceAnalysis(
                name=self.model_name,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            
            # 准备模型，设置检测阈值
            self.app.prepare(ctx_id=0, det_thresh=self.detection_threshold)
            
            logger.info("InsightFace模型初始化成功")
            
        except Exception as e:
            logger.error(f"InsightFace模型初始化失败: {e}")
            raise
    
    def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        检测图片中的人脸
        
        Args:
            image: 输入图片 (BGR格式)
            
        Returns:
            检测到的人脸信息列表
        """
        if self.app is None:
            raise RuntimeError("人脸分析应用未初始化")
        
        try:
            # 使用InsightFace检测人脸
            faces = self.app.get(image)
            
            face_info = []
            for face in faces:
                info = {
                    'bbox': face.bbox.astype(int).tolist(),  # 边界框 [x1, y1, x2, y2]
                    'kps': face.kps.astype(int).tolist() if hasattr(face, 'kps') else None,  # 关键点
                    'det_score': float(face.det_score),  # 检测置信度
                    'embedding': face.embedding,  # 人脸特征向量
                    'age': int(face.age) if hasattr(face, 'age') else None,  # 年龄
                    'gender': int(face.gender) if hasattr(face, 'gender') else None,  # 性别
                }
                face_info.append(info)
            
            logger.debug(f"检测到 {len(face_info)} 张人脸")
            return face_info
            
        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            return []
    
    def extract_face_embedding(self, image: np.ndarray, face_info: Dict[str, Any] = None) -> Optional[np.ndarray]:
        """
        提取人脸特征向量
        
        Args:
            image: 输入图片
            face_info: 人脸信息 (如果为None则检测最大的人脸)
            
        Returns:
            人脸特征向量
        """
        if face_info is None:
            # 检测人脸并选择最大的那个
            faces = self.detect_faces(image)
            if not faces:
                return None
            
            # 按检测置信度排序，选择最可信的人脸
            faces.sort(key=lambda x: x['det_score'], reverse=True)
            face_info = faces[0]
        
        return face_info.get('embedding')
    
    def align_face(self, image: np.ndarray, face_info: Dict[str, Any], 
                   output_size: Tuple[int, int] = (112, 112)) -> Optional[np.ndarray]:
        """
        人脸对齐
        
        Args:
            image: 输入图片
            face_info: 人脸信息
            output_size: 输出尺寸
            
        Returns:
            对齐后的人脸图片
        """
        if not self.face_alignment or 'kps' not in face_info or face_info['kps'] is None:
            # 如果没有关键点信息，直接裁剪
            bbox = face_info['bbox']
            x1, y1, x2, y2 = bbox
            face_crop = image[y1:y2, x1:x2]
            return cv2.resize(face_crop, output_size)
        
        try:
            # 使用5个关键点进行仿射变换对齐
            kps = np.array(face_info['kps']).reshape(5, 2)
            
            # 标准人脸关键点位置 (112x112)
            src = np.array([
                [30.2946, 51.6963],  # 左眼
                [65.5318, 51.5014],  # 右眼
                [48.0252, 71.7366],  # 鼻尖
                [33.5493, 92.3655],  # 左嘴角
                [62.7299, 92.2041]   # 右嘴角
            ], dtype=np.float32)
            
            if output_size != (112, 112):
                # 缩放标准关键点位置
                scale_x = output_size[0] / 112
                scale_y = output_size[1] / 112
                src[:, 0] *= scale_x
                src[:, 1] *= scale_y
            
            # 计算仿射变换矩阵
            tform = cv2.estimateAffinePartial2D(kps, src)[0]
            
            # 应用仿射变换
            aligned_face = cv2.warpAffine(image, tform, output_size)
            
            return aligned_face
            
        except Exception as e:
            logger.warning(f"人脸对齐失败，使用简单裁剪: {e}")
            # 回退到简单裁剪
            bbox = face_info['bbox']
            x1, y1, x2, y2 = bbox
            face_crop = image[y1:y2, x1:x2]
            return cv2.resize(face_crop, output_size)
    
    def _imread_chinese(self, image_path: str) -> Optional[np.ndarray]:
        """
        支持中文路径的图片读取函数
        
        Args:
            image_path: 图片路径
            
        Returns:
            图片数组，如果读取失败返回None
        """
        try:
            # 使用numpy读取支持中文路径
            with open(image_path, 'rb') as f:
                image_data = np.frombuffer(f.read(), np.uint8)
                image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                return image
        except Exception as e:
            logger.error(f"读取图片失败 {image_path}: {e}")
            return None
    
    def _imwrite_chinese(self, image_path: str, image: np.ndarray) -> bool:
        """
        支持中文路径的图片保存函数
        
        Args:
            image_path: 图片保存路径
            image: 图片数组
            
        Returns:
            保存是否成功
        """
        try:
            # 编码图片
            success, encoded_image = cv2.imencode('.jpg', image)
            if success:
                # 写入文件
                with open(image_path, 'wb') as f:
                    f.write(encoded_image.tobytes())
                return True
            return False
        except Exception as e:
            logger.error(f"保存图片失败 {image_path}: {e}")
            return False

    def process_image(self, image_path: str) -> List[Dict[str, Any]]:
        """
        处理单张图片，提取所有人脸信息
        
        Args:
            image_path: 图片路径
            
        Returns:
            人脸信息列表
        """
        try:
            # 读取图片 - 支持中文路径
            image = self._imread_chinese(image_path)
            if image is None:
                logger.error(f"无法读取图片: {image_path}")
                return []
            
            # 检测人脸
            faces = self.detect_faces(image)
            
            # 处理每张人脸
            processed_faces = []
            for i, face_info in enumerate(faces):
                try:
                    # 对齐人脸
                    aligned_face = self.align_face(image, face_info)
                    
                    if aligned_face is not None:
                        face_data = {
                            'face_id': i,
                            'image_path': image_path,
                            'bbox': face_info['bbox'],
                            'det_score': face_info['det_score'],
                            'embedding': face_info['embedding'],
                            'aligned_face': aligned_face,
                            'age': face_info.get('age'),
                            'gender': face_info.get('gender')
                        }
                        processed_faces.append(face_data)
                        
                except Exception as e:
                    logger.warning(f"处理人脸 {i} 失败: {e}")
                    continue
            
            logger.debug(f"成功处理 {len(processed_faces)} 张人脸，来源: {Path(image_path).name}")
            return processed_faces
            
        except Exception as e:
            logger.error(f"处理图片失败 {image_path}: {e}")
            return []
    
    def batch_process_images(self, image_paths: List[str], 
                           save_aligned_faces: bool = True) -> List[Dict[str, Any]]:
        """
        批量处理图片
        
        Args:
            image_paths: 图片路径列表
            save_aligned_faces: 是否保存对齐后的人脸图片
            
        Returns:
            所有人脸信息列表
        """
        logger.info(f"开始批量处理 {len(image_paths)} 张图片")
        
        all_faces = []
        storage_config = config.get_storage_config()
        aligned_faces_dir = None
        
        if save_aligned_faces:
            aligned_faces_dir = Path(storage_config.get('images_dir', './data/images')) / 'aligned_faces'
            aligned_faces_dir.mkdir(parents=True, exist_ok=True)
        
        for image_path in image_paths:
            try:
                faces = self.process_image(image_path)
                
                for face_data in faces:
                    # 保存对齐后的人脸图片
                    if save_aligned_faces and aligned_faces_dir:
                        image_name = Path(image_path).stem
                        face_id = face_data['face_id']
                        aligned_path = aligned_faces_dir / f"{image_name}_face_{face_id}.jpg"
                        
                        self._imwrite_chinese(str(aligned_path), face_data['aligned_face'])
                        face_data['aligned_face_path'] = str(aligned_path)
                        
                        # 移除内存中的图片数据以节省空间
                        del face_data['aligned_face']
                    
                    all_faces.append(face_data)
                    
            except Exception as e:
                logger.error(f"处理图片失败 {image_path}: {e}")
                continue
        
        logger.info(f"批量处理完成，共提取 {len(all_faces)} 张人脸")
        return all_faces
    
    def calculate_face_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        计算两个人脸特征向量的相似度
        
        Args:
            embedding1: 人脸特征向量1
            embedding2: 人脸特征向量2
            
        Returns:
            相似度 (0-1之间，1表示完全相同)
        """
        try:
            # 归一化特征向量
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)
            
            # 计算余弦相似度
            similarity = np.dot(embedding1, embedding2)
            
            # 将相似度映射到0-1范围
            similarity = (similarity + 1) / 2
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"计算人脸相似度失败: {e}")
            return 0.0
    
    def filter_best_faces(self, faces: List[Dict[str, Any]], 
                         max_faces: int = None, min_score: float = None) -> List[Dict[str, Any]]:
        """
        筛选最佳人脸
        
        Args:
            faces: 人脸信息列表
            max_faces: 最大保留人脸数量（None时使用配置值）
            min_score: 最低检测分数（None时使用配置值）
            
        Returns:
            筛选后的人脸列表
        """
        # 使用配置项作为默认值
        if max_faces is None:
            max_faces = self.max_faces_per_actor
        if min_score is None:
            min_score = self.min_face_score
        
        # 过滤低质量人脸
        filtered_faces = [face for face in faces if face['det_score'] >= min_score]
        
        # 按检测分数排序
        filtered_faces.sort(key=lambda x: x['det_score'], reverse=True)
        
        # 简单去重：移除相似度过高的人脸
        final_faces = []
        for face in filtered_faces:
            is_duplicate = False
            for existing_face in final_faces:
                similarity = self.calculate_face_similarity(
                    face['embedding'], existing_face['embedding']
                )
                if similarity > 0.95:  # 相似度阈值
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                final_faces.append(face)
                
            if len(final_faces) >= max_faces:
                break
        
        # 详细的过滤统计
        original_count = len(faces)
        after_quality_filter = len(filtered_faces)
        final_count = len(final_faces)
        
        logger.info(f"人脸筛选统计: 原始{original_count}张 → 质量过滤后{after_quality_filter}张 → 最终{final_count}张 "
                   f"(限制:{max_faces}, 阈值:{min_score})")
        
        if original_count > final_count:
            filtered_out = original_count - final_count
            logger.info(f"过滤掉了 {filtered_out} 张人脸 (质量不足: {original_count - after_quality_filter}, "
                       f"重复/超限: {after_quality_filter - final_count})")
        
        return final_faces
    
    def get_face_config(self) -> Dict[str, Any]:
        """获取人脸处理配置信息"""
        return {
            'max_faces_per_actor': self.max_faces_per_actor,
            'min_face_score': self.min_face_score,
            'detection_threshold': self.detection_threshold,
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'face_alignment': self.face_alignment
        }
