# coding: utf-8
import os
import re
import sys
reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('..')

from django.http import *
from mwlib import cdbwiki

from swim import *

HEAD = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>%s</title>
<link rel="StyleSheet" href="/resources/main.css" type="text/css">
</head>
<body>
"""

TAIL = """</body>
</html>
"""

SEARCH_BAR = """<script type="text/javascript">
function DoSearch(form)
{
top.location='/searchbar/?data='+form.data.value;
}
</script>
<form name="SearchForm" onSubmit="DoSearch(this.form)" method="get" action="/searchbar">
Search for
<input type="text" name="data" size="50">
<input type="submit" value="Submit" onclick="DoSearch(this.form)">
<br>
<hr>
</form>
"""

def get_html(name):
    wiki = cdbwiki.WikiDB('..').getRawArticle(name)
    if wiki:
        return parse_wiki(name, wiki, make_math_png=True)

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
    return HttpResponse((HEAD % article) + result + TAIL)

def search(request, article, multi=False):
    if multi:
        print "Searching for keywords of article", article
        keywords = [i for i in article.lower().replace('_', ' ').split()]
    else:
        print "Searching for article", article
        keywords = [article]
    lines = search_articles(default_database_dir, keywords)
    if len(lines) == 0:
        result = """%s
Wikipedia has nothing about this.
You can keyword search about it <a href="/keyword/%s">here</a><br/><br/>
Or search otherelse:<br/>
%s
%s
""" % ((HEAD % 'Wikipedia has nothing about this.'),
        article, SEARCH_BAR, TAIL)
    else:
        result = """%s
<h1>Choose one of the options below</h1>
""" % (HEAD % 'Choose one')
        result += '<ul>\n'
        for rank, percent, docid, name in lines:
            result += '<li>(%s) <A HREF="/article/%s">%s</A></li>\n' % (
                    percent, name, name)
        result += '</ul>\n'
        result += "<br/>Or serch here: %s" % SEARCH_BAR
        result += TAIL
    return HttpResponse(result)

def keyword(request, article):
    return search(request, article, multi=True)

def searchbar(request):
    searchData = request.GET['data']
    return keyword(request, searchData)
