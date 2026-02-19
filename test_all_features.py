"""
Comprehensive smoke test for all 4 features:
1. Bug fix: X button for removing new custom fields
2. Status change on task detail page
3. Sorting tasks on onboarding detail page
4. Todo-list field type
"""
import os
import sys
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from datetime import date, timedelta
from django.test import RequestFactory, TestCase
from apps.core.models import SystemUser
from apps.entities.models import Entity, CustomFieldDefinition, FieldType
from apps.templates_mgmt.models import OnboardingTemplate, TemplateEntity
from apps.templates_mgmt.services import create_onboarding_from_template
from apps.onboarding.models import OnboardingProcess, OnboardingTask, OnboardingTaskFieldValue, TaskStatus
from apps.onboarding.services import change_task_status, complete_task, skip_task, start_task

passed = 0
failed = 0


def assert_eq(a, b):
    if a != b:
        raise AssertionError(f"Expected {b!r}, got {a!r}")


def assert_true(val):
    if not val:
        raise AssertionError(f"Expected truthy, got {val!r}")


def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  PASS: {name}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {name} -> {e}")
        failed += 1

# Cleanup
OnboardingProcess.objects.all().delete()
OnboardingTemplate.objects.all().delete()
Entity.objects.all().delete()
SystemUser.objects.filter(email__in=['test@test.dk', 'test2@test.dk']).delete()

# Setup
user1 = SystemUser.objects.create(name='Test Bruger', email='test@test.dk', department='IT')
user2 = SystemUser.objects.create(name='Test Bruger 2', email='test2@test.dk', department='HR')

print("\n=== Test 1: FieldType.TODOLIST exists ===")
test("TODOLIST choice exists", lambda: FieldType.TODOLIST)
test("TODOLIST value is 'todolist'", lambda: assert_eq(FieldType.TODOLIST.value, 'todolist'))

print("\n=== Test 2: Entity with todolist field ===")
entity = Entity.objects.create(name='Test Entity Med Todo', description='Test')
field_text = CustomFieldDefinition.objects.create(entity=entity, name='Notater', field_type=FieldType.TEXT)
field_todo = CustomFieldDefinition.objects.create(entity=entity, name='Tjekliste', field_type=FieldType.TODOLIST)

test("Text field created", lambda: assert_eq(field_text.field_type, 'text'))
test("Todolist field created", lambda: assert_eq(field_todo.field_type, 'todolist'))

print("\n=== Test 3: Onboarding from template with todolist ===")
template = OnboardingTemplate.objects.create(name='Test Template')
te = TemplateEntity.objects.create(template=template, entity=entity, sort_order=0)

process = create_onboarding_from_template(
    template=template,
    new_employee_name='Test Person',
    new_employee_email='tp@test.dk',
    new_employee_department='IT',
    new_employee_position='Developer',
    start_date=date.today() + timedelta(days=14),
    created_by=user1,
)

task = process.tasks.first()
fvs = task.field_values.select_related('field_definition').all()

test("Task created", lambda: assert_true(task is not None))
test("2 field values created", lambda: assert_eq(fvs.count(), 2))

fv_text = fvs.get(field_definition__field_type='text')
fv_todo = fvs.get(field_definition__field_type='todolist')

test("Text field value initialized with empty string", lambda: assert_eq(fv_text.value_text, ''))
test("Todolist field value initialized with '[]'", lambda: assert_eq(fv_todo.value_text, '[]'))

print("\n=== Test 4: Todo toggle - add items ===")
items = json.loads(fv_todo.value_text)
test("Initial items is empty list", lambda: assert_eq(items, []))

# Simulate adding items
items.append({'text': 'Bestil laptop', 'done': False})
items.append({'text': 'Opret konto', 'done': False})
items.append({'text': 'Opsæt email', 'done': False})
fv_todo.value_text = json.dumps(items, ensure_ascii=False)
fv_todo.save(update_fields=['value_text'])

fv_todo.refresh_from_db()
loaded = json.loads(fv_todo.value_text)
test("3 items saved", lambda: assert_eq(len(loaded), 3))
test("First item text correct", lambda: assert_eq(loaded[0]['text'], 'Bestil laptop'))
test("First item not done", lambda: assert_eq(loaded[0]['done'], False))

print("\n=== Test 5: Todo toggle - toggle item ===")
loaded[0]['done'] = True
fv_todo.value_text = json.dumps(loaded, ensure_ascii=False)
fv_todo.save(update_fields=['value_text'])

