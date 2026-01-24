from django.contrib import admin
from django_mptt_admin.admin import DjangoMpttAdmin


from apps.blog.models import Post, Category, Comment, Rating

@admin.register(Category)
class CategoryAdmin(DjangoMpttAdmin):

    prepopulated_fields = {"slug": ("title",)}

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Comment)
class CommentAdmin(DjangoMpttAdmin):
    pass

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    pass

