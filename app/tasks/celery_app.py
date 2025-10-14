"""
Celery应用配置
"""
from celery import Celery
from app.config import settings

# 创建Celery应用实例
celery_app = Celery(
    "yuntu_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务结果设置
    result_expires=3600,  # 结果过期时间（秒）
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },

    # 任务执行设置
    task_acks_late=True,  # 任务执行完成后才确认
    task_reject_on_worker_lost=True,  # Worker丢失时拒绝任务
    task_track_started=True,  # 跟踪任务开始状态

    # Worker设置
    worker_prefetch_multiplier=1,  # 每个worker一次只预取1个任务
    worker_max_tasks_per_child=1000,  # 每个worker子进程最多执行1000个任务后重启

    # 任务路由
    task_routes={
        "app.tasks.render_tasks.simulate_render_task": {"queue": "render"},
    },

    # 任务时间限制
    task_time_limit=7200,  # 硬时间限制（秒）
    task_soft_time_limit=3600,  # 软时间限制（秒）

    # Beat调度设置
    beat_schedule={
        # 可以在这里添加定时任务
        # 'cleanup-old-tasks': {
        #     'task': 'app.tasks.cleanup_tasks.cleanup_old_tasks',
        #     'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点执行
        # },
    },
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])

if __name__ == "__main__":
    celery_app.start()
