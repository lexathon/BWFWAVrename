#! python

# this script will take mono wavs from a folder with BWF metadata and rename them
# so that we can see track names in Avid and they are numbered correctly.
# PLEASE BE AWARE IT IS NOT EXTENSIVELY TESTED. ALWAYS COPY MEDIA FIRST!

# If you are working with polywav files, you'll need to separate them first
# You can use BWF Manager from Fostex to do this:
# https://www.fostexinternational.com/docs/tech_support/bwf_manager.shtml

# Instructions:
# Install python if it is not on your system already
# Drop a folder containing your WAVs on to the script
# Rename occurs (hopefully!)
# When importing to Avid, deselect 'Use Broadcast Wave Scene...' and 'Autodetect Broadcast...'

# Thoughts or issues, email lex@lextv.uk

import re
import os
import sys
import xml.etree.cElementTree as ET

path = os.path.abspath(sys.argv[1])

print(path)

filesList = []
for x in os.listdir(path):
	filesList.append(os.path.join(path, x))

def fileHeader(file):
	openfile = open(file, 'rb')
	stream = openfile.read(5000)
	openfile.close()
	headerData = stream.decode('utf-8', 'ignore')
	return '<?xml version' + headerData.split('<?xml version',1)[1]

def newName(file):
	filePathHead, fileName = os.path.split(file)
	xmlTree = ET.ElementTree(ET.fromstring(fileHeader(file)))
	#The test for polywav and type... TRACK_COUNT > 1. Polywav. CURRENT_FILENAME != fileName. Split.
	for elem in xmlTree.iterfind('HISTORY/CURRENT_FILENAME'):
		currentFileName = elem.text
	for elem in xmlTree.iterfind('TRACK_LIST/TRACK_COUNT'):
		trackCount = elem.text
	if trackCount != '1':
		print('Polywav detected...')
		if currentFileName[-5:].lower() == fileName[-5:].lower():
			print('Appears to be genuine polywav. Aborting...')
			return
		else:
			print('Appears to be a polywav that\'s been split...')
			interleaveIndex = fileName[-6:][:2].replace('_','')
	else:
		interleaveIndex = '1'
	channelIndex = xmlTree.find('.//TRACK[INTERLEAVE_INDEX="' + interleaveIndex + '"]/CHANNEL_INDEX').text
	name = xmlTree.find('.//TRACK[INTERLEAVE_INDEX="' + interleaveIndex + '"]/NAME').text.replace(' ','_')
	print('Track number: ' + channelIndex)
	print('Name: ' + name)
	newFileName = name + '_' + fileName[:-6] + '_' + channelIndex + '.WAV'
	os.rename(os.path.join(filePathHead, fileName), os.path.join(filePathHead, newFileName))
	return newFileName

for x in filesList:
	if (x[-4:] == '.wav') or (x[-4:] == '.WAV') :
		print(' ')
		print(x)
		print(newName(x))
