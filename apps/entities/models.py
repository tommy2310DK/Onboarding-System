from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name='Navn')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategorier'
        ordering = ['name']

    def __str__(self):
        return self.name


class FieldType(models.TextChoices):
    TEXT = 'text', 'Tekst'
    NUMBER = 'number', 'Tal'
    CHECKBOX = 'checkbox', 'Checkbox'
    TODOLIST = 'todolist', 'Todo-liste'


class Entity(models.Model):
    name = models.CharField(max_length=300, verbose_name='Navn')
    description = models.TextField(blank=True, verbose_name='Beskrivelse')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entities', verbose_name='Kategori',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Enhed'
        verbose_name_plural = 'Enheder'
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomFieldDefinition(models.Model):
    entity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name='custom_fields'
    )
    name = models.CharField(max_length=200, verbose_name='Feltnavn')
    field_type = models.CharField(
        max_length=20, choices=FieldType.choices, default=FieldType.TEXT,
        verbose_name='Felttype'
    )
    is_required = models.BooleanField(default=False, verbose_name='Påkrævet')
    show_on_overview = models.BooleanField(default=False, verbose_name='Vis på onboarding')
    default_value = models.CharField(max_length=500, blank=True, verbose_name='Standardværdi')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Sortering')

    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = ['entity', 'name']
        verbose_name = 'Brugerdefineret felt'
        verbose_name_plural = 'Brugerdefinerede felter'

    def __str__(self):
        return f"{self.entity.name} → {self.name} ({self.get_field_type_display()})"
