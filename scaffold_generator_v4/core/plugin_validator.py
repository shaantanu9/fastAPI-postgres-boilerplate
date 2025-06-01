"""
Plugin validation and testing utilities
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Any


class PluginValidator:
    """Handles plugin validation and testing"""
    
    def __init__(self):
        self.required_files = [
            '__init__.py',
            'models.py',
            'schemas.py', 
            'services.py',
            'routes.py'
        ]
        
        self.optional_files = [
            'tasks.py',
            'repositories.py',
            'dependencies.py',
            'config.py'
        ]
    
    def validate_plugin_structure(self, plugin_path: Path) -> Dict[str, Any]:
        """Validate the structure of a plugin directory"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'files_found': [],
            'files_missing': []
        }
        
        if not plugin_path.exists():
            results['valid'] = False
            results['errors'].append(f"Plugin directory does not exist: {plugin_path}")
            return results
        
        # Check required files
        for required_file in self.required_files:
            file_path = plugin_path / required_file
            if file_path.exists():
                results['files_found'].append(required_file)
            else:
                results['files_missing'].append(required_file)
                results['errors'].append(f"Required file missing: {required_file}")
                results['valid'] = False
        
        # Check optional files
        for optional_file in self.optional_files:
            file_path = plugin_path / optional_file
            if file_path.exists():
                results['files_found'].append(optional_file)
        
        return results
    
    def validate_file_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Validate Python syntax of a file"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check syntax by parsing
            ast.parse(content)
            
            # Check for common issues
            issues = self._check_common_issues(content, file_path.name)
            results['warnings'].extend(issues)
            
        except SyntaxError as e:
            results['valid'] = False
            results['errors'].append(f"Syntax error in {file_path.name}: {e}")
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Error reading {file_path.name}: {e}")
        
        return results
    
    def _check_common_issues(self, content: str, filename: str) -> List[str]:
        """Check for common plugin issues"""
        issues = []
        
        # Check for malformed features list
        if 'features=["crud", "search"(' in content:
            issues.append(f"{filename}: Malformed features list detected")
        
        # Check for status override
        if 'self.metadata.status = PluginStatus.INITIALIZED' in content:
            issues.append(f"{filename}: Manual status override detected (should be managed by plugin system)")
        
        # Check for deprecated settings reference
        if 'settings.SECRET_KEY' in content:
            issues.append(f"{filename}: Deprecated settings.SECRET_KEY reference")
        
        # Check for missing async/await patterns
        if filename == 'services.py' and 'async def' not in content:
            issues.append(f"{filename}: Consider using async methods for better performance")
        
        return issues
    
    def validate_plugin(self, plugin_path: Path) -> Dict[str, Any]:
        """Comprehensive plugin validation"""
        results = {
            'valid': True,
            'structure': {},
            'syntax': {},
            'overall_errors': [],
            'overall_warnings': []
        }
        
        # Validate structure
        structure_results = self.validate_plugin_structure(plugin_path)
        results['structure'] = structure_results
        
        if not structure_results['valid']:
            results['valid'] = False
            results['overall_errors'].extend(structure_results['errors'])
        
        # Validate syntax of found files
        for file_name in structure_results['files_found']:
            file_path = plugin_path / file_name
            syntax_results = self.validate_file_syntax(file_path)
            results['syntax'][file_name] = syntax_results
            
            if not syntax_results['valid']:
                results['valid'] = False
                results['overall_errors'].extend(syntax_results['errors'])
            
            results['overall_warnings'].extend(syntax_results['warnings'])
        
        return results
    
    def test_plugin_generation(self, model_name: str, fields: List[str]) -> bool:
        """Test plugin generation without creating files"""
        try:
            # This would be called with the actual generators
            # For now, just validate the inputs
            
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', model_name):
                print(f"❌ Invalid model name: {model_name}. Must be PascalCase")
                return False
            
            if not fields:
                print("❌ No fields provided")
                return False
            
            # Basic field validation
            for field in fields:
                if ':' not in field:
                    print(f"❌ Invalid field format: {field}")
                    return False
            
            print(f"✅ Plugin generation test passed for {model_name}")
            return True
            
        except Exception as e:
            print(f"❌ Plugin generation test failed: {e}")
            return False
    
    def fix_common_issues(self, plugin_path: Path) -> List[str]:
        """Fix common issues in plugin files"""
        fixes_applied = []
        
        for file_name in self.required_files + self.optional_files:
            file_path = plugin_path / file_name
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                original_content = content
                
                # Fix malformed features list
                if 'features=["crud", "search"(' in content:
                    content = re.sub(
                        r'features=\["crud", "search"\([^)]*\)\([^)]*\)\]',
                        'features=["crud", "search", "tasks", "bulk"]',
                        content
                    )
                    fixes_applied.append(f"{file_name}: Fixed malformed features list")
                
                # Fix status override
                if 'self.metadata.status = PluginStatus.INITIALIZED' in content:
                    content = content.replace(
                        'self.metadata.status = PluginStatus.INITIALIZED',
                        '# Status will be set by plugin manager - don\'t override here'
                    )
                    fixes_applied.append(f"{file_name}: Removed status override")
                
                # Fix SECRET_KEY reference
                if 'settings.SECRET_KEY' in content:
                    content = content.replace('settings.SECRET_KEY', 'settings.jwt_secret_token')
                    fixes_applied.append(f"{file_name}: Fixed SECRET_KEY reference")
                
                # Write back if changes were made
                if content != original_content:
                    with open(file_path, 'w') as f:
                        f.write(content)
                
            except Exception as e:
                print(f"❌ Error fixing {file_name}: {e}")
        
        return fixes_applied 