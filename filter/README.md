

```bash
pip install pipreqs
pipreqs . --force
```

- Для запуска Redis отдельно в Docker контейнере:
```bash
docker run --name redis -d -p 6379:6379 redis
```