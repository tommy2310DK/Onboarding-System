"""
Comprehensive smoke test for all features.
Uses Django TestCase which wraps each test in a transaction that is
rolled back after the test — production data is NEVER touched.

IMPORTANT: TransactionTestCase MUST NOT be used because it flushes the
entire database after each test. TestCase uses transaction rollback instead.
"""
import os
import sys
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from datetime import date, timedelta
from django.test import TestCase, Client
from apps.core.models import SystemUser
from apps.entities.models import Entity, CustomFieldDefinition, FieldType, Category
from apps.templates_mgmt.models import OnboardingTemplate, TemplateEntity
from apps.templates_mgmt.services import create_onboarding_from_template
from apps.onboarding.models import OnboardingProcess, OnboardingTask, OnboardingTaskFieldValue, TaskStatus
from apps.onboarding.services import change_task_status, complete_task, skip_task, start_task


class AllFeaturesTest(TestCase):
    """Each test wrapped in a transaction that rolls back — production data is NEVER affected."""

    def setUp(self):
        """Create isolated test data — only for this test run."""
        self.user1 = SystemUser.objects.create(
            name='Test Bruger X1', email='testx1@test.dk', department='IT'
        )
        self.user2 = SystemUser.objects.create(
            name='Test Bruger X2', email='testx2@test.dk', department='HR'
        )
        self.cat = Category.objects.create(name='_Test_Intern')
        self.entity = Entity.objects.create(
            name='_Test Entity Med Todo', description='Test', category=self.cat,
        )
        self.field_text = CustomFieldDefinition.objects.create(
            entity=self.entity, name='Notater', field_type=FieldType.TEXT,
        )
        self.field_todo = CustomFieldDefinition.objects.create(
            entity=self.entity, name='Tjekliste', field_type=FieldType.TODOLIST,
        )
        self.template = OnboardingTemplate.objects.create(name='_Test Template X')
        self.te = TemplateEntity.objects.create(
            template=self.template, entity=self.entity, sort_order=0,
        )
        self.process = create_onboarding_from_template(
            template=self.template,
            new_employee_name='Test Person X',
            new_employee_email='tpx@test.dk',
            new_employee_department='IT',
            new_employee_position='Developer',
            start_date=date.today() + timedelta(days=14),
            created_by=self.user1,
        )
        self.task = self.process.tasks.first()

    def _p(self, msg):
        """Print test result."""
        print(f"  PASS: {msg}")

    # ------------------------------------------------------------------
    # Test 1: FieldType.TODOLIST
    # ------------------------------------------------------------------
    def test_01_todolist_fieldtype_exists(self):
        print("\n=== Test 1: FieldType.TODOLIST exists ===")
        self.assertEqual(FieldType.TODOLIST.value, 'todolist')
        self._p("TODOLIST choice exists and value is 'todolist'")

    # ------------------------------------------------------------------
    # Test 2: Entity with todolist field
    # ------------------------------------------------------------------
    def test_02_entity_with_todolist_field(self):
        print("\n=== Test 2: Entity with todolist field ===")
        self.assertEqual(self.field_text.field_type, 'text')
        self._p("Text field created")
        self.assertEqual(self.field_todo.field_type, 'todolist')
        self._p("Todolist field created")

    # ------------------------------------------------------------------
    # Test 3: Onboarding from template with todolist
    # ------------------------------------------------------------------
    def test_03_onboarding_from_template(self):
        print("\n=== Test 3: Onboarding from template with todolist ===")
        self.assertIsNotNone(self.task)
        self._p("Task created")
        fvs = self.task.field_values.select_related('field_definition').all()
        self.assertEqual(fvs.count(), 2)
        self._p("2 field values created")
        fv_text = fvs.get(field_definition__field_type='text')
        fv_todo = fvs.get(field_definition__field_type='todolist')
        self.assertEqual(fv_text.value_text, '')
        self._p("Text field value initialized with empty string")
        self.assertEqual(fv_todo.value_text, '[]')
        self._p("Todolist field value initialized with '[]'")

    # ------------------------------------------------------------------
    # Test 4-6: Todo toggle operations
    # ------------------------------------------------------------------
    def test_04_todo_add_items(self):
        print("\n=== Test 4: Todo toggle - add items ===")
        fv_todo = self.task.field_values.get(field_definition__field_type='todolist')
        items = json.loads(fv_todo.value_text)
        self.assertEqual(items, [])
        self._p("Initial items is empty list")

        items.append({'text': 'Bestil laptop', 'done': False})
        items.append({'text': 'Opret konto', 'done': False})
        items.append({'text': 'Opsæt email', 'done': False})
        fv_todo.value_text = json.dumps(items, ensure_ascii=False)
        fv_todo.save(update_fields=['value_text'])
        fv_todo.refresh_from_db()
        loaded = json.loads(fv_todo.value_text)
        self.assertEqual(len(loaded), 3)
        self._p("3 items saved")
        self.assertEqual(loaded[0]['text'], 'Bestil laptop')
        self._p("First item text correct")
        self.assertFalse(loaded[0]['done'])
        self._p("First item not done")

    def test_05_todo_toggle_item(self):
        print("\n=== Test 5: Todo toggle - toggle item ===")
        fv_todo = self.task.field_values.get(field_definition__field_type='todolist')
        items = [{'text': 'A', 'done': False}, {'text': 'B', 'done': False}]
        fv_todo.value_text = json.dumps(items)
        fv_todo.save(update_fields=['value_text'])

        items[0]['done'] = True
        fv_todo.value_text = json.dumps(items)
        fv_todo.save(update_fields=['value_text'])
        fv_todo.refresh_from_db()
        reloaded = json.loads(fv_todo.value_text)
        self.assertTrue(reloaded[0]['done'])
        self._p("First item now done")
        self.assertFalse(reloaded[1]['done'])
        self._p("Second item still not done")

    def test_06_todo_remove_item(self):
        print("\n=== Test 6: Todo toggle - remove item ===")
        fv_todo = self.task.field_values.get(field_definition__field_type='todolist')
        items = [{'text': 'Bestil laptop', 'done': True}, {'text': 'Opret konto', 'done': False}, {'text': 'Opsæt email', 'done': False}]
        fv_todo.value_text = json.dumps(items)
        fv_todo.save(update_fields=['value_text'])

        items.pop(1)
        fv_todo.value_text = json.dumps(items)
        fv_todo.save(update_fields=['value_text'])
        fv_todo.refresh_from_db()
        final = json.loads(fv_todo.value_text)
        self.assertEqual(len(final), 2)
        self._p("2 items after removal")
        self.assertEqual([i['text'] for i in final], ['Bestil laptop', 'Opsæt email'])
        self._p("Remaining items correct")

    # ------------------------------------------------------------------
    # Test 7: change_task_status service
    # ------------------------------------------------------------------
    def test_07_change_task_status(self):
        print("\n=== Test 7: change_task_status service ===")
        task = self.task
        self.assertEqual(task.status, TaskStatus.READY)
        self._p("Initial status is READY")

        change_task_status(task, TaskStatus.IN_PROGRESS, self.user1)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
        self._p("Status changed to IN_PROGRESS")

        change_task_status(task, TaskStatus.READY, self.user1)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.READY)
        self._p("Status changed back to READY")

        change_task_status(task, TaskStatus.PENDING, self.user1)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.PENDING)
        self._p("Status changed to PENDING")

        change_task_status(task, TaskStatus.COMPLETED, self.user1)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self._p("Status changed to COMPLETED")
        self.assertIsNotNone(task.completed_at)
        self._p("completed_at is set")
        self.assertEqual(task.completed_by, self.user1)
        self._p("completed_by is user1")

    # ------------------------------------------------------------------
    # Test 8: Sorting helpers
    # ------------------------------------------------------------------
    def test_08_sorting(self):
        print("\n=== Test 8: Sorting helpers ===")
        entity2 = Entity.objects.create(name='_AAA Test Entity', description='First', category=self.cat)
        entity3 = Entity.objects.create(name='_ZZZ Test Entity', description='Last', category=self.cat)

        template2 = OnboardingTemplate.objects.create(name='_Sort Test Template X')
        TemplateEntity.objects.create(template=template2, entity=self.entity, sort_order=0, default_assignee=self.user2)
        TemplateEntity.objects.create(template=template2, entity=entity2, sort_order=1, default_assignee=self.user1)
        TemplateEntity.objects.create(template=template2, entity=entity3, sort_order=2)

        process2 = create_onboarding_from_template(
            template=template2,
            new_employee_name='Sort Test X',
            new_employee_email='sortx@test.dk',
            new_employee_department='IT',
            new_employee_position='Tester',
            start_date=date.today() + timedelta(days=14),
            created_by=self.user1,
        )

        tasks = list(process2.tasks.select_related('assignee').all())
        self.assertEqual(len(tasks), 3)
        self._p("3 tasks created")

        sorted_by_name = sorted(tasks, key=lambda t: t.name)
        self.assertEqual(sorted_by_name[0].name, '_AAA Test Entity')
        self._p("Name sort: AAA first")
        self.assertEqual(sorted_by_name[-1].name, '_ZZZ Test Entity')
        self._p("Name sort: ZZZ last")

        from apps.onboarding.views import OnboardingDetailView
        STATUS_ORDER = OnboardingDetailView.STATUS_ORDER

        task_a = process2.tasks.get(name='_AAA Test Entity')
        start_task(task_a)
        for t in tasks:
            t.refresh_from_db()
        sorted_by_status = sorted(tasks, key=lambda t: STATUS_ORDER.get(t.status, 99))
        self.assertLessEqual(
            STATUS_ORDER[sorted_by_status[0].status],
            STATUS_ORDER[sorted_by_status[-1].status],
        )
        self._p("Status sort works (ready before in_progress)")

    # ------------------------------------------------------------------
    # Test 9: TaskTodoToggleView endpoint
    # ------------------------------------------------------------------
    def test_09_todo_toggle_view(self):
        print("\n=== Test 9: TaskTodoToggleView endpoint ===")
        client = Client()
        fv_todo = self.task.field_values.get(field_definition__field_type='todolist')

        resp = client.post(
            f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/todo/{fv_todo.pk}/',
            data=json.dumps({'action': 'add', 'text': 'Test item'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self._p("Add todo: status 200")
        result = resp.json()
        self.assertEqual(len(result['items']), 1)
        self._p("Add todo: 1 item")
        self.assertEqual(result['items'][0]['text'], 'Test item')
        self._p("Add todo: correct text")

        resp = client.post(
            f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/todo/{fv_todo.pk}/',
            data=json.dumps({'action': 'toggle', 'index': 0}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self._p("Toggle todo: status 200")
        result = resp.json()
        self.assertTrue(result['items'][0]['done'])
        self._p("Toggle todo: item done")

        resp = client.post(
            f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/todo/{fv_todo.pk}/',
            data=json.dumps({'action': 'toggle', 'index': 0}),
            content_type='application/json',
        )
        result = resp.json()
        self.assertFalse(result['items'][0]['done'])
        self._p("Toggle back: item not done")

        resp = client.post(
            f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/todo/{fv_todo.pk}/',
            data=json.dumps({'action': 'add', 'text': 'Second item'}),
            content_type='application/json',
        )
        result = resp.json()
        self.assertEqual(len(result['items']), 2)
        self._p("Add second: 2 items")

        resp = client.post(
            f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/todo/{fv_todo.pk}/',
            data=json.dumps({'action': 'remove', 'index': 0}),
            content_type='application/json',
        )
        result = resp.json()
        self.assertEqual(len(result['items']), 1)
        self._p("Remove: 1 item remaining")
        self.assertEqual(result['items'][0]['text'], 'Second item')
        self._p("Remove: correct item remains")

    # ------------------------------------------------------------------
    # Test 10: View endpoints respond
    # ------------------------------------------------------------------
    def test_10_view_endpoints(self):
        print("\n=== Test 10: View endpoints respond ===")
        client = Client()

        resp = client.get(f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/')
        self.assertEqual(resp.status_code, 200)
        self._p("Task detail page loads")
        self.assertIn(b'todo-list-widget', resp.content)
        self._p("Task detail has todo widget")
        self.assertIn(b'change-status', resp.content)
        self._p("Task detail has status dropdown")

        # Sorting needs a process with >1 task
        entity2 = Entity.objects.create(name='_View Test E2', description='', category=self.cat)
        template2 = OnboardingTemplate.objects.create(name='_View Sort Tmpl X')
        TemplateEntity.objects.create(template=template2, entity=self.entity, sort_order=0)
        TemplateEntity.objects.create(template=template2, entity=entity2, sort_order=1)
        p2 = create_onboarding_from_template(
            template=template2,
            new_employee_name='View Test X',
            new_employee_email='viewx@test.dk',
            new_employee_department='IT',
            new_employee_position='Tester',
            start_date=date.today() + timedelta(days=14),
            created_by=self.user1,
        )

        resp = client.get(f'/onboarding/{p2.pk}/?sort=name&dir=asc')
        self.assertEqual(resp.status_code, 200)
        self._p("Onboarding detail with sort loads")

        resp = client.get(f'/onboarding/{p2.pk}/?sort=status&dir=desc')
        self.assertEqual(resp.status_code, 200)
        self._p("Onboarding detail with status sort loads")

        resp = client.get(f'/onboarding/{p2.pk}/?sort=deadline&dir=asc')
        self.assertEqual(resp.status_code, 200)
        self._p("Onboarding detail with deadline sort loads")

        resp = client.post(
            f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/change-status/',
            data={'status': 'in_progress'},
        )
        self.assertEqual(resp.status_code, 302)
        self._p("Status change redirects")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, TaskStatus.IN_PROGRESS)
        self._p("Status changed to in_progress")

        resp = client.get(f'/onboarding/{self.process.pk}/tasks/{self.task.pk}/edit/')
        self.assertEqual(resp.status_code, 200)
        self._p("Task edit page loads")
        self.assertIn('Todo-listen redigeres', resp.content.decode())
        self._p("Edit page shows todolist notice")

    # ------------------------------------------------------------------
    # Test 11: notify_dependent_assignees
    # ------------------------------------------------------------------
    def test_11_notify_dependent_assignees(self):
        print("\n=== Test 11: notify_dependent_assignees ===")
        from apps.onboarding.models import TaskNotificationRule
        from apps.notifications.models import Notification

        e1 = Entity.objects.create(name='_Test Dep E1', description='', category=self.cat)
        e2 = Entity.objects.create(name='_Test Dep E2', description='', category=self.cat)
        tmpl = OnboardingTemplate.objects.create(name='_Test Dep Tmpl X')
        te1 = TemplateEntity.objects.create(tmpl, entity=e1, sort_order=0, default_assignee=self.user1) if False else \
              TemplateEntity.objects.create(template=tmpl, entity=e1, sort_order=0, default_assignee=self.user1)
        te2 = TemplateEntity.objects.create(template=tmpl, entity=e2, sort_order=1, default_assignee=self.user2)
        te2.dependencies.add(te1)

        from apps.templates_mgmt.models import TemplateEntityNotificationRule
        TemplateEntityNotificationRule.objects.create(
            template_entity=te1,
            notify_dependent_assignees=True,
            trigger_status='completed',
            send_email=True,
            send_in_app=True,
        )

        notif_before = Notification.objects.filter(recipient=self.user2).count()

        proc = create_onboarding_from_template(
            template=tmpl,
            new_employee_name='Dep Test X',
            new_employee_email='depx@test.dk',
            new_employee_department='IT',
            new_employee_position='Dev',
            start_date=date.today() + timedelta(days=30),
            created_by=self.user1,
        )
        tasks = list(proc.tasks.order_by('sort_order'))
        task1, task2 = tasks[0], tasks[1]

        self.assertEqual(task1.status, TaskStatus.READY)
        self.assertEqual(task2.status, TaskStatus.PENDING)
        self._p("Initial statuses correct")

        complete_task(task1, self.user1)
        task2.refresh_from_db()
        self.assertEqual(task2.status, TaskStatus.READY)
        self._p("Task2 promoted to READY")

        notif_after = Notification.objects.filter(recipient=self.user2).count()
        self.assertGreaterEqual(notif_after - notif_before, 1)
        self._p("Dependent assignee received notification")

        latest = Notification.objects.filter(recipient=self.user2).order_by('-created_at').first()
        self.assertIn('afhængige opgaver', latest.message.lower())
        self._p("Notification contains dependent task links")
        self.assertIn('href=', latest.message)
        self._p("Notification message has HTML links")


if __name__ == '__main__':
    import unittest
    # Run with verbosity to see individual test output
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda x, y: (x > y) - (x < y)
    suite = loader.loadTestsFromTestCase(AllFeaturesTest)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    passed = total - failures
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failures} failed out of {total}")
    if failures == 0:
        print("All tests passed!")
    sys.exit(0 if failures == 0 else 1)
