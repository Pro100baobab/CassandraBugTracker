from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uuid
import logging
import sys
from database import cassandra_manager
from contextlib import asynccontextmanager
from models import *

# Настройка логирования для всего приложения
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def get_db():
    """Получение сессии Cassandra"""
    if not cassandra_manager.is_connected or cassandra_manager.session is None:
        raise HTTPException(
            status_code=503,
            detail="Database connection is not available. Please check server logs and ensure Cassandra is running."
        )
    return cassandra_manager.session


# Вспомогательные функции
def generate_uuid():
    return uuid.uuid4()


def get_current_time():
    return datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Если подключение еще не установлено (запуск через uvicorn main:app)
    if not cassandra_manager.is_connected:
        logger.info("Connecting to Cassandra...")
        cassandra_manager.connect()
        
        if not cassandra_manager.is_connected:
            error_msg = "Connection flag is False after connect()"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        if cassandra_manager.session is None:
            error_msg = "Session is None after connect()"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        logger.info("Cassandra connection established successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    cassandra_manager.close()


app = FastAPI(
    title="BugTracker API",
    description="REST API для системы отслеживания ошибок на Apache Cassandra",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------------------------------------------- #


# Q9: Создание пользователя
@app.post("/users/", response_model=UserResponse, tags=["Пользователи"])
async def create_user(user: UserCreate, db=Depends(get_db)):
    user_id = generate_uuid()
    created_at = get_current_time()

    query = f"""
        INSERT INTO users (user_id, username, email, role, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """

    try:
        db.execute(query, (user_id, user.username, user.email, user.role.value, created_at))

        return UserResponse(
            user_id=user_id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            created_at=created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


# Q11: Просмотр пользователей
@app.get("/users/", response_model=List[UserResponse], tags=["Пользователи"])
async def get_users(
        skip: int = 0,
        limit: int = 100,
        db=Depends(get_db)
):
    query = "SELECT * FROM users LIMIT %s"
    try:
        result = db.execute(query, [limit])
        users = []
        for row in result:
            users.append(UserResponse(**row))
        return users[skip:skip + limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


# Q10: Создание проекта
@app.post("/projects/", response_model=ProjectResponse, tags=["Проекты"])
async def create_project(project: ProjectCreate, db=Depends(get_db)):
    project_id = generate_uuid()
    created_at = get_current_time()

    query = """
        INSERT INTO projects (project_id, name, description, created_at)
        VALUES (%s, %s, %s, %s)
    """

    try:
        db.execute(query, (project_id, project.name, project.description, created_at))

        return ProjectResponse(
            project_id=project_id,
            name=project.name,
            description=project.description,
            created_at=created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")


# Q: Получение всех проектов
@app.get("/projects/", response_model=List[ProjectResponse], tags=["Проекты"])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db)
):
    """Получение списка всех проектов"""
    query = "SELECT * FROM projects LIMIT %s"
    try:
        result = db.execute(query, [limit])
        projects = []
        for row in result:
            projects.append(ProjectResponse(**row))
        return projects[skip:skip + limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")


# Q1: Создание нового issue
@app.post("/issues/", response_model=IssueResponse, tags=["Issues"])
async def create_issue(issue: IssueCreate, db=Depends(get_db)):
    issue_id = generate_uuid()
    created_at = get_current_time()
    updated_at = created_at

    # Вставка в issues_by_project
    query1 = """
        INSERT INTO issues_by_project (
            project_id, created_at, issue_id, title, description, 
            status, priority, assignee_id, reporter_id, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Вставка в issues_by_status
    query2 = """
        INSERT INTO issues_by_status (
            project_id, status, created_at, issue_id, title, 
            priority, assignee_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    # Вставка в issues_by_assignee (если назначен)
    query3 = """
        INSERT INTO issues_by_assignee (
            project_id, assignee_id, status, created_at, issue_id, 
            title, priority
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    # Вставка в issues_by_priority
    query4 = """
        INSERT INTO issues_by_priority (
            project_id, priority, created_at, issue_id, title, 
            status, assignee_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    # Вставка в issues_by_component (если указан компонент)
    query5 = """
        INSERT INTO issues_by_component (
            project_id, component, created_at, issue_id, title, 
            status, priority, assignee_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        # Выполняем все вставки
        db.execute(query1, (
            issue.project_id, created_at, issue_id, issue.title, issue.description,
            issue.status.value, issue.priority.value, issue.assignee_id, issue.reporter_id,
            updated_at
        ))

        db.execute(query2, (
            issue.project_id, issue.status.value, created_at, issue_id, issue.title,
            issue.priority.value, issue.assignee_id
        ))

        if issue.assignee_id:
            db.execute(query3, (
                issue.project_id, issue.assignee_id, issue.status.value, created_at, issue_id,
                issue.title, issue.priority.value
            ))

        db.execute(query4, (
            issue.project_id, issue.priority.value, created_at, issue_id, issue.title,
            issue.status.value, issue.assignee_id
        ))

        if issue.component:
            db.execute(query5, (
                issue.project_id, issue.component, created_at, issue_id, issue.title,
                issue.status.value, issue.priority.value, issue.assignee_id
            ))

        return IssueResponse(
            issue_id=issue_id,
            project_id=issue.project_id,
            title=issue.title,
            description=issue.description,
            status=issue.status.value,
            priority=issue.priority.value,
            assignee_id=issue.assignee_id,
            reporter_id=issue.reporter_id,
            component=issue.component,
            created_at=created_at,
            updated_at=updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating issue: {str(e)}")


# Q2: Просмотр созданного issue
@app.get("/issues/{issue_id}", response_model=IssueResponse, tags=["Issues"])
async def get_issue(issue_id: str, project_id: str, db=Depends(get_db)):
    query = """
        SELECT * FROM issues_by_project 
        WHERE project_id = %s AND issue_id = %s 
        LIMIT 1
    """

    try:
        result = db.execute(query, (uuid.UUID(project_id), uuid.UUID(issue_id)))
        issue = result.one()

        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        return IssueResponse(**issue)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issue: {str(e)}")


# Q3: Issues по статусу
@app.get("/issues/status/{status}", response_model=List[IssueResponse], tags=["Issues"])
async def get_issues_by_status(
        project_id: str,
        status: Status,
        db=Depends(get_db)
):
    query = """
        SELECT ip.* FROM issues_by_status ibs
        JOIN issues_by_project ip ON ibs.project_id = ip.project_id AND ibs.issue_id = ip.issue_id
        WHERE ibs.project_id = %s AND ibs.status = %s
    """

    try:
        result = db.execute(query, (uuid.UUID(project_id), status))
        issues = [IssueResponse(**row) for row in result]
        return issues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issues by status: {str(e)}")


# Q4: Issues назначенные пользователю
@app.get("/issues/assignee/{assignee_id}", response_model=List[IssueResponse], tags=["Issues"])
async def get_issues_by_assignee(
        project_id: str,
        assignee_id: str,
        status: Optional[Status] = None,
        db=Depends(get_db)
):
    if status:
        query = """
            SELECT ip.* FROM issues_by_assignee iba
            JOIN issues_by_project ip ON iba.project_id = ip.project_id AND iba.issue_id = ip.issue_id
            WHERE iba.project_id = %s AND iba.assignee_id = %s AND iba.status = %s
        """
        result = db.execute(query, (uuid.UUID(project_id), uuid.UUID(assignee_id), status))
    else:
        query = """
            SELECT ip.* FROM issues_by_assignee iba
            JOIN issues_by_project ip ON iba.project_id = ip.project_id AND iba.issue_id = ip.issue_id
            WHERE iba.project_id = %s AND iba.assignee_id = %s
        """
        result = db.execute(query, (uuid.UUID(project_id), uuid.UUID(assignee_id)))

    try:
        issues = [IssueResponse(**row) for row in result]
        return issues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issues by assignee: {str(e)}")


# Q5: Issues по приоритету
@app.get("/issues/priority/{priority}", response_model=List[IssueResponse], tags=["Issues"])
async def get_issues_by_priority(
        project_id: str,
        priority: Priority,
        db=Depends(get_db)
):
    query = """
        SELECT ip.* FROM issues_by_priority ibp
        JOIN issues_by_project ip ON ibp.project_id = ip.project_id AND ibp.issue_id = ip.issue_id
        WHERE ibp.project_id = %s AND ibp.priority = %s
    """

    try:
        result = db.execute(query, (uuid.UUID(project_id), priority))
        issues = [IssueResponse(**row) for row in result]
        return issues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issues by priority: {str(e)}")


# Q6: Issues по компоненту
@app.get("/issues/component/{component}", response_model=List[IssueResponse], tags=["Issues"])
async def get_issues_by_component(
        project_id: str,
        component: str,
        db=Depends(get_db)
):
    query = """
        SELECT ip.* FROM issues_by_component ibc
        JOIN issues_by_project ip ON ibc.project_id = ip.project_id AND ibc.issue_id = ip.issue_id
        WHERE ibc.project_id = %s AND ibc.component = %s
    """

    try:
        result = db.execute(query, (uuid.UUID(project_id), component))
        issues = [IssueResponse(**row) for row in result]
        return issues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issues by component: {str(e)}")


# Q12: Оставление комментария
@app.post("/issues/{issue_id}/comments", response_model=CommentResponse, tags=["Комментарии"])
async def create_comment(
        issue_id: str,
        project_id: str,
        comment: CommentCreate,
        db=Depends(get_db)
):
    comment_id = generate_uuid()
    created_at = get_current_time()

    query = """
        INSERT INTO issue_comments (project_id, issue_id, created_at, comment_id, user_id, content)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try:
        db.execute(query, (
            uuid.UUID(project_id), uuid.UUID(issue_id), created_at,
            comment_id, comment.user_id, comment.content
        ))

        return CommentResponse(
            comment_id=comment_id,
            issue_id=uuid.UUID(issue_id),
            project_id=uuid.UUID(project_id),
            user_id=comment.user_id,
            content=comment.content,
            created_at=created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating comment: {str(e)}")


# Получение комментариев к issue
@app.get("/issues/{issue_id}/comments", response_model=List[CommentResponse], tags=["Комментарии"])
async def get_issue_comments(
        issue_id: str,
        project_id: str,
        db=Depends(get_db)
):
    query = """
        SELECT * FROM issue_comments 
        WHERE project_id = %s AND issue_id = %s
        ORDER BY created_at DESC
    """

    try:
        result = db.execute(query, (uuid.UUID(project_id), uuid.UUID(issue_id)))
        comments = [CommentResponse(**row) for row in result]
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching comments: {str(e)}")


# Q7: История изменений issue
@app.get("/issues/{issue_id}/history", response_model=List[HistoryEventResponse], tags=["История"])
async def get_issue_history(
        issue_id: str,
        project_id: str,
        db=Depends(get_db)
):
    query = """
        SELECT * FROM issue_history 
        WHERE project_id = %s AND issue_id = %s
        ORDER BY changed_at DESC
    """

    try:
        result = db.execute(query, (uuid.UUID(project_id), uuid.UUID(issue_id)))
        history = [HistoryEventResponse(**row) for row in result]
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issue history: {str(e)}")


# Q8: Статистика по проекту
@app.get("/projects/{project_id}/statistics", response_model=ProjectStatistics, tags=["Аналитика"])
async def get_project_statistics(project_id: str, db=Depends(get_db)):
    try:
        project_uuid = uuid.UUID(project_id)

        # Общее количество issues
        total_query = "SELECT COUNT(*) as count FROM issues_by_project WHERE project_id = %s"
        total_result = db.execute(total_query, [project_uuid])
        total_issues = total_result.one()['count']

        # Issues по статусам
        status_query = """
            SELECT status, COUNT(*) as count FROM issues_by_status 
            WHERE project_id = %s GROUP BY status
        """
        status_result = db.execute(status_query, [project_uuid])
        issues_by_status = {row['status']: row['count'] for row in status_result}

        # Issues по приоритетам
        priority_query = """
            SELECT priority, COUNT(*) as count FROM issues_by_priority 
            WHERE project_id = %s GROUP BY priority
        """
        priority_result = db.execute(priority_query, [project_uuid])
        issues_by_priority = {row['priority']: row['count'] for row in priority_result}

        # Issues по компонентам
        component_query = """
            SELECT component, COUNT(*) as count FROM issues_by_component 
            WHERE project_id = %s GROUP BY component
        """
        component_result = db.execute(component_query, [project_uuid])
        issues_by_component = {row['component']: row['count'] for row in component_result if row['component']}

        return ProjectStatistics(
            project_id=project_uuid,
            total_issues=total_issues,
            issues_by_status=issues_by_status,
            issues_by_priority=issues_by_priority,
            issues_by_component=issues_by_component
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project statistics: {str(e)}")


# Обновление issue
@app.put("/issues/{issue_id}", response_model=IssueResponse, tags=["Issues"])
async def update_issue(
        issue_id: str,
        project_id: str,
        issue_update: IssueUpdate,
        db=Depends(get_db)
):
    try:
        project_uuid = uuid.UUID(project_id)
        issue_uuid = uuid.UUID(issue_id)


        get_query = """
            SELECT * FROM issues_by_project 
            WHERE project_id = %s
        """
        result = db.execute(get_query, [project_uuid])

        # Ищем нужный issue по issue_id
        current_issue = None
        for row in result:
            if row['issue_id'] == issue_uuid:
                current_issue = row
                break

        if not current_issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        # Подготавливаем обновленные значения
        updated_fields = issue_update.dict(exclude_unset=True)
        if not updated_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Определяем новые значения
        new_title = updated_fields.get('title', current_issue['title'])
        new_description = updated_fields.get('description', current_issue['description'])
        new_status = updated_fields.get('status', current_issue['status'])
        new_priority = updated_fields.get('priority', current_issue['priority'])
        new_assignee_id = updated_fields.get('assignee_id', current_issue['assignee_id'])
        new_component = updated_fields.get('component', current_issue['component'])
        updated_at = get_current_time()
        created_at = current_issue['created_at']

        # Обновляем основную таблицу issues_by_project
        update_main_query = """
            UPDATE issues_by_project SET 
            title = %s, description = %s, status = %s, 
            priority = %s, assignee_id = %s, updated_at = %s
            WHERE project_id = %s AND created_at = %s AND issue_id = %s
        """
        db.execute(update_main_query, (
            new_title, new_description, new_status, new_priority,
            new_assignee_id, updated_at,
            project_uuid, created_at, issue_uuid
        ))

        # ОБНОВЛЕНИЕ ДЕНОРМАЛИЗОВАННЫХ ТАБЛИЦ

        changes = []
        old_status = current_issue['status']
        old_priority = current_issue['priority']
        old_assignee_id = current_issue['assignee_id']
        old_component = current_issue['component']

        # 1. issues_by_status - ключ: ((project_id, status), created_at, issue_id)
        if 'status' in updated_fields:
            # Удаляем старую запись со старым статусом
            delete_old_status_query = """
                DELETE FROM issues_by_status 
                WHERE project_id = %s AND status = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(delete_old_status_query, (project_uuid, old_status, created_at, issue_uuid))

            # Создаем новую запись с новым статусом
            insert_new_status_query = """
                INSERT INTO issues_by_status 
                (project_id, status, created_at, issue_id, title, priority, assignee_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            db.execute(insert_new_status_query, (
                project_uuid, new_status, created_at, issue_uuid,
                new_title, new_priority, new_assignee_id
            ))
            changes.append(("status", old_status, new_status))
        else:
            # Обновляем существующую запись
            update_status_query = """
                UPDATE issues_by_status SET title = %s, priority = %s, assignee_id = %s
                WHERE project_id = %s AND status = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(update_status_query, (
                new_title, new_priority, new_assignee_id,
                project_uuid, old_status, created_at, issue_uuid
            ))

        # 2. issues_by_priority - ключ: ((project_id, priority), created_at, issue_id)
        if 'priority' in updated_fields:
            # Удаляем старую запись со старым приоритетом
            delete_old_priority_query = """
                DELETE FROM issues_by_priority 
                WHERE project_id = %s AND priority = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(delete_old_priority_query, (project_uuid, old_priority, created_at, issue_uuid))

            # Создаем новую запись с новым приоритетом
            insert_new_priority_query = """
                INSERT INTO issues_by_priority 
                (project_id, priority, created_at, issue_id, title, status, assignee_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            db.execute(insert_new_priority_query, (
                project_uuid, new_priority, created_at, issue_uuid,
                new_title, new_status, new_assignee_id
            ))
            changes.append(("priority", old_priority, new_priority))
        else:
            # Обновляем существующую запись
            update_priority_query = """
                UPDATE issues_by_priority SET title = %s, status = %s, assignee_id = %s
                WHERE project_id = %s AND priority = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(update_priority_query, (
                new_title, new_status, new_assignee_id,
                project_uuid, old_priority, created_at, issue_uuid
            ))

        # 3. issues_by_assignee - ключ: ((project_id, assignee_id), status, created_at, issue_id)
        assignee_changed = 'assignee_id' in updated_fields
        status_changed = 'status' in updated_fields

        if assignee_changed or status_changed:
            # Удаляем старую запись (если был assignee)
            if old_assignee_id:
                delete_old_assignee_query = """
                    DELETE FROM issues_by_assignee 
                    WHERE project_id = %s AND assignee_id = %s AND status = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(delete_old_assignee_query, (
                    project_uuid, old_assignee_id, old_status, created_at, issue_uuid
                ))

            # Создаем новую запись (если есть новый assignee)
            if new_assignee_id:
                insert_new_assignee_query = """
                    INSERT INTO issues_by_assignee 
                    (project_id, assignee_id, status, created_at, issue_id, title, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                db.execute(insert_new_assignee_query, (
                    project_uuid, new_assignee_id, new_status, created_at, issue_uuid,
                    new_title, new_priority
                ))

            if assignee_changed:
                changes.append(("assignee_id",
                                str(old_assignee_id) if old_assignee_id else None,
                                str(new_assignee_id) if new_assignee_id else None))
        else:
            # Обновляем существующую запись
            if new_assignee_id:
                update_assignee_query = """
                    UPDATE issues_by_assignee SET title = %s, priority = %s
                    WHERE project_id = %s AND assignee_id = %s AND status = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(update_assignee_query, (
                    new_title, new_priority,
                    project_uuid, new_assignee_id, new_status, created_at, issue_uuid
                ))

        # 4. issues_by_component - ключ: ((project_id, component), created_at, issue_id)
        if 'component' in updated_fields:
            # Удаляем старую запись (если был компонент)
            if old_component:
                delete_old_component_query = """
                    DELETE FROM issues_by_component 
                    WHERE project_id = %s AND component = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(delete_old_component_query, (project_uuid, old_component, created_at, issue_uuid))

            # Создаем новую запись (если есть новый компонент)
            if new_component:
                insert_new_component_query = """
                    INSERT INTO issues_by_component 
                    (project_id, component, created_at, issue_id, title, status, priority, assignee_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                db.execute(insert_new_component_query, (
                    project_uuid, new_component, created_at, issue_uuid,
                    new_title, new_status, new_priority, new_assignee_id
                ))

            changes.append(("component", old_component, new_component))
        else:
            # Обновляем существующую запись
            if new_component:
                update_component_query = """
                    UPDATE issues_by_component SET title = %s, status = %s, priority = %s, assignee_id = %s
                    WHERE project_id = %s AND component = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(update_component_query, (
                    new_title, new_status, new_priority, new_assignee_id,
                    project_uuid, new_component, created_at, issue_uuid
                ))

        # --- ЗАПИСЬ В ИСТОРИЮ ИЗМЕНЕНИЙ ---
        if changes:
            history_query = """
                INSERT INTO issue_history 
                (project_id, issue_id, changed_at, event_id, field_changed, old_value, new_value, changed_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            changed_by = current_issue['reporter_id']

            for field_changed, old_value, new_value in changes:
                event_id = generate_uuid()
                db.execute(history_query, (
                    project_uuid, issue_uuid, updated_at, event_id,
                    field_changed,
                    str(old_value) if old_value is not None else None,
                    str(new_value) if new_value is not None else None,
                    changed_by
                ))

        # Возвращаем обновленный issue
        return IssueResponse(
            issue_id=issue_uuid,
            project_id=project_uuid,
            title=new_title,
            description=new_description,
            status=new_status,
            priority=new_priority,
            assignee_id=new_assignee_id,
            reporter_id=current_issue['reporter_id'],
            component=new_component,
            created_at=created_at,
            updated_at=updated_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating issue: {str(e)}")


# Обновление issue
@app.put("/issues/{issue_id}", response_model=IssueResponse, tags=["Issues"])
async def update_issue(
        issue_id: str,
        project_id: str,
        issue_update: IssueUpdate,
        db=Depends(get_db)
):
    try:
        # Получаем текущий issue чтобы получить created_at и все текущие значения
        get_query = """
            SELECT * FROM issues_by_project 
            WHERE project_id = %s AND issue_id = %s 
            LIMIT 1
        """
        current_result = db.execute(get_query, (uuid.UUID(project_id), uuid.UUID(issue_id)))
        current_issue = current_result.one()

        if not current_issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        # Получаем component из issues_by_component (если есть)
        component_query = """
            SELECT component FROM issues_by_component 
            WHERE project_id = %s AND issue_id = %s 
            LIMIT 1
        """
        component_result = db.execute(component_query, (uuid.UUID(project_id), uuid.UUID(issue_id)))
        component_row = component_result.one()
        current_component = component_row['component'] if component_row else None

        # Подготавливаем обновленные значения
        updated_fields = issue_update.dict(exclude_unset=True)
        if not updated_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Определяем старые и новые значения
        old_title = current_issue['title']
        old_description = current_issue['description']
        old_status = current_issue['status']
        old_priority = current_issue['priority']
        old_assignee_id = current_issue['assignee_id']
        old_component = current_component

        new_title = updated_fields.get('title', old_title)
        new_description = updated_fields.get('description', old_description)
        new_status = updated_fields.get('status', old_status) if 'status' in updated_fields else old_status
        new_priority = updated_fields.get('priority', old_priority) if 'priority' in updated_fields else old_priority
        new_assignee_id = updated_fields.get('assignee_id', old_assignee_id) if 'assignee_id' in updated_fields else old_assignee_id
        new_component = updated_fields.get('component', old_component) if 'component' in updated_fields else old_component
        
        # Обрабатываем значения из Enum
        if isinstance(new_status, type) and hasattr(new_status, 'value'):
            new_status = new_status.value
        if isinstance(new_priority, type) and hasattr(new_priority, 'value'):
            new_priority = new_priority.value
        
        updated_at = get_current_time()
        created_at = current_issue['created_at']
        project_uuid = uuid.UUID(project_id)
        issue_uuid = uuid.UUID(issue_id)

        # Собираем изменения для истории
        changes = []
        if 'title' in updated_fields and old_title != new_title:
            changes.append(("title", old_title, new_title))
        if 'description' in updated_fields and old_description != new_description:
            changes.append(("description", old_description, new_description))
        if 'status' in updated_fields and old_status != new_status:
            changes.append(("status", old_status, new_status))
        if 'priority' in updated_fields and old_priority != new_priority:
            changes.append(("priority", old_priority, new_priority))
        if 'assignee_id' in updated_fields:
            old_assignee_str = str(old_assignee_id) if old_assignee_id else None
            new_assignee_str = str(new_assignee_id) if new_assignee_id else None
            if old_assignee_str != new_assignee_str:
                changes.append(("assignee_id", old_assignee_str, new_assignee_str))
        if 'component' in updated_fields:
            old_comp = old_component if old_component else None
            new_comp = new_component if new_component else None
            if old_comp != new_comp:
                changes.append(("component", old_comp, new_comp))

        # Обновляем основную таблицу issues_by_project
        update_main_query = """
            UPDATE issues_by_project SET 
            title = %s, description = %s, status = %s, 
            priority = %s, assignee_id = %s, updated_at = %s
            WHERE project_id = %s AND created_at = %s AND issue_id = %s
        """
        db.execute(update_main_query, (
            new_title, new_description, new_status, new_priority,
            new_assignee_id, updated_at,
            project_uuid, created_at, issue_uuid
        ))

        # если часть первичного ключа изменилась нужно удалить старую запись и создать новую. Если ключ не изменился, обновляем существующую.

        # 1. issues_by_status - ключ: ((project_id, status), created_at, issue_id)
        status_changed = 'status' in updated_fields and old_status != new_status
        if status_changed:
            # Удаляем старую запись со старым статусом
            delete_old_status = """
                DELETE FROM issues_by_status 
                WHERE project_id = %s AND status = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(delete_old_status, (project_uuid, old_status, created_at, issue_uuid))

            # Создаем новую запись с новым статусом
            insert_new_status = """
                INSERT INTO issues_by_status 
                (project_id, status, created_at, issue_id, title, priority, assignee_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            db.execute(insert_new_status, (
                project_uuid, new_status, created_at, issue_uuid,
                new_title, new_priority, new_assignee_id
            ))
        else:
            # Если статус не изменился, обновляем существующую запись
            update_status = """
                UPDATE issues_by_status SET title = %s, priority = %s, assignee_id = %s
                WHERE project_id = %s AND status = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(update_status, (
                new_title, new_priority, new_assignee_id,
                project_uuid, new_status, created_at, issue_uuid
            ))

        # 2. issues_by_priority - ключ: ((project_id, priority), created_at, issue_id)
        priority_changed = 'priority' in updated_fields and old_priority != new_priority
        if priority_changed:
            # Удаляем старую запись со старым приоритетом
            delete_old_priority = """
                DELETE FROM issues_by_priority 
                WHERE project_id = %s AND priority = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(delete_old_priority, (project_uuid, old_priority, created_at, issue_uuid))

            # Создаем новую запись с новым приоритетом
            insert_new_priority = """
                INSERT INTO issues_by_priority 
                (project_id, priority, created_at, issue_id, title, status, assignee_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            db.execute(insert_new_priority, (
                project_uuid, new_priority, created_at, issue_uuid,
                new_title, new_status, new_assignee_id
            ))
        else:
            # Если приоритет не изменился, обновляем существующую запись
            update_priority = """
                UPDATE issues_by_priority SET title = %s, status = %s, assignee_id = %s
                WHERE project_id = %s AND priority = %s AND created_at = %s AND issue_id = %s
            """
            db.execute(update_priority, (
                new_title, new_status, new_assignee_id,
                project_uuid, new_priority, created_at, issue_uuid
            ))

        # 3. issues_by_assignee - ключ: ((project_id, assignee_id), status, created_at, issue_id)
        assignee_changed = 'assignee_id' in updated_fields
        assignee_or_status_changed = assignee_changed or status_changed
        
        if assignee_or_status_changed:
            # Если изменился assignee ИЛИ status, нужно пересоздать записи
            # Удаляем старую запись (если был assignee)
            if old_assignee_id:
                delete_old_assignee = """
                    DELETE FROM issues_by_assignee 
                    WHERE project_id = %s AND assignee_id = %s AND status = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(delete_old_assignee, (
                    project_uuid, old_assignee_id, old_status, created_at, issue_uuid
                ))

            # Создаем новую запись (если есть новый assignee)
            if new_assignee_id:
                insert_new_assignee = """
                    INSERT INTO issues_by_assignee 
                    (project_id, assignee_id, status, created_at, issue_id, title, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                db.execute(insert_new_assignee, (
                    project_uuid, new_assignee_id, new_status, created_at, issue_uuid,
                    new_title, new_priority
                ))
        else:
            # Если assignee и status не изменились, обновляем существующую запись
            if new_assignee_id:
                update_assignee = """
                    UPDATE issues_by_assignee SET title = %s, priority = %s
                    WHERE project_id = %s AND assignee_id = %s AND status = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(update_assignee, (
                    new_title, new_priority,
                    project_uuid, new_assignee_id, new_status, created_at, issue_uuid
                ))

        # 4. issues_by_component - ключ: ((project_id, component), created_at, issue_id)
        component_changed = 'component' in updated_fields
        if component_changed:
            # Удаляем старую запись (если был компонент)
            if old_component:
                delete_old_component = """
                    DELETE FROM issues_by_component 
                    WHERE project_id = %s AND component = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(delete_old_component, (project_uuid, old_component, created_at, issue_uuid))

            # Создаем новую запись (если есть новый компонент)
            if new_component:
                insert_new_component = """
                    INSERT INTO issues_by_component 
                    (project_id, component, created_at, issue_id, title, status, priority, assignee_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                db.execute(insert_new_component, (
                    project_uuid, new_component, created_at, issue_uuid,
                    new_title, new_status, new_priority, new_assignee_id
                ))
        else:
            # Если компонент не изменился, обновляем существующую запись
            if new_component:
                update_component = """
                    UPDATE issues_by_component SET title = %s, status = %s, priority = %s, assignee_id = %s
                    WHERE project_id = %s AND component = %s AND created_at = %s AND issue_id = %s
                """
                db.execute(update_component, (
                    new_title, new_status, new_priority, new_assignee_id,
                    project_uuid, new_component, created_at, issue_uuid
                ))

        # --- ЗАПИСЬ В ИСТОРИЮ ИЗМЕНЕНИЙ ---
        if changes:
            history_query = """
                INSERT INTO issue_history 
                (project_id, issue_id, changed_at, event_id, field_changed, old_value, new_value, changed_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            changed_by = current_issue['reporter_id']  # В реальном приложении брать из авторизации

            for field_changed, old_value, new_value in changes:
                event_id = generate_uuid()
                db.execute(history_query, (
                    project_uuid, issue_uuid, updated_at, event_id,
                    field_changed,
                    str(old_value) if old_value is not None else None,
                    str(new_value) if new_value is not None else None,
                    changed_by
                ))

        # Возвращаем обновленный issue
        return IssueResponse(
            issue_id=issue_uuid,
            project_id=project_uuid,
            title=new_title,
            description=new_description,
            status=new_status,
            priority=new_priority,
            assignee_id=new_assignee_id,
            reporter_id=current_issue['reporter_id'],
            component=new_component,
            created_at=created_at,
            updated_at=updated_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating issue: {str(e)}")


# ------------------------------------------------------------------------------------------------------------------- #


@app.get("/")
async def root():
    return {"message": "BugTracker API", "version": "1.0.0"}


@app.get("/health", tags=["Система"])
async def health_check():
    """Проверка состояния подключения к базе данных"""
    return {
        "status": "ok" if cassandra_manager.is_connected else "error",
        "database_connected": cassandra_manager.is_connected,
        "session_available": cassandra_manager.session is not None,
        "cluster_available": cassandra_manager.cluster is not None
    }


# Добавляем в main.py после существующих импортов
@app.post("/admin/clear-data", tags=["Администрирование"])
async def clear_all_data(db=Depends(get_db)):
    """Очистка всех таблиц"""
    try:
        cassandra_manager.clear_tables()
        return {"message": "All tables cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")


@app.post("/admin/seed-data", tags=["Администрирование"])
async def seed_test_data():
    """Заполнение базы тестовыми данными"""
    try:
        result = cassandra_manager.seed_test_data()
        return {
            "message": "Test data seeded successfully",
            "created": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding test data: {str(e)}")


@app.post("/admin/reset-data", tags=["Администрирование"])
async def reset_test_data():
    """Очистка и заполнение тестовыми данными"""
    try:
        cassandra_manager.clear_tables()
        result = cassandra_manager.seed_test_data()
        return {
            "message": "Database reset with test data successfully",
            "created": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting data: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Принудительно подключаемся к БД перед запуском сервера
    try:
        logger.info("Connecting to Cassandra...")
        cassandra_manager.connect()
        
        if not cassandra_manager.is_connected:
            error_msg = "Connection flag is False after connect()"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        if cassandra_manager.session is None:
            error_msg = "Session is None after connect()"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        logger.info("Cassandra connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to Cassandra: {e}", exc_info=True)
        logger.error("Application will not start without database connection")
        raise
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
