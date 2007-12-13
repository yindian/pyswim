import os
import re
import sys
sys.path.append('..')

from django.http import *

from swim import *

SEARCH_BAR = """<script type="text/javascript">
function DoSearch(form)
{
top.location='/searchbar/?data='+form.data.value;
}
</script>
<form name="SearchForm" onSubmit="DoSearch(this.form)" method="get" action="/searchbar">
Search for
<input type="text" name="data" size="50">
<input type="button" value="Submit" onclick="DoSearch(this.form)">
<br>
<hr>
</form>
"""

def get_html(name):
    wiki = get_wiki(default_database_dir, default_articles_dir, name)
    if wiki:
        return parse_wiki(wiki)

def index(request):
    return article(request, "Wikipedia")

def article(request, article):
    result = "Not found"
    print "Searching for exact article", article
    html = get_html(article)
    if html:
        result = SEARCH_BAR + html
    else:
        return search(request, article)
    return HttpResponse(result)

def search(request, article, multi=False):
    if multi:
        print "Searching for keywords of article", article
        keywords = [i for i in article.lower().replace('_', ' ').split()]
    else:
        print "Searching for article", article
        keywords = [article]
    lines = search_articles(default_database_dir, keywords)
    if len(lines) == 0:
        result = """<html><head><title>Wikipedia has nothing about this.</title>
</head><body>Wikipedia has nothing about this.<br/>
You can keyword search about it <a href="/keyword/%s">here</a><br/><br/>
Or search otherelse:<br/>
%s
</body></html>""" % (article, SEARCH_BAR)
    else:
        result = """<html><head><title>Choose one</title>
</head><body><h1>Choose one of the options below</h1>
"""
        for rank, percent, docid, file, name in lines:
            result += '(%s) <A HREF="/article/%s">%s</A><br/>\n' % (percent,
                    name, name)
        result += "Or serch here: %s</body></html>" % SEARCH_BAR
    return HttpResponse(result)

def keyword(request, article):
    return search(request, article, multi=True)

def searchbar(request):
    searchData = request.GET['data']
    return keyword(request, searchData)
