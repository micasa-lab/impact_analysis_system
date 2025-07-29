# Impact Analysis System

A comprehensive Django-based system for analyzing component dependencies and assessing change impacts in complex software architectures. This system provides advanced transitive dependency analysis, interactive visualizations, and detailed impact assessments to help teams make informed decisions about system changes.

## 🚀 Features

### Core Functionality
- **Component Management**: Define and manage system components with detailed metadata
- **Flow Designer**: Visual flow designer for creating and managing component relationships
- **Transitive Dependency Analysis**: Advanced analysis showing both direct and indirect impacts
- **Interactive Visualizations**: D3.js-powered network graphs with force simulation
- **Impact Assessment**: Comprehensive severity analysis with business impact scoring
- **Runbook Management**: Operational procedures and step-by-step guides
- **YAML/JSON Import**: Import system architectures from external formats

### Advanced Analysis Features
- **Multi-directional Analysis**: Downstream, upstream, and bidirectional impact analysis
- **Depth Control**: Configurable analysis depth (1-3 levels or unlimited)
- **Severity Calculation**: Dynamic severity scoring based on connection types and component criticality
- **Impact Paths**: Visual representation of dependency chains
- **Business Impact Scoring**: Quantitative assessment of change impacts
- **Component Grouping**: Visual distinction between direct and indirect impacts

### User Interface
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Real-time Updates**: Dynamic component loading and analysis results
- **Interactive Elements**: Clickable components, expandable sections, and detailed tooltips
- **Export Capabilities**: Export analysis results and flow diagrams
- **Authentication System**: Secure user management and session handling

## 📋 Prerequisites

- Python 3.8+
- Django 4.2+
- PostgreSQL (recommended) or SQLite for development
- Node.js (for frontend dependencies)
- Git

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/impact-analysis-system.git
cd impact-analysis-system
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

```bash
# Create and run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Load Sample Data (Optional)

```bash
python manage.py loaddata sample_data.json
```

### 6. Run Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## 🏗️ System Architecture

### Backend Components

```
impact_analysis_system/
├── core/                   # Core models and business logic
│   ├── models.py          # Component, Flow, Connection, ImpactAnalysis models
│   └── admin.py           # Django admin configuration
├── api/                   # REST API endpoints
│   ├── views.py           # API viewsets with analysis algorithms
│   ├── serializers.py     # Data serialization
│   └── urls.py            # API routing
├── frontend/              # Web interface
│   ├── views.py           # Frontend views
│   ├── urls.py            # Frontend routing
│   └── templates/         # HTML templates
└── templates/             # Shared templates
    ├── base.html          # Base template
    ├── frontend/          # Frontend-specific templates
    └── registration/      # Authentication templates
```

### Key Models

#### Component
- **Purpose**: Represents individual system components
- **Fields**: Name, type, business function, description, metadata
- **Types**: Database, Service, API, Frontend, Middleware, External Service

#### Flow
- **Purpose**: Represents system workflows or processes
- **Fields**: Name, version, description, metadata
- **Relationships**: Contains multiple components and their connections

#### Connection
- **Purpose**: Defines relationships between components
- **Types**: API Call, Data Flow, Message Queue, Database Connection, Event Trigger
- **Metadata**: Source, target, connection type, custom properties

#### ImpactAnalysis
- **Purpose**: Stores analysis results and recommendations
- **Features**: Severity assessment, affected components, analysis metadata
- **Analysis Types**: Downstream, Upstream, Bidirectional

## 🔍 Usage Guide

### Creating Components

1. Navigate to **Components** section
2. Click **"Add Component"**
3. Fill in component details:
   - Name and description
   - Component type (Database, Service, API, etc.)
   - Business function
   - Technical metadata

### Designing Flows

1. Go to **Flows** section
2. Create a new flow or edit existing one
3. Use the **Flow Designer** to:
   - Add components to the flow
   - Create connections between components
   - Position components visually
   - Define connection types and metadata

### Running Impact Analysis

1. Navigate to **Impact Analysis**
2. Configure analysis parameters:
   - **Select Flow**: Choose the target flow
   - **Target Component**: Select component to analyze
   - **Analysis Type**: Downstream, Upstream, or Bidirectional
   - **Max Depth**: Set analysis depth (1-3 levels or unlimited)
   - **Severity**: Set minimum severity threshold

3. Click **"Run Analysis"** to execute

### Understanding Results

#### Impact Summary
- **Total Components Affected**: Count of all impacted components
- **Direct vs Indirect**: Breakdown of impact types
- **Severity Distribution**: Components grouped by impact severity

#### Affected Components
- **Direct Impacts**: Components immediately connected to the target
- **Indirect Impacts**: Components affected through dependency chains
- **Impact Paths**: Visual representation of dependency flows
- **Severity Indicators**: Color-coded severity levels

#### Visualization
- **Network Graph**: Interactive D3.js visualization
- **Force Simulation**: Dynamic positioning based on relationships
- **Visual Distinction**: Different styles for direct vs indirect impacts
- **Interactive Elements**: Hover tooltips and clickable components

## 🔧 API Reference

### Core Endpoints

#### Components
```
GET    /api/v1/components/           # List all components
POST   /api/v1/components/           # Create new component
GET    /api/v1/components/{id}/      # Get component details
PUT    /api/v1/components/{id}/      # Update component
DELETE /api/v1/components/{id}/      # Delete component
```

#### Flows
```
GET    /api/v1/flows/                # List all flows
POST   /api/v1/flows/                # Create new flow
GET    /api/v1/flows/{id}/           # Get flow details
GET    /api/v1/flows/{id}/components/ # Get flow components
GET    /api/v1/flows/{id}/connections/ # Get flow connections
```

#### Impact Analysis
```
GET    /api/v1/impact-analyses/      # List analyses
POST   /api/v1/impact-analyses/      # Run new analysis
GET    /api/v1/impact-analyses/{id}/ # Get analysis results
```

### Analysis Request Format

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

### Analysis Response Format

```json
{
  "id": "analysis-uuid",
  "flow": "flow-uuid",
  "flow_name": "PayShield Flow",
  "affected_component": "component-uuid",
  "affected_component_name": "Payment Service",
  "severity": "medium",
  "affected_components": [
    {
      "id": "component-uuid",
      "name": "Validation Engine",
      "type": "service",
      "severity": "high",
      "impact_type": "direct",
      "depth": 1,
      "path": ["Payment Service", "Validation Engine"],
      "transitive_reason": "Directly connected to the target component"
    }
  ],
  "severity_distribution": {
    "total": {"low": 2, "medium": 1, "high": 1, "critical": 0},
    "direct": {"low": 0, "medium": 1, "high": 1, "critical": 0},
    "indirect": {"low": 2, "medium": 0, "high": 0, "critical": 0},
    "summary": {
      "total_affected": 4,
      "direct_affected": 2,
      "indirect_affected": 2,
      "max_depth": 2
    }
  }
}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test core
python manage.py test api
python manage.py test frontend

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Test Structure

