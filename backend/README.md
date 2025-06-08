# News collector

- Создание виртуального окружения:
```bash
python -m venv venv
.\venv\Scripts\activate
```

- Получение зависимостей проекта (requirements.txt):
```bash
pip install pipreqs
pipreqs . --force
```

- Для запуска Redis отдельно в Docker контейнере:
```bash
docker run --name redis -d -p 6379:6379 redis
```

## REST Server

Этот модуль реализует RESTful API сервер с использованием FastAPI, предоставляющий функционал для:
- Регистрации и аутентификации пользователей
- Управления подписками пользователей на каналы
- Хранения данных в Redis

### API Endpoints
1. Регистрация нового пользователя
```POST /register```

Параметры:
- username (string): Имя пользователя

Пример запроса:
```bash
curl -X POST -d "username=alice" http://localhost:9080/register
```

Успешный ответ (200 OK):
```json
{
  "status": "success",
  "token": "JfPyRj...HkU"
}
```

Ошибки:
```400 Bad Request: Ошибка при создании пользователя```

2. Аутентификация пользователя
```POST /login```

Параметры:
- username (string): Имя пользователя

Пример запроса:
```bash
curl -X POST -d "username=alice" http://localhost:9080/login
```

Успешный ответ (200 OK):
```json
{
  "status": "success",
  "token": "kL8sZ...qW2"
}
```

Ошибки:
- 401 Unauthorized: Неверные учетные данные

3. Добавление канала в подписки
```POST /users/{user_id}/channels```

Параметры:
- channel_id (int): ID канала для подписки
- Заголовок Authorization: Токен доступа

Пример запроса:

```bash
curl -X POST -H "Authorization: kL8sZ...qW2" -d "channel_id=123" http://localhost:9080/users/me/channels
```

Успешный ответ (200 OK):
```json
{
  "status": "added",
  "channel_id": 123
}
```

Особенности:
user_id в пути игнорируется - используется ID из токена
Пользователь автоматически подписывается на канал 0 при регистрации

4. Удаление канала из подписок
```DELETE /users/{user_id}/channels/{channel_id}```

Параметры:
- channel_id (int): ID канала для отписки
- Заголовок Authorization: Токен доступа

Пример запроса:
```bash
curl -X DELETE -H "Authorization: kL8sZ...qW2" http://localhost:9080/users/me/channels/123
```

Успешный ответ (200 OK):
```json
{
  "status": "removed",
  "channel_id": 123
}
```

### Аутентификация
Все защищенные endpoints используют схему аутентификации:

Заголовок: Authorization: <token>

Токен выдается при регистрации и логине

Каждый логин генерирует новый токен (старые остаются валидными)

### Структура данных в Redis
- Данные пользователя:
```redis
user:<user_id> = {
  "id": "user_3a7b...",
  "username": "alice",
  "tokens": ["token1", "token2"]
}
```

- Соответствие токен→ID пользователя:
```redis
auth:token:<token> = <user_id>
```

- Подписки пользователя (Set):
```redis
user:channels:<user_id> = {0, 123, 456}
```

Обработка ошибок
401 Unauthorized: Невалидный или отсутствующий токен
400 Bad Request: Ошибки валидации входных данных
500 Internal Server Error: Необработанные исключения