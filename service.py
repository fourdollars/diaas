#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re
from flask import Flask, Response, Markup, request, render_template, make_response

series = (
        "sid",
        "buster",
        "stretch",
        "jessie",
        "wheezy",
        "squeeze",
        "artful",
        "zesty",
        "xenial",
        "trusty",
        "precise",
        )

app = Flask(__name__)
_pattern = re.compile("^([0-9a-f]{8})$")

def get_file_path(remote_addr, file_name, codename=None, iphex=None):
    ip_addr = ''
    if iphex and _pattern.match(iphex):
        for i in (0,2,4,6):
            ip_addr = ip_addr + str(int("0x" + iphex[i:i+2], 16)) + '.'
        else:
            ip_addr = ip_addr[:-1]

    if codename:
        if ip_addr:
            file_path = os.path.join(app.root_path, 'ip', ip_addr, codename, file_name)
            if os.path.exists(file_path):
                return file_path

        file_path = os.path.join(app.root_path, 'ip', remote_addr, codename, file_name)
        if os.path.exists(file_path):
            return file_path

    if ip_addr:
        file_path = os.path.join(app.root_path, 'ip', ip_addr, file_name)
        if os.path.exists(file_path):
            return file_path

    file_path = os.path.join(app.root_path, 'ip', remote_addr, file_name)
    if os.path.exists(file_path):
        return file_path

    return os.path.join(app.root_path, file_name)

def get_file_context(remote_addr, file_name, codename=None, iphex=None):
    file_path = get_file_path(remote_addr, file_name, codename, iphex)
    with open(file_path) as f:
        return f.read().decode("utf-8")

def save_file_context(remote_addr, preseed, late_command, codename=None):
    # Sanity check
    if codename and codename in series:
        folder = os.path.join(app.root_path, 'ip', remote_addr, codename)
        if not os.path.exists(folder):
            os.makedirs(folder)
    else:
        folder = os.path.join(app.root_path, 'ip', remote_addr)
        if not os.path.exists(folder):
            os.makedirs(folder)
    file_path = os.path.join(folder, 'preseed.cfg')
    with open(file_path, 'w') as f:
        f.write(preseed.encode("utf-8")+"\n")
    file_path = os.path.join(folder, 'late_command')
    with open(file_path, 'w') as f:
        f.write(late_command.encode("utf-8")+"\n")

@app.route('/', methods=['GET', 'POST'])
def index():
    remote_addr = request.remote_addr
    if request.url_root.endswith("d-i/"):
        url_root = request.url_root
    else:
        url_root = request.url_root + "d-i/"
    codename = None
    ip = None
    if request.method == 'POST':
        save_file_context(remote_addr,
                request.form['preseed'].replace("\r\n", "\n").rstrip(),
                request.form['late_command'].replace("\r\n", "\n").rstrip(),
                request.form['codename'])
        codename = request.form['codename']
    else: # request.method == 'GET'
        codename = request.args.get('codename')
        if not codename:
            codename = request.cookies.get('codename')
        ip = request.args.get('ip')
    # Sanity check
    if codename and codename in series:
        pass
    else:
        codename = 'any'
    preseed_path = "<a href=\"" + url_root + codename + "/preseed.cfg\">preseed.cfg</a>"
    late_command_path = "<a href=\"" + url_root + codename + "/late_command\">late_command</a>"
    preseed = get_file_context(remote_addr, 'preseed.cfg', codename, ip)
    late_command = get_file_context(remote_addr, 'late_command', codename, ip)
    option = '<option value="any">any</option>'
    for each in series:
        option = option + "\n          <option value=\"{codename}\"".format(codename=each)
        if codename == each:
            option = option + " selected"
        option = option + ">{codename}</option>".format(codename=each)
    ip = "%02x%02x%02x%02x" % tuple(int(num) for num in remote_addr.split('.'))
    share = "<a href=\"{url}\">{url}</a>".format(url=request.url_root+"?ip="+ip+"&codename="+codename)
    response = make_response(render_template('preseed.html',
        ip=remote_addr,
        preseed=preseed,
        late_command=late_command,
        preseed_path=preseed_path,
        late_command_path=late_command_path,
        option=option,
        share=share))
    response.set_cookie('codename', codename)
    return response

@app.route('/<codename>/preseed.cfg')
@app.route('/d-i/<codename>/preseed.cfg')
def preseed(codename):
    file_path = get_file_path(request.remote_addr, 'preseed.cfg', codename)
    late_command = "\nd-i preseed/late_command string\
 in-target wget {url}d-i/{codename}/late_command ;\
 in-target sh late_command ;\
 in-target rm late_command\n".format(url=request.url_root, codename=codename)
    print(dir(request))
    print(request.url_root)
    with open(file_path) as f:
        return Response(f.read().decode("utf-8") + late_command, mimetype='text/plain')

@app.route('/<codename>/late_command')
@app.route('/d-i/<codename>/late_command')
def late_command(codename):
    file_path = get_file_path(request.remote_addr, 'late_command', codename)
    with open(file_path) as f:
        return Response(f.read().decode("utf-8") , mimetype='text/plain')
