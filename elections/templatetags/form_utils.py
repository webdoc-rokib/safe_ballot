from django import template
import json

register = template.Library()


@register.filter
def add_attrs(field, attrs):
    """Usage: {{ form.field|add_attrs:'{"class":"form-control"}' }}
    attrs is a JSON string mapping attribute names to values.
    Returns rendered widget HTML with merged attrs.
    """
    try:
        new_attrs = json.loads(attrs)
    except Exception:
        return field
    # Merge with existing attrs
    final_attrs = field.field.widget.attrs.copy() if hasattr(field, 'field') else {}
    final_attrs.update(new_attrs)
    return field.as_widget(attrs=final_attrs)
