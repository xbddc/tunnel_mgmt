#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, url_for, render_template, request, session, redirect, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from config import load_config
import subprocess
import json
import random
import traceback
import os
import time

app = Flask(__name__)
db = MongoClient().ssh
config = {}

def check_key(str):
    if str[0:8] != 'ssh-rsa ':
        return False
    if str[380] != ' ':
        return False
    return True


def check_free_port(port, only_check_netstat=False):
    used_port = subprocess.check_output("netstat -an | grep -e '^tcp .*LISTEN' | grep -Eo ':[0-9]+' | sed 's/://g'", shell=True).split('\n')

    if only_check_netstat == False:
        hosts = db.keys.find()
        for host in hosts:
            try:
                used_port.append(host['cmd-port'])
            except:
                pass
            try:
                for ports in host['ports']:
                    used_port.append(ports['srcport'])
            except:
                pass

    if str(port) in used_port:
        return False
    return True


def connect_ports(res):
    try:
        if os.path.exists('/tmp/ssh-ctl-%d' % int(res['cmd-port'])) == False:
            os.system('ssh -M -S /tmp/ssh-ctl-%d -p%d %s@localhost -Nf' % \
                (int(res['cmd-port']), int(res['cmd-port']), res['user']))

        for port in res['ports']:
            if 'toggle' in port and port['toggle'] == 'on':
                print "start port "+port['srcport']
                os.system('ssh -S /tmp/ssh-ctl-%d -p%d %s@localhost -O forward -L%s:%d:0:%d' % \
                    (int(res['cmd-port']), int(res['cmd-port']), res['user'], config['server_ip'], \
                    int(port['srcport']), int(port['dstport'])))
    except:
        print traceback.format_exc()
        return False
    return True


def update_ssh_forwarding(res, post_port):
   if config['openssh_version'] == 5:
       if os.path.exists('/tmp/ssh-ctl-%d' % int(res['cmd-port'])) != False:
           os.system('ssh -S /tmp/ssh-ctl-%d -p%d %s@localhost -O exit' % \
               (int(res['cmd-port']), int(res['cmd-port']), res['user']))
           time.sleep(.5)
   elif config['openssh_version'] == 6:
       if os.path.exists('/tmp/ssh-ctl-%d' % int(res['cmd-port'])) != False:
           os.system('ssh -S /tmp/ssh-ctl-%d -p%d %s@localhost -O cancel -L%s:%d:0:%d' % \
               (int(res['cmd-port']), int(res['cmd-port']), res['user'], config['server_ip'], \
               int(post_port['srcport']), int(post_port['dstport'])))
   connect_ports(res)


def make_authorized_keys():
    try:
        buf = ""
        for line in db.keys.find():
            buf += line['key'] + "\n"
        f = open(os.path.expanduser('~/.ssh/authorized_keys'), 'w')
        f.write(buf)
        f.close()
    except:
        print traceback.format_exc()
        return False
    return True


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        if 'password' in request.form and request.form['password'] == config['password']:
            session['logged'] = True
            return ''
        else:
            session['logged'] = False
            abort(401)
    else:
        if 'logged' in session and session['logged'] == True:
            return ''
        abort(401)


@app.route("/getkey")
def getkey():
    return open(os.path.expanduser('~/.ssh/id_rsa.pub'), 'r').read()


@app.route("/getpy")
def getpy():
    return open('launch.py', 'r').read() \
        .replace('{{ gateway_user }}', config['gateway_user']) \
        .replace('{{ ip }}', config['server_ip']) \
        .replace('{{ port }}', str(config['server_port']))


@app.route("/")
def index():
    return render_template('_login.html')


@app.route("/list")
def list():
    if 'logged' not in session or session['logged'] != True:
        return redirect(url_for('index'))

    lines = []
    try:
        for line in db.keys.find():
            lines.append(line)
    except:
        print traceback.format_exc()
        pass
    return render_template('_index.html', lines=lines, ip=config['server_ip'], port=config['server_port'])


