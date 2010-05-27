from imagequery import ImageQuery
from django.core.cache import cache

# TODO: Keep this?
# TODO: Add storage support
def equal_height(images, maxwidth=None):
    """ Allows you to pass in multiple images, which all get resized to
    the same height while allowing you to defina a maximum width.
    
    The maximum height is calculated by resizing every image to the maximum
    width and comparing all resulting heights. maxheight gets to be
    min(heights). Because of the double-resize involved here the function
    caches the heights. But there is room for improvement. """
    minheight = None # infinity
    all_values = ':'.join(images.values())
    for i, value in images.items():
        if not value:
            continue
        try:
            cache_key = 'imagequery_equal_height_%s_%s_%d' % (all_values, value, maxwidth)
            height = cache.get(cache_key, None)
            if height is None:
                height = ImageQuery(value).resize(x=maxwidth).height()
                cache.set(cache_key, height, 604800) # 7 days
            if minheight is None or height < minheight:
                minheight = height
        except IOError:
            pass
    result = {}
    for i, value in images.items():
        try:
            result[i] = ImageQuery(value).scale(x=maxwidth, y=minheight)
        except IOError:
            result[i] = None
    return result

