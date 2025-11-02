# MCP Django Server Roadmap

**Version:** Draft 1.0
**Last Updated:** 2025-11-02
**Current Version:** v0.12.0

## Vision

Build the premier MCP server for Django development, achieving feature parity with Laravel Boost while leveraging Django-specific strengths.

---

## Phase 1: Laravel Boost Parity (Critical Gaps)
**Goal:** Match core Laravel Boost functionality
**Target:** v0.13.0 - v0.15.0

### 1.1 Database Toolset (v0.13.0) 🎯 HIGH PRIORITY
**Motivation:** Laravel Boost's most powerful features are database-related

#### Tools
- `database_query` - Execute read-only SQL queries against database
  - Support for all Django-configured databases
  - Query result formatting (table, JSON, CSV)
  - Query explain/analyze support
  - Safety: Read-only by default, explicit flag for writes
  - Parameter binding support (prevent SQL injection)

- `get_database_schema` - Full database schema inspection
  - Tables, columns, types, constraints
  - Indexes and their definitions
  - Foreign key relationships
  - View definitions
  - Database-specific features (PostgreSQL schemas, etc.)

- `list_database_connections` - Inspect database configuration
  - All configured databases from settings.DATABASES
  - Connection status (can connect?)
  - Database engine, name, host, port
  - Hide sensitive credentials

#### Resources
- `django://database/{alias}/schema` - Schema for specific database
- `django://database/{alias}/tables` - List tables
- `django://database/{alias}/table/{table_name}` - Table details
- `django://databases` - All database connections

**Implementation Notes:**
- Use Django's connection.introspection module
- Leverage Django's cursor context managers
- Consider django-read-only integration for safety
- Support multiple database backends (PostgreSQL, MySQL, SQLite, Oracle)

**Security Considerations:**
- Default to read-only queries
- Sanitize credential display
- Add optional `allow_writes` configuration flag (default: false)
- Log all database operations with request/client tracking

---

### 1.2 Logging Toolset (v0.14.0)
**Motivation:** Critical for debugging and monitoring

#### Tools
- `read_log_entries` - Parse Django log files
  - Read last N entries
  - Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Filter by logger name
  - Time range filtering
  - Structured output (timestamp, level, logger, message, traceback)

- `get_last_error` - Quick access to most recent error
  - Parse last ERROR/CRITICAL from logs
  - Include full traceback
  - Context (request info if available)

- `search_logs` - Search logs by pattern
  - Regex support
  - Context lines (before/after match)
  - Multiple log file support

#### Resources
- `django://logs/latest?level=ERROR&limit=10` - Recent logs with filtering
- `django://logs/error/last` - Last error

**Implementation Notes:**
- Support Django's default logging configuration
- Handle rotated log files
- Parse Django's standard log format
- Consider structured logging (JSON logs) support
- Handle large log files efficiently (streaming/pagination)

**Configuration:**
- Allow specifying log file paths via CLI args
- Auto-detect common log locations
- Support multiple log files

---

### 1.3 System Introspection (v0.15.0)
**Motivation:** Complete the introspection picture

#### Tools
- `list_management_commands` - Django management commands
  - All available commands (built-in + custom)
  - Command help text
  - Arguments and options
  - App source (which app provides the command)

- `list_settings_keys` - All available settings
  - All settings keys currently defined
  - Values (with sensitive data masked)
  - Source (Django default, project settings, env override)
  - Documentation links

- `list_env_vars` - Environment variables
  - All env vars used in settings
  - Current values (with sensitive data masked)
  - Whether they're set or using defaults

- `reverse_url` - Django's reverse() as a tool
  - Convert route name to absolute URL
  - Support for URL parameters
  - Support for different URL configs
  - Query parameter building

#### Resources
- `django://management-commands` - All management commands
- `django://management-command/{name}` - Specific command details
- `django://settings/all` - All settings
- `django://env` - Environment variables

**Implementation Notes:**
- Use `django.core.management.get_commands()`
- Settings introspection via `django.conf.settings`
- Env var detection from settings file AST parsing
- URL reversal via `django.urls.reverse()`

---

## Phase 2: Django-Specific Power Features
**Goal:** Leverage Django's unique strengths
**Target:** v0.16.0 - v0.19.0

### 2.1 Migration Toolset (v0.16.0) 🎯 HIGH VALUE
**Motivation:** Django's migration system is more complex than Laravel's

#### Tools
- `list_migrations` - Migration status
  - All migrations (applied/unapplied)
  - Migration dependencies
  - Filter by app
  - Detect conflicts

- `show_migration` - Migration details
  - Operations in migration
  - Dependencies
  - SQL preview (sqlmigrate)
  - Affected models/tables

- `detect_migration_issues` - Analyze migrations
  - Unapplied migrations
  - Conflicting migrations
  - Missing migrations (makemigrations --dry-run)
  - Migration ordering issues

