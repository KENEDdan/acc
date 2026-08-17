from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()[:30]
    data = [
        {
            "id": n.id,
            "message": n.message,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%b %d, %H:%M"),
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data, "unread_count": request.user.notifications.filter(is_read=False).count()})


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    if notification.link:
        return redirect(notification.link)
    return redirect('core:home')