import os
import Image
from django.conf import settings
from django.utils.encoding import smart_str


BASE_DIR = settings.MEDIA_ROOT
IMAGE_CACHE_DIR = getattr(settings, 'IMAGEQUERY_CACHE_DIR', 'cache')
# can be used to define quality
# IMAGEQUERY_DEFAULT_OPTIONS = {'quality': 92}
DEFAULT_OPTIONS = getattr(settings, 'IMAGEQUERY_DEFAULT_OPTIONS', None)

def get_image_object(value):
	if isinstance(value, ImageQuery):
		return value.raw()
	if isinstance(value, Image.Image):
		return value
	import ImageFile
	if isinstance(value, ImageFile.ImageFile):
		return value
	return Image.open(os.path.join(BASE_DIR, value))

def get_font_object(value, size=None):
	import ImageFont
	if isinstance(value, (ImageFont.ImageFont, ImageFont.FreeTypeFont)):
		return value
	if value[-4:].lower() in ('.ttf', '.otf'):
		return ImageFont.truetype(value, size)
	return ImageFont.load(value)

def get_coords(first, second, align):
	if align in ('left', 'top'):
		return 0
	if align in ('center', 'middle'):
		return (first / 2) - (second / 2)
	if align in ('right', 'bottom'):
		return first - second
	return align


# stores rendered images
# keys are hashes of image operations
import weakref
_IMAGE_REGISTRY = weakref.WeakKeyDictionary()

def _set_image_registry(item, image):
	_IMAGE_REGISTRY[item] = image
def _get_image_registry(item):
	return _IMAGE_REGISTRY.get(item, None)


# TODO: Einfach verkettete Liste ohne next, damit das copy klappt...
class QueryItem(object):
	def __init__(self, operation=None):
		self._previous = None
		self._evaluated_image = None
		self._name = None
		self.operation = operation

	def _get_previous(self):
		return self._previous
	def _set_previous(self, athor):
		prev = self._previous
		athor._previous = prev
		self._previous = athor
	previous = property(_get_previous, _set_previous)
	
	def __unicode__(self):
		return u', '.join([unicode(x.operation) for x in self.iter_previous()])
	
	def execute(self, image):
		evaluated_image = _get_image_registry(self)
		if evaluated_image is None:
			if self._previous is not None:
				image = self._previous.execute(image)
			if self.operation is not None:
				image = self.operation.execute(image, self)
			evaluated_image = image
			_set_image_registry(self, evaluated_image)
		return evaluated_image
	
	def get_attrs(self):
		attrs = {}
		if self._previous is not None:
			attrs.update(self._previous.get_attrs())
		if self.operation is not None:
			attrs.update(self.operation.attrs)
		return attrs
	
	def name(self, value=None):
		import hashlib
		if value:
			self._name = value
			return value
		if self._name:
			return self._name
		val = hashlib.sha1()
		altered = False
		item = self
		while item:
			if item._name: # stop on first named operation
				val.update(item._name)
				altered = True
				break
			if item.operation:
				val.update(unicode(item))
				altered = True
			item = item._previous
		if altered:
			return val.hexdigest()
		else:
			return None
	
	def get_first(self):
		first = self
		while first._previous is not None:
			first = first._previous
		return first


class Operation(object):
	args = ()
	args_defaults = {}
	attrs = {}

	def __init__(self, *args, **kwargs):
		allowed_args = list(self.args)
		allowed_args.reverse()
		for key in self.args_defaults:
			setattr(self, key, self.args_defaults[key])
		for value in args:
			assert allowed_args, 'too many arguments, only accepting %s arguments' % len(self.args)
			key = allowed_args.pop()
			setattr(self, key, value)
		for key in kwargs:
			assert key in allowed_args, '%s is not an accepted keyword argument' % key
			setattr(self, key, kwargs[key])

	def __unicode__(self):
		content = [self.__class__.__name__]
		args = '-'.join([str(getattr(self, key)) for key in self.args])
		if args:
			content.append(args)
		return '_'.join(content)

	def execute(self, image, query):
		return image


