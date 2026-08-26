"""Guards pets.views._annotated_pets — both halves of it.

Query-count tests prove the annotations replaced per-row queries.
Render tests prove the annotations actually reach the template.
A page can be fast and wrong; only the second kind catches that.
"""
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Bookmark, Pet, PetRating, PetType, UserProfile


class _PetFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='counter', password='password123')
        cls.pet_type = PetType.objects.create(type_name='Dog')
        # profile() lazily creates this; without it the first request
        # pays 3 extra queries and the comparison measures that instead.
        UserProfile.objects.get_or_create(user=cls.user)

    def setUp(self):
        self.client.force_login(self.user)

    def _make_pets(self, n, rate_all=False):
        Pet.objects.all().delete()
        Pet.objects.bulk_create([
            Pet(TypeID=self.pet_type, UserID=self.user, name=f'Pet{i}')
            for i in range(n)
        ])
        targets = list(Pet.objects.all())
        if not rate_all:
            targets = targets[::3]
        PetRating.objects.bulk_create([
            PetRating(PetID=p, UserID=self.user, stars=4, comment='ok') for p in targets
        ])
        Bookmark.objects.bulk_create([
            Bookmark(PetID=p, UserID=self.user) for p in targets
        ])


class NPlusOneQueryTests(_PetFixtureMixin, TestCase):
    """Query count must not grow with row count."""

    def _count_queries_for(self, n_pets, url=None):
        url = url or reverse('pets:categories')
        self._make_pets(n_pets)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f'{url} did not return 200')
        return len(ctx.captured_queries)

    def test_categories_does_not_scale_with_pet_count(self):
        small = self._count_queries_for(5)
        large = self._count_queries_for(200)
        self.assertEqual(small, large, f'categories grew: {small} -> {large}')

    def test_profile_does_not_scale_with_pet_count(self):
        url = reverse('pets:profile')
        small = self._count_queries_for(5, url=url)
        large = self._count_queries_for(200, url=url)
        self.assertEqual(small, large, f'profile grew: {small} -> {large}')

    def test_home_does_not_scale_for_anonymous_visitors(self):
        self.client.logout()
        small = self._count_queries_for(5, url='/')
        large = self._count_queries_for(200, url='/')
        self.assertEqual(small, large, f'home grew: {small} -> {large}')


class AnnotationRenderTests(_PetFixtureMixin, TestCase):
    """The annotations must reach the template with the right values."""

    def test_bookmark_icon_matches_state(self):
        self._make_pets(5, rate_all=True)
        html = self.client.get(reverse('pets:categories')).content.decode()
        self.assertEqual(html.count('btn-unbookmark'), 5,
                         'all 5 pets are bookmarked but the page says otherwise')

    def test_profile_renders_real_rating(self):
        self._make_pets(3, rate_all=True)
        html = self.client.get(reverse('pets:profile')).content.decode()
        self.assertEqual(html.count('data-user-rating="4"'), 3,
                         'profile is not reading the user_rating annotation')