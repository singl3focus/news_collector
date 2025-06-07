#!/bin/bash

# Базовый URL API
BASE_URL="http://localhost:8001"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔍 Testing Telegram Fetcher API endpoints..."

# Тест 1: Получение списка каналов
echo -e "\n${GREEN}Test 1: Get channels list${NC}"
curl -s "${BASE_URL}/api/channels" | jq '.'

# Тест 2: Добавление нового канала
echo -e "\n${GREEN}Test 2: Add new channel${NC}"
curl -s -X POST "${BASE_URL}/api/add_channel" \
  -H "Content-Type: application/json" \
  -d '{"link": "https://t.me/durov"}' | jq '.'

# Тест 3: Получение ID канала
echo -e "\n${GREEN}Test 3: Get channel ID${NC}"
curl -s "${BASE_URL}/api/channel_id/durov" | jq '.'

# Тест 4: Удаление канала
echo -e "\n${GREEN}Test 4: Delete channel${NC}"
curl -s -X DELETE "${BASE_URL}/api/channels/durov" | jq '.'

# Тест 5: Проверка rate limiting (множественные запросы)
echo -e "\n${GREEN}Test 5: Rate limiting test${NC}"
for i in {1..6}; do
  echo "Request $i:"
  curl -s "${BASE_URL}/api/channels" | jq '.'
  sleep 0.5
done

echo -e "\n${GREEN}All tests completed!${NC}" 