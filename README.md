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
## Настройка GitHub Actions

Для настройки автоматического деплоя через GitHub Actions необходимо добавить следующие секреты в настройках репозитория (Settings -> Secrets and variables -> Actions):

1. `DOCKER_USERNAME` - имя пользователя на Docker Hub
2. `DOCKER_PASSWORD` - пароль от Docker Hub
3. `HOST` - IP-адрес сервера
4. `USERNAME` - имя пользователя для SSH-подключения
5. `SSH_KEY` - приватный SSH-ключ
6. `PROJECT_PATH` - путь к проекту на сервере

### Как добавить секреты:

1. Перейдите в настройки репозитория на GitHub
2. Выберите "Secrets and variables" -> "Actions"
3. Нажмите "New repository secret"
4. Добавьте каждый секрет с соответствующим значением

### Как получить SSH-ключ:

1. На локальном компьютере выполните:
   ```bash
   cat ~/.ssh/id_rsa
   ```
2. Скопируйте вывод команды (включая строки BEGIN и END)
3. Добавьте как секрет `SSH_KEY`

---

**Статус проекта** в разработке
**Автор проекта** Разживина Наталья

