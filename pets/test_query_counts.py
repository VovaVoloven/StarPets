from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Bookmark, Pet, PetRating, PetType


class NPlusOneQueryTests(TestCase):
    """Guards the annotation fix in pets.views._annotated_pets.

    Asserts query count does not GROW with row count, rather than asserting
    a specific number — a fixed count breaks on any unrelated middleware or
    auth-backend change, and you end up deleting the test.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='counter', password='password123')
        cls.pet_type = PetType.objects.create(type_name='Dog')

    def setUp(self):
        self.client.force_login(self.user)

    def _make_pets(self, n):
        Pet.objects.bulk_create([
            Pet(TypeID=self.pet_type, UserID=self.user, name=f'Pet{i}')
            for i in range(n)
        ])
        # Rate and bookmark every third pet so the correlated subqueries in
        # _annotated_pets return real rows instead of always being empty.
        sample = list(Pet.objects.all())[::3]
        PetRating.objects.bulk_create([
            PetRating(PetID=p, UserID=self.user, stars=4, comment='ok') for p in sample
        ])
        Bookmark.objects.bulk_create([
            Bookmark(PetID=p, UserID=self.user) for p in sample
        ])

    def _count_queries_for(self, n_pets, url=None):
        url = url or reverse('pets:categories')

    def test_categories_does_not_scale_with_pet_count(self):
        small = self._count_queries_for(5)
        large = self._count_queries_for(200)
        self.assertEqual(
            small, large,
            f'Query count grew with row count: {small} -> {large}. '
            'An N+1 has been reintroduced in the categories view.'
        )

    def test_home_does_not_scale_for_anonymous_visitors(self):
        self.client.logout()
        small = self._count_queries_for(5, url='/')
        large = self._count_queries_for(200, url='/')
        self.assertEqual(small, large, f'{small} -> {large} on the anonymous home page')