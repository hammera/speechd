#!/usr/bin/env python3
# coding: utf-8
# NVDA symbols and cldr import
# Import NVDA symbols dictionaries then emojies from CLDR database
# Copyright (C) 2001, 2019 Patrick Zajda
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
###
#This file includes portions of code from the NVDA project.
#URL: http://www.nvda-project.org/
###

from os import path
import codecs
from collections import OrderedDict
from shutil import copy
import gi
from gi.repository import GLib
import csv
import os

class SymbolsDictionary(OrderedDict):
	""" This class inherited from OrderedDict is displayed as a .dic file content when converted to a string
	Attribute: symbolsQualifier, default None - if the 4th column must have one """

	def __init__(self, symbolsQualifier=None,*args,**kwargs):
		super(SymbolsDictionary, self).__init__(*args,**kwargs)
		self.symbolsQualifier=symbolsQualifier

	def __str__(self):
		dicText = str("symbols:\r\n")
		for pattern, description in self.items():
			if self.symbolsQualifier:
				dicText = str().join((dicText,u"{pattern}\t{description}\tnone\t{qualifier}\r\n".format(
				pattern=pattern,
				description=description,
				qualifier=self.symbolsQualifier
				)))
			else:
				dicText = str().join((dicText,u"{pattern}\t{description}\tnone\r\n".format(
				pattern=pattern,
				description=description
				)))
		return dicText

def createCLDRAnnotationsDict(sources):
	""" Argument: the list of CLDR files to parse
	Returns: a SymbolsDictionary object containing all emojies in the specified language """
	from xml.etree import ElementTree
	cldrDict = SymbolsDictionary() # Where the list of emojies will be storred
	# We brows the source files
	for source in sources:
		tree = ElementTree.parse(source) # We parse the CLDR XML file to extract all emojies
		for element in tree.iter("annotation"):
			if element.attrib.get("type") == "tts":
				cldrDict[element.attrib['cp']] = element.text.replace(":","")
	assert cldrDict, "cldrDict is empty"
	return cldrDict

# List of languages which are non-standard for CLDR files
CLDRExceptionsList = {
	"sr":("sr","sr_Latn"),
	"sr_BA":("sr_Latn_BA",),
	"yue": ("yue","yue_Hans"),
	"zh_HK":("zh_Hant_HK",),
	"zh_TW":("zh_Hant",),
}

# The NVDA path
NVDADir = "symbolsrc/nvda-beta"
# CLDR base dir
CLDRDir = "symbolsrc/cldr"
# UnicodeData.txt path
unicodeDataPath = "symbolsrc/UnicodeData.txt"
# CLDR paths
annotationsDir = path.join(CLDRDir, "common/annotations")
annotationsDerivedDir = path.join(CLDRDir, "common/annotationsDerived")

# This is the header which will be inserted in all symbols file
docHeader = """# This file was automatically generated by make import-symbols
# DO NOT MODIFY IT!
# See locale/README.md to know how to import dictionaries

"""

# Open UnicodeData.txt
with open(unicodeDataPath, "r", newline='') as uDataFile:
	uDataCSV = csv.reader(uDataFile, delimiter = ';')
	fontVariantsDict = SymbolsDictionary("literal")
	for uCharacter in uDataCSV:
		# The 6th field starts with <font> code for all font variants
		# So get the code after <font> and the first field content to have the character and the one to pronounce
		if uCharacter[5].startswith("<font>"):
			fontVariant = chr(int("0x"+uCharacter[0], 16))
			pronouncedCharacter = chr(int("0x"+uCharacter[5][7:], 16))
			if pronouncedCharacter != GLib.utf8_normalize(fontVariant, -1, GLib.NormalizeMode.ALL_COMPOSE):
			    fontVariantsDict[fontVariant] = pronouncedCharacter

# Write the dictionary to en/font-variants.dic with documentation at the top
with codecs.open("base/font-variants.dic", "w", "utf_8_sig", errors="replace") as dicFile:
	dicFile.write(docHeader)
	dicFile.write(str(fontVariantsDict))

# Copy all NVDA symbols dictionaries
# Browse the "locale" directory, check if item is a directory and if it contains a symbols.dic file to copy it fter creating this directory in Speech-Dispatcher if not exists
NVDALocale = path.join(NVDADir, "source","locale")
for NVDALang in os.listdir(NVDALocale):
	langPath = path.join(NVDALocale,NVDALang)
	if not path.isdir(langPath):
		continue
	if not path.exists(path.join(langPath,"symbols.dic")):
		continue
	if not path.exists(NVDALang):
		os.mkdir(NVDALang)
	# Read the NVDA symbols dictionary
	NVDADic = codecs.open(path.join(langPath,"symbols.dic"),"r", "utf_8_sig").read()
	# We write the dictionnary with the doc and the punctuations
	with codecs.open(path.join(NVDALang, "symbols.dic"), "w", "utf_8_sig", errors="replace") as dicFile:
		dicFile.write(docHeader)
		dicFile.write(NVDADic)
copy("en/symbols.dic", "base/symbols.dic")

# Create all emojis dictionaries
processedFiles = ["root.xml","en_001.xml","sr_Cyrl.xml","sr_Cyrl_BA.xml"] # To avoid creating too much directories when we process a file in a non-standard language
# root.xml is added because it doesn't contain any language related content
# SR_CYRL* are also excluded, as en_001

""" Firstly, we process exceptions
so we can add their files to the processed files """
for lang,files in CLDRExceptionsList.items():
	if not path.exists(lang):
		os.mkdir(lang)
	cldrSources = []
	for CLDRFile in files:
		# First add all annotations, then the derived ones.
		if path.exists(path.join(annotationsDir,CLDRFile+".xml")):
			cldrSources.append(path.join(annotationsDir,CLDRFile+".xml"))
		if path.exists(path.join(annotationsDerivedDir,CLDRFile+".xml")):
			cldrSources.append(path.join(annotationsDerivedDir,CLDRFile+".xml"))
		processedFiles.append(CLDRFile+".xml")
	# We list emogies and don't continue if there is none
	try:
		emojiDic = createCLDRAnnotationsDict(cldrSources)
	except AssertionError:
		continue
	# We write the dictionnary with the doc and the emojies
	with codecs.open(path.join(lang, "emojis.dic"), "w", "utf_8_sig", errors="replace") as dicFile:
		dicFile.write(docHeader)
		dicFile.write(str(emojiDic))

# Browse the CLDR files and create corresponding dictionaries
for CLDRFile in os.listdir(annotationsDir):
	if CLDRFile in processedFiles:
		continue
	CLDRLang = CLDRFile[:-4]
	if not path.exists(CLDRLang):
		os.mkdir(CLDRLang)
	cldrSources = []
	# First add all annotations, then the derived ones.
	cldrSources.append(path.join(annotationsDir,CLDRFile))
	if path.exists(path.join(annotationsDerivedDir,CLDRFile)):
		cldrSources.append(path.join(annotationsDerivedDir,CLDRFile))
	# We list emogies and don't continue if there is none
	try:
		emojiDic = createCLDRAnnotationsDict(cldrSources)
	except AssertionError:
		continue
	# We write the dictionnary with the doc and the emojies
	with codecs.open(path.join(CLDRLang, "emojis.dic"), "w", "utf_8_sig", errors="replace") as dicFile:
		dicFile.write(docHeader)
		dicFile.write(str(emojiDic))
	processedFiles.append(CLDRFile)