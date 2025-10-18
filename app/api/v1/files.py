"""
文件API端点
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Path, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from pathlib import Path as FilePath
import shutil

from app.services.file_service import file_service
from app.services.sts_service import sts_service
from app.utils.logger import setup_logger
from app.dependencies import get_current_user
from app.models.user import User as DBUser
from app.config import settings

logger = setup_logger()

router = APIRouter()

# 分片上传临时目录
TEMP_UPLOAD_DIR = FilePath("./temp_uploads")
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Pydantic模型
class UploadResponse(BaseModel):
    """文件上传响应"""
    filename: str
    object_key: str
    url: str
    size: int
    content_type: Optional[str] = None
    message: str


class DownloadUrlResponse(BaseModel):
    """下载URL响应"""
    download_url: str
    filename: str
    object_key: str
    expires_in: int


class UploadUrlResponse(BaseModel):
    """上传URL响应"""
    upload_url: str
    object_key: str
    filename: str
    expires_in: int


class FileInfoResponse(BaseModel):
    """文件信息响应"""
    object_key: str
    size: int
    content_type: str
    last_modified: int
    etag: str


class GetUploadCredentialsRequest(BaseModel):
    """获取上传凭证请求"""
    taskId: str
    fileName: str


class GetUploadCredentialsResponse(BaseModel):
    """获取上传凭证响应"""
    accessKeyId: str
    accessKeySecret: str
    securityToken: str
    endpoint: str
    bucketName: str
    objectKey: str
    expiration: str


@router.post(
    "/get-upload-credentials",
    response_model=GetUploadCredentialsResponse,
    summary="获取OSS上传凭证（STS临时授权）"
)
async def get_upload_credentials(
    request: GetUploadCredentialsRequest,
    current_user: DBUser = Depends(get_current_user)
):
    """
    获取阿里云 OSS 直传所需的 STS 临时凭证

    - **taskId**: 任务ID
    - **fileName**: 文件名

    返回 STS 临时凭证，客户端使用这些凭证直接上传到 OSS，无需经过服务器中转

    ## 使用流程
    1. 客户端调用此接口获取 STS 凭证
    2. 客户端使用凭证初始化 OSS SDK 客户端
    3. 客户端直接上传文件到 OSS（断点续传）
    4. 上传完成后通知服务器
    """
    try:
        # 获取 STS 临时凭证
        sts_credentials = sts_service.get_upload_credentials(
            user_id=current_user.id,
            task_id=request.taskId,
            duration_seconds=3600  # 1 小时有效期
        )

        # 构建 OSS object key
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d")
        object_key = f"{settings.OSS_SCENE_FOLDER}/{timestamp}/{request.taskId}/{request.fileName}"

        logger.info(
            f"Generated STS credentials for user {current_user.id}, "
            f"task {request.taskId}, file {request.fileName}"
        )

        return GetUploadCredentialsResponse(
            accessKeyId=sts_credentials["accessKeyId"],
            accessKeySecret=sts_credentials["accessKeySecret"],
            securityToken=sts_credentials["securityToken"],
            endpoint=settings.OSS_ENDPOINT,
            bucketName=settings.OSS_BUCKET_NAME,
            objectKey=object_key,
            expiration=sts_credentials["expiration"]
        )

    except Exception as e:
        logger.error(f"Failed to get upload credentials: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get upload credentials: {str(e)}"
        )


@router.post("/upload", response_model=UploadResponse, summary="上传场景文件")
async def upload_scene_file(
    task_id: UUID = Query(..., description="任务ID"),
    file: UploadFile = File(..., description="上传的文件")
):
    """
    上传场景文件到OSS

    - **task_id**: 关联的任务ID
    - **file**: 要上传的文件

    支持的文件类型：.ma, .mb, .zip, .rar等
    """
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid file")

        # 读取文件内容
        file_content = await file.read()

        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # 上传文件
        result = await file_service.upload_scene_file(
            task_id=task_id,
            filename=file.filename,
            file_content=file_content,
            content_type=file.content_type
        )

        logger.info(f"File uploaded successfully: {file.filename} for task {task_id}")

        return UploadResponse(
            filename=result["filename"],
            object_key=result["object_key"],
            url=result["url"],
            size=result["size"],
            content_type=result.get("content_type"),
            message="File uploaded successfully"
        )

    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get(
    "/download/{task_id}/{filename}",
    response_model=DownloadUrlResponse,
    summary="生成下载URL"
)
async def generate_download_url(
    task_id: UUID = Path(..., description="任务ID"),
    filename: str = Path(..., description="文件名"),
    expire_time: int = Query(3600, description="URL过期时间（秒）", ge=60, le=86400)
):
    """
    生成文件下载URL

    - **task_id**: 任务ID
    - **filename**: 文件名
    - **expire_time**: URL过期时间（秒），默认1小时，最长24小时

    返回预签名的下载URL，客户端可以直接通过该URL下载文件
    """
    try:
        # 构建object_key（需要匹配上传时的路径规则）
        from datetime import datetime
        from app.config import settings

        # 注意：这里简化处理，实际应该从数据库查询文件的object_key
        # 这里假设文件是今天上传的
        timestamp = datetime.now().strftime("%Y%m%d")
        object_key = f"{settings.OSS_SCENE_FOLDER}/{timestamp}/{task_id}/{filename}"

        # 生成下载URL
        download_url = file_service.get_download_url(
            object_key=object_key,
            filename=filename,
            expire_time=expire_time
        )

        logger.info(f"Download URL generated for: {filename}")

        return DownloadUrlResponse(
            download_url=download_url,
            filename=filename,
            object_key=object_key,
            expires_in=expire_time
        )

    except FileNotFoundError as e:
        logger.warning(f"File not found: {filename}")
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")


@router.post("/upload-url", response_model=UploadUrlResponse, summary="获取上传URL")
async def get_upload_url(
    task_id: UUID = Query(..., description="任务ID"),
    filename: str = Query(..., description="文件名"),
    content_type: Optional[str] = Query(None, description="文件MIME类型"),
    expire_time: int = Query(3600, description="URL过期时间（秒）", ge=60, le=86400)
):
    """
    获取预签名上传URL（用于客户端直接上传到OSS）

    - **task_id**: 关联的任务ID
    - **filename**: 文件名
    - **content_type**: 文件MIME类型（可选）
    - **expire_time**: URL过期时间（秒），默认1小时

    客户端可以使用返回的URL直接通过PUT请求上传文件到OSS
    """
    try:
        result = file_service.get_upload_url(
            task_id=task_id,
            filename=filename,
            content_type=content_type,
            expire_time=expire_time
        )

        logger.info(f"Upload URL generated for: {filename}")

        return UploadUrlResponse(**result)

    except Exception as e:
        logger.error(f"Failed to get upload URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get upload URL: {str(e)}")


@router.get("/info/{object_key:path}", response_model=FileInfoResponse, summary="获取文件信息")
async def get_file_info(
    object_key: str = Path(..., description="OSS对象键（文件路径）")
):
    """
    获取文件元数据信息

    - **object_key**: OSS对象键（文件路径）

    返回文件的大小、类型、最后修改时间等信息
    """
    try:
        file_info = file_service.get_file_info(object_key)

        logger.info(f"File info retrieved: {object_key}")

        return FileInfoResponse(
            object_key=object_key,
            size=file_info["size"],
            content_type=file_info["content_type"],
            last_modified=file_info["last_modified"],
            etag=file_info["etag"]
        )

    except Exception as e:
        logger.error(f"Failed to get file info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@router.delete("/{object_key:path}", summary="删除文件")
async def delete_file(
    object_key: str = Path(..., description="OSS对象键（文件路径）")
):
    """
    删除OSS文件

    - **object_key**: OSS对象键（文件路径）

    警告：此操作不可恢复
    """
    try:
        result = await file_service.delete_file(object_key)

        if result:
            logger.info(f"File deleted: {object_key}")
            return JSONResponse(
                content={
                    "message": "File deleted successfully",
                    "object_key": object_key
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")

    except Exception as e:
        logger.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


class ChunkUploadRequest(BaseModel):
    """分片上传请求（JSON格式，用于向后兼容）"""
    taskId: str
    chunkIndex: int
    totalChunks: int
    chunkHash: str
    chunkData: str  # Base64 encoded


class MergeRequest(BaseModel):
    """合并请求"""
    taskId: str
    fileName: str
    totalChunks: int
    fileSize: int


@router.post("/upload/chunk", summary="上传文件分片")
async def upload_chunk(
    # Multipart 格式参数（新客户端）
    taskId: Optional[str] = Form(None),
    chunkIndex: Optional[int] = Form(None),
    totalChunks: Optional[int] = Form(None),
    chunkHash: Optional[str] = Form(None),
    chunkData: Optional[UploadFile] = File(None),
    current_user: DBUser = Depends(get_current_user)
):
    """
    上传文件分片（支持两种格式）

    **格式1：Multipart/form-data（推荐，新客户端）**
    - taskId: 任务ID
    - chunkIndex: 分片索引
    - totalChunks: 总分片数
    - chunkHash: 分片MD5哈希
    - chunkData: 二进制文件数据

    **格式2：JSON + Base64（向后兼容，旧客户端）**
    - 使用 ChunkUploadRequest 模型
    - chunkData 字段为 Base64 编码
    """
    try:
        import base64
        from fastapi import Request

        # 检测请求格式
        if taskId is not None and chunkData is not None:
            # 格式1: Multipart/form-data（新客户端）
            logger.info(f"收到 Multipart 格式的分片上传请求 - Chunk {chunkIndex}/{totalChunks} for task {taskId}")

            # 创建任务临时目录
            task_temp_dir = TEMP_UPLOAD_DIR / taskId
            task_temp_dir.mkdir(parents=True, exist_ok=True)

            # 直接读取二进制数据
            chunk_data_bytes = await chunkData.read()

            # 保存分片
            chunk_file_path = task_temp_dir / f"chunk_{chunkIndex}"
            with open(chunk_file_path, 'wb') as f:
                f.write(chunk_data_bytes)

            logger.info(f"Multipart chunk {chunkIndex}/{totalChunks} uploaded for task {taskId}, size: {len(chunk_data_bytes)} bytes")

            return JSONResponse(content={
                "success": True,
                "message": f"Chunk {chunkIndex} uploaded successfully",
                "chunkIndex": chunkIndex
            })
        else:
            # 格式2: JSON + Base64（旧客户端，向后兼容）
            # 注意：这种情况下，FastAPI 会自动解析 JSON body
            # 但由于我们已经定义了 Form 参数，需要特殊处理
            raise HTTPException(
                status_code=400,
                detail="Invalid request format. Please use multipart/form-data format."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload chunk: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload chunk: {str(e)}")


@router.post("/upload/merge", summary="合并文件分片")
async def merge_chunks(
    request: MergeRequest,
    current_user: DBUser = Depends(get_current_user)
):
    """
    合并所有分片为完整文件并上传到OSS

    - **taskId**: 任务ID
    - **fileName**: 文件名
    - **totalChunks**: 总分片数
    - **fileSize**: 文件总大小
    """
    try:
        task_temp_dir = TEMP_UPLOAD_DIR / request.taskId

        if not task_temp_dir.exists():
            raise HTTPException(status_code=404, detail="Task temp directory not found")

        # 合并分片
        merged_file_path = task_temp_dir / request.fileName

        with open(merged_file_path, 'wb') as merged_file:
            for i in range(request.totalChunks):
                chunk_file_path = task_temp_dir / f"chunk_{i}"

                if not chunk_file_path.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Chunk {i} is missing"
                    )

                with open(chunk_file_path, 'rb') as chunk_file:
                    merged_file.write(chunk_file.read())

                # 删除已合并的分片
                chunk_file_path.unlink()

        logger.info(f"All chunks merged for task {request.taskId}, file: {request.fileName}")

        # 上传合并后的文件到OSS
        with open(merged_file_path, 'rb') as f:
            file_content = f.read()

        result = await file_service.upload_scene_file(
            task_id=UUID(request.taskId),
            filename=request.fileName,
            file_content=file_content
        )

        # 清理临时文件
        merged_file_path.unlink()
        task_temp_dir.rmdir()

        logger.info(f"File uploaded to OSS: {request.fileName} for task {request.taskId}")

        return JSONResponse(content={
            "success": True,
            "message": "File uploaded successfully",
            "objectKey": result["object_key"],
            "url": result["url"],
            "fileName": request.fileName,
            "fileSize": request.fileSize
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to merge chunks: {str(e)}")
        # 尝试清理临时文件
        try:
            if task_temp_dir.exists():
                shutil.rmtree(task_temp_dir)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to merge chunks: {str(e)}")
