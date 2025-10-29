"""
OSS 上传回调处理端点
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.models.file import File, UploadSource
from app.models.task_file import TaskFile, FileUploadStatus
from app.models.upload_task import UploadTask, TaskStatus
from app.utils.oss_callback import (
    extract_callback_params,
    build_callback_success_response,
    build_callback_error_response
)
from app.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/oss-callback", tags=["OSS Callback"])


@router.post("/upload-complete")
async def handle_upload_complete_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    处理 OSS 上传完成回调

    客户端上传文件到 OSS 后,OSS 自动调用此接口通知服务端
    服务端创建/更新数据库记录

    无需身份验证,因为是 OSS 调用
    """
    try:
        # 1. 读取请求体
        body = await request.body()

        logger.info(f"Received OSS callback - Content-Type: {request.headers.get('content-type')}")
        logger.info(f"Callback body length: {len(body)} bytes")

        # 2. 提取回调参数
        params = extract_callback_params(request, body)

        logger.info(f"OSS callback params: {params}")

        # 3. 验证必需参数
        required_fields = ["task_file_id", "user_id", "drive_id", "oss_key", "filename", "size"]
        missing_fields = [field for field in required_fields if field not in params]

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return build_callback_error_response(error_msg)

        # 4. 解析参数
        task_file_id = UUID(params["task_file_id"])
        user_id = UUID(params["user_id"])
        drive_id = UUID(params["drive_id"])
        oss_key = params["oss_key"]
        filename = params["filename"]
        file_size = int(params["size"])
        md5 = params.get("md5")
        mime_type = params.get("mime_type")
        folder_id_str = params.get("folder_id")
        folder_id = UUID(folder_id_str) if folder_id_str else None

        logger.info(f"Processing OSS callback for TaskFile: {task_file_id}, File: {filename}")

        # 5. 查询 TaskFile
        result = await db.execute(
            select(TaskFile).where(TaskFile.id == task_file_id)
        )
        task_file = result.scalar_one_or_none()

        if not task_file:
            error_msg = f"TaskFile not found: {task_file_id}"
            logger.error(error_msg)
            return build_callback_error_response(error_msg)

        # 6. 检查是否已经处理过（幂等性）
        if task_file.status == FileUploadStatus.COMPLETED and task_file.file_id:
            logger.info(f"TaskFile already completed: {task_file_id}")
            return build_callback_success_response()

        # 7. 生成 OSS URL
        from app.config import settings
        oss_url = f"{settings.OSS_BASE_URL}/{oss_key}"

        # 8. 创建 File 记录
        new_file = File(
            name=filename,
            original_name=filename,
            size=file_size,
            extension=_get_file_extension(filename),
            mime_type=mime_type,
            oss_key=oss_key,
            oss_url=oss_url,
            md5=md5 or task_file.md5,  # 使用回调提供的 MD5 或 TaskFile 的 MD5
            drive_id=drive_id,
            folder_id=folder_id,
            uploaded_by=user_id,
            upload_source=UploadSource.CLIENT
        )

        db.add(new_file)
        await db.flush()
        await db.refresh(new_file)

        logger.info(f"Created File record: {new_file.id} for {filename}")

        # 9. 更新 TaskFile 状态
        task_file.status = FileUploadStatus.COMPLETED
        task_file.file_id = new_file.id
        task_file.oss_key = oss_key
        task_file.oss_url = oss_url
        task_file.upload_progress = 100.0
        task_file.completed_at = datetime.utcnow()

        if md5:
            task_file.md5 = md5

        logger.info(f"Updated TaskFile status to COMPLETED: {task_file_id}")

        # 10. 更新 UploadTask 进度
        result = await db.execute(
            select(UploadTask).where(UploadTask.id == task_file.task_id)
        )
        upload_task = result.scalar_one_or_none()

        if upload_task:
            # 更新已上传文件数和大小
            upload_task.uploaded_files += 1
            upload_task.uploaded_size += file_size

            # 如果所有文件都上传完成，更新任务状态
            if upload_task.uploaded_files >= upload_task.total_files:
                upload_task.status = TaskStatus.COMPLETED
                upload_task.completed_at = datetime.utcnow()
                logger.info(f"UploadTask completed: {upload_task.id}")
            else:
                upload_task.status = TaskStatus.UPLOADING
                logger.info(f"UploadTask progress: {upload_task.uploaded_files}/{upload_task.total_files}")

        # 11. 提交数据库事务
        await db.commit()

        logger.info(f"OSS callback processed successfully for {filename}")

        # 12. 返回成功响应
        return build_callback_success_response()

    except ValueError as e:
        # UUID 解析错误
        error_msg = f"Invalid UUID format: {str(e)}"
        logger.error(error_msg)
        return build_callback_error_response(error_msg)

    except Exception as e:
        # 其他错误
        error_msg = f"Failed to process callback: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await db.rollback()
        return build_callback_error_response(error_msg)


def _get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    import os
    return os.path.splitext(filename)[1]
