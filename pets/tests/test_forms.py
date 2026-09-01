from django.test import SimpleTestCase, override_settings
from pets.forms import ExtendedUserCreationForm, CustomAuthenticationForm

class CaptchaFormTests(SimpleTestCase):
    
    @override_settings(RECAPTCHA_ENABLED=True)
    def test_forms_include_captcha_when_enabled(self):
        auth_form = CustomAuthenticationForm()
        register_form = ExtendedUserCreationForm()
        
        self.assertIn('captcha', auth_form.fields)
        self.assertIn('captcha', register_form.fields)

    @override_settings(RECAPTCHA_ENABLED=False)
    def test_forms_drop_captcha_when_disabled(self):
        auth_form = CustomAuthenticationForm()
        register_form = ExtendedUserCreationForm()
        
        self.assertNotIn('captcha', auth_form.fields)
        self.assertNotIn('captcha', register_form.fields)
