from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Post, Comment, Profile, Follow, Like, Message, LoginToken, TelegramUser, Category, Tag, PostTag, Bookmark, Notification, Story, Repost, GroupChat, GroupMessage, Announcement, StoryView, StoryLike, StoryComment
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
import secrets


# ── Auth (Telegram Deep Link) ────────────────────────

def login_view(request):
    """Login sahifasi - Telegram + password (admin uchun)"""
    if request.user.is_authenticated:
        return redirect('feed')
    error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', '/'))
        error = 'Noto\'g\'ri login yoki parol'
    return render(request, 'login.html', {'error': error})


@csrf_exempt
def auth_init(request):
    """API: yangi token yaratish → deep link uchun"""
    token = secrets.token_urlsafe(32)
    LoginToken.objects.create(token=token)
    deep_link = f'https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}'
    return JsonResponse({'token': token, 'deep_link': deep_link})


@csrf_exempt
def auth_status(request):
    """API: frontend polling — token verified bo'ldimi?"""
    token = request.GET.get('token', '')
    if not token:
        return JsonResponse({'status': 'error', 'message': 'No token'}, status=400)
    try:
        lt = LoginToken.objects.get(token=token)
    except LoginToken.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid token'}, status=404)

    if lt.is_expired():
        return JsonResponse({'status': 'expired'})

    if lt.verified and lt.user:
        login(request, lt.user)
        lt.delete()
        return JsonResponse({'status': 'verified', 'redirect': '/'})

    return JsonResponse({'status': 'pending'})


def register_view(request):
    return redirect('login')


def auto_login(request, token):
    """Token orqali avtomatik login — bot dan kelgan URL"""
    try:
        lt = LoginToken.objects.get(token=token, verified=True)
    except LoginToken.DoesNotExist:
        return redirect('login')
    if lt.is_expired():
        lt.delete()
        return redirect('login')
    if lt.user:
        login(request, lt.user)
        lt.delete()
    return redirect('index')


def logout_view(request):
    logout(request)
    return redirect('index')


# ── Feed & Explore ────────────────────────────────────

@login_required
def feed(request):
    following_ids = request.user.following.values_list('following_id', flat=True)
    posts = Post.objects.filter(author_id__in=following_ids, published=True)
    return render(request, 'feed.html', {'posts': posts})


def index(request):
    posts = Post.objects.filter(published=True)[:6]
    return render(request, 'index.html', {'posts': posts})


def explore(request):
    posts = Post.objects.filter(published=True)
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(body__icontains=q))
    if cat:
        posts = posts.filter(category__slug=cat)
    categories = Category.objects.all()
    return render(request, 'explore.html', {'posts': posts, 'categories': categories, 'q': q, 'current_cat': cat})


# ── Post CRUD ─────────────────────────────────────────

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, published=True)
    Post.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
    post.refresh_from_db()
    comments = post.comments.filter(parent=None)
    liked = request.user.is_authenticated and post.likes.filter(user=request.user).exists()
    bookmarked = request.user.is_authenticated and post.bookmarks.filter(user=request.user).exists()
    reposted = request.user.is_authenticated and post.reposts.filter(user=request.user).exists()
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f'/login/?next=/post/{slug}/')
        body = request.POST.get('body', '').strip()
        parent_id = request.POST.get('parent')
        if body:
            parent = Comment.objects.filter(pk=parent_id).first() if parent_id else None
            Comment.objects.create(post=post, author=request.user, body=body, parent=parent)
        return redirect('post_detail', slug=slug)
    return render(request, 'post_detail.html', {
        'post': post, 'comments': comments, 'liked': liked, 'bookmarked': bookmarked, 'reposted': reposted
    })


@login_required
def post_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        cover = request.FILES.get('cover')
        published = request.POST.get('action') == 'publish'
        scheduled = request.POST.get('scheduled_at', '').strip()
        cat_id = request.POST.get('category')
        category = Category.objects.filter(id=cat_id).first() if cat_id else Category.objects.get_or_create(name="Dunyoga sig'maydi", defaults={'slug': 'dunyoga-sigmaydi'})[0]
        if title and body:
            from django.utils.dateparse import parse_datetime
            scheduled_at = parse_datetime(scheduled) if scheduled else None
            if scheduled_at:
                published = False
            post = Post.objects.create(author=request.user, title=title, body=body, cover=cover, published=published, category=category, scheduled_at=scheduled_at)
            return redirect('post_detail', slug=post.slug) if published else redirect('profile', username=request.user.username)
    categories = Category.objects.all()
    return render(request, 'post_form.html', {'action': 'Create', 'categories': categories})


