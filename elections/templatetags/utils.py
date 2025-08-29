from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except Exception:
        return None
from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def add_attrs(field, attr_str):
    """Add attributes to a form field widget from template.
    Usage: {{ form.title|add_attrs:'class=form-control id=myid' }}
    """
    try:
        attrs = {}
        for part in attr_str.split():
            if '=' in part:
                k, v = part.split('=', 1)
                attrs[k] = v.strip('"\'')
        return field.as_widget(attrs=attrs)
    except Exception:
        return field
