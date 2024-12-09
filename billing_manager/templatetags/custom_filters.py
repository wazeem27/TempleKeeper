from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """Add a CSS class to a form field."""
    try:
        value.field.widget.attrs['class'] = arg
    except AttributeError:
        pass
    return value