#### Resources
- `django://migrations` - All migrations with status
- `django://migrations/{app_label}` - App-specific migrations
- `django://migration/{app_label}/{migration_name}` - Migration details

**Implementation Notes:**
- Use `django.db.migrations.loader.MigrationLoader`
- Call management commands: showmigrations, sqlmigrate
- Parse migration files for operation details
- Detect conflicts using migration graph

---

### 2.2 Testing Toolset (v0.17.0)
**Motivation:** Essential for TDD and quality assurance

#### Tools
- `run_tests` - Execute Django tests
  - Run specific tests or test suites
  - Filter by app, class, method
  - Output verbosity control
  - Generate coverage report
  - JUnit XML output support

- `list_tests` - Discover tests
  - All available tests
  - Filter by app
  - Test structure (TestCase > method)

- `analyze_test_coverage` - Coverage reports
  - Overall coverage percentage
  - Per-app and per-file coverage
  - Uncovered lines
  - Integration with coverage.py

#### Resources
- `django://tests` - All tests
- `django://tests/{app_label}` - App-specific tests
- `django://coverage` - Coverage report

**Implementation Notes:**
- Use Django's DiscoverRunner
- Integrate with coverage.py
- Capture test output and failures
- Support for pytest-django as alternative runner

---

### 2.3 Admin Toolset (v0.18.0)
**Motivation:** Django admin is a killer feature with no Laravel equivalent

#### Tools
- `list_admin_models` - Models registered in admin
  - ModelAdmin configuration
  - List display fields
  - Filters, search fields
  - Inlines
  - Custom actions

- `get_admin_config` - ModelAdmin introspection
  - All configuration options
  - Permissions
  - Custom views/URLs

- `list_admin_actions` - Available admin actions
  - Built-in and custom actions
  - Action permissions

#### Resources
- `django://admin/models` - All admin-registered models
- `django://admin/model/{app_label}/{model_name}` - ModelAdmin config

**Implementation Notes:**
- Introspect django.contrib.admin.site
- Parse ModelAdmin classes
- Extract configuration via inspection
- Document admin URLs and permissions

---

### 2.4 System Checks Toolset (v0.19.0)
**Motivation:** Django's check framework is powerful and underutilized

#### Tools
- `run_checks` - Execute Django system checks
  - All checks or specific tags
  - Filter by level (error, warning, info)
  - Deploy checks (--deploy flag)
  - Security checks

- `list_available_checks` - All registered checks
  - Check IDs and descriptions
  - Tags (security, database, models, etc.)

#### Resources
- `django://checks/results` - Recent check results
- `django://checks/available` - All available checks

**Implementation Notes:**
- Use django.core.checks API
- Run check framework programmatically
- Format results for LLM consumption
- Include suggestions for fixing issues

---

## Phase 3: Documentation & Developer Experience
**Goal:** Make learning and troubleshooting easier
**Target:** v0.20.0 - v0.21.0

### 3.1 Documentation Integration (v0.20.0)
**Motivation:** Laravel Boost has docs search - we should too

#### Tools
- `search_django_docs` - Query Django documentation
  - Search official Django docs
  - Filter by version
  - Return relevant sections with links

- `search_package_docs` - Third-party package docs
  - Search docs for installed packages
  - DRF, Celery, etc.
  - Return relevant sections

- `explain_concept` - Django concept explainer
  - Query-based explanations
  - Examples from project context
  - Links to relevant docs

**Implementation Notes:**
- Integrate with docs.djangoproject.com API (if available)
- Fallback to web scraping with caching
- Use local docs if available
- Consider ReadTheDocs API for packages

---

### 3.2 Code Generation Toolset (v0.21.0)
**Motivation:** Accelerate boilerplate creation

#### Tools
- `generate_model` - Create model boilerplate
  - From specification
  - Common field patterns
  - Relationships
  - Meta options

- `generate_view` - Create view boilerplate
  - Function-based or class-based
  - CRUD operations
  - Form handling

- `generate_serializer` - DRF serializer
  - From model
  - Field selection
  - Nested serializers

- `generate_admin` - Admin configuration
  - From model
  - Common patterns (list_display, filters, search)

- `generate_test` - Test boilerplate
  - From model or view
  - Common test patterns
  - Fixtures

**Implementation Notes:**
- Template-based generation
- Use Django's code generation patterns
- Support for customization
- Integration with project structure

---

## Phase 4: Advanced Features & Integrations
**Goal:** Power user features
**Target:** v0.22.0+

### 4.1 Performance Analysis (v0.22.0)
- Query performance analysis (N+1 detection)
- Template rendering performance
- Cache analysis
- Integration with Django Debug Toolbar

### 4.2 Celery Integration (v0.23.0)
- List registered tasks
- Task execution with parameter validation
- Queue introspection
- Task result inspection
- Worker status

### 4.3 Cache Toolset (v0.24.0)
- Cache backend introspection
- Cache statistics
- Cache key inspection
- Cache invalidation tools

