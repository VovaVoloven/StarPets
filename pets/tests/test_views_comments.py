from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from pets.models import Pet, PetRating, PetType

XSS_PAYLOAD = '<img src=x onerror=alert(1)>'

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
