"""
URL patterns for the Impact Analysis System API.

This module defines the URL routing for all API endpoints including
REST API viewsets and custom views for YAML processing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ComponentViewSet, RunbookViewSet, StepViewSet,
    FlowViewSet, FlowComponentViewSet, ConnectionViewSet,
    ImpactAnalysisViewSet, YAMLImportView, YAMLValidateView,
    JSONImportView, JSONValidateView, SystemStatsView
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'components', ComponentViewSet)
router.register(r'runbooks', RunbookViewSet)
router.register(r'steps', StepViewSet)
router.register(r'flows', FlowViewSet)
router.register(r'flow-components', FlowComponentViewSet)
router.register(r'connections', ConnectionViewSet)
router.register(r'impact-analyses', ImpactAnalysisViewSet)

# Define URL patterns
urlpatterns = [
    # API root
    path('', include(router.urls)),
    
    # YAML processing endpoints
    path('yaml/import/', YAMLImportView.as_view(), name='yaml-import'),
    path('yaml/validate/', YAMLValidateView.as_view(), name='yaml-validate'),
    
    # JSON processing endpoints
    path('json/import/', JSONImportView.as_view(), name='json-import'),
    path('json/validate/', JSONValidateView.as_view(), name='json-validate'),
    
    # System statistics
    path('stats/', SystemStatsView.as_view(), name='system-stats'),
    
    # Authentication endpoints
    path('auth/', include('rest_framework.urls')),
    path('flows/<uuid:flow_id>/components/', FlowViewSet.get_flow_components, name='flow-components'),

    # Impact Analysis
    # path('impact-analyses/', create_impact_analysis, name='create-impact-analysis'),
    path('perform-impact-analysis/', FlowViewSet.perform_impact_analysis, name='perform-impact-analysis'),  # NEW ENDPOINT

]

# Add app name for namespacing
app_name = 'api'