### 4.4 Static Files & Media (v0.25.0)
- Static files collection analysis
- Missing static files detection
- Media file management
- Whitenoise/CDN configuration analysis

### 4.5 Security Auditing (v0.26.0)
- Security middleware checks
- CSRF configuration validation
- XSS vulnerability scanning
- Dependency vulnerability checks
- Secrets detection in code

### 4.6 Deployment Readiness (v0.27.0)
- Production settings validation
- Environment comparison
- Checklist generation
- Docker configuration analysis

---

## Feature Prioritization Matrix

### Must Have (Feature Parity)
1. ✅ Database Query (v0.13.0)
2. ✅ Database Schema (v0.13.0)
3. ✅ Logging (v0.14.0)
4. ✅ Management Commands (v0.15.0)
5. ✅ Settings Keys (v0.15.0)
6. ✅ URL Reversal (v0.15.0)

### High Value (Django-Specific)
1. ✅ Migrations (v0.16.0)
2. ✅ Testing (v0.17.0)
3. ✅ Admin Introspection (v0.18.0)
4. ✅ System Checks (v0.19.0)

### Important (DX Improvements)
1. ✅ Documentation Search (v0.20.0)
2. ✅ Code Generation (v0.21.0)

### Nice to Have (Advanced)
1. ⚪ Performance Analysis (v0.22.0)
2. ⚪ Celery (v0.23.0)
3. ⚪ Cache (v0.24.0)
4. ⚪ Static Files (v0.25.0)
5. ⚪ Security (v0.26.0)
6. ⚪ Deployment (v0.27.0)

---

## Implementation Guidelines

### Architecture Principles
1. **Toolset per domain** - Keep related tools together
2. **Resources for read-only** - Tools for actions
3. **Safety first** - Default to read-only, explicit writes
4. **Stateless preferred** - Maintain v0.12.0 philosophy
5. **Observable** - Log all operations with request/client IDs

### Security Considerations
1. **Credential masking** - Never expose passwords/secrets
2. **Read-only defaults** - Require explicit flags for mutations
3. **SQL injection prevention** - Use parameter binding
4. **Path traversal prevention** - Validate file paths
5. **Audit logging** - Track all sensitive operations

### Testing Requirements
1. **100% coverage** - Maintain current standard
2. **Multi-version testing** - Python 3.10-3.14, Django 4.2-6.0
3. **Integration tests** - Test actual Django projects
4. **Security tests** - Verify security controls

### Documentation Standards
1. **Tool descriptions** - Clear purpose and examples
2. **Security warnings** - Document safety considerations
3. **Configuration options** - All CLI flags documented
4. **Migration guides** - Breaking changes documented

---

## Success Metrics

### Feature Parity Milestone
- ✅ All Laravel Boost core features implemented
- ✅ Django-specific advantages documented
- ✅ Comparison blog post published

### Adoption Metrics
- GitHub stars
- PyPI download trends
- Community contributions
- Issue/PR activity

### Quality Metrics
- 100% test coverage maintained
- Zero critical security issues
- <1% error rate in production use
- Positive user feedback

---

## Community & Feedback

### Contribution Opportunities
- Feature requests via GitHub issues
- Community voting on roadmap priorities
- Beta testing program for new features
- Documentation improvements

### Communication Channels
- GitHub Issues - Bug reports and feature requests
- GitHub Discussions - Community Q&A
- Blog - Release announcements and tutorials
- Twitter/Social - Updates and tips

---

## Open Questions

1. **Database writes:** Should we support write queries? How to make it safe?
   - Option A: Never allow writes (strictest)
   - Option B: Allow with explicit flag + confirmation
   - Option C: Separate tool with warnings

2. **Logging strategy:** How to handle large log files?
   - Streaming vs pagination
   - Memory limits
   - Multiple file handling

3. **Documentation API:** Best approach for docs search?
   - Official API (if exists)
   - Web scraping + caching
   - Local docs bundling
   - Hybrid approach

4. **Code generation:** How opinionated should templates be?
   - Minimal boilerplate
   - Best practices by default
   - Customization support

5. **Celery priority:** High demand or niche?
   - Survey community
   - Check Django package usage stats

---

## Version History

- **v0.12.0** (Current) - Stateless shell, export history, model filtering
- **v0.11.0** - Project introspection toolset
- **v0.10.0** - Consolidated mcp-django-shell
- **v0.9.0** - Shell-only functionality

---

## Next Steps

1. **Community Feedback** - Share roadmap for input
2. **v0.13.0 Planning** - Detailed database toolset design
3. **Security Review** - Database query safety architecture
4. **Documentation** - Update contributing guide with roadmap
5. **Milestones** - Create GitHub milestones for each version

---

**Status:** Draft - Seeking feedback
**Contributors:** Add your name after reviewing
**Last Review:** 2025-11-02
