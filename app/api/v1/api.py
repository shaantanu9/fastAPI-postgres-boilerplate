from fastapi import APIRouter
from app.api.v1.endpoints import user
from app.api.v1.endpoints import task 
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import bulk_operations
from app.api.v1.endpoints import procrastinate_tasks
from app.api.v1.endpoints import examples
from app.api.v1.endpoints import plugins

api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(task.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(bulk_operations.router, tags=["bulk-operations"])
api_router.include_router(procrastinate_tasks.router, prefix="/procrastinate", tags=["procrastinate-tasks"])
api_router.include_router(examples.router, prefix="/examples", tags=["examples"])
api_router.include_router(plugins.router, prefix="/system", tags=["plugin-management"])
