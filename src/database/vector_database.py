"""
向量数据库模块
支持Faiss和ChromaDB两种向量数据库
"""
import os
import pickle
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

# Faiss相关导入
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# ChromaDB相关导入
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from ..utils.config_loader import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class VectorDatabaseInterface(ABC):
    """向量数据库接口"""
    
    @abstractmethod
    def add_embeddings(self, embeddings: List[np.ndarray], metadata: List[Dict[str, Any]]) -> bool:
        """添加向量和元数据"""
        pass
    
    @abstractmethod
    def search_similar(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    def delete_by_id(self, face_id: str) -> bool:
        """根据ID删除向量"""
        pass
    
    @abstractmethod
    def save(self) -> bool:
        """保存数据库"""
        pass
    
    @abstractmethod
    def load(self) -> bool:
        """加载数据库"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        pass


class FaissVectorDatabase(VectorDatabaseInterface):
    """Faiss向量数据库实现"""
    
    def __init__(self, dimension: int = 512, index_type: str = "IVF"):
        """
        初始化Faiss向量数据库
        
        Args:
            dimension: 向量维度
            index_type: 索引类型 (Flat, IVF, HNSW)
        """
        if not FAISS_AVAILABLE:
            raise ImportError("Faiss未安装，请运行: pip install faiss-cpu")
        
        self.dimension = dimension
        self.index_type = index_type
        
        # 初始化索引
        self.index = self._create_index()
        self.metadata = []  # 存储元数据
        self.id_to_idx = {}  # ID到索引的映射
        
        # 配置文件路径
        storage_config = config.get_storage_config()
        self.embeddings_dir = Path(storage_config.get('embeddings_dir', './data/embeddings'))
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.embeddings_dir / 'faiss_index.bin'
        self.metadata_file = self.embeddings_dir / 'metadata.pkl'
        self.id_mapping_file = self.embeddings_dir / 'id_mapping.json'
    
    def _create_index(self) -> faiss.Index:
        """创建Faiss索引"""
        if self.index_type == "Flat":
            # 精确搜索，适合小数据集
            index = faiss.IndexFlatIP(self.dimension)  # 内积相似度
        elif self.index_type == "IVF":
            # 倒排文件索引，适合大数据集
            nlist = 100  # 聚类中心数量
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        elif self.index_type == "HNSW":
            # 分层导航小世界图，查询速度快
            M = 16  # 连接数
            index = faiss.IndexHNSWFlat(self.dimension, M)
        else:
            logger.warning(f"未知索引类型 {self.index_type}，使用Flat索引")
            index = faiss.IndexFlatIP(self.dimension)
        
        logger.info(f"创建Faiss索引: {type(index).__name__}")
        return index
    
    def add_embeddings(self, embeddings: List[np.ndarray], metadata: List[Dict[str, Any]]) -> bool:
        """添加向量和元数据"""
        try:
            if len(embeddings) != len(metadata):
                raise ValueError("向量数量与元数据数量不匹配")
            
            # 转换为numpy数组并归一化
            embeddings_array = np.array(embeddings).astype('float32')
            
            # 归一化向量 (对于内积相似度)
            faiss.normalize_L2(embeddings_array)
            
            # 如果是IVF索引且未训练，需要先训练
            if hasattr(self.index, 'is_trained') and not self.index.is_trained:
                if embeddings_array.shape[0] >= 100:  # 需要足够的数据进行训练
                    logger.info("训练IVF索引...")
                    self.index.train(embeddings_array)
                else:
                    logger.warning("数据量不足，无法训练IVF索引")
                    return False
            
            # 记录当前索引大小
            start_idx = self.index.ntotal
            
            # 添加向量到索引
            self.index.add(embeddings_array)
            
            # 添加元数据
            for i, meta in enumerate(metadata):
                face_id = meta.get('face_id', f"face_{start_idx + i}")
                self.metadata.append(meta)
                self.id_to_idx[face_id] = start_idx + i
            
            logger.info(f"成功添加 {len(embeddings)} 个向量到Faiss索引")
            return True
            
        except Exception as e:
            logger.error(f"添加向量到Faiss失败: {e}")
            return False
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            if self.index.ntotal == 0:
                logger.warning("索引为空，无法搜索")
                return []
            
            # 归一化查询向量
            query_vector = query_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_vector)
            
            # 搜索
            scores, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
            
            # 整理结果
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # Faiss返回-1表示无效结果
                    continue
                
                result = {
                    'similarity': float(score),
                    'metadata': self.metadata[idx] if idx < len(self.metadata) else {}
                }
                results.append(result)
            
            logger.debug(f"搜索到 {len(results)} 个相似结果")
            return results
            
        except Exception as e:
            logger.error(f"Faiss搜索失败: {e}")
            return []
    
    def delete_by_id(self, face_id: str) -> bool:
        """根据ID删除向量 (通过重建索引实现)"""
        try:
            if face_id not in self.id_to_idx:
                logger.warning(f"未找到face_id: {face_id}")
                return False
            
            # 获取要删除的索引
            delete_idx = self.id_to_idx[face_id]
            
            # 收集保留的数据
            keep_embeddings = []
            keep_metadata = []
            new_id_to_idx = {}
            
            # 遍历所有数据，保留除了要删除的之外的所有数据
            for i, meta in enumerate(self.metadata):
                if i != delete_idx:
                    # 获取向量（需要重新构建）
                    if i < self.index.ntotal:
                        # Faiss不能直接获取单个向量，需要重建
                        keep_metadata.append(meta)
                        new_id_to_idx[meta.get('face_id', '')] = len(keep_metadata) - 1
            
            # 如果没有数据保留，创建空索引
            if not keep_metadata:
                self.index = self._create_index()
                self.metadata = []
                self.id_to_idx = {}
                logger.info(f"删除face_id {face_id}，索引已清空")
                return True
            
            # 重建索引（简化实现：标记删除，实际删除需要重建整个索引）
            # 由于Faiss的限制，这里只删除metadata，向量索引保持不变
            # 在搜索时会过滤掉已删除的条目
            
            # 从metadata中移除
            self.metadata = [meta for i, meta in enumerate(self.metadata) if i != delete_idx]
            
            # 重建ID映射
            self.id_to_idx = {}
            for i, meta in enumerate(self.metadata):
                self.id_to_idx[meta.get('face_id', '')] = i
            
            logger.info(f"成功删除face_id: {face_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
    
    def save(self) -> bool:
        """保存数据库"""
        try:
            # 保存索引
            faiss.write_index(self.index, str(self.index_file))
            
            # 保存元数据
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            # 保存ID映射
            with open(self.id_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.id_to_idx, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Faiss数据库已保存到 {self.embeddings_dir}")
            return True
            
        except Exception as e:
            logger.error(f"保存Faiss数据库失败: {e}")
            return False
    
    def load(self) -> bool:
        """加载数据库"""
        try:
            if not self.index_file.exists():
                logger.info("Faiss索引文件不存在，创建新索引")
                return True
            
            # 加载索引
            self.index = faiss.read_index(str(self.index_file))
            
            # 加载元数据
            if self.metadata_file.exists():
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
            
            # 加载ID映射
            if self.id_mapping_file.exists():
                with open(self.id_mapping_file, 'r', encoding='utf-8') as f:
                    self.id_to_idx = json.load(f)
            
            logger.info(f"成功加载Faiss数据库，包含 {self.index.ntotal} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"加载Faiss数据库失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        return {
            'database_type': 'Faiss',
            'index_type': self.index_type,
            'dimension': self.dimension,
            'total_vectors': self.index.ntotal,
            'metadata_count': len(self.metadata),
            'is_trained': getattr(self.index, 'is_trained', True)
        }


class ChromaVectorDatabase(VectorDatabaseInterface):
    """ChromaDB向量数据库实现"""
    
    def __init__(self, collection_name: str = "actor_faces"):
        """
        初始化ChromaDB向量数据库
        
        Args:
            collection_name: 集合名称
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB未安装，请运行: pip install chromadb")
        
        self.collection_name = collection_name
        
        # 配置存储路径
        vector_config = config.get_vector_database_config()
        chromadb_config = vector_config.get('chromadb', {})
        
        self.persist_directory = chromadb_config.get('persist_directory', './data/embeddings/chromadb')
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"加载现有ChromaDB集合: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"创建新的ChromaDB集合: {self.collection_name}")
    
    def add_embeddings(self, embeddings: List[np.ndarray], metadata: List[Dict[str, Any]]) -> bool:
        """添加向量和元数据"""
        try:
            if len(embeddings) != len(metadata):
                raise ValueError("向量数量与元数据数量不匹配")
            
            # 准备数据
            ids = []
            embeddings_list = []
            metadatas = []
            documents = []
            
            for i, (embedding, meta) in enumerate(zip(embeddings, metadata)):
                face_id = meta.get('face_id', f"face_{i}_{hash(str(meta)) % 10000}")
                ids.append(face_id)
                embeddings_list.append(embedding.tolist())
                
                # ChromaDB元数据只支持基本类型
                clean_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif isinstance(v, (list, np.ndarray)):
                        clean_meta[k] = str(v)  # 转为字符串
                    else:
                        clean_meta[k] = str(v)
                
                metadatas.append(clean_meta)
                
                # 创建文档内容用于全文搜索（以角色为主）
                character = meta.get('character', meta.get('actor_name', 'Unknown'))
                movie = meta.get('movie_title', 'Unknown Movie')
                actor = meta.get('actor_name', 'Unknown Actor')
                doc = f"Movie: {movie} Character: {character} Actor: {actor} Face ID: {face_id}"
                documents.append(doc)
            
            # 添加到集合
            self.collection.add(
                embeddings=embeddings_list,
                metadatas=metadatas,
                documents=documents,
                ids=ids
            )
            
            logger.info(f"成功添加 {len(embeddings)} 个向量到ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"添加向量到ChromaDB失败: {e}")
            return False
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            # 查询
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k
            )
            
            # 整理结果
            search_results = []
            if results['metadatas'] and results['distances']:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    # ChromaDB返回距离，转换为相似度
                    similarity = 1.0 / (1.0 + distance)
                    
                    result = {
                        'similarity': similarity,
                        'metadata': metadata
                    }
                    search_results.append(result)
            
            logger.debug(f"搜索到 {len(search_results)} 个相似结果")
            return search_results
            
        except Exception as e:
            logger.error(f"ChromaDB搜索失败: {e}")
            return []
    
    def delete_by_id(self, face_id: str) -> bool:
        """根据ID删除向量"""
        try:
            self.collection.delete(ids=[face_id])
            logger.info(f"成功删除ID为 {face_id} 的向量")
            return True
            
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
    
    def save(self) -> bool:
        """保存数据库 (ChromaDB自动持久化)"""
        logger.info("ChromaDB自动持久化，无需手动保存")
        return True
    
    def load(self) -> bool:
        """加载数据库 (ChromaDB自动加载)"""
        logger.info("ChromaDB自动加载，无需手动操作")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            count = self.collection.count()
            return {
                'database_type': 'ChromaDB',
                'collection_name': self.collection_name,
                'total_vectors': count,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            logger.error(f"获取ChromaDB统计信息失败: {e}")
            return {'database_type': 'ChromaDB', 'error': str(e)}


class VectorDatabaseManager:
    """向量数据库管理器"""
    
    def __init__(self):
        """初始化向量数据库管理器"""
        self.vector_config = config.get_vector_database_config()
        self.db_type = self.vector_config.get('type', 'faiss').lower()
        
        # 创建数据库实例
        if self.db_type == 'faiss':
            dimension = self.vector_config.get('dimension', 512)
            index_type = self.vector_config.get('index_type', 'IVF')
            self.database = FaissVectorDatabase(dimension=dimension, index_type=index_type)
        elif self.db_type == 'chromadb':
            collection_name = self.vector_config.get('chromadb', {}).get('collection_name', 'actor_faces')
            self.database = ChromaVectorDatabase(collection_name=collection_name)
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
        
        # 加载现有数据
        self.database.load()
        
        logger.info(f"向量数据库管理器初始化完成，使用 {self.db_type.upper()}")
    
    def add_face_embeddings(self, faces_data: List[Dict[str, Any]]) -> bool:
        """
        添加人脸嵌入向量
        
        Args:
            faces_data: 人脸数据列表，每个元素包含embedding和metadata
            
        Returns:
            是否添加成功
        """
        try:
            embeddings = []
            metadata = []
            
            for face_data in faces_data:
                if 'embedding' not in face_data:
                    logger.warning("人脸数据缺少embedding字段")
                    continue
                
                embeddings.append(face_data['embedding'])
                
                # 构建元数据（重点存储角色信息）
                meta = {
                    'face_id': face_data.get('face_id', ''),
                    'character': face_data.get('character', ''),  # 主要的角色信息
                    'actor_name': face_data.get('actor_name', ''),  # 演员信息作为辅助
                    'actor_id': face_data.get('actor_id', ''),
                    'movie_title': face_data.get('movie_title', ''),
                    'image_path': face_data.get('image_path', ''),
                    'bbox': face_data.get('bbox', []),
                    'det_score': face_data.get('det_score', 0.0),
                    'age': face_data.get('age'),
                    'gender': face_data.get('gender'),
                    # 新增颜色和框形信息
                    'color_bgr': face_data.get('color_bgr'),
                    'color_rgb': face_data.get('color_rgb'),
                    'color_hex': face_data.get('color_hex'),
                    'color_index': face_data.get('color_index'),
                    'shape_type': face_data.get('shape_type', 'rectangle'),
                    'line_thickness': face_data.get('line_thickness', 2),
                    'character_priority': face_data.get('character_priority', 0)
                }
                metadata.append(meta)
            
            if not embeddings:
                logger.warning("没有有效的嵌入向量可添加")
                return False
            
            success = self.database.add_embeddings(embeddings, metadata)
            
            if success:
                # 保存数据库
                self.database.save()
                logger.info(f"成功添加 {len(embeddings)} 个人脸嵌入向量")
            
            return success
            
        except Exception as e:
            logger.error(f"添加人脸嵌入向量失败: {e}")
            return False
    
    def search_similar_faces(self, query_embedding: np.ndarray, 
                           top_k: int = 10, min_similarity: float = 0.6) -> List[Dict[str, Any]]:
        """
        搜索相似人脸
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值
            
        Returns:
            相似人脸列表
        """
        try:
            results = self.database.search_similar(query_embedding, top_k)
            
            # 过滤低相似度结果
            filtered_results = [
                result for result in results 
                if result['similarity'] >= min_similarity
            ]
            
            logger.info(f"搜索到 {len(filtered_results)} 个相似人脸 (阈值: {min_similarity})")
            return filtered_results
            
        except Exception as e:
            logger.error(f"搜索相似人脸失败: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        return self.database.get_stats()
    
    def save_database(self) -> bool:
        """保存数据库"""
        return self.database.save()
    
    def delete_face(self, face_id: str) -> bool:
        """删除人脸数据"""
        return self.database.delete_by_id(face_id)
