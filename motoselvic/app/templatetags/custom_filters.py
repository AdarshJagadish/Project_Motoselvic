from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return value * arg
    except (TypeError, ValueError):
        return 0

@register.filter
def percentage(part, whole):
    try:
        return (float(part) / float(whole)) * 100
    except (ValueError, ZeroDivisionError):
        return 0
    
@register.filter
def get_default(addresses):
    return addresses.filter(is_default=True).first()

@register.filter
def main_image(images):
    # images is a RelatedManager or queryset of images
    return images.filter(is_main=True).first()