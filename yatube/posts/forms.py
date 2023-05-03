from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {'text': 'Текст публикации',
                  'group': 'Группа',
                  'image': 'Изображение',
                  }
        help_texts = {
            'group': 'Группа, к которой будет относиться пост',
            'text': 'Tекст нового поста',
            'image': 'Добавьте изображение'
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст комментария'
        }
