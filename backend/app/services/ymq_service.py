import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import aioboto3
from botocore.exceptions import ClientError
from app.config.settings import settings

logger = logging.getLogger(__name__)

class YandexQueueService:
    """Сервис для работы с Yandex Message Queue (с поддержкой тестового режима)"""
    
    def __init__(self):
        # Проверяем, тестовые ли это ключи
        self.test_mode = (
            settings.YMQ_ACCESS_KEY_ID == "test_access_key" and
            settings.YMQ_SECRET_ACCESS_KEY == "test_secret_key"
        )
        
        if self.test_mode:
            logger.info("Running in TEST mode with mock Yandex Queue")
            self.enabled = True
            return
        
        # Режим с реальными ключами
        if not settings.YMQ_ACCESS_KEY_ID or not settings.YMQ_SECRET_ACCESS_KEY:
            logger.warning("Yandex Queue credentials not set")
            self.enabled = False
            return
        
        self.enabled = True
        try:
            self.session = aioboto3.Session(
                aws_access_key_id=settings.YMQ_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YMQ_SECRET_ACCESS_KEY,
                region_name=settings.YMQ_REGION
            )
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            self.enabled = False
    
    async def send_message(self, 
                          queue_name: str, 
                          message_body: Dict[str, Any],
                          delay_seconds: int = 0,
                          message_attributes: Optional[Dict] = None) -> str:
        """
        Отправка сообщения в очередь
        """
        if not self.enabled:
            raise Exception("Yandex Queue not configured")
        
        # ТЕСТОВЫЙ РЕЖИМ: имитируем отправку
        if self.test_mode:
            logger.info(f"[TEST MODE] Sending to queue {queue_name}: {message_body}")
            timestamp = int(datetime.now().timestamp())
            message_id = f"test_msg_{timestamp}_{hash(str(message_body))}"
            logger.info(f"[TEST MODE] Generated message ID: {message_id}")
            return message_id
        
        # РЕАЛЬНЫЙ РЕЖИМ: отправка в Yandex Queue
        queue_url = f"{settings.YMQ_QUEUE_PREFIX}/{queue_name}"
        
        try:
            async with self.session.client(
                'sqs',
                endpoint_url='https://message-queue.api.cloud.yandex.net'
            ) as client:
                
                attributes = self._prepare_attributes(message_attributes or {})
                
                response = await client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message_body),
                    DelaySeconds=delay_seconds,
                    MessageAttributes=attributes
                )
                
                message_id = response['MessageId']
                logger.info(f"Message sent to queue {queue_name}, ID: {message_id}")
                
                return message_id
                
        except ClientError as e:
            logger.error(f"Failed to send message to queue {queue_name}: {e}")
            raise
    
    async def receive_messages(self, 
                              queue_name: str, 
                              max_messages: int = 10,
                              wait_time_seconds: int = 20) -> List[Dict]:
        """
        Получение сообщений из очереди
        """
        if not self.enabled:
            logger.warning("Yandex Queue not enabled")
            return []
        
        # ТЕСТОВЫЙ РЕЖИМ
        if self.test_mode:
            logger.info(f"[TEST MODE] Receiving from queue {queue_name}")
            return []
        
        # РЕАЛЬНЫЙ РЕЖИМ
        queue_url = f"{settings.YMQ_QUEUE_PREFIX}/{queue_name}"
        
        try:
            async with self.session.client(
                'sqs',
                endpoint_url='https://message-queue.api.cloud.yandex.net'
            ) as client:
                
                response = await client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=max_messages,
                    WaitTimeSeconds=wait_time_seconds,
                    MessageAttributeNames=['All'],
                    VisibilityTimeout=30
                )
                
                messages = response.get('Messages', [])
                
                for message in messages:
                    if 'Body' in message:
                        try:
                            message['Body'] = json.loads(message['Body'])
                        except json.JSONDecodeError:
                            pass
                
                logger.info(f"Received {len(messages)} messages from queue {queue_name}")
                
                return messages
                
        except ClientError as e:
            logger.error(f"Failed to receive messages from queue {queue_name}: {e}")
            return []
    
    async def delete_message(self, queue_name: str, receipt_handle: str) -> bool:
        """Удаление сообщения из очереди"""
        if self.test_mode:
            logger.info(f"[TEST MODE] Deleting message from {queue_name}")
            return True
        
        if not self.enabled:
            return False
        
        queue_url = f"{settings.YMQ_QUEUE_PREFIX}/{queue_name}"
        
        try:
            async with self.session.client(
                'sqs',
                endpoint_url='https://message-queue.api.cloud.yandex.net'
            ) as client:
                
                await client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                
                logger.info(f"Message deleted from queue {queue_name}")
                return True
                
        except ClientError as e:
            logger.error(f"Failed to delete message from queue {queue_name}: {e}")
            return False
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Получение статистики очереди"""
        if self.test_mode:
            logger.info(f"[TEST MODE] Getting stats for queue {queue_name}")
            return {
                'queue_name': queue_name,
                'messages_available': 0,
                'messages_in_flight': 0,
                'messages_delayed': 0,
                'mode': 'test',
                'status': 'mock_queue_active'
            }
        
        if not self.enabled:
            return {'enabled': False, 'message': 'Yandex Queue not configured'}
        
        queue_url = f"{settings.YMQ_QUEUE_PREFIX}/{queue_name}"
        
        try:
            async with self.session.client(
                'sqs',
                endpoint_url='https://message-queue.api.cloud.yandex.net'
            ) as client:
                
                response = await client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=[
                        'ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible',
                        'ApproximateNumberOfMessagesDelayed',
                        'CreatedTimestamp',
                        'LastModifiedTimestamp'
                    ]
                )
                
                attributes = response.get('Attributes', {})
                
                return {
                    'queue_name': queue_name,
                    'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
                    'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                    'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                    'created_at': self._timestamp_to_datetime(attributes.get('CreatedTimestamp')),
                    'modified_at': self._timestamp_to_datetime(attributes.get('LastModifiedTimestamp'))
                }
                
        except ClientError as e:
            logger.error(f"Failed to get queue stats for {queue_name}: {e}")
            return {}
    
    def _prepare_attributes(self, attributes: Dict) -> Dict:
        """Подготовка атрибутов сообщения"""
        prepared = {}
        
        standard_attrs = {
            'Source': 'fastapi-backend',
            'Timestamp': datetime.now().isoformat(),
            'MessageType': 'task'
        }
        
        all_attrs = {**standard_attrs, **attributes}
        
        for key, value in all_attrs.items():
            if isinstance(value, str):
                prepared[key] = {
                    'DataType': 'String',
                    'StringValue': value
                }
            elif isinstance(value, (int, float)):
                prepared[key] = {
                    'DataType': 'Number',
                    'StringValue': str(value)
                }
            elif isinstance(value, bool):
                prepared[key] = {
                    'DataType': 'String',
                    'StringValue': str(value).lower()
                }
        
        return prepared
    
    def _timestamp_to_datetime(self, timestamp: Optional[str]) -> Optional[str]:
        """Конвертация timestamp в datetime строку"""
        if not timestamp:
            return None
        
        try:
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.isoformat()
        except (ValueError, TypeError):
            return None
    
    def is_enabled(self) -> bool:
        """Проверка, включен ли сервис"""
        return self.enabled
    
    def is_test_mode_active(self) -> bool:
        """Проверка, работает ли в тестовом режиме"""
        return self.test_mode

# Создаем экземпляр сервиса
ymq_service = YandexQueueService()
