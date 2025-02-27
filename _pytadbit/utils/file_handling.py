"""
22 Jan 2014
"""

import ctypes
import os
import platform
import bz2, gzip, zipfile, tarfile

def check_pik(path):
    with open(path, "r") as f:
        f.seek (0, 2)           # Seek @ EOF
        fsize = f.tell()        # Get Size
        f.seek (max (fsize-2, 0), 0) # Set pos @ last n chars
        key = f.read()       # Read to end
    return key == 's.'


def magic_open(filename, verbose=False):
    """
    To read uncompressed zip gzip bzip2 or tar.xx files

    :param filename: either a path to a file, or a file handler

    :returns: opened file ready to be iterated
    """
    if isinstance(filename, str):
        fhandler = file(filename, 'rb')
        inputpath = True
        if tarfile.is_tarfile(filename):
            print 'tar'
            thandler = tarfile.open(filename)
            if len(thandler.members) != 1:
                raise NotImplementedError(
                    'Not exactly one file in this tar archieve.')
            return magic_open(thandler.extractfile(thandler.getnames()[0]))
    else:
        fhandler = filename
        filename = fhandler.name
        inputpath = False
        start_of_file = ''
    if inputpath:
        start_of_file = fhandler.read(1024)
        fhandler.seek(0)
    if start_of_file.startswith('\x50\x4b\x03\x04'):
        if verbose:
            print 'zip'
        zhandler = zipfile.ZipFile(fhandler)
        if len(zhandler.NameToInfo) != 1:
            raise NotImplementedError(
                'Not exactly one file in this zip archieve.')
        return zhandler.open(zhandler.NameToInfo.keys()[0])
    if start_of_file.startswith('\x42\x5a\x68'):
        if verbose:
            print 'bz2'
        fhandler.close()
        return bz2.BZ2File(filename)
    if start_of_file.startswith('\x1f\x8b\x08'):
        if verbose:
            print 'gz'
        return gzip.GzipFile(fileobj=fhandler)
    if verbose:
        print 'text'
    return fhandler


def get_free_space_mb(folder, div=2):
    """
    Return folder/drive free space (in bytes)

    Based on stackoverflow answer: http://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python

    :param folder: folder/drive to measure
    :param 2 div: divide the size by (div*1024) to get the size in Mb (3 is Gb...)
    
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value/1024/1024
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize/(1024**div)

def wc(fnam):
    """
    Pythonic way to count lines
    """
    return sum(1 for _ in open(fnam))
