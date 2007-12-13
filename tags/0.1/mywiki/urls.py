import os

from django.conf.urls.defaults import *
from django.http import HttpResponseRedirect

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
        {'document_root': os.path.expanduser("~/pngmath/")}),
    (r'^images/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': '../mediawiki_sa/images/math'}),
)
