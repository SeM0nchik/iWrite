from datetime import datetime

import redis
from math import exp, log
from .splaytree import SplayTree
from time import time
from django.conf import settings
from ..blog.models import Post

_global_redis = None
_global_tree = None

class RecommendationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            global _global_redis, _global_tree
            if _global_redis is None:
                _global_redis = redis.Redis(
                    host=getattr(settings, 'REDIS_HOST', 'redis'),
                    port=getattr(settings, 'REDIS_PORT', 6379),
                    db=getattr(settings, 'REDIS_DB', 0),
                    decode_responses=True
                )
                _global_tree = SplayTree()

                keys = _global_redis.keys("post:*:metrics")
                for key in keys:
                    pid = int(key.split(':')[1])
                    score = int(_global_redis.hget(key, "cached_score") or 0)
                    _global_tree.insert(pid, score)

            cls._instance.redis = _global_redis
            cls._instance.tree = _global_tree
        return cls._instance

    def __init__(self):
        pass

    def ensure_tree_health(self):
        if not self.tree.root and self.redis.keys("post:*:metrics"):
            for key in self.redis.keys("post:*:metrics"):
                post_id = int(key.split(':')[1])
                score = int(self.redis.hget(key, "cached_score") or 0)
                self.tree.insert(post_id, score)

    def calculate_score_from_metrics(self, metrics) ->int:

        views = int(metrics.get("views", 0))
        likes = int(metrics.get("likes", 0))

        created_at = float(metrics.get("created_at", datetime.now().timestamp()))
        last_access = float(metrics.get("last_access", created_at))

        activity = log(1 + views) * 0.4 + log(1 + likes) * 0.6

        recency = exp(-(time() - last_access) / 864000)

        age = time() - created_at

        freshness = exp(-age / 864000)

        return int((activity * 0.5 + freshness * 0.4 + recency * 0.1) * 10_000)

    def calculate_score(self, post_id: int) -> int:
        key = f"post:{post_id}:metrics"
        metrics = self.redis.hgetall(key)
        return self.calculate_score_from_metrics(metrics)
    def on_view(self, post_id : int):
        pipe = self.redis.pipeline()

        pipe.hincrby(f"post:{post_id}:metrics", "views", 1)
        pipe.hset(f"post:{post_id}:metrics", mapping={"last_access" : datetime.now().timestamp()})
        pipe.sadd("post:dirty", post_id)

        pipe.execute()


    def on_like(self, post_id : int):

        pipe = self.redis.pipeline()
        pipe.hincrby(f"post:{post_id}:metrics", "likes", 1)
        pipe.hset(f"post:{post_id}:metrics", "last_access", datetime.now().timestamp())
        pipe.sadd("posts:dirty", post_id)
        pipe.execute()


    def on_new_post(self, post_id: int):
        self.redis.hset(f"post:{post_id}:metrics", mapping={
            "created_at": datetime.now().timestamp(),
            "views": 0,
            "likes": 0,
            "last_access": datetime.now().timestamp(),
        })
        self.redis.sadd("posts:dirty", post_id)

    def recalculate_score(self, post_id: int):
        key = f"post:{post_id}:metrics"

        metrics = self.redis.hgetall(key)

        old_score = metrics.get("cached_score")
        new_score = self.calculate_score_from_metrics(metrics)

        if old_score:
            self.tree.delete(post_id, int(old_score))

        self.tree.insert(post_id, new_score)
        self.redis.hset(key, "cached_score", new_score)

    def rebuild_tree_from_redis(self):
        self.tree.clear()

        redis_keys = self.redis.keys("post:*:metrics")

        for key in redis_keys:
            post_id = int(key.split(':')[1])
            score = float(self.redis.hget(key, "cached_score") or 0)
            self.tree.insert(post_id, score)


    def recompute_batch(self, batch_size=100):
        post_ids = self.redis.spop("posts:dirty", batch_size)

        if not post_ids:

            post_ids = [pid.split(':')[1] for pid in self.redis.keys("post:*:metrics")]

        count = 0
        for post_id in post_ids:
            self.recalculate_score(int(post_id))
            count += 1


        self.rebuild_tree_from_redis()

    def get_recommendations(self, limit : int = 5):
        return self.tree.get_top_posts(limit)

    def _get_or_create_metrics(self, post_id):
        key = f"post:{post_id}:metrics"

        if self.redis.exists(key):
            cached_score = int(self.redis.hget(key, "cached_score"))
            cached_score = int(cached_score) if cached_score else 0
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


