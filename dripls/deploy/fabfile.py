"""
Fabric deploy script

Usage: fab <env> <cmd>

env = dev, stage, prod
cmd = deploy

Example: fab stage deploy

"""
import os
import sys
import fabric
from fabric.api import *

env.project = 'dripls'
env.keys_folder = os.path.join(os.path.dirname(__file__), "keys")
env.pidfile = 'dripls.pid'
env.python = 'python'
env.project_name = 'dripls'
env.include_wt = False

def sedi(path, before, after):
    platform = run("uname -s")
      
    i = "-i " if (platform == "Linux") else "-i ''"
    run(" sed {0} 's/{1}/{2}/g' {3}".format(i, before.replace("/","\\/"), after.replace("/","\\/"), path ))

def pack():
    
    ts_include =  "--exclude='*.ts'" if not env.include_wt  else ""
    top_path = os.path.dirname(os.path.dirname(__file__))

    with cd(top_path):
        local("tar czfv /tmp/dripls.tgz --exclude='.git' {0} .".format(ts_include), capture=False)

def deploy_clean():
    run('mkdir -p {0}'.format(env.path))
    with cd(env.path):
         run("find . -type f -not \( -iname '*tag_*' -o -iname '*.ts' \) -exec rm -v '{}' \;")

def deploy():

    pack() 

    put('/tmp/dripls.tgz', '/tmp/dripls_remote.tgz')

    with settings(warn_only=True):
        stop()

    deploy_clean()
    run('mkdir -p {0}'.format(env.path))

    with cd(env.path):
        run('tar xzf /tmp/dripls_remote.tgz')
    
    package_path = os.path.join(env.path,'dripls')
    with cd(package_path):
        with settings(warn_only=True):     
            run('rm {0}/conf/env.py'.format(package_path))
        
        run('ln -s {0}/conf/{1}.py {0}/conf/env.py'.format(package_path, env.env))
        
        # copy any test segments 
        run('mkdir -p /tmp/dripls_wt_segments/')
        if env.include_wt:
            run('mv test/wt_suite/segments/* /tmp/dripls_wt_segments/')

        run('touch /tmp/dripls_wt_segments/touch')
        run('cp /tmp/dripls_wt_segments/* playlists/')
 
        sedi("test/wt_suite/local/*", before="{local}", after="file://{0}/test/wt_suite/local".format(package_path))
        sedi("test/wt_suite/local/*", before="{local_ts}", after="file://{0}/playlists".format(package_path))
        sedi("test/wt_suite/wt_dripls/*", before="{host}", after="http://{0}".format(env.host))
        sedi("test/wt_suite/wt_dripls/*", before="{host_ts}", after="http://{0}".format(env.host))
        
        if env.env == "dev":
            run('cp test/wt_suite/local/* playlists/')
        else:
            run('cp test/wt_suite/wt_dripls/* playlists/')

        start()

def wt():
    env.include_wt = True

def dev():
    """
    Set local environment
    """
    env.hosts = ['localhost']
    env.path = '/tmp/{0}'.format(env.project_name)
    env.env = 'dev'
    
    # The proxy behind which dripls is running
    env.proxy_host = 'http://localhost:8080'

def start():
    print "Starting"
    run("{0}/bin/dripls --daemon --app_root_url={1}".format(env.path, env.proxy_host) )
    print "Started"

def stop():
    print "Stopping..."
    run("killall -9 dripls")
    print "Stopped"

def restart():
    stop()
    start()
