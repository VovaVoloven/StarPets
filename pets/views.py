from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Exists, OuterRef, Subquery, Value, IntegerField
from django.db.models.functions import Coalesce
from .forms import ExtendedUserCreationForm, UploadForm, UserProfileForm, CustomAuthenticationForm, CommentForm
from .models import Bookmark, Pet, PetType, PetRating, UserProfile
import datetime
import json


def _annotated_pets(qs, user):
    """One query for the page: FKs joined, per-user rating/bookmark folded in
    as correlated subqueries instead of a query per card."""
    qs = qs.select_related('UserID', 'TypeID')
    if not user.is_authenticated:
        return qs.annotate(
            user_commented=Value(False),
            user_rating=Value(0, output_field=IntegerField()),
            is_bookmarked=Value(False),
        )
    mine = PetRating.objects.filter(PetID=OuterRef('pk'), UserID=user)
    return qs.annotate(
        user_commented=Exists(mine.exclude(comment="")),
        user_rating=Coalesce(Subquery(mine.values('stars')[:1]), Value(0)),
        is_bookmarked=Exists(Bookmark.objects.filter(PetID=OuterRef('pk'), UserID=user)),
    )

def home(request):
    pets = _annotated_pets(Pet.objects.all(), request.user)
    return render(request, 'pets/home.html', {'pets': pets})

@login_required
def top_pets(request):
    # Calculate the exact time 7 days ago
    one_week_ago = timezone.now() - datetime.timedelta(days=7)
    
    # Fetch and filter pets added in the last 7 days, then get the top 4 pets based on their average rating, ordered from highest to lowest
    top_pets_list = Pet.objects.filter(date_added__gte=one_week_ago).order_by('-average_rating')[:4]
    
    # If the list is empty, fallback to the all-time top 4
    if not top_pets_list.exists():
        top_pets_list = Pet.objects.order_by('-average_rating')[:4]
    
    top_pets_list = _annotated_pets(top_pets_list, request.user)
    
    # Add the top pets to the context dictionary and render the top pets template
    context = {
        'top_pets' : top_pets_list,
        'comment_form': CommentForm(),
    }
    return render(request, 'pets/top_pets.html', context)

@login_required
def categories(request):
    # Fetch all pet types for the filter
    pet_types = PetType.objects.all().order_by('type_name')
    selected_type = request.GET.get('type')
    
    # Apply a filter or return ALL pets if no filter is selected
    if selected_type and selected_type != 'all':
        pets = Pet.objects.filter(TypeID__type_name=selected_type)
    else:
        pets = Pet.objects.all()
    
    pets = _annotated_pets(pets, request.user)

    # Add to the context dictionary the list of pets, types and selected type
    context = {
        'pets': pets,
        'pet_types': pet_types,
        'selected_type': selected_type,
        'comment_form': CommentForm(),
    }
    return render(request, 'pets/categories.html', context)

@login_required
def bookmarks(request):
    # Fetch the pets that are bookmarked by the user
    bookmarked_pets = _annotated_pets(
        Pet.objects.filter(bookmark__UserID=request.user), request.user)
    
    # Add the bookmarked pets to the context dictionary and render the bookmarks template
    context = {
        'pets': bookmarked_pets,
        'comment_form': CommentForm()
    }
    return render(request, 'pets/bookmarks.html', context)

