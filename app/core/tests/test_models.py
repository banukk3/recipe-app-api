from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        """Test creating a new user with an email is successul"""
        email = 'test001@azgmail.com'
        password = 'Test001'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test the email for a new user is normalized"""
        email = 'test001@AZGMAIL.COM'
        user = get_user_model().objects.create_user(email, 'Test001')

        self.assertEqual(user.email, email.lower())

    def test_new_user_invalid_email(self):
        """Test creating user with no email raises error"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user(None, 'Test123')

    def test_create_super_user(self):
        """Test creating a new superuser"""
        user = get_user_model().objects.create_superuser(
            'test001@azgmail.com',
            'Test001'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
