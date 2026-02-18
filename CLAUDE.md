# Kentaur Onboarding System

## Overview
Processtyringsværktøj til onboarding af nye medarbejdere hos Kentaur. Holder styr på alle opgaver, afhængigheder, deadlines, ansvarlige og notifikationer.

## Tech Stack
- **Backend:** Python 3 / Django 5.1
- **Database:** SQLite (`db.sqlite3`)
- **Frontend:** Django templates + HTMX 1.9 + Tailwind CSS (CDN) + SortableJS (drag/drop)
- **Auth:** Simpel brugervælger (session-baseret, ingen login) — Azure AD-klar struktur
- **Notifikationer:** In-app + email (console backend i dev)

## Project Structure
```
Onboarding_System/
├── config/              # Django project configuration (settings, urls, wsgi)
├── apps/
│   ├── core/            # SystemUser model, dashboard, user switching, user admin, context processors
│   ├── entities/        # Entity definitions with custom fields (text/number/checkbox, dynamic add/remove)
│   ├── templates_mgmt/  # Onboarding templates with dependencies and notification rules
│   ├── onboarding/      # Live onboarding processes, task management, completion workflow
│   └── notifications/   # In-app + email notification system
├── templates/           # Django templates organized by app
├── static/              # CSS (main.css) and JS (app.js)
└── manage.py
```

## Key Architectural Patterns

### Template → Instance Pattern
- `OnboardingTemplate` (blueprint) → `OnboardingProcess` (runtime instance)
- `TemplateEntity` (design-time) → `OnboardingTask` (runtime with real deadlines)
- Instantiation creates a snapshot — template changes don't affect existing onboardings

### Dependency System (DAG)
- Dependencies are a Directed Acyclic Graph within a template/onboarding
- Cycle detection via DFS in `apps/templates_mgmt/services.py`
- Cascading status updates: completing a task promotes dependents from PENDING → READY

### Service Layer
- Business logic in `services.py` files, views are thin
- `apps/templates_mgmt/services.py`: `create_onboarding_from_template()`, cycle validation
- `apps/onboarding/services.py`: `complete_task()`, `skip_task()`, status cascading
- `apps/notifications/services.py`: `send_notification()`, centralized dispatch

### Task Status Flow
`PENDING` → `READY` → `IN_PROGRESS` → `COMPLETED` (or `SKIPPED`)

### Dynamic Custom Fields
- Entity forms use JavaScript-driven dynamic formset management (add/remove rows)
- Django `inlineformset_factory` with `extra=0`; new rows added via JS cloning
- Existing fields: soft-delete via Django's DELETE checkbox with undo support
- New unsaved fields: immediate DOM removal

### Drag/Drop Reorder (Templates)
- SortableJS handles drag/drop of entities within a template
- `ReorderEntitiesView` accepts JSON POST with ordered entity IDs
- Updates `sort_order` field on `TemplateEntity` records

### User Administration
- Full CRUD for `SystemUser` at `/users/` (list, create, detail, edit, toggle active)
- Azure AD-ready: `auth_method` field (local/azure_ad) and `azure_ad_object_id`
- Search and active/inactive filtering on user list

## Common Commands
```bash
pip install -r requirements.txt        # Install dependencies
python manage.py migrate               # Run migrations
python manage.py seed_data             # Populate demo data (5 users, 12 entities, 2 templates)
python manage.py runserver             # Start dev server at http://127.0.0.1:8000
python manage.py check_overdue         # Send notifications for overdue tasks
python manage.py createsuperuser       # Create admin user for /admin/
```

## Data Models (key relationships)
- `SystemUser` — simple user with Azure AD-ready fields (name, email, department, title, phone, auth_method, azure_ad_object_id). Selected via dropdown, managed via `/users/`
- `Entity` → has many `CustomFieldDefinition` (text/number/checkbox fields, dynamically managed in forms)
- `OnboardingTemplate` → has many `TemplateEntity` (with dependencies M2M, notification rules)
- `OnboardingProcess` → has many `OnboardingTask` (with dependencies M2M, field values, notification rules)
- `OnboardingTaskFieldValue` — EAV with typed columns (value_text, value_number, value_checkbox)
- `Notification` — in-app notifications linked to tasks/onboardings

## Code Conventions
- Language: Danish for UI text and model verbose names. English for code (variable names, function names, comments).
- Views: Class-based views using `django.views.View`
- Forms: Django forms with Tailwind CSS classes applied in widgets
- Templates: HTMX for interactive updates (task completion, notification polling), SortableJS for drag/drop
- JavaScript: Vanilla JS for dynamic formsets and drag/drop; no build step
- URLs: namespaced per app (`core:`, `entities:`, `templates_mgmt:`, `onboarding:`, `notifications:`)
- Admin: All models registered with Django admin at `/admin/`

## Configuration
- Settings in `config/settings.py`
- Language: Danish (`LANGUAGE_CODE = 'da'`)
- Timezone: `Europe/Copenhagen`
- Email: Console backend in dev (prints to stdout). Configure SMTP in settings for production.
- Current user stored in `request.session['current_user_id']`
- Context processor `apps.core.context_processors.current_user` provides `current_user` and `all_users` to all templates
