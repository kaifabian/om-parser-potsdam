om-parser-potsdam
================

OpenMensa: Provides a feed parser for the canteens in Potsdam, Wildau and Brandenburg (Havel) (Studentenwerk Potsdam).

I know, the code is messy and pretty fucked up. For example the compFormat() function in mensa.py that provides compatibility between Python 2.5 and Python 2.7. But it is working. ;)

I also have to fight with the scraped page's encoding. It's pretty messy, feel free to fix it or to write your own parser! ;)

The current parser requires the following python packages:
- lxml
- beautifulsoup
