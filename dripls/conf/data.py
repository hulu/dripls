"""
   Base data provider for customizable options that allow for extending the way that dripls fetches and shapes playlists 
"""

import cherrypy
import urlparse
import hashlib
import uuid
import re
import os
import urllib2

import common


class HttplsProvider( object ):
    """To provide custom httpls provider logic, inherit this class""" 
    
    base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    def get_cdn_from_playlist_url(self, url):
        """Seeds the cid in a format that is acceptable for debugging purposes"""
          
        # overwrite with appropriate extraction method, this is a sample 
        kargs = urlparse.parse_qs(urlparse.urlparse(url).query)

        if "cdn" in kargs:
            return kargs["cdn"][0]
        else:
             return "_d" #default 

    def normalize_segment_url(self, url):
        """Returns a hash that can uniq a url"""
        
        return re.sub("authToken=(.*?)(?:&|$)", "-", url)
           
    def get_segment_type(self, url):
        """Returns the type of the segment (ad, content, etc)"""

        # Note : This is just a sample of how you can extend
        #        the provider so that rule matching can be done
        #        on different segment types
        #
        # if url.startswith("http://asset"):
        #     return "asset"
        # 
        # if url.startswith("http://ad"):
        #     return "ad"

        return "content"

    def get_tag_kwargs(self, kwargs):
        """Strip arguments that are not tag relevant and may contain sensitive information"""
        
        # by default nothing sensative, so return everything
        return kwargs

    def pull_master_m3u8(self, cid, kwargs):
        """
        
        Return the master m3u8 playlist contents. This function is generally outside of httpls_client
        because to get to the master playlist from an arbitrary cid could require a number of custom steps or custom auth.
        Additionally all params to the call to dripls are passed, which allows extra parameters to be processed and used 
        for the pulling of the master m3u8 playlist.
             
        """

        if not cid:
            raise ValueError("Invalid content token specified")

        # if wt is requested , shortcut and use the local playlist
        if cid == "wt":
            return  urllib2.urlopen("file://" + self.base_path + "/playlists/wt.m3u8").read()

        raise ValueError("Unable to find provider that can fetch cid = {0} ".format(cid))


"""Overwrite the provider with a derived class from HttlsProvider"""
provider = HttplsProvider()


