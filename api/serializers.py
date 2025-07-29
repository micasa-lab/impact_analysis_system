"""
Serializers for the Impact Analysis System API.

This module contains Django REST Framework serializers for converting
model instances to JSON and handling API request/response data.
"""

from rest_framework import serializers
from core.models import (
    Component, Runbook, Step, Flow, FlowComponent, 
    Connection, ImpactAnalysis
)
import yaml
import json


class ComponentSerializer(serializers.ModelSerializer):
    """Serializer for Component model."""
    
    runbook_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Component
        fields = [
            'id', 'name', 'description', 'business_function', 
            'component_type', 'metadata', 'is_active', 
            'runbook_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StepSerializer(serializers.ModelSerializer):
    """Serializer for Step model."""
    
    class Meta:
        model = Step
        fields = [
            'id', 'name', 'description', 'action_type', 
            'parameters', 'order', 'estimated_duration', 
            'is_critical', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RunbookSerializer(serializers.ModelSerializer):
    """Serializer for Runbook model."""
    
    steps = StepSerializer(many=True, read_only=True)
    step_count = serializers.ReadOnlyField()
    estimated_total_duration = serializers.ReadOnlyField()
    component_name = serializers.CharField(source='component.name', read_only=True)
    
    class Meta:
        model = Runbook
        fields = [
            'id', 'component', 'component_name', 'name', 'description', 
            'version', 'is_active', 'steps', 'step_count', 
            'estimated_total_duration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RunbookDetailSerializer(RunbookSerializer):
    """Detailed serializer for Runbook model with nested steps."""
    
    steps = StepSerializer(many=True, read_only=False)
    
    def create(self, validated_data):
        """Create runbook with nested steps."""
        steps_data = validated_data.pop('steps', [])
        runbook = Runbook.objects.create(**validated_data)
        
        for step_data in steps_data:
            Step.objects.create(runbook=runbook, **step_data)
        
        return runbook
    
    def update(self, instance, validated_data):
        """Update runbook with nested steps."""
        steps_data = validated_data.pop('steps', [])
        
        # Update runbook fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update steps
        if steps_data:
            # Delete existing steps and create new ones
            instance.steps.all().delete()
            for step_data in steps_data:
                Step.objects.create(runbook=instance, **step_data)
        
        return instance


class FlowComponentSerializer(serializers.ModelSerializer):
    """Serializer for FlowComponent model."""
    
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_type = serializers.CharField(source='component.component_type', read_only=True)
    component_details = ComponentSerializer(source='component', read_only=True)
    
    class Meta:
        model = FlowComponent
        fields = [
            'id', 'component', 'component_name', 'component_type',
            'component_details', 'position_x', 'position_y', 
            'configuration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Connection model."""
    
    source_component_name = serializers.CharField(
        source='source_component.component.name', read_only=True
    )
    target_component_name = serializers.CharField(
        source='target_component.component.name', read_only=True
    )
    
    class Meta:
        model = Connection
        fields = [
            'id', 'source_component', 'target_component', 
            'source_component_name', 'target_component_name',
            'connection_type', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FlowSerializer(serializers.ModelSerializer):
    """Serializer for Flow model."""
    
    component_count = serializers.SerializerMethodField()
    connection_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Flow
        fields = [
            'id', 'name', 'description', 'version', 'yaml_content',
            'is_active', 'component_count', 'connection_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def get_component_count(self, obj):
        return obj.flow_components.count()

class FlowDetailSerializer(FlowSerializer):
    """Detailed serializer for Flow model with nested components and connections."""
    
    flow_components = FlowComponentSerializer(many=True, read_only=True)
    connections = ConnectionSerializer(many=True, read_only=True)
    
    class Meta(FlowSerializer.Meta):
        fields = FlowSerializer.Meta.fields + ['flow_components', 'connections']


class ImpactAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for ImpactAnalysis model."""
    
    flow_name = serializers.CharField(source='flow.name', read_only=True)
    affected_component_name = serializers.CharField(
        source='affected_component.name', read_only=True
    )
    affected_components_details = ComponentSerializer(
        source='affected_components', many=True, read_only=True
    )
    
    class Meta:
        model = ImpactAnalysis
        fields = [
            'id', 'flow', 'flow_name', 'affected_component', 
            'affected_component_name', 'severity', 'affected_components',
            'affected_components_details', 'analysis_results', 
            'recommendations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ImpactAnalysisCreateSerializer(serializers.Serializer):
    flow_id = serializers.UUIDField()
    component_id = serializers.UUIDField()
    severity = serializers.ChoiceField(choices=['low', 'medium', 'high', 'critical'])
    description = serializers.CharField(required=False, allow_blank=True)
    analysis_type = serializers.ChoiceField(
        choices=['downstream', 'upstream', 'bidirectional', 'full_system'],
        default='downstream'
    )
    max_depth = serializers.IntegerField(default=3)
    include_inactive = serializers.BooleanField(default=False)
    
    def validate_flow_id(self, value):
        try:
            Flow.objects.get(pk=value)
            return value
        except Flow.DoesNotExist:
            raise serializers.ValidationError("Flow not found")
    
    def validate_component_id(self, value):
        try:
            Component.objects.get(pk=value)
            return value
        except Component.DoesNotExist:
            raise serializers.ValidationError("Component not found")


class YAMLFlowSerializer(serializers.Serializer):
    """Serializer for YAML flow import/export."""
    
    yaml_content = serializers.CharField()
    
    def validate_yaml_content(self, value):
        """Validate YAML content structure."""
        try:
            data = yaml.safe_load(value)
        except yaml.YAMLError as e:
            raise serializers.ValidationError(f"Invalid YAML format: {str(e)}")
        
        # Validate required fields
        if not isinstance(data, dict):
            raise serializers.ValidationError("YAML content must be a dictionary")
        
        # Check for required flow fields at root level
        required_fields = ['name', 'description', 'version']
        for field in required_fields:
            if field not in data:
                raise serializers.ValidationError(f"YAML must contain '{field}' field")
        
        # Validate components section
        if 'components' in data:
            if not isinstance(data['components'], list):
                raise serializers.ValidationError("Components must be a list")
            
            for i, component in enumerate(data['components']):
                if not isinstance(component, dict):
                    raise serializers.ValidationError(f"Component {i} must be a dictionary")
                
                required_component_fields = ['name', 'business_function', 'type']
                for field in required_component_fields:
                    if field not in component:
                        raise serializers.ValidationError(
                            f"Component {i} must contain '{field}' field"
                        )
        
        # Validate connections section
        if 'connections' in data:
            if not isinstance(data['connections'], list):
                raise serializers.ValidationError("Connections must be a list")
            
            for i, connection in enumerate(data['connections']):
                if not isinstance(connection, dict):
                    raise serializers.ValidationError(f"Connection {i} must be a dictionary")
                
                required_connection_fields = ['source', 'target', 'type']
                for field in required_connection_fields:
                    if field not in connection:
                        raise serializers.ValidationError(
                            f"Connection {i} must have '{field}' field"
                        )
        
        return value

    def create(self, validated_data):
        """Create or update flow from YAML data."""
        yaml_content = validated_data['yaml_content']
        
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise serializers.ValidationError(f"Invalid YAML: {e}")
        
        # Check if flow with same name and version already exists
        flow_name = data['name']
        flow_version = data['version']
        
        try:
            # Try to get existing flow
            flow = Flow.objects.get(name=flow_name, version=flow_version)
            
            # Clear existing flow components and connections
            FlowComponent.objects.filter(flow=flow).delete()
            Connection.objects.filter(flow=flow).delete()
            
            # Update flow details
            flow.description = data.get('description', '')
            flow.yaml_content = yaml_content
            flow.save()
            
        except Flow.DoesNotExist:
            # Create new flow if it doesn't exist
            flow = Flow.objects.create(
                name=flow_name,
                description=data.get('description', ''),
                version=flow_version,
                yaml_content=yaml_content,
                is_active=True
            )
        
        # Create components
        component_map = {}
        if 'components' in data:
            for i, comp_data in enumerate(data['components']):
                # Check if component already exists
                component, created = Component.objects.get_or_create(
                    name=comp_data['name'],
                    defaults={
                        'description': comp_data.get('description', ''),
                        'business_function': comp_data['business_function'],
                        'component_type': comp_data['type'],
                        'metadata': comp_data.get('metadata', {}),
                        'is_active': comp_data.get('is_active', True)
                    }
                )
                
                # Update component if it already exists
                if not created:
                    component.description = comp_data.get('description', component.description)
                    component.business_function = comp_data['business_function']
                    component.component_type = comp_data['type']
                    component.metadata.update(comp_data.get('metadata', {}))
                    component.is_active = comp_data.get('is_active', True)
                    component.save()
                
                # Create flow component
                position = comp_data.get('position', {})
                flow_component = FlowComponent.objects.create(
                    flow=flow,
                    component=component,
                    position_x=position.get('x', i * 200),  # Default positioning
                    position_y=position.get('y', i * 100),
                    configuration=comp_data.get('configuration', {})
                )
                
                component_map[comp_data['name']] = flow_component
                
                # Create runbooks if specified
                if 'runbooks' in comp_data:
                    for runbook_data in comp_data['runbooks']:
                        runbook, created = Runbook.objects.get_or_create(
                            component=component,
                            name=runbook_data['name'],
                            defaults={
                                'description': runbook_data.get('description', ''),
                                'is_active': True
                            }
                        )
                        
                        if not created:
                            # Update existing runbook
                            runbook.description = runbook_data.get('description', runbook.description)
                            runbook.save()
                            
                            # Clear existing steps
                            Step.objects.filter(runbook=runbook).delete()
                        
                        # Create steps if specified
                        if 'steps' in runbook_data:
                            for j, step_data in enumerate(runbook_data['steps']):
                                Step.objects.create(
                                    runbook=runbook,
                                    name=step_data['name'],
                                    description=step_data.get('description', ''),
                                    action_type='command',
                                    parameters={
                                        'command': step_data.get('command', ''),
                                        'expected_outcome': step_data.get('expected_outcome', '')
                                    },
                                    order=j + 1
                                )
        
        # Create connections
        if 'connections' in data:
            for conn_data in data['connections']:
                source_name = conn_data['source']
                target_name = conn_data['target']
                
                if source_name in component_map and target_name in component_map:
                    Connection.objects.create(
                        flow=flow,
                        source_component=component_map[source_name],
                        target_component=component_map[target_name],
                        connection_type=conn_data['type'],
                        metadata=conn_data.get('metadata', {})
                    )
        
        return flow


class FlowExportSerializer(serializers.ModelSerializer):
    """Serializer for exporting flow to YAML format."""
    
    class Meta:
        model = Flow
        fields = ['id', 'name', 'description', 'version']
    
    def to_representation(self, instance):
        """Convert flow to YAML format."""
        # Build flow data structure
        flow_data = {
            'flow': {
                'name': instance.name,
                'description': instance.description,
                'version': instance.version
            },
            'components': [],
            'connections': []
        }
        
        # Add components
        component_id_map = {}
        for flow_component in instance.flow_components.all():
            component = flow_component.component
            component_id = f"component-{component.id}"
            component_id_map[flow_component.id] = component_id
            
            comp_data = {
                'id': component_id,
                'name': component.name,
                'description': component.description,
                'business_function': component.business_function,
                'type': component.component_type,
                'position': {
                    'x': flow_component.position_x,
                    'y': flow_component.position_y
                },
                'metadata': component.metadata,
                'configuration': flow_component.configuration
            }
            
            # Add runbooks
            runbooks = []
            for runbook in component.runbooks.filter(is_active=True):
                runbook_data = {
                    'name': runbook.name,
                    'description': runbook.description,
                    'version': runbook.version,
                    'steps': []
                }
                
                # Add steps
                for step in runbook.steps.all():
                    step_data = {
                        'name': step.name,
                        'description': step.description,
                        'action': step.action_type,
                        'parameters': step.parameters,
                        'estimated_duration': step.estimated_duration
                    }
                    runbook_data['steps'].append(step_data)
                
                runbooks.append(runbook_data)
            
            if runbooks:
                comp_data['runbooks'] = runbooks
            
            flow_data['components'].append(comp_data)
        
        # Add connections
        for connection in instance.connections.all():
            source_id = component_id_map.get(connection.source_component.id)
            target_id = component_id_map.get(connection.target_component.id)
            
            if source_id and target_id:
                conn_data = {
                    'source': source_id,
                    'target': target_id,
                    'type': connection.connection_type,
                    'metadata': connection.metadata
                }
                flow_data['connections'].append(conn_data)
        
        # Convert to YAML
        yaml_content = yaml.dump(flow_data, default_flow_style=False, sort_keys=False)
        
        return {
            'id': instance.id,
            'name': instance.name,
            'yaml_content': yaml_content
        }

