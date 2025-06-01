"""
Template modules for generating modular plugin files
"""

from .models_template import ModelsTemplate
from .schemas_template import SchemasTemplate
from .services_template import ServicesTemplate
from .routes_template import RoutesTemplate
from .tasks_template import TasksTemplate
from .init_template import InitTemplate

__all__ = [
    'ModelsTemplate',
    'SchemasTemplate', 
    'ServicesTemplate',
    'RoutesTemplate',
    'TasksTemplate',
    'InitTemplate'
] 