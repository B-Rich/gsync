#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.sync.file import SyncFile

class TestSyncFile(unittest.TestCase):
    def test_SyncFile_relativeTo(self):
        f = SyncFile("/gsync_unittest")

        self.assertEqual(
            f.relativeTo("/gsync_unittest/open_for_read.txt"),
            "open_for_read.txt"
        )
