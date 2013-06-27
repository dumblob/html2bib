#!/usr/bin/env python3

# Author: Jan Pacner xpacne00@stud.fit.vutbr.cz
# Date:   2013-03-07 12:42:41 CET

# FIXME presentation
#   kazdy autor cituje jinak
#   vetsina nastroju kasle na "pretty print", takze zdvojene znaky bezna zalezitost
#   >95% citaci obsahuje alespon jednu zasadni chybu, ktera znemoznuje
#     pouzit univerzalni regex nebo parse/pattern
#     viz. tistena zadani BP, to myslim mluvi za vse
#   python regex engine nove generace stoji za starou backoru :)
#   dalsim cilem bylo, aby program okamzite skoncil srozumitelnou chybou v
#     pripade chyby - tzn. vyuziti exceptions pro programatorske chyby,
#     vyuziti locals() apod.

# XPath cheatsheet
#   "//table/tr/td[not(@*) and position()>1]"
#   "node-name(*)!='img'"

# NOTE
# Python does not yet (!) support "extended" unicode regex handling like
#   lowercase matching with \p{} and therefore while using the `re' module,
#   some input items are not parsed correctly and produce nonsensical
#   BibTeX results.
#   Therefore the default module for regexp handling is `regex', which
#   should become the default regexp module in later python 3.3 versions.

import os
import sys
#import re
import regex as re
from lxml.html import parse, etree
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape

BIBTEXML_HEADER = \
"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE bibtex:file PUBLIC
    "-//BibTeXML//DTD XML for BibTeX v1.0//EN"
    "bibteXML.dtd">
