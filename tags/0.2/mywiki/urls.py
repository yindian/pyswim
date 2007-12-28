import os
import sys
sys.path.append('..')

from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect
from swim import default_math_dir

def redirect(url):
    def inner(request):
        return HttpResponseRedirect(url)
    return inner

urlpatterns = patterns('',
    (r'^$', redirect('/article/Wikipedia')),
    (r'^searchbar/$', 'views.searchbar'),
    (r'^keyword/(?P<article>.+?)/?$', 'views.keyword'),
    (r'^search/(?P<article>.+?)/?$', 'views.search'),
    (r'^article/(?P<article>.+?)/?$', 'views.article'),
    (r'^pngmath/(?P<path>.*)/$', 'django.views.static.serve',
        {'document_root': os.path.join(default_math_dir, 'pngmath/')}),
    (r'^resources/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(default_math_dir, 'resources/')}),
)
