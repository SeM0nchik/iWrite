import redis
from math import exp, log
from .splaytree import SplayTree
from time import time


class RecommendationService:

    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.tree = SplayTree()

    def calculate_score(self, post_id) ->float:
        metrics = self.redis.hgetall(f"post:{post_id}:metrics")
        views = int(metrics.get("views", 0))
        likes = int(metrics.get("likes", 0))
        last_access = float(metrics.get("last_access", 0))
        created_at = float(metrics.get("created_at", time()))

        activity = log(1 + views) * 0.4 + log(1 + likes) * 0.6

        recency = exp(-0.001 * (time() - last_access))

        age = time() - created_at

        freshness = exp(-0.001 * age)


        return activity * 0.5 + freshness * 0.4 + recency * 0.1

    def on_view(self, post_id : int):

        self.redis.hincrby(f"post:{post_id}:metrics", "views", 1)
        self.redis.hset(f"post:{post_id}:metrics", "last_access", str(time()))

        old_score = self.redis.hget(f"post:{post_id}:metrics", "cached_score")
        if old_score:
            self.tree.delete(post_id, float(old_score))

        new_score = self.calculate_score(post_id)
        self.redis.hset(f"post:{post_id}:metrics", "cached_score", str(new_score))
        self.tree.insert(post_id, new_score)

    def on_like(self, post_id : int):
        self.redis.hincrby(f"post:{post_id}:metrics", "likes", 1)
        self.redis.hset(f"post:{post_id}:metrics", "last_access", str(time()))

        old_score = self.redis.hget(f"post:{post_id}:metrics", "cached_score")
        if old_score:
            self.tree.delete(post_id, float(old_score))

        new_score = self.calculate_score(post_id)
        self.redis.hset(f"post:{post_id}:metrics", "cached_score", str(new_score))
        self.tree.insert(post_id, new_score)


    def on_new_post(self, post_id: int):
        self.redis.hset(f"post:{post_id}:metrics", mapping={
            "created_at": time(),
            "views": 0,
            "likes": 0,
            "last_access": time()
        })
        score = self.calculate_score(post_id)
        self.redis.hset(f"post:{post_id}:metrics", "cached_score", str(score))
        self.tree.insert(post_id, score)


    def get_recommendations(self, limit : int = 5):
        return self.tree.get_top_posts(limit)

