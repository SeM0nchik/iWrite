from celery import shared_task
from .redis_service import RecommendationService

@shared_task(bind=True, autoretry_for=[Exception,], retry_backoff=5)
def recalculate_score_batch(self):
    service = RecommendationService()
    service.recompute_batch(batch_size=100)
