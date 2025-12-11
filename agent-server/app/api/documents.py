"""
文档管理API
"""
import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from app.core.document_loader import document_loader
from app.core.vector_store import vector_store_manager
from app.core.config import settings

router = APIRouter()

# 临时文件存储目录
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentInfo(BaseModel):
    """文档信息响应模型"""
    file_name: str
    file_type: str
    status: str
    message: str


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """上传并处理文档"""
    try:
        # 检查文件大小
        file_content = await file.read()
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )
        
        # 检查文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(settings.SUPPORTED_EXTENSIONS)}"
            )
        
        # 保存文件
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 加载文档
        documents = document_loader.load_file(file_path)
        
        # 添加描述到元数据
        if description:
            for doc in documents:
                doc.metadata["description"] = description
        
        # 分割文档
        split_docs = document_loader.split_documents(documents)
        
        # 添加到向量存储
        vector_store_manager.add_documents(split_docs)
        
        # 清理临时文件
        os.remove(file_path)
        
        return DocumentInfo(
            file_name=file.filename,
            file_type=file_ext,
            status="success",
            message=f"成功上传并处理文档，共 {len(split_docs)} 个文档块"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档时出错: {str(e)}")


@router.post("/upload-directory")
async def upload_directory(directory_path: str):
    """上传整个目录的文档"""
    try:
        if not os.path.isdir(directory_path):
            raise HTTPException(status_code=400, detail="目录不存在")
        
        # 加载目录中的所有文档
        documents = document_loader.load_directory(directory_path)
        
        if not documents:
            return {"message": "目录中没有找到支持的文档文件"}
        
        # 分割文档
        split_docs = document_loader.split_documents(documents)
        
        # 添加到向量存储
        vector_store_manager.add_documents(split_docs)
        
        return {
            "message": f"成功处理目录，共 {len(split_docs)} 个文档块",
            "document_count": len(split_docs)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理目录时出错: {str(e)}")


@router.get("/info")
async def get_document_info():
    """获取知识库信息"""
    try:
        info = vector_store_manager.get_collection_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")


@router.delete("/clear")
async def clear_all_documents():
    """清空所有文档"""
    try:
        success = vector_store_manager.delete_all()
        if success:
            return {"message": "成功清空所有文档"}
        else:
            raise HTTPException(status_code=500, detail="清空文档失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空文档时出错: {str(e)}")

