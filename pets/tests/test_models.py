import hashlib
import tempfile
import io
from PIL import Image
from django.test import TestCase
from django.contrib.auth.models import User
from pets.models import Bookmark, Pet, PetRating, PetType
from django.core.files.uploadedfile import SimpleUploadedFile

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
        
class PetImageTests(TestCase):   
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='rater', password='password123')
        self.pet_type = PetType.objects.create(type_name='Dog')
        
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        
    def test_rating_does_not_reencode_image(self):
        with self.settings(MEDIA_ROOT=self.media_dir.name):
            
            image_io = io.BytesIO()
            Image.effect_noise((300, 300), 50).convert('RGB').save(image_io, format='JPEG')
            
            fake_image = SimpleUploadedFile(
                'test_pet.jpg',
                image_io.getvalue(),
                content_type='image/jpeg'
            )
            
            pet = Pet.objects.create(
                TypeID=self.pet_type,
                UserID=self.user,
                name='TestPet',
                picture=fake_image
            )
            
            def get_file_hash(filepath):
                with open(filepath, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()
                    
            initial_hash = get_file_hash(pet.picture.path)
            
            PetRating.objects.create(PetID=pet, UserID=self.user, stars = 3)
            
            post_rating_hash = get_file_hash(pet.picture.path)
            
            self.assertEqual(initial_hash, post_rating_hash)
