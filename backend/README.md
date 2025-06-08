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
curl -X POST "http://localhost:9080/register?username=alice"
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
curl -X POST "http://localhost:9080/login?username=alice"
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
- channel_name (int): ID канала для подписки
- Заголовок Authorization: Токен доступа

Пример запроса:

```bash
curl -X POST -H "Authorization: kL8sZ...qW2" "http://localhost:9080/users/me/channels?channel_name=example_channel"
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
```DELETE /users/{user_id}/channels```

Параметры:
- channel_name (int): ID канала для отписки
- Заголовок Authorization: Токен доступа

Пример запроса:
```bash
curl -X DELETE -H "Authorization: kL8sZ...qW2" http://localhost:9080/users/me/channels?channel_name=example_channel
```

Успешный ответ (200 OK):
```json
{
  "status": "removed",
  "channel_id": 123
}
```

5. Удаление всех каналов из подписок
```DELETE /user/channels/all```

Параметры:
- Заголовок Authorization: Токен доступа

Пример запроса:
```bash
curl -X DELETE -H "Authorization: kL8sZ...qW2" http://localhost:9080/user/channels/all
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

## WSServer
```json
{
  "text": "Компания Apple представила новый iPhone 15 с революционными функциями",
  "tonality": 1,
  "trend": 1,
  "volatility": 1,
  "channel_id": "133113113",
  "channel_title": "Технологические новости",
  "channel_url": "Ссылка на канал",
  "timestamp": 1691500000
}
```

Разъяснение полей:
- ```text (string)```: Текст новостного поста.
Пример: "Акции компании выросли на 5% сегодня"

- ```tonality (int)```: Тональность новости
    1 - позитивная/хорошая новость
    -1 - негативная/плохая новость
Пример: 1 (для хорошей новости)

- ```trend (int)```: Направление тренда
    1 - восходящий тренд (улучшение/рост)
    -1 - нисходящий тренд (ухудшение/падение)
Пример: 1 (для растущего тренда)

- ```volatility (int)```: Волатильность
    1 - высокая волатильность
    0 - низкая волатильность
Пример: 0 (для стабильной новости)

- ```channel_id (string)```: Уникальный идентификатор канала
Пример: "111134141"

- ```channel_title (string)```: Название канала/источника
Пример: "Финансовые новости"

- ```timestamp (int, optional)```: Временная метка в Unix time (по умолчанию 0)
Пример: 1691500000 (2023-08-08 12:06:40 UTC)
