from PIL import Image
from io import BytesIO
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from pets.models import Bookmark, Pet, PetRating, PetType, UserProfile

# pet views tests
# Tests for home page
class HomePageTests(TestCase):
    def test_home_page_status_code(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_page_correct_content(self):
        response = self.client.get('/')
        self.assertContains(response, 'Welcome to StarPets!')
        
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
        self.other_user = User.objects.create_user(username='other', password='password123')
        self.pet_type = PetType.objects.create(type_name='Dog')
    
    # test that user cannot access pages unless logged in
    def test_top_pets_blocks_logged_out_user(self):
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
    def test_top_pets_logout_blocks_access(self):
        self.client.login(username='testuser', password='password123')
        self.client.logout()
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(response.status_code, 302)

    def test_top_pets_unrated_pet_excluded_and_empty_state_renders(self):
        self.client.login(username='testuser', password='password123')
        Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='TestPet')
        
        response = self.client.get(reverse('pets:top_pets'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['top_pets']), 0)
        self.assertContains(response, "No pets have been rated this week. Be the first!")
        
    def test_top_pets_higher_star_rating_outranks_lower(self):
        self.client.login(username='testuser', password='password123')
        pet_winner = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='Winner')
        pet_loser = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='Loser')
        
        PetRating.objects.create(PetID=pet_winner, UserID=self.user, stars = 5)
        PetRating.objects.create(PetID=pet_loser, UserID=self.user, stars = 3)
        
        response = self.client.get(reverse('pets:top_pets'))
        top_pets = list(response.context['top_pets'])
        
        self.assertEqual(len(top_pets), 2)
        self.assertEqual(top_pets[0], pet_winner)
        
    def test_top_pets_ratings_outside_window_are_excluded(self):
        self.client.login(username='testuser', password='password123')
        pet_old = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='Old Rating Pet')
        rating = PetRating.objects.create(PetID=pet_old, UserID=self.user, stars = 5)
        
        eight_days_ago = timezone.now() - timedelta(days=8)
        PetRating.objects.filter(pk=rating.pk).update(date_rated=eight_days_ago)
        
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(len(response.context['top_pets']), 0)
    
    def test_top_pets_deterministic_tie_breaker(self):
        self.client.login(username='testuser', password='password123')
        pet_older = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='Older Tied Pet')
        pet_newer = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name='Newer Tied Pet')
        
        yesterday = timezone.now() - timedelta(days=1)
        Pet.objects.filter(pk=pet_older.pk).update(date_added=yesterday)
        
        PetRating.objects.create(PetID=pet_older, UserID=self.user, stars = 4)
        PetRating.objects.create(PetID=pet_newer, UserID=self.other_user, stars = 4)
        
        response = self.client.get(reverse('pets:top_pets'))
        top_pets = list(response.context['top_pets'])
        
        self.assertEqual(top_pets[0], pet_newer)
        self.assertEqual(top_pets[1], pet_older)
        
    def test_top_pets_comment_only_rating_is_excluded(self):
        self.client.login(username='testuser', password='password123')
        pet_comment_only = Pet.objects.create(TypeID=self.pet_type, UserID=self.user, name="Comment Only")
        
        PetRating.objects.create(PetID=pet_comment_only, UserID=self.user, stars=0, comment="Nice pet!")
        
        response = self.client.get(reverse('pets:top_pets'))
        self.assertEqual(len(response.context['top_pets']), 0)

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
