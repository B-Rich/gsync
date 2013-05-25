# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime, time, posix, pickle, dateutil.parser, re
from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.options import GsyncOptions

class EUnknownSourceType(Exception):
    pass

class SyncFileInfoDatetime(object):
    __epoch = datetime.datetime(1970, 1, 1)

    def __(self, d):
        if isinstance(d, SyncFileInfoDatetime):
            return d.__d
        else:
            return d

    def __init__(self, datestring):
        self.__d = dateutil.parser.parse(datestring, ignoretz=True)
        
    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except:
            return getattr(self.__d, name)

    def __repr__(self): return "SyncFileInfoDatetime('%s')" % str(self)
    def __str__(self): return self.__d.isoformat()
    def __secs(self): return (self.__d - self.__epoch).total_seconds()
    def __int__(self): return int(self.__secs())
    def __long__(self): return long(self.__secs())
    def __float__(self): return float(self.__secs())
    def __sub__(self, d): return self.__d - self.__(d)
    def __cmp__(self, d): return int(self.__d) - self.__(d)
    def __lt__(self, d): return (self.__d < self.__(d))
    def __le__(self, d): return (self.__d <= self.__(d))
    def __eq__(self, d): return (self.__d == self.__(d))
    def __ne__(self, d): return (self.__d != self.__(d))
    def __gt__(self, d): return (self.__d > self.__(d))
    def __ge__(self, d): return (self.__d >= self.__(d))


class SyncFileInfo(object):
    # Note: The description field is currently overloaded to also provide
    #       custom metadata tags that currently aren't facilitated by Google
    #       Drive.
    def __init__(self, id, title, modifiedDate, mimeType,
                 description = None, fileSize = 0, md5Checksum = "",
                 **misc):

        self.id = id
        self.title = title
        self.modifiedDate = SyncFileInfoDatetime(modifiedDate)
        self.mimeType = mimeType
        self.statInfo = None
        self.description = None
        self.fileSize = fileSize
        self.md5Checksum = md5Checksum
        self.path = misc.get('path')

        if isinstance(description, str):
            self.description = description
            try:
                self.statInfo = pickle.loads(description.decode("hex"))
            except pickle.UnpicklingError:
                pass
            except EOFError:
                pass

        elif isinstance(description, posix.stat_result):
            self.statInfo = description
            try:
                self.description = pickle.dumps(description).encode("hex")
            except pickle.PicklingError:
                pass

    def __repr__(self):
        return """SyncFileInfo(
    id="%s",
    title="%s",
    modifiedDate="%s",
    mimeType="%s",
    fileSize=%d",
    md5Checksum=%s",
    description="%s",
    statInfo=%s
)""" % (
    self.id,
    self.title,
    self.modifiedDate,
    self.mimeType,
    self.fileSize,
    self.md5Checksum,
    self.description,
    self.statInfo
)


class SyncFile(object):
    path = None
    bytesRead = 0
    bytesWritten = 0

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def __add__(self, path):
        return os.path.join(self.path, path)

    def getPath(self, path = None):
        if path is None:
            path = self.path
        else:
            debug("Joining: %s with %s" % (self.path, path))
            path = os.path.join(self.path, path)
            debug("Got: %s" % path)

        return path

    def getContent(self, path = None, callback = None):
        raise ESyncFileAbstractMethod

    def getInfo(self, path = None):
        raise ESyncFileAbstractMethod

    def _createDir(self, path, src = None):
        raise ESyncFileAbstractMethod

    def _updateDir(self, path, src):
        raise ESyncFileAbstractMethod

    def _createFile(self, path, src):
        raise ESyncFileAbstractMethod

    def _updateFile(self, path, src):
        raise ESyncFileAbstractMethod

    def _updateStats(self, path, src, mode, uid, gid, atime, mtime):
        raise ESyncFileAbstractMethod

    def __createFile(self, path, src = None):
        self._createFile(path, src)
        self._updateFile(path, src)
        self.__updateStats(path, src)

    def __createDir(self, path, src = None):
        self._createDir(path, src)
        self.__updateStats(path, src)

    def __updateFile(self, path, src):
        self._updateFile(path, src)
        self.__updateStats(path, src)

    def __updateDir(self, path, src):
        self._updateDir(path, src)
        self.__updateStats(path, src)

    def __updateStats(self, path, src):
        if src is None: return

        srcInfo = src.getInfo()
        srcStatInfo = srcInfo.statInfo

        mode, uid, gid, atime, mtime = None, None, None, None, None

        if GsyncOptions.perms:
            if srcStatInfo is not None:
                mode = srcStatInfo.st_mode

        if GsyncOptions.owner:
            uid = srcStatInfo.st_uid
            if uid is not None:
                debug("Updating with uid: %d" % uid)

        if GsyncOptions.group:
            gid = srcStatInfo.st_gid
            if gid is not None:
                debug("Updating with gid: %d" % gid)

        if GsyncOptions.times:
            if srcStatInfo is not None:
                mtime = srcStatInfo.st_mtime
                atime = srcStatInfo.st_atime
            else:
                mtime = float(srcInfo.modifiedDate)
                atime = mtime

            debug("Updating with mtime: %0.2f" % mtime)
            debug("Updating with atime: %0.2f" % atime)

        self._updateStats(path, src, mode, uid, gid, atime, mtime)


    def _normaliseSource(self, src):
        srcPath, srcObj, srcInfo = None, None, None

        debug("src = %s" % repr(src))

        if src is not None:
            from libgsync.sync.file.factory import SyncFileFactory

            if isinstance(src, SyncFileInfo):
                srcInfo = src
                srcObj = SyncFileFactory.create(srcPath)
                srcPath = srcObj.path

            elif isinstance(src, SyncFile):
                srcObj = src
                srcInfo = src.getInfo()
                srcPath = src.path

            elif isinstance(src, str):
                srcPath = src
                srcObj = SyncFileFactory.create(srcPath)
                srcInfo = srcObj.getInfo()

            else:
                raise EUnknownSourceType

        debug("srcInfo = %s" % repr(srcInfo))

        return (srcPath, srcInfo, srcObj)

    def create(self, path, src = None):
        (srcPath, srcInfo, srcObj) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            self.__createDir(path, srcObj)
            return

        self.__createFile(path, srcObj)

    def update(self, path, src):
        (srcPath, srcInfo, srcObj) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            self.__updateDir(path, srcObj)
            return

        self.__updateFile(path, srcObj)

    def stripped(self):
        return self.path

    def relativeTo(self, path):
        strippedPath = self.stripped()

        if strippedPath == "/":
            strippedPath = ""

        expr = r'^%s/+' % strippedPath

        debug("Creating relative path from %s and %s" % (expr, path))
        return re.sub(expr, "", path)
