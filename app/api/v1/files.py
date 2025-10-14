"""
文件API端点
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.file_service import file_service
from app.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter()


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
