# BugTracker API

REST API для системы отслеживания ошибок, построенный на FastAPI с использованием Apache Cassandra в качестве базы данных.

## Функциональность

- ✅ Управление пользователями
- ✅ Управление проектами
- ✅ Создание и управление issues (задачами/ошибками)
- ✅ Комментирование issues
- ✅ История изменений issues
- ✅ Фильтрация issues по статусу, приоритету, назначенному пользователю, компоненту
- ✅ Статистика по проектам
- ✅ Администрирование (очистка и заполнение тестовыми данными)

## Технологии

- **Python 3.8+** (<= 3.11 во избежание ошибок, связанных с подключением драйвера)
- **FastAPI** - веб-фреймворк
- **Apache Cassandra** - распределенная NoSQL база данных
- **Uvicorn** - ASGI сервер
- **Pydantic** - валидация данных

## Установка и запуск

### 0. Предварительные требования

- Python 3.8-3.11
- Apache Cassandra (локально или Docker)
- Git

### 1. Клонирование репозитория

```bash
git clone <url-репозитория>
cd bugtracker
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Запуск Cassandra

#### Использование Docker (рекомендуется)

**Для Windows с WSL:**

```bash
# В WSL терминале
docker run --name some-cassandra -p 9042:9042 -d cassandra:latest
```

Убедитесь, что порт проброшен правильно:
```bash
docker ps
# Должно быть видно: 0.0.0.0:9042->9042/tcp
```

**Настройка подключения:**

Приложение по умолчанию подключается к `127.0.0.1:9042`. Если нужно изменить настройки, используйте переменные окружения:

```bash
# Windows PowerShell
$env:CASSANDRA_HOSTS="127.0.0.1"
$env:CASSANDRA_PORT="9042"
$env:CASSANDRA_KEYSPACE="issue_tracker"

# Linux/Mac
export CASSANDRA_HOSTS=127.0.0.1
export CASSANDRA_PORT=9042
export CASSANDRA_KEYSPACE=issue_tracker
```

**Если подключение не работает:**

1. Проверьте, что Cassandra запущена: `docker ps`
2. Проверьте доступность порта: `telnet 127.0.0.1 9042` (или используйте `Test-NetConnection -ComputerName 127.0.0.1 -Port 9042` в PowerShell)
3. Если используете WSL, убедитесь, что порт проброшен: `0.0.0.0:9042->9042/tcp`
4. Попробуйте использовать `localhost` вместо `127.0.0.1` или наоборот

#### Локальная установка

```bash
# Запуск Cassandra сервиса
sudo service cassandra start
```

### 4. Запуск приложения
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
````
Приложение будет доступно по адресу: http://localhost:8000

## 5. Документация API
После запуска приложения доступна автоматическая документация:

- Swagger UI: http://localhost:8000/docs

## Примеры запросов через Postman

### Администрирование
1. Очистка базы данных
```
POST /admin/clear-data
```
2. Заполнение тестовыми данными
```
POST /admin/seed-data
```

3. Сброс базы данных (очистка + заполнение)
```
POST /admin/reset-data
```
Пользователи
4. Создание пользователя
```
POST /users/

{
    "username": "john_doe",
    "email": "john@example.com",
    "role": "developer"
}
```
5. Получение списка пользователей
```
GET /users/?skip=0&limit=100
```
Проекты
6. Создание проекта
```
POST /projects/

{
    "name": "Новый проект",
    "description": "Описание нового проекта"
}
```
Issues
7. Создание issue
```
POST /issues/

{
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Новая ошибка",
    "description": "Подробное описание ошибки",
    "status": "open",
    "priority": "high",
    "assignee_id": "123e4567-e89b-12d3-a456-426614174001",
    "reporter_id": "123e4567-e89b-12d3-a456-426614174002",
    "component": "backend"
}
```
8. Получение issue по ID

```
GET /issues/123e4567-e89b-12d3-a456-426614174003?project_id=123e4567-e89b-12d3-a456-426614174000
```
9. Получение issues по статусу
```
GET /issues/status/open?project_id=123e4567-e89b-12d3-a456-426614174000
```
10. Получение issues по назначенному пользователю
```
GET /issues/assignee/123e4567-e89b-12d3-a456-426614174001?project_id=123e4567-e89b-12d3-a456-426614174000
```
11. Получение issues по приоритету
```
GET /issues/priority/high?project_id=123e4567-e89b-12d3-a456-426614174000
```
12. Получение issues по компоненту
```
GET /issues/component/backend?project_id=123e4567-e89b-12d3-a456-426614174000
```
13. Обновление issue
```
PUT /issues/123e4567-e89b-12d3-a456-426614174003?project_id=123e4567-e89b-12d3-a456-426614174000

{
    "status": "in_progress",
    "assignee_id": "123e4567-e89b-12d3-a456-426614174001"
}
```
14. Удаление issue
```
DELETE /issues/123e4567-e89b-12d3-a456-426614174003?project_id=123e4567-e89b-12d3-a456-426614174000
```
Комментарии
15. Добавление комментария к issue
```
POST /issues/123e4567-e89b-12d3-a456-426614174003/comments?project_id=123e4567-e89b-12d3-a456-426614174000

{
    "user_id": "123e4567-e89b-12d3-a456-426614174001",
    "content": "Это комментарий к issue"
}
```
16. Получение комментариев к issue
```
GET /issues/123e4567-e89b-12d3-a456-426614174003/comments?project_id=123e4567-e89b-12d3-a456-426614174000
```
История изменений
17. Получение истории изменений issue
```
GET /issues/123e4567-e89b-12d3-a456-426614174003/history?project_id=123e4567-e89b-12d3-a456-426614174000
```
Аналитика
18. Получение статистики по проекту
```
GET /projects/123e4567-e89b-12d3-a456-426614174000/statistics
```
## Структура базы данных
Проект использует денормализованный дизайн данных в Cassandra с несколькими таблицами для оптимизации различных запросов:

- users - пользователи системы
- projects - проекты
- issues_by_project - основные данные issues, отсортированные по дате создания
- issues_by_status - issues сгруппированные по статусу
- issues_by_assignee - issues сгруппированные по назначенным пользователям
- issues_by_priority - issues сгруппированные по приоритету
- issues_by_component - issues сгруппированные по компонентам
- issue_comments - комментарии к issues
- issue_history - история изменений issues

### Тестирование
Для тестирования API рекомендуется использовать Postman или аналогичные инструменты. Все эндпоинты возвращают данные в формате JSON.
