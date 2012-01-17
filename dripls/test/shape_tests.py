import unittest
from urlparse import urlparse
import os

import shaper, httpls_client, conf

class TestShaper(unittest.TestCase):
    test_path = ""

    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))

        for each in os.listdir( "%s/playlists" % self.test_path  ):
            os.remove("%s/playlists/%s" % (self.test_path,each))

        self.master_playlist = open(self.test_path + "/wt_suite/wt_dripls/wt.m3u8","r").read()
        self.master_loc_playlist = open(self.test_path + "/wt_suite/local/wt.m3u8","r").read().replace("{local}", "file://" + self.test_path + "/wt_suite/local")

        local_url = "file://" + os.path.abspath(self.test_path + "/wt_suite/basic/wt_1000k_asset_ad.m3u8")
        self.v_playlist_1000k =  httpls_client.pull_variant_playlist(local_url)
        self.v_playlist_1000k["bandwidth"] = 1000000
        self.v_playlist_1000k["cdn"] = "a"
        self.v_playlist_1000k["type"] = "vplaylist"
 
        self.s0_1000k = self.v_playlist_1000k["segments"][0]

        self.s0_1000k_mock = self.v_playlist_1000k["segments"][0].copy()
        self.s0_1000k_mock["url"] =  "file://" + os.path.abspath(self.test_path + "/wt_suite/basic/mock_segment.ts")

        self.c0_1000k = next( self.v_playlist_1000k["segments"][s] for s in self.v_playlist_1000k["segments"] if self.v_playlist_1000k["segments"][s]["type"] == "content" )   
        self.a0_1000k = next( self.v_playlist_1000k["segments"][s] for s in self.v_playlist_1000k["segments"] if self.v_playlist_1000k["segments"][s]["type"] == "ad" )   
        self.as0_1000k = next( self.v_playlist_1000k["segments"][s] for s in self.v_playlist_1000k["segments"] if self.v_playlist_1000k["segments"][s]["type"] == "asset" )   


        self.mpl = {}
        self.mpl["400000"] = {}
        self.mpl["400000"]["__d"] = { "url": "http://test.com", "original_url" : "http://test.com", "type":"vplaylist", "bandwidth":400000, "cdn" : "__d"}
        self.mpl["650000"] = {}
        self.mpl["650000"]["__d"] = { "url": "http://test.com", "original_url" : "http://test.com", "type":"vplaylist", "bandwidth":650000, "cdn" : "__d"}
        self.mpl["1000000"] = {}
        self.mpl["1000000"]["__d"] = { "url": "http://test.com", "original_url" : "http://test.com", "type":"vplaylist", "bandwidth":1000000, "cdn" : "__d"}
        self.mpl["1000000"]["v"] = { "url": "http://test.com", "original_url" : "http://test.com", "type":"vplaylist", "bandwidth":1000000, "cdn" : "__d"}
        self.mpl["1000000"]["c"] = { "url": "http://test.com", "original_url" : "http://test.com", "type":"vplaylist", "bandwidth":1000000, "cdn" : "__d"}
        self.mpl["4000000"] = {}
        self.mpl["4000000"]["__d"] = { "url": "http://test.com", "original_url" : "http://test.com", "type":"vplaylist", "bandwidth":4000000, "cdn" : "__d"}

        shaper.shaper_store_path = "%s/" % self.test_path
        return
        
    def tearDown(self):
        return

    def test_rule_parse_with_mpl(self):
        rules = shaper.parse_rules("v.400k-4000k.s1-10~e404", self.mpl)
        self.assertTrue(rules["v.400k.s5"] == "e404")
        self.assertTrue(rules["v.650k.s5"] == "e404")
        self.assertTrue(rules["v.4000k.s5"] == "e404")

        rules = shaper.parse_rules("v.400k-4000k~e404", self.mpl)
        self.assertTrue(rules["v.400k"] == "e404")

        rules = shaper.parse_rules("400k-4000k~e404", self.mpl)
        self.assertTrue(rules["400k"] == "e404")

        rules = shaper.parse_rules("*~e404,1000-2000k~e500", self.mpl)
        self.assertTrue(rules["1000k"] == "e500")

        rules = shaper.parse_rules("*~e404,*.*.s10-20~net10", self.mpl)
        self.assertTrue(rules["*.*.s12"] == "net10")




    def test_rule_parse(self):
        rules = shaper.parse_rules("*.*~e404")
        self.assertTrue(rules["*.*"] == "e404")
        self.assertTrue(shaper.parse_rules(None) == {})

        self.assertRaises(ValueError, shaper.parse_rules, "*.-404")

        #test out [cdn][bitrate][segment]        
        rules = shaper.parse_rules("v.*.*~e404")
        rules = shaper.parse_rules("v.*.*~net100.loss10")

        #test out range rules
        rules = shaper.parse_rules("v.*.c1-10~e404")
        rules = shaper.parse_rules("v.1000k.c1-10~e404")
        self.assertTrue(rules["v.1000k.c5"] == "e404")
        rules = shaper.parse_rules("v.1000k.s1-10~e404")
        self.assertTrue(rules["v.1000k.s5"] == "e404")

        #segment multiple rules
        rules = shaper.parse_rules("v.650k.*~net100.loss10, *~ e404 ,500k~net100")
        self.assertTrue(rules["*"] == "e404")           

        self.assertRaises(ValueError, shaper.parse_rules, "*.c0-12fa~e404,650k.c0~e404")
        self.assertRaises(ValueError, shaper.parse_rules, "*.c0~e404,*,650k.c0~e404")
        self.assertRaises(ValueError, shaper.parse_rules, "*.c0~404,*,650k.c0~e404")

        return
 
    def test_status_gen(self):
        status_url = shaper.generate_status(404)
        s = urlparse(status_url)
        self.assertTrue(s.query == "s=404")

    def test_port_queue(self):
        p = shaper.get_next_shape_port()
        p2 = shaper.get_next_shape_port()
           
        self.assertTrue ( p != None and p2 != None and p != p2)
        
    def test_segment_rule_match_vplaylist(self):
        v_playlists_desc = httpls_client.get_variant_playlist_urls(self.master_playlist)
       
        p4000k = next( v_playlists_desc["4000000"].itervalues())
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("4000k~e404"), p4000k, p4000k) != None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("650k~e404"), p4000k, p4000k) == None )

        master_cdn_playlist = open(self.test_path + "/wt_suite/basic/wt_master_cdn_fallback.m3u8","r").read()
        v_playlists_cdn_desc = httpls_client.get_variant_playlist_urls(master_cdn_playlist)
    
        p4000k_a =  v_playlists_cdn_desc["4000000"]["a"]
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("b.4000k~e404"), p4000k_a, p4000k_a) == None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("a.4000k~e404"), p4000k_a, p4000k_a) != None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("4000k~e404"), p4000k_a, p4000k_a) != None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("*~e404"), p4000k_a, p4000k_a) != None )
        
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k.s0~e404,1000k~e500"), self.v_playlist_1000k, self.v_playlist_1000k) != None )
 
    def test_segment_rule_match_segment(self):
        # test rule matching with regular segments      
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k~e404"), self.v_playlist_1000k, self.s0_1000k) == None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k.s1~e404"), self.v_playlist_1000k, self.s0_1000k) == None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k.s0~e404"), self.v_playlist_1000k, self.s0_1000k) == "e404" )

        # test rule matching with content segments
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k.c0~e404"), self.v_playlist_1000k, self.c0_1000k) == "e404" )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k.*~e404"), self.v_playlist_1000k, self.c0_1000k) == "e404" )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("1000k.c0~e404"), self.v_playlist_1000k, self.s0_1000k) == None )

        # test rule matching with cdn and segments
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("a.*.c0~e404"), self.v_playlist_1000k, self.c0_1000k) == "e404" )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("b.*.c0~e404"), self.v_playlist_1000k, self.c0_1000k) == None )
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("a.*.*~e404"), self.v_playlist_1000k, self.c0_1000k) == "e404" )

        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("a.*.*~net100.loss10"), self.v_playlist_1000k, self.c0_1000k) == "net100.loss10")

        # specific rule takes precedencee
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("a.*.*~net100.loss10,1000k.c0~e404"), self.v_playlist_1000k, self.c0_1000k) == "e404")
        self.assertTrue( shaper.segment_rule_match(shaper.parse_rules("a.*.*~net100.loss10,1000k.s0~net100"), self.v_playlist_1000k, self.s0_1000k) == "net100")

    def test_segment_shape(self):
        self.assertTrue( shaper.segment_rule_rewrite(shaper.parse_rules("1000k~e400"), self.v_playlist_1000k, self.v_playlist_1000k) == shaper.generate_status(400))

        self.assertTrue( shaper.segment_rule_rewrite(shaper.parse_rules("1000k.s0~e404"), self.v_playlist_1000k, self.s0_1000k) == shaper.generate_status(404))
        self.assertTrue( shaper.segment_rule_rewrite(shaper.parse_rules("1000k.s1~e404"), self.v_playlist_1000k, self.s0_1000k) == None)
  
        self.assertTrue( shaper.segment_rule_rewrite(shaper.parse_rules("1000k.s0~net100.loss10"), self.v_playlist_1000k, self.s0_1000k_mock, mock_shape_segment=True) != None)
        self.assertTrue( shaper.segment_rule_rewrite(shaper.parse_rules("1000k.*~net100.loss10"),self.v_playlist_1000k, self.s0_1000k_mock, mock_shape_segment=True) != None)

        self.assertRaises(ValueError, shaper.segment_rule_rewrite, {"1000k.*":"404"}, self.v_playlist_1000k, self.s0_1000k_mock)
      
    def test_cache_and_shape(self):
        seeded_cid = conf.common.get_seeded_cid("wt")
      
        shaper.cache_and_shape(self.master_loc_playlist, seeded_cid, shaper.parse_rules("1000k.s0~e404,4000k~e500"))
                
        self.assertTrue( open("%s/playlists/m_%s.m3u8" % (self.test_path, seeded_cid) ).read().find("s=500") != -1)
        self.assertTrue( open("%s/playlists/m_%s_1000000__d.m3u8" % (self.test_path, seeded_cid) ).read().find("s=404") != -1)

        pass

