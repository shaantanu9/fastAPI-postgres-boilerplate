"""
Architecture Analyzer for FastAPI Projects

Provides comprehensive analysis of project architecture including:
- Plugin dependency analysis and visualization
- Code organization assessment
- Architecture pattern compliance
- Scalability recommendations
- Integration health checks
"""

import ast
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import importlib.util


@dataclass
class PluginInfo:
    """Information about a plugin"""
    name: str
    path: Path
    models: List[str]
    routes: List[str]
    dependencies: List[str]
    size_metrics: Dict[str, int]
    complexity_score: float


@dataclass
class DependencyIssue:
    """Represents a dependency issue"""
    type: str  # 'circular', 'missing', 'unused'
    source: str
    target: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    suggestion: str


@dataclass
class ArchitectureReport:
    """Complete architecture analysis report"""
    plugins: List[PluginInfo]
    dependency_graph: Dict[str, List[str]]
    issues: List[DependencyIssue]
    metrics: Dict[str, Any]
    recommendations: List[str]
    health_score: float


class ArchitectureAnalyzer:
    """Analyzes FastAPI project architecture and provides optimization suggestions"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.app_path = self.project_root / "app"
        self.plugins_path = self.app_path / "plugins"
        
    def analyze_project(self) -> ArchitectureReport:
        """Perform comprehensive architecture analysis"""
        print("🔍 Analyzing Project Architecture...")
        print("=" * 50)
        
        # Analyze plugins
        plugins = self._analyze_plugins()
        print(f"✅ Analyzed {len(plugins)} plugins")
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(plugins)
        print(f"✅ Built dependency graph with {len(dependency_graph)} nodes")
        
        # Detect issues
        issues = self._detect_issues(plugins, dependency_graph)
        print(f"✅ Detected {len(issues)} potential issues")
        
        # Calculate metrics
        metrics = self._calculate_metrics(plugins, dependency_graph)
        print(f"✅ Calculated architecture metrics")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(plugins, issues, metrics)
        print(f"✅ Generated {len(recommendations)} recommendations")
        
        # Calculate health score
        health_score = self._calculate_health_score(issues, metrics)
        print(f"✅ Architecture health score: {health_score:.1f}%")
        
        return ArchitectureReport(
            plugins=plugins,
            dependency_graph=dependency_graph,
            issues=issues,
            metrics=metrics,
            recommendations=recommendations,
            health_score=health_score
        )
    
    def _analyze_plugins(self) -> List[PluginInfo]:
        """Analyze all plugins in the project"""
        plugins = []
        
        if not self.plugins_path.exists():
            return plugins
            
        for plugin_dir in self.plugins_path.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith('__'):
                plugin_info = self._analyze_single_plugin(plugin_dir)
                if plugin_info:
                    plugins.append(plugin_info)
                    
        return plugins
    
    def _analyze_single_plugin(self, plugin_path: Path) -> PluginInfo:
        """Analyze a single plugin"""
        try:
            models = self._extract_models(plugin_path / "models.py")
            routes = self._extract_routes(plugin_path / "routes.py")
            dependencies = self._extract_dependencies(plugin_path)
            size_metrics = self._calculate_size_metrics(plugin_path)
            complexity_score = self._calculate_complexity_score(plugin_path)
            
            return PluginInfo(
                name=plugin_path.name,
                path=plugin_path,
                models=models,
                routes=routes,
                dependencies=dependencies,
                size_metrics=size_metrics,
                complexity_score=complexity_score
            )
        except Exception as e:
            print(f"⚠️ Warning: Could not analyze plugin {plugin_path.name}: {e}")
            return None
    
    def _extract_models(self, models_file: Path) -> List[str]:
        """Extract model names from models.py"""
        models = []
        if not models_file.exists():
            return models
            
        try:
            with open(models_file, 'r') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a SQLAlchemy model
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'Base':
                            models.append(node.name)
                            break
        except Exception as e:
            print(f"⚠️ Warning: Could not parse {models_file}: {e}")
            
        return models
    
    def _extract_routes(self, routes_file: Path) -> List[str]:
        """Extract route endpoints from routes.py"""
        routes = []
        if not routes_file.exists():
            return routes
            
        try:
            with open(routes_file, 'r') as f:
                content = f.read()
                
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Look for FastAPI route decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                    routes.append(f"{decorator.func.attr.upper()} {node.name}")
        except Exception as e:
            print(f"⚠️ Warning: Could not parse {routes_file}: {e}")
            
        return routes
    
    def _extract_dependencies(self, plugin_path: Path) -> List[str]:
        """Extract dependencies from plugin files"""
        dependencies = set()
        
        for py_file in plugin_path.glob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    tree = ast.parse(f.read())
                    
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            dependencies.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            dependencies.add(node.module.split('.')[0])
            except Exception:
                continue
                
        # Filter to only app-related dependencies
        app_dependencies = [dep for dep in dependencies if dep.startswith('app')]
        return app_dependencies
    
    def _calculate_size_metrics(self, plugin_path: Path) -> Dict[str, int]:
        """Calculate size metrics for a plugin"""
        metrics = {
            'total_files': 0,
            'total_lines': 0,
            'python_files': 0,
            'python_lines': 0
        }
        
        for file_path in plugin_path.rglob("*"):
            if file_path.is_file():
                metrics['total_files'] += 1
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        metrics['total_lines'] += lines
                        
                        if file_path.suffix == '.py':
                            metrics['python_files'] += 1
                            metrics['python_lines'] += lines
                except Exception:
                    continue
                    
        return metrics
    
    def _calculate_complexity_score(self, plugin_path: Path) -> float:
        """Calculate complexity score for a plugin"""
        total_complexity = 0
        file_count = 0
        
        for py_file in plugin_path.glob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    tree = ast.parse(f.read())
                    
                complexity = self._calculate_cyclomatic_complexity(tree)
                total_complexity += complexity
                file_count += 1
            except Exception:
                continue
                
        return total_complexity / max(file_count, 1)
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
                
        return complexity
    
    def _build_dependency_graph(self, plugins: List[PluginInfo]) -> Dict[str, List[str]]:
        """Build dependency graph between plugins"""
        graph = defaultdict(list)
        
        for plugin in plugins:
            for dep in plugin.dependencies:
                # Check if dependency is another plugin
                dep_plugin = self._find_plugin_by_module(dep, plugins)
                if dep_plugin and dep_plugin != plugin.name:
                    graph[plugin.name].append(dep_plugin)
                    
        return dict(graph)
    
    def _find_plugin_by_module(self, module: str, plugins: List[PluginInfo]) -> str:
        """Find plugin name by module path"""
        for plugin in plugins:
            if f"plugins.{plugin.name}" in module or plugin.name in module:
                return plugin.name
        return None
    
    def _detect_issues(self, plugins: List[PluginInfo], dependency_graph: Dict[str, List[str]]) -> List[DependencyIssue]:
        """Detect various architecture issues"""
        issues = []
        
        # Detect circular dependencies
        issues.extend(self._detect_circular_dependencies(dependency_graph))
        
        # Detect overly complex plugins
        issues.extend(self._detect_complex_plugins(plugins))
        
        # Detect large plugins
        issues.extend(self._detect_large_plugins(plugins))
        
        # Detect unused dependencies
        issues.extend(self._detect_unused_dependencies(plugins))
        
        return issues
    
    def _detect_circular_dependencies(self, graph: Dict[str, List[str]]) -> List[DependencyIssue]:
        """Detect circular dependencies in the dependency graph"""
        issues = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found circular dependency
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                issues.append(DependencyIssue(
                    type='circular',
                    source=cycle[0],
                    target=cycle[-1],
                    severity='high',
                    description=f"Circular dependency detected: {' -> '.join(cycle)}",
                    suggestion="Refactor to remove circular dependency by extracting common functionality"
                ))
                return True
                
            if node in visited:
                return False
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if dfs(neighbor, path + [neighbor]):
                    return True
                    
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                dfs(node, [node])
                
        return issues
    
    def _detect_complex_plugins(self, plugins: List[PluginInfo]) -> List[DependencyIssue]:
        """Detect overly complex plugins"""
        issues = []
        
        for plugin in plugins:
            if plugin.complexity_score > 20:  # Threshold for high complexity
                issues.append(DependencyIssue(
                    type='complexity',
                    source=plugin.name,
                    target='',
                    severity='medium' if plugin.complexity_score < 30 else 'high',
                    description=f"Plugin {plugin.name} has high complexity score: {plugin.complexity_score:.1f}",
                    suggestion="Consider breaking down complex functions and reducing nested logic"
                ))
                
        return issues
    
    def _detect_large_plugins(self, plugins: List[PluginInfo]) -> List[DependencyIssue]:
        """Detect overly large plugins"""
        issues = []
        
        for plugin in plugins:
            lines = plugin.size_metrics.get('python_lines', 0)
            if lines > 1000:  # Threshold for large plugins
                issues.append(DependencyIssue(
                    type='size',
                    source=plugin.name,
                    target='',
                    severity='medium' if lines < 2000 else 'high',
                    description=f"Plugin {plugin.name} is large: {lines} lines of Python code",
                    suggestion="Consider splitting into multiple smaller plugins or modules"
                ))
                
        return issues
    
    def _detect_unused_dependencies(self, plugins: List[PluginInfo]) -> List[DependencyIssue]:
        """Detect potentially unused dependencies"""
        issues = []
        
        # This is a simplified check - in practice, you'd want more sophisticated analysis
        for plugin in plugins:
            if len(plugin.dependencies) > 10:  # Many dependencies might indicate unused ones
                issues.append(DependencyIssue(
                    type='dependencies',
                    source=plugin.name,
                    target='',
                    severity='low',
                    description=f"Plugin {plugin.name} has many dependencies ({len(plugin.dependencies)})",
                    suggestion="Review dependencies and remove unused imports"
                ))
                
        return issues
    
    def _calculate_metrics(self, plugins: List[PluginInfo], dependency_graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """Calculate overall architecture metrics"""
        total_lines = sum(p.size_metrics.get('python_lines', 0) for p in plugins)
        avg_complexity = sum(p.complexity_score for p in plugins) / max(len(plugins), 1)
        
        return {
            'total_plugins': len(plugins),
            'total_models': sum(len(p.models) for p in plugins),
            'total_routes': sum(len(p.routes) for p in plugins),
            'total_lines_of_code': total_lines,
            'average_complexity': avg_complexity,
            'dependency_connections': sum(len(deps) for deps in dependency_graph.values()),
            'plugins_with_dependencies': len([p for p in plugins if p.dependencies]),
            'largest_plugin_lines': max((p.size_metrics.get('python_lines', 0) for p in plugins), default=0),
            'most_complex_plugin': max((p.complexity_score for p in plugins), default=0)
        }
    
    def _generate_recommendations(self, plugins: List[PluginInfo], issues: List[DependencyIssue], metrics: Dict[str, Any]) -> List[str]:
        """Generate architecture improvement recommendations"""
        recommendations = []
        
        # Plugin organization recommendations
        if metrics['total_plugins'] > 10:
            recommendations.append("Consider organizing plugins into categories/modules for better maintainability")
            
        if metrics['average_complexity'] > 15:
            recommendations.append("Overall code complexity is high - consider refactoring complex functions")
            
        # Dependency recommendations
        if metrics['dependency_connections'] > metrics['total_plugins'] * 2:
            recommendations.append("High plugin interdependency detected - consider reducing coupling")
            
        # Size recommendations
        if metrics['largest_plugin_lines'] > 1500:
            recommendations.append("Some plugins are very large - consider splitting into smaller modules")
            
        # Issue-based recommendations
        critical_issues = [i for i in issues if i.severity == 'critical']
        if critical_issues:
            recommendations.append("Address critical architecture issues immediately")
            
        high_issues = [i for i in issues if i.severity == 'high']
        if high_issues:
            recommendations.append("Prioritize fixing high-severity architecture issues")
            
        # Performance recommendations
        if metrics['total_lines_of_code'] > 10000:
            recommendations.append("Large codebase detected - consider implementing code splitting and lazy loading")
            
        # Testing recommendations
        recommendations.append("Implement comprehensive integration tests for plugin interactions")
        recommendations.append("Add performance benchmarks for critical plugin operations")
        
        return recommendations
    
    def _calculate_health_score(self, issues: List[DependencyIssue], metrics: Dict[str, Any]) -> float:
        """Calculate overall architecture health score (0-100)"""
        base_score = 100.0
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == 'critical':
                base_score -= 20
            elif issue.severity == 'high':
                base_score -= 10
            elif issue.severity == 'medium':
                base_score -= 5
            elif issue.severity == 'low':
                base_score -= 2
                
        # Deduct points for complexity
        if metrics['average_complexity'] > 20:
            base_score -= 10
        elif metrics['average_complexity'] > 15:
            base_score -= 5
            
        # Deduct points for size issues
        if metrics['largest_plugin_lines'] > 2000:
            base_score -= 10
        elif metrics['largest_plugin_lines'] > 1000:
            base_score -= 5
            
        return max(0.0, min(100.0, base_score))
    
    def generate_report(self, report: ArchitectureReport, output_file: Path = None) -> str:
        """Generate a detailed architecture analysis report"""
        output = []
        output.append("# 🏗️ FastAPI Project Architecture Analysis Report")
        output.append("=" * 60)
        output.append("")
        
        # Executive Summary
        output.append("## 📊 Executive Summary")
        output.append(f"**Architecture Health Score: {report.health_score:.1f}%**")
        output.append("")
        output.append(f"- **Total Plugins:** {report.metrics['total_plugins']}")
        output.append(f"- **Total Models:** {report.metrics['total_models']}")
        output.append(f"- **Total Routes:** {report.metrics['total_routes']}")
        output.append(f"- **Lines of Code:** {report.metrics['total_lines_of_code']:,}")
        output.append(f"- **Average Complexity:** {report.metrics['average_complexity']:.1f}")
        output.append("")
        
        # Issues Summary
        if report.issues:
            output.append("## ⚠️ Issues Detected")
            issue_counts = defaultdict(int)
            for issue in report.issues:
                issue_counts[issue.severity] += 1
                
            for severity in ['critical', 'high', 'medium', 'low']:
                if issue_counts[severity] > 0:
                    output.append(f"- **{severity.title()}:** {issue_counts[severity]} issues")
            output.append("")
            
            # Detailed issues
            for issue in sorted(report.issues, key=lambda x: ['critical', 'high', 'medium', 'low'].index(x.severity)):
                output.append(f"### {issue.severity.title()}: {issue.type.title()} Issue")
                output.append(f"**Source:** {issue.source}")
                if issue.target:
                    output.append(f"**Target:** {issue.target}")
                output.append(f"**Description:** {issue.description}")
                output.append(f"**Suggestion:** {issue.suggestion}")
                output.append("")
        
        # Plugin Details
        output.append("## 🔌 Plugin Analysis")
        for plugin in sorted(report.plugins, key=lambda x: x.complexity_score, reverse=True):
            output.append(f"### {plugin.name}")
            output.append(f"- **Models:** {len(plugin.models)} ({', '.join(plugin.models)})")
            output.append(f"- **Routes:** {len(plugin.routes)}")
            output.append(f"- **Dependencies:** {len(plugin.dependencies)}")
            output.append(f"- **Lines of Code:** {plugin.size_metrics.get('python_lines', 0)}")
            output.append(f"- **Complexity Score:** {plugin.complexity_score:.1f}")
            output.append("")
        
        # Recommendations
        if report.recommendations:
            output.append("## 💡 Recommendations")
            for i, rec in enumerate(report.recommendations, 1):
                output.append(f"{i}. {rec}")
            output.append("")
        
        # Dependency Graph
        if report.dependency_graph:
            output.append("## 🔗 Plugin Dependencies")
            for plugin, deps in report.dependency_graph.items():
                if deps:
                    output.append(f"- **{plugin}** → {', '.join(deps)}")
            output.append("")
        
        report_text = "\n".join(output)
        
        if output_file:
            output_file.write_text(report_text)
            print(f"📄 Report saved to: {output_file}")
            
        return report_text 