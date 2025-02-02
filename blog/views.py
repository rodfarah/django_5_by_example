from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from taggit.models import Tag

from .forms import CommentForm, EmailPostForm, SearchForm
from .models import Post


# Post_list is deprecated because of its class based view down bellow
def post_list(request, tag_slug=None):
    # 'published' is our new Manager, set up in model
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(
            klass=Tag,
            slug=tag_slug,
        )
        post_list = post_list.filter(tags__in=[tag])
    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get("page", 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer, get the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range, get last page of results
        posts = paginator.page(paginator.num_pages)
    return render(
        request,
        template_name="blog/post/list.html",
        context={
            "posts": posts,
            "tag": tag,
        },
    )


# bellow, the 'post' parameter is, in fact, a slug


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    comments = post.comments.filter(active=True)
    form = CommentForm()

    # List of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(
        id=post.id
    )
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-publish"
    )[:4]

    return render(
        request,
        "blog/post/detail.html",
        {
            "post": post,
            "comments": comments,
            "form": form,
            "similar_posts": similar_posts,
        },
    )


class PostListView(ListView):
    """
    Alternative post list view
    """

    queryset = Post.published.all()
    context_object_name = "posts"
    paginate_by = 3
    template_name = "blog/post/list.html"


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(
        klass=Post, id=post_id, status=Post.Status.PUBLISHED
    )
    sent = False

    if request.method == "POST":
        # form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # form fields pass validation
            cd = form.cleaned_data
            # send email
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = (
                f"{cd['name']} ({cd['email']}) "
                f"reccomends you read {post.title}"
            )
            message = (
                f"Read {post.title} at {post_url}\n\n"
                f"{cd['name']}'s comments: {cd['comments']}"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[cd["to"]],
            )
            sent = True
    else:
        form = EmailPostForm()
    return render(
        request=request,
        template_name="blog/post/share.html",
        context={"post": post, "form": form, "sent": sent},
    )


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(
        klass=Post, id=post_id, status=Post.Status.PUBLISHED
    )
    comment = None
    # A comment was posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # create a comment without saving it to the database
        comment = form.save(commit=False)
        # assign the post to the comment
        comment.post = post
        # save the comment to the database
        comment.save()
    return render(
        request=request,
        template_name="blog/post/comment.html",
        context={
            "comment": comment,
            "post": post,
            "form": form,
        },
    )


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            # # SearchVector allows me to search for two fields combined
            # # Weigh "A" boosts vector when ordering results by relevancy.
            # search_vector = SearchVector("title", weight="A") + SearchVector(
            #     "body", weight="B"
            # )
            # # SearchQuery deletes unuseful words of query, like 'of', 'the'
            # search_query = SearchQuery(query)
            # # annotate adds an extra temporary field to the search query \
            # # without saving it into db.
            # # SearchRank ranking function that orders results based on how \
            # # often the query terms appear and how close together they are
            # results = (
            #     Post.published.annotate(
            #         search=search_vector,
            #         rank=SearchRank(search_vector, search_query),
            #     )
            #     .filter(rank__gte=0.3)
            #     .order_by("-rank")
            # )

            # Trigram considers similar words on searching words. ie: \
            # iender vs fender
            results = (
                Post.published.annotate(
                    similarity=TrigramSimilarity("title", query),
                )
                .filter(similarity__gt=0.1)
                .order_by("-similarity")
            )
    return render(
        request=request,
        template_name="blog/post/search.html",
        context={"form": form, "query": query, "results": results},
    )
