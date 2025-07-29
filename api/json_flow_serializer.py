"""
JSON Flow Serializer for the new PayShield structure format.

This module handles the import and processing of JSON-based flow definitions
with the new structure that includes system_name, system_purpose, owned_by, kpis, and flows.
"""

import json
from rest_framework import serializers
from core.models import Flow, Component, FlowComponent, Connection


class JSONFlowSerializer(serializers.Serializer):
    """Serializer for JSON flow import/export with the new structure."""
    
    json_content = serializers.CharField()
    
    def validate_json_content(self, value):
        """Validate JSON content structure."""
        try:
            data = json.loads(value)
        except json.JSONDecodeError as e:
            raise serializers.ValidationError(f"Invalid JSON format: {str(e)}")
        
        # Validate required fields
        if not isinstance(data, dict):
            raise serializers.ValidationError("JSON content must be a dictionary")
        
        # Check for required flow fields at root level
        required_fields = ['system_name', 'system_purpose', 'components']
        for field in required_fields:
            if field not in data:
                raise serializers.ValidationError(f"JSON must contain '{field}' field")
        
        # Validate components section
        if 'components' in data:
            if not isinstance(data['components'], list):
                raise serializers.ValidationError("Components must be a list")
            
            for i, component in enumerate(data['components']):
                if not isinstance(component, dict):
                    raise serializers.ValidationError(f"Component {i} must be a dictionary")
                
                required_component_fields = ['component_name', 'business_function', 'owned_by', 'kpis', 'flows']
                for field in required_component_fields:
                    if field not in component:
                        raise serializers.ValidationError(
                            f"Component {i} must contain '{field}' field"
                        )
                
                # Validate flows within component
                if not isinstance(component['flows'], list):
                    raise serializers.ValidationError(f"Component {i} flows must be a list")
                
                for j, flow in enumerate(component['flows']):
                    if not isinstance(flow, dict):
                        raise serializers.ValidationError(f"Component {i} flow {j} must be a dictionary")
                    
                    required_flow_fields = ['type', 'source', 'target', 'description']
                    for field in required_flow_fields:
                        if field not in flow:
                            raise serializers.ValidationError(
                                f"Component {i} flow {j} must have '{field}' field"
                            )
        
        return value

    def create(self, validated_data):
        """Create or update flow from JSON data."""
        json_content = validated_data['json_content']
        
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise serializers.ValidationError(f"Invalid JSON: {e}")
        
        # Extract system information
        system_name = data['system_name']
        system_purpose = data['system_purpose']
        
        # Create flow name from system name
        flow_name = f"{system_name} Flow"
        flow_version = "1.0"
        
        # Check if flow with same name and version already exists
        try:
            # Try to get existing flow
            flow = Flow.objects.get(name=flow_name, version=flow_version)
            
            # Clear existing flow components and connections
            FlowComponent.objects.filter(flow=flow).delete()
            Connection.objects.filter(flow=flow).delete()
            
            # Update flow details
            flow.description = system_purpose
            flow.system_name = system_name
            flow.system_purpose = system_purpose
            flow.yaml_content = json_content
            flow.save()
            
        except Flow.DoesNotExist:
            # Create new flow if it doesn't exist
            flow = Flow.objects.create(
                name=flow_name,
                description=system_purpose,
                system_name=system_name,
                system_purpose=system_purpose,
                version=flow_version,
                yaml_content=json_content,
                is_active=True
            )
        
        # Create components
        component_map = {}
        if 'components' in data:
            for i, comp_data in enumerate(data['components']):
                # Map component type based on business function
                component_type = self._determine_component_type(comp_data['business_function'])
                
                # Check if component already exists
                component, created = Component.objects.get_or_create(
                    name=comp_data['component_name'],
                    defaults={
                        'description': comp_data.get('description', ''),
                        'business_function': comp_data['business_function'],
                        'component_type': component_type,
                        'owned_by': comp_data['owned_by'],
                        'kpis': comp_data['kpis'],
                        'metadata': {},
                        'is_active': True
                    }
                )
                
                # Update component if it already exists
                if not created:
                    component.business_function = comp_data['business_function']
                    component.component_type = component_type
                    component.owned_by = comp_data['owned_by']
                    component.kpis = comp_data['kpis']
                    component.is_active = True
                    component.save()
                
                # Create flow component
                flow_component = FlowComponent.objects.create(
                    flow=flow,
                    component=component,
                    position_x=i * 200,  # Default positioning
                    position_y=i * 100,
                    configuration={}
                )
                
                component_map[comp_data['component_name']] = flow_component
        
        # Create connections from flows
        connection_count = 0
        if 'components' in data:
            for comp_data in data['components']:
                source_component = component_map.get(comp_data['component_name'])
                
                if source_component and 'flows' in comp_data:
                    for flow_data in comp_data['flows']:
                        # Find target component
                        target_name = flow_data['target']
                        target_component = component_map.get(target_name)
                        
                        # If target is not in our component map, create a placeholder
                        if not target_component and target_name not in component_map:
                            # Create external component
                            external_component, created = Component.objects.get_or_create(
                                name=target_name,
                                defaults={
                                    'description': f'External component: {target_name}',
                                    'business_function': 'External system or service',
                                    'component_type': 'external_service',
                                    'owned_by': 'External',
                                    'kpis': [],
                                    'metadata': {},
                                    'is_active': True
                                }
                            )
                            
                            # Create flow component for external
                            target_component = FlowComponent.objects.create(
                                flow=flow,
                                component=external_component,
                                position_x=len(component_map) * 200,
                                position_y=len(component_map) * 100,
                                configuration={}
                            )
                            
                            component_map[target_name] = target_component
                        
                        if target_component:
                            # Create connection
                            Connection.objects.create(
                                flow=flow,
                                source_component=source_component,
                                target_component=target_component,
                                connection_type=self._map_connection_type(flow_data['type']),
                                flow_type=flow_data['type'],
                                source=flow_data['source'],
                                target=flow_data['target'],
                                metadata={
                                    'description': flow_data['description'],
                                    'original_type': flow_data['type']
                                }
                            )
                            connection_count += 1
        
        return {
            'flow': flow,
            'components_created': len(component_map),
            'connections_created': connection_count,
            'message': f'Successfully imported {system_name} with {len(component_map)} components and {connection_count} connections'
        }
    
    def _determine_component_type(self, business_function):
        """Determine component type based on business function."""
        business_function_lower = business_function.lower()
        
        if any(keyword in business_function_lower for keyword in ['api', 'gateway', 'endpoint']):
            return 'api'
        elif any(keyword in business_function_lower for keyword in ['database', 'storage', 'data']):
            return 'database'
        elif any(keyword in business_function_lower for keyword in ['queue', 'message', 'broker']):
            return 'middleware'
        elif any(keyword in business_function_lower for keyword in ['ui', 'frontend', 'interface']):
            return 'frontend'
        elif any(keyword in business_function_lower for keyword in ['external', 'third-party', 'partner']):
            return 'external_service'
        else:
            return 'service'
    
    def _map_connection_type(self, flow_type):
        """Map flow type to connection type."""
        type_mapping = {
            'external_user_triggered': 'api',
            'internal': 'internal',
            'external_system_triggered': 'api'
        }
        return type_mapping.get(flow_type, 'api')

