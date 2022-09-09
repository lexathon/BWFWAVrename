#! python

import os
import shutil
import xml.etree.cElementTree as ET
import BWFwave
import numpy as np
import tkinter
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
from tkinter import *


class WavFile(object):
    def __init__(self, originalFileName, directory):
        self._originalFileName = originalFileName
        self._directory = directory
        self._channels = None
        self._xml = None
        self._badWav = self._xmlExtract() # badWav (1 = xmlError, 2 = problem with WAV)
        if self._badWav == 0: # can we read the xml?
            self._tracks = [ None ] * self._channels
            for i in range(self._channels):
                if self._channels == 1:
                    interleaveIndex = self._polywavSplitTest()
                else:
                    interleaveIndex = i + 1
                self._tracks[i] = Track(self._xml, interleaveIndex)

    def __str__(self):
        return self._originalFileName

    def _xmlExtract(self):
        try:
            file = (os.path.join(self._directory, self._originalFileName))
            wavfile = BWFwave.open(file, 'rb')
            self._channels = wavfile.getnchannels()
            headerData = wavfile.getixml()
            wavfile.close()
            # let's parse naughty xmls containing '&' characters
            headerData = headerData.replace(b'&amp;', b'&')
            headerData = headerData.replace(b'&', b'&amp;')
            # lose any binary guff at the end (some files need this)
            headerData = headerData.decode('ascii').rstrip('\x00\x02')
            # take header data up to end of XML - deals with other weirdness on some files:-
            sep = "</BWFXML>"
            headerData = headerData.split(sep, 1)[0] + sep
        except:
            return 2
        try:
            self._xml = ET.ElementTree(ET.fromstring(headerData))
        except:
            return 1
        return 0

    def _fileId(self):
        # ignore trimming if polywav
        if self._channels > 1:
            return(self._originalFileName[:-4])
        # otherwise work backwards to '_'
        trimLength = len(self._originalFileName)
        for l in self._originalFileName[::-1]:
            trimLength -= 1
            if l == '_':
                break
        if trimLength == 0:
            return(self._originalFileName[:-4])
        else:
            return(self._originalFileName[:trimLength])

    # in cases where BWFManager or equivalent has separated polywavs into individual files
    # an interleaveIndex is returned.
    def _polywavSplitTest(self):
        for elem in self._xml.iterfind('TRACK_LIST/TRACK_COUNT'):
            trackCount = int(elem.text)
        if trackCount > 1:
            return int(self._originalFileName[-6:][:2].replace('_', ''))
        else:
            return 1

    def getNewFileName(self, channel, style):
        if self._badWav == 1:
            return 'Problem reading XML'
        if self._badWav == 2:
            return 'Problem reading WAV'
        else:
            if style == 0:
                return self._fileId() + '_' + self._tracks[channel].getName() + '_'\
                       + self._tracks[channel].getChannel() + '.WAV'
            if style == 1:
                return self._tracks[channel].getName() + '_' + self._fileId() + '_'\
                       + self._tracks[channel].getChannel() + '.WAV'
            if style == 2:
                return self._originalFileName[:-4] + '_' + self._tracks[channel].getChannel() + '.WAV'

    def getBadWav(self):
        return self._badWav

    def getChannels(self):
        return self._channels

    def getOriginalFileName(self):
        return self._originalFileName

    def getDirectory(self):
        return self._directory

    def getTrack(self, track):
        return self._tracks[track]

    def getFileId(self):
        return self._fileId()


class Track(object):
    def __init__(self, xml, interleaveIndex):
        self._xml = xml
        self._interleaveIndex = interleaveIndex
        self._channel = self._xmlRead('CHANNEL_INDEX')
        self._name = self._xmlRead('NAME')

    def _xmlRead(self, tag):
        return self._xml.find('.//TRACK[INTERLEAVE_INDEX="' + str(self._interleaveIndex) + '"]/' + tag).text

    def getChannel(self):
        return self._channel

    def getName(self):
        return self._name


