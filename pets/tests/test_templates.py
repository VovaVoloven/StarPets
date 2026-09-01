from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from pets.models import Pet, PetType
from pets.templatetags.pet_filters import draw_stars

# template testing
class TemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.pet_type = PetType.objects.create(type_name='Dog')
        self.pet = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='TestPet')

    # home
    def test_home_template(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/home.html')

    # login
    def test_login_template(self):
        response = self.client.get(reverse('pets:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/login.html')

    # signup
    def test_signup_template(self):
        response = self.client.get(reverse('pets:signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/signup.html')

    # top pets
    def test_top_pets_template(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/top_pets.html')

    # categories
    def test_categories_template(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:categories'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/categories.html')

    # bookmarks
    def test_bookmarks_template(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:bookmarks'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/bookmarks.html')

    # upload
    def test_upload_template(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/upload.html')

    # own profile
    def test_profile_template(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/profile.html')

    # other user profile
    def test_view_user_profile_template(self):
        other = User.objects.create_user(username='otheruser', password='password123')
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:view_user_profile', args=[other.username]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/profile.html')

class DrawStarsTagTests(TestCase):
    def test_draw_stars_fill_percentage(self):
        self.assertEqual(draw_stars(0)['fill_percentage'], 0.0)
        self.assertEqual(draw_stars(2.5)['fill_percentage'], 50.0)
        self.assertEqual(draw_stars(5)['fill_percentage'], 100.0)
        
        # Out of bounds (Clamping)
        self.assertEqual(draw_stars(-1)['fill_percentage'], 0.0)
        self.assertEqual(draw_stars(6)['fill_percentage'], 100.0)
        
        # Bad data handling (Strings, None)
        self.assertEqual(draw_stars('invalid')['fill_percentage'], 0.0)
        self.assertEqual(draw_stars(None)['fill_percentage'], 0.0)
