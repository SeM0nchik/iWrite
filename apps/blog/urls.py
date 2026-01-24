from django.urls import path
from .views import *


urlpatterns = [
    path('', PostListView.as_view(), name='home'),
    path('post/create/', PostCreateView.as_view(), name='post_create'),
    path('post/<slug:slug>/update/', PostUpdateView.as_view(), name='post_update'),
    path('post/<slug:slug>', PostDetailView.as_view(), name='post_detail'),
    path('post/<int:pk>/comments/create/', CommentCreationView.as_view(), name='comment_create_view'),
    path('post/tags/<str:tag>/', PostByTagListView.as_view(), name='post_by_tags'),
    path('category/<str:slug>', PostFromCategory.as_view(), name='post_by_category'),
    path('rating/', RatingCreateView.as_view(), name='rating'),
    path('post/my/', PostByUserListView.as_view(), name='my_posts'),

]