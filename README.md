tunnel_mgmt
===========

`tunnel_mgmt` is a web gui for setting ssh reverse tunnels, creating ports forwarding and managing them. 
It is written in `python-flask` with `pymongo` and use `autossh` as the core program.

Installation
==========

<pre>
$ sudo apt-get install -y python-flask python-pymongo autossh mongodb-server
$ ssh-keygen -t rsa -f .ssh/id_rsa -b 2048 -N ""
$ git clone https://github.com/xbddc/tunnel_mgmt
$ cd tunnel_mgmt ; cp config.py.sample config.py # and do some modify
$ python daemon.py
</pre>
