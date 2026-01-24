from uuid import uuid4
from pytils.translit import slugify
from django.db import models

def unique_slugify(instance, slug, slug_field):
    model = instance.__class__
    if not slug_field:
        slug_field = slugify(instance)
    if model.objects.filter(slug=slug_field).exclude(id=instance.id).exists():
        slug_field = f'{slugify(slug)}--{uuid4().hex[:8]}'
    return slug_field