from django.db.models import Avg
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import PetRating, UserProfile, Pet
import os

# --- Pet Rating Signals ---

# Signal to update average rating of a pet whenever a new rating is added or deleted
@receiver(post_save, sender='pets.PetRating')
@receiver(post_delete, sender='pets.PetRating')
# Listens for any save() or delete() on a PetRating. When triggered recalculates the average and updates the parent Pet.
def update_pet_average_rating(sender, instance, **kwargs):
    pet = instance.PetID
    
    # Calculate the new average for this specific pet
    stats = PetRating.objects.filter(PetID=pet, stars__gt=0).aggregate(Avg('stars'))
    
    # If all ratings were deleted, new_avg will be None. Default back to 0.0.
    pet.average_rating = stats['stars__avg'] or 0
    
    # Save the updated average to the db
    pet.save(update_fields=['average_rating'])
    
    
# --- PROFILE PIC DELETE LOGIC ---

#delete old file when a new one is uploaded
@receiver(pre_save, sender=UserProfile)
def auto_delete_pfp_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False
    
    try: 
        old_profile = UserProfile.objects.get(pk=instance.pk)
        old_file = old_profile.profile_picture
    except UserProfile.DoesNotExist:
        return False
    
    new_file = instance.profile_picture

    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
            
#delete file when UserProfile delete (user deletes account)
@receiver(post_delete, sender=UserProfile)
def auto_delete_pfp_on_account_delete(sender, instance, **kwargs):
    if instance.profile_picture:
        if os.path.isfile(instance.profile_picture.path):
            os.remove(instance.profile_picture.path)


#------ PET IMAGE DELETE LOGIC -------

@receiver(post_delete, sender=Pet)
def auto_delete_pet_file_on_delete(sender, instance, **kwargs):
    #Deletes pet image file if:
    #1. User deletes a single pet
    #2. User deltes their account (all their pet images get delted)

    if instance.picture:
        try:
            if os.path.isfile(instance.picture.path):
                os.remove(instance.picture.path)
        except (ValueError, FileNotFoundError):
            pass
        