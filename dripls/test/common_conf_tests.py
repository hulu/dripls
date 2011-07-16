import unittest
import os

from conf import common, data

class TestConfCommonStream(unittest.TestCase):

    def setUp(self):
        return
        
    def tearDown(self):
        return


    def test_consistent_hash(self):
        self.assertTrue( data.provider.normalize_segment_url("http://www.test.com/abc") == data.provider.normalize_segment_url("http://www.test.com/abc"))
        self.assertTrue( data.provider.normalize_segment_url("http://www.test.com/nbc") != data.provider.normalize_segment_url("http://www.test.com/abc"))

        #test stripping of some attributes to achieve consistent hashing
        self.assertTrue( data.provider.normalize_segment_url("http://www.test.com/abc?authToken=123") == data.provider.normalize_segment_url("http://www.test.com/abc?authToken=321"))
        return 
