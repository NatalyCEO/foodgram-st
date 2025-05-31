from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
    Subscription,
    User,
)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.safestring import mark_safe



@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id', 'username', 'full_name', 'email', 'avatar_preview',
        'recipes_count', 'subscriptions_count', 'subscribers_count'
    )
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active')

    @admin.display(description="FIO")
    def full_name(self, user):
        return f"{user.first_name} {user.last_name}"
    
    @admin.display(description="Avatar")
    @mark_safe
    def avatar_preview(self, user):
        avatar_url = "/media/users/default_avatar.png"
        if user.avatar:
            avatar_url = user.avatar_url
        return(
            f'<img src="{avatar_url}" width="50" '
            'height="50" style="border-radius: 50 %;" >/'
        )
    
    @admin.display(description="Recipes")
    def recipes_count(self, user):
        return user.recipes.count()
    
    @admin.display(description="Count of subscriptions")
    def subscriptions_count(self, user):
        return user.followers.count()
    
    @admin.display(description="Count of followers")
    def subscribers_count(self, user):
        return user.authors.count()
    

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'cooking_time', 'author', 'favorites_count',
        'ingredients_list', 'image_preview'
    )
    list_filter = ('author', 'cooking_time', 'date_published')
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]

    @admin.display(description='Add to favorites')
    def favorites_count(self, recipe):
        return recipe.favorites.count()
    
    @admin.display(description='Products')
    @mark_safe
    def ingredients_list(self, recipe):
        return "<br>".join(
            f"{ingredient.name} ({ingredient.measurement_unit})"
            for ingredient in recipe.ingredients.all()
        )
    
    @admin.display(description="Photo")
    @mark_safe
    def image_preview(self, recipe):
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="80" height="50" />'
        return ""
    

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'recipes_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit',)

    @admin.display(description="Recipes")
    def recipes_count(self, ingredient):
        return ingredient.recipes.count()
        

@admin.register(Favorite, ShoppingCart)
class FavoriteAndSpoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_filter = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__username', 'author__username')