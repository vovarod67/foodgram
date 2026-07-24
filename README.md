# Foodgram

Foodgram — веб-приложение для публикации и поиска рецептов.

Пользователи могут создавать рецепты, добавлять их в избранное и список
покупок, подписываться на других авторов и скачивать сводный список
необходимых ингредиентов.

Проект доступен по адресу:

https://vovarod-foodgram.duckdns.org

## Возможности проекта

- регистрация и авторизация пользователей;
- создание, редактирование и удаление рецептов;
- фильтрация рецептов по тегам и авторам;
- добавление рецептов в избранное;
- добавление рецептов в список покупок;
- скачивание списка покупок в текстовом формате;
- подписка на авторов;
- загрузка пользовательского аватара;
- создание коротких ссылок на рецепты;
- REST API для взаимодействия с приложением.

## Развёртывание в Docker

### 1. Клонировать репозиторий

```bash
git clone https://github.com/vovarod67/foodgram.git
```

### 2. Создать файл `.env`

```bash
cd foodgram
```

В корневой директории проекта создайте файл `.env`:

```env
SECRET_KEY=your-secret-key
DEBUG=False

ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost

POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5432
```

При развёртывании на сервере добавьте домен в `ALLOWED_HOSTS` и
`CSRF_TRUSTED_ORIGINS`.

Пример:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,example.org
CSRF_TRUSTED_ORIGINS=http://example.org,https://example.org
```

### 3. Запустить контейнеры

```bash
docker compose -f docker-compose.production.yml up -d
```

В проекте используются сервисы:

- `db` — база данных PostgreSQL;
- `backend` — Django-приложение;
- `frontend` — подготовка файлов frontend-приложения;
- `gateway` — веб-сервер Nginx.

### 4. Выполнить миграции

```bash
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
```

### 5. Собрать статические файлы

```bash
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic --noinput
```

```bash
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```

### 6. Создать суперпользователя

```bash
docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser
```

После запуска проект будет доступен по адресу:

```text
http://localhost/
```

Административная панель:

```text
http://localhost/admin/
```

## Стек технологий

### Backend

- Python;
- Django;
- Django REST Framework;
- Djoser;
- django-filter;
- PostgreSQL;
- Gunicorn.

### Frontend

- JavaScript;
- React.

### Инфраструктура

- Docker;
- Docker Compose;
- Nginx;
- GitHub Actions.

## Наполнение БД данными

Теги можно создать через административную панель. Пользователей и рецепты можно создать через интерфейс приложения или административную панель:

```text
http://localhost/admin/
```

Базовый набор ингредиентов можно загрузить с помощью менеджмент-команды. Для локально запущенного проекта, находясь в директории foodgram/backend:
```bash
python manage.py load_ingredients
```

Для загрузки ингредиентов в проект на удалённом сервере, из директории foodgram выполните:
```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py load_ingredients
```

## Документация API

Локально документация: http://localhost/api/docs/

Документация развёрнутого проекта: https://vovarod-foodgram.duckdns.org/api/docs/

## Примеры запросов и ответов

### Регистрация пользователя

Запрос:

```http
POST /api/users/
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "username": "user",
  "first_name": "Иван",
  "last_name": "Иванов",
  "password": "example-password"
}
```

Ответ со статусом `201 Created`:

```json
{
  "email": "user@example.com",
  "id": 1,
  "username": "user",
  "first_name": "Иван",
  "last_name": "Иванов"
}
```

### Добавление рецепта в избранное

Запрос:

```http
POST /api/recipes/1/favorite/
Authorization: Token 0123456789abcdef0123456789abcdef01234567
```

Ответ со статусом `201 Created`:

```json
{
  "id": 1,
  "name": "Картофельное пюре",
  "image": "http://localhost/media/recipes/images/puree.jpg",
  "cooking_time": 30
}
```

### Получение короткой ссылки на рецепт

Запрос:

```http
GET /api/recipes/1/get-link/
```

Ответ со статусом `200 OK`:

```json
{
  "short-link": "http://localhost/s/a1b2c"
}
```

## Авторство

Родионов Владимир

https://github.com/vovarod67
