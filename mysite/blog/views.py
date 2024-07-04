from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView

from .forms import EmailPostForm
from .models import Post


# Post_list is deprecated because of its class based view down bellow
def post_list(request):
    # 'published' is our new Manager, set up in model
    post_list = Post.published.all()
    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer, get the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range, get last page of results
        posts = paginator.page(paginator.num_pages)
    return render(request, template_name='blog/post/list.html',
                  context={'posts': posts})

# bellow, the 'post' parameter is, in fact, a slug


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day
    )
    return render(request, 'blog/post/detail.html', {'post': post})


class PostListView(ListView):
    """
    Alternative post list view
    """
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(
        klass=Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )

    if request.method == "POST":
        # form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # form fields pass validation
            cd = form.cleaned_data
            # send email ...
    else:
        form = EmailPostForm()
    return render(
        request=request,
        template_name='blog/post/share',
        context={
            'post': post,
            'form': form
        }
    )
