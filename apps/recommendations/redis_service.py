from datetime import datetime

import redis
from math import exp, log
from .splaytree import SplayTree
from time import time
from django.conf import settings
from ..blog.models import Post

class RecommendationService:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            cls._instance.tree = SplayTree()
        return cls._instance

    def __init__(self):
        pass

    def calculate_score(self, post_id) ->float:
        metrics = self.redis.hgetall(f"post:{post_id}:metrics")
        views = int(metrics.get("views", 0))
        likes = int(metrics.get("likes", 0))

        created_at = float(metrics.get("created_at", datetime.now().timestamp()))
        last_access = float(metrics.get("last_access", created_at))

        activity = log(1 + views) * 0.4 + log(1 + likes) * 0.6

        recency = exp(-0.001 * (time() - last_access))

        age = time() - created_at

        freshness = exp(-0.001 * age)


        return activity * 0.5 + freshness * 0.4 + recency * 0.1

    def on_view(self, post_id : int):

        self.redis.hincrby(f"post:{post_id}:metrics", "views", 1)
        self.redis.hset(f"post:{post_id}:metrics", mapping={"last_access" : datetime.now().timestamp()})

        old_score = self.redis.hget(f"post:{post_id}:metrics", "cached_score")
        if old_score:
            self.tree.delete(post_id, float(old_score))

        new_score = self.calculate_score(post_id)
        self.redis.hset(f"post:{post_id}:metrics", "cached_score", str(new_score))
        self.tree.insert(post_id, new_score)

    def on_like(self, post_id : int):
        self.redis.hincrby(f"post:{post_id}:metrics", "likes", 1)
        self.redis.hset(f"post:{post_id}:metrics", mapping={"last_access" : datetime.now().timestamp()})

        old_score = self.redis.hget(f"post:{post_id}:metrics", "cached_score")
        if old_score:
            self.tree.delete(post_id, float(old_score))

        new_score = self.calculate_score(post_id)
        self.redis.hset(f"post:{post_id}:metrics", "cached_score", str(new_score))
        self.tree.insert(post_id, new_score)


    def on_new_post(self, post_id: int):
        self.redis.hset(f"post:{post_id}:metrics", mapping={
            "created_at": datetime.now().timestamp(),
            "views": 0,
            "likes": 0,
            "last_access": datetime.now().timestamp(),
        })
        score = self.calculate_score(post_id)
        self.redis.hset(f"post:{post_id}:metrics", "cached_score", str(score))
        self.tree.insert(post_id, score)


    def get_recommendations(self, limit : int = 5):
        return self.tree.get_top_posts(limit)

    def _get_or_create_metrics(self, post_id):
        key = f"post:{post_id}:metrics"

        if self.redis.exists(key):
            cached_score = float(self.redis.hget(key, "cached_score"))
            self.tree.insert(post_id, cached_score)
            return True

        try:
            post = Post.objects.get(pk=post_id)
            created_at = post.create.timestamp()
            likes = post.get_positive_count()

            self.redis.hset(key, mapping={
                "created_at": created_at,
                "views": 0,
                "likes": likes,
                "last_access": created_at
            })

            cached_score = self.calculate_score(post_id)

            self.redis.hset(key, "cached_score", str(cached_score))
            self.tree.insert(post_id, cached_score)

            return True

        except Post.DoesNotExist:
            return False
    def init_cache(self):

        self.redis.flushall()

        posts = Post.objects.all()

        for post in posts:
            self._get_or_create_metrics(post.pk)