# Backend view for handling bookmark toggling via javascript fetch API
@login_required
def toggle_bookmark(request, pet_id):
    if request.method == 'POST':
        # Fetch the pet based on provided ID or return 404 if not found
        pet = get_object_or_404(Pet, id=pet_id)

        # Get a bookmark or create one if it doesn't exist, then toggle its existence
        bookmark, created = Bookmark.objects.get_or_create(UserID=request.user, PetID=pet)

        if not created:
            # If it already exists, it means we want to remove the bookmark, so we delete it
            bookmark.delete()
            return JsonResponse({'is_bookmarked': False})
        else:
            # If it was created, it means we want to add the bookmark, so we return a success response
            return JsonResponse({'is_bookmarked': True})
        
    # If the request method is not POST, we return an error response indicating an invalid request
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def upload_pets(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.UserID = request.user
            pet.save()
            return redirect('pets:profile')
    else:
        form = UploadForm()
    return render(request, 'pets/upload.html', {'form':form})

@login_required
def profile(request, username=None):
    #no username given, & user is logged in: display their own profile
    #if username given, show that user's profile

    if username is None:
        if request.user.is_authenticated:
            viewed_user = request.user
        else:
            return redirect('pets:login')
    else:
        viewed_user = get_object_or_404(User, username=username)

    user_pets = _annotated_pets(Pet.objects.filter(UserID=viewed_user), request.user)
    user_profile, created = UserProfile.objects.get_or_create(user=viewed_user)

    is_owner = (request.user == viewed_user)

    context = {
        "viewed_user": viewed_user,
        "user_profile": user_profile,
        "pets": user_pets,
        "is_owner": is_owner,
        "comment_form": CommentForm()
    } 

    return render(request, 'pets/profile.html', context)

@login_required
def edit_profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "status":"success",
                    "message": "Profile updates successfully!",
                    "description": user_profile.description
                })
            return redirect('pets:profile')
    
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "errors": form.errors}, status = 400)
            
    return redirect('pets:profile')

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        logout(request)
        messages.success(request, "Your account has been successfully deleted.")
        return redirect('pets:home')
    
    return redirect('pets:profile')

def login_view(request):
    if request.method == 'POST':
        # Pass the request and the POST data to your custom form
        form = CustomAuthenticationForm(request, data=request.POST)
        
        # This is where ReCaptcha is actually verified!
        if form.is_valid(): 
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('pets:home')
    else:
        form = CustomAuthenticationForm()
        
    return render(request, 'pets/login.html', {'form': form})


def sign_up(request):
    if request.method == 'POST':
        form = ExtendedUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request,user)
            messages.success(request, f"Welcome to StarPets, {user.username}!")
            return redirect('pets:home')

    else:
        form = ExtendedUserCreationForm()
    return render(request, 'pets/signup.html', {'form':form})

@login_required
@require_POST
def rate_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    try:
        data = json.loads(request.body)
        stars = int(data.get('rating', 0))
    except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
        return JsonResponse({'error' : "Invalid rating format"}, status=400)    
    
    if 1<= stars <= 5:
        PetRating.objects.update_or_create(
            UserID=request.user,
            PetID=pet,
            defaults={'stars': stars}
        )
        
        pet.refresh_from_db()
        
        return JsonResponse({'success' : True, 'new_average' : pet.average_rating})
    return JsonResponse({'error' : "Rating must be between 1 and 5"}, status=400)

#pet deletion

@login_required
@require_POST
def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, UserID=request.user)
    pet.delete()
    messages.success(request, "Your upload has been successfully deleted.")
    return redirect('pets:profile')

# comments
@login_required
def get_comments(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    ratings = PetRating.objects.filter(PetID=pet).select_related('UserID')

    user_comment = ratings.filter(UserID=request.user).first()
    
    comments_data = [{
        'username': r.UserID.username,
        'text': r.comment,
        'date': r.rating_date.strftime("%b %d, %Y"),
        'is_owner': r.UserID == request.user
    }for r in ratings if r.comment]

    return JsonResponse({
        'comments': comments_data,
        'user_has_commented': user_comment is not None and bool(user_comment.comment),
        'user_comment_text': user_comment.comment if user_comment else ""
    })

@login_required
@require_POST
def post_comment(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id)
    form = CommentForm(request.POST)
    
    if form.is_valid():
        text = form.cleaned_data['comment']
        
        PetRating.objects.update_or_create(
            PetID=pet, UserID=request.user,
            defaults={'comment':text}
        )
        return JsonResponse({'status': 'success','text': text})
    error_msg = form.errors['comment'][0] if 'comment' in form.errors else "Invalid submission"
    return JsonResponse({'error': error_msg}, status=400)

@login_required
@require_POST
def delete_comment(request, pet_id):
    rating = PetRating.objects.filter(PetID=pet_id, UserID=request.user).first()
    if rating:
        rating.comment = ""
        rating.save()
        return JsonResponse({'status': 'deleted'})
    return JsonResponse({'error': 'Invalid request'}, status=400)
