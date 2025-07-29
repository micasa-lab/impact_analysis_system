"""
Core models for the Impact Analysis System.

This module contains the main data models for components, runbooks, flows,
and their relationships.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class BaseModel(models.Model):
    """Base model with common fields for all models."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='%(class)s_created'
    )
    
    class Meta:
        abstract = True


class Component(BaseModel):
    """
    Represents an application component with business functions.
    
    Components are the building blocks of application flows and can have
    associated runbooks for operational procedures.
    """
    
    COMPONENT_TYPES = [
        ('service', 'Service'),
        ('database', 'Database'),
        ('api', 'API'),
        ('frontend', 'Frontend'),
        ('middleware', 'Middleware'),
        ('external_service', 'External Service'),
    ]
    
    name = models.CharField(max_length=255, help_text="Component name")
    description = models.TextField(blank=True, help_text="Component description")
    business_function = models.TextField(help_text="Business function description")
    component_type = models.CharField(
        max_length=50, 
        choices=COMPONENT_TYPES,
        help_text="Type of component"
    )
    owned_by = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Team or organization that owns this component"
    )
    kpis = models.JSONField(
        default=list,
        blank=True,
        help_text="Key Performance Indicators for this component"
    )
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Additional metadata as JSON"
    )
    is_active = models.BooleanField(default=True, help_text="Whether component is active")
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['component_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.component_type})"
    
    @property
    def runbook_count(self):
        """Return the number of runbooks associated with this component."""
        return self.runbooks.count()


class Runbook(BaseModel):
    """
    Contains step-by-step procedures for components.
    
    Runbooks define operational procedures that can be executed on components
    for maintenance, troubleshooting, or other operational tasks.
    """
    
    component = models.ForeignKey(
        Component, 
        on_delete=models.CASCADE, 
        related_name='runbooks',
        help_text="Associated component"
    )
    name = models.CharField(max_length=255, help_text="Runbook name")
    description = models.TextField(blank=True, help_text="Runbook description")
    version = models.CharField(
        max_length=50, 
        default='1.0.0',
        help_text="Runbook version"
    )
    is_active = models.BooleanField(default=True, help_text="Whether runbook is active")
    
    class Meta:
        ordering = ['component__name', 'name']
        unique_together = ['component', 'name', 'version']
        indexes = [
            models.Index(fields=['component', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.component.name} - {self.name} (v{self.version})"
    
    @property
    def step_count(self):
        """Return the number of steps in this runbook."""
        return self.steps.count()
    
    @property
    def estimated_total_duration(self):
        """Return the total estimated duration of all steps in minutes."""
        return self.steps.aggregate(
            total=models.Sum('estimated_duration')
        )['total'] or 0


class Step(BaseModel):
    """
    Individual steps within runbooks.
    
    Steps define specific actions that can be performed as part of a runbook
    procedure, with parameters and estimated duration.
    """
    
    ACTION_TYPES = [
        ('shell_command', 'Shell Command'),
        ('api_call', 'API Call'),
        ('database_query', 'Database Query'),
        ('file_operation', 'File Operation'),
        ('notification', 'Notification'),
        ('manual_step', 'Manual Step'),
    ]
    
    runbook = models.ForeignKey(
        Runbook, 
        on_delete=models.CASCADE, 
        related_name='steps',
        help_text="Associated runbook"
    )
    name = models.CharField(max_length=255, help_text="Step name")
    description = models.TextField(help_text="Step description")
    action_type = models.CharField(
        max_length=50, 
        choices=ACTION_TYPES,
        help_text="Type of action"
    )
    parameters = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Action parameters as JSON"
    )
    order = models.PositiveIntegerField(
        help_text="Step order within the runbook"
    )
    estimated_duration = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        help_text="Estimated duration in minutes"
    )
    is_critical = models.BooleanField(
        default=False,
        help_text="Whether this step is critical for the procedure"
    )
    
    class Meta:
        ordering = ['runbook', 'order']
        unique_together = ['runbook', 'order']
        indexes = [
            models.Index(fields=['runbook', 'order']),
            models.Index(fields=['action_type']),
        ]
    
    def __str__(self):
        return f"{self.runbook.name} - Step {self.order}: {self.name}"


class Flow(BaseModel):
    """
    Defines application flows connecting multiple components.
    
    Flows represent the overall application architecture and component
    relationships, and can be imported/exported as YAML files.
    """
    
    name = models.CharField(max_length=255, help_text="Flow name")
    description = models.TextField(blank=True, help_text="Flow description")
    system_name = models.CharField(
        max_length=255, 
        blank=True,
        help_text="System name for this flow"
    )
    system_purpose = models.TextField(
        blank=True,
        help_text="Purpose and objective of the system"
    )
    version = models.CharField(
        max_length=50, 
        default='1.0.0',
        help_text="Flow version"
    )
    yaml_content = models.TextField(
        blank=True,
        help_text="YAML representation of the flow"
    )
    is_active = models.BooleanField(default=True, help_text="Whether flow is active")
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'version']
        indexes = [
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    @property
    def component_count(self):
        """Return the number of components in this flow."""
        return self.flow_components.count()
    
    @property
    def connection_count(self):
        """Return the number of connections in this flow."""
        return self.connections.count()


class FlowComponent(BaseModel):
    """
    Represents a component within a specific flow with positioning and configuration.
    
    This model links components to flows and stores flow-specific information
    like position and configuration.
    """
    
    flow = models.ForeignKey(
        Flow, 
        on_delete=models.CASCADE, 
        related_name='flow_components',
        help_text="Associated flow"
    )
    component = models.ForeignKey(
        Component, 
        on_delete=models.CASCADE, 
        related_name='flow_instances',
        help_text="Associated component"
    )
    position_x = models.FloatField(
        default=0.0,
        help_text="X position in the flow diagram"
    )
    position_y = models.FloatField(
        default=0.0,
        help_text="Y position in the flow diagram"
    )
    configuration = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Flow-specific configuration as JSON"
    )
    
    class Meta:
        unique_together = ['flow', 'component']
        indexes = [
            models.Index(fields=['flow']),
            models.Index(fields=['component']),
        ]
    
    def __str__(self):
        return f"{self.flow.name} - {self.component.name}"