class DummyOperation(Operation):
	pass


class CommandOperation(Operation):
	def file_operation(self, image, query, command):
		import tempfile, subprocess
		suffix = '.%s' % os.path.basename(query.source).split('.', -1)[1]
		whfile, wfile = tempfile.mkstemp(suffix)
		image.save(wfile)
		rhfile, rfile = tempfile.mkstemp(suffix)
		proc = subprocess.Popen(command % {'infile': wfile, 'outfile': rfile}, shell=True)
		proc.wait()
		image = Image.open(rfile)
		return image


class Enhance(Operation):
	args = ('enhancer', 'factor')

	def execute(self, image, query):
		enhancer = self.enhancer(image)
		return enhancer.enhance(self.factor)


class Resize(Operation):
	args = ('x', 'y', 'filter')
	args_defaults = {
		'x': None,
		'y': None,
		'filter': Image.ANTIALIAS,
	}

	def execute(self, image, query):
		if self.x is None and self.y is None:
			self.x, self.y = image.size
		elif self.x is None:
			orig_x, orig_y = image.size
			ratio = float(self.y) / float(orig_y)
			self.x = int(orig_x * ratio)
		elif self.y is None:
			orig_x, orig_y = image.size
			ratio = float(self.x) / float(orig_x)
			self.y = int(orig_y * ratio)
		return image.resize((self.x, self.y), self.filter)


class Scale(Operation):
	args = ('x', 'y', 'filter')
	args_defaults = {
		'filter': Image.ANTIALIAS,
	}

	def execute(self, image, query):
		image = image.copy()
		image.thumbnail((self.x, self.y), self.filter)
		return image


class Invert(Operation):
	args = ('keep_alpha',)
	def execute(self, image, query):
		import ImageChops
		if self.keep_alpha:
			image = image.convert('RGBA')
			channels = list(image.split())
			for i in xrange(0, 3):
				channels[i] = ImageChops.invert(channels[i])
			return Image.merge('RGBA', channels)
		else:
			return ImageChops.invert(image)


class Grayscale(Operation):
	def execute(self, image, query):
		import ImageOps
		return ImageOps.grayscale(image)


class Flip(Operation):
	def execute(self, image, query):
		import ImageOps
		return ImageOps.flip(image)


class Mirror(Operation):
	def execute(self, image, query):
		import ImageOps
		return ImageOps.mirror(image)


class Blur(Operation):
	args = ('amount',)
	def execute(self, image, query):
		import ImageFilter
		for i in xrange(0, self.amount):
			image = image.filter(ImageFilter.BLUR)
		return image


class Filter(Operation):
	args = ('filter',)
	def execute(self, image, query):
		return image.filter(self.filter)


class Crop(Operation):
	args = ('x', 'y', 'w', 'h')
	def execute(self, image, query):
		box = (
			self.x,
			self.y,
			self.x + self.w,
			self.y + self.h,
		)
		return image.crop(box)


class Fit(Operation):
	args = ('x', 'y', 'centering', 'method')
	args_defaults = {
		'method': Image.ANTIALIAS,
		'centering': (0.5, 0.5),
	}
	def execute(self, image, query):
		import ImageOps
		return ImageOps.fit(image, (self.x, self.y), self.method, centering=self.centering)


class Blank(Operation):
	args = ('x','y','color','mode')
	args_defaults = {
		'x': None,
		'y': None,
		'color': None,
		'mode': 'RGBA',
	}
	def execute(self, image, query):
		x, y = self.x, self.y
		if x is None:
			x = image.size[0]
		if y is None:
			y = image.size[1]
		if self.color:
			return Image.new(self.mode, (x, y), self.color)
		else:
			return Image.new(self.mode, (x, y))


