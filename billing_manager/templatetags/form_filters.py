from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Adds a class to the form field.
    Usage: {{ form.field_name|add_class:"class-name" }}
    """
    return value.as_widget(attrs={'class': arg})