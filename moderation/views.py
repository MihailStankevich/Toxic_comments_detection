from django.shortcuts import render

from .models import DeletedComment

def admin_deleted_comments(request, channel_id):
    deleted_comments = DeletedComment.objects.filter(channel_id=channel_id)
    return render(request, 'moderation/deleted_comments.html', {'deleted_comments': deleted_comments})