class Paste(Operation):
	args = ('image','x','y')
	def execute(self, image, query):
		athor = get_image_object(self.image)
		x2, y2 = athor.size
		x1 = get_coords(image.size[0], athor.size[0], self.x)
		y1 = get_coords(image.size[1], athor.size[1], self.y)
		box = (
			x1,
			y1,
			x1 + x2,
			y1 + y2,
		)
		# Note that if you paste an "RGBA" image, the alpha band is ignored.
		# You can work around this by using the same image as both source image and mask.
		image = image.copy()
		if athor.mode == 'RGBA':
			if image.mode == 'RGBA':
				import ImageChops
				channels = image.split()
				alpha = channels[3]
				image = Image.merge('RGB', channels[0:3])
				athor_channels = athor.split()
				athor_alpha = athor_channels[3]
				athor = Image.merge('RGB', athor_channels[0:3])
				image.paste(athor, box, mask=athor_alpha)
				# merge alpha
				athor_image_alpha = Image.new('L', image.size, color=0)
				athor_image_alpha.paste(athor_alpha, box)
				new_alpha = ImageChops.add(alpha, athor_image_alpha)
				image = Image.merge('RGBA', image.split() + (new_alpha,))
			else:
				image.paste(athor, box, mask=athor)
		else:
			image.paste(athor, box)
		return image


class Background(Operation):
	args = ('image','x','y')
	def execute(self, image, query):
		background = Image.new('RGBA', image.size, color=(0,0,0,0))
		athor = get_image_object(self.image)
		x2,y2 = image.size
		x1 = get_coords(image.size[0], athor.size[0], self.x)
		y1 = get_coords(image.size[1], athor.size[1], self.y)
		box = (
			x1,
			y1,
			x1 + x2,
			y1 + y2,
		)
		background.paste(athor, box, mask=athor)
		background.paste(image, None, mask=image)
		return background


class Convert(Operation):
	args = ('mode', 'matrix')
	args_defaults = {
		'matrix': None,
	}
	def execute(self, image, query):
		if self.matrix:
			return image.convert(self.mode, self.matrix)
		else:
			return image.convert(self.mode)


class GetChannel(Operation):
	args = ('channel',)
	channel_map = {
		'red': 0,
		'green': 1,
		'blue': 2,
		'alpha': 3,
	}
	def execute(self, image, query):
		image = image.convert('RGBA')
		alpha = image.split()[self.channel_map[self.channel]]
		return Image.merge('RGBA', (alpha, alpha, alpha, alpha))


class ApplyAlpha(GetChannel):
	args = ('alphamap',)
	def execute(self, image, query):
		# TODO: Use putalpha(band)?
		image = image.convert('RGBA')
		alphamap = get_image_object(self.alphamap).convert('RGBA')
		data = image.split()[self.channel_map['red']:self.channel_map['alpha']]
		alpha = alphamap.split()[self.channel_map['alpha']]
		alpha = alpha.resize(image.size, Image.ANTIALIAS)
		return Image.merge('RGBA', data + (alpha,))


class Blend(Operation):
	args = ('image','alpha')
	channel_map = {
		'alpha': 0.5,
	}
	def execute(self, image, query):
		athor = get_image_object(self.image)
		return Image.blend(image, athor, self.alpha)


class Text(Operation):
	args = ('text','x','y','font','size','fill')
	args_defaults = {
		'size': None,
		'fill': None,
	}
	def execute(self, image, query):
		image = image.copy()
		import ImageDraw
		font = get_font_object(self.font, self.size)
		size, offset = ImageQuery.img_textbox(self.text, self.font, self.size)
		x = get_coords(image.size[0], size[0], self.x) + offset[0]
		y = get_coords(image.size[1], size[1], self.y) + offset[1]
		draw = ImageDraw.Draw(image)
		text = self.text
		# HACK
		if Image.VERSION == '1.1.5' and isinstance(text, unicode):
			text = text.encode('utf-8')
		draw.text((x, y), text, font=font, fill=self.fill)
		return image


