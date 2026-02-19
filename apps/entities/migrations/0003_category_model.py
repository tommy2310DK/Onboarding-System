# Generated manually: Create Category model, migrate data, change FK

import django.db.models.deletion
from django.db import migrations, models


def migrate_categories_forward(apps, schema_editor):
    """Create Category objects from existing Entity.category text values and link them."""
    Entity = apps.get_model('entities', 'Entity')
    Category = apps.get_model('entities', 'Category')

    # Collect unique non-empty category names
    category_names = (
        Entity.objects
        .exclude(category_text='')
        .exclude(category_text__isnull=True)
        .values_list('category_text', flat=True)
        .distinct()
    )

    name_to_cat = {}
    for name in category_names:
        cat, _ = Category.objects.get_or_create(name=name)
        name_to_cat[name] = cat

    # Update entities to point to Category objects
    for name, cat in name_to_cat.items():
        Entity.objects.filter(category_text=name).update(category=cat)


def migrate_categories_backward(apps, schema_editor):
    """Restore category text values from FK."""
    Entity = apps.get_model('entities', 'Entity')
    for entity in Entity.objects.select_related('category').all():
        if entity.category:
            entity.category_text = entity.category.name
            entity.save(update_fields=['category_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('entities', '0002_alter_customfielddefinition_field_type'),
    ]

    operations = [
        # 1. Create the Category model
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='Navn')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Kategori',
                'verbose_name_plural': 'Kategorier',
                'ordering': ['name'],
            },
        ),

        # 2. Rename old category CharField to category_text
        migrations.RenameField(
            model_name='entity',
            old_name='category',
            new_name='category_text',
        ),

        # 3. Add new category FK (nullable)
        migrations.AddField(
            model_name='entity',
            name='category',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='entities',
                to='entities.category',
                verbose_name='Kategori',
            ),
        ),

        # 4. Migrate data from text to FK
        migrations.RunPython(migrate_categories_forward, migrate_categories_backward),

        # 5. Remove old category_text field
        migrations.RemoveField(
            model_name='entity',
            name='category_text',
        ),
    ]
