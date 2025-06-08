"""Template modules for generating modular plugin files."""

from .auth_models_template import AuthModelsTemplate
from .auth_routes_template import AuthRoutesTemplate
from .enhanced_routes_template import EnhancedRoutesTemplate
from .init_template import InitTemplate
from .models_template import ModelsTemplate
from .routes_template import RoutesTemplate
from .schemas_template import SchemasTemplate
from .services_template import ServicesTemplate
from .tasks_template import TasksTemplate

__all__ = [
    "AuthModelsTemplate",
    "AuthRoutesTemplate",
    "EnhancedRoutesTemplate",
    "InitTemplate",
    "ModelsTemplate",
    "RoutesTemplate",
    "SchemasTemplate",
    "ServicesTemplate",
    "TasksTemplate",
]