<bibtex:file xmlns:bibtex="http://bibtexml.sf.net/">
"""
BIBTEXML_FOOTER = '</bibtex:file>'

# BibTeX: ' and '; BibTeXML: '; '
AUTHOR_JOIN = '; '

# 'profile': {'xpath': "XPath", 'url': 'already_normalized_URL'}
db = {
  'hermansky': {
    'xpath': "//div[@id='publications-container']/h3 | //div[@class='publications']",
    'url': 'http://www.clsp.jhu.edu/publications/author/hynek-hermansky' },
  'zendulka': {
    'xpath': "//table[@id='contenttable']/tr/td/table/tr/td/a",
    #FIXME etree.parse() https support?
    'url': 'http://www.fit.vutbr.cz/~zendulka/pubs.php.en' },
  'assaleh': {
    'xpath': "//div[@class='bibtex']/code",
    'url': 'http://tony.abou-assaleh.net/publications' },
  'ladamic': {
    'xpath': "/html/body/table/tr/td/" +
             "table/tr/td/" +
             "table/tr/td/" +
             "table/tr/td/div[@class='item']/*",
    'url': 'http://www-personal.umich.edu/~ladamic' },
  'cond': {
    'xpath': "/html/body/center/table[@width]/tr[not(@*)]/" +
             "td[@colspan and count(@*)=1 and count(*)=1 and not(child::img)]",
    'url': 'http://www.cond.org' },
  'janal': {
    'xpath': "/html/body/ul[position()=1]",
    'url': 'http://www.dfki.de/~janal/publications.html' },
  'alcazar': {
    'xpath': "/html/body/div[@class='Section1']",
    #'xpath': "/html/head/" +
             # 11x smarttagtype (because of lxml bad parsing)
             #"smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/smarttagtype/" +
             # yes, you see it right - lxml puts <body> into <head>
             #"body/div[@class='Section1']",
    'url': 'http://www-scf.usc.edu/~alcazar' },
  'argitalpenak': {
    'xpath': "//div[@class='core_text']",
    'url': 'http://ixa.si.ehu.es/ixa/argitalpenak/kidearen_argitalpenak?kidea=1000808989' },
  'james': {
    'xpath': "//div[@class='Section1']",
    'url': 'http://www.cs.rochester.edu/u/james' },
  'alonso': {
    'xpath': "//ul[not(@*)]/li[not(@*)]/a[@href]",
    'url': 'http://www.dc.fi.udc.es/~alonso/papers.html' },
}

# order matters (used for printing)
bibtex_allowed = ('author', 'title', 'school', 'institution', 'booktitle',
    'chapter', 'publisher', 'journal', 'year', 'address', 'note', 'abstract')

# escape() and unescape() takes care of & < >
xml_escape_table = {
  '"': '&quot;',
  "'": '&apos;',
}

arg = {
  'o':   None,  # file_descriptor | stdout
  'p':   None,
  'l':   None,
  'x':   None,
  'b':   None,
  'url': None,
}

def err_exit (msg = 'Unknow error occured.', ret = 1):
  print(msg, 'Use -h for help.', file = sys.stderr)
  sys.exit(ret)  # clean everything including file handles etc.

# nasty hack with mutable type to mimic "static" var
def printw(*abc, __my_state=[1], **xyz):
  """print() wrapper"""

  if __my_state[0]:
    print(BIBTEXML_HEADER, file = arg['o'])
    __my_state[0] = 0
  xyz['file'] = arg['o']
  print(*abc, **xyz)

# indexing needed for double/triple/... arguments
i = 1
while i < len(sys.argv):
  p = sys.argv[i]

  if p in ('-h', '--help'):
    if len(sys.argv) != 2:
      err_exit('Argument mismatch.')
    print("USAGE:\n\t" + sys.argv[0] + " [OPTIONS] -p <profile> <URL>\n" +
"""OPTIONS
\t-h --help
\t    this help
\t-o --output <file>
\t    optional output file (use stdout if -o not given)
\t-p --profile <profile>
\t    select profile; mandatory if URL not already known (see -l)
\t-l --list-profiles
\t    list available profiles in format 'name\\n\\tXPath_prefix\\n\\tdefault_URL'
\t-x --xpath-prefix <prefix>
\t    set XPath pointing to root nodes where to start an attempt to match
\t      the bibliography tree; this overwrites the profile default one
\t-b --beautiful-output
\t    output beautifully reformatted input HTML (useful e.g. for finding
\t      the right XPath etc.)
""")
    sys.exit(0)
  elif p in ('-o', '--output'):
    i += 1
    try:
      arg['o'] = open(sys.argv[i], 'w')
    except:  # catch all exceptions
      err_exit('Error while opening output file.')
  elif p in ('-p', '--profile'):
    i += 1
    arg['p'] = sys.argv[i]
  elif p in ('-l', '--list-profiles'):
    if len(sys.argv) != 2 and len(sys.argv) != 4:  # optional -o
      err_exit('Argument mismatch.')
    arg['l'] = True
  elif p in ('-x', '--xpath-prefix'):
    i += 1
    arg['x'] = sys.argv[i]
  elif p in ('-b', '--beautiful-output'):
    if len(sys.argv) != 3 and len(sys.argv) != 5:  # optional -o; mandatory URL
      err_exit('Argument mismatch.')
    arg['b'] = True
  elif i == len(sys.argv) -1:
    # cut off reference (leave the rest including GET values as they are)
    a, _, c = p.rpartition('#')
    if _:
      arg['url'] = a.rstrip('/')
    else:
      arg['url'] = p.rstrip('/')
  else:
    err_exit('Unknown argument ' + p)
  i += 1

if arg['l']:
  """handle --list-profiles argument"""

  if len(sys.argv) == 4 and not arg['o']:
    err_exit('Argument mismatch.')
  for x in db:
    printw(x)
    printw('\t' + db[x]['xpath'])
    printw('\t' + db[x]['url'])
  sys.exit(0)

if not arg['url']:
  err_exit('Missing URL.')

# beautiful print will be handled after html parsing
if arg['b']:
  if len(sys.argv) == 5 and not arg['o']:
    err_exit('Argument mismatch.')
else:
  if arg['p']:
    if not arg['p'] in db:
      err_exit('Uknown profile.')
  else:
    # try to find matching profile
    for x in db:
      if arg['url'].lower() == db[x]['url']:
        arg['p'] = x
        break
    else:
      err_exit('Please choose profile for the given URL.')
  if not arg['x']:
    arg['x'] = db[arg['p']]['xpath']

if not arg['o']:
  arg['o'] = sys.stdout

try:
  tree = parse(arg['url'])
  #parser = etree.HTMLParser()
  #tree = etree.parse(arg['url'], parser)
except:
  # should not be raised if only some minor HTML errors occur
  err_exit('Unable to parse the given HTML document.')

if arg['b']:
  """handle --beautiful-output argument"""

  # nasty solution, but we need the "cleaned" version (i.e. the
  #   lxml-specific one) of HTML tree
  printw(BeautifulSoup(
    etree.tostring(tree.getroot(), method='html') ).prettify())
  sys.exit(0)

# precompile regexps
eres = {
  'url': re.compile('^(http://)?www[.]', re.IGNORECASE),
  'trail_space': re.compile('\\s*$'),
  'lead_space': re.compile('^\\s*'),
  'whole_blank': re.compile('^\\s*$'),
  'blank': re.compile('[\\s\u00a0]+'),  # \u00a0 == nbsp
  'url_hex': re.compile('(%[A-F0-9]{2}|\\+)+'),
  'year4': re.compile('[(]\\s*([12][0-9][0-9][0-9])\\s*[)]'),
  'year2': re.compile('[(]\\s*([01][0-9])\\s*[)]'),
  'year4r': re.compile('[(]\\s*([12][0-9][0-9][0-9])(?!.*?[12][0-9][0-9][0-9])\\s*[)]'),
  'year2r': re.compile('[(]\\s*([01][0-9])(?!.*?[01][0-9])\\s*[)]'),
  'year4r_no_paren': re.compile('\\s*([12][0-9][0-9][0-9])(?!.*?[12][0-9][0-9][0-9])\\s*'),
  'year2r_no_paren': re.compile('\\s*([01][0-9])(?!.*?[01][0-9])\\s*'),
  'clean_start': re.compile('^[·.:;, \t\f\n\'"`]+'),
  'clean_end': re.compile('[.:;, \t\f\n\'"`]+$'),
  'clean_author': re.compile('^[\\s.;,]+'),
  'author_join_start': re.compile('^\\s*and\\s+'),
  'author_join_end': re.compile('\\s+and\\s*$'),
  'nonlatinchar': re.compile('[^a-zA-Z]'),
  'author': re.compile('^((and|[Ww]ith)\\s+)?' +
    # NOTE causes "try all possible combinations" behaviour of the
    #   regex engine, see grep_author_note() for details
    #'(?!(' + FORBIDDEN_NAMES + '))' +
    # allow max 2 consecutive uppercase letters
    '(?!\\p{Lu}{3,})' +
    '((\\p{Lu}(' +
      # longer names than 1 + 3 inclusive cannot end with a dot
      '([\\p{Ll}-]{3,}|\\p{Lu}[\\p{Ll}-]{2,})|' +
      # some abbreviated names are without dot (eg. "A Marinelli")
      '([\\p{Ll}-]{1,2}|\\p{Lu}[\\p{Ll}-]{0,1})\\.?|' +
      '\\.' +
    # assume `de' is valid word part of name
    ')?(-|\\s*)|de\\s+|et\\s+al\\.)+)'),
  'author_forbidden': re.compile('(de)?\\s*(' +
    '(Transitive|Defining|Towards|Against' +
    '|Argument|Edited|Proceed|With\\s|Publish|A\\s+Note|Verb|Aspect|On\\s' +
    '|The|Two|National|Info|Frontiers|Chapter|Workshop|Query|Sociolingu' +
    '|Unpublish|Discourse|Robust|Speech).*|A\\s*' +
    ')$'),
  'author_forbidden_rest': re.compile('^[\'’]s'),
  'unwanted_prefix': re.compile('^\\s*([Ii]n(\\s*:|\\s+(?=[Pp]roceedings))|'
    '([Vv]ol\\.\\s*[0-9]+|[Vv]olume\\s+[0-9]+)|ed\\.|editors|and)\\s*'),
  # assume words ending on [0-9][.] belongs to journal name (e.g.
  #   `21. Century', `About 1. league')
  # we do not assume double-quote character to appear in a journal
  #   title (e.g. no nesting)
  'journal': re.compile('^[^\\p{L}"]*("([^"]+)"|((([^0-9.,](?!(Vol\\.|Volume)))*' +
    '([0-9]+\\.|[0-9]+|(?<=vs)\\.)?)+))'),
  'school': re.compile('^.+?thesis, *([^,]+)'),
  'pages': re.compile('(pp\\.)\\s*([0-9]+)\\s*(--\\s*([0-9]+))?'),
  'publisher': re.compile('\\s*([^:,.;]+:(\\s*[^,.:;\\s]+)+)' +
    '(?![:,.;\\s]*[^:,.;]+:(\\s*[^,.:;\\s]+)+)'),
  'title_extension': re.compile('(and|,)\\s*$'),
  'starts_with_with': re.compile('^\\s*[Ww]ith\\s+[\\p{Lu}-]'),

  'bibtex_preamble': re.compile('\\s*@([A-Za-z]+)\\s*[{]'),
  'bibtex_author_brace': re.compile('(\\}[\\s,]*\\{|\\s+and\\s+)'),
  'bibtex_ordinary_nested': re.compile('^(\\\\.|[^\\\\{}])+'),
  'bibtex_ordinary': re.compile('^(\\\\.|[^\\\\{}",])+'),
  'bibtex_cleanup': re.compile('[{}\\\\~]'),
}

def text_content_modified(subtree):
  """enclose content of <a> tags into quotation marks"""

  prefix, postfix, s = '', '', ''

  if not str(subtree.tag).startswith('<built-in'):
    if subtree.tag == 'a':
      prefix, postfix = '"', '"'
    if subtree.text:
      s = subtree.text

  for i in subtree:
    s += text_content_modified(i)

  if subtree.tail:
    return prefix + s + postfix + subtree.tail
  else:
    return prefix + s + postfix

def clean_start_end(s, start = True, end = True, blank_only = False):
  if blank_only:
    if start: s = re.sub(eres['lead_space'],  '', s)
    if end:   s = re.sub(eres['trail_space'], '', s)
  else:
    if start: s = re.sub(eres['clean_start'], '', s)
    if end:   s = re.sub(eres['clean_end'],   '', s)
  return s

def clean_whole(s, blank_only = False):
  s = re.sub(eres['blank'], ' ', s)
  return clean_start_end(s, blank_only = blank_only)

def clean_start_iter(s):
  while True:
    old = s
    s = re.sub(eres['unwanted_prefix'], '', s)
    s = clean_start_end(s, end = False)
    s = s.strip('()')
    if old == s:
      return s

def normalize_author(s):
  s = re.sub(eres['author_join_start'], '', s)
  s = re.sub(eres['author_join_end'], '', s)
  s = re.sub(eres['bibtex_author_brace'], ' ', s)
  return re.sub(eres['blank'], ' ', s.strip(', \t'))

# search for year from the end of the given string
def grep_year_note(s, reverse = False, with_paren = True):
  s = clean_start_end(s, start = False)
  s = re.sub(eres['clean_author'], '', s)
  if reverse:
    postfix = 'r'
  else:
    postfix = ''

  if not with_paren:
    postfix += '_no_paren'

  tmp = re.search(eres['year4' + postfix], s)
  if tmp:
    year = tmp.group(1)
    note = s[:tmp.start()] + s[tmp.end():]
  else:
    tmp = re.search(eres['year2' + postfix], s)
    if tmp:
      year = '20' + tmp.group(1)
      note = s[:tmp.start()] + s[tmp.end():]
    else:
      year = ''
      note = s

  return year, note

# TODO try to distinguish between 'Name X.,' and 'Name, X.'
# impossible: Chambers, N., J. Allen, et al.
# possible?:  Chambers, Nol., J. Allen,
# possible?:  Chambers, Nolan, J. Allen,
# impossible: Allen, J. F. and C. R. Perrault
# impossible: Hinkelman, E. and J.F. Allen
# impossible: Traum, D. and Allen, J.F.
def grep_author_note(s):
  author = ''
  g = 3
  while True:
    s = re.sub(eres['clean_author'], '', s)
    tmp = re.search(eres['author'], s)
    if tmp:
      # all the following mess is needed because of too slow regex engine
      #   (he gives up and tries each possible combination if the
      #   forbidden part is written inside of the `author' regex)
      # TODO handle situation '..., Surname A Paper Name ...' (where `A'
      #   belongs to Paper Name...)
      if re.search(eres['author_forbidden_rest'], s[tmp.end(g):]):
        break
      ss = tmp.group(g)
      tmpp = re.search(eres['author_forbidden'], ss)
      if tmpp:
        maybe_empty = ss[:tmpp.start()]
        if author and maybe_empty:
          author += AUTHOR_JOIN
        author += maybe_empty
        s = s[tmp.start(g) + tmpp.start(2):]
        break
      else:
        if author:
          author += '; '
        author += ss.strip(' \t')
        # save only the rest (drop prefixes like `and' `with' etc.)
        s = s[tmp.end(g):]
    else:
      break
  return author, s

def grep_journal_note(s):
  tmp = re.search(eres['journal'], s)
  journal, note = '', s
  if tmp:
    if tmp.group(2):
      journal += tmp.group(2)
      note = s[tmp.end(2) +1:]
    else:
      journal += tmp.group(3)
      note = s[tmp.end(3):]
  return journal, note

def grep_school_note(s):
  tmp = re.search(eres['school'], s)
  school, note = '', s
  if tmp:
    school += tmp.group(1)
    note = s[:tmp.start(1)] + s[tmp.end(1):]
  return school, note

def grep_publisher_note(s):
  tmp = re.search(eres['publisher'], s)
  publisher, note = '', s
  if tmp:
    publisher += tmp.group(1)
    note = s[:tmp.start(1)] + s[tmp.end(1):]
  return publisher, note

def grep_pages_note(s):
  tmp = re.search(eres['pages'], s)
  pages, note = '', s
  if tmp:
    pages += tmp.group(2)
    if tmp.group(4):
      pages += '--' + tmp.group(4)
    note = s[:tmp.start()] + s[tmp.end():]  # remove the whole match
  return pages, note

def get_preamble(s, note):
  if s == 'Thesis':
    if note.strip(' \t\n').startswith('Phd '):
      return 'PHDTHESIS'
    else:
      return 'MASTERTHESIS'
  elif s == 'Articles':
    return 'ARTICLE'
  elif s == 'Book Chapters':
    return 'INBOOK'
  elif s == 'Conference Papers' or \
       s == 'Workshop Papers' or \
       s == 'Posters' or \
       s == 'Demonstrations':
    return 'CONFERENCE'  # the same as INPROCEEDINGS
  elif s == 'Reports and Memos':
    return 'TECHREPORT'
  elif s == 'Editorials':
    return 'PROCEEDINGS'
  else:
    printw('WARN: No matching BibTeX type found for ' + s + '.', file = sys.stderr)
    return 'MISC'

def print_bib(preamble, do_not_check_items = False, **x):
  if 'title' not in x:
    raise NameError('Missing argument `title\'.')
  for i in x:
    # prevent typos
    if not do_not_check_items and i not in bibtex_allowed:
      raise NameError('Illegal BibTeX item name `' + i + '\'.')
    # prevent None.string_functions()
    if x[i] == None:
      x[i] = ''
    else:
      x[i] = str(x[i])

  if 'yet_generated_bib_id' in x:
    bib_id = re.sub(eres['nonlatinchar'], '-', x['yet_generated_bib_id'])
    del x['yet_generated_bib_id']
  else:
    # generate some ID from title
    bib_id = re.sub(eres['nonlatinchar'], '-', x['title'][:20].lower())

  # BibTeXML strict (the extended one is too complicated for fuzzy matching)
  printw(
    '<bibtex:entry id="' + bib_id + '">\n' +
    '  <bibtex:' + preamble.lower() + '>')

  # mandatory/standardized items
  for i in bibtex_allowed:
    if i in x:
      printw('    <bibtex:' + i + '>' +
          escape(x[i], xml_escape_table) + '</bibtex:' + i + '>')
      del x[i]

  # other items
  for i, j in x.items():
    printw('    <bibtex:' + i + '>' +
        escape(j, xml_escape_table) + '</bibtex:' + i + '>')

  printw(
    '  </bibtex:' + preamble.lower() + '>\n' +
    '</bibtex:entry>')

  # BibTeX version
  #printw('@' + preamble + ' { ' + bib_id + ',')
  ## try to comply with order
  #for i in bibtex_allowed:
  #  if i in x:
  #    printw('  ' + i + ' = {' + x[i].replace("'", "\\'") + '},')
  #printw('}')

def _parse_bib_item(s, first_call = True):
  res = ''
  end = 0
  first_pair_quote_found = False

  # http://maverick.inria.fr/~Xavier.Decoret/resources/xdkbibtex/bibtex_summary.html

  while True:
    if first_call:
      x = re.search(eres['bibtex_ordinary'], s)
      if x:
        end = x.end()

      # first iteration
      if s[end] == '"':
        if first_pair_quote_found:
          first_pair_quote_found = False
        else:
          first_pair_quote_found = True
        res += s[:end +1]
        s = s[end +1:]
        end = 0
        continue
      elif s[end] == '{':
        # only { left
        res += s[:end]
        s = s[end:]
      elif s[end] == ',' or s[end] == '}':
        if first_pair_quote_found:
          res += s[:end +1]
          s = s[end +1:]
        elif res:
          res = clean_start_end(res, end = False, blank_only = True)
          return res[1:-1], s[end +1:]
        else:
          # month = Sep, year = 2005}
          return s[:end], s[end +1:]
      elif not res:
        res = s[0]
        s = s[1:]
        end = 0
        continue
    else:
      x = re.search(eres['bibtex_ordinary_nested'], s)
      if x:
        end = x.end()
      res += s[:end]
      s = s[end:]

      if s[0] == '}':
        return res, s

    if s[0] == '{':
      tmp, s = _parse_bib_item(s[1:], first_call = False)
      res += '{' + tmp + s[0]
      s = s[1:]
      end = 0

def print_bib_from_bibtex(s):
  """simple conversion from BibTeX to BibTeXML
  supported
    double quotes
    escaped characters
    nested curly braces
  not supported
    checks for invalid BibTeX format (assume correct BibTeX syntax)
