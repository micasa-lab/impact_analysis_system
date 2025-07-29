# API Documentation

This document provides comprehensive documentation for the Impact Analysis System REST API.

## Base URL

```
http://localhost:8000/api/v1/
```

## Authentication

The API uses Django's session-based authentication. For API access, you can also use token authentication.

### Session Authentication
```bash
# Login first through the web interface, then use session cookies
curl -X GET "http://localhost:8000/api/v1/components/" \
  -H "Cookie: sessionid=your-session-id"
```

### Token Authentication (Future)
```bash
curl -X GET "http://localhost:8000/api/v1/components/" \
  -H "Authorization: Token your-api-token"
```

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "count": 25,
  "next": "http://localhost:8000/api/v1/components/?page=2",
  "previous": null,
  "results": [...]
}
```

### Error Response
```json
{
  "error": "Error message",
  "details": {
    "field_name": ["Field-specific error message"]
  }
}
```

## Endpoints

### Components

#### List Components
```http
GET /api/v1/components/
```

**Parameters:**
- `component_type` (string): Filter by component type
- `is_active` (boolean): Filter by active status
- `search` (string): Search in name, description, business_function
- `ordering` (string): Order by field (name, component_type, created_at)
- `page` (integer): Page number for pagination

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "name": "Payment Service",
      "component_type": "service",
      "business_function": "Payment Processing",
      "description": "Handles payment transactions",
      "is_active": true,
      "created_at": "2024-07-29T10:00:00Z",
      "updated_at": "2024-07-29T10:00:00Z"
    }
  ]
}
```

#### Create Component
```http
POST /api/v1/components/
```

**Request Body:**
```json
{
  "name": "New Component",
  "component_type": "service",
  "business_function": "Business Function",
  "description": "Component description",
  "is_active": true,
  "metadata": {
    "version": "1.0",
    "owner": "Team Name"
  }
}
```

**Response:**
```json
{
  "id": "new-uuid",
  "name": "New Component",
  "component_type": "service",
  "business_function": "Business Function",
  "description": "Component description",
  "is_active": true,
  "metadata": {
    "version": "1.0",
    "owner": "Team Name"
  },
  "created_at": "2024-07-29T10:00:00Z",
  "updated_at": "2024-07-29T10:00:00Z"
}
```

#### Get Component
```http
GET /api/v1/components/{id}/
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Payment Service",
  "component_type": "service",
  "business_function": "Payment Processing",
  "description": "Handles payment transactions",
  "is_active": true,
  "metadata": {},
  "created_at": "2024-07-29T10:00:00Z",
  "updated_at": "2024-07-29T10:00:00Z"
}
```

#### Update Component
```http
PUT /api/v1/components/{id}/
PATCH /api/v1/components/{id}/
```

**Request Body (PUT - full update):**
```json
{
  "name": "Updated Component",
  "component_type": "service",
  "business_function": "Updated Function",
  "description": "Updated description",
  "is_active": true
}
```

**Request Body (PATCH - partial update):**
```json
{
  "description": "Updated description only"
}
```

#### Delete Component
```http
DELETE /api/v1/components/{id}/
```

**Response:** `204 No Content`

#### Component Types
```http
GET /api/v1/components/types/
```

**Response:**
```json
[
  {"value": "database", "label": "Database"},
  {"value": "service", "label": "Service"},
  {"value": "api", "label": "API"},
  {"value": "frontend", "label": "Frontend"},
  {"value": "middleware", "label": "Middleware"},
  {"value": "external_service", "label": "External Service"}
]
```

### Flows

#### List Flows
```http
GET /api/v1/flows/
```

