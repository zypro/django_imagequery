import os
from django.test import TestCase
from django.conf import settings

import imagequery
import imagequery.query
from imagequery.query import ImageQuery


class ImageQueryTest(TestCase):
	def setUp(self):
		self.sample_dir = os.path.join(os.path.dirname(__file__), 'sampleimages')
		import tempfile
		self.tmp_dir = tempfile.mkdtemp()
		self.media_root = settings.MEDIA_ROOT
		settings.MEDIA_ROOT = self.tmp_dir

	def tearDown(self):
		settings.MEDIA_ROOT = self.media_root

	def sample(self, path):
		return os.path.join(self.sample_dir, path)
	def tmp(self, path):
		return os.path.join(self.tmp_dir, path)
	def compare(self, im1, im2):
		import hashlib
		f1hash = hashlib.md5()
		f1hash.update(file(im1).read())
		f2hash = hashlib.md5()
		f2hash.update(file(im2).read())
		return f1hash.hexdigest() == f2hash.hexdigest()

	def testLoading(self):
		import Image
		dj = ImageQuery(self.sample('django_colors.jpg'))
		dj.grayscale().save(self.tmp('test1.jpg'))
		dj2 = ImageQuery(Image.open(self.sample('django_colors.jpg')))
		dj2.grayscale().save(self.tmp('test2.jpg'))
		self.assert_(self.compare(self.tmp('test1.jpg'), self.tmp('test2.jpg')))
		blank = ImageQuery(x=100,y=100,color=(250,200,150,100))
		blank.save(self.tmp('test.png'))
		self.assert_(self.compare(self.tmp('test.png'), self.sample('results/blank_100x100_250,200,150,100.png')))

	def testOperations(self):
		dj = ImageQuery(self.sample('django_colors.jpg'))
		tux = ImageQuery(self.sample('tux_transparent.png'))
		lynx = ImageQuery(self.sample('lynx_kitten.jpg'))

		dj.grayscale().save(self.tmp('test.jpg'))
		self.assert_(self.compare(self.tmp('test.jpg'), self.sample('results/django_colors_gray.jpg')))

		dj.paste(tux, 'center', 'bottom').save(self.tmp('test.jpg'))
		self.assert_(self.compare(self.tmp('test.jpg'), self.sample('results/django_colors_with_tux_center_bottom.jpg')))

		lynx.mirror().flip().invert().resize(400,300).save(self.tmp('test.jpg'))
		self.assert_(self.compare(self.tmp('test.jpg'), self.sample('results/lynx_kitten_mirror_flip_invert_resize_400_300.jpg')))

		lynx.fit(400,160).save(self.tmp('test.jpg'))
		self.assert_(self.compare(self.tmp('test.jpg'), self.sample('results/lynx_fit_400_160.jpg')))

		tux_blank = tux.blank(color='#000088').save(self.tmp('test.png'))
		self.assert_(self.compare(self.tmp('test.png'), self.sample('results/tux_blank_000088.png')))
		self.assertEqual(tux.size(), tux_blank.size())

		lynx.resize(400).save(self.tmp('test.jpg'))
		lynx.resize(400).sharpness(3).save(self.tmp('test2.jpg'))
		lynx.resize(400).sharpness(-1).save(self.tmp('test3.jpg'))
		self.assert_(self.compare(self.tmp('test.jpg'), self.sample('results/lynx_resize_400.jpg')))
		self.assert_(self.compare(self.tmp('test2.jpg'), self.sample('results/lynx_resize_400_sharpness_3.jpg')))
		self.assert_(self.compare(self.tmp('test3.jpg'), self.sample('results/lynx_resize_400_sharpness_-1.jpg')))
		self.assert_(not self.compare(self.tmp('test.jpg'), self.tmp('test2.jpg')))

		tux.makeshadow(15, 10, '#444444').save(self.tmp('test.png'))
		self.assert_(self.compare(self.tmp('test.png'), self.sample('results/tux_shadow_15_10_444444.png')))
		tux.makeshadow(15, 10, '#444444', 0.7, 2.5).save(self.tmp('test.png'))
		self.assert_(self.compare(self.tmp('test.png'), self.sample('results/tux_shadow_15_10_444444_0.7_2.5.png')))

		dj.text('Django ImageQuery', 'center', 10, self.sample('../samplefonts/Vera.ttf'), 20, '#000000').save(self.tmp('test.jpg'))
		self.assert_(self.compare(self.tmp('test.jpg'), self.sample('results/django_colors_text_center_10.jpg')))

		self.assertEqual(dj.mimetype(), 'image/jpeg')
		self.assertEqual(tux.mimetype(), 'image/png')

	def testHashCalculation(self):
		dj = ImageQuery(self.sample('django_colors.jpg'))
		self.assertEqual(dj._name(), self.sample('django_colors.jpg'))
		dj1 = dj.scale(100,100)
		self.assertNotEqual(dj1._name(), dj._name())
		dj2 = ImageQuery(self.sample('django_colors.jpg')).scale(100,100)
		self.assertEqual(dj1._name(), dj2._name())
		self.assertNotEqual(dj._name(), dj2._name())
		dj3 = dj.scale(101,101)
		self.assertNotEqual(dj1._name(), dj3._name())
