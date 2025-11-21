from cassandra.cluster import Cluster
from cassandra.query import dict_factory
import uuid
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class CassandraManager:
    def __init__(self):
        self.cluster = None
        self.session = None
        self.is_connected = False

    def connect(self, hosts=None, port=None, keyspace=None):
        if hosts is None:
            hosts = os.getenv('CASSANDRA_HOSTS', '127.0.0.1')
        if port is None:
            port = int(os.getenv('CASSANDRA_PORT', '9042'))
        if keyspace is None:
            keyspace = os.getenv('CASSANDRA_KEYSPACE', 'issue_tracker')
        
        # Если hosts - строка, преобразуем в список
        if isinstance(hosts, str):
            hosts = [hosts]

        if isinstance(port, str):
            port = int(port)

        try:
            logger.info(f"Connecting to Cassandra at {hosts}:{port}")

            try:
                self.cluster = Cluster(
                    hosts,
                    port=port,
                    connect_timeout=30,
                    control_connection_timeout=30,
                    protocol_version=4
                )
            except Exception as e:
                logger.warning(f"Failed to use protocol version 4: {e}, using auto-detection")
                self.cluster = Cluster(
                    hosts,
                    port=port,
                    connect_timeout=30,
                    control_connection_timeout=30
                )

            self.session = self.cluster.connect()
            logger.info("Successfully established connection to Cassandra cluster")
            
            # Проверяем, что session действительно создан
            if self.session is None:
                error_msg = "Session is None after connection attempt"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Создаем keyspace если не существует
            self.session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {keyspace} 
                WITH replication = {{
                    'class': 'SimpleStrategy', 
                    'replication_factor': 1
                }}
            """)

            self.session.set_keyspace(keyspace)
            self.session.row_factory = dict_factory

            self.create_tables()
            self.create_indexes()

            self.is_connected = True
            logger.info("Successfully connected to Cassandra and created tables")

        except Exception as e:
            logger.error(f"Error connecting to Cassandra: {e}", exc_info=True)
            self.is_connected = False
            self.session = None
            self.cluster = None
            raise

    def close(self):
        """Закрытие соединения"""
        if self.cluster:
            self.cluster.shutdown()
            logger.info("Cassandra connection closed")

    def create_tables(self):
        """Создание таблиц в базе данных"""

        try:
            # Таблица projects
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id UUID,
                    name TEXT,
                    description TEXT,
                    created_at TIMESTAMP,
                    PRIMARY KEY (project_id)
                )
            """)

            # Таблица issues_by_project
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issues_by_project (
                    project_id UUID,
                    created_at TIMESTAMP,
                    issue_id UUID,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    priority TEXT,
                    assignee_id UUID,
                    reporter_id UUID,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (project_id, created_at, issue_id)
                ) WITH CLUSTERING ORDER BY (created_at DESC, issue_id ASC)
            """)

            # Таблица issues_by_status
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issues_by_status (
                    project_id UUID,
                    status TEXT,
                    created_at TIMESTAMP,
                    issue_id UUID,
                    title TEXT,
                    priority TEXT,
                    assignee_id UUID,
                    PRIMARY KEY ((project_id, status), created_at, issue_id)
                ) WITH CLUSTERING ORDER BY (created_at DESC, issue_id ASC)
            """)

            # Таблица issues_by_assignee
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issues_by_assignee (
                    project_id UUID,
                    assignee_id UUID,
                    status TEXT,
                    created_at TIMESTAMP,
                    issue_id UUID,
                    title TEXT,
                    priority TEXT,
                    PRIMARY KEY ((project_id, assignee_id), status, created_at, issue_id)
                ) WITH CLUSTERING ORDER BY (status ASC, created_at DESC, issue_id ASC)
            """)

            # Таблица issues_by_priority
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issues_by_priority (
                    project_id UUID,
                    priority TEXT,
                    created_at TIMESTAMP,
                    issue_id UUID,
                    title TEXT,
                    status TEXT,
                    assignee_id UUID,
                    PRIMARY KEY ((project_id, priority), created_at, issue_id)
                ) WITH CLUSTERING ORDER BY (created_at DESC, issue_id ASC)
            """)

            # Таблица issue_comments
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issue_comments (
                    project_id UUID,
                    issue_id UUID,
                    created_at TIMESTAMP,
                    comment_id UUID,
                    user_id UUID,
                    content TEXT,
                    PRIMARY KEY ((project_id, issue_id), created_at, comment_id)
                ) WITH CLUSTERING ORDER BY (created_at DESC, comment_id ASC)
            """)

            # Таблица issue_history
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issue_history (
                    project_id UUID,
                    issue_id UUID,
                    changed_at TIMESTAMP,
                    event_id UUID,
                    field_changed TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by UUID,
                    PRIMARY KEY ((project_id, issue_id), changed_at, event_id)
                ) WITH CLUSTERING ORDER BY (changed_at DESC, event_id ASC)
            """)

            # Таблица users
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID,
                    username TEXT,
                    email TEXT,
                    role TEXT,
                    created_at TIMESTAMP,
                    PRIMARY KEY (user_id)
                )
            """)

            # Таблица issues_by_component
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS issues_by_component (
                    project_id UUID,
                    component TEXT,
                    created_at TIMESTAMP,
                    issue_id UUID,
                    title TEXT,
                    status TEXT,
                    priority TEXT,
                    assignee_id UUID,
                    PRIMARY KEY ((project_id, component), created_at, issue_id)
                ) WITH CLUSTERING ORDER BY (created_at DESC, issue_id ASC)
                """)
        except Exception as e:
            logger.error(f"Error creating tables: {e}", exc_info=True)
            raise

    def create_indexes(self):
        """Создание индексов"""

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)",
            "CREATE INDEX IF NOT EXISTS idx_comments_user ON issue_comments (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_history_field ON issue_history (field_changed)",
            "CREATE INDEX IF NOT EXISTS idx_issues_status ON issues_by_project (status)",
            "CREATE INDEX IF NOT EXISTS idx_issues_priority ON issues_by_project (priority)"
        ]

        for index_query in indexes:
            try:
                self.session.execute(index_query)
            except Exception as e:
                logger.error(f"Error creating index: {e}")

    def clear_tables(self):
        """Очистка всех таблиц (без удаления самих таблиц)"""

        try:
            tables = [
                'users',
                'projects',
                'issues_by_project',
                'issues_by_status',
                'issues_by_assignee',
                'issues_by_priority',
                'issues_by_component',
                'issue_comments',
                'issue_history'
            ]

            for table in tables:
                self.session.execute(f"TRUNCATE {table}")

            logger.info("All tables cleared successfully")

        except Exception as e:
            logger.error(f"Error clearing tables: {e}")
            raise

    def seed_test_data(self):
        """Заполнение базы тестовыми данными"""

        try:
            self.clear_tables()  # Очищаем перед заполнением

            # Создаем тестовых пользователей
            users_data = [
                {
                    'user_id': uuid.uuid4(),
                    'username': 'admin_user',
                    'email': 'admin@company.com',
                    'role': 'admin',
                    'created_at': datetime.now()
                },
                {
                    'user_id': uuid.uuid4(),
                    'username': 'dev_user1',
                    'email': 'dev1@company.com',
                    'role': 'developer',
                    'created_at': datetime.now()
                },
                {
                    'user_id': uuid.uuid4(),
                    'username': 'dev_user2',
                    'email': 'dev2@company.com',
                    'role': 'developer',
                    'created_at': datetime.now()
                },
                {
                    'user_id': uuid.uuid4(),
                    'username': 'tester_user',
                    'email': 'tester@company.com',
                    'role': 'tester',
                    'created_at': datetime.now()
                }
            ]

            users_insert = """
                INSERT INTO users (user_id, username, email, role, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """

            for user in users_data:
                self.session.execute(users_insert, (
                    user['user_id'], user['username'], user['email'],
                    user['role'], user['created_at']
                ))

            # Создаем тестовые проекты
            projects_data = [
                {
                    'project_id': uuid.uuid4(),
                    'name': 'Web Application',
                    'description': 'Основное веб-приложение компании',
                    'created_at': datetime.now()
                },
                {
                    'project_id': uuid.uuid4(),
                    'name': 'Mobile App',
                    'description': 'Мобильное приложение для iOS и Android',
                    'created_at': datetime.now()
                }
            ]

            projects_insert = """
                INSERT INTO projects (project_id, name, description, created_at)
                VALUES (%s, %s, %s, %s)
            """

            for project in projects_data:
                self.session.execute(projects_insert, (
                    project['project_id'], project['name'],
                    project['description'], project['created_at']
                ))

            # Создаем тестовые issues
            web_app_project = projects_data[0]['project_id']
            mobile_project = projects_data[1]['project_id']
            admin_user = users_data[0]['user_id']
            dev1_user = users_data[1]['user_id']
            dev2_user = users_data[2]['user_id']
            tester_user = users_data[3]['user_id']

            issues_data = [
                # Issues для Web Application
                {
                    'project_id': web_app_project,
                    'issue_id': uuid.uuid4(),
                    'title': 'Ошибка авторизации',
                    'description': 'Пользователи не могут войти в систему с правильными credentials',
                    'status': 'open',
                    'priority': 'high',
                    'assignee_id': dev1_user,
                    'reporter_id': tester_user,
                    'component': 'authentication',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                },
                {
                    'project_id': web_app_project,
                    'issue_id': uuid.uuid4(),
                    'title': 'Медленная загрузка страницы',
                    'description': 'Главная страница загружается более 5 секунд',
                    'status': 'in_progress',
                    'priority': 'medium',
                    'assignee_id': dev2_user,
                    'reporter_id': admin_user,
                    'component': 'performance',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                },
                {
                    'project_id': web_app_project,
                    'issue_id': uuid.uuid4(),
                    'title': 'Некорректное отображение в Safari',
                    'description': 'Страница профиля некорректно отображается в браузере Safari',
                    'status': 'open',
                    'priority': 'low',
                    'assignee_id': None,
                    'reporter_id': tester_user,
                    'component': 'frontend',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                },
                # Issues для Mobile App
                {
                    'project_id': mobile_project,
                    'issue_id': uuid.uuid4(),
                    'title': 'Крах приложения при повороте экрана',
                    'description': 'Приложение крашится при изменении ориентации экрана на главном экране',
                    'status': 'open',
                    'priority': 'critical',
                    'assignee_id': dev1_user,
                    'reporter_id': tester_user,
                    'component': 'ui',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
            ]

            # Запросы для вставки в разные таблицы
            issues_by_project_insert = """
                INSERT INTO issues_by_project (
                    project_id, created_at, issue_id, title, description, 
                    status, priority, assignee_id, reporter_id, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            issues_by_status_insert = """
                INSERT INTO issues_by_status (
                    project_id, status, created_at, issue_id, title, 
                    priority, assignee_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            issues_by_assignee_insert = """
                INSERT INTO issues_by_assignee (
                    project_id, assignee_id, status, created_at, issue_id, 
                    title, priority
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            issues_by_priority_insert = """
                INSERT INTO issues_by_priority (
                    project_id, priority, created_at, issue_id, title, 
                    status, assignee_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            issues_by_component_insert = """
                INSERT INTO issues_by_component (
                    project_id, component, created_at, issue_id, title, 
                    status, priority, assignee_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            for issue in issues_data:
                # Вставляем в основную таблицу
                self.session.execute(issues_by_project_insert, (
                    issue['project_id'], issue['created_at'], issue['issue_id'],
                    issue['title'], issue['description'], issue['status'],
                    issue['priority'], issue['assignee_id'], issue['reporter_id'],
                    issue['updated_at']
                ))

                # Вставляем в таблицу по статусу
                self.session.execute(issues_by_status_insert, (
                    issue['project_id'], issue['status'], issue['created_at'],
                    issue['issue_id'], issue['title'], issue['priority'],
                    issue['assignee_id']
                ))

                # Вставляем в таблицу по назначенному пользователю (если есть)
                if issue['assignee_id']:
                    self.session.execute(issues_by_assignee_insert, (
                        issue['project_id'], issue['assignee_id'], issue['status'],
                        issue['created_at'], issue['issue_id'], issue['title'],
                        issue['priority']
                    ))

                # Вставляем в таблицу по приоритету
                self.session.execute(issues_by_priority_insert, (
                    issue['project_id'], issue['priority'], issue['created_at'],
                    issue['issue_id'], issue['title'], issue['status'],
                    issue['assignee_id']
                ))

                # Вставляем в таблицу по компоненту (если есть)
                if issue['component']:
                    self.session.execute(issues_by_component_insert, (
                        issue['project_id'], issue['component'], issue['created_at'],
                        issue['issue_id'], issue['title'], issue['status'],
                        issue['priority'], issue['assignee_id']
                    ))

            # Создаем тестовые комментарии
            comments_data = [
                {
                    'project_id': web_app_project,
                    'issue_id': issues_data[0]['issue_id'],
                    'comment_id': uuid.uuid4(),
                    'user_id': dev1_user,
                    'content': 'Начинаю разбираться с этой проблемой. Похоже на issue с сессиями.',
                    'created_at': datetime.now()
                },
                {
                    'project_id': web_app_project,
                    'issue_id': issues_data[0]['issue_id'],
                    'comment_id': uuid.uuid4(),
                    'user_id': tester_user,
                    'content': 'Спасибо! Буду ждать обновлений.',
                    'created_at': datetime.now()
                }
            ]

            comments_insert = """
                INSERT INTO issue_comments (
                    project_id, issue_id, created_at, comment_id, user_id, content
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            for comment in comments_data:
                self.session.execute(comments_insert, (
                    comment['project_id'], comment['issue_id'], comment['created_at'],
                    comment['comment_id'], comment['user_id'], comment['content']
                ))

            logger.info("Test data seeded successfully")
            return {
                'users': [str(user['user_id']) for user in users_data],
                'projects': [str(project['project_id']) for project in projects_data],
                'issues': [str(issue['issue_id']) for issue in issues_data]
            }

        except Exception as e:
            logger.error(f"Error seeding test data: {e}")
            raise


# Глобальный экземпляр менеджера БД
cassandra_manager = CassandraManager()
