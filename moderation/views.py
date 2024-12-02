from django.shortcuts import render, redirect
from .models import DeletedComment

from django.contrib import messages
from .forms import OwnerRegistrationForm

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

@login_required
def admin_deleted_comments(request, channel_id):
    deleted_comments = DeletedComment.objects.filter(channel_id=channel_id).order_by('-deleted_at')[:3]
    return render(request, 'moderation/deleted_comments.html', {'deleted_comments': deleted_comments})

def home(request):
    return render(request, 'moderation/home.html')




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