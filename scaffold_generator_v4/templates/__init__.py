"""
Template modules for generating modular plugin files
"""

from .models_template import ModelsTemplate
from .schemas_template import SchemasTemplate
from .services_template import ServicesTemplate
from .routes_template import RoutesTemplate
from .tasks_template import TasksTemplate
from .init_template import InitTemplate
from .auth_routes_template import AuthRoutesTemplate
from .auth_models_template import AuthModelsTemplate

__all__ = [
    'ModelsTemplate',
    'SchemasTemplate', 
    'ServicesTemplate',
    'RoutesTemplate',
    'TasksTemplate',
    'InitTemplate',
    'AuthRoutesTemplate',
    'AuthModelsTemplate'
] 