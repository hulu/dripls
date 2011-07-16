import unittest
import shutil
import json
import os

import shaper, main, httpls_client, conf

class MockHTTPLSProvider(conf.data.HttplsProvider):
    def __init__(self):
        self.base_path = os.path.dirname(os.path.realpath(__file__))

    def get_segment_type(self, url):
        if url.startswith("http://asset"):
            return "asset"
 
        if url.startswith("http://ad"):
            return "ad"

        return "content"


conf.data.provider = MockHTTPLSProvider()

class TestShaper(unittest.TestCase):
    test_path = ""

    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))

        for each in os.listdir("%s/playlists" % self.test_path):
            os.remove("%s/playlists/%s" % (self.test_path,each))
        
        for each in os.listdir("%s/wt_suite/local" % self.test_path):
            p = open(self.test_path + "/wt_suite/local/%s" % each,"r").read()
            p = p.replace("{local}",  "file://" + self.test_path + "/wt_suite/local")

            with open(self.test_path + "/playlists/%s" % each, "wb+") as pf:
                pf.write(p)  
      
        shaper.shaper_store_path = "%s/" % self.test_path
        return
        
    def tearDown(self):
        return

    def test_tag(self):
        service = main.DriplsController()
        service.cache_info("wt","1000k.s0~e404","tag1",authkey="sample") 

        self.assertTrue( open("%s/playlists/tag_tag1" % (self.test_path) ).read().find("authkey=sample&r=1000k.s0%7Ee404&cid=wt") != -1)

        playlist_contents = service.tag_m3u8("tag1")
        self.assertTrue( playlist_contents != None)

    def test_cache_and_shape_info(self):
        service = main.DriplsController()
        info = service.cache_info("wt","1000k.s0~e404","tag1",authkey="sample")

        self.assertTrue( "1000000._d.s0" in info)
        self.assertTrue( "url" in info)

        playlist_contents = service.playlist_m3u8( "m_%s" % json.loads(info)["id"] ) 
        self.assertTrue( playlist_contents != None)

    def test_master_m3u8(self):
        service = main.DriplsController()
        playlist_contents = service.master_m3u8("wt", None ,"tag1",authkey="sample")
        
        self.assertTrue( playlist_contents != None)

         
