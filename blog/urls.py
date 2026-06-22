from django.urls import path
from . import views

urlpatterns = [
    # auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('auto-login/<str:token>/', views.auto_login, name='auto_login'),

    # auth API (deep link flow)
    path('api/auth/init/', views.auth_init, name='auth_init'),
    path('api/auth/status/', views.auth_status, name='auth_status'),
    path('api/check-username/', views.check_username, name='check_username'),
    path('api/search-users/', views.search_users, name='search_users'),

    # main pages
    path('', views.index, name='index'),
    path('explore/', views.explore, name='explore'),
    path('feed/', views.feed, name='feed'),

    # posts
    path('post/new/', views.post_create, name='post_create'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('post/<slug:slug>/edit/', views.post_edit, name='post_edit'),
    path('post/<slug:slug>/delete/', views.post_delete, name='post_delete'),
    path('post/<slug:slug>/like/', views.like_toggle, name='like_toggle'),

    # profile
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('u/<str:username>/', views.profile, name='profile'),
    path('u/<str:username>/follow/', views.follow_toggle, name='follow_toggle'),
    path('u/<str:username>/followers.json', views.followers_json, name='followers_json'),
    path('u/<str:username>/following.json', views.following_json, name='following_json'),

    # DM
    path('dm/', views.dm_inbox, name='dm_inbox'),
    path('dm/<str:username>/', views.dm_thread, name='dm_thread'),
    path('dm/msg/<int:pk>/edit/', views.msg_edit, name='msg_edit'),
    path('dm/msg/<int:pk>/delete/', views.msg_delete, name='msg_delete'),

    # Admin
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/chats/', views.admin_chats, name='admin_chats'),

    # Bookmarks, Notifications, Stories, Repost, Tags
    path('post/<slug:slug>/bookmark/', views.bookmark_toggle, name='bookmark_toggle'),
    path('bookmarks/', views.bookmarks_list, name='bookmarks'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('story/new/', views.story_create, name='story_create'),
    path('stories/', views.stories_feed, name='stories_feed'),
    path('story/<int:pk>/', views.story_detail, name='story_detail'),
    path('post/<slug:slug>/repost/', views.repost_toggle, name='repost_toggle'),
    path('tag/<slug:slug>/', views.tag_posts, name='tag_posts'),
]
