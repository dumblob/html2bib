#!/bin/sh

P='./dumps03/'
EXE='./html2bib.py'
cd ~/src/college/isj/

[ -d "$P" ] || mkdir "$P" || exit $?

echo _________________________hermansky
$EXE -o "$P"bib_hermansky 'http://www.clsp.jhu.edu/publications/author/hynek-hermansky/'
#$EXE -b -o "$P"bib_hermansky.html 'http://www.clsp.jhu.edu/publications/author/hynek-hermansky/'

echo _________________________zendulka
#$EXE -o "$P"bib_zendulka 'http://www.fit.vutbr.cz/~zendulka/pubs.php.en'
$EXE -p zendulka -o "$P"bib_zendulka 'http://www.fit.vutbr.cz/~zendulka/pubs.php.en'
#$EXE -o "$P"bib_zendulka 'http://www.fit.vutbr.cz/~zendulka/pubs.php.en'
#$EXE -p zendulka ./web_input/"Doc. Ing. Jaroslav Zendulka, CSc. - Publications.html"

echo _________________________assaleh
$EXE -o "$P"bib_assaleh 'http://tony.abou-assaleh.net/Publications'
#$EXE 'file://localhost/home/honza/src/college/isj/web_input/Publications%20%7C%20Tony%20Abou-Assaleh.html'
#$EXE -b -o "$P"html_assaleh.html web_input/"Publications | Tony Abou-Assaleh.html"
#$EXE -o "$P"bib_assaleh -p assaleh web_input/"Publications | Tony Abou-Assaleh.html"

echo _________________________ladamic
##$EXE -o "$P"bib_ladamic 'http://www-personal.umich.edu/~ladamic/'
$EXE -p ladamic -o "$P"bib_ladamic 'http://www.ladamic.com/'
#$EXE -o "$P"bib_ladamic -p ladamic web_input/"Lada Adamic: University of Michigan.html"
#$EXE -b -o "$P"html_ladamic.html web_input/"Lada Adamic: University of Michigan.html"

echo _________________________cond
$EXE -o "$P"bib_cond 'http://www.cond.org/'
#$EXE -o "$P"bib_cond -p cond web_input/"Eytan Adar.html"
#$EXE -b -o "$P"html_cond.html web_input/"Eytan Adar.html"

echo _________________________janal
$EXE -o "$P"bib_janal 'http://www.dfki.de/~janal/publications.html'
#$EXE -o "$P"bib_janal -p janal web_input/"Most of Jan Alexandersson's publications.html"
#$EXE -b -o "$P"html_janal.html web_input/"Most of Jan Alexandersson's publications.html"

echo _________________________alcazar
$EXE -o "$P"bib_alcazar 'http://www-scf.usc.edu/~alcazar/#_List_of_publications'
#$EXE -o "$P"bib_alcazar -p alcazar web_input/"Home Page for Asier Alcazar.html"
#$EXE -b -o "$P"html_alcazar.html web_input/"Home Page for Asier Alcazar.html"

#echo _________________________argitalpenak
##FIXME problems with utf-8 handling in lxml:
##  ...
##  File "./html2bib.py", line 1030, in handle_profile_argitalpenak
##    booktitle, tmp = grep_journal_note(clean_whole(i.text_content()))
##  File "/usr/lib/python3.3/site-packages/lxml/html/__init__.py", line 278, in text_content
##    return _collect_string_content(self)
##  File "xpath.pxi", line 460, in lxml.etree.XPath.__call__ (src/lxml/lxml.etree.c:132811)
##  File "xpath.pxi", line 245, in lxml.etree._XPathEvaluatorBase._handle_result (src/lxml/lxml.etree.c:130574)
##  File "extensions.pxi", line 626, in lxml.etree._unwrapXPathObject (src/lxml/lxml.etree.c:126085)
##  File "apihelpers.pxi", line 1305, in lxml.etree.funicode (src/lxml/lxml.etree.c:23909)
##  UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf1 in position 1: invalid continuation byte
#$EXE -o "$P"bib_argitalpenak 'http://ixa.si.ehu.es/Ixa/Argitalpenak/kidearen_argitalpenak?kidea=1000808989'
##$EXE -o "$P"bib_argitalpenak -p argitalpenak web_input/"IXA taldea.html"
##$EXE -b -o "$P"html_argitalpenak.html web_input/"IXA taldea.html"

echo _________________________james
$EXE -o "$P"bib_james 'http://www.cs.rochester.edu/u/james/'
#$EXE -o "$P"bib_james -p james web_input/"James F. Allen's Home Page.html"
#$EXE -b -o "$P"html_james.html web_input/"James F. Allen's Home Page.html"

echo _________________________alonso
$EXE -o "$P"bib_alonso 'http://www.dc.fi.udc.es/~alonso/papers.html'
#$EXE -o "$P"bib_alonso -p alonso web_input/"Miguel A. Alonso's Publications.html"
#$EXE -b -o "$P"html_alonso.html web_input/"Miguel A. Alonso's Publications.html"
