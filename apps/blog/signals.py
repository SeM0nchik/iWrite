from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Post
from ..recommendations.redis_service import RecommendationService


@receiver(post_save, sender=Post)
def create_post(sender, instance, created, **kwargs):
    if created:
        RecommendationService.on_new_post(instance.pk)