# TODO: enhance text operations

class TextImage(Operation):
	args = ('text', 'font', 'size', 'mode')
	args_defaults = {
		'size': None,
		'fill': None,
	}
	def execute(self, image, query):
		font = get_font_object(self.font, self.size)
		font.getmask(self.text)


class FontDefaults(Operation):
	args = ('font', 'size', 'fill')

	@property
	def attrs(self):
		return {
			'font': self.font,
			'size': self.size,
			'fill': self.fill,
		}


class Composite(Operation):
	args = ('image','mask')
	def execute(self, image, query):
		athor = get_image_object(self.image)
		mask = get_image_object(self.mask)
		return Image.composite(image, athor, mask)


class Offset(Operation):
	args = ('x','y')
	def execute(self, image, query):
		import ImageChops
		return ImageChops.offset(image, self.x, self.y)


class Padding(Operation):
	args = ('left','top','right','bottom','color')
	def execute(self, image, query):
		left, top, right, bottom = self.left, self.top, self.right, self.bottom
		color = self.color
		if top is None:
			top = left
		if right is None:
			right = left
		if bottom is None:
			bottom = top
		if color is None:
			color = (0,0,0,0)
		new_width = left + right + image.size[0]
		new_height = top + bottom + image.size[1]
		new = Image.new('RGBA', (new_width, new_height), color=color)
		new.paste(image, (left, top))
		return new


class Opacity(Operation):
	args = ('opacity',)
	def execute(self, image, query):
		opacity = int(self.opacity * 255)
		background = Image.new('RGBA', image.size, color=(0,0,0,0))
		mask = Image.new('RGBA', image.size, color=(0,0,0,opacity))
		box = (0,0) + image.size
		background.paste(image, box, mask)
		return background


class Clip(Operation):
	args = ('start','end',)
	args_defaults = {
		'start': None,
		'end': None,
	}
	def execute(self, image, query):
		start = self.start
		if start is None:
			start = (0, 0)
		end = self.end
		if end is None:
			end = image.size
		new = image.crop(self.start + self.end)
		new.load() # crop is a lazy operation, see docs
		return new


