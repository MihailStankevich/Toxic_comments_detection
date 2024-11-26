from django.db import models
from django.contrib.auth.models import User
# Create your models here.
''' 
class Post(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
   
class User_profile(models.Model):
    user_id = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    ''' 
class DeletedComment(models.Model):
    comment = models.CharField(max_length=400)
    user = models.CharField(max_length=400)
    post = models.CharField(max_length=400)
    deleted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.id} on {self.post.title}"
    