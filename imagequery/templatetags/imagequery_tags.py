from django import template
from imagequery import ImageQuery, format
from imagequery.utils import get_imagequery
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

# register all (/most of) the ImageQuery methods as filters
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


class ImageFormatNode(template.Node):
    def __init__(self, format, image, name):
        self.format = template.Variable(format)
        self.image = template.Variable(image)
        self.name = name

    def render(self, context):
        try:
            formatname = self.format.resolve(context)
            image = self.image.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        try:
            format_cls = format.get(formatname)
        except format.FormatDoesNotExist:
            return ''
        result = format_cls(get_imagequery(image))
        if self.name:
            context[self.name] = result
            return ''
        else:
            return result.url()


@register.tag
def image_format(parser, token):
    """
    Allows you to use predefined Format's for changing your images according to
    predefined sets of operations. Format's must be registered for using them
    here (using imagequery.format.register("name", MyFormat).
    
    You can get the resulting Format instance as a context variable.
    
    Examples:
    {% image_format "some_format" foo.image %}
    {% image_format "some_format" foo.image as var %}
    
    This tag does not support storage by design. If you want to use different
    storage engines here you have to:
     * pass in an ImageQuery instance
     * write your own template filter that constructs an ImageQuery instance
       (including storage settings)
     * pass in an FieldImage
    """
    bits = token.split_contents()
    tag_name = bits[0]
    values = bits[1:]
    if len(values) not in (2, 4):
        raise template.TemplateSyntaxError(u'%r tag needs two or four parameters.' % tag_name)
    format = values[0]
    image = values[1]
    name = None
    if len(values) == 5:
        if values[2] != 'as':
            raise template.TemplateSyntaxError(u'%r tag: third parameter must be "as"' % tag_name)
        name = values[3]
    return ImageFormatNode(format, image, name)

