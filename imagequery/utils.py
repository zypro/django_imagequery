from imagequery import ImageQuery
from django.core.cache import cache

def equal_height(images, maxwidth=None):
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

