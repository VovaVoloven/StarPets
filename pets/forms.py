from django import forms
from django.conf import settings
from .models import Pet, PetType, UserProfile, PetRating
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3
from django.contrib.auth.models import User

class ExtendedUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Enter your email here")
    captcha = ReCaptchaField(widget=ReCaptchaV3)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop the captcha field if API keys are not configured in settings
        if not hasattr(settings, 'RECAPTCHA_PUBLIC_KEY'):
            del self.fields['captcha']
        
# Custom login form to inject the Captcha
class CustomAuthenticationForm(AuthenticationForm):
    captcha = ReCaptchaField(widget=ReCaptchaV3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop the captcha field if API keys are not configured in settings
        if not hasattr(settings, 'RECAPTCHA_PUBLIC_KEY'):
            del self.fields['captcha']


class UploadForm(forms.ModelForm):
    name = forms.CharField(required=True, label="Enter your pets name:")
    TypeID = forms.ModelChoiceField(required=True, queryset=PetType.objects.none(), label="Select pet category:")
    picture = forms.ImageField(required=True, label="Upload pet image")
    description = forms.CharField(label="Description:")

    class Meta:
        model = Pet
        exclude = ('UserID', 'average_rating')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['TypeID'].queryset = PetType.objects.all().order_by('type_name')


class UserProfileForm(forms.ModelForm):
    description = forms.CharField(required=False, max_length=200, help_text="Enter your description here!")
    profile_picture = forms.ImageField(required=False, help_text="Upload a profile picture")

    class Meta:
        model = UserProfile
        fields = ('profile_picture','description')

class CommentForm(forms.ModelForm):
    class Meta:
        model = PetRating
        fields = ['stars', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'id': 'commentContent',
                'class': 'form-control',
                'rows':3,
                'placeholder': 'Share your thoughts!',
                'maxlength': '200'
            }),
        }
