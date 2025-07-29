"""
Utility functions for the Impact Analysis System.

This module contains helper functions for YAML processing, impact analysis,
and other common operations.
"""

import yaml
import json
from typing import Dict, List, Any, Optional
from django.conf import settings


class YAMLProcessor:
    """Utility class for processing YAML flow definitions."""
    
    @staticmethod
    def validate_yaml_structure(yaml_content: str) -> Dict[str, Any]:
        """
        Validate YAML content structure and return parsed data.
        
        Args:
            yaml_content: YAML content as string
            
        Returns:
            Dictionary containing parsed YAML data
            
        Raises:
            ValueError: If YAML structure is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")
        
        if not isinstance(data, dict):
            raise ValueError("YAML content must be a dictionary")
        
        # Validate required sections
        required_sections = ['flow']
        for section in required_sections:
            if section not in data:
                raise ValueError(f"YAML must contain '{section}' section")
        
        # Validate flow section
        flow_data = data['flow']
        required_flow_fields = ['name', 'description', 'version']
        for field in required_flow_fields:
            if field not in flow_data:
                raise ValueError(f"Flow must contain '{field}' field")
        
        return data
    
    @staticmethod
    def validate_components(components: List[Dict[str, Any]]) -> None:
        """
        Validate components section of YAML.
        
        Args:
            components: List of component dictionaries
            
        Raises:
            ValueError: If component structure is invalid
        """
        if not isinstance(components, list):
            raise ValueError("Components must be a list")
        
        component_ids = set()
        for i, component in enumerate(components):
            if not isinstance(component, dict):
                raise ValueError(f"Component {i} must be a dictionary")
            
            # Check required fields
            required_fields = ['id', 'name', 'business_function', 'type']
            for field in required_fields:
                if field not in component:
                    raise ValueError(f"Component {i} must contain '{field}' field")
            
            # Check for duplicate IDs
            comp_id = component['id']
            if comp_id in component_ids:
                raise ValueError(f"Duplicate component ID: {comp_id}")
            component_ids.add(comp_id)
            
            # Validate component type
            valid_types = [choice[0] for choice in settings.IMPACT_ANALYSIS['SUPPORTED_COMPONENT_TYPES']]
            if component['type'] not in valid_types:
                raise ValueError(f"Invalid component type: {component['type']}")
    
    @staticmethod
    def validate_connections(connections: List[Dict[str, Any]], component_ids: set) -> None:
        """
        Validate connections section of YAML.
        
        Args:
            connections: List of connection dictionaries
            component_ids: Set of valid component IDs
            
        Raises:
            ValueError: If connection structure is invalid
        """
        if not isinstance(connections, list):
            raise ValueError("Connections must be a list")
        
        for i, connection in enumerate(connections):
            if not isinstance(connection, dict):
                raise ValueError(f"Connection {i} must be a dictionary")
            
            # Check required fields
            required_fields = ['source', 'target', 'type']
            for field in required_fields:
                if field not in connection:
                    raise ValueError(f"Connection {i} must contain '{field}' field")
            
            # Validate component references
            source_id = connection['source']
            target_id = connection['target']
            
            if source_id not in component_ids:
                raise ValueError(f"Connection {i} references unknown source component: {source_id}")
            
            if target_id not in component_ids:
                raise ValueError(f"Connection {i} references unknown target component: {target_id}")
            
            if source_id == target_id:
                raise ValueError(f"Connection {i} cannot connect component to itself")


class ImpactAnalyzer:
    """Utility class for performing impact analysis."""
    
    @staticmethod
    def analyze_component_impact(flow, component) -> Dict[str, Any]:
        """
        Analyze the impact of a component failure in a flow.
        
        Args:
            flow: Flow instance
            component: Component instance
            
        Returns:
            Dictionary containing impact analysis results
        """
        from .models import FlowComponent, Connection
        
        # Find the flow component
        try:
            flow_component = FlowComponent.objects.get(flow=flow, component=component)
        except FlowComponent.DoesNotExist:
            return {
                'error': 'Component not found in flow',
                'affected_components': [],
                'severity': 'none'
            }
        
        # Find directly connected components
        outgoing_connections = Connection.objects.filter(
            flow=flow, source_component=flow_component
        )
        incoming_connections = Connection.objects.filter(
            flow=flow, target_component=flow_component
        )
        
        directly_affected = set()
        for conn in outgoing_connections:
            directly_affected.add(conn.target_component.component)
        for conn in incoming_connections:
            directly_affected.add(conn.source_component.component)
        
        # Perform recursive impact analysis
        all_affected = ImpactAnalyzer._recursive_impact_analysis(
            flow, flow_component, set(), max_depth=3
        )
        
        # Determine severity
        severity = ImpactAnalyzer._calculate_severity(len(all_affected))
        
        # Generate recommendations
        recommendations = ImpactAnalyzer._generate_recommendations(
            component, directly_affected, all_affected
        )
        
        return {
            'affected_component': component,
            'directly_affected': list(directly_affected),
            'all_affected': list(all_affected),
            'severity': severity,
            'recommendations': recommendations,
            'analysis_metadata': {
                'direct_impact_count': len(directly_affected),
                'total_impact_count': len(all_affected),
                'analysis_depth': 3
            }
        }
    
    @staticmethod
    def _recursive_impact_analysis(flow, flow_component, visited, max_depth=3, current_depth=0):
        """
        Recursively analyze impact propagation.
        
        Args:
            flow: Flow instance
            flow_component: Starting FlowComponent
            visited: Set of already visited components
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
            
        Returns:
            Set of affected components
        """
        from .models import Connection
        
        if current_depth >= max_depth or flow_component in visited:
            return set()
        
        visited.add(flow_component)
        affected = {flow_component.component}
        
        # Find outgoing connections
        outgoing_connections = Connection.objects.filter(
            flow=flow, source_component=flow_component
        )
        
        for conn in outgoing_connections:
            target_component = conn.target_component
            if target_component not in visited:
                affected.add(target_component.component)
                # Recursively analyze impact
                recursive_affected = ImpactAnalyzer._recursive_impact_analysis(
                    flow, target_component, visited.copy(), max_depth, current_depth + 1
                )
                affected.update(recursive_affected)
        
        return affected
    
    @staticmethod
    def _calculate_severity(impact_count: int) -> str:
        """
        Calculate severity based on number of affected components.
        
        Args:
            impact_count: Number of affected components
            
        Returns:
            Severity level string
        """
        if impact_count >= 10:
            return 'critical'
        elif impact_count >= 5:
            return 'high'
        elif impact_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _generate_recommendations(component, directly_affected, all_affected) -> str:
        """
        Generate recommendations based on impact analysis.
        
        Args:
            component: Affected component
            directly_affected: Set of directly affected components
            all_affected: Set of all affected components
            
        Returns:
            Recommendations string
        """
        recommendations = []
        
        if len(directly_affected) > 0:
            recommendations.append(
                f"Immediately review {len(directly_affected)} directly connected components."
            )
        
        if len(all_affected) > len(directly_affected):
            cascade_count = len(all_affected) - len(directly_affected)
            recommendations.append(
                f"Monitor {cascade_count} components that may be affected by cascade failures."
            )
        
        if component.component_type == 'database':
            recommendations.append(
                "Consider implementing database failover and backup procedures."
            )
        elif component.component_type == 'api':
            recommendations.append(
                "Implement API circuit breakers and retry mechanisms."
            )
        elif component.component_type == 'service':
            recommendations.append(
                "Review service health checks and auto-scaling policies."
            )
        
        recommendations.append(
            f"Execute relevant runbooks for {component.name} to mitigate impact."
        )
        
        return " ".join(recommendations)


class FlowValidator:
    """Utility class for validating flow configurations."""
    
    @staticmethod
    def validate_flow_integrity(flow) -> Dict[str, Any]:
        """
        Validate the integrity of a flow configuration.
        
        Args:
            flow: Flow instance
            
        Returns:
            Dictionary containing validation results
        """
        from .models import FlowComponent, Connection
        
        issues = []
        warnings = []
        
        # Check for orphaned components
        flow_components = FlowComponent.objects.filter(flow=flow)
        connected_components = set()
        
        connections = Connection.objects.filter(flow=flow)
        for conn in connections:
            connected_components.add(conn.source_component.id)
            connected_components.add(conn.target_component.id)
        
        orphaned_components = []
        for fc in flow_components:
            if fc.id not in connected_components:
                orphaned_components.append(fc.component.name)
        
        if orphaned_components:
            warnings.append(f"Orphaned components (no connections): {', '.join(orphaned_components)}")
        
        # Check for circular dependencies
        circular_deps = FlowValidator._detect_circular_dependencies(flow)
        if circular_deps:
            issues.append(f"Circular dependencies detected: {circular_deps}")
        
        # Check for missing critical components
        component_types = set(fc.component.component_type for fc in flow_components)
        if 'database' not in component_types:
            warnings.append("No database components found in flow")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'component_count': flow_components.count(),
            'connection_count': connections.count()
        }
    
    @staticmethod
    def _detect_circular_dependencies(flow) -> List[str]:
        """
        Detect circular dependencies in flow connections.
        
        Args:
            flow: Flow instance
            
        Returns:
            List of circular dependency descriptions
        """
        from .models import Connection
        
        # Build adjacency list
        graph = {}
        connections = Connection.objects.filter(flow=flow)
        
        for conn in connections:
            source_id = conn.source_component.id
            target_id = conn.target_component.id
            
            if source_id not in graph:
                graph[source_id] = []
            graph[source_id].append(target_id)
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle_path = path[cycle_start:] + [node]
                cycles.append(" -> ".join(str(n) for n in cycle_path))
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [neighbor])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [node])
        
        return cycles

