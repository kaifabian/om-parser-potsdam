#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys,os
from BeautifulSoup import *
import libxml2,urllib2
from lxml.html import soupparser
from xml.sax.saxutils import escape, quoteattr
import time

curr_url = "http://www.studentenwerk-potsdam.de/mensa-{mensa}.html"
next_url = "http://www.studentenwerk-potsdam.de/speiseplan/"
meta_url = "http://www.studentenwerk-potsdam.de/mensa-{mensa}.html"
xsd_location = "http://openmensa.org/open-mensa-v2.xsd"

meta_names = [
    "am-neuen-palais",
    "brandenburg",
    "friedrich-ebert-strasse",
    "golm",
    "griebnitzsee",
    "pappelallee",
    "wildau",
]

addresses = {
    "am-neuen-palais": (u"Am Neuen Palais 10, Haus 12", 14469, u"Potsdam"),
    "brandenburg": (u"Magdeburger Straße 50", 14770, u"Brandenburg an der Havel"),
    "friedrich-ebert-strasse": (u"Friedrich-Ebert-Str. 4", 14467, u"Potsdam"),
    "golm": (u"Karl-Liebknecht-Str. 24/25", 14476, u"Potsdam OT Golm"),
    "griebnitzsee": (u"August-Bebel-Str. 89", 14482, u"Potsdam"),
    "pappelallee": (u"Kiepenheuerallee 5", 14469, u"Potsdam"),
    "wildau": (u"Bahnhofstr. 1", 15745, u"Wildau"),
}

def compFormat(instr, *args, **kwargs):
    if hasattr(instr, "format"):
        return instr.format(*args, **kwargs)
    
    slices = instr.split("{}")
    instr = ""
    if len(slices) - 1 == len(args):
        for i in range(0, len(args)):
            instr += slices[i]
            instr += str(args[i])
        instr += slices[-1]
    
    for i in range(0, len(args)):
        instr = instr.replace("{" + str(i) + "}", str(args[i]))
    
    for name in kwargs:
        value = kwargs[name]
        if value.__class__ != instr.__class__:
            value = instr.__class__(value)
        instr = instr.replace("{" + name + "}", value)
        x = re.compile("{" + re.escape(name) + ":(?P<pad>.)(?P<length>[0-9]+)}")
        y = set(x.findall(instr))
        if len(y) > 0:
            for pad, length in y:
                length = int(length)
                padded = (pad * (length - len(value))) + value
                instr = instr.replace("{" + name + ":" + pad + str(length) + "}", padded)
    
    return instr

class ScraperError(Exception):
    pass

class ScraperStructureChangedError(ScraperError):
    pass

def getContents(url):
    handle = urllib2.urlopen(url)
    content = handle.read().decode('iso-8859-1')
    handle.close()
    
    return BeautifulSoup(content)
    
months = {
    'Januar': 1,
    'Februar': 2,
    'Marz': 3,
    'Maerz': 3,
    u'M\xe4rz': 3,
    u'M\xc3\xa4rz': 3,
    'April': 4,
    'Mai': 5,
    'Juni': 6,
    'Juli': 7,
    'August': 8,
    'September': 9,
    'Oktober': 10,
    'November': 11,
    'Dezember': 12,
}

def scrape_table(table, force_date = None):
    output = u""
    
    if not force_date:
        dateRe = re.compile("(?P<weekName>[A-Za-z]+,?) +(?P<day>[0-9]+)\. (?P<month>.+) (?P<year>[0-9]+)")
        
        dates = table.xpath(".//div[contains(@class, 'date')]")
        date = dates[0]
        
        dateText = dateRe.match(date.text)
        if not dateText:
            raise ScraperStructureChangedError(compFormat("Could not parse date {}", repr(date.text)))
        
        day,year = map(lambda w: int(dateText.group(w)), ["day", "year", ])
        month = months[dateText.group("month")]
        year = year + 2000 if year < 1900 else year
        dateText = compFormat("{year:04}-{month:02}-{day:02}", day = day, month = month, year = year)
    else:
        dateText = force_date
        
    categories = table.xpath(".//td[contains(@class, 'head')]")
    meals = table.xpath(".//td[starts-with(@class, 'text')]")
    labels = table.xpath(".//td[starts-with(@class, 'label')]")
    
    assert len(meals) == len(labels), ":)"
    
    output += compFormat(u" <day date={}>\n", quoteattr(dateText))
    for index,meal in enumerate(meals):
        label = labels[index]
        category = categories[index % len(categories)]
        
        labelList = label.xpath(".//a/img/@title")
        labelList = map(lambda s: s, labelList)
        
        mealName = meal.text_content()
        
        categoryName = category.text.decode("iso-8859-1").encode("utf-8")
        
        if len(mealName) > 0:
            output += compFormat(u"  <category name={}>\n", quoteattr(category.text))
            output += u"   <meal>\n"
            output += compFormat(u"    <name>{name}</name>\n", name = escape(mealName))
            for labelText in labelList:
                output += compFormat(u"    <note>{note}</note>\n", note = escape(labelText))
            output += u"   </meal>\n"
            output += u"  </category>\n"
    output += u" </day>\n"
    
    return output

