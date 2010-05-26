from django import template
from imagequery import ImageQuery
from django.db.models.fields.files import ImageFieldFile
from django.utils.encoding import smart_unicode

register = template.Library()

def parse_value(value):
    try:
        if int(value) == float(value):
            return int(value)
        else:
            return float(value)
    except (TypeError, ValueError):
        return value

def parse_attrs(attrs):
    args, kwargs = [], {}
    if attrs:
        for attr in attrs.split(','):
            try:
                key, value = attr.split('=', 1)
                kwargs[key] = parse_value(value)
            except ValueError:
                args.append(parse_value(attr))
    return args, kwargs

def get_imagequery(value):
    if isinstance(value, ImageQuery):
        return value
    # value must be the path to an image or an image field (model attr)
    value = smart_unicode(value)
    return ImageQuery(value)

def imagequerify(func):
    from functools import wraps
    # Template-filters do not work without funcs that _need_ args
    # because of some inspect-magic (not) working here
    # TODO: Find some way to support optional "attr"
    @wraps(func)
    def newfunc(image, attr):
        try:
            image = get_imagequery(image)
        except IOError:
            return ''
        return func(image, attr)
    return newfunc

#@register.filter
#@imagequerify
#def resize(image, attr):
#   args, kwargs = parse_attrs(attr)
#   return image.resize(*args, **kwargs)
#
#@register.filter
#@imagequerify
#def scale(image, attr):
#   args, kwargs = parse_attrs(attr)
#   return image.scale(*args, **kwargs)
#
#@register.filter
#@imagequerify
#def unsharp(value, attr=None):
#   args, kwargs = parse_attrs(attr)
#   return image.unsharp(*args, **kwargs)
#
#@register.filter
#@imagequerify
#def grayscale(value):
#   return image.grayscale()
#
#@register.filter
#@imagequerify
#def blur(value):
#   return image.blur()
def imagequerify_filter(value):
    return get_imagequery(value)
register.filter('imagequerify', imagequerify_filter)

def imagequery_filter(method_name, filter_name=None):
    if not filter_name:
        filter_name = method_name
    def filter(image, attr=None):
        args, kwargs = parse_attrs(attr)
        return getattr(image, method_name)(*args, **kwargs)
    filter = imagequerify(filter)
    filter = register.filter(filter_name, filter)
    return filter


crop = imagequery_filter('crop')
fit = imagequery_filter('fit')
resize = imagequery_filter('resize')
scale = imagequery_filter('scale')
sharpness = imagequery_filter('sharpness')
blur = imagequery_filter('blur')
truecolor = imagequery_filter('truecolor')
invert = imagequery_filter('invert')
flip = imagequery_filter('flip')
mirror = imagequery_filter('mirror')
grayscale = imagequery_filter('grayscale')
offset = imagequery_filter('offset')
padding = imagequery_filter('padding')
opacity = imagequery_filter('opacity')
shadow = imagequery_filter('shadow')
makeshadow = imagequery_filter('makeshadow')
mimetype = imagequery_filter('mimetype')
width = imagequery_filter('width')
height = imagequery_filter('height')
x = imagequery_filter('x')
y = imagequery_filter('y')
size = imagequery_filter('size')
url = imagequery_filter('url')
query_name = imagequery_filter('query_name')




class EqualHeightNode(template.Node):
    def __init__(self, from_values, to_values, options):
        self.from_values = []
        self.to_values = to_values
        self.options = options
        for value in from_values:
            self.from_values.append(template.Variable(value))

    def render(self, context):
        try:
            import ipdb; ipdb.set_trace()
        except ImportError:
            pass
        maxwidth = int(self.options['maxwidth'])
        minheight = None # infinity
        from_values = []
        for value in self.from_values:
            try:
                value = value.resolve(context)
                if value:
                    value = get_imagequery(value)
                from_values.append(value)
            except template.VariableDoesNotExist:
                from_values.append(None)
        for i, value in enumerate(from_values):
            if not value:
                continue
            test_value = value.resize(x=maxwidth)
            if minheight is None or test_value.height() < minheight:
                minheight = test_value.height()
            from_values[i] = value
        for i, value in enumerate(from_values):
            if not value:
                context[self.to_values[i]] = value
            else:
                value = value.scale(x=maxwidth, y=minheight)
                context[self.to_values[i]] = value
        return ''


@register.tag
def equal_height(parser, token):
    '''
    Takes images and resizes them to the same height. You must pass an maxwidth
    argument. The resizing keeps the images' ratio.

    Usage:
        {% equal_height (variable as new_variable)?
            (and variable as new_variable)* maxwidth=[int] %}

    Example:
        {% equal_height image1 as newimage1 and image2 as newimage2 maxwidth=100 %}
    '''
    bits = token.split_contents()
    tag_name = bits[0]
    values = bits[1:-1]
    options = {}
    for option in bits[-1].split(','):
        key, value = option.split('=')
        options[key] = value
    from_value = []
    to_value = []
    for i,v in enumerate(values):
        i = ((i+1) % 4) or 4
        if i == 1:
            from_value.append(v)
        if i == 3:
            to_value.append(v)
        if (i == 4 and v != 'and') or (i == 2 and v != 'as'):
            raise template.TemplateSyntaxError(u'%r tag must look like {%% %r obj as obj2 and obj3 as obj4 ... %}.' % (tag_name, tag_name))
    if len(from_value) != len(to_value) or not from_value:
        raise template.TemplateSyntaxError(u'%r tag must look like {%% %r obj as obj2 and obj3 as obj4 ... %}.' % (tag_name, tag_name))
    if 'maxwidth' not in options:
        raise template.TemplateSyntaxError(u'%r tag must have an maxwidth option.' % tag_name)
    return EqualHeightNode(from_value, to_value, options)

