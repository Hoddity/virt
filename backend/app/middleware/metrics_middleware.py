import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.monitoring_service import monitoring_service
import logging

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware для сбора метрик запросов"""
    
    async def dispatch(self, request: Request, call_next):
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
            response.headers['X-Request-Id'] = str(int(start_time * 1000))
            
            return response
            
        except Exception as e:
            monitoring_service.increment_counter('requests_error')
            logger.error(f"Request error: {e}")
            raise
