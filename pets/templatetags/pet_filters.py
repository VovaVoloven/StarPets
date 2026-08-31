from django import template

#registering the template library
register = template.Library()

@register.inclusion_tag('pets/partials/stars_overlay.html')
def draw_stars(stars):
    #try to convert the input to a float, if it fails, default to 0.0
    try:
        stars = float(stars)
    except (ValueError, TypeError):
        stars = 0.0
        
    #ensure stars is between 0.0 and 5.0
    stars = max(0.0, min(stars, 5.0))
    
    # Calculate the width percentage for the gold stars
    fill_percentage = (stars / 5.0) * 100
    
    return {
        'stars': stars,
        'fill_percentage': fill_percentage
        }
