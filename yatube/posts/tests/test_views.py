import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.urls import reverse
from django.conf import settings
from django import forms

from posts.models import Post, User, Group, Follow

TEST_POSTS_NUM = 13

IMG = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B')

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
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
            text='Тестовый текст длиной не менее 15 символов',
            group=cls.group,
            image=SimpleUploadedFile(name='image.jpg',
                                     content=IMG,
                                     content_type='image/jpg'))

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_pages_show_correct_context(self):
        """Страницы корректно отображают пост."""
        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username':
                                             PostPagesTests.user.username}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                first_object = response.context['page_obj'][0]
                post_author = first_object.author
                post_text = first_object.text
                post_pub_date = first_object.pub_date
                post_image = first_object.image
                self.assertEqual(post_author, PostPagesTests.user)
                self.assertEqual(post_text, PostPagesTests.post.text)
                self.assertEqual(post_pub_date, PostPagesTests.post.pub_date)
                self.assertEqual(post_image, PostPagesTests.post.image)

    def test__group_posts_page_shows_correct_context(self):
        """Шаблон страницы group_posts сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}))
        group_test = response.context['group']
        self.assertEqual(group_test.title, PostPagesTests.group.title)
        self.assertEqual(group_test.slug, PostPagesTests.group.slug)
        self.assertEqual(group_test.description,
                         PostPagesTests.group.description)

    def test_group_page_contains_group_records(self):
        """На странице group оттображены посты группы."""
        response = self.guest_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}))
        group_post = response.context['page_obj'][0]
        expected = response.context['group']
        self.assertEqual(str(group_post.group), expected.title)

    def test__profile_page_shows_correct_context(self):
        """Шаблон страницы profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile',
                    kwargs={'username': PostPagesTests.user.username}))
        author_test = response.context['author']
        self.assertEqual(str(author_test.username),
                         PostPagesTests.user.username)

    def test_profile_page_contains_auth_records(self):
        """На странице profile отображены посты автора."""
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username':
                                     PostPagesTests.user.username}))
        auth_post = response.context['page_obj'][0]
        expected = response.context['author']
        self.assertEqual(str(auth_post.author), expected.username)

    def test_post_detail_shows_correct_content(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        test_post = response.context['post']
        self.assertEqual(test_post.author, PostPagesTests.user)
        self.assertEqual(test_post.text, PostPagesTests.post.text)
        self.assertEqual(test_post.pub_date, PostPagesTests.post.pub_date)
        self.assertEqual(test_post.group, PostPagesTests.group)
        self.assertEqual(test_post.image, PostPagesTests.post.image)

    def test_create_post_page_contains_correct_form(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_page_contains_correct_form(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_new_post(self):
        """Проверяем отображение нового поста."""
        urls = [
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': PostPagesTests.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': PostPagesTests.post.author}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                posts = response.context['page_obj']
                self.assertIn(PostPagesTests.post, posts)

    def test_new_post_not_in_wrong_group(self):
        """Созданный пост не попал в группу,
        для которой не был предназначен.
        """
        some_group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug_2',
            description='Тестовое описание 2',
        )
        response = self.authorized_client.get(
            reverse("posts:group_list", kwargs={"slug":
                                                some_group.slug}))
        some_group_posts = response.context['page_obj']
        self.assertNotIn(PostPagesTests.post, some_group_posts)

    def test_cache_index_page(self):
        """Кеширование работает для главной страницы."""
        response = self.authorized_client.get(reverse('posts:index'))
        content_old = response.content
        first_post = response.context['page_obj'][0]
        first_post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        content_new = response.content
        self.assertEqual(content_old, content_new)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        content_after_clear = response.content
        self.assertNotEqual(
            content_old,
            content_after_clear
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.list_post = [
            Post(
                author=cls.user,
                text=f'Тестовый пост {post_num}',
                group=cls.group,
            )
            for post_num in range(TEST_POSTS_NUM)
        ]
        Post.objects.bulk_create(cls.list_post)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_main_page_contains_ten_records(self):
        """Проверяем, что на страницах выводится по 10 постов"""
        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': PaginatorViewsTest.user.username}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(len(response.context['page_obj']),
                                 settings.POSTS_SHOWN)


class FollowViewsTests(TestCase):
    def setUp(self):
        self.auth_follower = Client()
        self.auth_following = Client()
        self.auth_other_user = Client()
        self.user_follower = User.objects.create_user(username='follower')
        self.user_following = User.objects.create_user(username='following')
        self.user_other = User.objects.create_user(username='other')
        self.post = Post.objects.create(
            author=self.user_following,
            text='Тестовый текст'
        )
        self.auth_follower.force_login(self.user_follower)
        self.auth_other_user.force_login(self.user_other)

    def test_auth_user_can_follow_unfollow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок.
        """
        followers_count = Follow.objects.count()
        # добавление подписки
        self.auth_follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_following.username}))
        self.assertEqual(Follow.objects.all().count(), followers_count + 1)
        self.assertTrue(Follow.objects.filter(
            author=self.user_following, user=self.user_follower).exists())
        # удаление подписки
        self.auth_follower.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_following.username}))
        self.assertEqual(Follow.objects.all().count(), followers_count)
        self.assertFalse(Follow.objects.filter(
            author=self.user_following, user=self.user_follower).exists())

    def test_new_post_on_correct_page(self):
        """Новая запись пользователя появляется в
        ленте тех, кто на него подписан, и не появляется
        у других пользователей.
        """
        self.auth_follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_following.username}))
        # появляется на странице подписчика
        response = self.auth_follower.get('/follow/')
        posts_followed = response.context['page_obj']
        self.assertIn(self.post, posts_followed)
        # не появляется у другого пользователя
        response = self.auth_other_user.get('/follow/')
        posts_followed = response.context['page_obj']
        self.assertNotIn(self.post, posts_followed)
