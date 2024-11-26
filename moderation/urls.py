from django.urls import path
from .views import admin_deleted_comments 

urlpatterns = [
    path('deleted_comments/<str:channel_id>/', admin_deleted_comments, name='admin_deleted_comments'),
]