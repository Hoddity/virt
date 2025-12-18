from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from typing import Dict, Any
import asyncio
import logging
import time
from datetime import datetime

from app.services.ymq_service import ymq_service
from app.services.monitoring_service import monitoring_service
from app.config.settings import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Фоновая задача для обработки очереди
queue_processor_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global queue_processor_task
    
    # Запускаем фоновые задачи при старте
    if ymq_service.is_enabled():
        queue_processor_task = asyncio.create_task(process_queue_messages())
        if hasattr(ymq_service, 'test_mode') and ymq_service.test_mode:
            logger.info("Queue processor started in TEST mode")
        else:
            logger.info("Queue processor started in PRODUCTION mode")
    else:
        logger.warning("Yandex Queue not configured, queue processor disabled")
    
    logger.info("Monitoring service started")
    
    yield
    
    # Останавливаем при завершении
    if queue_processor_task:
        queue_processor_task.cancel()
        try:
            await queue_processor_task
        except asyncio.CancelledError:
            logger.info("Queue processor stopped")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    debug=settings.DEBUG,
    version="1.0.0"
)

async def process_queue_messages():
    """Фоновая задача для обработки сообщений из очереди"""
    logger.info(f"Starting queue processor for {settings.YMQ_QUEUE_DEFAULT}")
    
    while True:
        try:
            # Получаем сообщения из очереди
            messages = await ymq_service.receive_messages(
                settings.YMQ_QUEUE_DEFAULT,
                max_messages=5,
                wait_time_seconds=10
            )
            
            # Обрабатываем каждое сообщение
            for message in messages:
                try:
                    await process_single_message(message)
                    monitoring_service.increment_counter('queue_messages_processed')
                    
                    # Удаляем обработанное сообщение
                    if 'ReceiptHandle' in message:
                        await ymq_service.delete_message(
                            settings.YMQ_QUEUE_DEFAULT,
                            message['ReceiptHandle']
                        )
                        
                except Exception as e:
                    monitoring_service.increment_counter('queue_messages_failed')
                    logger.error(f"Error processing message: {e}")
            
            # Пауза перед следующей проверкой
            await asyncio.sleep(2)
            
        except asyncio.CancelledError:
            logger.info("Queue processor cancelled")
            break
        except Exception as e:
            logger.error(f"Queue processor error: {e}")
            await asyncio.sleep(5)

async def process_single_message(message: Dict[str, Any]):
    """Обработка одного сообщения из очереди"""
    message_body = message.get('Body', {})
    message_type = message_body.get('type', 'unknown')
    
    logger.info(f"Processing message type: {message_type}")
    
    if message_type == 'create_task':
        await handle_create_task(message_body.get('data', {}))
    elif message_type == 'test':
        await handle_test_message(message_body)
    else:
        logger.warning(f"Unknown message type: {message_type}")

async def handle_create_task(task_data: Dict[str, Any]):
    """Обработка создания задачи"""
    logger.info(f"Creating task with data: {task_data}")
    logger.info(f"Task would be created: {task_data}")

