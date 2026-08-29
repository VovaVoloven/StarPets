from django import forms
from django.conf import settings
from .models import Pet, PetType, UserProfile, PetRating
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3
from django.contrib.auth.models import User

class OptionalReCaptchaMixin:
    """
    Dynamically removes the 'captcha' field if settings.RECAPTCHA_ENABLED is False.
    Must be placed BEFORE the main form class in the inheritance list.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # We use getattr with a default of False to avoid crashes, 
        # and because it plays perfectly with Django's @override_settings in tests.
        if not getattr(settings, 'RECAPTCHA_ENABLED', False):
            if 'captcha' in self.fields:
                del self.fields['captcha']

class ExtendedUserCreationForm(OptionalReCaptchaMixin, UserCreationForm):
    email = forms.EmailField(required=True, help_text="Enter your email here")
    captcha = ReCaptchaField(widget=ReCaptchaV3)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)
        
# Custom login form to inject the Captcha
class CustomAuthenticationForm(OptionalReCaptchaMixin, AuthenticationForm):
    captcha = ReCaptchaField(widget=ReCaptchaV3)


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
