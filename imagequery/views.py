from django.http import HttpResponseRedirect, Http404

def generate_lazy(request, pk):
    from imagequery.models import LazyFormat
    try:
        lazy_format = LazyFormat.objects.get(pk=pk)
    except LazyFormat.DoesNotExist:
        raise Http404()
    return HttpResponseRedirect(lazy_format.generate_image_url())

