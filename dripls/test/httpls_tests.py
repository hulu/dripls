import unittest
import os

import httpls_client

class TestHttpLiveStreamClient(unittest.TestCase):
    test_path = ""

    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))
        return
        
    def tearDown(self):
        return


    def test_pull_master_playlist(self):
        master_playlist = open(self.test_path + "/wt_suite/wt_dripls/wt.m3u8","r").read()
        v_playlists = httpls_client.get_variant_playlist_urls(master_playlist)

        #test with a master playlist
        c = 0
        for bandwidth in v_playlists.iterkeys():
            for cdn in v_playlists[bandwidth].iterkeys():
                self.assertTrue(v_playlists[bandwidth][cdn]["type"] == "vplaylist")
                self.assertTrue(v_playlists[bandwidth][cdn]["url"] != None)
                c += 1
        self.assertTrue( c > 0)

        # test with a non-master playlist
        not_master_playlist = open(self.test_path + "/wt_suite/wt_dripls/wt_1700k.m3u8","r").read()
        v_playlists = httpls_client.get_variant_playlist_urls(not_master_playlist)
        for bandwidth in v_playlists.iterkeys():
            for cdn in v_playlists[bandwidth].iterkeys():
               self.fail("found a variable playlist inside a vplaylist")    
            
        return 

    def test_pull_variant_playlist(self):
    
        # test a read of a vplaylist and its decomposition 
        local_url = "file://" + os.path.abspath(self.test_path + "/wt_suite/basic/wt_1000k_asset_ad.m3u8") 
        v_playlist =  httpls_client.pull_variant_playlist(local_url)
        
        self.assertTrue( v_playlist["url"] != None) 
        self.assertTrue( v_playlist["content"] != None) 
        
        for segment in v_playlist["segments"].iterkeys():
           self.assertTrue ( v_playlist["segments"][segment]["url"] != None)
           self.assertTrue ( v_playlist["segments"][segment]["segment"] != None)
           self.assertTrue ( v_playlist["segments"][segment]["type"] != None)
             
           if ( v_playlist["segments"][segment]["type"] == "content"):
               self.assertTrue ( v_playlist["segments"][segment]["content_segment"] != None)

        return
 
    def test_switch_segment(self):

        # test switch with master playlist
        master_playlist = open(self.test_path + "/wt_suite/wt_dripls/wt.m3u8","r").read()
        v_playlists = httpls_client.get_variant_playlist_urls(master_playlist)
         
        c = 0 
        for bandwidth in v_playlists.iterkeys():
            for cdn in v_playlists[bandwidth].iterkeys():
                c += 1
                replace_segment = "http://testsegment" + str(c)
                master_playlist = httpls_client.switch_segment(master_playlist, v_playlists[bandwidth][cdn]["url"], replace_segment) 
                self.assertTrue( master_playlist.find(v_playlists[bandwidth][cdn]["url"]) == -1 ) 
                self.assertTrue( master_playlist.find( replace_segment) != -1 ) 
        
        variant_playlist = open(self.test_path + "/wt_suite/wt_dripls/wt_1700k.m3u8","r").read()

        return
