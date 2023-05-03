from users.forms import CreationForm
from posts.models import User
from django.test import Client, TestCase
from django.urls import reverse


class UserFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.form = CreationForm()

    def setUp(self):
        self.guest_client = Client()

    def test_user_create(self):
        """Валидная форма создает пользователя."""
        users_count = User.objects.count()
        form_data = {
            'first_name': 'Somedody',
            'last_name': 'ToTest',
            'username': 'tester',
            'email': 'tester@test.com',
            'password1': 'Somepessword',
            'password2': 'Somepessword',
        }
        response = self.guest_client.post(
            reverse('users:signup'),
            data=form_data,
            follow=True
        )
        new_user = User.objects.latest('id')
        self.assertEqual(new_user.username, form_data['username'])
        self.assertRedirects(response, reverse('posts:index'))
        self.assertEqual(User.objects.count(), users_count + 1)
