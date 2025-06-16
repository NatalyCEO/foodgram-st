from foodgram.models import Recipe, RecipeIngredient, Favorite, ShoppingCart, Subscription
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files import File
import os
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Load test data into the database'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting to load test data...')
        
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        self.stdout.write(self.style.SUCCESS('Created admin user'))

        chef = User.objects.create_user(
            username='chef',
            email='chef@example.com',
            password='testpass123',
            first_name='Master',
            last_name='Chef'
        )
        self.stdout.write(self.style.SUCCESS('Created chef user'))

        foodie = User.objects.create_user(
            username='foodie',
            email='foodie@example.com',
            password='testpass123',
            first_name='Food',
            last_name='Lover'
        )
        self.stdout.write(self.style.SUCCESS('Created foodie user'))

        self.stdout.write('Creating recipes...')
        
        carbonara = Recipe.objects.create(
            name='Паста Карбонара',
            text='Классическая итальянская паста с беконом и сливочным соусом',
            author=chef,
            cooking_time=30
        )
        
        carbonara_image_path = os.path.join(settings.MEDIA_ROOT, 'recipes/images/carbonara.jpg')
        self.stdout.write(f'Looking for image at: {carbonara_image_path}')
        if os.path.exists(carbonara_image_path):
            self.stdout.write('Found carbonara image, attaching it...')
            with open(carbonara_image_path, 'rb') as f:
                carbonara.image.save('carbonara.jpg', File(f), save=True)
            self.stdout.write('Successfully attached carbonara image')
        else:
            self.stdout.write(self.style.WARNING(f'Image not found at {carbonara_image_path}'))
        self.stdout.write(self.style.SUCCESS('Created Carbonara recipe'))

        caesar = Recipe.objects.create(
            name='Салат Цезарь',
            text='Свежий салат с куриной грудкой и сухариками',
            author=foodie,
            cooking_time=20
        )
                
        caesar_image_path = os.path.join(settings.MEDIA_ROOT, 'recipes/images/caesar.jpg')
        self.stdout.write(f'Looking for image at: {caesar_image_path}')
        if os.path.exists(caesar_image_path):
            self.stdout.write('Found caesar image, attaching it...')
            with open(caesar_image_path, 'rb') as f:
                caesar.image.save('caesar.jpg', File(f), save=True)
            self.stdout.write('Successfully attached caesar image')
        else:
            self.stdout.write(self.style.WARNING(f'Image not found at {caesar_image_path}'))
        self.stdout.write(self.style.SUCCESS('Created Caesar salad recipe'))

        self.stdout.write('Adding ingredients to recipes...')
        
        RecipeIngredient.objects.create(
            recipe=carbonara,
            ingredient_id=1211,  
            amount=200
        )
        RecipeIngredient.objects.create(
            recipe=carbonara,
            ingredient_id=120,  
            amount=100
        )
        RecipeIngredient.objects.create(
            recipe=carbonara,
            ingredient_id=1749,  
            amount=100
        )
        RecipeIngredient.objects.create(
            recipe=carbonara,
            ingredient_id=1633,  
            amount=200
        )
        RecipeIngredient.objects.create(
            recipe=caesar,
            ingredient_id=780,  
            amount=150
        )
        RecipeIngredient.objects.create(
            recipe=caesar,
            ingredient_id=1739,  
            amount=50
        )
        RecipeIngredient.objects.create(
            recipe=caesar,
            ingredient_id=1353,  
            amount=150
        )
        RecipeIngredient.objects.create(
            recipe=caesar,
            ingredient_id=1749,  
            amount=100
        )
        self.stdout.write(self.style.SUCCESS('Added ingredients to recipes'))

        self.stdout.write('Creating relationships...')
        
        Favorite.objects.create(user=foodie, recipe=carbonara)
        ShoppingCart.objects.create(user=foodie, recipe=carbonara)
        Subscription.objects.create(user=foodie, author=chef)
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded test data')) 