@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == 'POST':
        post.title = request.POST.get('title', post.title).strip()
        post.body = request.POST.get('body', post.body).strip()
        post.published = request.POST.get('action') == 'publish'
        cat_id = request.POST.get('category')
        post.category = Category.objects.filter(id=cat_id).first() if cat_id else Category.objects.get_or_create(name="Dunyoga sig'maydi", defaults={'slug': 'dunyoga-sigmaydi'})[0]
        if request.FILES.get('cover'):
            post.cover = request.FILES['cover']
        post.save()
        return redirect('post_detail', slug=post.slug)
    categories = Category.objects.all()
    return render(request, 'post_form.html', {'action': 'Edit', 'post': post, 'categories': categories})


@login_required
def post_delete(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == 'POST':
        post.delete()
        return redirect('profile', username=request.user.username)
    return render(request, 'post_confirm_delete.html', {'post': post})


# ── Like ──────────────────────────────────────────────

@login_required
def like_toggle(request, slug):
    post = get_object_or_404(Post, slug=slug)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    else:
        if post.author != request.user:
            Notification.objects.create(user=post.author, actor=request.user, notif_type='like', post=post)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'likes': post.likes_count(), 'liked': created})
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ── Profile & Follow ──────────────────────────────────

def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user, published=True)
    drafts = Post.objects.filter(author=user, published=False) if request.user == user else None
    is_following = (
        request.user.is_authenticated and
        Follow.objects.filter(follower=request.user, following=user).exists()
    )
    from django.utils import timezone
    from datetime import timedelta
    latest_story = Story.objects.filter(author=user, created__gte=timezone.now() - timedelta(hours=24)).first()
    return render(request, 'profile.html', {
        'profile_user': user, 'posts': posts, 'drafts': drafts, 'is_following': is_following,
        'has_story': latest_story is not None, 'latest_story': latest_story,
    })


@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == 'POST':
        new_username = request.POST.get('username', '').strip()
        if new_username and new_username != request.user.username:
            if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                return render(request, 'profile_edit.html', {'profile': profile, 'error': 'Bu username band'})
            request.user.username = new_username
        profile.bio = request.POST.get('bio', '').strip()
        profile.website = request.POST.get('website', '').strip()
        cover_color = request.POST.get('cover_color', '').strip()
        if cover_color:
            profile.cover_color = cover_color
            profile.cover = None
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
        if request.FILES.get('cover'):
            profile.cover = request.FILES['cover']
            profile.cover_color = ''
        profile.save()
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save()
        return redirect('profile', username=request.user.username)
    return render(request, 'profile_edit.html', {'profile': profile})


@login_required
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username)
    if target != request.user:
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if not created:
            follow.delete()
        else:
            Notification.objects.create(user=target, actor=request.user, notif_type='follow')
    return redirect('profile', username=username)


def followers_json(request, username):
    user = get_object_or_404(User, username=username)
    data = [
        {
            'username': f.follower.username,
            'avatar': f.follower.profile.avatar.url if f.follower.profile.avatar else None,
            'is_following': request.user.is_authenticated and
                Follow.objects.filter(follower=request.user, following=f.follower).exists()
        }
        for f in user.followers.select_related('follower', 'follower__profile').all()
    ]
    return JsonResponse({'users': data})


def following_json(request, username):
    user = get_object_or_404(User, username=username)
    data = [
        {
            'username': f.following.username,
            'avatar': f.following.profile.avatar.url if f.following.profile.avatar else None,
            'is_following': request.user.is_authenticated and
                Follow.objects.filter(follower=request.user, following=f.following).exists()
        }
        for f in Follow.objects.filter(follower=user).select_related('following', 'following__profile')
    ]
    return JsonResponse({'users': data})


# ── Direct Messages ───────────────────────────────────

@login_required
def dm_inbox(request):
    contacts = User.objects.filter(
        Q(sent_messages__recipient=request.user) |
        Q(received_messages__sender=request.user)
    ).exclude(pk=request.user.pk).distinct()
    for contact in contacts:
        contact.unread_count = Message.objects.filter(sender=contact, recipient=request.user, read=False).count()
    return render(request, 'dm_inbox.html', {'contacts': contacts})


