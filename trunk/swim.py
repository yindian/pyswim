#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bz2
import os
import re
import socket
import StringIO
import sys
import urllib2
from xml.sax.saxutils import unescape

import xapian
from mwlib import uparser, htmlwriter, rendermath, cdbwiki

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE)
reload(sys)
sys.setdefaultencoding('utf-8')
socket.setdefaulttimeout(3)

__version__ = '0.2'
user_agent = 'StaticWikiMirror/%s' % __version__
download_site = 'http://download.wikimedia.org/'
index_url = download_site + 'backup-index.html'
re_database_item = re.compile(
    r'<li>([\d-]{10} [\d:]{8}) <a href="([^"]*)">([^<]*)</a>.*Dump complete')
block_size = 8192
articles_per_file = 100
default_database_dir = os.path.join(BASE, 'db')
default_math_dir = BASE
default_wiki_dir = BASE

def open_url(url, resume=0):
    request = urllib2.Request(url)
    request.add_header('User-Agent', user_agent)
    if resume:
        request.add_header('Range', 'bytes=%d-' % resume)
    opener = urllib2.build_opener()
    file = opener.open(request)
    return file

def list_database():
    try:
        html = open_url(index_url).read()
    except:
        print 'Network error'
        return []
    items = []
    for line in html.split('\n'):
        mo = re_database_item.findall(line)
        if mo:
            items.append(mo[0])
    databases = sorted(items, key=lambda x: x[1])
    print '%019s\t%s' % ('backup datetime', 'database')
    print '%019s\t%s' % ('='*19, '='*30)
    for dt, database, name in databases:
        print '%s\t%s' % (dt, database)
    print '%019s\t%s' % ('='*19, '='*30)
    print '%019s\t%s' % ('backup datetime', 'database')
    print
    print 'Select one database to download.'
    return databases

def download_database(database):
    filename = '%s-pages-articles.xml.bz2' % database.replace('/', '-')
    url = '%s%s/%s' % (download_site, database, filename)
    if os.path.exists(filename):
        filesize = os.path.getsize(filename)
        u = open_url(url, resume=filesize)
        f = open(filename, 'a')
        i = filesize
    else:
        u = open_url(url)
        f = open(filename, 'w')
        i = 0
    size = 0
    size = int(u.headers['Content-Length'])
    print "downloading", url
    print "file: %s, size: %s" % (filename, size)
    if i:
        print 'resume: %s' % i
    data = u.read(block_size)
    try:
        while data:
            f.write(data)
            i += block_size
            sys.stdout.write('\r%s/%s %.2f%%' % (i, size, i*100.0/size))
            sys.stdout.flush()
            data = u.read(block_size)
        return filename
    except KeyboardInterrupt:
        print
        print 'user break'
        return filename

class QuickIndex:
    def __init__(self, db_dir):
        self.db = xapian.WritableDatabase(db_dir, xapian.DB_CREATE_OR_OPEN)
        self.indexer = xapian.TermGenerator()
        stemmer = xapian.Stem("english")
        self.indexer.set_stemmer(stemmer)

    def add_article(self, title):
        doc = xapian.Document()
        target = title
        doc.set_data(target)
        # 1st Source: the lowercased title
        title = title.lower()
        doc.add_posting(title, 1)
        # 2nd source: All the title's lowercased words
        for i, word in enumerate(title.split(" /-_")):
            doc.add_posting(word, i+2)
        self.indexer.set_document(doc)
        self.indexer.index_text(target)
        self.db.add_document(doc)

def index_all(wiki_file, db_dir):
    # build mwlib's wiki database: index and articles file
    d = cdbwiki.BuildWiki(wiki_file, default_wiki_dir)
    try:
        d()
    except SyntaxError:
        d.out.flush()
        d.cdb.finish()
        d.cdb.outfile.close()

    c = cdbwiki.WikiDB(default_wiki_dir)
    # build xapian index
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    qi = QuickIndex(db_dir)
    total = 0
    try:
        for key in c.cdb.keys():
            if key.startswith(':'):
                qi.add_article(key[1:])
            if key.startswith('T:'):
                qi.add_article('Template:'+key[2:])
            total += 1
            if total % 1000 == 0:
                print total, "articles indexed so far"
        print total, "articles indexed so far"
    except StopIteration:
        pass

def search_articles(db_dir, keywords):
    try:
        database = xapian.Database(db_dir)
        enquire = xapian.Enquire(database)
        query_string = keywords[0]
        for arg in keywords[1:]:
            query_string += ' '
            query_string += arg

        qp = xapian.QueryParser()
        stemmer = xapian.Stem("english")
        qp.set_stemmer(stemmer)
        qp.set_database(database)
        qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
        query = qp.parse_query(query_string)
        #print "Parsed query is: %s" % query.get_description()

        enquire.set_query(query)
        matches = enquire.get_mset(0, 10) # top 10

        # Display the results.
        #print "%i results found." % matches.get_matches_estimated()
        #print "Results 1-%i:" % matches.size()

        ret = []
        for m in matches:
            rank = m[xapian.MSET_RANK] + 1
            percent = m[xapian.MSET_PERCENT]
            docid = m[xapian.MSET_DID]
            data = m[xapian.MSET_DOCUMENT].get_data()
            #print "%i: %i%% docid=%i [%s]" % (m[xapian.MSET_RANK] + 1,
            #    m[xapian.MSET_PERCENT], m[xapian.MSET_DID],
            #    m[xapian.MSET_DOCUMENT].get_data())
            #print "%i%% [%s]" % (m[xapian.MSET_PERCENT],
            #        m[xapian.MSET_DOCUMENT].get_data())
            ret.append([rank, percent, docid, data])
        return ret
    except Exception, e:
        print >> sys.stderr, "Exception: %s" % str(e)
        return []

