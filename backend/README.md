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