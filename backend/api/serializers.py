from foodgram.models import (
    Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart, User, Subscription, Tag
)
from djoser.serializers import UserSerializer
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from drf_extra_fields.fields import Base64ImageField
from typing import Any, Dict, List, Optional


User = get_user_model()


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


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    author = UserProfileSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False,
        write_only=True
    )
    name = serializers.CharField(max_length=200)
    text = serializers.CharField()
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time', 'tags'
        )
        read_only_fields = ('id', 'author')

    def to_representation(self, instance):
        data = {
            'id': instance.id,
            'author': UserProfileSerializer(instance.author, context=self.context).data,
            'ingredients': [],
            'is_favorited': self.get_is_favorited(instance),
            'is_in_shopping_cart': self.get_is_in_shopping_cart(instance),
            'name': instance.name,
            'image': instance.image.url if instance.image else None,
            'text': instance.text,
            'cooking_time': instance.cooking_time
        }
        
        for ri in instance.recipe_ingredients.select_related('ingredient').all():
            data['ingredients'].append({
                'id': ri.ingredient.id,
                'name': ri.ingredient.name,
                'measurement_unit': ri.ingredient.measurement_unit,
                'amount': ri.amount
            })
            
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags', None)
        recipe = Recipe.objects.create(**validated_data)
        if tags_data is not None:
            recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        if ingredients_data is not None:
            instance.ingredients.clear()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
        if tags_data is not None:
            instance.tags.set(tags_data)
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