async def handle_test_message(message_data: Dict[str, Any]):
    """Обработка тестового сообщения"""
    logger.info(f"Test message received: {message_data}")

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware для сбора метрик"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Собираем метрики
        monitoring_service.increment_counter('requests_total')
        
        if 200 <= response.status_code < 400:
            monitoring_service.increment_counter('requests_success')
        else:
            monitoring_service.increment_counter('requests_error')
            
        # Записываем время ответа
        response_time = time.time() - start_time
        monitoring_service.record_response_time(response_time)
        
        # Добавляем метрики в заголовки
        response.headers['X-Response-Time'] = str(response_time)
        
        return response
        
    except Exception as e:
        monitoring_service.increment_counter('requests_error')
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    mode = "test" if hasattr(ymq_service, 'test_mode') and ymq_service.test_mode else "production"
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "queue_enabled": ymq_service.is_enabled(),
        "queue_mode": mode,
        "queue_name": settings.YMQ_QUEUE_DEFAULT,
        "monitoring": "enabled",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "monitoring": "/monitoring",
            "queue_stats": "/api/queue/stats",
            "send_task": "/api/tasks/send-to-queue (POST)",
            "test_queue": "/api/tasks/test-queue (POST)",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check для балансировщика"""
    mode = "test" if hasattr(ymq_service, 'test_mode') and ymq_service.test_mode else "production"
    
    # Собираем метрики для health check
    metrics = monitoring_service.get_application_metrics()
    system_metrics = monitoring_service.get_system_metrics()
    
    return {
        "status": "healthy",
        "service": "backend",
        "queue_connected": ymq_service.is_enabled(),
        "queue_mode": mode,
        "monitoring": {
            "requests_total": metrics.get('requests_total', 0),
            "success_rate": metrics.get('success_rate', 0),
            "uptime_seconds": system_metrics.get('uptime_seconds', 0)
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """Эндпоинт для получения метрик"""
    try:
        all_metrics = monitoring_service.get_all_metrics()
        
        # Форматируем в Prometheus-like format
        prometheus_metrics = []
        
        # Application metrics
        app_metrics = all_metrics['application']
        for key, value in app_metrics.items():
            if isinstance(value, (int, float)) and not key == 'timestamp':
                prometheus_metrics.append(f'virt_backend_{key}{{type="application"}} {value}')
        
        # System metrics
        sys_metrics = all_metrics['system']
        for key, value in sys_metrics.items():
            if isinstance(value, (int, float)) and not key == 'timestamp':
                prometheus_metrics.append(f'virt_backend_{key}{{type="system"}} {value}')
        
        return {
            "format": "prometheus",
            "metrics": prometheus_metrics,
            "raw": all_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring")
async def get_monitoring_dashboard():
    """Эндпоинт для мониторинга"""
    try:
        metrics = monitoring_service.get_application_metrics()
        system_metrics = monitoring_service.get_system_metrics()
        
        # Определяем статус системы
        status = "healthy"
        if metrics.get('error_rate', 0) > 10:
            status = "warning"
        if metrics.get('error_rate', 0) > 30:
            status = "critical"
        
        return {
            "status": status,
            "application": {
                "requests": {
                    "total": metrics.get('requests_total', 0),
                    "success": metrics.get('requests_success', 0),
                    "error": metrics.get('requests_error', 0),
                    "success_rate": f"{metrics.get('success_rate', 0):.1f}%",
                    "error_rate": f"{metrics.get('error_rate', 0):.1f}%"
                },
                "queue": {
                    "messages_sent": metrics.get('queue_messages_sent', 0),
                    "messages_processed": metrics.get('queue_messages_processed', 0),
                    "messages_failed": metrics.get('queue_messages_failed', 0)
                },
                "performance": {
                    "response_time_avg": f"{metrics.get('response_time_avg', 0):.3f}s"
                }
            },
            "system": {
                "cpu_percent": f"{system_metrics.get('cpu_percent', 0):.1f}%",
                "memory_mb": f"{system_metrics.get('memory_mb', 0):.1f} MB",
                "thread_count": system_metrics.get('thread_count', 0),
                "uptime_seconds": system_metrics.get('uptime_seconds', 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/send-to-queue")
async def send_to_queue(task_data: Dict[str, Any]):
    """Отправка задачи в очередь"""
    try:
        if not ymq_service.is_enabled():
            raise HTTPException(status_code=500, detail="Yandex Queue not configured")
        
        message_body = {
            'type': 'create_task',
            'data': task_data,
            'timestamp': datetime.now().isoformat(),
            'source': 'api'
        }
        
        message_id = await ymq_service.send_message(
            settings.YMQ_QUEUE_DEFAULT,
            message_body
        )
        
        # Собираем метрики
        monitoring_service.increment_counter('queue_messages_sent')
        
        mode = "test" if hasattr(ymq_service, 'test_mode') and ymq_service.test_mode else "production"
        
        return {
            "status": "success",
            "message": "Task queued successfully",
            "message_id": message_id,
            "queue": settings.YMQ_QUEUE_DEFAULT,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        monitoring_service.increment_counter('requests_error')
        logger.error(f"Error sending to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/queue/stats")
async def get_queue_stats():
    """Получение статистики очереди"""
    try:
        if not ymq_service.is_enabled():
            return {
                "enabled": False,
                "message": "Yandex Queue not configured",
                "timestamp": datetime.now().isoformat()
            }
        
        stats = await ymq_service.get_queue_stats(settings.YMQ_QUEUE_DEFAULT)
        mode = "test" if hasattr(ymq_service, 'test_mode') and ymq_service.test_mode else "production"
        
        return {
            "enabled": True,
            "mode": mode,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        monitoring_service.increment_counter('requests_error')
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/test-queue")
async def test_queue():
    """Тестовый эндпоинт для отправки сообщения в очередь"""
    try:
        if not ymq_service.is_enabled():
            raise HTTPException(status_code=500, detail="Yandex Queue not configured")
        
        test_message = {
            'type': 'test',
            'message': 'Hello from FastAPI!',
            'timestamp': datetime.now().isoformat(),
            'test': True
        }
        
        message_id = await ymq_service.send_message(
            settings.YMQ_QUEUE_DEFAULT,
            test_message
        )
        
        monitoring_service.increment_counter('queue_messages_sent')
        
        mode = "test" if hasattr(ymq_service, 'test_mode') and ymq_service.test_mode else "production"
        
        return {
            "status": "success",
            "message": "Test message sent successfully",
            "message_id": message_id,
            "queue": settings.YMQ_QUEUE_DEFAULT,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        monitoring_service.increment_counter('requests_error')
        logger.error(f"Error sending test message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/reset")
async def reset_monitoring():
    """Сброс метрик мониторинга"""
    monitoring_service.reset_metrics()
    return {
        "status": "success",
        "message": "Monitoring metrics reset",
        "timestamp": datetime.now().isoformat()
    }

# Импортируем существующие CRUD эндпоинты
from app import crud, models, database

@app.get("/api/crud/status")
async def crud_status():
    """Статус CRUD операций"""
    monitoring_service.increment_counter('db_operations')
    return {
        "crud_operations": ["create", "read", "update", "delete"],
        "database": "sqlite",
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }
