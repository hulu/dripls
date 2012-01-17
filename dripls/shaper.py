import cherrypy
import copy
import logging 
import os.path
import subprocess
from subprocess import *
import Queue
import urlparse
import urllib2
import uuid
import hashlib
import re

import conf.data
import conf
import httpls_client

#port shaping queue
port_queue = Queue.Queue()
shaper_store_path = "{0}/".format(os.path.dirname(os.path.realpath(__file__)))

def get_next_shape_port():
   if port_queue.empty():
       for port in range(conf.common.shape_start_port, conf.common.shape_end_port):
           port_queue.put(port)

   # rotate the port
   port = port_queue.get()
   port_queue.put(port)
   
   return port  

def generate_status(status):
    return conf.common.get_final_url("ostatus","s={0}".format(status))

def validate_match_rule_part(part):
    parts = part.split('.')
    if len(parts) > 3:
	return False
   
    #check segment part
    if len(parts) > 1 and not parts[-1][-1] == "k" and  not ( parts[-1][1:].isdigit() or parts[-1] == "*"):
        # check for range
        invalid_part = True

        if parts[-1].find('-') > 0:
            range = parts[-1][1:].split('-')
            invalid_part = not (range[0].isdigit() and range[1].isdigit())

        if invalid_part:
	    return False

    #check playlist part
    if len(parts) == 1 and parts[-1][-1] != "k" and parts[-1][-1] != "*":
        return False

    if len(parts) == 2 and ( parts[1][-1] != "k" and parts[1][-1] != "*") and ( parts[0][-1] != "k" and parts[0][-1] != "*"):
        return False       

    if len(parts) == 3 and parts[1][-1] != "k" and parts[1][-1] != "*":
        return False       

    return True

def expand_bitrate_match(matches, master_playlist_obj):
    if not master_playlist_obj:
        return matches

    return_matches = []
    for m in matches: 
        parts = m.split('.')

        has_range = False
        for i in range(0,len(parts)): 
           if parts[i][-1] == "k":
               #found bitrate segment
               if parts[i].find("-") < 0:
                  break

               has_range = True
               rng = parts[i].split("-")                  
               s_r = int(rng[0].replace("k","")) * 1000
               e_r = int(rng[1].replace("k","")) * 1000

               for vp in master_playlist_obj.keys():
                   bitrate = int(vp)
                   if s_r <= bitrate and bitrate <= e_r: 
                       parts[i] = "{0}k".format(bitrate/1000) 
                       return_matches.append(".".join(parts))
 
        if not has_range:
             return_matches.append(m)  
           

    return return_matches

def expand_segment_match(matches):
    return_matches = []
    for m in matches: 
       parts = m.split('.')

       if parts[-1].find('-') > 0:    
           t = parts[-1][0]
           rng = parts[-1][1:].split('-')
           for r in range( int(rng[0]), int(rng[1]) + 1 ):
               parts[-1] = "{0}{1}".format(t,r)

               return_matches.append('.'.join(parts))
       else:
           return_matches.append(m)
 
    return return_matches 

def expand_rule_match(match_part, master_playlist_obj):
    matches = [match_part]

    return expand_segment_match( expand_bitrate_match(matches, master_playlist_obj) )


def parse_rules(rule_string, master_playlist_obj = None):
    rules = {}

    if not rule_string:
        return rules

    rule_string = str(rule_string)

    try: 
        for rule in rule_string.split(","):
            rule_parts = rule.strip().split("~")
             
            action = rule_parts[1].strip()
            if not (action.startswith("e") or action.startswith("net")):
                raise ValueError("Unable to parse rule action {0}".format(action)) 

            match = rule_parts[0].strip()

            if not validate_match_rule_part(match):
                raise ValueError("Rule invalid: " + match)
            

            for r_match in expand_rule_match(match, master_playlist_obj):
                rules[r_match] = rule_parts[1].strip()

    except Exception, err:
        raise ValueError("Cannot parse rules : {0}, {1}".format(rule_string, str(err)))

    return rules

