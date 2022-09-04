#! python

import re
import os
import shutil
import sys
import xml.etree.cElementTree as ET
from Tkinter import *
import tkFileDialog
import tkMessageBox
import ttk

class wavFile(object):
	def __init__(self, originalFileName, directory):
		self.originalFileName = originalFileName
		self.directory = directory
		self.xml = ET.ElementTree(ET.fromstring(xmlExtract(os.path.join(directory, originalFileName))))
		self.polywav = 0
		self.interleaveIndex = 1
		self.trackCount = 0
		#The test for polywav and type... TRACK_COUNT > 1. Polywav. CURRENT_FILENAME != fileName. Split.
		for elem in self.xml.iterfind('HISTORY/CURRENT_FILENAME'):
			self.currentFileName = elem.text
		for elem in self.xml.iterfind('TRACK_LIST/TRACK_COUNT'):
			self.trackCount = int(elem.text)
		if self.trackCount > 1: #polywav detected
			if self.currentFileName[-5:].lower() == self.originalFileName[-5:].lower(): #genuine polywav
				self.polywav = 1
			else: #polywav that's been split
				self.interleaveIndex = int(self.originalFileName[-6:][:2].replace('_',''))
		#determine track number, track name, fileId
		if self.polywav == 1:
			self.fileId = originalFileName
			self.trackNumber = 'N/A'
			self.trackName =  'polywav'
		else:
			self.fileId = determineFileId(self.originalFileName)
			self.trackNumber = xmlRead(self.xml, self.interleaveIndex, 'CHANNEL_INDEX')
			self.trackName = xmlRead(self.xml, self.interleaveIndex, 'NAME').replace(' ','_')
			
	def newFileName(self, nameOrder):
		if self.polywav == 1:
			return 'please convert first'
		else:
			if nameOrder == 1:
				return self.trackName + '_' + self.fileId + '_' + self.trackNumber + '.WAV'
			else:
				return self.fileId + '_' + self.trackName + '_' + self.trackNumber + '.WAV'
				

class filesList():
	def __init__(self, directory):
		self.list = []
		self.directory = directory
		self.tree = ttk.Treeview(root)
		self.tree['height'] = 20
		self.tree['columns'] = ('Track No.', 'Track Name', 'New Filename')
		self.tree.column('Track No.', width = 100, anchor = 'center')
		self.tree.column('Track Name', width = 200, anchor = 'w')
		self.tree.heading('#0', text = 'Filename')
		self.tree.heading('Track No.', text = 'Track No.')
		self.tree.heading('Track Name', text = 'Track Name')
		self.tree.heading('New Filename', text = 'New Filename')
		
	def clear(self):
		self.list = []
		directoryField.configure(state = 'normal')
		directoryField.delete('1.0', END)
		directoryField.configure(state = 'disabled')
		for i in self.tree.get_children():
			self.tree.delete(i)
			
	def load(self, directory):
		self.directory = directory
		directoryField.configure(state = 'normal')
		directoryField.insert('end', directory)
		directoryField.configure(state = 'disabled')
		for x in os.listdir(directory):
			if x[-4:].lower() == '.wav':
				self.list.append(wavFile(x, directory))
		for x in self.list:
			self.tree.insert('', 0, text = x.originalFileName, values=(x.trackNumber, x.trackName, x.newFileName(nameOrder.get())))
	
def directorySelect():
	files.clear()
	directory = tkFileDialog.askdirectory(title = 'Select directory containing files')
	if directory:
		files.load(directory)
	return

def nameOrderToggle():
	directory = files.directory
	files.clear()
	files.load(directory)
	
def execute():
	if len(files.list) == 0:
		tkMessageBox.showwarning('Error','No files to rename.')
		return
	if copy.get() == 1:
		parentPath, folderName = os.path.split(files.directory)
		newPath = os.path.join(parentPath, folderName + ' rename')
		if not os.path.exists(newPath):
			os.makedirs(newPath)
		else:
			tkMessageBox.showwarning('Error', 'Duplicate folder \'' + folderName + ' rename\'' + ' seems to already exist.\nNo files copied.')
		for x in files.list:
			if x.polywav == 0:
				shutil.copyfile((os.path.join(x.directory, x.originalFileName)), (os.path.join(newPath, x.newFileName(nameOrder.get()))))
	else:
		for x in files.list:
			if x.polywav == 0:
				os.rename(os.path.join(x.directory, x.originalFileName), os.path.join(x.directory, x.newFileName(nameOrder.get())))
	files.clear()
	
	

def xmlExtract(file):
	openfile = open(file, 'rb')
	stream = openfile.read(5000)
	openfile.close()
	headerData = stream.decode('utf-8', 'ignore')
	return '<?xml version' + headerData.split('<?xml version',1)[1]
	
def xmlRead(xml, interleaveIndex, tag):
	return xml.find('.//TRACK[INTERLEAVE_INDEX="' + str(interleaveIndex) + '"]/' + tag).text
	
def determineFileId(fileName):
	#work backwards to '_'
	trimLength = len(fileName)
	for l in fileName[::-1]:
		trimLength -= 1
		if l == '_':
			break
	id = fileName[:trimLength]
	return id
	

# start of launch code

root = Tk()
root.title('bwfwavrename')

files = filesList([])
nameOrder = IntVar()
copy = IntVar()

# graphical elements
directoryLabel = Label(root, text='Folder containing wavs:')
directoryField = Text(root, width = 80, height = 1, state = 'disabled', relief = 'solid', borderwidth = 1)
browseButton = Button(root, text = 'Browse', command = directorySelect, width = 10)
executeButton = Button(root, text = 'Execute', command = execute, width = 10)
nameOrderCheck = Checkbutton(root, text='Track name at start of file name', command = nameOrderToggle, variable=nameOrder)
nameOrderCheck.select()
copyCheck = Checkbutton(root, text='Create a duplicate folder and leave original folder untouched', variable=copy)

# place graphical elements
directoryLabel.grid(row = 1, column = 1, columnspan = 3, sticky = E, padx = 10, pady = 10)
directoryField.grid(row = 1, column = 4, columnspan = 3, sticky = W, padx = 10, pady = 10)
browseButton.grid(row = 2, column = 1, sticky = E)
files.tree.grid(row = 3, column = 1, columnspan = 6, padx = 10, pady = 10)
nameOrderCheck.grid(row =4, column = 1, columnspan = 6, sticky = W, padx = 10)
copyCheck.grid(row =5, column = 1, columnspan = 6, sticky = W, padx = 10)
executeButton.grid(row = 6, column = 6, sticky = E, padx = 10, pady = 10)


# if directory provided as argument at launch
if len(sys.argv) > 1:
	files.load(os.path.abspath(sys.argv[1]))

root.mainloop()