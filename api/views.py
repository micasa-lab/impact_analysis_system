"""
API views for the Impact Analysis System.

This module contains Django REST Framework viewsets and views for handling
API requests for components, runbooks, flows, and YAML processing.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
import yaml
import json

from core.models import (
    Component, Runbook, Step, Flow, FlowComponent, 
    Connection, ImpactAnalysis
)
from .serializers import (
    ComponentSerializer, RunbookSerializer, RunbookDetailSerializer,
    StepSerializer, FlowSerializer, FlowDetailSerializer,
    FlowComponentSerializer, ConnectionSerializer,
    ImpactAnalysisSerializer, YAMLFlowSerializer, FlowExportSerializer
)
from .json_flow_serializer import JSONFlowSerializer


class ComponentViewSet(viewsets.ModelViewSet):
    """ViewSet for Component model."""
    
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  # Allow read access without auth
    filterset_fields = ['component_type', 'is_active']
    search_fields = ['name', 'description', 'business_function']
    ordering_fields = ['name', 'component_type', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a component."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def runbooks(self, request, pk=None):
        """Get all runbooks for a specific component."""
        component = self.get_object()
        runbooks = component.runbooks.filter(is_active=True)
        serializer = RunbookSerializer(runbooks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def flows(self, request, pk=None):
        """Get all flows that contain this component."""
        component = self.get_object()
        flow_components = FlowComponent.objects.filter(component=component)
        flows = [fc.flow for fc in flow_components]
        serializer = FlowSerializer(flows, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available component types."""
        types = [{'value': choice[0], 'label': choice[1]} 
                for choice in Component.COMPONENT_TYPES]
        return Response(types)


