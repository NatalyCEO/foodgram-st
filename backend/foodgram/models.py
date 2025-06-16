from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator, RegexValidator
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from typing import Optional, List
from django.utils.translation import gettext_lazy as _
from .constants import (
    USERNAME_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    FIRST_NAME_MAX_LENGTH,
    LAST_NAME_MAX_LENGTH,
    INGREDIENT_NAME_MAX_LENGTH,
    MEASUREMENT_UNIT_MAX_LENGTH,
    RECIPE_NAME_MAX_LENGTH,
    MIN_COOKING_TIME,
    MIN_AMOUNT,
    NAME_REGEX,
    NAME_VALIDATION_MSG,
    MEASUREMENT_UNIT_VALIDATION_MSG
)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    username = models.CharField(
        _('Username'),
        max_length=USERNAME_MAX_LENGTH,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    )
    email = models.EmailField(
        _('Email address'),
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        help_text=_('Required. Must be a valid email address.')
    )
    first_name = models.CharField(
        _('First name'),
        max_length=FIRST_NAME_MAX_LENGTH,
        validators=[
            RegexValidator(
                regex=NAME_REGEX,
                message=_(NAME_VALIDATION_MSG)
            )
        ]
    )
    last_name = models.CharField(
        _('Last name'),
        max_length=LAST_NAME_MAX_LENGTH,
        validators=[
            RegexValidator(
                regex=NAME_REGEX,
                message=_(NAME_VALIDATION_MSG)
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


class Ingredient(TimeStampedModel):
    name = models.CharField(
        max_length=INGREDIENT_NAME_MAX_LENGTH,
        verbose_name=_('Name'),
        validators=[
            RegexValidator(
                regex=NAME_REGEX,
                message=_(NAME_VALIDATION_MSG)
            )
        ]
    )
    measurement_unit = models.CharField(
        max_length=MEASUREMENT_UNIT_MAX_LENGTH,
        verbose_name=_('Measurement Unit'),
        validators=[
            RegexValidator(
                regex=NAME_REGEX,
                message=_(MEASUREMENT_UNIT_VALIDATION_MSG)
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


class Recipe(TimeStampedModel):
    name = models.CharField(
        max_length=RECIPE_NAME_MAX_LENGTH,
        verbose_name=_('Name'),
        validators=[
            RegexValidator(
                regex=NAME_REGEX,
                message=_(NAME_VALIDATION_MSG)
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
        validators=[MinValueValidator(MIN_COOKING_TIME)],
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
    amount = models.PositiveSmallIntegerField(
        verbose_name=_('Amount'),
        validators=[MinValueValidator(MIN_AMOUNT)],
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


class RecipeCollection(TimeStampedModel):
    user = models.ForeignKey(
        User,
        verbose_name=_('User'),
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name=_('Recipe'),
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        ordering = ('-created_at',)


class Favorite(RecipeCollection):
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

    class Meta(RecipeCollection.Meta):
        verbose_name = _('Favorite')
        verbose_name_plural = _('Favorites')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username} has {self.recipe.name} in favorites'


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


class ShoppingCart(RecipeCollection):
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

    class Meta(RecipeCollection.Meta):
        verbose_name = _('Shopping Cart')
        verbose_name_plural = _('Shopping Carts')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username} has {self.recipe.name} in shopping cart'

