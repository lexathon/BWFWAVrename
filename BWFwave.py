"""Modification of wave module to deal with BWF mono and polywavs

We are allowing for a additional chunks of data in the file header named 'bext' and 'iXML'


"""

import builtins

__all__ = ["open", "openfp", "Error", "Wave_read", "Wave_write"]

class Error(Exception):
    pass

WAVE_FORMAT_PCM = 0x0001

_array_fmts = None, 'b', 'h', None, 'i'

import wave
import audioop
import struct
import sys
from chunk import Chunk
from collections import namedtuple
import warnings

_wave_params = namedtuple('_wave_params',
                     'nchannels sampwidth framerate nframes comptype compname')

class Wave_read(wave.Wave_read):
    def initfp(self, file):
        self._convert = None
        self._soundpos = 0
        self._file = Chunk(file, bigendian = 0)
        if self._file.getname() != b'RIFF':
            raise Error('file does not start with RIFF id')
        if self._file.read(4) != b'WAVE':
            raise Error('not a WAVE file')
        self._fmt_chunk_read = 0
        self._data_chunk = None
        self._bext = None
        self._ixml = None
        while 1:
            self._data_seek_needed = 1
            try:
                chunk = Chunk(self._file, bigendian = 0)
            except EOFError:
                break
            chunkname = chunk.getname()
            if chunkname == b'bext':
                self._bext = chunk.read(chunk.chunksize)
            if chunkname == b'iXML':
                self._ixml = chunk.read(chunk.chunksize)
            if chunkname == b'fmt ':
                self._read_fmt_chunk(chunk)
                self._fmt_chunk_read = 1
            elif chunkname == b'data':
                if not self._fmt_chunk_read:
                    raise Error('data chunk before fmt chunk')
                self._data_chunk = chunk
                self._nframes = chunk.chunksize // self._framesize
                self._data_seek_needed = 0
                break
            chunk.skip()
        if not self._fmt_chunk_read or not self._data_chunk:
            raise Error('fmt chunk and/or data chunk missing')

    def getixml(self):
        return self._ixml

    def getbext(self):
        return self._bext

class Wave_write(wave.Wave_write):
    def setixml(self, ixml):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        self._ixml = ixml

    def getixml(self):
        return self._ixml

    def setbext(self, bext):
        if self._datawritten:
            raise Error('cannot change parameters after starting to write')
        self._bext = bext

    def getbext(self):
        return self._bext

    def _write_header(self, initlength):
        assert not self._headerwritten
        self._file.write(b'RIFF')
        if not self._nframes:
            self._nframes = initlength // (self._nchannels * self._sampwidth)
        self._datalength = self._nframes * self._nchannels * self._sampwidth
        if not self._bext:
            self._bext = 'nothing here'
        if not self._ixml:
            self._ixml = 'nothing here'
        try:
            self._form_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._form_length_pos = None
        self._file.write(struct.pack('<L4s4sL' + str(len(self._bext)) + 's4sL' + str(len(self._ixml)) + 's4sLHHLLHH4s',
                                     36 + self._datalength, b'WAVE', b'bext', len(self._bext), self._bext,
                                     b'iXML', len(self._ixml), self._ixml, b'fmt ', 16,
                                     WAVE_FORMAT_PCM, self._nchannels, self._framerate,
                                     self._nchannels * self._framerate * self._sampwidth,
                                     self._nchannels * self._sampwidth,
                                     self._sampwidth * 8, b'data'))
        if self._form_length_pos is not None:
            self._data_length_pos = self._file.tell()
        self._file.write(struct.pack('<L', self._datalength))
        self._headerwritten = True

def open(f, mode=None):
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return Wave_read(f)
    elif mode in ('w', 'wb'):
        return Wave_write(f)
    else:
        raise Error("mode must be 'r', 'rb', 'w', or 'wb'")

def openfp(f, mode=None):
    warnings.warn("wave.openfp is deprecated since Python 3.7. "
                  "Use wave.open instead.", DeprecationWarning, stacklevel=2)
    return open(f, mode=mode)