class ImageQuery(object):
	def __init__(self, image=None, query=None, x=None, y=None, color=(0,0,0,0)):
		assert (image and not x and not y) or (not image and x and y)
		if image:
			import ImageFile
			if isinstance(image, ImageQuery):
				athor = image
				self.source = athor.source
				self.image = athor.image
				query = athor.query
			elif isinstance(image, ImageFile.ImageFile):
				self.image = image.copy()
				self.source = image.filename
			elif isinstance(image, Image.Image):
				self.image = image.copy()
				self.source = None
			else:
				# assume that image is a filename
				self.source = smart_str(image)
				self.image = Image.open(os.path.join(BASE_DIR, self.source))
		else:
			self.image = Image.new('RGBA', (x, y), color)
			self.source = None
		if query:
			import copy
			self.query = copy.copy(query)
		else:
			self.query = QueryItem()
		self.query.source = self.source

	def _basename(self):
		if self.source:
			return os.path.basename(self.source)
		else:
			# the image was not loaded from source. create a random name
			# TODO: Use md5 of contents, so we don't flood the cache
			import datetime, random
			CHOICES = '0123456789abcdef'
			name = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
			random_name = ''
			while len(random_name) < 8:
				random_name += random.choice(CHOICES)
			name += '-' + random_name
			return '%s.png' % name

	def _name(self):
		hashval = self.query.name()
		if hashval:
			if not self.source or self.source.startswith('/'): # TODO: Support windows?
				return os.path.join(IMAGE_CACHE_DIR, hashval, self._basename())
			else:
				return os.path.join(IMAGE_CACHE_DIR, hashval, self.source)
		else:
			return self.source

	def _source(self):
		if self.source:
			return os.path.join(BASE_DIR, self.source)

	def _path(self):
		if self.source:
			return os.path.join(BASE_DIR, self._name())

	def _url(self):
		return os.path.join(settings.MEDIA_URL, self._name())

	def _exists(self):
		if self.source and \
			os.path.exists(self._path()) and not ( \
				os.path.exists(self._source()) and \
				os.path.getmtime(self._source()) > os.path.getmtime(self._path()) \
			):
				return True
		return False

	def _apply_operations(self, image):
		image = self.query.execute(image)
		return image

	def _create_raw(self):
		if self._exists(): # Load existing image if possible
			# TODO: Check if this has side-effects!
			path = os.path.join(BASE_DIR, self._path())
			return Image.open(path)
		return self._apply_operations(self.image)

	def _create(self, name=None, **options):
		'''
		Recreate image. Does not check whether the image already exists.
		'''
		if self.query:
			if name is None:
				name = self._path()
			name = smart_str(name)
			image = self._create_raw()
			path = os.path.join(BASE_DIR, name)
			pathdir = os.path.dirname(path)
			if not os.path.exists(pathdir):
				os.makedirs(pathdir)
			if DEFAULT_OPTIONS:
				save_options = DEFAULT_OPTIONS.copy()
			else:
				save_options = {}
			save_options.update(options)
			# options may raise errors
			# TODO: Check this
			try:
				image.save(path, None, **save_options)
			except TypeError:
				image.save(path)

	def _clone(self):
		return ImageQuery(self)

	def _evaluate(self):
		if not self._exists():
			self._create()
	
	def _append(self, query):
		append_query = QueryItem(athor)
		append_query._previous = self.query
		self.query = append_query
		return self

	def __unicode__(self):
		return self.url()

	def __repr__(self):
		return '<ImageQuery %s> ' % self._name()

	########################################
	# Query methods ########################
	########################################

	def blank(self,x=None,y=None,color=None):
		q = self._clone()
		q = q._append(Blank(x,y,color))
		return q

	def paste(self, image, x=0, y=0):
		'''
		Pastes the given image above the current one.
		'''
		q = self._clone()
		q = q._append(Paste(image,x,y))
		return q

	def background(self, image, x=0, y=0):
		'''
		Same as paste but puts the given image behind the current one.
		'''
		q = self._clone()
		q = q._append(Background(image,x,y))
		return q

	def blend(self, image, alpha=0.5):
		q = self._clone()
		q = q._append(Blend(image,alpha))
		return q

	def resize(self, x=None, y=None, filter=Image.ANTIALIAS):
		q = self._clone()
		q = q._append(Resize(x,y,filter))
		return q

	def scale(self, x, y, filter=Image.ANTIALIAS):
		q = self._clone()
		q = q._append(Scale(x,y,filter))
		return q

	def crop(self, x, y, w, h):
		q = self._clone()
		q = q._append(Crop(x,y,w,h))
		return q

	def fit(self, x, y, centering=(0.5,0.5), method=Image.ANTIALIAS):
		q = self._clone()
		q = q._append(Fit(x,y,centering,method))
		return q

	def enhance(self, enhancer, factor):
		q = self._clone()
		q = q._append(Enhance(enhancer, factor))
		return q

	def sharpness(self, amount=2.0):
		'''
		amount: 
			< 1 makes the image blur
			1.0 returns the original image
			> 1 increases the sharpness of the image
		'''
		import ImageEnhance
		return self.enhance(ImageEnhance.Sharpness, amount)

	def blur(self, amount=1):
		#return self.sharpness(1-(amount-1))
		q = self._clone()
		q = q._append(Blur(amount))
		return q

	def filter(self, image_filter):
		q = self._clone()
		q = q._append(Filter(image_filter))
		return q
	
	def truecolor(self):
		q = self._clone()
		q = q._append(Convert('RGBA'))
		return q

	def invert(self, keep_alpha=True):
		q = self._clone()
		q = q._append(Invert(keep_alpha))
		return q

	def flip(self):
		q = self._clone()
		q = q._append(Flip())
		return q

	def mirror(self):
		q = self._clone()
		q = q._append(Mirror())
		return q

	def grayscale(self):
		q = self._clone()
		q = q._append(Grayscale())
		return q

	def alpha(self):
		q = self._clone()
		q = q._append(GetChannel('alpha'))
		return q

	def applyalpha(self, alphamap):
		q = self._clone()
		q = q._append(ApplyAlpha(alphamap))
		return q

	def text(self, text, x, y, font, size=None, fill=None):
		q = self._clone()
		q = q._append(Text(text, x, y, font, size, fill))
		return q

	@staticmethod
	def textbox(text, font, size=None):
		font = get_font_object(font, size)
		return font.getsize(text)

	@staticmethod
	def img_textbox(text, font, size=None):
		font = get_font_object(font, size)
		try:
			imgsize, offset = font.font.getsize(text)
			if isinstance(imgsize, int) and isinstance(offset, int):
				imgsize = (imgsize, offset)
				offset = (0, 0)
		except AttributeError:
			imgsize = font.getsize(text)
			offset = (0, 0)
		return (
			imgsize[0] - offset[0],
			imgsize[1] - offset[1],
		), (
			-offset[0],
			-offset[1],
		)

	@staticmethod
	def textimg(text, font, size=None, fill=None, padding=0, mode='RGBA'):
		import ImageDraw
		font = get_font_object(font, size)
		imgsize, offset = ImageQuery.img_textbox(text, font, size)
		bg = [0,0,0,0]
		# Workaround: Image perhaps is converted to RGB before pasting,
		# black background draws dark outline around text
		if fill:
			for i in xrange(0, min(len(fill), 3)):
				bg[i] = fill[i]
		if padding:
			imgsize = (imgsize[0] + padding * 2, imgsize[1] + padding * 2)
			offset = (offset[0] + padding, offset[1] + padding)
		fontimage = Image.new(mode, imgsize, tuple(bg))
		draw = ImageDraw.Draw(fontimage)
		# HACK
		if Image.VERSION == '1.1.5' and isinstance(text, unicode):
			text = text.encode('utf-8')
		draw.text(offset, text, font=font, fill=fill)
		return ImageQuery(fontimage)

	def composite(self, image, mask):
		q = self._clone()
		q = q._append(Composite(image, mask))
		return q

	def offset(self, x, y):
		q = self._clone()
		q = q._append(Offset(x, y))
		return q

	def padding(self, left, top=None, right=None, bottom=None, color=None):
		q = self._clone()
		q = q._append(Padding(left, top, right, bottom, color))
		return q

	def opacity(self, opacity):
		q = self._clone()
		q = q._append(Opacity(opacity))
		return q

	def clip(self, start=None, end=None):
		q = self._clone()
		q = q._append(Clip(start, end))
		return q

	def shadow(self, color):
		#mask = self.alpha().invert()
		#return self.blank(color=None).composite(self.blank(color=color), mask)
		return self.blank(color=color).applyalpha(self)

	def makeshadow(self, x, y, color, opacity=1, blur=1):
		shadow = self.shadow(color).opacity(opacity).blur(blur)
		return self.background(shadow, x, y)

	def save(self, name=None, **options):
		self._create(name, **options)
		q = self._clone()
		return q

	def query_name(self, value):
		q = self._clone()
		q = q._append(None)
		q.query.name(value)
		return q

	# methods which does not return a new ImageQuery instance
	def mimetype(self):
		format = self.raw().format
		try:
			return Image.MIME[format]
		except KeyError:
			return None

	def width(self):
		return self.raw().size[0]
	x = width

	def height(self):
		return self.raw().size[1]
	y = height

	def size(self):
		return self.raw().size

	def raw(self):
		return self._create_raw()

	def name(self):
		self._evaluate()
		return self._name()

	def path(self):
		self._evaluate()
		return self._path()

	def url(self):
		self._evaluate()
		return self._url()