@login_required
def dm_thread(request, username):
    other = get_object_or_404(User, username=username)
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        if body or image or video:
            Message.objects.create(sender=request.user, recipient=other, body=body, image=image, video=video)
        return redirect('dm_thread', username=username)
    messages_qs = Message.objects.filter(
        Q(sender=request.user, recipient=other) |
        Q(sender=other, recipient=request.user)
    )
    messages_qs.filter(recipient=request.user, read=False).update(read=True)
    return render(request, 'dm_thread.html', {'other': other, 'chat_messages': messages_qs})


@login_required
def msg_edit(request, pk):
    msg = get_object_or_404(Message, pk=pk, sender=request.user)
    if request.method == 'POST':
        msg.body = request.POST.get('body', '').strip()
        msg.edited = True
        msg.save()
    return redirect('dm_thread', username=msg.recipient.username)


@login_required
def msg_delete(request, pk):
    msg = get_object_or_404(Message, pk=pk, sender=request.user)
    username = msg.recipient.username
    msg.delete()
    return redirect('dm_thread', username=username)


def check_username(request):
    username = request.GET.get('username', '').strip()
    if not username or len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Kamida 3 belgi'})
    if not username.isalnum() and '_' not in username:
        return JsonResponse({'available': False, 'message': 'Faqat harf, raqam va _'})
    exists = User.objects.filter(username=username).exclude(pk=request.user.pk if request.user.is_authenticated else -1).exists()
    return JsonResponse({'available': not exists, 'message': 'Band' if exists else 'Mavjud'})


@login_required
def search_users(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'users': []})
    users = User.objects.filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
    ).exclude(pk=request.user.pk)[:10]
    data = [{
        'username': u.username,
        'name': f'{u.first_name} {u.last_name}'.strip(),
        'avatar': u.profile.avatar.url if u.profile.avatar else None,
    } for u in users]
    return JsonResponse({'users': data})


# ── Admin Dashboard ───────────────────────────────────

@login_required
def dashboard(request):
    if not request.user.is_superuser:
        return redirect('index')
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    stats = {
        'users': User.objects.count(),
        'posts': Post.objects.count(),
        'comments': Comment.objects.count(),
        'messages': Message.objects.count(),
        'new_users_week': User.objects.filter(date_joined__gte=week_ago).count(),
        'new_posts_week': Post.objects.filter(created__gte=week_ago).count(),
        'stories': Story.objects.filter(created__gte=now - timedelta(hours=24)).count(),
        'notifications': Notification.objects.count(),
    }
    users = User.objects.annotate(post_count=Count('posts')).order_by('-date_joined')[:20]
    posts = Post.objects.select_related('author').order_by('-created')[:20]

    # Conversations
    from django.db.models import Max
    pairs = Message.objects.values('sender', 'recipient').annotate(last=Max('created')).order_by('-last')
    seen = set()
    conversations = []
    for p in pairs:
        key = tuple(sorted([p['sender'], p['recipient']]))
        if key not in seen:
            seen.add(key)
            u1 = User.objects.get(pk=key[0])
            u2 = User.objects.get(pk=key[1])
            cnt = Message.objects.filter(Q(sender=u1, recipient=u2) | Q(sender=u2, recipient=u1)).count()
            conversations.append({'user1': u1, 'user2': u2, 'count': cnt, 'last': p['last']})
        if len(conversations) >= 10:
            break

    recent_stories = Story.objects.filter(created__gte=now - timedelta(hours=24)).select_related('author')[:10]
    recent_notifs = Notification.objects.select_related('actor', 'user', 'post')[:10]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_user':
            uid = request.POST.get('uid')
            User.objects.filter(pk=uid).exclude(pk=request.user.pk).delete()
        elif action == 'delete_post':
            pid = request.POST.get('pid')
            Post.objects.filter(pk=pid).delete()
        elif action == 'toggle_publish':
            pid = request.POST.get('pid')
            p = Post.objects.filter(pk=pid).first()
            if p:
                p.published = not p.published
                p.save(update_fields=['published'])
        elif action == 'ban_user':
            uid = request.POST.get('uid')
            reason = request.POST.get('reason', '')
            u = User.objects.filter(pk=uid).exclude(pk=request.user.pk).first()
            if u:
                u.profile.is_banned = not u.profile.is_banned
                u.profile.ban_reason = reason if u.profile.is_banned else ''
                u.profile.save()
        elif action == 'announce':
            title = request.POST.get('title', '').strip()
            body_text = request.POST.get('body', '').strip()
            if title and body_text:
                Announcement.objects.create(title=title, body=body_text, author=request.user)
                # Barcha userlarga notification
                for u in User.objects.exclude(pk=request.user.pk):
                    Notification.objects.create(user=u, actor=request.user, notif_type='announce')
        return redirect('dashboard')

    announcements = Announcement.objects.filter(active=True)[:5]
    return render(request, 'dashboard.html', {
        'stats': stats, 'users': users, 'posts': posts,
        'conversations': conversations, 'recent_stories': recent_stories,
        'recent_notifs': recent_notifs, 'announcements': announcements,
    })