**Parameters:**
- `is_active` (boolean): Filter by active status
- `search` (string): Search in name, description
- `ordering` (string): Order by field

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid",
      "name": "Payment Flow",
      "version": "1.0",
      "description": "Payment processing flow",
      "is_active": true,
      "created_at": "2024-07-29T10:00:00Z"
    }
  ]
}
```

#### Create Flow
```http
POST /api/v1/flows/
```

**Request Body:**
```json
{
  "name": "New Flow",
  "version": "1.0",
  "description": "Flow description",
  "is_active": true,
  "metadata": {
    "purpose": "Business process"
  }
}
```

#### Get Flow Details
```http
GET /api/v1/flows/{id}/
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Payment Flow",
  "version": "1.0",
  "description": "Payment processing flow",
  "is_active": true,
  "metadata": {},
  "components": [
    {
      "id": "component-uuid",
      "name": "Payment Service",
      "component_type": "service",
      "position_x": 100.0,
      "position_y": 200.0
    }
  ],
  "connections": [
    {
      "id": "connection-uuid",
      "source_component": "source-uuid",
      "target_component": "target-uuid",
      "connection_type": "api_call",
      "source_component_name": "Source Component",
      "target_component_name": "Target Component"
    }
  ],
  "created_at": "2024-07-29T10:00:00Z"
}
```

#### Get Flow Components
```http
GET /api/v1/flows/{id}/components/
```

**Response:**
```json
[
  {
    "id": "flow-component-uuid",
    "component": {
      "id": "component-uuid",
      "name": "Payment Service",
      "component_type": "service"
    },
    "position_x": 100.0,
    "position_y": 200.0,
    "created_at": "2024-07-29T10:00:00Z"
  }
]
```

#### Get Flow Connections
```http
GET /api/v1/flows/{id}/connections/
```

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": "connection-uuid",
      "source_component": "source-flow-component-uuid",
      "target_component": "target-flow-component-uuid",
      "source_component_name": "Source Component",
      "target_component_name": "Target Component",
      "connection_type": "api_call",
      "metadata": {},
      "created_at": "2024-07-29T10:00:00Z"
    }
  ]
}
```

### Impact Analysis

#### List Impact Analyses
```http
GET /api/v1/impact-analyses/
```

**Parameters:**
- `flow` (uuid): Filter by flow ID
- `affected_component` (uuid): Filter by component ID
- `severity` (string): Filter by severity level
- `ordering` (string): Order by field

**Response:**
```json
{
  "count": 10,
  "results": [
    {
      "id": "analysis-uuid",
      "flow": "flow-uuid",
      "flow_name": "Payment Flow",
      "affected_component": "component-uuid",
      "affected_component_name": "Payment Service",
      "severity": "medium",
      "created_at": "2024-07-29T10:00:00Z"
    }
  ]
}
```

#### Run Impact Analysis
```http
POST /api/v1/impact-analyses/
```

**Request Body:**
```json
{
  "flow": "flow-uuid",
  "affected_component": "component-uuid",
  "analysis_type": "downstream",
  "severity": "medium",
  "max_depth": "2",
  "include_inactive": false,
  "description": "Analysis description"
}
```

**Response:**
```json
{
  "id": "analysis-uuid",
  "flow": "flow-uuid",
  "flow_name": "Payment Flow",
  "affected_component": "component-uuid",
  "affected_component_name": "Payment Service",
  "severity": "medium",
  "analysis_type": "downstream",
  "max_depth": "2",
  "affected_components": [
    {
      "id": "affected-component-uuid",
      "name": "Validation Engine",
      "type": "service",
      "severity": "high",
      "impact_type": "direct",
      "depth": 1,
      "path": ["Payment Service", "Validation Engine"],
      "transitive_reason": "Directly connected to the target component",
      "connection_type": "api_call"
    },
    {
      "id": "indirect-component-uuid",
      "name": "Screening Engine",
      "type": "service",
      "severity": "low",
      "impact_type": "indirect",
      "depth": 2,
      "path": ["Payment Service", "Validation Engine", "Screening Engine"],
      "transitive_reason": "Indirectly impacted through: Validation Engine",
      "connection_type": "database_connection"
    }
  ],
  "severity_distribution": {
    "total": {"low": 1, "medium": 0, "high": 1, "critical": 0},
    "direct": {"low": 0, "medium": 0, "high": 1, "critical": 0},
    "indirect": {"low": 1, "medium": 0, "high": 0, "critical": 0},
    "summary": {
      "total_affected": 2,
      "direct_affected": 1,
      "indirect_affected": 1,
      "max_depth": 2
    }
  },
  "impact_paths": [
    {
      "from": "Payment Service",
      "to": "Validation Engine",
      "connection_type": "api_call",
      "severity": "high",
      "depth": 1
    }
  ],
  "recommendations": "Changes to this component will affect 2 other components.\n🔶 1 components have HIGH impact - plan carefully.\nReview all affected components before implementing changes.",
  "created_at": "2024-07-29T10:00:00Z"
}
```

#### Get Impact Analysis
```http
GET /api/v1/impact-analyses/{id}/
```

**Response:** Same as create response

### Connections

#### List Connections
```http
GET /api/v1/connections/
```

