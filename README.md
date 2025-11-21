# BugTracker API

REST API for an issue tracking system built with FastAPI using Apache Cassandra as the database.

## Features

- ✅ User management
- ✅ Project management
- ✅ Issue creation and management
- ✅ Issue commenting
- ✅ Issue change history
- ✅ Issue filtering by status, priority, assignee, component
- ✅ Project statistics
- ✅ Administration (data cleanup and test data seeding)

## Technology Stack

- **Python 3.8+** (<= 3.11 to avoid driver connection issues)
- **FastAPI** - web framework
- **Apache Cassandra** - distributed NoSQL database
- **Uvicorn** - ASGI server
- **Pydantic** - data validation

## Database Structure
### **Physical Schema in Chebotko Notation**
<img width="974" height="662" alt="image" src="https://github.com/user-attachments/assets/5bdf1566-d76c-424a-96c8-e24ec6837107" />

The project uses a denormalized data design in Cassandra with multiple tables optimized for different queries:

- users - system users
- projects - projects
- issues_by_project - main issue data sorted by creation date
- issues_by_status - issues grouped by status
- issues_by_assignee - issues grouped by assigned users
- issues_by_priority - issues grouped by priority
- issues_by_component - issues grouped by components
- issue_comments - issue comments
- issue_history - issue change history

### **ER Diagram in Chen Notation**
<img width="873" height="616" alt="image" src="https://github.com/user-attachments/assets/cc84635f-c6e2-489e-86f5-39a98b919463" />

### **Logical Schema in Chebotko Notation**

<img width="944" height="634" alt="image" src="https://github.com/user-attachments/assets/2161a955-5181-4810-a210-dcf89a4f05da" />
<img width="869" height="764" alt="image" src="https://github.com/user-attachments/assets/923d724e-3e80-407c-86d7-d9e92472b0d8" />

## Installation and Setup

### 0. Prerequisites

- Python 3.8-3.11
- Apache Cassandra (local or Docker)
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bugtracker
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Cassandra

#### Using Docker (Recommended)

**For Windows with WSL:**

```bash
# In WSL terminal
docker run --name some-cassandra -p 9042:9042 -d cassandra:latest
```

Verify port forwarding is correct:
```bash
docker ps
# Should show: 0.0.0.0:9042->9042/tcp
```

**Connection Configuration:**

The application connects to `127.0.0.1:9042` by default. To change settings, use environment variables:

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

**If connection fails:**

1. Check if Cassandra is running: `docker ps`
2. Check port availability: `telnet 127.0.0.1 9042` (or use `Test-NetConnection -ComputerName 127.0.0.1 -Port 9042` in PowerShell)
3. If using WSL, verify port forwarding: `0.0.0.0:9042->9042/tcp`
4. Try using `localhost` instead of `127.0.0.1` or vice versa

#### Local Installation

```bash
# Start Cassandra service
sudo service cassandra start
```

### 4. Start the Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at: http://localhost:8000

## 5. API Documentation
After starting the application, automatic documentation is available:

- Swagger UI: http://localhost:8000/docs

### Testing
For API testing, we recommend using Postman or similar tools. All endpoints return data in JSON format.

## Example API Requests via Postman

### Administration
1. Clear database
```
POST /admin/clear-data
```
2. Seed test data
```
POST /admin/seed-data
```

3. Reset database (clear + seed)
```
POST /admin/reset-data
```

### Users
4. Create user
```
POST /users/

{
    "username": "john_doe",
    "email": "john@example.com",
    "role": "developer"
}
```
5. Get users list
```
GET /users/?skip=0&limit=100
```

### Projects
6. Create project
```
POST /projects/

{
    "name": "New Project",
    "description": "Description of the new project"
}
```

### Issues
7. Create issue
```
POST /issues/

{
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "New Bug",
    "description": "Detailed bug description",
    "status": "open",
    "priority": "high",
    "assignee_id": "123e4567-e89b-12d3-a456-426614174001",
    "reporter_id": "123e4567-e89b-12d3-a456-426614174002",
    "component": "backend"
}
```
8. Get issue by ID
```
GET /issues/123e4567-e89b-12d3-a456-426614174003?project_id=123e4567-e89b-12d3-a456-426614174000
```
9. Get issues by status
```
GET /issues/status/open?project_id=123e4567-e89b-12d3-a456-426614174000
```
10. Get issues by assignee
```
GET /issues/assignee/123e4567-e89b-12d3-a456-426614174001?project_id=123e4567-e89b-12d3-a456-426614174000
```
11. Get issues by priority
```
GET /issues/priority/high?project_id=123e4567-e89b-12d3-a456-426614174000
```
12. Get issues by component
```
GET /issues/component/backend?project_id=123e4567-e89b-12d3-a456-426614174000
```
13. Update issue
```
PUT /issues/123e4567-e89b-12d3-a456-426614174003?project_id=123e4567-e89b-12d3-a456-426614174000

{
    "status": "in_progress",
    "assignee_id": "123e4567-e89b-12d3-a456-426614174001"
}
```
14. Delete issue
```
DELETE /issues/123e4567-e89b-12d3-a456-426614174003?project_id=123e4567-e89b-12d3-a456-426614174000
```

### Comments
15. Add comment to issue
```
POST /issues/123e4567-e89b-12d3-a456-426614174003/comments?project_id=123e4567-e89b-12d3-a456-426614174000

{
    "user_id": "123e4567-e89b-12d3-a456-426614174001",
    "content": "This is a comment on the issue"
}
```
16. Get issue comments
```
GET /issues/123e4567-e89b-12d3-a456-426614174003/comments?project_id=123e4567-e89b-12d3-a456-426614174000
```

### Change History
17. Get issue change history
```
GET /issues/123e4567-e89b-12d3-a456-426614174003/history?project_id=123e4567-e89b-12d3-a456-426614174000
```

### Analytics
18. Get project statistics
```
GET /projects/123e4567-e89b-12d3-a456-426614174000/statistics
```
-------------------------------------------------------------------------------------------------------------------------

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

## Структура базы данных
### **Физическая схема в нотации Чеботко**
<img width="974" height="662" alt="image" src="https://github.com/user-attachments/assets/5bdf1566-d76c-424a-96c8-e24ec6837107" />

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

### **ER-диаграмма в нотации Чена**
<img width="873" height="616" alt="image" src="https://github.com/user-attachments/assets/cc84635f-c6e2-489e-86f5-39a98b919463" />

### **Логическая схема в нотации Чеботко**

<img width="944" height="634" alt="image" src="https://github.com/user-attachments/assets/2161a955-5181-4810-a210-dcf89a4f05da" />
<img width="869" height="764" alt="image" src="https://github.com/user-attachments/assets/923d724e-3e80-407c-86d7-d9e92472b0d8" />



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

### Тестирование
Для тестирования API рекомендуется использовать Postman или аналогичные инструменты. Все эндпоинты возвращают данные в формате JSON.

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
