"""
Django admin configuration for the Impact Analysis System.

This module configures the Django admin interface for managing
components, runbooks, flows, and related models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    Component, Runbook, Step, Flow, FlowComponent, 
    Connection, ImpactAnalysis
)


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    """Admin interface for Component model."""
    
    list_display = [
        'name', 'component_type', 'business_function_short', 
        'runbook_count', 'is_active', 'created_at'
    ]
    list_filter = ['component_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'business_function']
    readonly_fields = ['id', 'created_at', 'updated_at', 'runbook_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'component_type', 'is_active')
        }),
        ('Description', {
            'fields': ('description', 'business_function')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def business_function_short(self, obj):
        """Return truncated business function for list display."""
        if len(obj.business_function) > 50:
            return obj.business_function[:50] + '...'
        return obj.business_function
    business_function_short.short_description = 'Business Function'
    
    def runbook_count(self, obj):
        """Return the number of runbooks for this component."""
        count = obj.runbooks.count()
        if count > 0:
            url = reverse('admin:core_runbook_changelist') + f'?component__id__exact={obj.id}'
            return format_html('<a href="{}">{} runbooks</a>', url, count)
        return '0 runbooks'
    runbook_count.short_description = 'Runbooks'


class StepInline(admin.TabularInline):
    """Inline admin for Step model within Runbook."""
    
    model = Step
    extra = 1
    fields = ['order', 'name', 'action_type', 'estimated_duration', 'is_critical']
    ordering = ['order']


@admin.register(Runbook)
class RunbookAdmin(admin.ModelAdmin):
    """Admin interface for Runbook model."""
    
    list_display = [
        'name', 'component', 'version', 'step_count', 
        'estimated_total_duration', 'is_active', 'created_at'
    ]
    list_filter = ['component__component_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'component__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'step_count', 'estimated_total_duration']
    inlines = [StepInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('component', 'name', 'version', 'is_active')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Statistics', {
            'fields': ('step_count', 'estimated_total_duration'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def step_count(self, obj):
        """Return the number of steps in this runbook."""
        return obj.steps.count()
    step_count.short_description = 'Steps'
    
    def estimated_total_duration(self, obj):
        """Return the total estimated duration."""
        total = obj.estimated_total_duration
        if total:
            hours = total // 60
            minutes = total % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "0m"
    estimated_total_duration.short_description = 'Total Duration'


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    """Admin interface for Step model."""
    
    list_display = [
        'runbook', 'order', 'name', 'action_type', 
        'estimated_duration', 'is_critical'
    ]
    list_filter = ['action_type', 'is_critical', 'runbook__component__component_type']
    search_fields = ['name', 'description', 'runbook__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('runbook', 'order', 'name', 'action_type')
        }),
        ('Details', {
            'fields': ('description', 'estimated_duration', 'is_critical')
        }),
        ('Parameters', {
            'fields': ('parameters',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


class FlowComponentInline(admin.TabularInline):
    """Inline admin for FlowComponent model within Flow."""
    
    model = FlowComponent
    extra = 1
    fields = ['component', 'position_x', 'position_y']


class ConnectionInline(admin.TabularInline):
    """Inline admin for Connection model within Flow."""
    
    model = Connection
    extra = 1
    fields = ['source_component', 'target_component', 'connection_type']


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    """Admin interface for Flow model."""
    
    list_display = [
        'name', 'version', 'component_count', 'connection_count', 
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'component_count', 'connection_count']
    inlines = [FlowComponentInline, ConnectionInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'version', 'is_active')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('YAML Content', {
            'fields': ('yaml_content',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('component_count', 'connection_count'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def component_count(self, obj):
        """Return the number of components in this flow."""
        return obj.flow_components.count()
    component_count.short_description = 'Components'
    
    def connection_count(self, obj):
        """Return the number of connections in this flow."""
        return obj.connections.count()
    connection_count.short_description = 'Connections'


@admin.register(FlowComponent)
class FlowComponentAdmin(admin.ModelAdmin):
    """Admin interface for FlowComponent model."""
    
    list_display = ['flow', 'component', 'position_x', 'position_y']
    list_filter = ['flow', 'component__component_type']
    search_fields = ['flow__name', 'component__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    """Admin interface for Connection model."""
    
    list_display = [
        'flow', 'source_component', 'target_component', 
        'connection_type', 'created_at'
    ]
    list_filter = ['connection_type', 'flow']
    search_fields = [
        'flow__name', 'source_component__component__name', 
        'target_component__component__name'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ImpactAnalysis)
class ImpactAnalysisAdmin(admin.ModelAdmin):
    """Admin interface for ImpactAnalysis model."""
    
    list_display = [
        'flow', 'affected_component', 'severity', 
        'affected_components_count', 'created_at'
    ]
    list_filter = ['severity', 'flow', 'affected_component__component_type']
    search_fields = [
        'flow__name', 'affected_component__name', 
        'recommendations'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['affected_components']
    fieldsets = (
        ('Basic Information', {
            'fields': ('flow', 'affected_component', 'severity')
        }),
        ('Impact Details', {
            'fields': ('affected_components', 'recommendations')
        }),
        ('Analysis Results', {
            'fields': ('analysis_results',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def affected_components_count(self, obj):
        """Return the number of affected components."""
        count = obj.affected_components.count()
        return f"{count} components"
    affected_components_count.short_description = 'Affected Components'


# Customize admin site
admin.site.site_header = "Impact Analysis System Administration"
admin.site.site_title = "Impact Analysis Admin"
admin.site.index_title = "Welcome to Impact Analysis System Administration"

