from django.core.management.base import BaseCommand
from apps.recommendations.redis_service import RecommendationService
class Command(BaseCommand):
    help = 'Синхронизирует все посты с кэшем в Redis'

    def handle(self, *args, **options):
        service = RecommendationService()
        service.init_cache()
