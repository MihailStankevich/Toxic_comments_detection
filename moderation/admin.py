from django.contrib import admin
from .models import DeletedComment, Owner

class OwnerAdmin(admin.ModelAdmin):
    list_display = ('username', 'channel_id')
class DeletedCommentAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'post','channel_id',"owner", 'deleted_at')  # Display relevant fields
    search_fields = ('comment','user')  # Add search capability for the comment text

admin.site.register(DeletedComment, DeletedCommentAdmin)
admin.site.register(Owner, OwnerAdmin)
