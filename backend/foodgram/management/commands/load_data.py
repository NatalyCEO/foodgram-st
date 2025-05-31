import json
import os
from django.core.management.base import BaseCommand
from foodgram.models import Ingredient


class Command(BaseCommand):
    help = "Загружает ингредиенты из JSON-фикстуры"

    def handle(self, *args, **kwargs):
        file_path = os.path.join("data", "ingredients.json")

        try:
            with open(file_path, encoding="utf-8") as file:
                created_count = sum(
                    1 for _ in Ingredient.objects.bulk_create(
                        (Ingredient(**row) for row in json.load(file)),
                        ignore_conflicts=True
                    )
                )
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Файл {file_path} не найден!"))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(
                f"Ошибка чтения JSON в файле {file_path}"
            ))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка: {e}"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Данные загружены успешно! Добавлено {created_count} записей."
            )
        )
