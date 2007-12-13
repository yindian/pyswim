#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bz2
import os
BASE = os.path.dirname(os.path.abspath(__file__))
import re
import sys
sys.path.append(BASE)
import urllib2
from xml.sax.saxutils import unescape
import StringIO

import xapian
from mwlib import uparser, htmlwriter

__version__ = '0.1'
user_agent = 'StaticWikiMirror/%s' % __version__
download_site = 'http://download.wikimedia.org/'
index_url = download_site + 'backup-index.html'
re_database_item = re.compile(
    r'<li>([\d-]{10} [\d:]{8}) <a href="([^"]*)">([^<]*)</a>.*Dump complete')
block_size = 8192
articles_per_file = 100
default_articles_dir = os.path.join(BASE, 'wiki-splits')
default_database_dir = os.path.join(BASE, 'db')

def open_url(url, resume=0):
    request = urllib2.Request(url)
    request.add_header('User-Agent', user_agent)
    if resume:
        request.add_header('Range', 'bytes=%d-' % resume)
    opener = urllib2.build_opener()
    file = opener.open(request)
    return file

def list_database():
    html = open_url(index_url).read()
    items = []
    for line in html.split('\n'):
        mo = re_database_item.findall(line)
        if mo:
            items.append(mo[0])
    print '%019s\t%s' % ('backup datetime', 'database')
    print '%019s\t%s' % ('='*19, '='*30)
    for i in sorted(items, key=lambda x: x[1]):
        print '%s\t%s' % (i[0], i[1])
    print '%019s\t%s' % ('='*19, '='*30)
    print '%019s\t%s' % ('backup datetime', 'database')
    print
    print 'Select one database to download.'

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
    except KeyboardInterrupt:
        print
        print 'user break'

class QuickIndex:
    def __init__(self, db_dir):
        self.db = xapian.WritableDatabase(db_dir, xapian.DB_CREATE_OR_OPEN)
        self.indexer = xapian.TermGenerator()
        stemmer = xapian.Stem("english")
        self.indexer.set_stemmer(stemmer)
        self.filename = ''

    def set_filename(self, filename):
        self.filename = filename

    def add_article(self, title):
        doc = xapian.Document()
        target = '%s:%s' % (self.filename, title)
        title = title.lower()
        doc.set_data(target)
        # 1st Source: the lowercased title
        doc.add_posting(title, 1)
        # 2nd source: All the title's lowercased words
        for i, word in enumerate(title.split(" /-_")):
            doc.add_posting(word, i+2)
        self.indexer.set_document(doc)
        self.indexer.index_text(target)
        self.db.add_document(doc)

def read_titles(wiki_dir):
    r = re.compile('<title>([^<]*)</title>')
    for filename in os.listdir(wiki_dir):
        if filename.startswith('rec') and filename.endswith('.bz2'):
            yield '#' + filename
            f = bz2.BZ2File(wiki_dir + '/' + filename)
            for line in f:
                mo = r.findall(line)
                if mo:
                    yield mo[0]

def index_all(db_dir, wiki_dir):
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    if not os.path.exists(wiki_dir):
        os.makedirs(wiki_dir)

    qi = QuickIndex(db_dir)
    total = 0
    try:
        for line in read_titles(wiki_dir):
            if line.startswith('#'):
                filename = line[1:]
                qi.set_filename(filename)
                continue
            #print line
            qi.add_article(line)
            total += 1
            if total % 1000 == 0:
                print total, "articles indexed so far"
        print total, "articles indexed so far"
    except StopIteration:
        pass

def split_articles(file, dir):
    if isinstance(file, basestring):
        file = bz2.BZ2File(file)
    if not os.path.exists(dir):
        os.makedirs(dir)

    i = j = 0
    def get_file(i):
        new_name = '%s/rec-%d.xml.bz2' % (dir, i)
        print new_name
        new_file = bz2.BZ2File(new_name, 'w')
        return new_name, new_file
    new_name, new_file = get_file(i)
    for line in file:
        new_file.write(line)
        if line.strip() == '</page>':
            j += 1
        if j > articles_per_file:
            i += 1
            j = 0
            new_file.close()
            new_name, new_file = get_file(i)
    new_file.close()

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
            data = data.strip('[]')
            file, name = data.split(':', 1)
            #print "%i: %i%% docid=%i [%s]" % (m[xapian.MSET_RANK] + 1,
            #    m[xapian.MSET_PERCENT], m[xapian.MSET_DID],
            #    m[xapian.MSET_DOCUMENT].get_data())
            #print "%i%% [%s]" % (m[xapian.MSET_PERCENT],
            #        m[xapian.MSET_DOCUMENT].get_data())
            ret.append([rank, percent, docid, file, name])
        return ret
    except Exception, e:
        print >> sys.stderr, "Exception: %s" % str(e)
        return []

