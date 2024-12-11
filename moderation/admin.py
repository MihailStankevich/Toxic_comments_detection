from django.contrib import admin
from .models import DeletedComment, Owner, BlockedUser

class OwnerAdmin(admin.ModelAdmin):
    list_display = ('username', 'channel_id')
class DeletedCommentAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'post','channel_id',"owner", 'deleted_at')  # Display relevant fields
    search_fields = ('comment','user')  # Add search capability for the comment text
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'owner', 'blocked_at', 'expires_at', 'is_active')
    list_filter = ('owner','comment', 'blocked_at', 'expires_at')
    search_fields = ('user',)

    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True 
admin.site.register(DeletedComment, DeletedCommentAdmin)
admin.site.register(Owner, OwnerAdmin)
admin.site.register(BlockedUser , BlockedUserAdmin)
