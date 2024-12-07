from django.shortcuts import render, redirect
from .models import DeletedComment, BlockedUser 

from django.contrib import messages
from .forms import OwnerRegistrationForm

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from django.core.paginator import Paginator

@login_required
def admin_deleted_comments(request, channel_id):
    deleted_comments = DeletedComment.objects.filter(channel_id=channel_id).order_by('-deleted_at')
    search_query = request.GET.get('search', '')
    if search_query:
        deleted_comments = deleted_comments.filter(post__icontains=search_query)

    paginator = Paginator(deleted_comments, 5)  # Show 5 comments per page
    page_number = request.GET.get('page', 1)  # Get the current page number
    comments_page = paginator.get_page(page_number) 

    blocked_users = BlockedUser .objects.filter(owner=request.user, expires_at__gt=timezone.now()).values_list('username', flat=True)

    return render(request, 'moderation/deleted_comments.html', {'deleted_comments': comments_page, "channel_id": channel_id, "blocked_users": blocked_users})

def home(request):
    return render(request, 'moderation/home.html')

@login_required
def block_user(request, username):
    if request.method == 'POST':
        block_duration = int(request.POST.get('block_duration', 5))  # Default to 5min
        expires_at = timezone.now() + timezone.timedelta(minutes=block_duration)

        # Create a new BlockedUser  entry
        BlockedUser.objects.update_or_create(
            username=username,
            defaults={
                'owner': request.user,  # Assuming you have the owner (user) available
                'expires_at': expires_at
            }
        )
        messages.success(request, f"User {username} has been blocked for {block_duration} minutes.")
        return redirect('admin_deleted_comments', channel_id=request.user.channel_id)


def register(request):
    if request.method == 'POST':
        form = OwnerRegistrationForm(request.POST)
        if form.is_valid():
            owner = form.save(commit=False)
            owner.set_password(form.cleaned_data['password'])   # Hash the password
            owner.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')  
    else:
        form = OwnerRegistrationForm()
    
    return render(request, 'moderation/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']  
        password = request.POST['password']  
        owner = authenticate(request, username=username, password=password)
        
        if owner is not None:
            login(request, owner)  # Log the user in
            return redirect('admin_deleted_comments', channel_id=owner.channel_id) 
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'moderation/login.html')

def user_logout(request):
    logout(request)  # Log out the user
    return redirect('home') 