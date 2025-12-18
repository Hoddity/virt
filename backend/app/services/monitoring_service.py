import logging
import time
from datetime import datetime
from typing import Dict, Any
from threading import Lock
import os

logger = logging.getLogger(__name__)

class MonitoringService:
    """Сервис для сбора метрик и мониторинга"""
    
    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_error': 0,
            'queue_messages_sent': 0,
            'queue_messages_processed': 0,
            'queue_messages_failed': 0,
            'db_operations': 0,
            'response_time_sum': 0.0,
            'response_time_count': 0
        }
        self.lock = Lock()
        self.start_time = time.time()
        
    def increment_counter(self, metric_name: str, value: int = 1):
        """Увеличить счетчик метрики"""
        with self.lock:
            if metric_name in self.metrics:
                self.metrics[metric_name] += value
            else:
                self.metrics[metric_name] = value
                
    def record_response_time(self, response_time: float):
        """Записать время ответа"""
        with self.lock:
            self.metrics['response_time_sum'] += response_time
            self.metrics['response_time_count'] += 1
            
    def get_system_metrics(self) -> Dict[str, Any]:
        """Получить системные метрики"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'thread_count': process.num_threads(),
                'uptime_seconds': time.time() - self.start_time,
                'timestamp': datetime.now().isoformat()
            }
        except ImportError:
            logger.warning("psutil not installed, using simplified metrics")
            return {
                'cpu_percent': 0,
                'memory_mb': 0,
                'thread_count': 0,
                'uptime_seconds': time.time() - self.start_time,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                'cpu_percent': 0,
                'memory_mb': 0,
                'thread_count': 0,
                'uptime_seconds': time.time() - self.start_time,
                'timestamp': datetime.now().isoformat()
            }
            
    def get_application_metrics(self) -> Dict[str, Any]:
        """Получить метрики приложения"""
        with self.lock:
            metrics = self.metrics.copy()
            
            # Вычисляем среднее время ответа
            if metrics['response_time_count'] > 0:
                metrics['response_time_avg'] = (
                    metrics['response_time_sum'] / metrics['response_time_count']
                )
            else:
                metrics['response_time_avg'] = 0
                
            # Вычисляем success rate
            if metrics['requests_total'] > 0:
                metrics['success_rate'] = (
                    metrics['requests_success'] / metrics['requests_total'] * 100
                )
            else:
                metrics['success_rate'] = 0
                
            # Вычисляем error rate
            if metrics['requests_total'] > 0:
                metrics['error_rate'] = (
                    metrics['requests_error'] / metrics['requests_total'] * 100
                )
            else:
                metrics['error_rate'] = 0
                
            metrics['timestamp'] = datetime.now().isoformat()
            return metrics
            
    def get_all_metrics(self) -> Dict[str, Any]:
        """Получить все метрики"""
        return {
            'application': self.get_application_metrics(),
            'system': self.get_system_metrics(),
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        
    def reset_metrics(self):
        """Сбросить метрики (для тестирования)"""
        with self.lock:
            self.metrics = {
                'requests_total': 0,
                'requests_success': 0,
                'requests_error': 0,
                'queue_messages_sent': 0,
                'queue_messages_processed': 0,
                'queue_messages_failed': 0,
                'db_operations': 0,
                'response_time_sum': 0.0,
                'response_time_count': 0
            }

# Глобальный экземпляр сервиса мониторинга
monitoring_service = MonitoringService()
