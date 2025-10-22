"""
文件操作日志模型
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.base import Base, UUID


class OperationType(str, enum.Enum):
    """操作类型"""
    UPLOAD = "upload"  # 上传文件
    DOWNLOAD = "download"  # 下载文件
    DELETE = "delete"  # 删除文件
    RENAME = "rename"  # 重命名
    MOVE = "move"  # 移动文件
    COPY = "copy"  # 复制文件
    SHARE = "share"  # 分享文件
    CREATE_FOLDER = "create_folder"  # 创建文件夹
    DELETE_FOLDER = "delete_folder"  # 删除文件夹
    RESTORE = "restore"  # 恢复文件（从回收站）
    PERMANENT_DELETE = "permanent_delete"  # 永久删除


class FileOperation(Base):
    """文件操作日志表"""

    __tablename__ = "file_operations"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # 操作类型
    operation_type = Column(Enum(OperationType), nullable=False, index=True)

    # 关联关系
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)  # 操作人
    file_id = Column(UUID(), ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True)  # 操作的文件
    folder_id = Column(UUID(), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)  # 操作的文件夹
    drive_id = Column(UUID(), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属盘符

    # 操作详情
    target_name = Column(String(255), nullable=True)  # 目标名称（用于记录被删除/重命名的文件名）
    source_path = Column(String(1024), nullable=True)  # 源路径（用于移动/复制操作）
    target_path = Column(String(1024), nullable=True)  # 目标路径（用于移动/复制操作）

    # 客户端信息
    ip_address = Column(String(45), nullable=True)  # 操作者 IP 地址
    user_agent = Column(String(512), nullable=True)  # 用户代理字符串
    device_info = Column(String(255), nullable=True)  # 设备信息（如 "Windows 10", "iOS 15"）

    # 操作结果
    is_success = Column(String(10), default="true", nullable=False)  # 操作是否成功
    error_message = Column(Text, nullable=True)  # 错误信息（如果操作失败）

    # 额外信息（JSON 格式存储灵活数据）
    extra_data = Column(JSON, nullable=True)  # 额外的元数据

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    file = relationship("File", foreign_keys=[file_id])
    folder = relationship("Folder", foreign_keys=[folder_id])
    drive = relationship("Drive", foreign_keys=[drive_id])

    def __repr__(self):
        return f"<FileOperation(id={self.id}, type={self.operation_type}, user_id={self.user_id})>"

    @property
    def operation_display(self) -> str:
        """获取操作类型的中文显示"""
        display_map = {
            OperationType.UPLOAD: "上传文件",
            OperationType.DOWNLOAD: "下载文件",
            OperationType.DELETE: "删除文件",
            OperationType.RENAME: "重命名",
            OperationType.MOVE: "移动文件",
            OperationType.COPY: "复制文件",
            OperationType.SHARE: "分享文件",
            OperationType.CREATE_FOLDER: "创建文件夹",
            OperationType.DELETE_FOLDER: "删除文件夹",
            OperationType.RESTORE: "恢复文件",
            OperationType.PERMANENT_DELETE: "永久删除",
        }
        return display_map.get(self.operation_type, str(self.operation_type))
