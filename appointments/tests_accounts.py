from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


class AccountsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user_and_profile(self):
        url = reverse('account-register')
        resp = self.client.post(url, {'username': 'newuser', 'password': 'secret'}, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn('id', data)
        user = User.objects.get(username='newuser')
        # ensure profile exists
        self.assertTrue(hasattr(user, 'userprofile'))

    def test_profile_api_get_and_update(self):
        # register and authenticate
        url = reverse('account-register')
        resp = self.client.post(url, {'username': 'profuser', 'password': 'secret'}, format='json')
        self.assertEqual(resp.status_code, 201)
        # obtain token
        token_url = reverse('api-token-auth')
        resp = self.client.post(token_url, {'username': 'profuser', 'password': 'secret'})
        self.assertEqual(resp.status_code, 200)
        token = resp.json()['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        profile_url = '/api/accounts/profile/'
        # GET
        resp = self.client.get(profile_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['username'], 'profuser')

        # PUT update phone
        resp = self.client.put(profile_url, {'phone': '0123456789'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['phone'], '0123456789')
