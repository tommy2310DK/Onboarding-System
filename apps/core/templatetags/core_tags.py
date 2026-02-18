from django import template

register = template.Library()


@register.filter
def percentage(value, total):
    if not total:
        return 0
    return int((value / total) * 100)
