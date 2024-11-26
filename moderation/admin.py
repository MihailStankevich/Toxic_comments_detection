from django.contrib import admin
from .models import DeletedComment

class DeletedCommentAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'post', 'deleted_at')  # Display relevant fields
    search_fields = ('comment',)  # Add search capability for the comment text

admin.site.register(DeletedComment, DeletedCommentAdmin)
