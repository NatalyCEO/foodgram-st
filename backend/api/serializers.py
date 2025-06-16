from foodgram.models import (
    Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart, User, Subscription
)
from djoser.serializers import UserSerializer
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from drf_extra_fields.fields import Base64ImageField
from typing import Any, Dict, List, Optional
from foodgram.constants import (
    RECIPE_NAME_MAX_LENGTH,
    MIN_COOKING_TIME,
    MIN_AMOUNT
)


User = get_user_model()


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField(required=True)

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError(_('Avatar data is required'))
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj: User) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(
            user=request.user,
            author=obj
        ).exists()


class RecipesUserSerializer(UserProfileSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + ('recipes', 'recipes_count')
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj: User) -> List[Dict[str, Any]]:
        request = self.context.get('request')
        recipes = obj.recipes.all()
        
        recipes_limit = None
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
            if recipes_limit:
                try:
                    recipes_limit = int(recipes_limit)
                    recipes = recipes[:recipes_limit]
                except ValueError:
                    pass
        
        return SubscriptionRecipeSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj: User) -> int:
        return obj.recipes.count()


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('id',)


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    author = UserProfileSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(write_only=True)
    image_url = serializers.SerializerMethodField(source='image', read_only=True)
    name = serializers.CharField(max_length=RECIPE_NAME_MAX_LENGTH)
    text = serializers.CharField()
    cooking_time = serializers.IntegerField(min_value=MIN_COOKING_TIME)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'image_url', 'text', 'cooking_time'
        )
        read_only_fields = ('id', 'author')

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ingredients'] = RecipeIngredientReadSerializer(
            instance.recipe_ingredients.all(),
            many=True
        ).data
        # Rename image_url to image in the response
        if 'image_url' in data:
            data['image'] = data.pop('image_url')
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        if ingredients_data is not None:
            instance.ingredients.clear()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ingredients = data.get('ingredients', [])
        if not ingredients:
            raise ValidationError(_('Recipe must have at least one ingredient'))

        ingredient_ids = [item['id'].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(_('Ingredients must be unique'))

        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        if len(existing_ingredients) != len(ingredient_ids):
            raise ValidationError(_('One or more ingredients do not exist'))

        for ingredient in ingredients:
            if ingredient['amount'] < 1:
                raise ValidationError(_('Ingredient amount must be at least 1'))

        if not data.get('name'):
            raise ValidationError(_('Name is required'))

        if not data.get('text'):
            raise ValidationError(_('Text is required'))

        if not data.get('image'):
            raise ValidationError(_('Image is required'))

        if not data.get('cooking_time'):
            raise ValidationError(_('Cooking time is required'))

        return data


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('__all__',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image.url if instance.image else None
        return data


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'author')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'author'),
                message=_("You are already subscribed to this user")
            )
        ]

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                _("You cannot subscribe to yourself")
            )
        return data

    def create(self, validated_data):
        return Subscription.objects.create(**validated_data)

    def delete(self, user, author):
        try:
            subscription = Subscription.objects.get(user=user, author=author)
            subscription.delete()
        except Subscription.DoesNotExist:
            raise serializers.ValidationError(
                _("You are not subscribed to this user")
            )


class RecipeCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                message=_('Recipe is already in collection'),
                fields=('user', 'recipe'),
                queryset=Favorite.objects.all()
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self.context.get('collection_model')
        action = self.context.get('action')
        if model:
            self.Meta.model = model
            if action == 'delete':
                self.Meta.validators = []
            else:
                self.Meta.validators[0].queryset = model.objects.all()

    def validate(self, data):
        model = self.context.get('collection_model')
        if not model:
            raise serializers.ValidationError(
                'collection_model is required in context'
            )
        return data

    def delete(self, data):
        model = self.context.get('collection_model')
        if not model:
            raise serializers.ValidationError(
                'collection_model is required in context'
            )
        
        obj = model.objects.filter(
            user=data['user'],
            recipe=data['recipe']
        ).first()
        
        if not obj:
            raise serializers.ValidationError(
                _('Recipe is not in collection')
            )
            
        obj.delete()
        return True
