from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchHeadline
from django.utils.html import strip_tags
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from ..recommendations.redis_service import RecommendationService
from django.db.models import Case, When, IntegerField

from .models import Post, Category, Rating
from .forms import PostCreteForm, PostUpdateForm, CommentCreateForm
from ..services.mixins import AuthorRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.formats import date_format
from django.utils.timezone import localtime
from taggit.models import Tag
from django.shortcuts import render

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 3
    queryset = Post.custom.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Главная страница'
        page = context['page_obj']
        context['paginator_range'] = page.paginator.get_elided_page_range(page.number)
        return context

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name='post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.object.title
        context['form'] = CommentCreateForm
        RecommendationService().on_view(self.object.pk)
        return context

class PostFromCategory(ListView):
    template_name='blog/post_list.html'
    context_object_name='posts'
    category=None
    paginate_by=1

    def get_queryset(self):
        self.category = Category.objects.get(slug=self.kwargs['slug'])
        queryset = Post.objects.filter(category=self.category)

        if not queryset:
            sub_cat = Category.objects.filter(parent=self.category)
            queryset = Post.objects.filter(category__in=sub_cat)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Записи из категории: {self.category.title}'
        page = context['page_obj']
        context['paginator_range'] = page.paginator.get_elided_page_range(page.number)
        return context

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/post_create.html'
    form_class = PostCreteForm
    login_url = 'home'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавление статей на сайт'
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class PostUpdateView(AuthorRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Post
    template_name = 'blog/post_update.html'
    context_object_name = 'post'
    form_class = PostUpdateForm
    login_url = 'home'
    success_message = 'Запись была успешно обновлена!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title']  =  f"Обновление статьи {self.object.title}"
        return context

    def form_valid(self, form):
        return super().form_valid(form)

class CommentCreationView(LoginRequiredMixin, CreateView):
    form_class = CommentCreateForm


    def is_ajax(self):
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({'error' : form.errors}, status=400)
        return super().form_invalid(form)

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.post_id = self.kwargs.get('pk')
        comment.author = self.request.user
        comment.parent_id = form.cleaned_data.get('parent')
        comment.save()

        if self.is_ajax():
            return JsonResponse({
                'is_child': comment.is_child_node(),
                'id': comment.id,
                'author': comment.author.username,
                'parent_id': comment.parent_id,
                'time_create': date_format(
                    localtime(comment.time_create),
                    format='DATETIME_FORMAT',
                    use_l10n=True,
                ),
                'avatar': comment.author.profile.avatar.url,
                'content': comment.content,
                'get_absolute_url': comment.author.profile.get_absolute_url()
            }, status=200)

        return redirect(comment.post.get_absolute_url())

    def handle_no_permission(self):
        return JsonResponse({'error' : 'Необходимо авторизоваться для добавления комментариев'}, status=400)


class PostByTagListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by=10
    tag = None

    def get_queryset(self):
        self.tag = Tag.objects.get(slug=self.kwargs['tag'])
        queryset = Post.objects.filter(tags__slug=self.tag.slug)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Статьи по тегу: {self.tag.name}'
        return context

class PostByUserListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by=10
    author = None

    def get_queryset(self):
        self.author = self.request.user
        queryset = Post.objects.filter(author=self.author)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Статьи пользователя {self.author.username}'
        return context

class RatingCreateView(View):
    model = Rating

    def post(self, request, *args, **kwargs):
        post_id = request.POST.get('post_id')
        value_str = request.POST.get('value', '0')
        value = 0 if value_str == 'NaN' else int(value_str)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        user = request.user if request.user.is_authenticated else None

        rating, created = Rating.objects.get_or_create(
            post_id=post_id,
            ip_address=ip,
            defaults = {'value' : value, 'user' : user}
        )

        RecommendationService().on_like(post_id)

        if not created:
            if rating.value == value:
                rating.delete()
            else:
                rating.value = value
                rating.user = user
                rating.save()
        return JsonResponse({'positive-count': rating.post.get_positive_count(),
                             'negative-count': rating.post.get_negative_count(), })

class RecommendationListView(ListView):
    model = Post
    template_name = 'blog/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        service = RecommendationService()
        top_ids = service.get_recommendations(10)

        ordering = Case(
            *[When(id=pk, then=pos) for pos, pk in enumerate(top_ids)],
            default=len(top_ids),
            output_field=IntegerField()
        )

        posts = Post.objects.filter(id__in=top_ids).order_by(ordering)
        return posts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Сейчас в тренде'
        page = context['page_obj']
        context['paginator_range'] = page.paginator.get_elided_page_range(page.number)
        return context

class BlogSearchView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by=10

    def get_queryset(self,):
        query = self.request.GET.get('query').strip()
        return self.get_search_results(query)

    def get_search_results(self, query):
        if not query:
            return Post.objects.none()

        vector = SearchVector('title', weight='A') + \
            SearchVector('description', weight='B')

        search_query = SearchQuery(query)
        return Post.objects.annotate(
            search=vector,
            rank=SearchRank(vector, search_query),
            headline=SearchHeadline(
                'title',
                search_query,
                max_words=30,
                start_sel='<mark>',
                stop_sel='</mark>'
            )
        ).filter(
            search=search_query,
            rank__gt=0.2
        ).order_by('-rank')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            query = self.request.GET.get('query').strip()

            posts = self.get_search_results(query)

            results = [{
                'id' : post.id,
                'title' : post.title,
                'headline' : strip_tags(getattr(post, 'headline', post.description[:100])[:150]),
                'url' : post.get_absolute_url(),
                'rank' : float(getattr(post, 'rank', 0))
            } for post in posts]

            return JsonResponse({'results': results, 'count' : len(results)})
        return super().render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('query')

        context['query'] = query

        return context


def tr_handler404(request, exception):
    return render(request=request, template_name = 'errors/error_page.html', status=404,context = {
        'title' : 'Страница не найдена: 404',
        'error_message' : 'К сожалению такая страница была не найдена, или перемещена',
    } )

def tr_handler400(request, exception):
    return render(request=request, template_name='errors/error_page.html', status=400, context = {
        'title' : 'Ошибка сервера: 500',
        'error_message' : 'Внутренняя ошибка сайта, вернитесь на главную страницу, отчет об ошибке мы направим администрации сайта',
    })

def tr_handler403(request, exception):
    return render(request=request, template_name='errors/error_page.html', status=403, context = {
        'title' : 'Ошибка доступа 403',
        'error_message' : 'Доступ к этой странице ограничен',
    })

