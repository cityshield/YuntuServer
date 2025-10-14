"""
日志上传 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
import base64
import os
from pathlib import Path

router = APIRouter(prefix="/logs", tags=["logs"])

# 日志存储目录
LOG_STORAGE_DIR = Path("./client_logs")
LOG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class LogUploadRequest(BaseModel):
    """日志上传请求"""
    fileName: str
    fileSize: int
    logContent: str  # Base64 encoded
    uploadTime: str


@router.post("/upload")
async def upload_log(request: LogUploadRequest):
    """
    上传客户端日志文件

    客户端在启动时会自动上传所有日志文件到服务器
    方便开发者远程查看和分析问题
    """
    try:
        # 解码 Base64 日志内容
        log_data = base64.b64decode(request.logContent)

        # 创建按日期分类的子目录
        upload_date = datetime.fromisoformat(request.uploadTime).strftime("%Y-%m-%d")
        date_dir = LOG_STORAGE_DIR / upload_date
        date_dir.mkdir(parents=True, exist_ok=True)

        # 保存日志文件（添加时间戳避免覆盖）
        timestamp = datetime.now().strftime("%H%M%S")
        file_name_parts = request.fileName.rsplit('.', 1)
        if len(file_name_parts) == 2:
            safe_file_name = f"{file_name_parts[0]}_{timestamp}.{file_name_parts[1]}"
        else:
            safe_file_name = f"{request.fileName}_{timestamp}"

        file_path = date_dir / safe_file_name

        with open(file_path, 'wb') as f:
            f.write(log_data)

        print(f"[LOG] 收到客户端日志: {safe_file_name} ({request.fileSize} bytes)")
        print(f"[LOG] 保存路径: {file_path}")

        return {
            "success": True,
            "message": "日志上传成功",
            "savedPath": str(file_path),
            "fileName": safe_file_name
        }

    except Exception as e:
        print(f"[ERROR] 日志上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"日志上传失败: {str(e)}"
        )


@router.get("/list")
async def list_logs():
    """
    列出所有已上传的日志文件
    """
    try:
        logs = []

        for date_dir in sorted(LOG_STORAGE_DIR.iterdir(), reverse=True):
            if date_dir.is_dir():
                for log_file in sorted(date_dir.iterdir(), reverse=True):
                    if log_file.is_file():
                        logs.append({
                            "date": date_dir.name,
                            "fileName": log_file.name,
                            "filePath": str(log_file),
                            "fileSize": log_file.stat().st_size,
                            "uploadTime": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                        })

        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志列表失败: {str(e)}"
        )


@router.get("/download/{date}/{file_name}")
async def download_log(date: str, file_name: str):
    """
    下载指定的日志文件
    """
    try:
        file_path = LOG_STORAGE_DIR / date / file_name

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="日志文件不存在"
            )

        with open(file_path, 'rb') as f:
            content = f.read()

        return {
            "success": True,
            "fileName": file_name,
            "content": base64.b64encode(content).decode('utf-8')
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载日志失败: {str(e)}"
        )