def xml_unescape(s):
    return unescape(s, entities={
        '&quot;': '"',
        })

def parse_wiki(name, wiki, make_math_png=False):
    c = cdbwiki.WikiDB(default_wiki_dir)
    a = uparser.parseString(name, raw=wiki, wikidb=c)
    out = StringIO.StringIO()
    mr = rendermath.Renderer(basedir=default_math_dir,
            lazy=(not make_math_png))
    w = htmlwriter.HTMLWriter(out, images=None, math_renderer=mr)
    w.write(a)
    return out.getvalue()

def get_wiki(name):
    c = cdbwiki.WikiDB(default_wiki_dir)
    wiki = c.getRawArticle(name)
    if wiki:
        return xml_unescape(wiki)
    else:
        return ''

def setup_wizard(file=None):
    print 'Setup wizard'
    print
    print 'Input a database name, to download it; or a articles.xml.bz2'
    print 'file path to reuse it. Press L to list databases avalialbe.'
    databases = []
    articles_file = None
    if (file is not None) and os.path.exists(file):
        articles_file = file
    while articles_file is None:
        database = raw_input('Input database name, or a downloaded filename'
            '(L to list databases): ')
        database = database.strip()
        if not database:
            continue
        if os.path.exists(database):
            articles_file = database
            break
        if database.upper() == 'L':
            databases = list_database()
            continue
        if re.match(r'\w+/\d{8}', database):
            print 'download database %s now...' % database
            articles_file = download_database(database)
            break
        find = [d for t,d,n in databases if d.startswith(database)]
        if len(find):
            database = find[0]
            print 'Do you mean this database: %s,' % database,
            a = raw_input('(Y/N): ')
            if a.strip().upper() != 'Y':
                database = ''
        else:
            print 'Not found this database in list.'
            a = raw_input('Forece download(Y/N): ')
            if a.strip().upper() != 'Y':
                database = ''
        if database:
                print 'download database %s now...' % database
                articles_file = download_database(database)
                break
    print
    print 'Do you want use this article file: %s, size: %d' % (
            articles_file, os.path.getsize(articles_file)),
    if (file is not None) and os.path.exists(file):
        a = 'Y'
        print '(Y/N): Y'
    else:
        a = raw_input('(Y/N): ')
    index_database = 'db'
    if a.upper() == 'Y':
        print 'index all articles now'
        index_all(articles_file, index_database)
    print
    print 'SWIM setup finished. Please run these commands to start up server:'
    print '  cd mywiki'
    print '  python manager.py runserver'

def run():
    from optparse import OptionParser
    parser = OptionParser(version='%prog ' + __version__,
            usage="%prog [-dfgisDLW] keywords...")
    parser.add_option('-W', '--setup-wizard', action='store_true',
            help='setup mirror using the wizard')
    parser.add_option('-L', '--list-databases', action='store_true',
            help='list databases can download')
    parser.add_option('-D', '--download-database', type='string',
            help='download a database, for example: enwiki/20071018')
    parser.add_option('-f', '--articles-file', type='string',
            help='backuped articles database file')
    parser.add_option('-i', '--index-all', action='store_true',
            help='index all xml articles in file ARTICLES-FILE')
    parser.add_option('-d', '--index-database', type='string',
            default=default_database_dir,
            help='xapian index database dir')
    parser.add_option('-s', '--search-articles', action='store_true',
            help='search articles')
    parser.add_option('-w', '--article-wiki', type='string',
            help="get article's wiki source")
    parser.add_option('-g', '--generate-html', type='string',
            help="generate article's html source code")
    (options, args) = parser.parse_args()

    if options.setup_wizard:
        try:
            file = args[0]
        except:
            file = None
        try:
            sys.exit(setup_wizard(file))
        except KeyboardInterrupt:
            print
            print 'user break'
            sys.exit(1)

    # check
    if not options.articles_file and options.index_all:
        parser.error('must give a database file with -f')
    if not args and options.search_articles:
        parser.error('must give some keywords')
    if not options.index_database and (options.index_all or
            options.search_articles or options.article_wiki or
            options.generate_html):
        parser.error('must give a index database dir with -d')

    if options.list_databases:
        list_database()
    elif options.download_database:
        download_database(options.download_database)
    elif options.index_all:
        index_all(options.articles_file, options.index_database)
    elif options.search_articles:
        for rank, percent, docid,  name in search_articles(
                options.index_database, args):
            print '%2d %s%% docid=%s [%s]' % (rank, percent, docid, name)
    elif options.article_wiki:
        print get_wiki(options.article_wiki)
    elif options.generate_html:
        wiki = get_wiki(options.generate_html)
        if wiki:
            print parse_wiki(options.generate_html, wiki)
    else:
        parser.print_help()

if __name__ == '__main__':
    run()
