from django.contrib.auth.models import User
from django.urls import reverse
from PIL import Image
from io import BytesIO
from pets.forms import UploadForm, ExtendedUserCreationForm, CustomAuthenticationForm
from .models import Bookmark, Pet, PetRating, PetType, UserProfile
from django.test import TestCase, SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

# Create your tests here.

XSS_PAYLOAD = '<img src=x onerror=alert(1)>'

# Tests for home page
class HomePageTests(TestCase):
    def test_home_page_status_code(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_page_correct_content(self):
        response = self.client.get('/')
        self.assertContains(response, 'Welcome to StarPets!')

# model tests
# Tests for pet model 
class PetModelTests(TestCase):
    # Not a test
    def setUp(self):
        # Create test user and pet
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.dog_type = PetType.objects.create(type_name='Dog')
        self.pet = Pet.objects.create(TypeID=self.dog_type, UserID=self.user, name='Buddy')

    def test_pet_creation(self):
        self.assertEqual(self.pet.name, 'Buddy')
        self.assertEqual(self.pet.TypeID.type_name, 'Dog')
        self.assertEqual(self.pet.UserID.username, 'testuser')           
   
    def test_pet_rating(self):
        # To check rating is dealt with correctly
        rating = PetRating.objects.create(PetID=self.pet, UserID=self.user, stars=5, comment='Great pet!')
        self.assertEqual(rating.stars, 5)
        self.assertEqual(self.pet.name, rating.PetID.name)

    def test_bookmark(self):
        bookmark = Bookmark.objects.create(PetID=self.pet, UserID=self.user)
        self.assertTrue(Bookmark.objects.filter(PetID=self.pet, UserID=self.user).exists())
    
    def test_average_rating_calculation(self):
        self.user2 = User.objects.create_user(username='testuser2', password='password123')
        PetRating.objects.create(PetID=self.pet, UserID=self.user, stars=5)
        PetRating.objects.create(PetID=self.pet, UserID=self.user2, stars=3)
        
        self.pet.refresh_from_db()
        # (5+3)/2 = 4.0
        self.assertEqual(self.pet.average_rating, 4.0)
        
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

# view tests        
class DeletePetViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='password123')
        cls.other_user = User.objects.create_user(username='other', password='password123')
        cls.pet_type = PetType.objects.create(type_name='Dog')
        cls.pet = Pet.objects.create(TypeID=cls.pet_type, UserID=cls.user, name='TestPet')
        
    def setUp(self):
        self.client.force_login(self.user)
            
    def test_delete_pet_user_post_succeeds(self):
        response = self.client.post(reverse('pets:delete_pet', args=[self.pet.id]))
        expected_url = reverse('pets:profile')
        self.assertRedirects(response, expected_url)
        self.assertEqual(Pet.objects.filter(id=self.pet.id).count(), 0)
        
    def test_delete_pet_of_other_user_fails(self):
        other_pet=Pet.objects.create(TypeID=self.pet_type, UserID=self.other_user, name='OtherUserTestPet')
        response = self.client.post(reverse('pets:delete_pet', args=[other_pet.id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Pet.objects.filter(id=other_pet.id).count(), 1)
        
    def test_delete_pet_rejects_get(self):
        response = self.client.get(reverse('pets:delete_pet', args=[self.pet.id]))
        self.assertEqual(response.status_code, 405)
    
    def test_delete_pet_blocks_logged_out_user(self):
        self.client.logout()
        
        response = self.client.post(reverse('pets:delete_pet', args=[self.pet.id]))
        expected_url = f"{reverse('pets:login')}?next={reverse('pets:delete_pet', args=[self.pet.id])}"
        self.assertRedirects(response, expected_url)

# tests for top pets view (& login required for all pages)
class TopPetsViewTests(TestCase):
    
    def setUp(self):
        # create test user
        self.user = User.objects.create_user(username='testuser', password='password123')
    
    # test that user cannot access pages unless logged in
    def test_login_required(self):
        #for top pets access
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(response.status_code, 302)
        #for category access
        response = self.client.get(reverse('pets:categories'))
        self.assertEqual(response.status_code, 302)
        #for bookmarks access
        response = self.client.get(reverse('pets:bookmarks'))
        self.assertEqual(response.status_code, 302)
        #for upload page
        response = self.client.get(reverse('pets:upload'))
        self.assertEqual(response.status_code, 302)

    #test that logout works and blocks access
    def test_logout_blocks_access(self):
        self.client.login(username='testuser', password='password123')
        self.client.logout()
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(response.status_code, 302)

    #test that when no pets, page still loads
    def test_top_pets_empty(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(response.status_code, 200)

    #test ordering of pets by rating
    def test_top_pets_ordering(self):
        self.client.login(username='testuser', password='password123')
        dog = PetType.objects.create(type_name='Dog')
        pet1 = Pet.objects.create(TypeID=dog, UserID=self.user, name='Low')
        pet2 = Pet.objects.create(TypeID=dog, UserID=self.user, name='High')
        PetRating.objects.create(PetID=pet1, UserID=self.user, stars=2)
        PetRating.objects.create(PetID=pet2, UserID=self.user, stars=5)
        response = self.client.get(reverse('pets:top_pets'))
        pets = list(response.context['top_pets'])
        self.assertEqual(pets[0].name, 'High')

#tests for bookmark view
class BookmarkViewTests(TestCase):
    
    def setUp(self):
        # create test user
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='other', password='password123')
        # create test pets
        self.pet_type = PetType.objects.create(type_name='Dog')
        self.pet1 = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='Pet1')
        self.pet2 = Pet.objects.create(TypeID=self.pet_type, UserID=self.other_user, name='Pet2')

    # add a bookmark
    def test_add_bookmark(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('pets:toggle_bookmark', args=[self.pet1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Bookmark.objects.filter(PetID=self.pet1, UserID=self.user).exists())
        self.assertEqual(response.json()['is_bookmarked'], True)

    # test only bookmarked pets are shown
    def test_only_bookmarked_pets_displayed(self):
        self.client.login(username='testuser', password='password123')
        # bookmark only pet1, check only that one is displayed
        Bookmark.objects.create(PetID=self.pet1, UserID=self.user)
        response = self.client.get(reverse('pets:bookmarks'))
        self.assertContains(response, 'Pet1')
        self.assertNotContains(response, 'Pet2')
    
    # test bookmarks can be removed
    def test_remove_bookmark(self):
        self.client.login(username='testuser', password='password123')
        Bookmark.objects.create(PetID=self.pet1, UserID=self.user)
        response = self.client.post(reverse('pets:toggle_bookmark', args=[self.pet1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Bookmark.objects.filter(PetID=self.pet1, UserID=self.user).exists())
        self.assertEqual(response.json()['is_bookmarked'], False)
    
# tests categories view
class CategoriesViewTests(TestCase):
    
    def setUp(self):
        # create test user
        self.user = User.objects.create_user(username='testuser', password='password123')
        # create test pets
        self.dog = PetType.objects.create(type_name='Dog')
        self.cat = PetType.objects.create(type_name='Cat')
        self.pet1 = Pet.objects.create(TypeID=self.dog, UserID=self.user, name='Pet1')
        self.pet2 = Pet.objects.create(TypeID=self.cat, UserID=self.user, name='Pet2')
    
    # test that if no filter, all pets returned
    def test_no_filter(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:categories'))
        self.assertContains(response, 'Pet1')
        self.assertContains(response, 'Pet2')
        self.assertEqual(len(response.context['pets']), 2)

    # test that animal filters work
    def test_filter_by_type(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:categories') + '?type=Dog')
        self.assertContains(response, 'Pet1')
        self.assertNotContains(response, 'Pet2')

# tests for upload page
class UploadViewTests(TestCase):
    def setUp(self):
        # create test user
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        self.pet_type = PetType.objects.create(type_name="Dog")
        self.url = reverse('pets:upload')        
    
    # test a get request returns correct template
    def test_upload_pets_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pets/upload.html')
        self.assertIn('form', response.context)

        # helper to generate test image
    def generate_photo_file(self):
        file = BytesIO()
        image = Image.new('RGB', (100, 100), 'white')
        image.save(file, 'jpeg')
        file.name = 'test.jpg'
        file.seek(0)
        return file

    # test valid upload
    def test_upload_file_success(self):
        image = self.generate_photo_file()
        form_data = {
            'TypeID': self.pet_type.id,
            'name': 'TestPet',
            'description': 'cute pet'
        }
        file_data = {
            'picture': image
        }
        response = self.client.post(self.url, data={**form_data, **file_data}, follow=True)
        # ckeck redirect to profile
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Pet.objects.filter(name='TestPet').exists())

    # test that uploaded pet is assigned to logged-in user
    def test_uploaded_pet_belongs_to_user(self):
        image = self.generate_photo_file()

        response = self.client.post(self.url, data={
            'TypeID': self.pet_type.id,
            'name': 'OwnedPet',
            'description': 'Owned by user',
            'picture': image
        })

        pet = Pet.objects.get(name='OwnedPet')
        self.assertEqual(pet.UserID, self.user)

# test rating view
class RatingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        self.pet_type = PetType.objects.create(type_name='Dog')
        self.pet = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='TestPet')

    # successful rating
    def test_rate_pet_success(self):
        response = self.client.post(
            reverse('pets:rate_pet', args=[self.pet.id]),
            data='{"rating": 5}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PetRating.objects.filter(PetID=self.pet, UserID=self.user).exists())
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_average'], 5.0)
        
    def test_rate_pet_missing_pet_fails(self):
        non_existent_id = 9999
        response = self.client.post(
            reverse('pets:rate_pet', args=[non_existent_id]),
            data='{"rating": 5}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        
    def test_rate_pet_bad_json_rejected_and_caught(self):
        response = self.client.post(
            reverse('pets:rate_pet', args=[self.pet.id]),
            data='{bad json',
            content_type='application/json'
        )
        data = response.json()
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Invalid rating format')
        
    def test_rate_pet_out_of_range_rejected_and_caught(self):
        response = self.client.post(
            reverse('pets:rate_pet', args=[self.pet.id]),
            data='{"rating": 6}',
            content_type='application/json'
        )
        data = response.json()
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Rating must be between 1 and 5')
        
    def test_rate_pet_rejects_get(self):
        response = self.client.get(
            reverse('pets:rate_pet', args=[self.pet.id]),
        )
        self.assertEqual(response.status_code, 405)

    # update existing rating
    def test_update_rating(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.user, stars=2)
        response = self.client.post(
            reverse('pets:rate_pet', args=[self.pet.id]),
            data='{"rating": 4}',
            content_type='application/json'
        )
        rating = PetRating.objects.get(PetID=self.pet, UserID=self.user)
        self.assertEqual(rating.stars, 4)

    # invalid rating - out of range
    def test_invalid_rating(self):
        response = self.client.post(
            reverse('pets:rate_pet', args=[self.pet.id]),
            data='{"rating": 10}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    # login rquired to rate
    def test_rate_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('pets:rate_pet', args=[self.pet.id]),
            data='{"rating": 5}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)

# test comments view
class CommentViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='password123')
        cls.other_user = User.objects.create_user(username='other', password='password123')
        cls.pet_type = PetType.objects.create(type_name='Dog')
        cls.pet = Pet.objects.create(TypeID=cls.pet_type, UserID=cls.user, name='TestPet')
        
    def setUp(self):
        self.client.force_login(self.user)
 
    def test_post_comment_valid(self):
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]),
            data={'comment': 'Nice pet!'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PetRating.objects.get(PetID=self.pet, UserID=self.user).comment, 'Nice pet!')
        
    def test_post_comment_whitespaces_only(self):
        response = self.client.post(
                reverse('pets:post_comment', args=[self.pet.id]),
                data={'comment': '     '}
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PetRating.objects.filter(PetID=self.pet, UserID=self.user).count(), 0)
        
    def test_post_comment_exactly_200_chars(self):
        max_length_comment = 'a' * 200
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]),
            data={'comment': max_length_comment}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PetRating.objects.get(PetID=self.pet, UserID=self.user).comment, max_length_comment)
        
    def test_post_comment_201_chars_fails(self):
        too_long_comment = 'a' * 201
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]),
            data={'comment': too_long_comment}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PetRating.objects.filter(PetID=self.pet, UserID=self.user).count(), 0)
        
    def test_post_comment_empty_string(self):
        response = self.client.post(
                reverse('pets:post_comment', args=[self.pet.id]),
                data={'comment': ''}
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PetRating.objects.filter(PetID=self.pet, UserID=self.user).count(), 0)
            
    def test_post_comment_blocks_logged_out_user(self):
        self.client.logout()
        
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]),
            data={'comment': 'Beatiful!'}
            )
        self.assertEqual(response.status_code, 302)
        
    def test_post_comment_edit_not_duplicate(self):
        self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]), 
            data={'comment': 'Beautifull pet!'})
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]), 
            data={'comment': 'Nice!'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        count = PetRating.objects.filter(PetID=self.pet, UserID=self.user).count()
        self.assertEqual(count, 1)
        self.assertEqual(data['text'], "Nice!")
            
    def test_post_comment_preserves_stars(self):
        rating = PetRating.objects.create(PetID=self.pet, UserID=self.user, stars = 4)
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]), 
            data={'comment': 'Nice!'})
        self.assertEqual(response.status_code, 200)
        
        rating.refresh_from_db()
        
        self.assertEqual(rating.stars, 4)
        
    def test_post_comment_without_rating_preserves_average(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.other_user, stars = 3)
        self.pet.refresh_from_db()
        self.assertEqual(self.pet.average_rating, 3.0)
        
        response = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]), 
            data={'comment': 'Nice!'})
        self.assertEqual(response.status_code, 200)
        
        self.pet.refresh_from_db()
        self.assertEqual(self.pet.average_rating, 3.0)
        
    def test_post_comment_rejects_get(self):
        response = self.client.get(
                reverse('pets:post_comment', args=[self.pet.id]),
                data={'comment': 'Nice!'}
            )
        self.assertEqual(response.status_code, 405)
        
    def test_get_comment_other_user_rated_not_commented(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.other_user, stars = 3)
        response = self.client.get(reverse('pets:get_comments', args=[self.pet.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['comments'], [])
        
    def test_get_comment_user_rated_not_commented(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.user, stars = 4)
        response = self.client.get(reverse('pets:get_comments', args=[self.pet.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user_has_commented'], False)
        self.assertEqual(data['user_comment_text'], '')
        
    def test_get_comment_user_valid_comment_appears(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.user, stars = 4, comment="Nice pet!")
        response = self.client.get(reverse('pets:get_comments', args=[self.pet.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user_comment_text'], 'Nice pet!')
        self.assertEqual(data['user_has_commented'], True)
        self.assertEqual(len(data['comments']), 1)
        self.assertEqual(data['comments'][0]['text'], 'Nice pet!')
        self.assertEqual(data['comments'][0]['is_owner'], True)
        
    def test_get_comment_other_user_valid_comment_appears(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.other_user, stars = 5, comment="Beautifull pet!")
        response = self.client.get(reverse('pets:get_comments', args=[self.pet.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['comments']), 1)
        self.assertEqual(data['comments'][0]['username'], 'other')
        self.assertEqual(data['comments'][0]['is_owner'], False)
        
    def test_get_comments_blocks_logged_out_user(self):
        self.client.logout()
        
        response = self.client.get(reverse('pets:get_comments', args=[self.pet.id]))
        self.assertEqual(response.status_code, 302)
        
    def test_delete_comment_valid(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.user, stars = 5, comment="Beautifull pet!")
        
        response = self.client.post(reverse('pets:delete_comment', args=[self.pet.id]))
        self.assertEqual(response.status_code, 200)
        
        rating = PetRating.objects.get(PetID=self.pet, UserID=self.user)
        data = response.json()
        
        self.assertEqual(rating.comment, '')
        self.assertEqual(rating.stars, 5)
        self.assertEqual(data['status'], 'deleted')
        
    def test_delete_comment_with_no_rating(self):
        response = self.client.post(reverse('pets:delete_comment', args=[self.pet.id]))
        data = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Invalid request')
        
    def test_delete_comment_other_user_comment_untouched(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.other_user, stars = 5, comment="Beautifull pet!")
        
        response = self.client.post(reverse('pets:delete_comment', args=[self.pet.id]))
        self.assertEqual(response.status_code, 400)
        
        rating = PetRating.objects.get(PetID=self.pet, UserID=self.other_user)
        self.assertEqual(rating.comment, 'Beautifull pet!')
        
    def test_delete_comment_blocks_logged_out_user(self):
        self.client.logout()
        
        response = self.client.post(reverse('pets:delete_comment', args=[self.pet.id]))
        self.assertEqual(response.status_code, 302)
        
    def test_delete_comment_rejects_get(self):
        response = self.client.get(
                reverse('pets:delete_comment', args=[self.pet.id])
            )
        self.assertEqual(response.status_code, 405)
        
    def test_get_comments_returns_unescaped_html(self):
        PetRating.objects.create(PetID=self.pet, UserID=self.user, stars = 4)
        response_post = self.client.post(
            reverse('pets:post_comment', args=[self.pet.id]),
            data={'comment': XSS_PAYLOAD})
        
        self.assertEqual(response_post.status_code, 200)
        
        response_get = self.client.get(reverse('pets:get_comments', args=[self.pet.id]))
        data = response_get.json()
        self.assertEqual(data['user_comment_text'], XSS_PAYLOAD)
        self.assertEqual(data['comments'][0]['text'], XSS_PAYLOAD)
    
# test profile view
class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.pet_type = PetType.objects.create(type_name='Dog')
        self.pet1 = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='UserPet')
        self.pet2 = Pet.objects.create(TypeID=self.pet_type, UserID=self.other_user, name='OtherPet')

    # user can view own profile once logged in
    def test_view_own_profile(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['viewed_user'], self.user)
        self.assertTrue(response.context['is_owner'])

    # if not logged in redirect
    def test_profile_requires_login(self):
        response = self.client.get(reverse('pets:profile'))
        self.assertEqual(response.status_code, 302)

    # view another user's profile
    def test_view_other_user_profile(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(
            reverse('pets:view_user_profile', args=[self.other_user.username])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['viewed_user'], self.other_user)
        self.assertFalse(response.context['is_owner'])

    # invalid username leads to error
    def test_view_nonexistent_user_profile(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(
            reverse('pets:view_user_profile', args=['doesnotexist'])
        )
        self.assertEqual(response.status_code, 404)

    # only user's own pets are shown
    def test_profile_shows_only_users_pets(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:profile'))
        self.assertContains(response, 'UserPet')
        self.assertNotContains(response, 'OtherPet')
        pets = response.context['pets']
        self.assertEqual(len(pets), 1)
        self.assertEqual(pets[0], self.pet1)

    # user profile object is created automatically
    def test_user_profile_created(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('pets:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

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

