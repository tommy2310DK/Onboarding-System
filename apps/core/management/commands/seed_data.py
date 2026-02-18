from django.core.management.base import BaseCommand

from apps.core.models import SystemUser
from apps.entities.models import Entity, CustomFieldDefinition, FieldType
from apps.templates_mgmt.models import (
    OnboardingTemplate, TemplateEntity, TemplateEntityNotificationRule,
)


class Command(BaseCommand):
    help = 'Populate database with demo data for Kentaur Onboarding'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')

        # Create users
        users = {}
        user_data = [
            ('Anders Jensen', 'anders@kentaur.dk', 'IT'),
            ('Maria Nielsen', 'maria@kentaur.dk', 'HR'),
            ('Peter Hansen', 'peter@kentaur.dk', 'IT'),
            ('Louise Pedersen', 'louise@kentaur.dk', 'Kontor'),
            ('Thomas Larsen', 'thomas@kentaur.dk', 'Ledelse'),
        ]
        for name, email, dept in user_data:
            user, created = SystemUser.objects.get_or_create(
                email=email,
                defaults={'name': name, 'department': dept},
            )
            users[name.split()[0].lower()] = user
            if created:
                self.stdout.write(f'  Created user: {name}')

        # Create entities
        entities = {}

        # IT entities
        e, _ = Entity.objects.get_or_create(
            name='Bestil laptop',
            defaults={'description': 'Bestil og klargør laptop til den nye medarbejder.', 'category': 'IT'}
        )
        entities['laptop'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Laptop model',
            defaults={'field_type': FieldType.TEXT, 'default_value': 'Dell Latitude 5540', 'sort_order': 0}
        )
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='RAM (GB)',
            defaults={'field_type': FieldType.NUMBER, 'default_value': '16', 'sort_order': 1}
        )
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Admin-rettigheder',
            defaults={'field_type': FieldType.CHECKBOX, 'sort_order': 2}
        )

        e, _ = Entity.objects.get_or_create(
            name='Opret AD-konto',
            defaults={'description': 'Opret Active Directory brugerkonto.', 'category': 'IT'}
        )
        entities['ad'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Brugernavn',
            defaults={'field_type': FieldType.TEXT, 'is_required': True, 'sort_order': 0}
        )

        e, _ = Entity.objects.get_or_create(
            name='Opret email-konto',
            defaults={'description': 'Opret Microsoft 365 email konto.', 'category': 'IT'}
        )
        entities['email'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Email-adresse',
            defaults={'field_type': FieldType.TEXT, 'is_required': True, 'sort_order': 0}
        )

        e, _ = Entity.objects.get_or_create(
            name='Opsæt VPN-adgang',
            defaults={'description': 'Konfigurer VPN-adgang til firmanetværket.', 'category': 'IT'}
        )
        entities['vpn'] = e

        e, _ = Entity.objects.get_or_create(
            name='Installer software',
            defaults={'description': 'Installer nødvendige softwarepakker på laptop.', 'category': 'IT'}
        )
        entities['software'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Software-pakker',
            defaults={'field_type': FieldType.TEXT, 'default_value': 'Office 365, Teams, Adobe Reader', 'sort_order': 0}
        )
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Specialsoftware',
            defaults={'field_type': FieldType.TEXT, 'sort_order': 1}
        )

        e, _ = Entity.objects.get_or_create(
            name='Tildel software-licenser',
            defaults={'description': 'Tildel licenser til nødvendige softwareprodukter.', 'category': 'IT'}
        )
        entities['licenser'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Licenser tildelt',
            defaults={'field_type': FieldType.TEXT, 'sort_order': 0}
        )

        # HR entities
        e, _ = Entity.objects.get_or_create(
            name='Kontrakt underskrevet',
            defaults={'description': 'Sikre at ansættelseskontrakt er underskrevet og arkiveret.', 'category': 'HR'}
        )
        entities['kontrakt'] = e

        e, _ = Entity.objects.get_or_create(
            name='Bestil adgangskort',
            defaults={'description': 'Bestil adgangskort til bygningen.', 'category': 'Adgang'}
        )
        entities['adgangskort'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Kortnummer',
            defaults={'field_type': FieldType.TEXT, 'sort_order': 0}
        )

        e, _ = Entity.objects.get_or_create(
            name='Klargør arbejdsplads',
            defaults={'description': 'Sæt skrivebord, stol, skærme og headset op.', 'category': 'Kontor'}
        )
        entities['arbejdsplads'] = e
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Pladsering / kontor',
            defaults={'field_type': FieldType.TEXT, 'sort_order': 0}
        )
        CustomFieldDefinition.objects.get_or_create(
            entity=e, name='Antal skærme',
            defaults={'field_type': FieldType.NUMBER, 'default_value': '2', 'sort_order': 1}
        )

        e, _ = Entity.objects.get_or_create(
            name='Velkomstmøde med leder',
            defaults={'description': 'Planlæg introsamtale med nærmeste leder.', 'category': 'HR'}
        )
        entities['velkomst'] = e

        e, _ = Entity.objects.get_or_create(
            name='Introduktion til teamet',
            defaults={'description': 'Præsenter ny medarbejder for teamet og vis rundt.', 'category': 'HR'}
        )
        entities['intro'] = e

        e, _ = Entity.objects.get_or_create(
            name='Opret i lønsystem',
            defaults={'description': 'Registrer medarbejder i lønsystemet.', 'category': 'HR'}
        )
        entities['lon'] = e

        self.stdout.write(f'  Created {len(entities)} entities')

        # Create template: Standard IT Onboarding
        tmpl, created = OnboardingTemplate.objects.get_or_create(
            name='Standard IT Onboarding',
            defaults={
                'description': 'Komplet onboarding-proces for nye IT-medarbejdere hos Kentaur. '
                               'Dækker alt fra kontrakt til første arbejdsdag.',
            }
        )

        if created:
            self.stdout.write('  Creating template entities...')

            # Add entities to template with order, deadlines, and assignees
            te_kontrakt = TemplateEntity.objects.create(
                template=tmpl, entity=entities['kontrakt'],
                days_before_start=14, default_assignee=users['maria'], sort_order=1,
            )
            te_lon = TemplateEntity.objects.create(
                template=tmpl, entity=entities['lon'],
                days_before_start=10, default_assignee=users['maria'], sort_order=2,
            )
            te_ad = TemplateEntity.objects.create(
                template=tmpl, entity=entities['ad'],
                days_before_start=7, default_assignee=users['anders'], sort_order=3,
            )
            te_email = TemplateEntity.objects.create(
                template=tmpl, entity=entities['email'],
                days_before_start=7, default_assignee=users['anders'], sort_order=4,
            )
            te_laptop = TemplateEntity.objects.create(
                template=tmpl, entity=entities['laptop'],
                days_before_start=10, default_assignee=users['peter'], sort_order=5,
            )
            te_licenser = TemplateEntity.objects.create(
                template=tmpl, entity=entities['licenser'],
                days_before_start=5, default_assignee=users['anders'], sort_order=6,
            )
            te_software = TemplateEntity.objects.create(
                template=tmpl, entity=entities['software'],
                days_before_start=3, default_assignee=users['peter'], sort_order=7,
            )
            te_vpn = TemplateEntity.objects.create(
                template=tmpl, entity=entities['vpn'],
                days_before_start=3, default_assignee=users['anders'], sort_order=8,
            )
            te_adgangskort = TemplateEntity.objects.create(
                template=tmpl, entity=entities['adgangskort'],
                days_before_start=5, default_assignee=users['louise'], sort_order=9,
            )
            te_arbejdsplads = TemplateEntity.objects.create(
                template=tmpl, entity=entities['arbejdsplads'],
                days_before_start=2, default_assignee=users['louise'], sort_order=10,
            )
            te_velkomst = TemplateEntity.objects.create(
                template=tmpl, entity=entities['velkomst'],
                days_before_start=0, default_assignee=users['thomas'], sort_order=11,
            )
            te_intro = TemplateEntity.objects.create(
                template=tmpl, entity=entities['intro'],
                days_before_start=0, default_assignee=users['thomas'], sort_order=12,
            )

            # Set up dependencies
            # AD-konto depends on kontrakt
            te_ad.dependencies.add(te_kontrakt)
            # Email depends on AD-konto
            te_email.dependencies.add(te_ad)
            # Løn depends on kontrakt
            te_lon.dependencies.add(te_kontrakt)
            # Licenser depends on AD-konto
            te_licenser.dependencies.add(te_ad)
            # Software depends on laptop + licenser
            te_software.dependencies.add(te_laptop, te_licenser)
            # VPN depends on AD-konto
            te_vpn.dependencies.add(te_ad)
            # Arbejdsplads depends on laptop
            te_arbejdsplads.dependencies.add(te_laptop)
            # Velkomstmøde depends on everything being almost ready
            te_velkomst.dependencies.add(te_email, te_adgangskort)
            # Intro depends on velkomstmøde
            te_intro.dependencies.add(te_velkomst)

            # Set up notification rules
            # Notify IT lead (Anders) when laptop is ready
            TemplateEntityNotificationRule.objects.create(
                template_entity=te_laptop, notify_user=users['anders'],
                send_email=True, send_in_app=True,
            )
            # Notify HR (Maria) when AD-konto is created
            TemplateEntityNotificationRule.objects.create(
                template_entity=te_ad, notify_user=users['maria'],
                send_email=True, send_in_app=True,
            )
            # Notify management when onboarding is nearly done
            TemplateEntityNotificationRule.objects.create(
                template_entity=te_velkomst, notify_user=users['thomas'],
                send_email=True, send_in_app=True,
            )
            # Notify Peter when licenser er klar (so he can install software)
            TemplateEntityNotificationRule.objects.create(
                template_entity=te_licenser, notify_user=users['peter'],
                send_email=True, send_in_app=True,
            )

            self.stdout.write('  Template created with entities, dependencies, and notification rules')

        # Create a simpler template too
        tmpl2, created2 = OnboardingTemplate.objects.get_or_create(
            name='Simpel Onboarding (ikke-IT)',
            defaults={
                'description': 'Forenklet onboarding for medarbejdere uden IT-specifikke behov.',
            }
        )
        if created2:
            te2_kontrakt = TemplateEntity.objects.create(
                template=tmpl2, entity=entities['kontrakt'],
                days_before_start=14, default_assignee=users['maria'], sort_order=1,
            )
            te2_lon = TemplateEntity.objects.create(
                template=tmpl2, entity=entities['lon'],
                days_before_start=10, default_assignee=users['maria'], sort_order=2,
            )
            te2_ad = TemplateEntity.objects.create(
                template=tmpl2, entity=entities['ad'],
                days_before_start=7, default_assignee=users['anders'], sort_order=3,
            )
            te2_email = TemplateEntity.objects.create(
                template=tmpl2, entity=entities['email'],
                days_before_start=7, default_assignee=users['anders'], sort_order=4,
            )
            te2_adgangskort = TemplateEntity.objects.create(
                template=tmpl2, entity=entities['adgangskort'],
                days_before_start=5, default_assignee=users['louise'], sort_order=5,
            )
            te2_velkomst = TemplateEntity.objects.create(
                template=tmpl2, entity=entities['velkomst'],
                days_before_start=0, default_assignee=users['thomas'], sort_order=6,
            )

            te2_lon.dependencies.add(te2_kontrakt)
            te2_ad.dependencies.add(te2_kontrakt)
            te2_email.dependencies.add(te2_ad)
            te2_velkomst.dependencies.add(te2_email, te2_adgangskort)

            self.stdout.write('  Simple template created')

        self.stdout.write(self.style.SUCCESS('Demo data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Users:')
        for user in SystemUser.objects.all():
            self.stdout.write(f'  - {user.name} ({user.email}) - {user.department}')
        self.stdout.write('')
        self.stdout.write('Templates:')
        for t in OnboardingTemplate.objects.all():
            self.stdout.write(f'  - {t.name} ({t.template_entities.count()} entities)')
