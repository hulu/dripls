from __future__ import with_statement
import sys
import random
import re
import shutil
import urllib
import urllib2
import urlparse
import base64
import subprocess
import conf.data
import cherrypy

def switch_segment(playlist_contents, old_segment, new_segment):
    """ Replace a segment from the original playlist with a new segment """

    new_contents = playlist_contents.replace(old_segment, new_segment)
    return new_contents

def store_playlist(playlist_contents, path):
    """ Store playlist locally """ 
    with open(path, "w") as p_file:
        p_file.writelines(playlist_contents)

def rewrite_ext_key(playlist_url, keyext):
    parts = keyext.split(',')
    key_parts = []

    for part in parts:
        kv = part.split('=')

        if kv[0].strip() == "URI":
            key_url = '='.join(kv[1:])
            kv[1] = "\"{0}\"".format( urlparse.urljoin(playlist_url, key_url.strip('"')) )
            url_part = '='.join([kv[0] , key_url])
            key_parts.append(url_part)
        else:
            key_parts.append(part)

    return ','.join(key_parts)


def pull_variant_playlist(url):
    """ Pull a variant playlist's content """

    variant_playlist = {}
    playlist_response = urllib2.urlopen(url)
    variant_playlist["url"] = url
    variant_playlist["content"] = playlist_response.read()
    variant_playlist["segments"] = {}
    
    try:
        segment_counts = {}

        ext = ""
        for line in variant_playlist["content"].splitlines():
            if line.startswith("#EXT"):
                # replace key with fullpath key
                if line.startswith("#EXT-X-KEY:"):
                    orig_line = line
                    line = rewrite_ext_key(url, orig_line)

                    variant_playlist["key_ext"] = line
                    variant_playlist["content"] = variant_playlist["content"].replace(orig_line, line)
                    
            else:
                type = conf.data.provider.get_segment_type(line)            
           
                if not "segment" in segment_counts:
                    segment_counts["segment"] = 0
                else:
                    segment_counts["segment"] += 1
  
                if not type in segment_counts:
                    segment_counts[type] = 0
                else:
                    segment_counts[type] += 1

                variant_playlist["segments"][segment_counts["segment"]] = { 
                   "url": urlparse.urljoin(url, line), 
                   "original_url": line, 
                   "segment": segment_counts["segment"], 
                   "{0}_segment".format(type): segment_counts[type],
                   "type":type,
                   "ext":ext
                }
    except:
        raise RuntimeError("Unable to parse playlist content at url: {0}".format(url) )
    
    return variant_playlist

def get_variant_playlist_urls(main_playlist, master_playlist_url = '' ):
    """ Extract variant playlists from the main playlist """

    variant_uris = {}
    bandwidth = None
    ext = ""

    try:
        for line in main_playlist.splitlines():
            line = line.strip()
            if len(line) > 0:
               if line.startswith("#EXT"):
                   ext = line
                   for arg in line.split(","):
                       if arg.strip().startswith("BANDWIDTH"):
                          bandwidth = arg.split("=")[1].strip()
               else:
                   if not bandwidth:
                       continue

                   if not bandwidth in variant_uris: 
                       variant_uris[str(bandwidth)] = {}
               
                   variant_uris[str(bandwidth)][conf.data.provider.get_cdn_from_playlist_url(line)] = {
                       "url": urlparse.urljoin(master_playlist_url, line), 
                       "original_url" : line, 
                       "type":"vplaylist", 
                       "bandwidth":bandwidth, 
                       "cdn" : conf.data.provider.get_cdn_from_playlist_url(line), 
                       "ext":ext}
    except:
        raise ValueError("Unable to parse master playlist's content")

    return variant_uris


