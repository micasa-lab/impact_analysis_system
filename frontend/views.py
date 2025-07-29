"""
Frontend views for the Impact Analysis System.

This module contains Django views for rendering the web-based user interface
including dashboard, flow designer, and management pages.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.core.paginator import Paginator
import json
import yaml

from core.models import (
    Component, Runbook, Step, Flow, FlowComponent, 
    Connection, ImpactAnalysis
)
from core.utils import ImpactAnalyzer, FlowValidator


@login_required
def dashboard(request):
    """Dashboard view with system overview and statistics."""
    
    # Get system statistics
    stats = {
        'components': {
            'total': Component.objects.count(),
            'active': Component.objects.filter(is_active=True).count(),
            'by_type': Component.objects.values('component_type').annotate(
                count=Count('id')
            ).order_by('component_type')
        },
        'runbooks': {
            'total': Runbook.objects.count(),
            'active': Runbook.objects.filter(is_active=True).count(),
        },
        'flows': {
            'total': Flow.objects.count(),
            'active': Flow.objects.filter(is_active=True).count(),
        },
        'impact_analyses': {
            'total': ImpactAnalysis.objects.count(),
            'by_severity': ImpactAnalysis.objects.values('severity').annotate(
                count=Count('id')
            ).order_by('severity')
        }
    }
    
    # Get recent activities
    recent_components = Component.objects.order_by('-created_at')[:5]
    recent_flows = Flow.objects.order_by('-created_at')[:5]
    recent_analyses = ImpactAnalysis.objects.order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'recent_components': recent_components,
        'recent_flows': recent_flows,
        'recent_analyses': recent_analyses,
    }
    
    return render(request, 'frontend/dashboard.html', context)


@login_required
def component_list(request):
    """List all components with filtering and pagination."""
    
    components = Component.objects.all()
    
    # Apply filters
    component_type = request.GET.get('type')
    if component_type:
        components = components.filter(component_type=component_type)
    
    is_active = request.GET.get('active')
    if is_active:
        components = components.filter(is_active=is_active.lower() == 'true')
    
    search = request.GET.get('search')
    if search:
        components = components.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(business_function__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(components, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'component_types': Component.COMPONENT_TYPES,
        'current_filters': {
            'type': component_type,
            'active': is_active,
            'search': search,
        }
    }
    
    return render(request, 'frontend/component_list.html', context)


@login_required
def component_detail(request, pk):
    """Display component details with runbooks and flows."""
    
    component = get_object_or_404(Component, pk=pk)
    runbooks = component.runbooks.filter(is_active=True)
    flow_instances = FlowComponent.objects.filter(component=component)
    
    context = {
        'component': component,
        'runbooks': runbooks,
        'flow_instances': flow_instances,
    }
    
    return render(request, 'frontend/component_detail.html', context)


@login_required
def component_create(request):
    """Create a new component."""
    
    if request.method == 'POST':
        # Handle form submission
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        business_function = request.POST.get('business_function')
        component_type = request.POST.get('component_type')
        
        if name and business_function and component_type:
            component = Component.objects.create(
                name=name,
                description=description,
                business_function=business_function,
                component_type=component_type,
                created_by=request.user
            )
            messages.success(request, f'Component "{component.name}" created successfully.')
            return redirect('frontend:component_detail', pk=component.pk)
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    context = {
        'component_types': Component.COMPONENT_TYPES,
    }
    
    return render(request, 'frontend/component_form.html', context)


@login_required
def component_edit(request, pk):
    """Edit an existing component."""
    
    component = get_object_or_404(Component, pk=pk)
    
    if request.method == 'POST':
        # Handle form submission
        component.name = request.POST.get('name', component.name)
        component.description = request.POST.get('description', component.description)
        component.business_function = request.POST.get('business_function', component.business_function)
        component.component_type = request.POST.get('component_type', component.component_type)
        component.is_active = request.POST.get('is_active') == 'on'
        
        component.save()
        messages.success(request, f'Component "{component.name}" updated successfully.')
        return redirect('frontend:component_detail', pk=component.pk)
    
    context = {
        'component': component,
        'component_types': Component.COMPONENT_TYPES,
        'is_edit': True,
    }
    
    return render(request, 'frontend/component_form.html', context)


@login_required
def runbook_list(request):
    """List all runbooks with filtering and pagination."""
    
    runbooks = Runbook.objects.select_related('component').all()
    
    # Apply filters
    component_id = request.GET.get('component')
    if component_id:
        runbooks = runbooks.filter(component_id=component_id)
    
    is_active = request.GET.get('active')
    if is_active:
        runbooks = runbooks.filter(is_active=is_active.lower() == 'true')
    
    search = request.GET.get('search')
    if search:
        runbooks = runbooks.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(component__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(runbooks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get components for filter dropdown
    components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'components': components,
        'current_filters': {
            'component': component_id,
            'active': is_active,
            'search': search,
        }
    }
    
    return render(request, 'frontend/runbook_list.html', context)


@login_required
def runbook_detail(request, pk):
    """Display runbook details with steps."""
    
    runbook = get_object_or_404(Runbook, pk=pk)
    steps = runbook.steps.all()
    
    context = {
        'runbook': runbook,
        'steps': steps,
    }
    
    return render(request, 'frontend/runbook_detail.html', context)


@login_required
def runbook_create(request):
    """Create a new runbook."""
    
    if request.method == 'POST':
        # Handle form submission
        component_id = request.POST.get('component')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        version = request.POST.get('version', '1.0.0')
        
        if component_id and name:
            component = get_object_or_404(Component, pk=component_id)
            runbook = Runbook.objects.create(
                component=component,
                name=name,
                description=description,
                version=version,
                created_by=request.user
            )
            messages.success(request, f'Runbook "{runbook.name}" created successfully.')
            return redirect('frontend:runbook_detail', pk=runbook.pk)
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'components': components,
    }
    
    return render(request, 'frontend/runbook_form.html', context)


@login_required
def runbook_edit(request, pk):
    """Edit an existing runbook."""
    
    runbook = get_object_or_404(Runbook, pk=pk)
    
    if request.method == 'POST':
        # Handle form submission
        runbook.name = request.POST.get('name', runbook.name)
        runbook.description = request.POST.get('description', runbook.description)
        runbook.version = request.POST.get('version', runbook.version)
        runbook.is_active = request.POST.get('is_active') == 'on'
        
        runbook.save()
        messages.success(request, f'Runbook "{runbook.name}" updated successfully.')
        return redirect('frontend:runbook_detail', pk=runbook.pk)
    
    components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'runbook': runbook,
        'components': components,
        'is_edit': True,
    }
    
    return render(request, 'frontend/runbook_form.html', context)


@login_required
def flow_list(request):
    """List all flows with filtering and pagination."""
    
    flows = Flow.objects.all()
    
    # Apply filters
    is_active = request.GET.get('active')
    if is_active:
        flows = flows.filter(is_active=is_active.lower() == 'true')
    
    search = request.GET.get('search')
    if search:
        flows = flows.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(flows, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_filters': {
            'active': is_active,
            'search': search,
        }
    }
    
    return render(request, 'frontend/flow_list.html', context)


# @login_required
# def flow_detail(request, pk):
#     """Display detailed information about a specific flow."""
#     try:
#         flow = get_object_or_404(Flow, pk=pk)
        
#         # Get flow components with related component data
#         flow_components = flow.flow_components.select_related('component').all()
        
#         # Get all component IDs for connection filtering
#         component_ids = [fc.component.id for fc in flow_components]
        
#         # Get connections within this flow
#         connections = Connection.objects.filter(
#             Q(source_component_id__in=component_ids) |
#             Q(target_component_id__in=component_ids)
#         ).select_related('source_component', 'target_component')
        
#         # Get recent impact analyses for this flow
#         impact_analyses = ImpactAnalysis.objects.filter(
#             flow=flow
#         ).select_related('affected_component').order_by('-created_at')[:10]
        
#         # Calculate statistics
#         stats = {
#             'total_components': flow_components.count(),
#             'total_connections': connections.count(),
#             'active_components': flow_components.filter(component__is_active=True).count(),
#             'component_types': {}
#         }
        
#         # Calculate component type distribution
#         for fc in flow_components:
#             comp_type = fc.component.get_component_type_display()
#             stats['component_types'][comp_type] = stats['component_types'].get(comp_type, 0) + 1
        
#         context = {
#             'flow': flow,
#             'components': flow_components,
#             'connections': connections,
#             'impact_analyses': impact_analyses,
#             'stats': stats,
#         }
        
#         return render(request, 'frontend/flow_detail.html', context)
        
#     except Exception as e:
#         print(f"Error in flow_detail view: {str(e)}")
#         import traceback
#         traceback.print_exc()
        
#         # Return error page or redirect
#         from django.contrib import messages
#         messages.error(request, f'Error loading flow details: {str(e)}')
#         return redirect('frontend:flow_list')



@login_required
def flow_create(request):
    """Create a new flow."""
    
    if request.method == 'POST':
        # Handle form submission
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        version = request.POST.get('version', '1.0.0')
        
        if name:
            flow = Flow.objects.create(
                name=name,
                description=description,
                version=version,
                created_by=request.user
            )
            messages.success(request, f'Flow "{flow.name}" created successfully.')
            return redirect('frontend:flow_designer', pk=flow.pk)
        else:
            messages.error(request, 'Please provide a flow name.')
    
    return render(request, 'frontend/flow_form.html')


@login_required
def flow_edit(request, pk):
    """Edit an existing flow."""
    
    flow = get_object_or_404(Flow, pk=pk)
    
    if request.method == 'POST':
        # Handle form submission
        flow.name = request.POST.get('name', flow.name)
        flow.description = request.POST.get('description', flow.description)
        flow.version = request.POST.get('version', flow.version)
        flow.is_active = request.POST.get('is_active') == 'on'
        
        flow.save()
        messages.success(request, f'Flow "{flow.name}" updated successfully.')
        return redirect('frontend:flow_detail', pk=flow.pk)
    
    context = {
        'flow': flow,
        'is_edit': True,
    }
    
    return render(request, 'frontend/flow_form.html', context)

@login_required
@require_http_methods(["POST"])
def flow_create_api(request):
    """API endpoint to create a new flow from the designer."""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Flow name is required'}, status=400)
        
        # Create the flow
        flow = Flow.objects.create(
            name=name,
            description=data.get('description', ''),
            system_name=data.get('system_name', ''),
            system_purpose=data.get('system_purpose', ''),
            created_by=request.user
        )
        
        # Add components to the flow
        components_data = data.get('components', [])
        flow_component_map = {}  # Map component_id to flow_component for connections
        
        for comp_data in components_data:
            try:
                # Use componentId field which contains the actual UUID
                component_id = comp_data.get('componentId')
                if not component_id:
                    continue  # Skip if no componentId
                    
                component = Component.objects.get(pk=component_id)
                flow_component = FlowComponent.objects.create(
                    flow=flow,
                    component=component,
                    position_x=comp_data.get('x', 0),
                    position_y=comp_data.get('y', 0),
                    created_by=request.user
                )
                flow_component_map[component_id] = flow_component
            except Component.DoesNotExist:
                continue  # Skip invalid components
            except Exception as e:
                print(f"Error processing component {comp_data}: {e}")
                continue  # Skip problematic components
        
        # Add connections to the flow
        connections_data = data.get('connections', [])
        for conn_data in connections_data:
            source_id = conn_data.get('sourceComponentId')
            target_id = conn_data.get('targetComponentId')
            
            if source_id in flow_component_map and target_id in flow_component_map:
                Connection.objects.create(
                    flow=flow,
                    source_component=flow_component_map[source_id],
                    target_component=flow_component_map[target_id],
                    connection_type=conn_data.get('connectionType', 'api'),
                    # description=conn_data.get('description', ''),
                    created_by=request.user
                )
        
        return JsonResponse({
            'success': True,
            'flow_id': str(flow.id),
            'message': 'Flow created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    

@login_required
def flow_designer(request):
    """Interactive flow designer interface for creating new flows."""
    
    # Get all available components for the designer
    available_components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'flow': None,  # No existing flow for new creation
        'flow_components': [],  # Empty for new flow
        'connections': [],  # Empty for new flow
        'available_components': available_components,
        'component_types': Component.COMPONENT_TYPES,
        'connection_types': Connection.CONNECTION_TYPES,
        'mode': 'create'
    }
    
    return render(request, 'frontend/flow_designer.html', context)

@login_required
def flow_designer_edit(request, pk):
    """Edit an existing flow in the designer."""
    flow = get_object_or_404(Flow, pk=pk)
    flow_components = flow.flow_components.select_related('component').all()
    
    # Get connections for this flow
    component_ids = [fc.component.id for fc in flow_components]
    connections = Connection.objects.filter(
        source_component_id__in=component_ids,
        target_component_id__in=component_ids
    ).select_related('source_component', 'target_component')
    
    # Get all available components for adding to flow
    available_components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'flow': flow,
        'flow_components': flow_components,
        'connections': connections,
        'available_components': available_components,
        'component_types': Component.COMPONENT_TYPES,
        'connection_types': Connection.CONNECTION_TYPES,
        'mode': 'edit'
    }
    
    return render(request, 'frontend/flow_designer.html', context)


@login_required
def yaml_import(request):
    """Import flow from YAML file."""
    
    if request.method == 'POST':
        yaml_content = request.POST.get('yaml_content', '')
        
        if yaml_content:
            try:
                # Validate YAML content
                from api.serializers import YAMLFlowSerializer
                serializer = YAMLFlowSerializer(data={'yaml_content': yaml_content})
                
                if serializer.is_valid():
                    flow = serializer.save()
                    flow.created_by = request.user
                    flow.save()
                    
                    messages.success(request, f'Flow "{flow.name}" imported successfully.')
                    return redirect('frontend:flow_detail', pk=flow.pk)
                else:
                    for field, errors in serializer.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
            
            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')
        else:
            messages.error(request, 'Please provide YAML content.')
    
    return render(request, 'frontend/yaml_import.html')


@login_required
def yaml_export(request, pk):
    """Export flow as YAML file."""
    
    flow = get_object_or_404(Flow, pk=pk)
    
    from api.serializers import FlowExportSerializer
    serializer = FlowExportSerializer(flow)
    data = serializer.to_representation(flow)
    
    response = HttpResponse(
        data['yaml_content'], 
        content_type='application/x-yaml'
    )
    response['Content-Disposition'] = f'attachment; filename="{flow.name}.yaml"'
    
    return response


@login_required
def impact_analysis(request):
    """Impact analysis dashboard."""
    
    analyses = ImpactAnalysis.objects.select_related(
        'flow', 'affected_component'
    ).order_by('-created_at')
    
    # Apply filters
    flow_id = request.GET.get('flow')
    if flow_id:
        analyses = analyses.filter(flow_id=flow_id)
    
    severity = request.GET.get('severity')
    if severity:
        analyses = analyses.filter(severity=severity)
    
    # Pagination
    paginator = Paginator(analyses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get flows for filter dropdown
    flows = Flow.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'flows': flows,
        'severity_levels': ImpactAnalysis.SEVERITY_LEVELS,
        'current_filters': {
            'flow': flow_id,
            'severity': severity,
        }
    }
    
    return render(request, 'frontend/impact_analysis.html', context)


@login_required
def impact_detail(request, flow_pk, component_pk):
    """Detailed impact analysis for a specific component in a flow."""
    
    flow = get_object_or_404(Flow, pk=flow_pk)
    component = get_object_or_404(Component, pk=component_pk)
    
    # Perform impact analysis
    analysis_result = ImpactAnalyzer.analyze_component_impact(flow, component)
    
    context = {
        'flow': flow,
        'component': component,
        'analysis_result': analysis_result,
    }
    
    return render(request, 'frontend/impact_detail.html', context)


# API endpoints for AJAX requests
@login_required
@require_http_methods(["POST"])
def api_add_component_to_flow(request, flow_pk):
    """Add a component to a flow via AJAX."""
    
    flow = get_object_or_404(Flow, pk=flow_pk)
    component_id = request.POST.get('component_id')
    position_x = float(request.POST.get('position_x', 0))
    position_y = float(request.POST.get('position_y', 0))
    
    if component_id:
        component = get_object_or_404(Component, pk=component_id)
        
        # Check if component is already in flow
        if FlowComponent.objects.filter(flow=flow, component=component).exists():
            return JsonResponse({'error': 'Component already in flow'}, status=400)
        
        flow_component = FlowComponent.objects.create(
            flow=flow,
            component=component,
            position_x=position_x,
            position_y=position_y,
            created_by=request.user
        )
        
        return JsonResponse({
            'id': str(flow_component.id),
            'component_name': component.name,
            'component_type': component.component_type,
            'position_x': position_x,
            'position_y': position_y,
        })
    
    return JsonResponse({'error': 'Component ID required'}, status=400)


@login_required
@require_http_methods(["POST"])
def api_create_connection(request, flow_pk):
    """Create a connection between components via AJAX."""
    
    flow = get_object_or_404(Flow, pk=flow_pk)
    source_id = request.POST.get('source_id')
    target_id = request.POST.get('target_id')
    connection_type = request.POST.get('connection_type', 'http')
    
    if source_id and target_id:
        source_component = get_object_or_404(FlowComponent, pk=source_id, flow=flow)
        target_component = get_object_or_404(FlowComponent, pk=target_id, flow=flow)
        
        connection = Connection.objects.create(
            flow=flow,
            source_component=source_component,
            target_component=target_component,
            connection_type=connection_type,
            created_by=request.user
        )
        
        return JsonResponse({
            'id': str(connection.id),
            'source_id': source_id,
            'target_id': target_id,
            'connection_type': connection_type,
        })
    
    return JsonResponse({'error': 'Source and target IDs required'}, status=400)



@login_required
def runbook_list(request):
    """Display list of runbooks with filtering and management capabilities."""
    return render(request, 'frontend/runbook_list.html')


@login_required
def runbook_detail(request, pk):
    """Display detailed view of a specific runbook."""
    runbook = get_object_or_404(Runbook, pk=pk)
    context = {
        'runbook': runbook,
        'steps': runbook.steps.all().order_by('order_index')
    }
    return render(request, 'frontend/runbook_detail.html', context)


@login_required
def flow_list(request):
    """List all flows with filtering and pagination."""
    
    flows = Flow.objects.all()
    
    # Apply filters
    is_active = request.GET.get('active')
    if is_active:
        flows = flows.filter(is_active=is_active.lower() == 'true')
    
    search = request.GET.get('search')
    if search:
        flows = flows.filter(
            Q(name__icontains=search) |
            Q(system_name__icontains=search) |
            Q(system_purpose__icontains=search)
        )
    
    # Order by most recent
    flows = flows.order_by('-updated_at')
    
    # Create a list of flow data with counts
    flow_data = []
    for flow in flows:
        # Use the existing property methods if they exist
        try:
            comp_count = flow.component_count if hasattr(flow, 'component_count') else flow.flow_components.count()
        except:
            comp_count = flow.flow_components.count()
        
        # Calculate connection count
        component_ids = flow.flow_components.values_list('component_id', flat=True)
        if component_ids:
            conn_count = Connection.objects.filter(
                Q(source_component_id__in=component_ids) |
                Q(target_component_id__in=component_ids)
            ).distinct().count()
        else:
            conn_count = 0
        
        # Create a flow data object
        flow_info = {
            'flow': flow,
            'comp_count': comp_count,
            'conn_count': conn_count,
        }
        flow_data.append(flow_info)
    
    # Pagination
    paginator = Paginator(flow_data, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_filters': {
            'active': request.GET.get('active', ''),
            'search': request.GET.get('search', ''),
        },
    }
    
    return render(request, 'frontend/flow_list.html', context)


@login_required
def flow_detail(request, pk):
    """Display detailed information about a specific flow."""
    try:
        flow = get_object_or_404(Flow, pk=pk)
        
        # Get flow components with related component data
        flow_components = flow.flow_components.select_related('component').all()
        
        # Get all component IDs for connection filtering
        component_ids = [fc.component.id for fc in flow_components]
        
        # Get connections within this flow
        connections = Connection.objects.filter(
            Q(source_component_id__in=component_ids) |
            Q(target_component_id__in=component_ids)
        ).select_related('source_component', 'target_component')
        
        # Get recent impact analyses for this flow
        impact_analyses = ImpactAnalysis.objects.filter(
            flow=flow
        ).select_related('affected_component').order_by('-created_at')[:10]
        
        # Calculate statistics
        stats = {
            'total_components': flow_components.count(),
            'total_connections': connections.count(),
            'active_components': flow_components.filter(component__is_active=True).count(),
            'component_types': {}
        }
        
        # Calculate component type distribution
        for fc in flow_components:
            comp_type = fc.component.get_component_type_display()
            stats['component_types'][comp_type] = stats['component_types'].get(comp_type, 0) + 1
        
        context = {
            'flow': flow,
            'components': flow_components,
            'connections': connections,
            'impact_analyses': impact_analyses,
            'stats': stats,
        }
        
        return render(request, 'frontend/flow_detail.html', context)
        
    except Exception as e:
        print(f"Error in flow_detail view: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return error page or redirect
        from django.contrib import messages
        messages.error(request, f'Error loading flow details: {str(e)}')
        return redirect('frontend:flow_list')

@login_required
def impact_analysis_view(request):
    """Impact analysis interface."""
    
    # Get all active flows
    flows = Flow.objects.filter(is_active=True).order_by('name')
    
    # Get recent impact analyses - FIX: Use affected_component
    recent_analyses = ImpactAnalysis.objects.select_related(
        'flow_id', 'affected_component'  # Changed from target_component
    ).order_by('-created_at')[:10]
    
    context = {
        'flows': flows,
        'recent_analyses': recent_analyses,
    }
    
    return render(request, 'frontend/impact_analysis.html', context)

@login_required
def impact_analysis_detail(request, pk):
    """Display detailed view of a specific impact analysis."""
    analysis = get_object_or_404(ImpactAnalysis, pk=pk)
    context = {
        'analysis': analysis,
        'flow': analysis.flow,
        'component': analysis.affected_component
    }
    return render(request, 'frontend/impact_analysis_detail.html', context)


@login_required
def flow_designer(request):
    """Interactive flow designer interface for creating new flows."""
    
    # Get all available components for the designer
    available_components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'flow': None,  # No existing flow for new creation
        'flow_components': [],  # Empty for new flow
        'connections': [],  # Empty for new flow
        'available_components': available_components,
        'component_types': Component.COMPONENT_TYPES,
        'connection_types': Connection.CONNECTION_TYPES,
        'mode': 'create'
    }
    
    return render(request, 'frontend/flow_designer.html', context)


@login_required
def flow_designer_edit(request, pk):
    """Edit an existing flow in the designer."""
    flow = get_object_or_404(Flow, pk=pk)
    flow_components = flow.flow_components.select_related('component').all()
    
    # Get connections for this flow
    component_ids = [fc.component.id for fc in flow_components]
    connections = Connection.objects.filter(
        source_component_id__in=component_ids,
        target_component_id__in=component_ids
    ).select_related('source_component', 'target_component')
    
    # Get all available components for adding to flow
    available_components = Component.objects.filter(is_active=True).order_by('name')
    
    context = {
        'flow': flow,
        'flow_components': flow_components,
        'connections': connections,
        'available_components': available_components,
        'component_types': Component.COMPONENT_TYPES,
        'connection_types': Connection.CONNECTION_TYPES,
        'mode': 'edit'
    }
    
    return render(request, 'frontend/flow_designer.html', context)



@login_required
@require_http_methods(["POST"] )
def flow_delete(request, pk):
    """Delete a flow."""
    flow = get_object_or_404(Flow, pk=pk)
    
    try:
        flow_name = flow.name
        flow.delete()
        messages.success(request, f'Flow "{flow_name}" deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting flow: {str(e)}')
    
    return redirect('frontend:flow_list')


@login_required
def component_detail(request, pk):
    """Display detailed view of a specific component."""
    component = get_object_or_404(Component, pk=pk)
    context = {
        'component': component,
        'runbooks': component.runbooks.all(),
        'flows': Flow.objects.filter(flow_components__component=component)
    }
    return render(request, 'frontend/component_detail.html', context)


@login_required
def system_statistics(request):
    """Display system statistics and analytics."""
    from django.db.models import Count, Avg
    
    # Component statistics
    component_stats = Component.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=models.Q(is_active=True))
    )
    
    component_types = Component.objects.values('component_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Flow statistics
    flow_stats = Flow.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=models.Q(is_active=True))
    )
    
    # Runbook statistics
    runbook_stats = Runbook.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=models.Q(is_active=True)),
        avg_steps=Avg('steps__id')
    )
    
    # Impact analysis statistics
    analysis_stats = ImpactAnalysis.objects.aggregate(
        total=Count('id')
    )
    
    analysis_by_severity = ImpactAnalysis.objects.values('severity').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'component_stats': component_stats,
        'component_types': component_types,
        'flow_stats': flow_stats,
        'runbook_stats': runbook_stats,
        'analysis_stats': analysis_stats,
        'analysis_by_severity': analysis_by_severity
    }
    
    return render(request, 'frontend/system_statistics.html', context)

@login_required
def component_add(request):
    """Add a new component."""
    if request.method == 'POST':
        try:
            component = Component.objects.create(
                name=request.POST.get('name'),
                component_type=request.POST.get('component_type'),
                description=request.POST.get('description', ''),
                business_function=request.POST.get('business_function', ''),
                owned_by=request.POST.get('owned_by', ''),
                technical_details=request.POST.get('technical_details', ''),
                dependencies=request.POST.get('dependencies', ''),
                kpis=json.loads(request.POST.get('kpis', '[]')) if request.POST.get('kpis') else [],
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, f'Component "{component.name}" created successfully.')
            return redirect('frontend:component_list')
        except Exception as e:
            messages.error(request, f'Error creating component: {str(e)}')
    
    context = {
        'component_types': Component.COMPONENT_TYPES,
    }
    return render(request, 'frontend/component_form.html', context)

@login_required
def component_edit(request, pk):
    """Edit an existing component."""
    component = get_object_or_404(Component, pk=pk)
    
    if request.method == 'POST':
        try:
            component.name = request.POST.get('name')
            component.component_type = request.POST.get('component_type')
            component.description = request.POST.get('description', '')
            component.business_function = request.POST.get('business_function', '')
            component.owned_by = request.POST.get('owned_by', '')
            component.technical_details = request.POST.get('technical_details', '')
            component.dependencies = request.POST.get('dependencies', '')
            component.kpis = json.loads(request.POST.get('kpis', '[]')) if request.POST.get('kpis') else []
            component.is_active = request.POST.get('is_active') == 'on'
            component.save()
            
            messages.success(request, f'Component "{component.name}" updated successfully.')
            return redirect('frontend:component_list')
        except Exception as e:
            messages.error(request, f'Error updating component: {str(e)}')
    
    context = {
        'component': component,
        'component_types': Component.COMPONENT_TYPES,
        'kpis_json': json.dumps(component.kpis) if component.kpis else '[]',
    }
    return render(request, 'frontend/component_form.html', context)

@login_required
@require_http_methods(["POST"] )
def component_delete(request, pk):
    """Delete a component."""
    component = get_object_or_404(Component, pk=pk)
    
    try:
        component_name = component.name
        component.delete()
        messages.success(request, f'Component "{component_name}" deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting component: {str(e)}')
    
    return redirect('frontend:component_list')
