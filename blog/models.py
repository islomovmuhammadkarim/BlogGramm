from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover = models.ImageField(upload_to='profile_covers/', blank=True, null=True)
    cover_color = models.CharField(max_length=7, blank=True)
    bio = models.TextField(blank=True, max_length=300)
    website = models.URLField(blank=True)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.user.username

    def followers_count(self):
        return self.user.followers.count()

    def following_count(self):
        return Follow.objects.filter(follower=self.user).count()

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f'{self.follower} → {self.following}'


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    name_uz = models.CharField(max_length=50, blank=True)
    name_ru = models.CharField(max_length=50, blank=True)
    name_en = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=250)
    title_uz = models.CharField(max_length=250, blank=True)
    title_ru = models.CharField(max_length=250, blank=True)
    title_en = models.CharField(max_length=250, blank=True)
    slug = models.SlugField(max_length=250, unique=True)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    body = models.TextField()
    body_uz = models.TextField(blank=True)
    body_ru = models.TextField(blank=True)
    body_en = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=True)
    views_count = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)
        # Auto-translate after save
        if not self.title_uz or not self.title_ru or not self.title_en:
            from threading import Thread
            Thread(target=_translate_post, args=(self.pk,), daemon=True).start()

    def likes_count(self):
        return self.likes.count()


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return f'{self.author} → {self.post}'


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to='dm_images/', blank=True, null=True)
    video = models.FileField(upload_to='dm_videos/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return f'{self.sender} → {self.recipient}'


class TelegramUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram')
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    username = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.user.username} (tg:{self.telegram_id})'


class LoginToken(models.Model):
    token = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    verified = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created).total_seconds() > 300


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='posts')

    class Meta:
        unique_together = ('post', 'tag')


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class Notification(models.Model):
    TYPES = [('like', 'Like'), ('comment', 'Comment'), ('follow', 'Follow'), ('repost', 'Repost'), ('announce', 'Announcement')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actions')
    notif_type = models.CharField(max_length=10, choices=TYPES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']


class Story(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to='stories/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def is_active(self):
        from django.utils import timezone
        return (timezone.now() - self.created).total_seconds() < 86400


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')


class StoryLike(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')


class StoryComment(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']


class Repost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reposts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reposts')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class GroupChat(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='group_chats')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to='group_images/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created']


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']


def _translate_post(post_id):
    """Background: post tarjimasini to'ldirish"""
    import time
    time.sleep(0.5)
    from deep_translator import GoogleTranslator
    try:
        post = Post.objects.get(pk=post_id)
        langs = ['uz', 'ru', 'en']
        for lang in langs:
            title_field = f'title_{lang}'
            body_field = f'body_{lang}'
            if not getattr(post, title_field):
                try:
                    setattr(post, title_field, GoogleTranslator(source='auto', target=lang).translate(post.title) or post.title)
                except:
                    setattr(post, title_field, post.title)
            if not getattr(post, body_field):
                try:
                    text = post.body[:4500]
                    setattr(post, body_field, GoogleTranslator(source='auto', target=lang).translate(text) or post.body)
                except:
                    setattr(post, body_field, post.body)
        Post.objects.filter(pk=post_id).update(
            title_uz=post.title_uz, title_ru=post.title_ru, title_en=post.title_en,
            body_uz=post.body_uz, body_ru=post.body_ru, body_en=post.body_en,
        )
    except Exception as e:
        print(f'Translation error for post {post_id}: {e}')
