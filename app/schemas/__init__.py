"""
Pydantic Schemas
"""
from app.schemas.common import (
    Response,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfile,
    BalanceResponse,
    RechargeRequest,
    UpdateMemberLevelRequest,
)
from app.schemas.task import (
    TaskStatus,
    TaskPriority,
    TaskBase,
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskResponse,
    TaskListResponse,
    TaskLogBase,
    TaskLogCreate,
    TaskLogResponse,
    TaskLogsResponse,
)
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    RegisterResponse,
    LoginResponse,
    ChangePasswordRequest,
    UserResponse as AuthUserResponse,
)

__all__ = [
    # Common
    "Response",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfile",
    "BalanceResponse",
    "RechargeRequest",
    "UpdateMemberLevelRequest",
    # Task
    "TaskStatus",
    "TaskPriority",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskStatusUpdate",
    "TaskResponse",
    "TaskListResponse",
    "TaskLogBase",
    "TaskLogCreate",
    "TaskLogResponse",
    "TaskLogsResponse",
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "LogoutRequest",
    "RegisterResponse",
    "LoginResponse",
    "ChangePasswordRequest",
    "AuthUserResponse",
]
