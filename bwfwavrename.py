#! python

# this script will take mono wavs from a folder with BWF metadata and rename them
# so that we can see track names in Avid and they are numbered correctly.
# PLEASE BE AWARE IT IS NOT EXTENSIVELY TESTED. ALWAYS COPY MEDIA FIRST!

# If you are working with polywav files, you'll need to separate them first
# You can use BWF Manager from Fostex to do this:
# https://www.fostexinternational.com/docs/tech_support/bwf_manager.shtml
# ***CURRENTLY polywavs converted this way cannot be renamed properly****
# ***because the polywav metadata is copied to all files - messy developers!****
# ***I'm working on it!***

# Instructions:
# Install python if it is not on your system already
# Drop a folder containing your WAVs on to the script
# Rename occurs (hopefully!)
# When importing to Avid, deselect 'Use Broadcast Wave Scene...' and 'Autodetect Broadcast...'

# Thoughts or issues, email lex@lextv.uk

import re
import os
import sys

path = os.path.abspath(sys.argv[1])

print(path)

filesList = []
for x in os.listdir(path):
	filesList.append(os.path.join(path, x))

def fileHeader(file):
	openfile = open(file, 'rb')
	stream = openfile.read(5000)
	openfile.close()
	return stream.decode('utf-8', 'ignore')

def xmlSplit(tag, data):
	startTag = '<' + tag + '>'
	endTag = '</' + tag + '>'
	return((data.split(startTag))[1].split(endTag)[0])

def newName(file):
	trackList = xmlSplit('TRACK_LIST', fileHeader(file))
	if xmlSplit('TRACK_COUNT', trackList) != '1':
		print('Polywav detected... aborting work on ' + file)
		return
	channelIndex = xmlSplit('CHANNEL_INDEX', trackList)
	print(channelIndex)
	name = xmlSplit('NAME', trackList)
	print('Track number: ' + channelIndex)
	print('Name: ' + name)
	head, tail = os.path.split(file)
	newFileName = name + '_' + tail[:-6] + '_' + channelIndex + '.WAV'
	os.rename(os.path.join(head, tail), os.path.join(head, newFileName))
	return newFileName	

for x in filesList:
	if (x[-4:] == '.wav') or (x[-4:] == '.WAV') :
		print(' ')
		print(x)
		print(newName(x))
