With ImageQuery you are able to write image manipulations without needing
to learn some low-level API for the most use cases. It allows you to:
 * simple manipulation like rescaling
 * combining images
 * handling text (note: fonts must be available locally)
 * even more like creating drop shadows (using the alpha mask)

ImageQuery basicly provides an API similar to the well known QuerySet API,
which means:
 * Most methods just return another ImageQuery
 * Every bit of your image manipulation chain can be used/saved
 * Image manipulations are lazy, they are only evaluated when needed

Some examples:

# load the image
iq = ImageQuery('some/file.png')
# scale it to 100x200 max
iq = iq.scale(100, 200)
iq.save('scaled/version.png')
# save the scaled version including a simple watermark
# note: this does not chenge "iq"
iq.paste('watermark.png', 'center', 'center').save('watermarked/version.png')
# create a grayscale version (without watermark of course)
iq = iq.grayscale()
iq.save('scaled_grayscale/version.png')

In addition ImageQuery provides some nice tools to make handling images
even more easy:
 * support for Django storage API
 * base class to manage multiple image formats
 * included template tags (using formats) and filters (lowlevel)
