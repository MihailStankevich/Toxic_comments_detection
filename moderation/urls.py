from django.urls import path
from .views import admin_deleted_comments, home, user_login, register, user_logout

urlpatterns = [
    path('', home, name='home'),
    path('deleted_comments/<str:channel_id>/', admin_deleted_comments, name='admin_deleted_comments'),
    path('register', register, name='register'),
    path('login', user_login, name='login'),
    path('logout', user_logout, name='logout'),
]