@app.route("/add-host/", methods=['POST'])
@app.route("/mod-host/<id>", methods=['POST'])
def add_host(id=None):
    if 'logged' not in session or session['logged'] != True:
        abort(401)

    try:
        if check_key(request.form['key']):
            post_host = request.form.copy()
            post_host['user'] = post_host['key'].split(' ')[2].split('@')[0]
            res = db.keys.update({"_id": ObjectId(id)}, post_host, upsert=True)
    except:
        print traceback.format_exc()
        abort(500)

    make_authorized_keys()
    res = id or res['upserted']
    return str(res)


@app.route("/del-host/<id>", methods=['POST'])
def del_host(id):
    if 'logged' not in session or session['logged'] != True:
        abort(401)

    try:
        db.keys.remove({"_id": ObjectId(id)})
    except:
        print traceback.format_exc()
        abort(500)

    make_authorized_keys()
    return ''


@app.route("/gen-port")
def gen_port():
    while True:
        gen_port = str(random.randrange(60001, 65536))
        if check_free_port(gen_port):
            break
        
    return gen_port


@app.route("/check-port/<port>")
def check_port(port):
    if check_free_port(port, True) == False:
        return ''
    abort(404)


@app.route("/add-port/<id>", methods=['POST'])
def add_port(id):
    if 'logged' not in session or session['logged'] != True:
        abort(401)

    try:
        if 'srcport' not in request.form or 'dstport' not in request.form:
            raise(KeyError)
        if check_free_port(request.form['srcport']) == False:
            raise()
    except KeyError:
        abort(400)
    except:
        abort(404)
        
    try:
        res = db.keys.find_one({"_id": ObjectId(id)})
        if 'ports' not in res:
            res['ports'] = []
        post_port = request.form.copy()
        post_port['toggle'] = 'off'
        res['ports'].append(post_port)
        ret = db.keys.update({"_id": ObjectId(id)}, res)
        connect_ports(res)
    except:
        print traceback.format_exc()
        abort(500)

    ret = id or ret['upserted']
    return str(ret)


@app.route("/toggle-port/<id>", methods=['POST'])
def toggle_port(id):
    if 'logged' not in session or session['logged'] != True:
        abort(401)

    try:
        res = db.keys.find_one({"_id": ObjectId(id)})
        post_port = request.form.copy()
        for idx, port in enumerate(res['ports']):
            if port['srcport'] == post_port['srcport'] and port['dstport'] == post_port['dstport']:
                res['ports'][idx]['toggle'] = post_port['toggle']
                break
        ret = db.keys.update({"_id": ObjectId(id)}, res)
        update_ssh_forwarding(res, post_port)

    except:
        print traceback.format_exc()
        abort(500)

    ret = id or ret['upserted']
    return str(ret)


@app.route("/del-port/<id>", methods=['POST'])
def del_port(id):
    if 'logged' not in session or session['logged'] != True:
        abort(401)

    try:
        res = db.keys.find_one({"_id": ObjectId(id)})
        post_port = request.form.copy()
        for idx, port in enumerate(res['ports']):
            if port['srcport'] == post_port['srcport'] and port['dstport'] == post_port['dstport']:
                del res['ports'][idx]
                break
        ret = db.keys.update({"_id": ObjectId(id)}, res)
        update_ssh_forwarding(res, post_port)
        
    except:
        print traceback.format_exc()
        abort(500)

    ret = id or ret['upserted']
    return str(ret)


@app.route("/list-port/<id>")
def list_port(id=None):
    if 'logged' not in session or session['logged'] != True:
        abort(401)

    ports = []
    try:
        ports = db.keys.find_one({"_id": ObjectId(id)})['ports']
    except KeyError:
        return '{}'
    except:
        print traceback.format_exc()
        abort(500)
    print ports
    return json.dumps(ports)

if __name__ == "__main__":
    config = load_config()
    app.secret_key = config['secret_key']
    app.run(host=config['server_ip'], port=config['server_port'])