def parse_net_rule_action(rule_action):
    """ 

    Parse the rule action. Net rule consists of two parts: bandwidth, and packet loss. 
    Format is net<speed>.loss<%packetloss>. Speed is assumed to be in kbs and loss is
    in percentages.

    """

    # Default to traffic limit exceeding any practical bandwith limitations
    # Useful for scenarios where only packet loss is provided 
    traffic_limit = 100000

    traffic_loss = 0
    for netrule in rule_action.split("."):
        if netrule.startswith("net"):
            traffic_limit = int(netrule[3:])
        if netrule.startswith("loss"):
            traffic_loss = int(netrule[4:])
    
    return (traffic_limit, traffic_loss)


def segment_rule_rewrite(rules, playlist, segment, mock_shape_segment=False):
    """

    Given a set of rules and a segment in a playlist, find out whether the 
    segment is matched in any of the rules and if so perform the rule action
    
    Possible rule actions are e - raise HTTP error, net - traffic shape

    """

    # perform rule matching
    rule_action = segment_rule_match(rules,playlist, segment)

    # no rule match    
    if not rule_action:
        return None

    # generate error pages if a match found  
    if rule_action.startswith("e"):
        return generate_status(rule_action[1:]) 

    if rule_action.startswith("net"):
        return shape_segment(segment, rule_action, mock_shape_segment=mock_shape_segment)

    raise ValueError( "Cannot match action against appropriate set of actions : {0}".format(rule_action))      

def segment_rule_match(rules, playlist, segment):
    """

    Check if any rule matches the current segment. Generate the playlist/segment possible 
    rule permutation and test for rule hit. Work from more specific rules to more generic rules.
    If a rule is hit, no further checks will be made.

    """

    non_cdn_bandwidth_key = "{0}k".format(int(playlist["bandwidth"]) / 1000)
    cdn_bandwidth_key = "{0}.{1}".format(playlist["cdn"], non_cdn_bandwidth_key) 
    cdn_wildcard_key = "{0}.*".format(playlist["cdn"]) 
    wildcard_key = "*"

    for bandwidth_key in (cdn_bandwidth_key,non_cdn_bandwidth_key, cdn_wildcard_key, wildcard_key ):
        check_rules = []

        # playlist match 
        if (segment["type"] == "vplaylist"):
            if bandwidth_key in rules: 
                return rules[bandwidth_key]

            if "*" in rules:
                return rules["*"]

            continue
           
        # handle case of specific type rule
        segment_type = "{0}_segment".format(segment["type"])
        check_rules.append("{0}.{1}{2}".format(bandwidth_key, segment["type"][0], segment[segment_type])) 
        check_rules.append("{0}.{1}*".format(bandwidth_key, segment["type"][0])) 

        # handle case of general segment rule
        check_rules.append("{0}.s{1}".format(bandwidth_key, segment["segment"])) 
        check_rules.append("{0}.s*".format(bandwidth_key))
        check_rules.append("{0}.*".format(bandwidth_key))
        
        for rule in check_rules:
            if rule in rules: 
                rule_action = rules[rule].lower() 
                
                logging.debug("matched rule : {0} in segment: {1} ".format(rule, segment["url"]))
           
                return rule_action

def call_ext_shape_port(port, traffic_limit, traffic_loss, mock_shape_segment):
    """
    
    Call the external port shaper script to make sure that the desired rules are set for the port
    
    Warning: If executing user is not in sudoers, the operation will fail
    
    """

    shape_cmd = "sudo {0} {1} {2} {3}".format(conf.shaper_path, port, traffic_limit, traffic_loss) 
    logging.info("External shape call : {0} {1}".format(port, shape_cmd))

    if not mock_shape_segment:
        # execute non-interactive
        p = subprocess.Popen(["/usr/bin/sudo", "-n", conf.shaper_path, str(port), str(traffic_limit), str(traffic_loss)], stdin=subprocess.PIPE)
        p.wait()
        
        if p.returncode != 0:
            raise SystemError('Executing {0} failed with {1}'.format(conf.shaper_path, p.returncode))