class FilesList(object):
    def __init__(self, caller):
        self._list = []
        self._directory = ''
        self._newDirectory = None
        self._caller = caller

    def getList(self):
        return self._list

    def getFile(self, x):
        return self._list[x]

    def __len__(self):
        return len(self._list)

    def getDirectory(self):
        return self._directory

    def setNewDirectory(self, newdir):
        self._newDirectory = newdir
        self._caller.clearTargetDirectoryField()
        self._caller.setTargetDirectoryField(newdir)

    def clear(self):
        self._list = []
        self._directory = ''
        self._newDirectory = self._directory
        self._caller.clear()

    def load(self, directory):
        if directory:
            self._directory = directory
        for x in sorted(os.listdir(self._directory)):
            if x[-4:].lower() != '.wav' or x[:2] == '._':
                continue
            wavFile = WavFile(x, self._directory)
            self._list.append(wavFile) # add it to the files list
            if wavFile.getBadWav() > 0:
                id = self._caller.treeInsert(None, wavFile.getOriginalFileName(),
                                             'N/A',
                                             'Error',
                                             wavFile.getNewFileName(0, self._caller.getStyle())
                                             )
                continue
            if wavFile.getChannels() == 1:
                id = self._caller.treeInsert(None, wavFile.getOriginalFileName(),
                                             wavFile.getTrack(0).getChannel(),
                                             wavFile.getTrack(0).getName(),
                                             wavFile.getNewFileName(0, self._caller.getStyle())
                                             )
            else:
                self._caller.selectCopyCheck()
                self._caller.disableCopyCheck()
                for y in range(wavFile.getChannels()):
                    if y == 0:
                        id = self._caller.treeInsert(None, wavFile.getOriginalFileName(),
                                                     '',
                                                     '',
                                                     '**polywav')
                        self._caller.treeOpen(id)
                    self._caller.treeInsert(id, wavFile.getFileId() + '_' + wavFile.getTrack(y).getChannel(),
                                                 wavFile.getTrack(y).getChannel(),
                                                 wavFile.getTrack(y).getName(),
                                                 wavFile.getNewFileName(y, self._caller.getStyle())
                                                 )

    def directorySelect(self):
        self.clear()
        directoryAsk = filedialog.askdirectory(title='Select directory containing files')
        if directoryAsk:
            popup = ProgressPopup(self._caller.master, 'Loading...')
            popup.progressBar['value'] = 5000
            popup.update()
            self.load(directoryAsk)
            popup.cancel(popup)

    def targetSelect(self):
        if self._caller.getCopy() == 0:
            messagebox.showwarning('Error', 'Files set to be renamed in their current directory. \n'
                                            + 'Choose \'copy files\' to select a new target.')
            return
        directoryAsk = filedialog.askdirectory(title='Select target directory')
        if directoryAsk:
            self.setNewDirectory(directoryAsk)

    def execute(self):
        style = self._caller.getStyle()
        copy = self._caller.getCopy()
        success = 0
        for x in self._list:
            if x.getBadWav() != 0:
                print(x)
                print(x.getBadWav())
        if len(self) == 0 or any(x for x in self._list if x.getBadWav() != 0):
            messagebox.showerror('Error', 'No files to rename.')
            return
        if copy == 1:
            if not self._newDirectory:
                messagebox.showerror('Error', 'No target directory selected.')
                return
            if self._newDirectory == self._directory:
                if not messagebox.askokcancel('Alert', 'Target folder for copies is the same as source folder. \n'
                                                'Are you sure?'):
                    return
            popup = ProgressPopup(self._caller.master, 'Copying files...')
            popup.update()
            popup.lift
            for x, wavFile in enumerate(self._list):
                popup.progressBar['value'] = (10000 / len(self._list)) * x
                popup.setFileLabel(wavFile.getNewFileName(0, style))
                popup.update()
                if wavFile.getBadWav() == 0:
                    if wavFile.getChannels() == 1:
                        try:
                            shutil.copyfile((os.path.join(wavFile.getDirectory(), wavFile.getOriginalFileName())),
                                    (os.path.join(self._newDirectory, wavFile.getNewFileName(0, style))))
                        except Exception as e:
                            messagebox.showwarning('Error', 'Unable to copy ' + wavFile.getOriginalFileName() + '\n'
                                                   + str(e) + '\nAborting...')
                            break
                    else:
                        try:
                            for y in range(wavFile.getChannels()):
                                splitPolywav(wavFile, y, self._newDirectory, wavFile.getNewFileName(y, style))
                                popup.setFileLabel(wavFile.getNewFileName(y, style))
                                print(wavFile.getNewFileName(y, style))
                                popup.progressBar['value'] = ((10000 / len(self._list)) * x) \
                                                             + (10000 / len(self._list)) / (wavFile.getChannels()) * y
                                popup.update()
                        except Exception as e:
                            messagebox.showwarning('Error', 'Unable to perform split. \n' + str(e))
                            break
                success = 1
            popup.cancel()
        else:
            for wavFile in self._list:
                if wavFile.getBadWav() == 0:
                    try:
                        os.rename(os.path.join(wavFile.getDirectory(), wavFile.getOriginalFileName()),
                                  os.path.join(wavFile.getDirectory(), wavFile.getNewFileName(0, style)))
                    except Exception as e:
                        messagebox.showwarning('Error', 'Unable to rename ' + wavFile.getOriginalFileName() + '\n'
                                               + str(e) + '\nAborting...')
                        break
            success = 1
        if success == 1:
            messagebox.showinfo('Success', 'Operation complete.')
        self.clear()