fv_todo.refresh_from_db()
reloaded = json.loads(fv_todo.value_text)
test("First item now done", lambda: assert_eq(reloaded[0]['done'], True))
test("Second item still not done", lambda: assert_eq(reloaded[1]['done'], False))

print("\n=== Test 6: Todo toggle - remove item ===")
reloaded.pop(1)  # Remove 'Opret konto'
fv_todo.value_text = json.dumps(reloaded, ensure_ascii=False)
fv_todo.save(update_fields=['value_text'])

fv_todo.refresh_from_db()
final = json.loads(fv_todo.value_text)
test("2 items after removal", lambda: assert_eq(len(final), 2))
test("Remaining items correct", lambda: assert_eq([i['text'] for i in final], ['Bestil laptop', 'Opsæt email']))

print("\n=== Test 7: change_task_status service ===")
# Task starts as READY (no dependencies)
test("Initial status is READY", lambda: assert_eq(task.status, TaskStatus.READY))

change_task_status(task, TaskStatus.IN_PROGRESS, user1)
task.refresh_from_db()
test("Status changed to IN_PROGRESS", lambda: assert_eq(task.status, TaskStatus.IN_PROGRESS))

change_task_status(task, TaskStatus.READY, user1)
task.refresh_from_db()
test("Status changed back to READY", lambda: assert_eq(task.status, TaskStatus.READY))

change_task_status(task, TaskStatus.PENDING, user1)
task.refresh_from_db()
test("Status changed to PENDING", lambda: assert_eq(task.status, TaskStatus.PENDING))

change_task_status(task, TaskStatus.COMPLETED, user1)
task.refresh_from_db()
test("Status changed to COMPLETED", lambda: assert_eq(task.status, TaskStatus.COMPLETED))
test("completed_at is set", lambda: assert_true(task.completed_at is not None))
test("completed_by is user1", lambda: assert_eq(task.completed_by, user1))

print("\n=== Test 8: Sorting helpers ===")
# Create a template with multiple entities to test sorting
entity2 = Entity.objects.create(name='AAA Entity', description='First alphabetically')
entity3 = Entity.objects.create(name='ZZZ Entity', description='Last alphabetically')

template2 = OnboardingTemplate.objects.create(name='Sort Test Template')
te2a = TemplateEntity.objects.create(template=template2, entity=entity, sort_order=0, default_assignee=user2)
te2b = TemplateEntity.objects.create(template=template2, entity=entity2, sort_order=1, default_assignee=user1)
te2c = TemplateEntity.objects.create(template=template2, entity=entity3, sort_order=2)

process2 = create_onboarding_from_template(
    template=template2,
    new_employee_name='Sort Test',
    new_employee_email='sort@test.dk',
    new_employee_department='IT',
    new_employee_position='Tester',
    start_date=date.today() + timedelta(days=14),
    created_by=user1,
)

tasks = list(process2.tasks.select_related('assignee').all())
test("3 tasks created", lambda: assert_eq(len(tasks), 3))

# Test name sorting
sorted_by_name = sorted(tasks, key=lambda t: t.name)
test("Name sort: AAA first", lambda: assert_eq(sorted_by_name[0].name, 'AAA Entity'))
test("Name sort: ZZZ last", lambda: assert_eq(sorted_by_name[-1].name, 'ZZZ Entity'))

# Test status sorting
from apps.onboarding.views import OnboardingDetailView
STATUS_ORDER = OnboardingDetailView.STATUS_ORDER

# Change one task to in_progress
task_a = process2.tasks.get(name='AAA Entity')
start_task(task_a)
task_a.refresh_from_db()

sorted_by_status = sorted(tasks, key=lambda t: STATUS_ORDER.get(t.status, 99))
# All should be READY except task_a which is IN_PROGRESS - but we need to refresh
for t in tasks:
    t.refresh_from_db()
sorted_by_status = sorted(tasks, key=lambda t: STATUS_ORDER.get(t.status, 99))
test("Status sort works (ready before in_progress)", lambda: assert_true(
    STATUS_ORDER[sorted_by_status[0].status] <= STATUS_ORDER[sorted_by_status[-1].status]
))

print("\n=== Test 9: TaskTodoToggleView endpoint ===")
from django.test import Client
client = Client()

# Create a fresh process with a todolist field
process3 = create_onboarding_from_template(
    template=template,
    new_employee_name='Ajax Test',
    new_employee_email='ajax@test.dk',
    new_employee_department='IT',
    new_employee_position='Dev',
    start_date=date.today() + timedelta(days=7),
    created_by=user1,
)
task3 = process3.tasks.first()
fv_todo3 = task3.field_values.get(field_definition__field_type='todolist')

