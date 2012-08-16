import unittest
import cherrypy
import urllib
import urlparse
import os

import shaper, httpls_client, conf, progressive, main

class TestProgressiveRuleMatcher(unittest.TestCase):
    test_path = ""

    def setUp(self):
        self.test_path = os.path.dirname(os.path.realpath(__file__))

        return
        
    def tearDown(self):
        return

    def test_simple_rule_matching(self):

        # Test simple matching
        matcher = progressive.from_rules("b501-1024~e404")
        self.assertIsNotNone(matcher)

        action = matcher.get_action(0, 500)
        self.assertIsNone(action, "Byte range before the rule start")

        action = matcher.get_action(600, 1000)
        self.assertEqual("e404", action, "Byte range in the middle of the rule start and end")

        action = matcher.get_action(1050, 2000)
        self.assertIsNone(action, "Byte range after the rule end")

        action = matcher.get_action(200, 600)
        self.assertEqual("e404", action, "Byte range contains the rule start")
        
        action = matcher.get_action(800, 1400)
        self.assertEqual("e404", action, "Byte range contains the rule end")

        action = matcher.get_action(200, 1400)
        self.assertEqual("e404", action, "Byte range encloses the entire rule")

        action = matcher.get_action(501, 1024)
        self.assertEqual("e404", action, "Byte range exactly the same as rule")

    def test_rule_collision_matching(self):
        
        matcher = progressive.from_rules("b500-1000~e404,b2000-2500~net20")
        self.assertIsNotNone(matcher)

        action = matcher.get_action(0,501)
        self.assertEqual("e404", action, "Only matches the first")

        action = matcher.get_action(1500, 2100)
        self.assertEqual("net20", action, "Only matches the second")

        action = matcher.get_action(500, 2100)
        self.assertEqual("e404", action, "Matches more of the first than the second")

        action = matcher.get_action(900, 2500)
        self.assertEqual("net20", action, "Matches more of the second than the first")

        action = matcher.get_action(500, 2500)
        self.assertEqual("e404", action, "Matches equally, so we choose the earliest match")

    def test_rule_validation(self):

        self.assertIsNotNone(progressive.from_rules("b1-2~e404"))
        self.assertIsNotNone(progressive.from_rules("b1-*~e404"))
        self.assertIsNotNone(progressive.from_rules("b1-1000~net20"))
        self.assertIsNotNone(progressive.from_rules("b1-1000~net20,b1100-*~e404"))
        self.assertRaises(ValueError, progressive.from_rules, "foo")
        self.assertRaises(ValueError, progressive.from_rules, ",")
        self.assertRaises(ValueError, progressive.from_rules, "~")
        self.assertRaises(ValueError, progressive.from_rules, "~e404")
        self.assertRaises(ValueError, progressive.from_rules, "b1-2~")
        self.assertRaises(ValueError, progressive.from_rules, "b1-2~e404,")
        self.assertRaises(ValueError, progressive.from_rules, "b1-2~e404,~")
        self.assertRaises(ValueError, progressive.from_rules, "b1-2~e404,~")
        self.assertRaises(ValueError, progressive.from_rules, "1-2~e404")
        self.assertRaises(ValueError, progressive.from_rules, "b1-~e404")
        self.assertRaises(ValueError, progressive.from_rules, "b-1000~e404")

        self.assertRaises(ValueError, progressive.from_rules, "b1-1000~e404,b999-2000~e404")
        self.assertRaises(ValueError, progressive.from_rules, "b1000-2000~e404,b0-1000~e404")

class StubCherryPyRequest(object):

    def __init__(self):
        self.headers = []


class TestProgressiveEndpoint(unittest.TestCase):

    def setUp(self):
        self._dripls = main.DriplsController()
        self._original_url = "http://original.com/file.mp4"

    def test_no_matching_rule(self):
        request  = StubCherryPyRequest()
        request.headers = {'Range': 'bytes=1-512'}
        rule = "b1024-2056~e404"

        self.assertEqual(self._original_url, self._dripls._handle_progressive_rules(self._original_url, rule, request, True))

    def test_matching_rule_with_error_action(self):
        request  = StubCherryPyRequest()
        request.headers = {'Range': 'bytes=512-1500'}
        rule = "b1024-2056~e404"

        with self.assertRaises(cherrypy.HTTPError):
            self._dripls._handle_progressive_rules(self._original_url, rule, request, True)

    def test_matching_rule_with_net_action(self):
        request  = StubCherryPyRequest()
        request.headers = {'Range': 'bytes=512-1500'}
        rule = "b1024-2056~net20"
        self.assertRegexpMatches(self._dripls._handle_progressive_rules(self._original_url, rule, request, True),
                                 r"http://127.0.0.1:8080/s/\d{4,6}/progressive\?url=%s&from_dripls=1" % urllib.quote_plus(self._original_url))

    def test_matching_with_no_range(self):
        request  = StubCherryPyRequest()
        rule = "b1024-2056~net20"
        self.assertRegexpMatches(self._dripls._handle_progressive_rules(self._original_url, rule, request, True),
                                 r"http://127.0.0.1:8080/s/\d{4,6}/progressive\?url=%s&from_dripls=1" % urllib.quote_plus(self._original_url))