# method for splitting a polywav into an individual file
def splitPolywav(wavFile, channel, newPath, newFileName):
    sourcewav = BWFwave.open(os.path.join(wavFile.getDirectory(), wavFile.getOriginalFileName()))
    depth = sourcewav.getsampwidth()
    sourcedata = sourcewav.readframes(sourcewav.getnframes())
    sourcewav.setpos(0)
    data = np.frombuffer(sourcedata, dtype='V' + str(depth))
    channeldata = data[channel::wavFile.getChannels()]
    outwav = BWFwave.open(os.path.join(newPath, newFileName), 'w')
    outwav.setparams(sourcewav.getparams())
    outwav.setnchannels(1)
    outwav.setnframes(sourcewav.getnframes())
    outwav.setbext(sourcewav.getbext())
    #need to sort out a new ixml here...
    tree = wavFile._xml
    root = tree.getroot()
    tracklistEl = root.find('TRACK_LIST')
    tracklistEl.clear()
    trackCountEl = ET.Element('TRACK_COUNT')
    trackCountEl.text = '1'
    trackCountEl.tail = '\n'
    trackEl = ET.Element('TRACK')
    trackEl.tail = '\n'
    channelIndexEl = ET.SubElement(trackEl, 'CHANNEL_INDEX')
    channelIndexEl.text = wavFile._tracks[channel].getChannel()
    channelIndexEl.tail = '\n'
    interleaveIndexEl = ET.SubElement(trackEl, 'INTERLEAVE_INDEX')
    interleaveIndexEl.text = '1'
    interleaveIndexEl.tail = '\n'
    nameEl = ET.SubElement(trackEl, 'NAME')
    nameEl.text = wavFile._tracks[channel].getName()
    nameEl.tail = '\n'
    tracklistEl.append(trackCountEl)
    tracklistEl.append(trackEl)
    output = '<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(root).decode('utf-8') + '                '
    #output must be even in length for wav to work:
    if (len(output) % 2 != 0):
        output = output + ' '
    #end of new xml section
    #outwav.setixml(sourcewav.getixml()) -- old xml line - just duplicate the original
    outwav.setixml(bytes(output, 'utf-8'))
    outwav.writeframesraw(channeldata.tobytes())
    outwav.close()
    sourcewav.close()


# start of launch code

root = Tk()
root.title('BWFWAVrename')

