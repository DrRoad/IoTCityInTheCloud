from __future__ import absolute_import
from celery import Celery

app = Celery('tasks',
             broker='amqp://rabbitmq:rabbitmq@localhost:5672//',
             backend='amqp://rabbitmq:rabbitmq@localhost:5672//',
             include=['tasks']
             )

app.conf.update(
        CELERY_TASK_SERIALIZER = 'json',
        CELERY_RESULT_SERIALIZER = 'json',
        CELERY_ACCEPT_CONTENT=['json'],
        CELERY_TIMEZONE = 'Europe/Lisbon',
        CELERY_ENABLE_UTC = True
                )

