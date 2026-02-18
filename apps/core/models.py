from django.db import models


class AuthMethod(models.TextChoices):
    LOCAL = 'local', 'Lokal'
    AZURE_AD = 'azure_ad', 'Azure AD'


class SystemUser(models.Model):
    name = models.CharField(max_length=200, verbose_name='Navn')
    email = models.EmailField(unique=True, verbose_name='Email')
    department = models.CharField(max_length=200, blank=True, verbose_name='Afdeling')
    title = models.CharField(max_length=200, blank=True, verbose_name='Stilling')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Telefon')
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')
    # Azure AD integration fields (prepared for future use)
    auth_method = models.CharField(
        max_length=20, choices=AuthMethod.choices, default=AuthMethod.LOCAL,
        verbose_name='Autentificeringsmetode',
        help_text='Lokal = brugervælger. Azure AD = fremtidig SSO integration.'
    )
    azure_ad_object_id = models.CharField(
        max_length=36, blank=True, verbose_name='Azure AD Object ID',
        help_text='Udfyldes automatisk ved Azure AD sync.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Bruger'
        verbose_name_plural = 'Brugere'

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()
