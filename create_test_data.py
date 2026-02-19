"""
Create test data: entities, templates, and onboarding processes.
Uses existing users and categories from the database.
Safe to run multiple times (uses get_or_create throughout).
"""
import json
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from datetime import date, timedelta

from apps.core.models import SystemUser
from apps.entities.models import Category, CustomFieldDefinition, Entity, FieldType
from apps.onboarding.models import OnboardingProcess, OnboardingTaskFieldValue, TaskStatus
from apps.onboarding.services import change_task_status, complete_task, start_task
from apps.templates_mgmt.models import (
    OnboardingTemplate,
    TemplateEntity,
    TemplateEntityNotificationRule,
)
from apps.templates_mgmt.services import create_onboarding_from_template

# ---------------------------------------------------------------------------
# USERS — use existing ones
# ---------------------------------------------------------------------------
users = list(SystemUser.objects.filter(is_active=True).order_by('pk'))
if len(users) < 3:
    print("FEJL: Mindst 3 aktive brugere nødvendige.")
    sys.exit(1)

user_it = users[0]
user_hr = users[1] if len(users) > 1 else users[0]
user_facilities = users[2] if len(users) > 2 else users[0]
user_mgmt = users[3] if len(users) > 3 else users[0]
user_extra = users[4] if len(users) > 4 else users[0]

print(f"Brugere: {', '.join(u.name for u in users[:5])}")

# ---------------------------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------------------------
print("\nKategorier...")
cat_it, _ = Category.objects.get_or_create(name='IT')
cat_hr, _ = Category.objects.get_or_create(name='HR')
cat_facilities, _ = Category.objects.get_or_create(name='Facilities')
cat_adgang, _ = Category.objects.get_or_create(name='Adgang')
cat_admin, _ = Category.objects.get_or_create(name='Administration')
print(f"  {Category.objects.count()} kategorier")

# ---------------------------------------------------------------------------
# ENTITIES + CUSTOM FIELDS
# ---------------------------------------------------------------------------
print("\nEnheder...")


def make_entity(name, desc, cat, fields):
    """Create entity + custom fields. Returns entity."""
    e, _ = Entity.objects.get_or_create(name=name, defaults={'description': desc, 'category': cat})
    if e.category != cat:
        e.category = cat
        e.save(update_fields=['category'])
    for i, f in enumerate(fields):
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name=f['name'],
            defaults={
                'field_type': f.get('type', FieldType.TEXT),
                'default_value': f.get('default', ''),
                'is_required': f.get('required', False),
                'show_on_overview': f.get('overview', False),
                'sort_order': i,
            },
        )
    print(f"  {e.name} ({len(fields)} felter) — {cat.name}")
    return e


# 1. Bestil laptop
e_laptop = make_entity('Bestil laptop',
    'Bestil og klargør laptop til den nye medarbejder.',
    cat_it, [
        {'name': 'Model', 'default': 'Dell Latitude 5550', 'overview': True},
        {'name': 'RAM (GB)', 'type': FieldType.NUMBER, 'default': '16', 'overview': True},
        {'name': 'Serienummer', 'overview': True},
        {'name': 'Admin-rettigheder', 'type': FieldType.CHECKBOX},
        {'name': 'Bestilt', 'type': FieldType.CHECKBOX, 'overview': True},
    ])

# 2. Opret AD-konto
e_ad = make_entity('Opret AD-konto',
    'Opret Active Directory-konto med korrekte grupper og rettigheder.',
    cat_it, [
        {'name': 'Brugernavn', 'required': True, 'overview': True},
        {'name': 'AD-grupper', 'default': 'Domain Users'},
        {'name': 'Adgangskode sendt', 'type': FieldType.CHECKBOX, 'overview': True},
    ])

# 3. Opret email-konto
e_email = make_entity('Opret email-konto',
    'Opret Microsoft 365 email-konto og konfigurer Outlook.',
    cat_it, [
        {'name': 'Email-adresse', 'required': True, 'overview': True},
        {'name': 'Distributionslister', 'default': 'Alle medarbejdere'},
    ])