@login_required
def admin_chats(request):
    if not request.user.is_superuser:
        return redirect('index')
    from django.db.models import Max, Q as Qq
    # Barcha chat juftliklarni topish
    pairs = Message.objects.values('sender', 'recipient').annotate(last=Max('created')).order_by('-last')
    seen = set()
    conversations = []
    for p in pairs:
        key = tuple(sorted([p['sender'], p['recipient']]))
        if key not in seen:
            seen.add(key)
            u1 = User.objects.get(pk=key[0])
            u2 = User.objects.get(pk=key[1])
            count = Message.objects.filter(
                Q(sender=u1, recipient=u2) | Q(sender=u2, recipient=u1)
            ).count()
            conversations.append({'user1': u1, 'user2': u2, 'count': count, 'last': p['last']})
    
    # Tanlangan chat
    chat_messages = []
    u1_name = request.GET.get('u1')
    u2_name = request.GET.get('u2')
    if u1_name and u2_name:
        user1 = User.objects.filter(username=u1_name).first()
        user2 = User.objects.filter(username=u2_name).first()
        if user1 and user2:
            chat_messages = Message.objects.filter(
                Q(sender=user1, recipient=user2) | Q(sender=user2, recipient=user1)
            )
    
    return render(request, 'admin_chats.html', {
        'conversations': conversations,
        'chat_messages': chat_messages,
        'u1': u1_name,
        'u2': u2_name,
    })


# ── Bookmark, Notifications, Stories, Repost, Tags ────

@login_required
def bookmark_toggle(request, slug):
    post = get_object_or_404(Post, slug=slug)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bookmark.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'bookmarked': created})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def bookmarks_list(request):
    posts = Post.objects.filter(bookmarks__user=request.user)
    return render(request, 'bookmarks.html', {'posts': posts})


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created')
    notifications.filter(read=False).update(read=True)
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
def story_create(request):
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        image = request.FILES.get('image')
        if body or image:
            Story.objects.create(author=request.user, body=body, image=image)
            return redirect('stories_feed')
    return render(request, 'story_form.html')


@login_required
def stories_feed(request):
    since = timezone.now() - timedelta(hours=24)
    # Muddati tugaganlarni o'chirish
    Story.objects.filter(created__lt=since).delete()
    stories = Story.objects.all().order_by('-created')
    return render(request, 'stories.html', {'stories': stories})


@login_required
def repost_toggle(request, slug):
    post = get_object_or_404(Post, slug=slug)
    repost, created = Repost.objects.get_or_create(user=request.user, post=post)
    if not created:
        repost.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'reposted': created})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def tag_posts(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    posts = Post.objects.filter(tags__tag=tag, published=True)
    return render(request, 'tag_posts.html', {'tag': tag, 'posts': posts})


@login_required
def story_detail(request, pk):
    from blog.models import StoryView, StoryLike, StoryComment
    story = get_object_or_404(Story, pk=pk)
    # Ko'rganini belgilash
    StoryView.objects.get_or_create(story=story, user=request.user)
    # Comment
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'comment':
            body = request.POST.get('body', '').strip()
            if body:
                StoryComment.objects.create(story=story, author=request.user, body=body)
        elif action == 'like':
            like, created = StoryLike.objects.get_or_create(story=story, user=request.user)
            if not created:
                like.delete()
        return redirect('story_detail', pk=pk)
    liked = StoryLike.objects.filter(story=story, user=request.user).exists()
    viewers = story.views.select_related('user')
    comments = story.comments.select_related('author')
    return render(request, 'story_detail.html', {
        'story': story, 'liked': liked, 'viewers': viewers, 'comments': comments,
    })
