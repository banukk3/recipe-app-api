import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Ingredient, Tag

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Return URL for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_recipe(user, **params):
    """Create and return a sampel recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


def sample_tag(user, name='Main Course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Cinnamon'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_require(self):
        """Test that authentication is required"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test Authenticated recipe API access"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'tests@az.com'
            'tests123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        recipes = Recipe.objects.all().order_by('-id')

        res = self.client.get(RECIPES_URL)

        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = get_user_model().objects.create_user(
            'tests@az.com',
            'tests123'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_details(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate Cheesecake',
            'time_minutes': 30,
            'price': 5.00
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

        def test_create_recipe_with_tags(self):
            """Test creating a recipe with tags"""
            tag1 = sample_tag(user=self.user, name='Vegan')
            tag2 = sample_tag(user=self.user, name='Dessert')
            payload = {
                'title': 'Avocado lime cheesecake',
                'tags': [tag1.id, tag2.id],
                'time_minutes': 60,
                'price': 20.00
            }
            res = self.client.post(RECIPES_URL, payload)

            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            recipe = Recipe.objects.get(id=res.data['id'])
            tags = recipe.tags.all()
            self.assertEqual(tags.count(), 2)
            self.assertIn(tag1, tags)
            self.assertIn(tag2, tags)

        def test_create_recipe_with_ingredients(self):
            """Test creating recipe with ingredients"""
            ingredient1 = sample_ingredient(user=self.user, name='Prwans')
            ingredient2 = sample_ingredient(user=self.user, name='Ginger')
            payload = {
                'title': 'Thai prawn red curry',
                'ingredients': [ingredient1.id, ingredient2.id],
                'time_minutes': 20,
                'price': 7.00
            }
            res = self.client.post(RECIPES_URL, payload)

            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            recipe = Recipe.objects.get(id=res.data['id'])
            ingredients = recipe.ingredients.all()
            self.assertEqual(ingredients.count(), 2)
            self.assertIn(ingredient1, ingredients)
            self.assertIn(ingredient2, ingredients)

        def test_partial_update_recipe(self):
            """Test updating a recipe with patch"""
            recipe = sample_recipe(user=self.user)
            recipe.tag.add(sample_tag(user=self.user))
            new_tag = sample_tag(user=self.user, name='Curry')

            payload = {'title': 'Chicken Tikka', 'tag': [new_tag.id]}
            url = detail_url(recipe.id)
            self.client.patch(url, payload)

            recipe.refresh_from_db()
            self.assertEqual(recipe.title, payload['title'])
            tags = recipe.tags.all()
            self.assertEqual(len(tags), 1)
            self.assertIn(new_tag, tags)

        def test_full_update_recipe(self):
            recipe = sample_recipe(user=self.user)
            recipe.tags.add(sample_tag(user=self.user))
            payload = {
                'title': 'Spaghetti carbonara',
                'time_minutes': 25,
                'price': 5.00
            }

            url = detail_url(recipe.id)
            self.client.post(url, payload)

            recipe.refresh_from_db()
            self.assertEqual(recipe.title, payload['title'])
            self.assertEqual(recipe.time_minutes, payload['time_minutes'])
            self.assertEqual(recipe.price, payload['time'])
            tags = recipe.tags.all()
            self.assertIn(len(tags), 0)


class RecipeImageUploadTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'tests@az.com',
            'tests123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_to_recipe(self):
        """Test uploading an image to recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