# 4. VPN-adgang
e_vpn = make_entity('Opsæt VPN-adgang',
    'Konfigurer VPN-adgang til firmanetværket via GlobalProtect.',
    cat_it, [
        {'name': 'VPN-profil', 'default': 'Standard'},
        {'name': 'Konfigureret', 'type': FieldType.CHECKBOX, 'overview': True},
    ])

# 5. Installer software
e_software = make_entity('Installer software',
    'Installer nødvendige softwarepakker på laptop.',
    cat_it, [
        {'name': 'Software-pakker', 'type': FieldType.TODOLIST,
         'default': 'Microsoft Office 365\nTeams\nAdobe Reader\nChrome\nVS Code',
         'overview': True},
        {'name': 'Specialsoftware'},
    ])

# 6. Tildel licenser
e_licenser = make_entity('Tildel software-licenser',
    'Tildel licenser til Microsoft 365, Adobe og øvrig software.',
    cat_it, [
        {'name': 'Licenser', 'type': FieldType.TODOLIST,
         'default': 'Microsoft 365 E3\nAdobe Acrobat\nSlack\nJira'},
    ])

# 7. Kontrakt
e_kontrakt = make_entity('Kontrakt underskrevet',
    'Sikre at ansættelseskontrakt er underskrevet og arkiveret.',
    cat_hr, [
        {'name': 'Kontraktdato', 'overview': True},
        {'name': 'Underskrevet', 'type': FieldType.CHECKBOX, 'overview': True},
    ])

# 8. Opret i lønsystem
e_lon = make_entity('Opret i lønsystem',
    'Registrer medarbejder i lønsystemet (Danløn).',
    cat_hr, [
        {'name': 'Medarbejder-nr.', 'overview': True},
        {'name': 'Bankkonto registreret', 'type': FieldType.CHECKBOX, 'overview': True},
    ])

# 9. Forbered velkomstpakke
e_welcome = make_entity('Forbered velkomstpakke',
    'Pakke med nøglekort, velkomstbrev, gadgets og informationsmateriale.',
    cat_hr, [
        {'name': 'Tjekliste', 'type': FieldType.TODOLIST,
         'default': 'Nøglekort\nVelkomstbrev\nKentaur-krus\nInformationsmappe\nParkeringstilladelse',
         'overview': True},
    ])

# 10. Bestil adgangskort
e_badge = make_entity('Bestil adgangskort',
    'Bestil adgangskort med foto til bygningsadgang.',
    cat_adgang, [
        {'name': 'Kortnummer', 'overview': True},
        {'name': 'Foto modtaget', 'type': FieldType.CHECKBOX, 'overview': True},
        {'name': 'Adgangszoner', 'default': 'Hovedindgang, Kantine, Parkering'},
    ])

# 11. Klargør arbejdsplads
e_desk = make_entity('Klargør arbejdsplads',
    'Sæt skrivebord, stol, skærme og headset op.',
    cat_facilities, [
        {'name': 'Placering / kontor', 'overview': True},
        {'name': 'Antal skærme', 'type': FieldType.NUMBER, 'default': '2', 'overview': True},
        {'name': 'Udstyr', 'type': FieldType.TODOLIST,
         'default': '27\" skærm\nDocking station\nTrådløs mus og tastatur\nHeadset (Jabra)\nHæve/sænke-bord'},
    ])

# 12. Velkomstmøde med leder
e_velkomst = make_entity('Velkomstmøde med leder',
    'Planlæg introsamtale med nærmeste leder.',
    cat_hr, [
        {'name': 'Tidspunkt', 'overview': True},
        {'name': 'Lokale'},
    ])

# 13. Introduktion til teamet
e_intro = make_entity('Introduktion til teamet',
    'Præsenter ny medarbejder for teamet og vis rundt.',
    cat_hr, [
        {'name': 'Tidspunkt', 'overview': True},
    ])