def shape_segment(segment, rule_action, mock_shape_segment=False):
    """Cache the segment and call the external shaper script"""

    sid = hashlib.sha224(conf.data.provider.normalize_segment_url(segment["url"])).hexdigest()
       
    #cache the file if it hasn't been cached already
    s_filename = "{0}playlists/{1}.ts".format(shaper_store_path, sid)
    if (not os.path.exists(s_filename)):
        logging.debug("Fetching segment {0} ".format(segment["url"]))
        segment_content = urllib2.urlopen(segment["url"]).read()
        logging.debug("Done")

        with open(s_filename, "wb+") as segment_file:
            segment_file.write(segment_content)
            segment_file.close()
        
        with open("{0}.meta".format(s_filename), "wb+") as metadata_file:
            metadata_file.write(segment["url"])
            metadata_file.close()
    else: 
        logging.debug("Segment cached {0} ".format(segment["url"]))

       
    #shape port 
    port = get_next_shape_port()
    (traffic_limit, traffic_loss) = parse_net_rule_action(rule_action)
    call_ext_shape_port(port, traffic_limit, traffic_loss, mock_shape_segment)

    #return the final url
    return conf.common.get_final_url("s/{0}/playlists/{1}.ts".format(port, sid), "" )

def update_shaped_segment(url, rule_action, mock_shape_segment=False): 
    """A request requested an update of a segment post-playlist generation. Handle this here"""

    port_regex = re.search( "/s/(.*?)/" , url)

    if not port_regex:
        raise("Invalid url. Url must be shaped in order to be re-shaped")
    
    port = port_regex.group(0).replace("/s/","").rstrip('/')
    (traffic_limit, traffic_loss) = parse_net_rule_action(rule_action)
    logging.debug("{0} {1}".format(traffic_limit , traffic_loss))
    call_ext_shape_port(port, traffic_limit, traffic_loss, mock_shape_segment)

def cache_and_shape(master_playlist, seeded_content_id, rules, master_playlist_url = ''):
    """Returns shaped m3u8 playlist

    Process and shape a m3u8 playlist based on a set of rules 

    """

    shape_info = {}
    shape_info["id"] = seeded_content_id

    variant_playlists = httpls_client.get_variant_playlist_urls(master_playlist, master_playlist_url)

    for bitrate in variant_playlists.iterkeys():
        for alt in variant_playlists[bitrate].iterkeys():
            variant_playlist_desc = variant_playlists[bitrate][alt]
            variant_playlist = httpls_client.pull_variant_playlist( variant_playlist_desc["url"])

            # perform rewrite on the variant playlist url to local url or a rule matched url 
            seg_rewrite_url = segment_rule_rewrite(rules, variant_playlist_desc, variant_playlist_desc)
            local_rewrite_url = conf.common.get_final_url("playlist.m3u8","p=m_{0}_{1}_{2}".format(seeded_content_id, bitrate, alt))
            master_playlist = httpls_client.switch_segment( master_playlist, variant_playlist_desc["original_url"], seg_rewrite_url if seg_rewrite_url else local_rewrite_url )

            # don't process a playlist if it hit a rule (ie has been errored out)
            if seg_rewrite_url:
                shape_info["{0}.{1}".format(bitrate, alt)] = seg_rewrite_url
                continue
 
            # perform rule rewrite on segments within the variant playlist  
            for s in variant_playlist["segments"].iterkeys():
                seg_rewrite_url = segment_rule_rewrite(rules, variant_playlist_desc, variant_playlist["segments"][s])
                
                # rewrite local to full url playlist
                if variant_playlist["segments"][s]["original_url"] != variant_playlist["segments"][s]["url"]:
                    variant_playlist["content"] = httpls_client.switch_segment(variant_playlist["content"], variant_playlist["segments"][s]["original_url"], variant_playlist["segments"][s]["url"])

                # replace segment with shaped url
                if seg_rewrite_url:
                    variant_playlist["content"] = httpls_client.switch_segment(variant_playlist["content"], variant_playlist["segments"][s]["url"], seg_rewrite_url)
                    variant_playlist["segments"][s]["url"] = seg_rewrite_url
                    shape_info["{0}.{1}.s{2}".format( bitrate, alt, s)] = seg_rewrite_url

            httpls_client.store_playlist(variant_playlist["content"], shaper_store_path + "playlists/m_{0}_{1}_{2}.m3u8".format(seeded_content_id, bitrate, alt))

         
    httpls_client.store_playlist(master_playlist, shaper_store_path + "playlists/m_{0}.m3u8".format(seeded_content_id))
    return shape_info
    