class Connection(BaseModel):
    """
    Represents connections between components in a flow.
    
    Connections define the relationships and data flow between components
    within an application flow.
    """
    
    CONNECTION_TYPES = [
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
        ('database', 'Database'),
        ('message_queue', 'Message Queue'),
        ('file_system', 'File System'),
        ('api', 'API'),
        ('internal', 'Internal'),
        ('external_user_triggered', 'External User Triggered'),
    ]
    
    FLOW_TYPES = [
        ('internal', 'Internal'),
        ('external_user_triggered', 'External User Triggered'),
        ('external_system_triggered', 'External System Triggered'),
    ]
    
    flow = models.ForeignKey(
        Flow, 
        on_delete=models.CASCADE, 
        related_name='connections',
        help_text="Associated flow"
    )
    source_component = models.ForeignKey(
        FlowComponent, 
        on_delete=models.CASCADE, 
        related_name='outgoing_connections',
        help_text="Source component"
    )
    target_component = models.ForeignKey(
        FlowComponent, 
        on_delete=models.CASCADE, 
        related_name='incoming_connections',
        help_text="Target component"
    )
    connection_type = models.CharField(
        max_length=50, 
        choices=CONNECTION_TYPES,
        help_text="Type of connection"
    )
    flow_type = models.CharField(
        max_length=50,
        choices=FLOW_TYPES,
        default='internal',
        help_text="Type of flow (internal, external_user_triggered, etc.)"
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        help_text="Source description for the flow"
    )
    target = models.CharField(
        max_length=255,
        blank=True,
        help_text="Target description for the flow"
    )
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Connection metadata as JSON"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['flow']),
            models.Index(fields=['connection_type']),
        ]
    
    def __str__(self):
        return f"{self.source_component.component.name} -> {self.target_component.component.name} ({self.connection_type})"


class ImpactAnalysis(BaseModel):
    """
    Stores impact analysis results for components and flows.
    
    This model tracks the potential impact when components are affected
    and provides analysis results for decision making.
    """
    print("In ImpactANalaysis CORE")
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    flow = models.ForeignKey(
        Flow, 
        on_delete=models.CASCADE, 
        related_name='impact_analyses',
        help_text="Associated flow"
    )
    affected_component = models.ForeignKey(
        Component, 
        on_delete=models.CASCADE, 
        related_name='impact_analyses',
        help_text="Component being analyzed"
    )
    severity = models.CharField(
        max_length=20, 
        choices=SEVERITY_LEVELS,
        help_text="Impact severity level"
    )
    affected_components = models.ManyToManyField(
        Component,
        related_name='impacted_by',
        blank=True,
        help_text="Components that would be affected"
    )
    analysis_results = models.JSONField(
        default=dict,
        help_text="Detailed analysis results as JSON"
    )
    recommendations = models.TextField(
        blank=True,
        help_text="Recommended actions"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['flow', 'severity']),
            models.Index(fields=['affected_component']),
        ]
    
    def __str__(self):
        return f"Impact Analysis: {self.affected_component.name} ({self.severity})"