# 14. Planlæg første dag
e_day1 = make_entity('Planlæg første dag',
    'Sørg for at den nye medarbejders første dag er planlagt med aktiviteter.',
    cat_hr, [
        {'name': 'Program', 'type': FieldType.TODOLIST,
         'default': '09:00 - Velkomst med HR\n09:30 - Rundvisning\n10:00 - IT-opsætning\n11:00 - Møde med leder\n12:00 - Frokost med teamet\n13:00 - Introduktion til projekter\n15:00 - Buddy-møde',
         'overview': True},
    ])

# 15. Bestil firmatelefon
e_phone = make_entity('Bestil firmatelefon',
    'Bestil mobiltelefon og opret abonnement hos TDC.',
    cat_it, [
        {'name': 'Model', 'default': 'iPhone 15', 'overview': True},
        {'name': 'Telefonnummer', 'overview': True},
        {'name': 'Bestilt', 'type': FieldType.CHECKBOX, 'overview': True},
    ])

# 16. Sikkerhedsinstruktion
e_security = make_entity('Gennemfør sikkerhedsinstruktion',
    'Gennemfør online sikkerhedskursus og underskriv IT-politik.',
    cat_admin, [
        {'name': 'Kursus gennemført', 'type': FieldType.CHECKBOX, 'overview': True},
        {'name': 'IT-politik underskrevet', 'type': FieldType.CHECKBOX, 'overview': True},
    ])


# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------
print("\nSkabeloner...")

# Template 1: Standard IT Onboarding (komplet)
tmpl1, _ = OnboardingTemplate.objects.get_or_create(
    name='Standard IT Onboarding',
    defaults={
        'description': 'Komplet onboarding-proces for nye IT-medarbejdere hos Kentaur. '
                       'Dækker alt fra kontrakt til første arbejdsdag.',
    },
)

te_map1 = {}
te_data1 = [
    ('kontrakt',   e_kontrakt,  14, user_hr),
    ('lon',        e_lon,       10, user_hr),
    ('ad',         e_ad,         7, user_it),
    ('email',      e_email,      7, user_it),
    ('laptop',     e_laptop,    10, user_it),
    ('phone',      e_phone,      7, user_it),
    ('licenser',   e_licenser,   5, user_it),
    ('software',   e_software,   3, user_extra),
    ('vpn',        e_vpn,        3, user_it),
    ('badge',      e_badge,      5, user_facilities),
    ('desk',       e_desk,       2, user_facilities),
    ('security',   e_security,   3, user_it),
    ('welcome',    e_welcome,    1, user_hr),
    ('velkomst',   e_velkomst,   0, user_mgmt),
    ('intro',      e_intro,      0, user_mgmt),
    ('day1',       e_day1,       0, user_hr),
]
for i, (key, entity, days, assignee) in enumerate(te_data1):
    te, _ = TemplateEntity.objects.get_or_create(
        template=tmpl1, entity=entity,
        defaults={'sort_order': i, 'days_before_start': days, 'default_assignee': assignee},
    )
    te_map1[key] = te

# Dependencies
deps1 = {
    'ad':       ['kontrakt'],
    'email':    ['ad'],
    'lon':      ['kontrakt'],
    'licenser': ['ad'],
    'software': ['laptop', 'licenser'],
    'vpn':      ['ad'],
    'desk':     ['laptop'],
    'security': ['ad'],
    'velkomst': ['email', 'badge'],
    'intro':    ['velkomst'],
    'day1':     ['welcome', 'intro', 'desk'],
}
for key, dep_keys in deps1.items():
    for dk in dep_keys:
        te_map1[key].dependencies.add(te_map1[dk])

# Notification rules
notif1 = [
    ('laptop', user_it),
    ('ad', user_hr),
    ('velkomst', user_mgmt),
    ('licenser', user_extra),
    ('day1', user_hr),
]
for te_key, notify_user in notif1:
    TemplateEntityNotificationRule.objects.get_or_create(
        template_entity=te_map1[te_key], notify_user=notify_user,
        defaults={'send_email': True, 'send_in_app': True},
    )

print(f"  {tmpl1.name} ({len(te_data1)} opgaver, {sum(len(v) for v in deps1.values())} afhængigheder)")