**Parameters:**
- `flow` (uuid): Filter by flow ID
- `connection_type` (string): Filter by connection type

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": "connection-uuid",
      "flow": "flow-uuid",
      "source_component": "source-flow-component-uuid",
      "target_component": "target-flow-component-uuid",
      "source_component_name": "Source Component",
      "target_component_name": "Target Component",
      "connection_type": "api_call",
      "metadata": {},
      "created_at": "2024-07-29T10:00:00Z"
    }
  ]
}
```

#### Connection Types
```http
GET /api/v1/connections/types/
```

**Response:**
```json
[
  {"value": "api_call", "label": "API Call"},
  {"value": "data_flow", "label": "Data Flow"},
  {"value": "message_queue", "label": "Message Queue"},
  {"value": "database_connection", "label": "Database Connection"},
  {"value": "event_trigger", "label": "Event Trigger"},
  {"value": "dependency", "label": "Dependency"}
]
```

### System Statistics

#### Get System Stats
```http
GET /api/v1/system-stats/
```

**Response:**
```json
{
  "components": {
    "total": 25,
    "active": 23,
    "by_type": {
      "database": {"label": "Database", "count": 5},
      "service": {"label": "Service", "count": 10},
      "api": {"label": "API", "count": 7},
      "frontend": {"label": "Frontend", "count": 2},
      "middleware": {"label": "Middleware", "count": 1}
    }
  },
  "flows": {
    "total": 8,
    "active": 7
  },
  "connections": {
    "total": 45,
    "by_type": {
      "api_call": {"label": "API Call", "count": 20},
      "data_flow": {"label": "Data Flow", "count": 15},
      "database_connection": {"label": "Database Connection", "count": 10}
    }
  },
  "impact_analyses": {
    "total": 15,
    "by_severity": {
      "low": {"label": "Low", "count": 5},
      "medium": {"label": "Medium", "count": 7},
      "high": {"label": "High", "count": 3},
      "critical": {"label": "Critical", "count": 0}
    }
  }
}
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Resource deleted successfully |
| 400 | Bad Request - Invalid request data |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 405 | Method Not Allowed - HTTP method not supported |
| 500 | Internal Server Error - Server error |

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider implementing rate limiting based on your requirements.

## Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (default: 1)
- `page_size`: Number of items per page (default: 20, max: 100)

## Filtering and Search

Most list endpoints support filtering and search:

- **Filtering**: Use query parameters matching field names
- **Search**: Use the `search` parameter for full-text search
- **Ordering**: Use the `ordering` parameter (prefix with `-` for descending)

Example:
```
GET /api/v1/components/?component_type=service&is_active=true&search=payment&ordering=-created_at
```

## Examples

### Complete Impact Analysis Workflow

1. **Get available flows:**
```bash
curl -X GET "http://localhost:8000/api/v1/flows/"
```

2. **Get components in a flow:**
```bash
curl -X GET "http://localhost:8000/api/v1/flows/{flow_id}/components/"
```

3. **Run impact analysis:**
```bash
curl -X POST "http://localhost:8000/api/v1/impact-analyses/" \
  -H "Content-Type: application/json" \
  -d '{
    "flow": "flow-uuid",
    "affected_component": "component-uuid",
    "analysis_type": "downstream",
    "max_depth": "2"
  }'
```

4. **Get analysis results:**
```bash
curl -X GET "http://localhost:8000/api/v1/impact-analyses/{analysis_id}/"
```

### Bulk Operations

For bulk operations, you can use the batch endpoints (if implemented) or make multiple API calls with proper error handling.

## SDK and Client Libraries

Currently, no official SDK is available. You can use any HTTP client library in your preferred programming language.

### Python Example
```python
import requests

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
session = requests.Session()

# Login (if using session auth)
login_data = {"username": "admin", "password": "password"}
session.post("http://localhost:8000/accounts/login/", data=login_data)

# Run impact analysis
analysis_data = {
    "flow": "flow-uuid",
    "affected_component": "component-uuid",
    "analysis_type": "downstream",
    "max_depth": "2"
}

response = session.post(f"{BASE_URL}/impact-analyses/", json=analysis_data)
analysis_result = response.json()
print(f"Analysis ID: {analysis_result['id']}")
print(f"Affected components: {len(analysis_result['affected_components'])}")
```

### JavaScript Example
```javascript
// Configuration
const BASE_URL = 'http://localhost:8000/api/v1';

// Run impact analysis
async function runImpactAnalysis(flowId, componentId) {
  const response = await fetch(`${BASE_URL}/impact-analyses/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(), // Get CSRF token from cookie
    },
    credentials: 'include', // Include session cookies
    body: JSON.stringify({
      flow: flowId,
      affected_component: componentId,
      analysis_type: 'downstream',
      max_depth: '2'
    })
  });
  
  const result = await response.json();
  return result;
}
```

## Support

For API support:
- Check the [GitHub Issues](https://github.com/yourusername/impact-analysis-system/issues)
- Review the [Contributing Guidelines](../CONTRIBUTING.md)
- Contact the development team

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for API changes and version history.