class MainWindow(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.files = FilesList(self)
        self.nameOrder = IntVar()
        self.copy = IntVar()
        self.justTrack = IntVar()
        # graphical elements
        self.directoryLabel = Label(master, text='Folder containing wavs:')
        self.directoryField = Text(master, width=100, height=1, state='disabled', relief='solid', borderwidth=1)
        self.targetDirectoryLabel = Label(master, text='Target folder:')
        self.targetDirectoryField = Text(master, width=100, height=1, state='disabled', relief='solid', borderwidth=1)
        self.browseDirectoryButton = Button(master, text='Select Source Folder', command=self.files.directorySelect)
        self.browseTargetButton = Button(master, text='Select Target Folder', command=self.files.targetSelect)
        self.aboutButton = Button(master, text='About...', command=self.about)
        self.executeButton = Button(master, text='Execute', command=self.files.execute, width=10)
        self.clearButton = Button(master, text='Clear List', command=self.files.clear, width=10)
        self.nameOrderCheck = Checkbutton(master, text='Track name at start of file name',
                                          command=self.refresh, variable=self.nameOrder)
        self.nameOrderCheck.select()
        self.justTrackCheck = Checkbutton(master, text='Just add a track number (no rename)',
                                          command=self.justTrackToggle, variable=self.justTrack)
        self.copyCheck = Checkbutton(master, text='Copy files and leave originals untouched '
                                                  '(mandatory with polywavs)', variable=self.copy)
        self.tree = ttk.Treeview(master)
        self.tree['height'] = 25
        self.tree['columns'] = ('Track No.', 'Track Name', 'New Filename')
        self.tree.column('#0', width=250, anchor='w')
        self.tree.column('Track No.', width=80, anchor='center')
        self.tree.column('Track Name', width=150, anchor='w')
        self.tree.column('New Filename', width=350, anchor='w')
        self.tree.heading('#0', text='Filename')
        self.tree.heading('Track No.', text='Track No.')
        self.tree.heading('Track Name', text='Track Name')
        self.tree.heading('New Filename', text='New Filename')
        self.vsb = ttk.Scrollbar(master, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)

        # place graphical elements
        self.directoryLabel.grid(row=1, column=1, columnspan=3, sticky=E, padx=10, pady=10)
        self.directoryField.grid(row=1, column=4, columnspan=3, sticky=W, padx=10, pady=10)
        self.browseDirectoryButton.grid(row=2, column=1, columnspan=2, sticky=E)
        self.tree.grid(row=3, column=1, columnspan=6, padx=10, pady=10)
        self.vsb.place(x=915, y=82, height=472)
        self.nameOrderCheck.grid(row=4, column=1, columnspan=6, sticky=W, padx=10)
        self.justTrackCheck.grid(row=5, column=1, columnspan=6, sticky=W, padx=10)
        self.copyCheck.grid(row=6, column=1, columnspan=6, sticky=W, padx=10)
        self.executeButton.grid(row=8, column=6, sticky=E, padx=10, pady=10)
        self.targetDirectoryLabel.grid(row=7, column=1, columnspan=3, sticky=E, padx=10, pady=10)
        self.targetDirectoryField.grid(row=7, column=4, columnspan=3, sticky=W, padx=10, pady=10)
        self.browseTargetButton.grid(row=8, column=1, columnspan=2, sticky=E, padx=10)
        self.aboutButton.grid(row=8, column=3, columnspan=1, sticky=E, padx=10)
        self.clearButton.grid(row=8, column=5, sticky=E, padx=10, pady=10)

    def treeInsert(self, id, originalFileName, track, name, newFileName):
        if not id:
            id = ''
        return self.tree.insert(id, 'end', text=originalFileName, values=(track, name, newFileName))

    def treeOpen(self, id):
        self.tree.item(id, open=TRUE)

    def treeClear(self):
        for i in self.tree.get_children():
            self.tree.delete(i)


    def clear(self):
        self.clearDirectoryField()
        self.clearTargetDirectoryField()
        self.deselectCopyCheck()
        self.enableCopyCheck()
        self.treeClear()

    def refresh(self):
        self.treeClear()
        self.files.load(None)

    def justTrackToggle(self):
        if self.justTrack.get() == 1:
            self.nameOrderCheck.configure(state='disabled')
        else:
            self.nameOrderCheck.configure(state='normal')
        self.refresh()

    def getStyle(self):  #read the checkboxes
        if self.justTrack.get() == 1:
            return 2
        if self.nameOrder.get() == 1:
            return 1
        else:
            return 0

    def getCopy(self):
        return self.copy.get()

    def selectCopyCheck(self):
        self.copyCheck.select()

    def deselectCopyCheck(self):
        self.copyCheck.deselect()

    def disableCopyCheck(self):
        self.copyCheck.configure(state='disabled')

    def enableCopyCheck(self):
        self.copyCheck.configure(state='normal')

    def getJustTrack(self):
        return self.justTrack.get()

    def setDirectoryField(self, text):
        self.directoryField.configure(state='normal')
        self.directoryField.insert('end', text)
        self.directoryField.configure(state='disabled')

    def clearDirectoryField(self):
        self.directoryField.configure(state='normal')
        self.directoryField.delete('1.0', END)
        self.directoryField.configure(state='disabled')

    def setTargetDirectoryField(self, text):
        self.targetDirectoryField.configure(state='normal')
        self.targetDirectoryField.insert('end', text)
        self.targetDirectoryField.configure(state='disabled')

    def clearTargetDirectoryField(self):
        self.targetDirectoryField.configure(state='normal')
        self.targetDirectoryField.delete('1.0', END)
        self.targetDirectoryField.configure(state='disabled')

    def about(self):
        AboutPopup(self.master)


class ProgressPopup(Toplevel):
    def __init__(self, master, title):
        Toplevel.__init__(self, master)
        self.overrideredirect(1)
        self.transient(master)
        self.master = master
        body = Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        self.Title = Label(body, text=title)
        self.Title.grid(row=0, column=0)
        self.progressBar = ttk.Progressbar(body, length=500, maximum=10000, mode='determinate')
        self.progressBar.grid(row=1, column=0)
        self.fileLabel = Label(body, text=' ')
        self.fileLabel.grid(row=2, column=0)

        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (master.winfo_rootx() + 100, master.winfo_rooty() + 200))
        self.initial_focus.focus_set()
        self.lift()
        self.wait_visibility(window=None)
    #
    # construction hooks
    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def cancel(self, event=None):
        # put focus back to the parent window
        self.master.focus_set()
        self.destroy()

    def setFileLabel(self, file):
        self.fileLabel['text'] = file

    def setTitle(self, title):
        self.Title['text'] = title