# Template 2: Simpel Onboarding (ikke-IT)
tmpl2, _ = OnboardingTemplate.objects.get_or_create(
    name='Simpel Onboarding (ikke-IT)',
    defaults={
        'description': 'Forenklet onboarding for medarbejdere uden IT-specifikke behov. '
                       'Dækker HR, adgang og velkomst.',
    },
)

te_map2 = {}
te_data2 = [
    ('kontrakt', e_kontrakt, 14, user_hr),
    ('lon',      e_lon,      10, user_hr),
    ('ad',       e_ad,        5, user_it),
    ('email',    e_email,     5, user_it),
    ('badge',    e_badge,     5, user_facilities),
    ('welcome',  e_welcome,   1, user_hr),
    ('velkomst', e_velkomst,  0, user_mgmt),
    ('intro',    e_intro,     0, user_mgmt),
]
for i, (key, entity, days, assignee) in enumerate(te_data2):
    te, _ = TemplateEntity.objects.get_or_create(
        template=tmpl2, entity=entity,
        defaults={'sort_order': i, 'days_before_start': days, 'default_assignee': assignee},
    )
    te_map2[key] = te

deps2 = {
    'lon':      ['kontrakt'],
    'ad':       ['kontrakt'],
    'email':    ['ad'],
    'velkomst': ['email', 'badge'],
    'intro':    ['velkomst'],
}
for key, dep_keys in deps2.items():
    for dk in dep_keys:
        te_map2[key].dependencies.add(te_map2[dk])

print(f"  {tmpl2.name} ({len(te_data2)} opgaver, {sum(len(v) for v in deps2.values())} afhængigheder)")

# ---------------------------------------------------------------------------
# ONBOARDING 1: Ny IT-medarbejder (delvist i gang)
# ---------------------------------------------------------------------------
print("\nOnboarding-processer...")

proc1 = None
if not OnboardingProcess.objects.filter(new_employee_name='Mikkel Andersen').exists():
    proc1 = create_onboarding_from_template(
        template=tmpl1,
        new_employee_name='Mikkel Andersen',
        new_employee_email='mikkel.andersen@kentaur.dk',
        new_employee_department='IT',
        new_employee_position='Senior Developer',
        start_date=date.today() + timedelta(days=12),
        created_by=user_hr,
    )

    # Fill in some field values to make it look realistic
    for task in proc1.tasks.all():
        if task.name == 'Kontrakt underskrevet':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Kontraktdato':
                    fv.value_text = (date.today() - timedelta(days=5)).strftime('%d/%m/%Y')
                    fv.save(update_fields=['value_text'])
                elif fv.field_definition.name == 'Underskrevet':
                    fv.value_checkbox = True
                    fv.save(update_fields=['value_checkbox'])

        elif task.name == 'Bestil laptop':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Model':
                    fv.value_text = 'Dell Latitude 5550'
                    fv.save(update_fields=['value_text'])
                elif fv.field_definition.name == 'Serienummer':
                    fv.value_text = 'DL-2026-K-0487'
                    fv.save(update_fields=['value_text'])
                elif fv.field_definition.name == 'Bestilt':
                    fv.value_checkbox = True
                    fv.save(update_fields=['value_checkbox'])

        elif task.name == 'Opret AD-konto':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Brugernavn':
                    fv.value_text = 'mian'
                    fv.save(update_fields=['value_text'])

        elif task.name == 'Opret email-konto':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Email-adresse':
                    fv.value_text = 'mikkel.andersen@kentaur.dk'
                    fv.save(update_fields=['value_text'])

        elif task.name == 'Klargør arbejdsplads':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Placering / kontor':
                    fv.value_text = 'Bygning A, 2. sal, plads 14'
                    fv.save(update_fields=['value_text'])
                elif fv.field_definition.name == 'Antal skærme':
                    fv.value_number = 2
                    fv.save(update_fields=['value_number'])

        elif task.name == 'Bestil adgangskort':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Kortnummer':
                    fv.value_text = 'K-2026-0892'
                    fv.save(update_fields=['value_text'])
                elif fv.field_definition.name == 'Foto modtaget':
                    fv.value_checkbox = True
                    fv.save(update_fields=['value_checkbox'])

        elif task.name == 'Bestil firmatelefon':
            for fv in task.field_values.all():
                if fv.field_definition.name == 'Model':
                    fv.value_text = 'iPhone 15 Pro'
                    fv.save(update_fields=['value_text'])
                elif fv.field_definition.name == 'Telefonnummer':
                    fv.value_text = '+45 42 87 19 03'
                    fv.save(update_fields=['value_text'])

    # Advance some tasks to simulate a partially completed onboarding
    # Complete: Kontrakt, Løn, Bestil laptop, Bestil adgangskort, Bestil firmatelefon
    for task_name in ['Kontrakt underskrevet', 'Bestil laptop', 'Bestil adgangskort', 'Bestil firmatelefon']:
        task = proc1.tasks.get(name=task_name)
        if task.status in ['pending', 'ready']:
            if task.status == 'pending':
                task.status = TaskStatus.READY
                task.save(update_fields=['status'])
            complete_task(task, user_hr)

    # Løn: after kontrakt is done it should be READY, complete it
    task_lon = proc1.tasks.get(name='Opret i lønsystem')
    task_lon.refresh_from_db()
    if task_lon.status == 'ready':
        complete_task(task_lon, user_hr)

    # Start AD-konto (should be READY after kontrakt is done)
    task_ad = proc1.tasks.get(name='Opret AD-konto')
    task_ad.refresh_from_db()
    if task_ad.status == 'ready':
        start_task(task_ad)

    print(f"  Mikkel Andersen — IT (delvist i gang, {proc1.tasks.filter(status='completed').count()} færdige)")
