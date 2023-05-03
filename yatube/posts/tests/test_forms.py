import shutil
import tempfile

from posts.forms import PostForm
from posts.models import Post, User, Group, Comment
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
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
            text='Тестовый текст',
            group=cls.group,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(PostFormTests.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create(self):
        """Валидная форма создает запись"""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Текст нового поста',
            'group': PostFormTests.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        new_post = Post.objects.latest('id')
        self.assertEqual(new_post.author, self.user)
        self.assertEqual(new_post.group, PostFormTests.group)
        self.assertEqual(new_post.image, 'posts/small.gif')
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username':
                                     self.user.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_post_edit_form(self):
        """Валидная форма редактирует запись."""
        posts_count = Post.objects.count()
        some_group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug_2',
            description='Тестовое описание 2',
        )
        new_form_data = {
            'text': 'Текст измененного поста',
            'group': some_group.id
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=new_form_data,
            follow=True
        )
        edited_post = response.context['post']
        old_group_response = self.authorized_client_author.get(
            reverse('posts:group_list', args=(self.group.slug,))
        )
        new_group_response = self.authorized_client_author.get(
            reverse('posts:group_list', args=(some_group.slug,))
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(edited_post.text, new_form_data['text'])
        self.assertEqual(edited_post.group, some_group)
        self.assertEqual(
            old_group_response.context['page_obj'].paginator.count, 0)
        self.assertEqual(
            new_group_response.context['page_obj'].paginator.count, 1)

    def test_guest_client_cant_make_comment(self):
        """Не авторизованный пользователь не может создать комментарий.
        """
        comm_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
            'post': PostFormTests.post,
            'author': PostFormTests.user
        }
        response = self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': PostFormTests.post.id}),
            data=form_data,
            follow=True
        )
        self.assertFalse(
            Comment.objects.filter(
                text=form_data['text']
            ).exists()
        )
        self.assertEqual(Comment.objects.count(), comm_count)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/comment/')

    def test_auth_client_make_comment(self):
        """Авторизованный пользователь создает комментарий,
        который появляется н странице поста.
        """
        comm_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
            'post': PostFormTests.post,
            'author': PostFormTests.user
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostFormTests.post.id}
            ),
            data=form_data,
            follow=True
        )
        new_comm = Comment.objects.latest('id')
        expected = response.context['post']
        self.assertEqual(new_comm.text, form_data['text'])
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.post.id}))
        self.assertEqual(Post.objects.count(), comm_count + 1)
        # комм-й относится в правильному посту
        self.assertEqual(new_comm.post.id, expected.id)