class AboutPopup(Toplevel):
    def __init__(self, master):
        Toplevel.__init__(self, master)
        self.overrideredirect(1)
        self.transient(master)
        self.master = master
        body = Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)
        self.Title = Label(body, text='About BWFWAVrename')
        self.Title.pack()
        self.content = Text(body, width=100, height=25)
        self.content.pack()
        self.content.insert(END, 'v0.8b. \n\n'
                                 'App to help us get track names on to our edit timelines. \n\n'
                                 'Avid Media Composer currently does not bring in track labels from '
                                 'BWF Wave files in such a way that they can be seen on the timeline.\n\n'
                                 'As a work around, if the filename contains the track name, we can identify '
                                 'what is on our timeline.\n\n'
                                 'This app will read the iXML data embedded in the BWF Wave File and rename '
                                 'the files accordingly.\n\n'
                                 'If the file is a polywav (with many channels), the app will split the polywav '
                                 'into several\n files that can be imported into Avid.\n\n'
                                 'The app also ensures that channels are correctly identifiable by Avid by ending '
                                 'each file with the\n channel number chosen by the sound recordist.\n\n'
                                 'For best results disable the following options in Media Composer\'s import:\n'
                                 '\'Use Broadcast Wave Scene and Take for Clip Names\'\n'
                                 '\'Autodetect Broadcast Wave Monophonic Groups\'\n\n'
                                 'Please support the project by donating if you find this app useful and send any ' 
                                 'problem files or\n comments to lex@lextv.uk - Thanks!\n\n'
                                 'Latest version is available at https://github.com/lexathon/BWFWAVrename \n\n'
                                 '(c) Lex Nichol, 2019-2022')
        self.content.configure(state='disabled')
        self.Ok = Button(body, text='Ok', command=self.cancel, width=10)
        self.Ok.pack()
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (master.winfo_rootx() + 60, master.winfo_rooty() + 60))
        self.initial_focus.focus_set()
        self.wait_visibility(window=None)
        self.lift()
    #
    # construction hooks
    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def cancel(self, event=None):
        # put focus back to the parent window
        self.master.focus_set()
        self.destroy()

app = MainWindow(master=root)
app.mainloop()