else:
    print("  Mikkel Andersen — allerede oprettet")

# ---------------------------------------------------------------------------
# ONBOARDING 2: Ny HR-medarbejder (lige startet)
# ---------------------------------------------------------------------------
proc2 = None
if not OnboardingProcess.objects.filter(new_employee_name='Sara Kristensen').exists():
    proc2 = create_onboarding_from_template(
        template=tmpl2,
        new_employee_name='Sara Kristensen',
        new_employee_email='sara.kristensen@kentaur.dk',
        new_employee_department='HR',
        new_employee_position='HR-konsulent',
        start_date=date.today() + timedelta(days=21),
        created_by=user_hr,
    )
    proc2.notes = 'Sara starter i Aalborg-kontoret. Husk parkering.'
    proc2.save(update_fields=['notes'])

    print(f"  Sara Kristensen — HR (ny, {proc2.tasks.count()} opgaver)")
else:
    print("  Sara Kristensen — allerede oprettet")

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Database indhold:")
print(f"  {SystemUser.objects.count()} brugere")
print(f"  {Category.objects.count()} kategorier")
print(f"  {Entity.objects.count()} enheder")
print(f"  {CustomFieldDefinition.objects.count()} brugerdefinerede felter")
show_overview_count = CustomFieldDefinition.objects.filter(show_on_overview=True).count()
print(f"    (heraf {show_overview_count} med 'Vis på onboarding')")
print(f"  {OnboardingTemplate.objects.count()} skabeloner")
print(f"  {OnboardingProcess.objects.count()} onboarding-processer")

for p in OnboardingProcess.objects.all():
    tasks = p.tasks.all()
    done = tasks.filter(status__in=['completed', 'skipped']).count()
    print(f"\n  {p.new_employee_name} ({p.new_employee_position}, {p.new_employee_department})")
    print(f"    Start: {p.start_date} — {done}/{tasks.count()} opgaver færdige ({p.progress_percentage}%)")
    for t in tasks.select_related('assignee').order_by('sort_order'):
        deps = ', '.join(d.name for d in t.dependencies.all())
        dep_str = f'  (← {deps})' if deps else ''
        status_icon = {'completed': '[OK]', 'in_progress': '[>>]', 'ready': '[**]', 'skipped': '[--]'}.get(t.status, '[  ]')
        print(f"    {status_icon} {t.get_status_display():15} {t.name} - {t.assignee or 'Ingen'}{dep_str}")

print(f"\n{'='*60}")
print("Testdata oprettet!")