"""
  s = clean_whole(s)
  m = {}

  x = re.search(eres['bibtex_preamble'], s)
  if not x:
    print('ERR: BibTeX bad format: ' + s, file = sys.stderr)
    return
  preamble, s = x.group(1).lower(), s[x.end(0):]

  tmp, _, s = s.partition('=')
  tmp, _, key = tmp.partition(',')
  # comma found => ID found
  if _:
    m['yet_generated_bib_id'] = clean_start_end(tmp, blank_only = True)
  else:
    key = tmp

  key = clean_start_end(key, blank_only = True).lower()

  while True:
    tmp, s = _parse_bib_item(s)
    m[key] = tmp
    key, _, s = s.partition('=')
    if not _:
      break
    key = clean_start_end(key, blank_only = True).lower()

  # BibTeXML specific
  if 'author' in m:
    # humble '{Name}, {Name2}' -> '{Name; Name2}' conversion
    m['author'] = re.sub(eres['bibtex_author_brace'], '; ', m['author'])

  for i, j in m.items():
    m[i] = re.sub(eres['bibtex_cleanup'], '', j)

  # title is mandatory
  if 'title' not in m:
    m['title'] = 'Unknown :('

  return print_bib(preamble, do_not_check_items = True, **m)

def handle_profile_hermansky(subtree, _year = [1]):
  if not _year[0]:
    _year[0] = 0

  if subtree.tag == 'h3':
    _year[0] = clean_whole(subtree.text_content())
    return

  abstract, title, author, note, tmp = '', '', '', '', ''
  if subtree[2].tag == 'div' and subtree[2].get('class') == 'hide abstract':
    abstract = clean_whole(subtree[2][0].tail, blank_only = True)

  if subtree[0].text:
    tmp = subtree[0].text

  for i in subtree[0]:
    if not title:
      title = tmp
      if i.tag == 'a':
        title += i.text_content()
      title = clean_whole(title, blank_only = True)
      continue
    if i.tag == 'em':
      note += i.text_content()
    else:
      for t in (i.text_content(), i.tail):
        if t:
          tmp = normalize_author(t)
          if tmp:
            if author:
              author += AUTHOR_JOIN + tmp
            else:
              author = tmp
  note = clean_whole(note)
  print_bib('MISC', abstract = abstract, title = title, author = author,
      note = note, year = _year[0])

def handle_profile_zendulka(subtree):
  """intentionally implemented as simple extraction of BibTeX from the
  reffered HTML (otherwise there would be much missing information)"""

  # locally downloaded pages contain generally absolute url paths
  url = subtree.get('href')
  if not eres['url'].search(url):
    url = "http://www.fit.vutbr.cz" + url

  try:
    detail = parse(url)
  except:
    print('ERR: Unable to parse HTML document ' + url, file = sys.stderr)
    return

  for p in detail.getroot().xpath(
      "//table[@id='contenttable']/tr/td/" +
      "table[@border='0' and @cellpadding='2' and @cellspacing='0']/" +
      "tr/td[@colspan='2']/pre"):
    print_bib_from_bibtex(p.text_content())

def handle_profile_assaleh(subtree):
  print_bib_from_bibtex(subtree.text_content())

def handle_profile_ladamic(subtree):
  # ... Click here for a complete list of publications
  if subtree.tag == 'a' and (subtree.tail == None or
      eres['whole_blank'].search(subtree.tail)):
    return

  if len(subtree) == 0:
    l = (subtree)  # make it iterable
  else:
    l = subtree

  for i in l:
    if i.tag == 'div' and i.get('class') == 'item':
      i = i[0]  # nest deeper

    if i.tag == 'p':
      i = i[0]  # nest yet deeper

    title = i.get('title')

    if title == None:
      title = clean_start_end(i.text_content(), blank_only = True)
      # just for sure
      if i.tail:
        year, note = grep_year_note(i.tail, reverse = True, with_paren = False)
        note = note.split(',')
        author = ''
        for j in note[:-1]:
          if author:
            author += AUTHOR_JOIN + normalize_author(j)
          else:
            author = normalize_author(j)
        note = clean_whole(note[-1], blank_only = True)
    else:
      # iterate through <a>s with author names (can't use text_content()
      #   and split because of commas between names)
      author = normalize_author(i[1][0].text)
      for a in i[1][1:]:
        author += AUTHOR_JOIN + normalize_author(a.text)

      # <span>.tail (conference name, year etc.)
      note = i[1].tail.strip(',. \t\n+')
      atitle = ''
      for j in i[2].get('title').split('&'):
        a, _, c = j.partition('=')
        if a == 'rft.atitle':
          atitle = re.sub(eres['url_hex'], ' ', c)
        elif a == 'rft.title':
          title = re.sub(eres['url_hex'], ' ', c)
        elif a == 'rft.date':
          year = c
        else:
          # ctx_ver rft.place rft.volume rft.issue rft.pub rft.series
          # rft.spage rft_id rfr_id rft.au rft_val_fmt rft.aulast rft.aufirst
          if note:
            note += '; ' + j.strip(',. \t\n+')
          else:
            note = j

      # atitle takes precedence in case both title and atitle are set
      if atitle:
        title = atitle

    print_bib('MISC', author = author, title = title, year = year,
        note = note)

def handle_profile_cond(subtree):
  title, note = '', ''
  x = 0
  while x < len(subtree[0]):
    i = subtree[0][x]
    if i.tag == 'p':
      i.drop_tag()
      continue

    x += 1

    if i.tag == 'span':
      # isn't it the very first span?
      if title:
        year, note = grep_year_note(note, reverse = True, with_paren = False)
        author, note = grep_author_note(note)
        print_bib('MISC', author = author, title = title, year = year,
            note = note)
        title, note = '', ''
    elif i.tag == 'br':
      note += i.tail
    else:
      if i.tag == 'a' and not title:
        title = i.text_content().strip('" \t»')
      else:
        note += i.text_content()
        if i.tail:
          note += i.tail
  # handle last item
  if title and note:
    year, note = grep_year_note(note, reverse = True)
    author, note = grep_author_note(note)
    print_bib('MISC', author = author, title = title, year = year,
        note = note)

def handle_profile_janal(subtree):
  title, author, note, piece, preamble_raw, mess = '', '', '', '', '', ''

  for i in subtree:
    if i.tag == 'h4':
      if preamble_raw:
        preamble_raw_old = preamble_raw
      else:
        preamble_raw_old = i.text
      preamble_raw = i.text
    elif i.tag == 'li':
      if i.text:
        author += i.text

      for ii in i:
        if ii.tag == 'b':
          author += ii.text_content()
          if ii.tail:
            author += ii.tail
        elif ii.tag == 'a':
          if re.search(eres['title_extension'], last_text):
            if ii.text_content().strip():
              author += ii.text_content()
            if ii.tail:
              author += ii.tail
          # first occurance of <a>
          elif not title:
            title = ii.text_content()
            if ii.tail:
              mess = clean_whole(ii.tail)  # year/journal/note/etc.
          else:
            if piece:
              note += clean_whole(ii.text_content())
            else:
              piece += clean_whole(ii.text_content())

            if ii.tail:
              note = clean_whole(ii.tail) + note
        elif ii.tag == 'h4':
          if preamble_raw:
            preamble_raw_old = preamble_raw
          else:
            preamble_raw_old = i.text_content()
          preamble_raw = ii.text_content()
        else:
          piece = clean_whole(ii.text_content())  # journal, book...
          note += clean_whole(ii.tail)

        # for guessing if the next <a> will be continuation of the current content
        if ii.tail:
          last_text = ii.tail
        else:
          last_text = ii.text_content()

      note = clean_start_iter(note)

      if note:
        preamble = get_preamble(preamble_raw_old, note)
      else:
        preamble = get_preamble(preamble_raw_old, mess)
      # we are one item delayed
      preamble_raw_old = preamble_raw

      author, trash = grep_author_note(normalize_author(author))
      title = clean_whole(title)

      if preamble == 'PHDTHESIS':
        year, note = grep_year_note(note, reverse = True, with_paren = False)
        if not year: year, _note = grep_year_note(mess, reverse = True, with_paren = False)
        piece, note = grep_school_note(_note + note)
        print_bib(preamble, author = author, title = title, school = piece,
            year = year, note = note)
      elif preamble == 'MASTERTHESIS':
        year, note = grep_year_note(note, reverse = True, with_paren = False)
        if not year: year, _note = grep_year_note(mess, reverse = True, with_paren = False)
        piece, note = grep_school_note(_note + note)
        print_bib(preamble, author = author, title = title, school = piece,
            year = year, note = note)
      elif preamble == 'ARTICLE':
        if piece:
          journal = piece
        else:
          journal, note = grep_journal_note(note)
          if not journal:
            journal, note = grep_journal_note(mess)
        # TODO save the trash if regexp [A-Z] is used instead of \p{}
        #note = trash + note
        year, note = grep_year_note(note, reverse = True, with_paren = False)
        print_bib(preamble, author = author, title = title, journal = journal,
            year = year, note = note)
      elif preamble == 'INBOOK':
        year, note = grep_year_note(note, reverse = True, with_paren = False)
        publisher, note = grep_publisher_note(note)
        if not year:
          year, trash = grep_year_note(trash, reverse = True, with_paren = False)
          note = trash + note
        if piece:
          note = clean_whole(mess + ', ' + note)
        # handle one special, totally different and messy item
        else:
          piece = title
          year, mess = grep_year_note(mess, reverse = True, with_paren = False)
          # assume the title contains :
          title, note = grep_publisher_note(note)
          note, _, publisher = note.rpartition(':')
          publisher = clean_whole(publisher)
        print_bib(preamble, author = author, title = piece, chapter = title,
            publisher = publisher, year = year, note = note)
      elif preamble == 'CONFERENCE':
        if title:
          if not note:
            note = mess + ', ' + trash
        else:
          note = clean_start_iter(trash + mess + note)
          title, note = grep_journal_note(note)
          note = clean_whole(note)

        if not piece:
          note = clean_start_iter(note)
          piece, note = grep_journal_note(note)
          note = clean_whole(note)

        year, note = grep_year_note(note, reverse = True, with_paren = False)
        if not year:
          year, _ = grep_year_note(piece, reverse = True, with_paren = False)
        print_bib(preamble, author = author, title = title, booktitle = piece,
            year = year, note = note)
      elif preamble == 'TECHREPORT':
        if trash != 'more reports, see also':
          year, note = grep_year_note(note, reverse = True, with_paren = False)
          institution, note = grep_journal_note(note)
          note = piece + ', ' + clean_whole(note)
          print_bib(preamble, author = author, title = title,
              institution = institution, year = year, note = note)
      elif preamble == 'PROCEEDINGS':
        note = trash + mess + piece + note

        year, note = grep_year_note(note, reverse = True, with_paren = False)
        if not year:
          year, note = grep_year_note(note, reverse = True, with_paren = False)
        if not title:
          note = clean_start_iter(note)
          title, note = grep_publisher_note(note)
          if not title:
            title, note = grep_journal_note(note)
        note = clean_start_end(note)
        print_bib(preamble, author = author, title = title, year = year,
            note = note)

      author, title, note, piece, year, mess = '', '', '', '', '', ''
    # <center>
    #else:

# LOL: pretty printed subtree (without empty lines) has over 4000 lines,
#   but there is only cca 20 publications
def handle_profile_alcazar(subtree):
  start = False
  preamble = ''
  # why the hell does he not mention himself in his bibliography?
  alcazar = clean_whole(tree.getroot().xpath(
    "//h1[child::a[position()=1 and @name='_top']]"
    )[0].text_content())
  for i in subtree:
    if i.tag == 'h1' and len(i) > 1 and i[1].text == 'List of publications':
      start = True
    elif i.tag == 'p' and len(i) and i[0].text == 'Top':
      start = False
    else:
      content = i.text_content()
      if start and not eres['whole_blank'].search(content):
        if 'Refereed journal articles' in content:
          preamble = 'ARTICLE'
        elif 'Other refereed publications' in content:
          preamble = 'MISC'
        else:
          x = 0
          place, rest = '', ''
          last_tag = ''

          while x < len(i):
            if i[x].tag == 'city' or i[x].tag == 'place':
              tmp = i[x].text_content()
              if place and tmp:
                place += ', ' + tmp
              else:
                place += tmp
            else:
              rest += i[x].text_content()
              if i[x].tail:
                rest += i[x].tail
            last_tag = i[x].tag
            x += 1

          rest = clean_whole(rest)

          # jump over non-bibliography items
          if not rest.startswith('Unpublished') and \
             not rest.startswith('Edited books') and \
             not rest.startswith('Published conference proceedings') and \
             not rest.startswith('With a co-authored introduction'):
            year, note = grep_year_note(rest)
            if re.search(eres['starts_with_with'], note):
              note = alcazar + ' ' + note
            else:
              note = alcazar + '. ' + note
            author, note = grep_author_note(note)
            title, note = grep_journal_note(note)
            if preamble == 'ARTICLE':
              note = clean_start_end(note, end = False)
              journal, note = grep_journal_note(note)
              note += ', ' + place
              note = clean_start_end(note)
              print_bib(preamble, author = author, title = title,
                  journal = journal, year = year, note = note)
            else:
              note = clean_start_end(note)
              if place:
                print_bib(preamble, author = author, title = title,
                    year = year, address = place, note = note)
              else:
                print_bib(preamble, author = author, title = title,
                    year = year, note = note)

          place, rest = '', ''

# a real mess - 3 lines in different languages which I don't undestand and
#   absolutely no regular syntax on that lines => I assume each line has
#   fixed meaning => no further processing is done
def handle_profile_argitalpenak(subtree):
  preamble = ''
  author, title, booktitle, year, note, paper_url = '', '', '', '', '', ''
  for i in subtree:
    if i.tag == 'h2':
      tmp = i.text_content()
      if tmp == 'Papers':
        preamble = 'CONFERENCE'
      elif tmp == 'Internal reports':
        preamble = 'MISC'
      elif tmp == 'Thesis':
        preamble = 'PHDTHESIS'

      author, title, booktitle, year, note, paper_url = '', '', '', '', '', ''
      if i.tail:
        author = clean_whole(i.tail)
    elif (i.tag == 'i' or i.tag == 'a') and \
        clean_whole(i.text_content()) == '[Google scholar]':
      if preamble == 'CONFERENCE':
        year, tmp = grep_year_note(author, reverse = True)
        author, tmp = grep_author_note(tmp)
        tmp = clean_start_end(tmp)
        if tmp:
          note += ', ' + tmp
        if paper_url:
          print_bib(preamble, author = author, title = title,
              booktitle = booktitle, year = year, note = note, url = paper_url)
        else:
          print_bib(preamble, author = author, title = title,
              booktitle = booktitle, year = year, note = note)

      author, title, booktitle, year, note, paper_url = '', '', '', '', '', ''
      if i.tail:
        author = clean_whole(i.tail)
    # `bibtext' wtf?
    elif i.tag == 'a' and clean_whole(i.text_content()) == '[bibtext]':
      url = i.get('href')
      try:
        detail = parse(url)
      except:
        print('ERR: Unable to parse HTML document ' + url, file = sys.stderr)
        continue

      for p in detail.getroot().xpath('//pre'):
        print_bib_from_bibtex(p.text_content())

      author, title, booktitle, year, note, paper_url = '', '', '', '', '', ''
      if i.tail:
        author = clean_whole(i.tail)
    else:
      if not title:
        title = clean_whole(i.text_content())
      elif not booktitle:
        booktitle, tmp = grep_journal_note(clean_whole(i.text_content()))
        note += tmp
      elif i.tag == 'a' and i.get('href'):
        paper_url = i.get('href')

      if i.tail:
        if not author:
          author = clean_whole(i.tail)
        else:
          note += clean_whole(i.tail)

def handle_profile_james(subtree):
  preamble = ''
  for i in subtree:
    # section with bibliography starts here
    if i.tag == 'p' and i.get('class') == 'heading3':
      preamble = 'MISC'
    # section with bibliography ends here
    elif i.tag == 'p' and i.get('class') == 'heading2':
      preamble = ''
    elif preamble:
      s = clean_whole(text_content_modified(i))
      if not s.startswith('Back to '):
        # each this citation item has different format and
        #   indistinguishable type => must use MISC
        s = s.replace('``', '"').replace("''", '"')
        author, s = grep_author_note(s)
        year, s = grep_year_note(s)
        if not year:
          year, s = grep_year_note(s, reverse = True, with_paren = False)
        title, s = grep_journal_note(s)
        print_bib(preamble, author = author, title = title, year = year,
            note = clean_start_end(s, end = False))

def handle_profile_alonso(subtree):
  if clean_whole(subtree.text_content(), blank_only = True) == 'bibTeX reference':
    url = i.get('href')
    try:
      # actually, it is plain text, but surprisingly, it works :)
      detail = parse(url)
    except:
      print('ERR: Unable to parse HTML document ' + url, file = sys.stderr)
      return

    print_bib_from_bibtex(detail.getroot().text_content())

items = tree.getroot().xpath(arg['x'])
if items:
  for i in items:
    locals()['handle_profile_' + arg['p']](i)
  printw(BIBTEXML_FOOTER)
else:
  err_exit('No bibliographic items found.', ret = 0)