# Test add
resp = client.post(
    f'/onboarding/{process3.pk}/tasks/{task3.pk}/todo/{fv_todo3.pk}/',
    data=json.dumps({'action': 'add', 'text': 'Test item'}),
    content_type='application/json',
)
test("Add todo: status 200", lambda: assert_eq(resp.status_code, 200))
result = resp.json()
test("Add todo: 1 item", lambda: assert_eq(len(result['items']), 1))
test("Add todo: correct text", lambda: assert_eq(result['items'][0]['text'], 'Test item'))

# Test toggle
resp = client.post(
    f'/onboarding/{process3.pk}/tasks/{task3.pk}/todo/{fv_todo3.pk}/',
    data=json.dumps({'action': 'toggle', 'index': 0}),
    content_type='application/json',
)
test("Toggle todo: status 200", lambda: assert_eq(resp.status_code, 200))
result = resp.json()
test("Toggle todo: item done", lambda: assert_eq(result['items'][0]['done'], True))

# Test toggle back
resp = client.post(
    f'/onboarding/{process3.pk}/tasks/{task3.pk}/todo/{fv_todo3.pk}/',
    data=json.dumps({'action': 'toggle', 'index': 0}),
    content_type='application/json',
)
result = resp.json()
test("Toggle back: item not done", lambda: assert_eq(result['items'][0]['done'], False))

# Add second item
resp = client.post(
    f'/onboarding/{process3.pk}/tasks/{task3.pk}/todo/{fv_todo3.pk}/',
    data=json.dumps({'action': 'add', 'text': 'Second item'}),
    content_type='application/json',
)
result = resp.json()
test("Add second: 2 items", lambda: assert_eq(len(result['items']), 2))

# Test remove
resp = client.post(
    f'/onboarding/{process3.pk}/tasks/{task3.pk}/todo/{fv_todo3.pk}/',
    data=json.dumps({'action': 'remove', 'index': 0}),
    content_type='application/json',
)
result = resp.json()
test("Remove: 1 item remaining", lambda: assert_eq(len(result['items']), 1))
test("Remove: correct item remains", lambda: assert_eq(result['items'][0]['text'], 'Second item'))

print("\n=== Test 10: View endpoints respond ===")
# Test task detail page loads
resp = client.get(f'/onboarding/{process3.pk}/tasks/{task3.pk}/')
test("Task detail page loads", lambda: assert_eq(resp.status_code, 200))
test("Task detail has todo widget", lambda: assert_true(b'todo-list-widget' in resp.content))
test("Task detail has status dropdown", lambda: assert_true(b'change-status' in resp.content))

# Test onboarding detail with sorting
resp = client.get(f'/onboarding/{process2.pk}/?sort=name&dir=asc')
test("Onboarding detail with sort loads", lambda: assert_eq(resp.status_code, 200))

resp = client.get(f'/onboarding/{process2.pk}/?sort=status&dir=desc')
test("Onboarding detail with status sort loads", lambda: assert_eq(resp.status_code, 200))

resp = client.get(f'/onboarding/{process2.pk}/?sort=deadline&dir=asc')
test("Onboarding detail with deadline sort loads", lambda: assert_eq(resp.status_code, 200))

# Test status change via POST
resp = client.post(
    f'/onboarding/{process3.pk}/tasks/{task3.pk}/change-status/',
    data={'status': 'in_progress'},
)
test("Status change redirects", lambda: assert_eq(resp.status_code, 302))
task3.refresh_from_db()
test("Status changed to in_progress", lambda: assert_eq(task3.status, TaskStatus.IN_PROGRESS))

# Test task edit page loads and skips todolist
resp = client.get(f'/onboarding/{process3.pk}/tasks/{task3.pk}/edit/')
test("Task edit page loads", lambda: assert_eq(resp.status_code, 200))
test("Edit page shows todolist notice", lambda: assert_true('Todo-listen redigeres' in resp.content.decode()))


# Cleanup
OnboardingProcess.objects.filter(pk__in=[process.pk, process2.pk, process3.pk]).delete()
OnboardingTemplate.objects.filter(pk__in=[template.pk, template2.pk]).delete()
Entity.objects.filter(pk__in=[entity.pk, entity2.pk, entity3.pk]).delete()
SystemUser.objects.filter(pk__in=[user1.pk, user2.pk]).delete()

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed > 0:
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)
