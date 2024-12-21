from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

@register.filter
def add_attr(value, attrs):
    """Adds attributes to an HTML element"""
    try:
        attrs = attrs.split(",")  # Splitting string into a list of attributes
        if len(attrs) % 2 == 0:
            attributes = dict(zip(attrs[::2], attrs[1::2]))  # Create a dictionary of key-value pairs
            for key, val in attributes.items():
                value.field.widget.attrs[key] = val
        return value
    except Exception as e:
        return value  # Return original if something goes wrong