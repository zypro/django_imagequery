
class Format(object):
	# we don't allow passing filenames here, as this would need us to
	# repeat big parts of the storage-logic
	def __init__(self, imagequery):
		self._query = imagequery
	
	def execute(self, query):
		''' needs to be filled by derivates '''
		return query
	
	def _execute(self):
		try:
			return self._executed
		except AttributeError:
			self._executed = self.execute(self._query)
			return self._executed
	
	def name(self):
		return self._execute().name()
	
	def path(self):
		return self._execute().path()
	
	def url(self):
		try:
			return self._execute().url()
		except:
			return None # TODO: Do this right.
	
	def height(self):
		return self._execute().height()
	
	def width(self):
		return self._execute().width()


# examples:
#
#class AvatarFormat(Format):
#	def execute(self, query):
#		return query.scale(80, 80).query_name('avatar')
#
#class ThumbnailFormat(Format):
#	def execute(self, query):
#		return query.scale(200, 200).query_name('thumbnail')
#

