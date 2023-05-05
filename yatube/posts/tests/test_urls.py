from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from http import HTTPStatus
from ..models import Post, User, Group


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            id=1,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostURLTests.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_urls_for_all_users(self):
        """Страницы доступны любому пользователю."""
        urls = [
            '/',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_only_for_author(self):
        """Страница /edit/ доступна только автору."""
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        users = {
            self.guest_client: HTTPStatus.FOUND,
            self.authorized_client_author: HTTPStatus.OK,
            self.authorized_client: HTTPStatus.FOUND,
        }
        for key, value in users.items():
            with self.subTest(key=key):
                response = key.get(url)
                self.assertEqual(response.status_code, value)

    def test_urls_only_for_authorised(self):
        """Страница /create/ доступна только авторизованному пользователю."""
        url = '/create/'
        users = {
            self.guest_client: HTTPStatus.FOUND,
            self.authorized_client: HTTPStatus.OK,
        }
        for key, value in users.items():
            with self.subTest(key=key):
                response = key.get(url)
                self.assertEqual(response.status_code, value)

    def test_anonimous_is_redirected(self):
        """Анонимный пользователь перенаправлен со страницы /create/."""
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_auth_user_is_redirected_from_edit(self):
        """Авторизованный пользователь перенаправлен со страницы /edit/."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertRedirects(response, reverse('posts:post_detail',
                                               kwargs={'post_id':
                                                       self.post.id}))

    def test_guest_user_is_redirected_from_edit(self):
        """Анонимный пользователь перенаправлен со страницы /edit/."""
        response = self.guest_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{self.post.id}/edit/')

    def test_unexisting_page(self):
        """Несуществующая страница не найдена.
           Использован кастомный шаблон."""
        response = self.guest_client.get('/some_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client_author.get(address)
                self.assertTemplateUsed(response, template)
