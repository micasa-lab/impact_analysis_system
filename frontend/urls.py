"""
URL patterns for the frontend interface.

This module defines the URL routing for the web-based user interface
including dashboard, flow designer, and management pages.
"""

from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Component management
    path('components/', views.component_list, name='component_list'),
    path('components/<uuid:pk>/', views.component_detail, name='component_detail'),
    # Component CRUD operations (ADD THESE LINES)
    path('components/add/', views.component_add, name='component_add'),
    path('components/<uuid:pk>/edit/', views.component_edit, name='component_edit'),
    path('components/<uuid:pk>/delete/', views.component_delete, name='component_delete'),

    
    # Runbook management
    path('runbooks/', views.runbook_list, name='runbook_list'),
    path('runbooks/<uuid:pk>/', views.runbook_detail, name='runbook_detail'),
    
    # Flow management
    path('flows/<uuid:pk>/delete/', views.flow_delete, name='flow_delete'),
    path('flows/', views.flow_list, name='flow_list'),
    path('flows/<uuid:pk>/', views.flow_detail, name='flow_detail'),
    path('flows/designer/', views.flow_designer, name='flow_designer'),  # For new flows
    path('flows/<uuid:pk>/designer/', views.flow_designer_edit, name='flow_designer_edit'),  # For editing
    path('api/flows/create/', views.flow_create_api, name='flow_create_api'),  # API endpoint

    
    # YAML import/export
    path('yaml/import/', views.yaml_import, name='yaml_import'),
    path('yaml/export/<uuid:pk>/', views.yaml_export, name='yaml_export'),
    
    # Impact analysis
    path('impact-analysis/', views.impact_analysis_view, name='impact_analysis'),
    path('impact-analysis/<uuid:pk>/', views.impact_analysis_detail, name='impact_analysis_detail'),
    
    # System statistics
    path('statistics/', views.system_statistics, name='system_statistics'),
    # Add this to your urlpatterns if it's missing
    path('components/<uuid:pk>/', views.component_detail, name='component_detail'),

]

