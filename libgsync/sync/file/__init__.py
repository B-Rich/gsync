# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime, time, posix, pickle, dateutil.parser, re
from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes

# PACK FORMAT:
# L = PACK_SERIAL L
# I = uid
# I = gid
# I = mode

class SyncFileInfo(object):
    # Note: The description field is currently overloaded to also provide
    #       custom metadata tags that currently aren't facilitated by Google
    #       Drive.
    def __init__(self, id, title, modifiedDate, mimeType,
                 description = None, **misc):

        self.id = id
        self.title = title
        self.modifiedDate = modifiedDate
        # ISO 8601 date format
        self.__modifiedDate = dateutil.parser.parse(
            modifiedDate, ignoretz=True)
        self.mimeType = mimeType
        self.statInfo = None
        self.description = None
        index = 1

        if isinstance(description, str):
            self.description = description
            try:
                self.statInfo = pickle.loads(description.decode("hex"))
            except pickle.UnpicklingError:
                pass
            except EOFError:
                pass

        elif isinstance(description, posix.stat_result):
            try:
                self.description = pickle.dumps(description).encode("hex")
            except pickle.PicklingError:
                pass

    def __gt__(self, fileInfo):
        return bool(self.__modifiedDate > fileInfo.__modifiedDate)

    def __lt__(self, fileInfo):
        return bool(self.__modifiedDate < fileInfo.__modifiedDate)

    def __ge__(self, fileInfo):
        return bool(self.__modifiedDate >= fileInfo.__modifiedDate)

    def __le__(self, fileInfo):
        return bool(self.__modifiedDate <= fileInfo.__modifiedDate)

    def __eq__(self, fileInfo):
        return bool(self.__modifiedDate == fileInfo.__modifiedDate)

    def __ne__(self, fileInfo):
        return bool(self.__modifiedDate != fileInfo.__modifiedDate)


class SyncFile(object):
    path = None

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def __add__(self, path):
        return os.path.join(self.path, path)

    def getInfo(self, path = None):
        raise ESyncFileAbstractMethod

    def _createDir(self, path):
        raise ESyncFileAbstractMethod

    def _createFile(self, path, src):
        raise ESyncFileAbstractMethod

    def _updateFile(self, path, src):
        raise ESyncFileAbstractMethod

    def _normaliseSource(self, src):
        srcInfo = None

        if src is not None:
            if not isinstance(src, SyncFile):
                from libgsync.sync.file.factory import SyncFileFactory
                src = SyncFileFactory.create(src)

            srcInfo = src.getInfo()

        return (src, srcInfo)

    def create(self, path, src = None):
        (src, srcInfo) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            self._createDir(path)
            return

        self._createFile(path, src)

    def update(self, path, src):
        (src, srcInfo) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            return

        self._updateFile(path, src)

    def stripped(self):
        return self.path

    def relativeTo(self, path):
        strippedPath = self.stripped()

        if strippedPath == "/":
            strippedPath = ""

        expr = r'^%s/+' % strippedPath

        debug("Creating relative path from %s and %s" % (expr, path))
        return re.sub(expr, "", path)
