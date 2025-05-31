from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator, RegexValidator
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from typing import Optional, List
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    username = models.CharField(
        _('Username'),
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    )
    email = models.EmailField(
        _('Email address'),
        max_length=254,
        unique=True,
        help_text=_('Required. Must be a valid email address.')
    )
    first_name = models.CharField(
        _('First name'),
        max_length=150,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Zа-яА-ЯёЁ\s-]+$',
                message=_('First name can only contain letters, spaces and hyphens')
            )
        ]
    )
    last_name = models.CharField(
        _('Last name'),
        max_length=150,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Zа-яА-ЯёЁ\s-]+$',
                message=_('Last name can only contain letters, spaces and hyphens')
            )
        ]
    )
    avatar = models.ImageField(
        _('Avatar'),
        upload_to='users/',
        null=True,
        blank=True,
        default='users/default_avatar.png'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('username',)
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                name='unique_email'
            )
        ]

    def __str__(self) -> str:
        return self.username

    def clean(self) -> None:
        super().clean()
        if self.email:
            self.email = self.email.lower()
        if self.username:
            self.username = self.username.lower()


class Ingredient(TimeStampedModel):
    name = models.CharField(
        max_length=128,
        verbose_name=_('Name'),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Zа-яА-ЯёЁ\s-]+$',
                message=_('Name can only contain letters, spaces and hyphens')
            )
        ]
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name=_('Measurement Unit'),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Zа-яА-ЯёЁ\s-]+$',
                message=_('Measurement unit can only contain letters, spaces and hyphens')
            )
        ]
    )

    class Meta:
        verbose_name = _('Ingredient')
        verbose_name_plural = _('Ingredients')
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.measurement_unit})"

    def clean(self) -> None:
        super().clean()
        if self.name:
            self.name = self.name.strip().lower()
        if self.measurement_unit:
            self.measurement_unit = self.measurement_unit.strip().lower()



class Recipe(TimeStampedModel):
    name = models.CharField(
        max_length=256,
        verbose_name=_('Name'),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Zа-яА-ЯёЁ\s-]+$',
                message=_('Name can only contain letters, spaces and hyphens')
            )
        ]
    )
    text = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Recipe description and instructions')
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name=_('Ingredients'),
        related_name='recipes',
        through='RecipeIngredient',
    )
    tags = models.ManyToManyField(
        'Tag',
        verbose_name=_('Tags'),
        related_name='recipes',
    )
    author = models.ForeignKey(
        User,
        verbose_name=_('Author'),
        related_name='recipes',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        verbose_name=_('Image'),
        upload_to='recipes/images/',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name=_('Cooking Time (minutes)'),
        validators=[MinValueValidator(1)],
        help_text=_('Cooking time in minutes')
    )
    date_published = models.DateTimeField(
        default=now,
        verbose_name=_('Publication Date')
    )

    class Meta:
        verbose_name = _('Recipe')
        verbose_name_plural = _('Recipes')
        ordering = ['-date_published']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'author'],
                name='unique_recipe_per_author'
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.name:
            self.name = self.name.strip()
        if self.text:
            self.text = self.text.strip()


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name=_('Recipe'),
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name=_('Ingredient'),
        related_name='ingredient_recipes',
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        verbose_name=_('Amount'),
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = _('Recipe Ingredient')
        verbose_name_plural = _('Recipe Ingredients')
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self) -> str:
        return f'{self.amount} {self.ingredient.name} in {self.recipe.name}'


class Favorite(TimeStampedModel):
    user = models.ForeignKey(
        User,
        verbose_name=_('User'),
        related_name='favorites',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name=_('Recipe'),
        related_name='favorites',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _('Favorite')
        verbose_name_plural = _('Favorites')
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username} has {self.recipe.name} in favorites'

    def clean(self) -> None:
        super().clean()
        if self.user == self.recipe.author:
            raise ValidationError(_('You cannot favorite your own recipe'))


class Subscription(TimeStampedModel):
    user = models.ForeignKey(
        User,
        related_name='followers',
        on_delete=models.CASCADE,
        verbose_name=_('Follower'),
    )
    author = models.ForeignKey(
        User,
        related_name='authors',
        on_delete=models.CASCADE,
        verbose_name=_('Author'),
    )

    class Meta:
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username} follows {self.author.username}'

    def clean(self) -> None:
        super().clean()
        if self.user == self.author:
            raise ValidationError(_('You cannot subscribe to yourself'))


class ShoppingCart(TimeStampedModel):
    user = models.ForeignKey(
        User,
        verbose_name=_('User'),
        related_name='shopping_carts',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name=_('Recipe'),
        related_name='shopping_carts',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _('Shopping Cart')
        verbose_name_plural = _('Shopping Carts')
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username} has {self.recipe.name} in shopping cart'


class Tag(models.Model):
    name = models.CharField(
        max_length=128,
        verbose_name=_('Name'),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Zа-яА-ЯёЁ\s-]+$',
                message=_('Name can only contain letters, spaces and hyphens')
            )
        ]
    )
    color = models.CharField(
        max_length=7,
        verbose_name=_('Color'),
        validators=[
            RegexValidator(
                regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message=_('Color must be a valid hex color code')
            )
        ]
    )
    slug = models.SlugField(
        max_length=128,
        unique=True,
        verbose_name=_('Slug')
    )

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ('name',)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.name:
            self.name = self.name.strip().lower()
        if self.slug:
            self.slug = self.slug.strip().lower()