class RunbookViewSet(viewsets.ModelViewSet):
    """ViewSet for Runbook model."""
    
    queryset = Runbook.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['component', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'component__name', 'created_at']
    ordering = ['component__name', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update', 'retrieve']:
            return RunbookDetailSerializer
        return RunbookSerializer
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a runbook."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        """Get all steps for a specific runbook."""
        runbook = self.get_object()
        steps = runbook.steps.all()
        serializer = StepSerializer(steps, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Simulate runbook execution (placeholder for actual implementation)."""
        runbook = self.get_object()
        
        # This is a placeholder for actual runbook execution logic
        # In a real implementation, this would execute the steps
        execution_result = {
            'runbook_id': str(runbook.id),
            'runbook_name': runbook.name,
            'status': 'simulated',
            'steps_executed': runbook.step_count,
            'estimated_duration': runbook.estimated_total_duration,
            'message': 'Runbook execution simulated successfully'
        }
        
        return Response(execution_result, status=status.HTTP_200_OK)


class StepViewSet(viewsets.ModelViewSet):
    """ViewSet for Step model."""
    
    queryset = Step.objects.all()
    serializer_class = StepSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['runbook', 'action_type', 'is_critical']
    search_fields = ['name', 'description']
    ordering_fields = ['runbook__name', 'order', 'name']
    ordering = ['runbook', 'order']
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a step."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def action_types(self, request):
        """Get available action types."""
        types = [{'value': choice[0], 'label': choice[1]} 
                for choice in Step.ACTION_TYPES]
        return Response(types)


class FlowViewSet(viewsets.ModelViewSet):
    """ViewSet for Flow model."""
    
    queryset = Flow.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'version', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['retrieve']:
            return FlowDetailSerializer
        return FlowSerializer
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a flow."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def components(self, request, pk=None):
        """Get all components in a specific flow."""
        flow = self.get_object()
        flow_components = flow.flow_components.all()
        serializer = FlowComponentSerializer(flow_components, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def connections(self, request, pk=None):
        """Get all connections in a specific flow."""
        flow = self.get_object()
        connections = flow.connections.all()
        serializer = ConnectionSerializer(connections, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def export_yaml(self, request, pk=None):
        """Export flow as YAML."""
        flow = self.get_object()
        serializer = FlowExportSerializer(flow)
        data = serializer.to_representation(flow)
        
        # Return as downloadable file
        response = HttpResponse(
            data['yaml_content'], 
            content_type='application/x-yaml'
        )
        response['Content-Disposition'] = f'attachment; filename="{flow.name}.yaml"'
        return response
    
    @action(detail=True, methods=['post'])
    def analyze_impact(self, request, pk=None):
        """Perform impact analysis for a specific component in the flow."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(id=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Perform impact analysis (simplified implementation)
        affected_components = []
        severity = 'low'
        
        # Find components connected to the affected component
        flow_component = FlowComponent.objects.filter(
            flow=flow, component=component
        ).first()
        
        if flow_component:
            # Find outgoing connections
            outgoing_connections = Connection.objects.filter(
                flow=flow, source_component=flow_component
            )
            
            # Find incoming connections
            incoming_connections = Connection.objects.filter(
                flow=flow, target_component=flow_component
            )
            
            # Collect affected components
            for conn in outgoing_connections:
                affected_components.append(conn.target_component.component)
            
            for conn in incoming_connections:
                affected_components.append(conn.source_component.component)
            
            # Determine severity based on number of affected components
            if len(affected_components) > 5:
                severity = 'critical'
            elif len(affected_components) > 3:
                severity = 'high'
            elif len(affected_components) > 1:
                severity = 'medium'
        
        # Create impact analysis record
        impact_analysis = ImpactAnalysis.objects.create(
            flow=flow,
            affected_component=component,
            severity=severity,
            analysis_results={
                'total_affected_components': len(affected_components),
                'analysis_timestamp': str(timezone.now()),
                'analysis_method': 'connection_based'
            },
            recommendations=f"Review {len(affected_components)} affected components and their dependencies.",
            created_by=request.user
        )
        
        # Add affected components
        impact_analysis.affected_components.set(affected_components)
        
        serializer = ImpactAnalysisSerializer(impact_analysis)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_component(self, request, pk=None):
        """Add a component to a flow."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        position_x = float(request.data.get('position_x', 0))
        position_y = float(request.data.get('position_y', 0))
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(pk=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if component is already in flow
        if FlowComponent.objects.filter(flow=flow, component=component).exists():
            return Response(
                {'error': 'Component already in flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the flow component
        flow_component = FlowComponent.objects.create(
            flow=flow,
            component=component,
            position_x=position_x,
            position_y=position_y,
            created_by=request.user
        )
        
        return Response({
            'id': str(flow_component.id),
            'component_id': str(component.id),
            'component_name': component.name,
            'component_type': component.component_type,
            'position_x': position_x,
            'position_y': position_y,
            'message': 'Component added successfully'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_component(self, request, pk=None):
        """Remove a component from a flow."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            flow_component = FlowComponent.objects.get(
                flow=flow, 
                component_id=component_id
            )
            flow_component.delete()
            
            return Response({
                'message': 'Component removed successfully'
            }, status=status.HTTP_200_OK)
            
        except FlowComponent.DoesNotExist:
            return Response(
                {'error': 'Component not found in flow'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def add_connection(self, request, pk=None):
        """Add a connection between components in a flow."""
        flow = self.get_object()
        source_component_id = request.data.get('source_component_id')
        target_component_id = request.data.get('target_component_id')
        connection_type = request.data.get('connection_type', 'api_call')
        description = request.data.get('description', '')
        
        if not source_component_id or not target_component_id:
            return Response(
                {'error': 'source_component_id and target_component_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if source_component_id == target_component_id:
            return Response(
                {'error': 'Source and target components cannot be the same'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            source_component = Component.objects.get(pk=source_component_id)
            target_component = Component.objects.get(pk=target_component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'One or both components not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the FlowComponent instances for this flow
        try:
            source_flow_component = FlowComponent.objects.get(
                flow=flow, component=source_component
            )
            target_flow_component = FlowComponent.objects.get(
                flow=flow, component=target_component
            )
        except FlowComponent.DoesNotExist:
            return Response(
                {'error': 'Both components must be in the flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if connection already exists
        if Connection.objects.filter(
            flow=flow,
            source_component=source_flow_component,
            target_component=target_flow_component,
            connection_type=connection_type
        ).exists():
            return Response(
                {'error': 'Connection already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the connection
        connection = Connection.objects.create(
            flow=flow,
            source_component=source_flow_component,
            target_component=target_flow_component,
            connection_type=connection_type,
            source=description,  # Use 'source' field instead of 'description'
            created_by=request.user
        )
        
        return Response({
            'id': str(connection.id),
            'source_component_id': str(source_component.id),
            'target_component_id': str(target_component.id),
            'source_component_name': source_component.name,
            'target_component_name': target_component.name,
            'connection_type': connection_type,
            'description': connection.source,  # Return source field as description for frontend
            'message': 'Connection created successfully'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def remove_connection(self, request, pk=None):
        """Remove a connection from a flow."""
        flow = self.get_object()
        connection_id = request.data.get('connection_id')
        
        if not connection_id:
            return Response(
                {'error': 'connection_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            connection = Connection.objects.get(pk=connection_id, flow=flow)
            
            connection.delete()
            return Response({
                'message': 'Connection removed successfully'
            }, status=status.HTTP_200_OK)
        except Connection.DoesNotExist:
            return Response(
                {'error': 'Connection not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def get_flow_components(self, request, pk=None):
        """Get all components in a flow with their connections."""
        flow = self.get_object()
        flow_components = FlowComponent.objects.filter(flow=flow).select_related('component')
        
        components_data = []
        for fc in flow_components:
            # Get connections for this component
            outgoing_connections = Connection.objects.filter(
                flow=flow, source_component=fc
            ).select_related('target_component__component')
            
            incoming_connections = Connection.objects.filter(
                flow=flow, target_component=fc
            ).select_related('source_component__component')
            
            component_data = {
                'id': str(fc.id),
                'component_id': str(fc.component.id),
                'name': fc.component.name,
                'type': fc.component.component_type,
                'business_function': fc.component.business_function,
                'position_x': fc.position_x,
                'position_y': fc.position_y,
                'outgoing_connections': [
                    {
                        'id': str(conn.id),
                        'target_component_id': str(conn.target_component.component.id),
                        'target_component_name': conn.target_component.component.name,
                        'connection_type': conn.connection_type,
                        'description': conn.source  # Use source field as description
                    } for conn in outgoing_connections
                ],
                'incoming_connections': [
                    {
                        'id': str(conn.id),
                        'source_component_id': str(conn.source_component.component.id),
                        'source_component_name': conn.source_component.component.name,
                        'connection_type': conn.connection_type,
                        'description': conn.source  # Use source field as description
                    } for conn in incoming_connections
                ]
            }
            components_data.append(component_data)
        
        return Response({
            'flow_id': str(flow.id),
            'flow_name': flow.name,
            'components': components_data,
            'total_components': len(components_data)
        })
    
    @action(detail=True, methods=['post'])
    def find_downstream_components_by_id(self, request, pk=None):
        """Find all downstream components from a given component."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        max_depth = int(request.data.get('max_depth', 10))
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(pk=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if component is in the flow
        if not FlowComponent.objects.filter(flow=flow, component=component).exists():
            return Response(
                {'error': 'Component not in this flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        downstream_components = self._find_downstream_recursive(component, flow, max_depth)
        
        return Response({
            'source_component': {
                'id': str(component.id),
                'name': component.name,
                'type': component.component_type
            },
            'downstream_components': downstream_components,
            'total_downstream': len(downstream_components)
        })
    
    @action(detail=True, methods=['post'])
    def find_upstream_components_by_id(self, request, pk=None):
        """Find all upstream components from a given component."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        max_depth = int(request.data.get('max_depth', 10))
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(pk=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if component is in the flow
        if not FlowComponent.objects.filter(flow=flow, component=component).exists():
            return Response(
                {'error': 'Component not in this flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        upstream_components = self._find_upstream_recursive(component, flow, max_depth)
        
        return Response({
            'target_component': {
                'id': str(component.id),
                'name': component.name,
                'type': component.component_type
            },
            'upstream_components': upstream_components,
            'total_upstream': len(upstream_components)
        })
    
    @action(detail=True, methods=['post'])
    def perform_impact_analysis(self, request, pk=None):
        """Perform basic impact analysis for a component."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(pk=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if component is in the flow
        if not FlowComponent.objects.filter(flow=flow, component=component).exists():
            return Response(
                {'error': 'Component not in this flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find downstream and upstream components
        downstream = self._find_downstream_recursive(component, flow, 5)
        upstream = self._find_upstream_recursive(component, flow, 5)
        
        # Calculate business impact
        business_impact = self._calculate_business_impact(component, downstream, upstream)
        
        # Determine impact level
        impact_level = self._determine_impact_level(len(downstream), len(upstream), business_impact)
        
        return Response({
            'component': {
                'id': str(component.id),
                'name': component.name,
                'type': component.component_type,
                'business_function': component.business_function
            },
            'impact_analysis': {
                'impact_level': impact_level,
                'business_impact_score': business_impact,
                'downstream_count': len(downstream),
                'upstream_count': len(upstream),
                'total_affected': len(downstream) + len(upstream)
            },
            'downstream_components': downstream,
            'upstream_components': upstream
        })
    
    @action(detail=True, methods=['post'])
    def perform_detailed_impact_analysis(self, request, pk=None):
        """Perform detailed impact analysis with business metrics."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        scenario = request.data.get('scenario', 'failure')  # failure, maintenance, upgrade
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(pk=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if component is in the flow
        if not FlowComponent.objects.filter(flow=flow, component=component).exists():
            return Response(
                {'error': 'Component not in this flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform comprehensive analysis
        downstream = self._find_downstream_recursive(component, flow, 10)
        upstream = self._find_upstream_recursive(component, flow, 10)
        
        # Calculate detailed metrics
        business_impact = self._calculate_business_impact(component, downstream, upstream)
        impact_level = self._determine_impact_level(len(downstream), len(upstream), business_impact)
        
        # Analyze by component types
        affected_by_type = self._analyze_components_by_type(downstream + upstream)
        
        # Calculate estimated downtime and recovery
        estimated_metrics = self._calculate_estimated_metrics(component, downstream, scenario)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(component, downstream, upstream, scenario)
        
        return Response({
            'component': {
                'id': str(component.id),
                'name': component.name,
                'type': component.component_type,
                'business_function': component.business_function
            },
            'scenario': scenario,
            'impact_analysis': {
                'impact_level': impact_level,
                'business_impact_score': business_impact,
                'downstream_count': len(downstream),
                'upstream_count': len(upstream),
                'total_affected': len(downstream) + len(upstream),
                'affected_by_type': affected_by_type,
                'estimated_metrics': estimated_metrics
            },
            'downstream_components': downstream,
            'upstream_components': upstream,
            'recommendations': recommendations,
            'analysis_timestamp': timezone.now().isoformat()
        })
    
    def _find_downstream_recursive(self, component, flow, max_depth, visited=None, current_depth=0):
        """Recursively find all downstream components."""
        if visited is None:
            visited = set()
        
        if current_depth >= max_depth or component.id in visited:
            return []
        
        visited.add(component.id)
        downstream = []
        
        # Find direct downstream connections
        connections = Connection.objects.filter(
            source_component__component=component
        ).select_related('target_component__component')
        
        for conn in connections:
            target = conn.target_component.component
            
            # Check if target is in the same flow
            if FlowComponent.objects.filter(flow=flow, component=target).exists():
                if target.id not in visited:
                    component_data = {
                        'id': str(target.id),
                        'name': target.name,
                        'type': target.component_type,
                        'business_function': target.business_function,
                        'connection_type': conn.connection_type,
                        'depth': current_depth + 1
                    }
                    downstream.append(component_data)
                    
                    # Recursively find downstream of this component
                    nested_downstream = self._find_downstream_recursive(
                        target, flow, max_depth, visited, current_depth + 1
                    )
                    downstream.extend(nested_downstream)
        
        return downstream
    
    def _find_upstream_recursive(self, component, flow, max_depth, visited=None, current_depth=0):
        """Recursively find all upstream components."""
        if visited is None:
            visited = set()
        
        if current_depth >= max_depth or component.id in visited:
            return []
        
        visited.add(component.id)
        upstream = []
        
        # Find direct upstream connections
        connections = Connection.objects.filter(
            target_component__component=component
        ).select_related('source_component__component')
        
        for conn in connections:
            source = conn.source_component.component
            
            # Check if source is in the same flow
            if FlowComponent.objects.filter(flow=flow, component=source).exists():
                if source.id not in visited:
                    component_data = {
                        'id': str(source.id),
                        'name': source.name,
                        'type': source.component_type,
                        'business_function': source.business_function,
                        'connection_type': conn.connection_type,
                        'depth': current_depth + 1
                    }
                    upstream.append(component_data)
                    
                    # Recursively find upstream of this component
                    nested_upstream = self._find_upstream_recursive(
                        source, flow, max_depth, visited, current_depth + 1
                    )
                    upstream.extend(nested_upstream)
        
        return upstream
    
    def _calculate_business_impact(self, component, downstream, upstream):
        """Calculate business impact score based on component and affected components."""
        base_score = 0
        
        # Base score based on component type
        type_scores = {
            'database': 8,
            'service': 6,
            'api': 5,
            'frontend': 4,
            'middleware': 3,
            'external_service': 7
        }
        base_score = type_scores.get(component.component_type, 3)
        
        # Add points for affected components
        downstream_impact = len(downstream) * 2
        upstream_impact = len(upstream) * 1.5
        
        # Bonus for critical component types in affected components
        critical_affected = sum(1 for comp in downstream + upstream 
                              if comp.get('type') in ['database', 'external_service'])
        
        total_score = base_score + downstream_impact + upstream_impact + (critical_affected * 2)
        
        # Normalize to 0-100 scale
        return min(100, max(0, int(total_score)))
    
    def _determine_impact_level(self, downstream_count, upstream_count, business_impact):
        """Determine impact level based on affected components and business impact."""
        total_affected = downstream_count + upstream_count
        
        if business_impact >= 80 or total_affected >= 10:
            return 'critical'
        elif business_impact >= 60 or total_affected >= 6:
            return 'high'
        elif business_impact >= 40 or total_affected >= 3:
            return 'medium'
        elif business_impact >= 20 or total_affected >= 1:
            return 'low'
        else:
            return 'minimal'
    
    def _analyze_components_by_type(self, components):
        """Analyze affected components by type."""
        type_counts = {}
        for comp in components:
            comp_type = comp.get('type', 'unknown')
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        return type_counts
    
    def _calculate_estimated_metrics(self, component, downstream, scenario):
        """Calculate estimated downtime and recovery metrics."""
        base_downtime = {
            'failure': 120,  # minutes
            'maintenance': 60,
            'upgrade': 30
        }
        
        downtime = base_downtime.get(scenario, 60)
        
        # Increase downtime based on affected components
        downtime += len(downstream) * 15
        
        # Increase for critical component types
        if component.component_type in ['database', 'external_service']:
            downtime *= 1.5
        
        recovery_time = downtime * 0.3  # Recovery typically 30% of downtime
        
        return {
            'estimated_downtime_minutes': int(downtime),
            'estimated_recovery_minutes': int(recovery_time),
            'total_impact_minutes': int(downtime + recovery_time)
        }
    
    def _generate_recommendations(self, component, downstream, upstream, scenario):
        """Generate recommendations based on impact analysis."""
        recommendations = []
        
        # General recommendations
        if len(downstream) > 5:
            recommendations.append({
                'priority': 'high',
                'category': 'architecture',
                'recommendation': 'Consider implementing circuit breakers to isolate failures'
            })
        
        if component.component_type == 'database':
            recommendations.append({
                'priority': 'critical',
                'category': 'backup',
                'recommendation': 'Ensure database backups are current and test recovery procedures'
            })
        
        if len(upstream) > 3:
            recommendations.append({
                'priority': 'medium',
                'category': 'monitoring',
                'recommendation': 'Implement comprehensive monitoring for upstream dependencies'
            })
        
        # Scenario-specific recommendations
        if scenario == 'failure':
            recommendations.append({
                'priority': 'high',
                'category': 'incident_response',
                'recommendation': 'Activate incident response team and notify stakeholders'
            })
        elif scenario == 'maintenance':
            recommendations.append({
                'priority': 'medium',
                'category': 'planning',
                'recommendation': 'Schedule maintenance during low-traffic periods'
            })
        elif scenario == 'upgrade':
            recommendations.append({
                'priority': 'medium',
                'category': 'testing',
                'recommendation': 'Perform thorough testing in staging environment first'
            })
        
        return recommendations


class FlowComponentViewSet(viewsets.ModelViewSet):
    """ViewSet for FlowComponent model."""
    
    queryset = FlowComponent.objects.all()
    serializer_class = FlowComponentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['flow', 'component']
    ordering = ['flow__name', 'component__name']
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a flow component."""
        serializer.save(created_by=self.request.user)


class ConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for Connection model."""
    
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['flow', 'connection_type']
    ordering = ['flow__name', 'source_component__component__name']
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a connection."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available connection types."""
        types = [{'value': choice[0], 'label': choice[1]} 
                for choice in Connection.CONNECTION_TYPES]
        return Response(types)


class ImpactAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet for ImpactAnalysis model with impact analysis functionality."""
    
    queryset = ImpactAnalysis.objects.all()
    serializer_class = ImpactAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['flow', 'affected_component', 'severity']
    search_fields = ['recommendations']
    ordering_fields = ['severity', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set the created_by field when creating an impact analysis."""
        serializer.save(created_by=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create impact analysis with automatic analysis execution."""
        data = request.data.copy()
        
        # Extract analysis parameters
        flow_id = data.get('flow')  # Changed from 'flow_id' to 'flow'
        component_id = data.get('affected_component')  # Changed from 'component_id' to 'affected_component'
        analysis_type = data.get('analysis_type', 'downstream')
        severity = data.get('severity', 'medium')
        max_depth = data.get('max_depth', '2')
        include_inactive = data.get('include_inactive', False)
        description = data.get('description', '')
        
        if not flow_id or not component_id:
            return Response(
                {'error': 'flow and affected_component are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get flow and component
            flow = Flow.objects.get(pk=flow_id)
            component = Component.objects.get(pk=component_id)
            
            # Perform impact analysis
            analysis_results = self._perform_impact_analysis(
                flow, component, analysis_type, max_depth, include_inactive
            )
            
            # Create ImpactAnalysis record
            impact_analysis = ImpactAnalysis.objects.create(
                flow=flow,
                affected_component=component,
                severity=severity,
                analysis_results=analysis_results,
                recommendations=self._generate_recommendations(analysis_results),
                created_by=request.user
            )
            
            # Add affected components to the many-to-many field
            affected_component_ids = [comp['id'] for comp in analysis_results.get('affected_components', [])]
            if affected_component_ids:
                affected_components = Component.objects.filter(id__in=affected_component_ids)
                impact_analysis.affected_components.set(affected_components)
            
            # Serialize and return the result
            serializer = self.get_serializer(impact_analysis)
            result_data = serializer.data
            
            # Add analysis-specific data for frontend
            result_data.update({
                'analysis_type': analysis_type,
                'max_depth': max_depth,
                'component_id': component_id,
                'affected_components': analysis_results.get('affected_components', []),
                'severity_distribution': analysis_results.get('severity_distribution', {}),
                'impact_paths': analysis_results.get('impact_paths', []),
                'total_affected': len(analysis_results.get('affected_components', []))
            })
            
            return Response(result_data, status=status.HTTP_201_CREATED)
            
        except Flow.DoesNotExist:
            return Response(
                {'error': 'Flow not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Analysis failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _perform_impact_analysis(self, flow, target_component, analysis_type, max_depth, include_inactive):
        """Perform the actual impact analysis."""
        
        # Get all flow components and connections
        flow_components = flow.flow_components.select_related('component').all()
        connections = flow.connections.select_related(
            'source_component__component', 'target_component__component'
        ).all()
        
        # Build component graph
        component_graph = self._build_component_graph(flow_components, connections)
        
        # Find target flow component
        target_flow_component = None
        for fc in flow_components:
            if fc.component.id == target_component.id:
                target_flow_component = fc
                break
        
        if not target_flow_component:
            return {
                'affected_components': [],
                'severity_distribution': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
                'impact_paths': [],
                'analysis_summary': 'Target component not found in flow'
            }
        
        # Perform analysis based on type
        if analysis_type == 'downstream':
            affected_components = self._analyze_downstream_impact(
                target_flow_component, component_graph, max_depth, include_inactive
            )
        elif analysis_type == 'upstream':
            affected_components = self._analyze_upstream_impact(
                target_flow_component, component_graph, max_depth, include_inactive
            )
        else:  # bidirectional
            downstream = self._analyze_downstream_impact(
                target_flow_component, component_graph, max_depth, include_inactive
            )
            upstream = self._analyze_upstream_impact(
                target_flow_component, component_graph, max_depth, include_inactive
            )
            # Merge and deduplicate
            affected_components = self._merge_impact_results(downstream, upstream)
        
        # Calculate severity distribution
        severity_distribution = self._calculate_severity_distribution(affected_components)
        
        # Generate impact paths
        impact_paths = self._generate_impact_paths(
            target_flow_component, affected_components, component_graph
        )
        
        return {
            'affected_components': affected_components,
            'severity_distribution': severity_distribution,
            'impact_paths': impact_paths,
            'analysis_summary': f'Found {len(affected_components)} affected components',
            'target_component': {
                'id': str(target_component.id),
                'name': target_component.name,
                'type': target_component.component_type
            }
        }
    
    def _build_component_graph(self, flow_components, connections):
        """Build a graph representation of component relationships."""
        graph = {
            'nodes': {},
            'edges': {'downstream': {}, 'upstream': {}}
        }
        
        # Add nodes
        for fc in flow_components:
            graph['nodes'][str(fc.id)] = {
                'flow_component_id': str(fc.id),
                'component_id': str(fc.component.id),
                'name': fc.component.name,
                'type': fc.component.component_type,
                'business_function': fc.component.business_function,
                'is_active': fc.component.is_active,
                'position': {'x': fc.position_x, 'y': fc.position_y}
            }
            graph['edges']['downstream'][str(fc.id)] = []
            graph['edges']['upstream'][str(fc.id)] = []
        
        # Add edges
        for conn in connections:
            source_id = str(conn.source_component.id)
            target_id = str(conn.target_component.id)
            
            if source_id in graph['edges']['downstream']:
                graph['edges']['downstream'][source_id].append({
                    'target': target_id,
                    'connection_type': conn.connection_type,
                    'connection_id': str(conn.id)
                })
            
            if target_id in graph['edges']['upstream']:
                graph['edges']['upstream'][target_id].append({
                    'source': source_id,
                    'connection_type': conn.connection_type,
                    'connection_id': str(conn.id)
                })
        
        return graph
    
    def _analyze_downstream_impact(self, target_component, graph, max_depth, include_inactive):
        """Analyze downstream impact with enhanced transitive dependency tracking."""
        affected = []
        visited = set()
        impact_chains = []
        
        def traverse_downstream(component_id, depth, path, impact_chain):
            if depth > int(max_depth) and max_depth != 'unlimited':
                return
            
            if component_id in visited:
                return
            
            visited.add(component_id)
            
            # Get downstream connections
            for edge in graph['edges']['downstream'].get(component_id, []):
                target_id = edge['target']
                target_node = graph['nodes'].get(target_id)
                
                if not target_node:
                    continue
                
                # Skip inactive components if not included
                if not include_inactive and not target_node['is_active']:
                    continue
                
                # Determine impact type (direct vs indirect)
                impact_type = 'direct' if depth == 0 else 'indirect'
                
                # Calculate impact severity with transitive consideration
                severity = self._calculate_transitive_impact_severity(
                    edge['connection_type'], depth, target_node['type'], impact_type
                )
                
                # Create impact chain entry
                chain_entry = {
                    'from': graph['nodes'][component_id]['name'],
                    'to': target_node['name'],
                    'connection_type': edge['connection_type'],
                    'depth': depth + 1
                }
                
                affected_component = {
                    'id': target_node['component_id'],
                    'name': target_node['name'],
                    'type': target_node['type'],
                    'business_function': target_node['business_function'],
                    'severity': severity,
                    'depth': depth + 1,
                    'impact_type': impact_type,
                    'path': path + [target_node['name']],
                    'connection_type': edge['connection_type'],
                    'impact_chain': impact_chain + [chain_entry],
                    'transitive_reason': self._get_transitive_reason(path, target_node['name'], impact_type)
                }
                
                affected.append(affected_component)
                impact_chains.append(impact_chain + [chain_entry])
                
                # Continue traversing for transitive impacts
                traverse_downstream(
                    target_id, 
                    depth + 1, 
                    path + [target_node['name']], 
                    impact_chain + [chain_entry]
                )
        
        # Start traversal from target component
        traverse_downstream(
            str(target_component.id), 
            0, 
            [target_component.component.name], 
            []
        )
        
        return affected
    
    def _analyze_upstream_impact(self, target_component, graph, max_depth, include_inactive):
        """Analyze upstream impact with enhanced transitive dependency tracking."""
        affected = []
        visited = set()
        impact_chains = []
        
        def traverse_upstream(component_id, depth, path, impact_chain):
            if depth > int(max_depth) and max_depth != 'unlimited':
                return
            
            if component_id in visited:
                return
            
            visited.add(component_id)
            
            # Get upstream connections
            for edge in graph['edges']['upstream'].get(component_id, []):
                source_id = edge['source']
                source_node = graph['nodes'].get(source_id)
                
                if not source_node:
                    continue
                
                # Skip inactive components if not included
                if not include_inactive and not source_node['is_active']:
                    continue
                
                # Determine impact type (direct vs indirect)
                impact_type = 'direct' if depth == 0 else 'indirect'
                
                # Calculate impact severity with transitive consideration
                severity = self._calculate_transitive_impact_severity(
                    edge['connection_type'], depth, source_node['type'], impact_type
                )
                
                # Create impact chain entry
                chain_entry = {
                    'from': source_node['name'],
                    'to': graph['nodes'][component_id]['name'],
                    'connection_type': edge['connection_type'],
                    'depth': depth + 1
                }
                
                affected_component = {
                    'id': source_node['component_id'],
                    'name': source_node['name'],
                    'type': source_node['type'],
                    'business_function': source_node['business_function'],
                    'severity': severity,
                    'depth': depth + 1,
                    'impact_type': impact_type,
                    'path': path + [source_node['name']],
                    'connection_type': edge['connection_type'],
                    'impact_chain': impact_chain + [chain_entry],
                    'transitive_reason': self._get_transitive_reason(path, source_node['name'], impact_type)
                }
                
                affected.append(affected_component)
                impact_chains.append(impact_chain + [chain_entry])
                
                # Continue traversing for transitive impacts
                traverse_upstream(
                    source_id, 
                    depth + 1, 
                    path + [source_node['name']], 
                    impact_chain + [chain_entry]
                )
        
        # Start traversal from target component
        traverse_upstream(
            str(target_component.id), 
            0, 
            [target_component.component.name], 
            []
        )
        
        return affected
    
    def _calculate_transitive_impact_severity(self, connection_type, depth, component_type, impact_type):
        """Calculate impact severity with enhanced transitive dependency consideration."""
        
        # Base severity based on connection type
        connection_severity = {
            'api_call': 'high',
            'data_flow': 'medium',
            'message_queue': 'medium',
            'database_connection': 'high',
            'event_trigger': 'medium',
            'dependency': 'critical'
        }.get(connection_type, 'medium')
        
        # Adjust based on component type
        component_multiplier = {
            'database': 1.3,
            'api': 1.1,
            'service': 1.0,
            'frontend': 0.8,
            'middleware': 1.0,
            'external_service': 1.4
        }.get(component_type, 1.0)
        
        # Enhanced depth consideration for transitive impacts
        if impact_type == 'direct':
            depth_multiplier = 1.0  # Full impact for direct connections
        else:
            # Indirect impacts have reduced but still significant severity
            depth_multiplier = max(0.4, 0.8 - (depth * 0.15))
        
        # Calculate final severity score
        severity_scores = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        base_score = severity_scores[connection_severity]
        final_score = base_score * component_multiplier * depth_multiplier
        
        # Map back to severity levels with transitive consideration
        if impact_type == 'direct':
            if final_score >= 3.5:
                return 'critical'
            elif final_score >= 2.5:
                return 'high'
            elif final_score >= 1.5:
                return 'medium'
            else:
                return 'low'
        else:  # indirect
            # Indirect impacts are generally one level lower but still important
            if final_score >= 3.8:
                return 'high'  # Very critical indirect impacts
            elif final_score >= 2.8:
                return 'medium'
            elif final_score >= 1.8:
                return 'low'
            else:
                return 'low'
    
    def _get_transitive_reason(self, path, component_name, impact_type):
        """Generate human-readable explanation for transitive impact."""
        if impact_type == 'direct':
            return f"Directly connected to the target component"
        else:
            if len(path) > 2:
                intermediate_components = ' → '.join(path[1:-1])
                return f"Indirectly impacted through: {intermediate_components}"
            else:
                return f"Indirectly impacted through transitive dependency"
    
    def _calculate_impact_severity(self, connection_type, depth, component_type):
        """Calculate impact severity based on connection type, depth, and component type."""
        
        # Base severity based on connection type
        connection_severity = {
            'api_call': 'high',
            'data_flow': 'medium',
            'message_queue': 'medium',
            'database_connection': 'high',
            'event_trigger': 'medium',
            'dependency': 'critical'
        }.get(connection_type, 'medium')
        
        # Adjust based on component type
        component_multiplier = {
            'database': 1.2,
            'api': 1.1,
            'service': 1.0,
            'frontend': 0.8,
            'middleware': 1.0,
            'external_service': 1.3
        }.get(component_type, 1.0)
        
        # Adjust based on depth (closer = higher impact)
        depth_multiplier = max(0.5, 1.0 - (depth * 0.2))
        
        # Calculate final severity score
        severity_scores = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        base_score = severity_scores[connection_severity]
        final_score = base_score * component_multiplier * depth_multiplier
        
        # Map back to severity levels
        if final_score >= 3.5:
            return 'critical'
        elif final_score >= 2.5:
            return 'high'
        elif final_score >= 1.5:
            return 'medium'
        else:
            return 'low'
    
    def _merge_impact_results(self, downstream, upstream):
        """Merge downstream and upstream impact results, removing duplicates."""
        merged = {}
        
        # Add downstream impacts
        for comp in downstream:
            comp_id = comp['id']
            merged[comp_id] = comp.copy()
            merged[comp_id]['impact_direction'] = 'downstream'
        
        # Add upstream impacts, merging if already exists
        for comp in upstream:
            comp_id = comp['id']
            if comp_id in merged:
                # Component affected in both directions - increase severity
                existing_severity = merged[comp_id]['severity']
                new_severity = comp['severity']
                
                # Take the higher severity
                severity_order = ['low', 'medium', 'high', 'critical']
                if severity_order.index(new_severity) > severity_order.index(existing_severity):
                    merged[comp_id]['severity'] = new_severity
                
                merged[comp_id]['impact_direction'] = 'bidirectional'
            else:
                comp_copy = comp.copy()
                comp_copy['impact_direction'] = 'upstream'
                merged[comp_id] = comp_copy
        
        return list(merged.values())
    
    def _calculate_severity_distribution(self, affected_components):
        """Calculate the distribution of severity levels with direct/indirect breakdown."""
        distribution = {
            'total': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
            'direct': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
            'indirect': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        }
        
        for comp in affected_components:
            severity = comp.get('severity', 'medium')
            impact_type = comp.get('impact_type', 'direct')
            
            if severity in distribution['total']:
                distribution['total'][severity] += 1
                distribution[impact_type][severity] += 1
        
        # Add summary statistics
        distribution['summary'] = {
            'total_affected': len(affected_components),
            'direct_affected': len([c for c in affected_components if c.get('impact_type') == 'direct']),
            'indirect_affected': len([c for c in affected_components if c.get('impact_type') == 'indirect']),
            'max_depth': max([c.get('depth', 1) for c in affected_components], default=1)
        }
        
        return distribution
    
    def _generate_impact_paths(self, target_component, affected_components, graph):
        """Generate impact paths showing how components are connected."""
        paths = []
        
        for comp in affected_components:
            # Simple path generation - could be enhanced with actual path finding
            path = {
                'from': target_component.component.name,
                'to': comp['name'],
                'connection_type': comp.get('connection_type', 'unknown'),
                'severity': comp['severity'],
                'depth': comp.get('depth', 1)
            }
            paths.append(path)
        
        return paths
    
    def _generate_recommendations(self, analysis_results):
        """Generate recommendations based on analysis results."""
        affected_count = len(analysis_results.get('affected_components', []))
        severity_dist = analysis_results.get('severity_distribution', {})
        
        recommendations = []
        
        if affected_count == 0:
            recommendations.append("No components will be affected by changes to this component.")
        else:
            recommendations.append(f"Changes to this component will affect {affected_count} other components.")
            
            if severity_dist.get('critical', 0) > 0:
                recommendations.append(f"⚠️ {severity_dist['critical']} components have CRITICAL impact - require immediate attention.")
            
            if severity_dist.get('high', 0) > 0:
                recommendations.append(f"🔶 {severity_dist['high']} components have HIGH impact - plan carefully.")
            
            if affected_count > 5:
                recommendations.append("Consider implementing changes in phases to minimize risk.")
            
            recommendations.append("Review all affected components before implementing changes.")
            recommendations.append("Ensure proper testing and rollback procedures are in place.")
        
        return "\n".join(recommendations)


class YAMLImportView(APIView):
    """View for importing flows from YAML."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Import flow from YAML content."""
        serializer = YAMLFlowSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    flow = serializer.save()
                    flow.created_by = request.user
                    flow.save()
                    
                    response_serializer = FlowDetailSerializer(flow)
                    return Response(
                        response_serializer.data, 
                        status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                return Response(
                    {'error': f'Failed to import flow: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JSONImportView(APIView):
    """View for importing flows from JSON."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Import flow from JSON content."""
        serializer = JSONFlowSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    result = serializer.save()
                    flow = result['flow']
                    flow.created_by = request.user
                    flow.save()
                    
                    response_data = {
                        'flow': FlowDetailSerializer(flow).data,
                        'components_created': result['components_created'],
                        'connections_created': result['connections_created'],
                        'message': result['message']
                    }
                    
                    return Response(
                        response_data, 
                        status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                return Response(
                    {'error': f'Failed to import flow: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JSONValidateView(APIView):
    """View for validating JSON content without importing."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Validate JSON content structure."""
        json_content = request.data.get('json_content', '')
        
        if not json_content:
            return Response(
                {'error': 'json_content is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = JSONFlowSerializer(data={'json_content': json_content})
        
        if serializer.is_valid():
            try:
                data = json.loads(json_content)
                
                # Provide validation summary
                validation_result = {
                    'valid': True,
                    'system_name': data.get('system_name', 'Unknown'),
                    'system_purpose': data.get('system_purpose', 'Not specified'),
                    'component_count': len(data.get('components', [])),
                    'total_flows': sum(len(comp.get('flows', [])) for comp in data.get('components', [])),
                    'message': 'JSON content is valid and ready for import'
                }
                
                return Response(validation_result, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response(
                    {'valid': False, 'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'valid': False, 'errors': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class YAMLValidateView(APIView):
    """View for validating YAML content without importing."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Validate YAML content structure."""
        yaml_content = request.data.get('yaml_content', '')
        
        if not yaml_content:
            return Response(
                {'error': 'yaml_content is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = YAMLFlowSerializer(data={'yaml_content': yaml_content})
        
        if serializer.is_valid():
            try:
                data = yaml.safe_load(yaml_content)
                
                # Provide validation summary
                validation_result = {
                    'valid': True,
                    'flow_name': data.get('flow', {}).get('name', 'Unknown'),
                    'component_count': len(data.get('components', [])),
                    'connection_count': len(data.get('connections', [])),
                    'message': 'YAML content is valid and ready for import'
                }
                
                return Response(validation_result, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response(
                    {'valid': False, 'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'valid': False, 'errors': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class SystemStatsView(APIView):
    """View for getting system statistics."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get system statistics."""
        stats = {
            'components': {
                'total': Component.objects.count(),
                'active': Component.objects.filter(is_active=True).count(),
                'by_type': {}
            },
            'runbooks': {
                'total': Runbook.objects.count(),
                'active': Runbook.objects.filter(is_active=True).count(),
            },
            'steps': {
                'total': Step.objects.count(),
                'critical': Step.objects.filter(is_critical=True).count(),
            },
            'flows': {
                'total': Flow.objects.count(),
                'active': Flow.objects.filter(is_active=True).count(),
            },
            'connections': {
                'total': Connection.objects.count(),
                'by_type': {}
            },
            'impact_analyses': {
                'total': ImpactAnalysis.objects.count(),
                'by_severity': {}
            }
        }
        
        # Component types breakdown
        for choice in Component.COMPONENT_TYPES:
            count = Component.objects.filter(component_type=choice[0]).count()
            stats['components']['by_type'][choice[0]] = {
                'label': choice[1],
                'count': count
            }
        
        # Connection types breakdown
        for choice in Connection.CONNECTION_TYPES:
            count = Connection.objects.filter(connection_type=choice[0]).count()
            stats['connections']['by_type'][choice[0]] = {
                'label': choice[1],
                'count': count
            }
        
        # Impact analysis severity breakdown
        for choice in ImpactAnalysis.SEVERITY_LEVELS:
            count = ImpactAnalysis.objects.filter(severity=choice[0]).count()
            stats['impact_analyses']['by_severity'][choice[0]] = {
                'label': choice[1],
                'count': count
            }
        
        return Response(stats, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'])
    def add_component(self, request, pk=None):
        """Add a component to a flow."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        position_x = float(request.data.get('position_x', 0))
        position_y = float(request.data.get('position_y', 0))
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            component = Component.objects.get(pk=component_id)
        except Component.DoesNotExist:
            return Response(
                {'error': 'Component not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if component is already in flow
        if FlowComponent.objects.filter(flow=flow, component=component).exists():
            return Response(
                {'error': 'Component already in flow'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the flow component
        flow_component = FlowComponent.objects.create(
            flow=flow,
            component=component,
            position_x=position_x,
            position_y=position_y,
            created_by=request.user
        )
        
        return Response({
            'id': str(flow_component.id),
            'component_id': str(component.id),
            'component_name': component.name,
            'component_type': component.component_type,
            'position_x': position_x,
            'position_y': position_y,
            'message': 'Component added successfully'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_component(self, request, pk=None):
        """Remove a component from a flow."""
        flow = self.get_object()
        component_id = request.data.get('component_id')
        
        if not component_id:
            return Response(
                {'error': 'component_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            flow_component = FlowComponent.objects.get(
                flow=flow, 
                component_id=component_id
            )
            flow_component.delete()
            
            return Response({
                'message': 'Component removed successfully'
            }, status=status.HTTP_200_OK)
            
        except FlowComponent.DoesNotExist:
            return Response(
                {'error': 'Component not found in flow'}, 
                status=status.HTTP_404_NOT_FOUND
            )