```
tests/
├── test_models.py         # Model tests
├── test_views.py          # View tests
├── test_api.py            # API tests
├── test_analysis.py       # Impact analysis algorithm tests
└── fixtures/              # Test data fixtures
```

## 🚀 Deployment

### Production Setup

1. **Environment Variables**
```bash
export DEBUG=False
export SECRET_KEY='your-secret-key'
export DATABASE_URL='postgresql://user:pass@localhost/dbname'
export ALLOWED_HOSTS='yourdomain.com'
```

2. **Database Configuration**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'impact_analysis',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

3. **Static Files**
```bash
python manage.py collectstatic
```

4. **Web Server Configuration**
- Use Gunicorn or uWSGI for application server
- Configure Nginx for static files and reverse proxy
- Set up SSL certificates for HTTPS

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "impact_analysis_system.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `python manage.py test`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use Black for code formatting: `black .`
- Use isort for import sorting: `isort .`
- Add type hints where appropriate
- Write comprehensive docstrings

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: feat, fix, docs, style, refactor, test, chore

## 📊 Performance Considerations

### Database Optimization
- Use database indexes on frequently queried fields
- Implement connection pooling for high-traffic scenarios
- Consider read replicas for analysis-heavy workloads

### Caching Strategy
- Redis for session storage and temporary data
- Cache analysis results for frequently accessed flows
- Implement cache invalidation on component updates

### Frontend Optimization
- Lazy loading for large component lists
- Pagination for analysis history
- Debounced search and filtering

## 🔒 Security

### Authentication & Authorization
- Django's built-in authentication system
- Role-based access control (RBAC)
- API token authentication for external integrations

### Data Protection
- Input validation and sanitization
- SQL injection prevention through ORM
- XSS protection with Django's template system
- CSRF protection for all forms

### Security Headers
```python
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
```

## 📈 Monitoring & Logging

### Application Monitoring
- Django's built-in logging framework
- Custom metrics for analysis performance
- Error tracking with Sentry (optional)

### Performance Metrics
- Analysis execution time
- Database query performance
- API response times
- User activity patterns

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database status
python manage.py dbshell

# Reset migrations (development only)
python manage.py migrate --fake-initial
```

#### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --clear

# Check STATIC_URL and STATIC_ROOT settings
```

#### Analysis Performance Issues
- Check database indexes on Connection and FlowComponent tables
- Consider reducing max_depth for large flows
- Monitor memory usage during complex analyses

### Debug Mode

Enable debug logging:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'impact_analysis': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## 📚 Additional Resources

### Documentation
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [D3.js Documentation](https://d3js.org/)

### Related Projects
- [System Architecture Tools](https://github.com/topics/system-architecture)
- [Dependency Analysis Tools](https://github.com/topics/dependency-analysis)
- [Impact Assessment Frameworks](https://github.com/topics/impact-analysis)



## 👥 Authors

- Chiraag Bhatia

## 🙏 Acknowledgments

- Django community for the excellent web framework
- D3.js team for powerful visualization capabilities
- Bootstrap team for responsive UI components


## 📞 Support

For support, email absurdcoders@gmail.com or create an issue in the GitHub repository.

---

**Built with ❤️ using Django, D3.js, and modern web technologies**

