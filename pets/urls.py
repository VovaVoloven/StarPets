from django.urls import path
from django.contrib.auth import views as auth_views
from pets import views
from pets.forms import CustomAuthenticationForm

app_name = 'pets'

urlpatterns = [
    # name='home' allows you to link to this page easily in your HTML
    path('', views.home, name='home'),
    path('signup', views.sign_up, name='signup'),
    path('login', auth_views.LoginView.as_view(
        template_name='pets/login.html', 
        form_class=CustomAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='pets:home'), name = 'logout'),

    path('rated/', views.top_pets, name='top_pets'),
    path('categories/', views.categories, name='categories'),
    path('bookmark/', views.bookmarks, name='bookmarks'),
    path('upload/', views.upload_pets, name='upload'),

    path('profile', views.profile, name='profile'),
    path('profile/edit/' ,views.edit_profile, name='edit_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('profile/<str:username>/', views.profile, name='view_user_profile'),

    path('toggle-bookmark/<int:pet_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('rate-pet/<int:pet_id>/', views.rate_pet, name='rate_pet'),
    path('delete/<int:pet_id>/', views.delete_pet, name='delete_pet'),
    
    path('get-comments/<int:pet_id>/', views.get_comments, name='get_comments'),
    path('post-comment/<int:pet_id>/', views.post_comment, name='post_comment'),
    path('delete-comment/<int:pet_id>/', views.delete_comment, name='delete_comment'),
]
