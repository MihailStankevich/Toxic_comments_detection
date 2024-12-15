from django.shortcuts import render, redirect, get_object_or_404
from .models import DeletedComment, BlockedUser, Owner

from django.contrib import messages
from .forms import OwnerRegistrationForm

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from django.core.paginator import Paginator

from django.db.models import Q
from django.core.mail import send_mail

def home(request):
    return render(request, 'moderation/home.html')

@login_required
def admin_deleted_comments(request, channel_id):
    deleted_comments = DeletedComment.objects.filter(channel_id=channel_id).order_by('-deleted_at')
    search_query = request.GET.get('search', '')
    if search_query:
        deleted_comments = deleted_comments.filter(
            Q(post__icontains=search_query) | Q(user__icontains=search_query)
        )

    paginator = Paginator(deleted_comments, 5)  # Show 5 comments per page
    page_number = request.GET.get('page', 1)  # Get the current page number
    comments_page = paginator.get_page(page_number) 

    blocked_users = BlockedUser .objects.filter(owner=request.user, expires_at__gt=timezone.now()).values_list('username', flat=True)

    return render(request, 'moderation/deleted_comments.html', {'deleted_comments': comments_page, "channel_id": channel_id, "blocked_users": blocked_users})

@login_required
def blocked_users(request,channel_id):
    owner = Owner.objects.get(channel_id=channel_id)
    blocked_users = BlockedUser.objects.filter(owner=owner, expires_at__gt=timezone.now())

    total = blocked_users.count()
    for user in blocked_users:
        remaining_time = user.expires_at - timezone.now()  # Calculate remaining time
        total_seconds = int(remaining_time.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        user.remaining_time_display = f"{days}d {hours}h {minutes}m {seconds}s" if days > 0 else f"{hours}h {minutes}m {seconds}s"
    return render(request, 'moderation/blocked_users.html',{'blocked_users': blocked_users, 'total': total})

@login_required
def block_user(request, username):
    if request.method == 'POST':
        block_duration = int(request.POST.get('block_duration', 5))  # Default to 5min
        expires_at = timezone.now() + timezone.timedelta(minutes=block_duration)

        comment_id = request.POST.get('comment_id') 
        comment = DeletedComment.objects.get(id=comment_id) if comment_id else None

        BlockedUser.objects.update_or_create(
            username=username,
            defaults={
                'owner': request.user,  
                'comment': comment,
                'expires_at': expires_at,
                'blocked_at': timezone.now()
            }
        )
        messages.success(request, f"User {username} has been blocked for {block_duration} minutes.")
        return redirect('admin_deleted_comments', channel_id=request.user.channel_id)
    
@login_required
def unblock_user(request, username):
    if request.method == 'POST':
        # Get the blocked user instance
        blocked_user = get_object_or_404(BlockedUser , username=username, owner=request.user)
        
        # Delete the blocked user record
        blocked_user.delete()
        messages.success(request, f'User  {username} has been unblocked successfully.')
        
        # Redirect to the blocked users page with a success message
        return redirect('blocked_users', channel_id=request.user.channel_id)

def register(request):
    if request.method == 'POST':
        form = OwnerRegistrationForm(request.POST)
        if form.is_valid():
            owner = form.save(commit=False)
            owner.set_password(form.cleaned_data['password'])  
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
            login(request, owner) 
            return redirect('admin_deleted_comments', channel_id=owner.channel_id) 
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'moderation/login.html')

def user_logout(request):
    logout(request) 
    return redirect('home') 

def contact(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        description = request.POST.get('description', '')

        # Prepare the email content
        subject = 'New Contact Form Submission'
        message = f'You have received a new message from {email}.\n\nDescription:\n{description}'
        from_email = 'mihailstankevich15@gmail.com'

        
        try:
            send_mail(subject, message, from_email, ['mihailstankevich15@gmail.com'])  
            messages.success(request, "Your message has been sent successfully! We will get in touch with you soon")
        except Exception as e:
            messages.error(request, "There was an error sending your message. Please try again later.")  # Log the error for debugging

        return redirect('home') 

    return render(request, 'moderation/home.html')


