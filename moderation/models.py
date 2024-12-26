from django.db import models
from django.contrib.auth.models import AbstractUser,Group, Permission
from django.utils import timezone
from datetime import timedelta
# Create your models here.

class Owner(AbstractUser):
    username = models.EmailField(("email address"), unique=True)
    channel_id = models.CharField(max_length=100, unique=True)
    USERNAME_FIELD = "username"

    groups = models.ManyToManyField(
        Group,
        related_name='owner_set', 
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions '
                  'granted to each of their groups.',
        verbose_name='groups',
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='owner_set', 
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    def __str__(self):
        return self.username
class DeletedComment(models.Model):
    comment = models.CharField(max_length=400)
    user = models.CharField(max_length=400)
    post = models.CharField(max_length=400)
    channel_id = models.CharField(max_length=100)
    deleted_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='deleted_comments', null=True)
    detected_by = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f"Comment by {self.user} on {self.post}"
    
class BlockedUser(models.Model):
    username = models.CharField(max_length=200)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='blocked_users')
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    comment = models.ForeignKey(DeletedComment, on_delete=models.CASCADE, null=True, blank=True)
    is_permanent = models.BooleanField(default=False)

    def is_active(self):
        if self.is_permanent:
            return True
        return timezone.now() < self.expires_at
    
    def __str__(self):
        return f'{self.username}'
