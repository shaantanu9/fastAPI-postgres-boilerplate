from fastapi import APIRouter
from app.api.v1.endpoints import user, task, auth, bulk_operations, procrastinate_tasks, examples, plugins

api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(task.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(bulk_operations.router, tags=["bulk-operations"])
api_router.include_router(procrastinate_tasks.router, prefix="/procrastinate", tags=["procrastinate-tasks"])
api_router.include_router(examples.router, prefix="/examples", tags=["examples"])
api_router.include_router(plugins.router, prefix="/system", tags=["plugin-management"])
