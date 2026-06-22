def lang_context(request):
    ctx = {'lang': request.COOKIES.get('lang', 'en')}
    if request.user.is_authenticated:
        from blog.models import Notification, Announcement
        ctx['unread_notifs'] = Notification.objects.filter(user=request.user, read=False).count()
    from blog.models import Announcement
    ctx['active_announcement'] = Announcement.objects.filter(active=True).first()
    return ctx
