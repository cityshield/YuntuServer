"""
渲染任务 - 模拟渲染流程
"""
import time
import random
from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal

from celery import Task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.models.task import Task as TaskModel, TaskLog
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.utils.logger import logger


class RenderTask(Task):
    """自定义Celery任务基类，支持异步数据库操作"""

    async def async_run(self, *args, **kwargs):
        """子类需要实现此方法"""
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        """同步调用，内部使用asyncio运行异步方法"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.async_run(*args, **kwargs))


@celery_app.task(bind=True, base=RenderTask, name="app.tasks.render_tasks.simulate_render_task")
async def simulate_render_task(self, task_id: str):
    """
    模拟渲染任务

    Args:
        task_id: 任务ID
    """
    logger.info(f"开始渲染任务: {task_id}")

    async with AsyncSessionLocal() as db:
        try:
            # 1. 获取任务信息
            result = await db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"任务不存在: {task_id}")
                return {"status": "error", "message": "Task not found"}

            # 2. 检查任务状态
            if task.status not in [1, 2, 3]:  # Pending, Queued, Rendering
                logger.warning(f"任务状态不正确，无法渲染: {task_id}, status={task.status}")
                return {"status": "error", "message": "Invalid task status"}

            # 3. 更新任务状态为渲染中
            task.status = 3  # Rendering
            task.started_at = datetime.now()
            task.progress = 0
            await db.commit()
            await db.refresh(task)

            # 记录日志
            log = TaskLog(
                task_id=task.id,
                log_level="INFO",
                message=f"开始渲染任务: {task.task_name}"
            )
            db.add(log)
            await db.commit()

            # 4. 计算渲染参数
            start_frame = task.start_frame or 1
            end_frame = task.end_frame or 1
            frame_step = task.frame_step or 1
            total_frames = (end_frame - start_frame) // frame_step + 1

            logger.info(f"渲染参数 - 开始帧: {start_frame}, 结束帧: {end_frame}, 步长: {frame_step}, 总帧数: {total_frames}")

            # 记录渲染参数日志
            log = TaskLog(
                task_id=task.id,
                log_level="INFO",
                message=f"渲染参数 - 帧范围: {start_frame}-{end_frame}, 步长: {frame_step}, 总帧数: {total_frames}, 分辨率: {task.width}x{task.height}"
            )
            db.add(log)
            await db.commit()

            # 5. 模拟逐帧渲染
            rendered_frames = 0
            total_cost = Decimal("0.00")

            for current_frame in range(start_frame, end_frame + 1, frame_step):
                # 检查任务是否被取消或暂停
                await db.refresh(task)
                if task.status == 7:  # Cancelled
                    logger.info(f"任务已取消: {task_id}")
                    log = TaskLog(
                        task_id=task.id,
                        log_level="WARNING",
                        message="任务已取消"
                    )
                    db.add(log)
                    await db.commit()
                    return {"status": "cancelled", "message": "Task cancelled"}

                if task.status == 4:  # Paused
                    logger.info(f"任务已暂停: {task_id}")
                    log = TaskLog(
                        task_id=task.id,
                        log_level="WARNING",
                        message="任务已暂停"
                    )
                    db.add(log)
                    await db.commit()
                    return {"status": "paused", "message": "Task paused"}

                # 模拟渲染时间
                if settings.RENDER_SIMULATE_MODE:
                    render_time = random.uniform(
                        settings.RENDER_FRAME_TIME_MIN,
                        settings.RENDER_FRAME_TIME_MAX
                    )
                    time.sleep(render_time)

                # 计算费用
                frame_cost = Decimal(str(settings.RENDER_COST_PER_FRAME))
                total_cost += frame_cost

                # 更新进度
                rendered_frames += 1
                progress = int((rendered_frames / total_frames) * 100)
                task.progress = progress
                task.actual_cost = total_cost
                await db.commit()

                # 记录帧渲染日志（每10帧记录一次，或最后一帧）
                if current_frame % (frame_step * 10) == 0 or current_frame == end_frame:
                    log = TaskLog(
                        task_id=task.id,
                        log_level="INFO",
                        message=f"渲染帧 {current_frame}/{end_frame} 完成，进度: {progress}%"
                    )
                    db.add(log)
                    await db.commit()
                    logger.info(f"任务 {task_id} - 渲染帧 {current_frame}/{end_frame}, 进度: {progress}%")

                # TODO: 这里应该调用WebSocket推送进度更新
                # await websocket_manager.send_task_progress(
                #     user_id=str(task.user_id),
                #     task_id=str(task.id),
                #     progress=progress,
                #     current_frame=current_frame,
                #     total_frames=total_frames
                # )

            # 6. 渲染完成，更新任务状态
            task.status = 5  # Completed
            task.progress = 100
            task.completed_at = datetime.now()
            task.actual_cost = total_cost
            await db.commit()

            # 记录完成日志
            log = TaskLog(
                task_id=task.id,
                log_level="INFO",
                message=f"渲染完成 - 总帧数: {total_frames}, 实际费用: ¥{total_cost}"
            )
            db.add(log)
            await db.commit()

            logger.info(f"任务渲染完成: {task_id}, 总帧数: {total_frames}, 费用: ¥{total_cost}")

            # TODO: 发送WebSocket通知任务完成
            # await websocket_manager.send_task_completed(
            #     user_id=str(task.user_id),
            #     task_id=str(task.id),
            #     actual_cost=float(total_cost)
            # )

            return {
                "status": "success",
                "message": "Render completed",
                "task_id": str(task.id),
                "rendered_frames": rendered_frames,
                "actual_cost": float(total_cost)
            }

        except Exception as e:
            # 渲染失败，更新任务状态
            logger.error(f"渲染任务失败: {task_id}, 错误: {str(e)}")

            try:
                result = await db.execute(
                    select(TaskModel).where(TaskModel.id == UUID(task_id))
                )
                task = result.scalar_one_or_none()

                if task:
                    task.status = 6  # Failed
                    task.error_message = str(e)
                    await db.commit()

                    # 记录错误日志
                    log = TaskLog(
                        task_id=task.id,
                        log_level="ERROR",
                        message=f"渲染失败: {str(e)}"
                    )
                    db.add(log)
                    await db.commit()

                    # TODO: 发送WebSocket通知任务失败
                    # await websocket_manager.send_task_failed(
                    #     user_id=str(task.user_id),
                    #     task_id=str(task.id),
                    #     error_message=str(e)
                    # )
            except Exception as update_error:
                logger.error(f"更新任务状态失败: {update_error}")

            return {
                "status": "error",
                "message": str(e),
                "task_id": task_id
            }


@celery_app.task(name="app.tasks.render_tasks.cancel_render_task")
async def cancel_render_task(task_id: str):
    """
    取消渲染任务

    Args:
        task_id: 任务ID
    """
    logger.info(f"取消渲染任务: {task_id}")

    async with AsyncSessionLocal() as db:
        try:
            # 更新任务状态
            result = await db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"任务不存在: {task_id}")
                return {"status": "error", "message": "Task not found"}

            task.status = 7  # Cancelled
            await db.commit()

            # 记录日志
            log = TaskLog(
                task_id=task.id,
                log_level="WARNING",
                message="任务已被用户取消"
            )
            db.add(log)
            await db.commit()

            logger.info(f"任务取消成功: {task_id}")

            return {"status": "success", "message": "Task cancelled"}

        except Exception as e:
            logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
            return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.render_tasks.pause_render_task")
async def pause_render_task(task_id: str):
    """
    暂停渲染任务

    Args:
        task_id: 任务ID
    """
    logger.info(f"暂停渲染任务: {task_id}")

    async with AsyncSessionLocal() as db:
        try:
            # 更新任务状态
            result = await db.execute(
                select(TaskModel).where(TaskModel.id == UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"任务不存在: {task_id}")
                return {"status": "error", "message": "Task not found"}

            if task.status != 3:  # 只有渲染中的任务才能暂停
                logger.warning(f"任务状态不正确，无法暂停: {task_id}, status={task.status}")
                return {"status": "error", "message": "Task is not rendering"}

            task.status = 4  # Paused
            await db.commit()

            # 记录日志
            log = TaskLog(
                task_id=task.id,
                log_level="WARNING",
                message="任务已被用户暂停"
            )
            db.add(log)
            await db.commit()

            logger.info(f"任务暂停成功: {task_id}")

            return {"status": "success", "message": "Task paused"}

        except Exception as e:
            logger.error(f"暂停任务失败: {task_id}, 错误: {str(e)}")
            return {"status": "error", "message": str(e)}
