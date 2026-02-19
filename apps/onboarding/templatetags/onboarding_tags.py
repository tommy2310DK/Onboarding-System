import json

from django import template

register = template.Library()


@register.filter
def parse_todo_json(value):
    """Parse a JSON string of todo items into a list of dicts."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError, TypeError):
        return []
