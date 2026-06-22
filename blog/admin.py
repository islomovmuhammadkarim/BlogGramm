from django.contrib import admin
from .models import Post, Comment, Profile, Follow, Like, Message


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'published', 'created']
    list_filter = ['published', 'created']
    search_fields = ['title', 'body']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['published']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'created']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio']


admin.site.register(Follow)
admin.site.register(Like)
admin.site.register(Message)
