from tabnanny import verbose

from ckeditor.fields import RichTextField
from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from mptt.models import MPTTModel, TreeForeignKey
from django.urls import reverse
from apps.services.utils import unique_slugify
from taggit.managers import TaggableManager


class PostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('author', 'category').filter(status='published')

class Post(models.Model):
    """
    Модель для нашего блога
    """

    objects = models.Manager()
    custom = PostManager()

    STATUS_OPTIONS = (
    ('published', 'Опубликовано'),
    ('draft', 'Черновик'),
    )


    title = models.CharField(verbose_name='Название записи', max_length=255)
    slug = models.SlugField(verbose_name='URL', max_length=255,  blank=True)
    description = RichTextField(config_name = 'awesome_ckeditor',verbose_name='Краткое описание', max_length=500)
    text = RichTextField(config_name = 'awesome_ckeditor',verbose_name='Полный текст записи')
    thumbnail = models.ImageField(
        verbose_name='Изображение записи',
        blank=True,
        upload_to='images/thumbnails/%Y/%m/%d',
        validators = [FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    status = models.CharField(choices=STATUS_OPTIONS, default='published', verbose_name='Статус записи', max_length=10)
    create = models.DateTimeField(auto_now_add=True, verbose_name='Время добавления')
    update = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    author = models.ForeignKey(to=User, verbose_name= 'Автор', on_delete=models.SET_DEFAULT,related_name='author_posts', default=1)
    updater = models.ForeignKey(to=User, verbose_name='Обновил', on_delete=models.SET_NULL, null=True, related_name='updater_posts', blank=True)
    category = TreeForeignKey('Category', on_delete=models.PROTECT, related_name='posts', verbose_name='Категории' )
    fixed = models.BooleanField(verbose_name='Прикреплено', default=False)


    tags = TaggableManager()

    class Meta:
        db_table = 'blog_post'
        ordering = ['-fixed', '-create']
        indexes = [
            models.Index(fields=['-fixed', '-create', 'status']),
        ]
        verbose_name = 'Статья'
        verbose_name_plural='Статьи'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        self.slug = unique_slugify(self, self.title, self.slug)
        super().save(*args, **kwargs)

    def get_positive_count(self):
        return sum([rating.value if rating.value == 1 else 0 for rating in self.ratings.all()])

    def get_negative_count(self):
        return sum([-rating.value if rating.value == -1 else 0 for rating in self.ratings.all()])


class Category(MPTTModel):
    title = models.CharField(max_length=255, verbose_name='Название категории')
    slug = models.SlugField(max_length=255, verbose_name='URL категории', blank=True)
    description =  models.TextField(verbose_name='Описание категории', max_length=300)

    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        related_name='children',
        verbose_name='Родительская категория'
    )

    class MTTPMeta:

        order_insertion_by = ('title', )

    class Meta:
        verbose_name = 'Категории'
        verbose_name_plural = 'Категории'

        db_table = 'app_categories'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_by_category', kwargs={'slug': self.slug})

class Comment(MPTTModel):
    STATUS_OPTIONS = (
        ('published', 'Опубликовано'),
        ('draft', 'Черновик'),
    )

    post = models.ForeignKey(to=Post, related_name='comments', on_delete=models.CASCADE, verbose_name ='Запись')
    author = models.ForeignKey(User, verbose_name='Автор комментария', on_delete=models.CASCADE,
                               related_name='comments_author')
    content = models.TextField(verbose_name='Текст комментария', max_length=3000)
    time_create = models.DateTimeField(verbose_name='Время добавления', auto_now_add=True)
    time_update = models.DateTimeField(verbose_name='Время обновления', auto_now=True)
    status = models.CharField(choices=STATUS_OPTIONS, default='published', verbose_name='Статус комментария',
                              max_length=10)
    parent = TreeForeignKey('self', verbose_name='Родительский комментарий', null=True, blank=True,
                            related_name='children', on_delete=models.CASCADE)
    class MTTPMeta:
        order_insertion_by = ('-time_create')

    class Meta:
        ordering = ['-time_create']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
    def __str__(self):
        return f'{self.author}: {self.content}'


class Rating(models.Model):
    post = models.ForeignKey(to=Post, related_name='ratings', on_delete=models.CASCADE, verbose_name='Запись')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, verbose_name='Пользователь', blank=True, null=True)
    value = models.IntegerField(verbose_name='Значение', choices=[(1, "Нравится"), (-1, "Не нравится")])
    time_create = models.DateTimeField(verbose_name='Время добавления', auto_now_add=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP Адрес')

    class Meta:
        unique_together = ('post', 'ip_address')
        ordering = ('-time_create', )
        indexes = [models.Index(fields=['-time_create', 'value'])]
        verbose_name = 'Рейтинг'
        verbose_name_plural = 'Рейтинги'

    def __str__(self):
        return self.post.title