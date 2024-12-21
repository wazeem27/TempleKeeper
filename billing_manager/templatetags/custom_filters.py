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

@register.filter
def dict_get(d, key):
    return d.get(key)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def get_dynamic_value(data, key):
    """
    Fetches the value of a dynamically generated key in a dictionary.
    Usage: {{ data|get_dynamic_value:'note_5' }}
    """
    return data.get(key, 0)  # Default to 0 if the key doesn't exist