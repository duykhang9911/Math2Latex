import os

from redis import Redis
from rq import Queue


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OCR_QUEUE_NAME = "math2latex"


def get_ocr_queue() -> Queue:
    connection = Redis.from_url(REDIS_URL)
    return Queue(OCR_QUEUE_NAME, connection=connection, default_timeout=7200)


def enqueue_job(function, *args):
    return get_ocr_queue().enqueue(
        function,
        *args,
        job_timeout=7200,
        result_ttl=86400,
        failure_ttl=604800,
    )