def read_article(wiki_dir, file, name):
    wiki = _read_article(wiki_dir, file, name)
    return unescape(wiki)
    #return wiki

def _read_article(wiki_dir, file, name):
    f = bz2.BZ2File(os.path.join(wiki_dir, file))
    output = []
    line = f.readline()
    r = re.compile(r'<title>%s</title>' % re.escape(name))
    while line != '' and not r.findall(line):
        line = f.readline()
    tt = re.compile(r'<text[^>]*>(.*)</text>')
    tb = re.compile(r'<text[^>]*>(.*)')
    te = re.compile(r'(.*)</text>$')
    inside_text = False
    for x in range(2): # try another file only once
        while line != '':
            if not inside_text:
                mo = tt.findall(line)
                if mo:
                    output.append(mo[0])
                    return ''.join(output)
                mo = tb.findall(line)
                if mo:
                    output.append(mo[0])
                    inside_text = True
            else:
                while line != '':
                    mo = te.findall(line)
                    if mo:
                        output.append(mo[0])
                        return ''.join(output)
                    output.append(line)
                    line = f.readline()
            line = f.readline()
        # next file
        def inc(mo):
            index = int(mo.groups()[0])
            return "rec%05d" % (index + 1)
        file = re.sub(r'rec(\d{5})', inc, file)
        f = bz2.BZ2File(file)
        line = f.readline()
    return ''.join(output)

def parse_wiki(wiki):
    a = uparser.simpleparse(wiki.decode('utf8'))
    out = StringIO.StringIO()
    w = htmlwriter.HTMLWriter(out, None)
    w.write(a)
    return out.getvalue()

def get_wiki(db_dir, wiki_dir, name):
    ret = search_articles(db_dir, [name])
    if ret:
        rank, percent, docid, file, name = ret[0]
        return read_article(wiki_dir, file, name)
    return ''

def run():
    from optparse import OptionParser
    parser = OptionParser(version='%prog ' + __version__,
            usage="%prog [-dfisDLS] keywords...")
    parser.add_option('-L', '--list-databases', action='store_true',
            help='list databases can download')
    parser.add_option('-D', '--download-database', type='string',
            help='download a database, for example: enwiki/20071018')
    parser.add_option('-A', '--articles-dir', type='string',
            default=default_articles_dir,
            help='splitted articles files storage dir ARTICLES-DIR')
    parser.add_option('-S', '--split-articles', action='store_true',
            help='split articles backup files into dir ARTICLES-DIR')
    parser.add_option('-f', '--articles-file', type='string',
            help='backuped articles database file')
    parser.add_option('-i', '--index-all', action='store_true',
            help='index all xml article files in dir INDEX-ALL')
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

    # check
    if not options.articles_file and options.split_articles:
        parser.error('must give a database file with -f')
    if not args and options.search_articles:
        parser.error('must give some keywords')
    if not options.index_database and (options.index_all or
            options.search_articles or options.article_wiki or
            options.generate_html):
        parser.error('must give a index database dir with -d')
    if not options.articles_dir and (options.index_all or
            options.split_articles or options.article_wiki or
            options.generate_html):
        parser.error('must special a articles storage dir with -A')

    if options.list_databases:
        list_database()
    elif options.download_database:
        download_database(options.download_database)
    elif options.split_articles:
        split_articles(options.articles_file, options.articles_dir)
    elif options.index_all:
        index_all(options.index_database, options.articles_dir)
    elif options.search_articles:
        for rank, percent, docid, file, name in search_articles(
                options.index_database, args):
            print '%2d %s%% docid=%s file=%s [%s]' % (
                rank, percent, docid, file, name)
    elif options.article_wiki:
        print get_wiki(options.index_database, options.articles_dir,
                options.article_wiki)
    elif options.generate_html:
        wiki = get_wiki(options.index_database, options.articles_dir,
                options.generate_html)
        if wiki:
            print parse_wiki(wiki)
    else:
        parser.print_help()

if __name__ == '__main__':
    run()
