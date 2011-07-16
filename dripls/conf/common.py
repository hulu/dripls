import cherrypy
import urlparse
import uuid
import os

# Service
socket = '0.0.0.0'
dripls_main_site_port = 8080
thread_pool = 10

bin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "bin")
pidfile = os.path.join(bin_path, "dripls.pid")
error_log = os.path.join(bin_path, "error_log.log")

app = {
  'root_url': cherrypy.url()
}

# Shaper path
shaper_path = os.path.join(bin_path, "set_ts_lo.sh")

# Shape port range 
shape_start_port = 10000
shape_end_port = 11000

# Environment overrides
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), "env.py")):
    from env import *
else:
    from local import *

port = int(dripls_main_site_port)

# Final url rewrite. Hack to battle the fact that cherrypy is behind a proxy on different port  
def get_final_url(path, args):
    cherrypy_url = cherrypy.url(path, args)
    
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(cherrypy_url)
    return urlparse.urlunsplit( (scheme, urlparse.urlsplit(app['root_url'])[1], path, qs, anchor))

def get_seeded_cid(cid):
    return "{0}_{1}".format(cid, uuid.uuid4().hex)