def scrape_daily(url):
    content = str(getContents(url))
    xml = soupparser.fromstring(content)
    
    tables = xml.xpath("//table[contains(@class, 'bill_of_fare')]")
    if len(tables) > 0:
        table = tables[0]
    else:
        return u"<!-- fetch again in 30 minutes -->\n"
    
    dateRe = re.compile("(.*)\s+(?P<weekName>[A-Za-z]+),\s*den\s*(?P<day>[0-9]+)\.\s*(?P<month>\w+)\s*(?P<year>[0-9]+)")
    date = xml.xpath("//h2[@id = 'ueberschrift_h2']/text()[starts-with(.,'Speiseplan')]")[0]
    dateMatch = dateRe.match(date)
    day,year = map(lambda w: int(dateMatch.group(w)), ["day", "year", ])
    month = months[dateMatch.group("month")]
    dateText = compFormat("{year:04}-{month:02}-{day:02}", day = day, month = month, year = year)
    
    output = scrape_table(table, force_date = dateText)
    
    return output

def scrape_week(url):
    content = str(getContents(url))
    xml = soupparser.fromstring(content)
    
    tables = xml.xpath("//table[contains(@class, 'bill_of_fare')]")
    
    output = u""
    for table in tables:
        output += scrape_table(table)
    
    return output

def scrape_meta(name, urls):
    url = compFormat(meta_url, mensa = name)
    urls.append(url)
    
    content = str(getContents(url))
    xml = soupparser.fromstring(content)
    
    telfield = 'Tel.: '
    
    mensaname = xml.xpath('//div[contains(@class, "site_title")]/h1/text()')
    #adresse = xml.xpath('//span[contains(@id, "container2")]/text()')
    telefon = xml.xpath('//p[contains(@class, "bodytext")]/text()[starts-with(.,"' + telfield + '")]')
    if len(mensaname) < 1:
        raise ScraperStructureChangedError("Name not found in meta")
    if len(telefon) < 1:
        raise ScraperStructureChangedError("Telephone not found in meta")
    
    mensaname = mensaname[0].strip().encode("utf-8")
    
    strasse,plz,ort = addresses[name]
    ort = ort.encode("utf-8")
    telefon = telefon[0].strip().encode("utf-8")[len(telfield):]
    
    output = " <!--\n"
    output += "  <om-proposed:info xmlns:om-proposed=\"http://mirror.space-port.eu/~om/om-proposed\">\n"
    output += "   <om-proposed:name><![CDATA[" + mensaname + "]]></om-proposed:name>\n"
    output += "   <om-proposed:street><![CDATA[" + strasse + "]]></om-proposed:street>\n"
    output += "   <om-proposed:zip>" + str(plz) + "</om-proposed:zip>\n"
    output += "   <om-proposed:city><![CDATA[" + ort + "]]></om-proposed:city>\n"
    output += "   <om-proposed:contact type=\"phone\"><![CDATA[" + telefon + "]]></om-proposed:contact>\n"
    output += " </om-proposed:info>\n"
    output += " -->\n\n"
    
    return output

def scrape_mensa(name, cacheTimeout = 1):
    cacheName = name.replace("/", "_").replace("\\", "_")
    cacheDir = os.path.join(os.path.dirname(__file__), "cache")
    cacheFile = compFormat("{name}.xml", name=cacheName)
    cachePath = os.path.join(cacheDir, cacheFile)

    if os.path.isfile(cachePath):
        now = time.time()
        cacheTime = os.path.getmtime(cachePath)
        age = now - cacheTime
        if age <= cacheTimeout:
            handle = open(cachePath, "rb")
            content = handle.read()
            handle.close()

            return content

    output = \
"""<?xml version="1.0" encoding="UTF-8"?>
<openmensa version="2.0"
            xmlns="http://openmensa.org/open-mensa-v2"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd">
 <canteen>
"""

    url1 = compFormat(curr_url, mensa=name)
    url2 = compFormat(next_url, mensa=name)
    
    urls = [url1, url2, ]
    
    output += scrape_meta(name, urls)
    output += scrape_daily(url1)
    output += scrape_week(url2)
    
    output += " </canteen>\n"
    output += "</openmensa>\n"
    output = output.encode("utf-8")

    if cacheTimeout > 0:
        handle = open(cachePath, "wb")
        handle.write(output)
        handle.close()

    return output

def canValidate():
    try:
        from lxml import etree
        from cStringIO import StringIO
    except ImportError, e:
        __import__("traceback").print_exc(e)
        return False

    return True


def validate(xmldata, schema):
    try:
        from lxml import etree
        from cStringIO import StringIO
    except ImportError:
        return False

    scs = etree.parse(StringIO(schema))
    sch = etree.XMLSchema(scs)
    xml = etree.parse(StringIO(xmldata))

    try:
        sch.assertValid(xml)
        return True
    except etree.DocumentInvalid:
        print sch.error_log
        return False

#if __name__ == "__main__" and "test" in sys.argv:
#    for mensa_name in meta_names:
#        print "---", "Testing", mensa_name, "---"
#        mensa = scrape_mensa(mensa_name, cacheTimeout = -1)
#        
#        f = open(compFormat("test-{}.xml", mensa_name), "wb")
#        f.write(mensa)
#        f.close()

if __name__ == "__main__" and "test" in sys.argv:
    doValidation = False
    if canValidate():
        doValidation = True

        try:
            import urllib2
            xsdh = urllib2.urlopen(xsd_location)
            xsd = xsdh.read()
            xsdh.close()
        except Exception,e:
            __import__("traceback").print_exc(e)
            print "ERROR"
            doValidation = False

    if not doValidation:
        print "[ERR ] cannot validate!"

    for mensa_name in meta_names:
        print "---", "Testing", mensa_name, "---"
        mensa = scrape_mensa(mensa_name, cacheTimeout = -1)

        if doValidation:
            if not validate(mensa, xsd):
                raise Exception("Validation Exception")

        f = open(compFormat("test-{}.xml", mensa_name), "wb")
        f.write(mensa)
        f.close()

