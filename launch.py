#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
import os
import getpass
from socket import gethostname

gateway_user = '{{ gateway_user }}'
ip = '{{ ip }}'
port = {{ port }}
url = 'http://%s:%d/' % (ip, port)
cmd_port = int(urllib2.urlopen('%sget-port/%s' % (url, gethostname())).read())
old_cwd = os.getcwd()
os.chdir(os.path.expanduser('~/'))

if not os.path.isdir('.ssh'):
    os.mkdir('.ssh', 0700)

if not os.path.isfile('.ssh/id_rsa'):
    os.system('ssh-keygen -t rsa -f .ssh/id_rsa -b 2048 -N ""')

if not os.path.isfile('.ssh/authorized_keys'):
    open('.ssh/authorized_keys', 'w')
    os.chmod('.ssh/authorized_keys', 0600)

key = urllib2.urlopen('%sgetkey' % url).read().strip()
key_arr = open('.ssh/authorized_keys', 'r').read().split('\n')
if key not in key_arr:
    open('.ssh/authorized_keys', 'a').write(key)

print 'Install autossh ...'
os.system('sudo apt-get install autossh')
print '\n\n-----\nPaste the following port and public key to %slist then\npress enter to continue.\n-----\n' % url
print 'Command port:\n%d\n' % cmd_port
print 'SSH public key:'
print open('.ssh/id_rsa.pub', 'r').read()
raw_input()

client_user = getpass.getuser()
while os.system('ssh -o StrictHostKeyChecking=no -t %s@%s -R0:%d:0:22 ssh -o StrictHostKeyChecking=no -t %s@localhost -p%d exit' % (gateway_user, ip, cmd_port, client_user, cmd_port)) != 0:
    print 'retry'

cmd = []
cmd.append('HOSTNAME=`hostname -s`')
cmd.append('TUNNEL_CMD_PORT=`wget -O /dev/stdout http://%s:%d/get-port/$HOSTNAME`' % (ip, port))
cmd.append('autossh %s@%s -R0:$TUNNEL_CMD_PORT:0:22 -Nf -o StrictHostKeyChecking=no' % (gateway_user, ip))
cmd.append('wget -q %sreconnect-ports/$TUNNEL_CMD_PORT' % url)
cmd.append('autossh %s@%s -R0:%d:0:22 -Nf -o StrictHostKeyChecking=no' % (gateway_user, ip, cmd_port))
print 'Start autossh ...' 
print cmd[-1]
os.system(cmd[-1])
print '\n-----\nYou can also add these lines into /etc/rc.local for launching autossh at reboot.\n-----\n'
print '\n'.join(cmd[0:2])
print 'su - %s -c "%s"' % (client_user, cmd[2])
print 'su - %s -c "%s"' % (client_user, cmd[3])
print '\nAll done.'
os.chdir(old_cwd)
