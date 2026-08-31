from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from PIL import Image, ImageOps

class PetType(models.Model):
    type_name = models.CharField(max_length=128, unique=True)
    
    class Meta:
        verbose_name_plural = "Pet Types"

    def __str__(self):
        return self.type_name

class Pet(models.Model):
    TypeID = models.ForeignKey(PetType, on_delete=models.CASCADE)
    UserID = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    picture = models.ImageField(upload_to='pet_images', blank=True)
    description = models.TextField(default="No description provided.")
    date_added = models.DateTimeField(auto_now_add=True)
    average_rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.name
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_picture = self.__dict__.get('picture')
    
    def save(self, *args, **kwargs):
        is_picture_changed = False
        current_picture_name = self.picture.name if self.picture else None
        
        if self.pk is None or current_picture_name != self._initial_picture:
            is_picture_changed = True

        super().save(*args, **kwargs)

        if is_picture_changed and self.picture:
            img_path = self.picture.path
            img = Image.open(img_path)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Simply scales down massive photos to 1200px max
            # thumbnail() PRESERVES the original aspect ratio (No padding!)
            img.thumbnail((1200, 1200)) 
            img.save(img_path)
            self._initial_picture = self.picture.name

class PetRating(models.Model):
    PetID = models.ForeignKey(Pet, on_delete=models.CASCADE)
    UserID = models.ForeignKey(User, on_delete=models.CASCADE)
    stars = models.IntegerField(default=0)
    comment = models.TextField(blank=True, max_length=200)
    date_rated = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('PetID', 'UserID')

    def __str__(self):
        return f"{self.UserID.username} rated {self.PetID.name} with {self.stars}"

class Bookmark(models.Model):
    PetID = models.ForeignKey(Pet, on_delete=models.CASCADE)
    UserID = models.ForeignKey(User, on_delete=models.CASCADE)
    bookmark_date= models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.UserID.username} bookmarked {self.PetID.name}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures', blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.user.username
