from django.shortcuts import get_object_or_404, render

from .models import Post


def post_list(request):
    posts = Post.published.all()
    return render(request, template_name='blog/post/list.html',
                  context={'posts': posts})


def post_detail(request, id):
    post = get_object_or_404(
        klass=Post,
        id=id,
        status=Post.Status.PUBLISHED
    )
    return render(request, 'blog/blog/details.html', {'post': post})
