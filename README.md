# **Foodgram**

**Foodgram** — это веб-приложение для обмена рецептами, подписки на любимых авторов и формирования списка покупок.
Зарегистрированные пользователи могут публиковать рецепты, добавлять их в избранное и получать автоматически сформированный список продуктов для покупки.

---

##  **Как запустить проект?**

### ** 1. Клонируйте репозиторий**
```sh
git clone https://github.com/NatalyCEO/foodgram-st.git
cd foodgram-st/infra
```

### ** 2. Создайте файл `.env`**
В корне директории `infra/` создайте файл `.env` по примеру `.env.example`

### ** 3. Запустите Docker**
```sh
docker-compose up -d --build
```

### ** 4. Выполните миграции**
```sh
docker-compose exec backend python manage.py migrate
```

### ** 4. Загрузите ингредиенты**
```sh
docker-compose exec backend python manage.py load_data
```

### ** 5. Загрузите тестовые данные**
```sh
docker-compose exec backend python manage.py load_test_data
```

Приложение будет доступно по адресу **[http://localhost/](http://localhost/)**


## **Пользователи**
- **Admin** email:admin@example.com пароль: testpass123
- **Master Chef** email:chef@example.com пароль: testpass123
- **Food Lover** email:foodie@example.com пароль: testpass123

---

## **Технологии**
- **Backend:** Django, Django REST Framework, PostgreSQL
- **Frontend:** React
- **Развертывание:** Docker, Gunicorn, Nginx

---

**Статус проекта** в разработке
**Автор проекта** Разживина Наталья