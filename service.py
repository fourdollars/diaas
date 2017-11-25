#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from flask import Flask, Response, Markup, request, render_template, make_response

app = Flask(__name__)

def get_file_path(remote_addr, file_name, codename=None):
    if codename:
        file_path = os.path.join(app.root_path, 'ip', remote_addr, codename, file_name)
        if os.path.exists(file_path):
            return file_path
    file_path = os.path.join(app.root_path, 'ip', remote_addr, file_name)
    if os.path.exists(file_path):
        return file_path
    return os.path.join(app.root_path, file_name)

def get_file_context(remote_addr, file_name, codename=None):
    file_path = get_file_path(remote_addr, file_name, codename)
    with open(file_path) as f:
        return f.read().decode("utf-8")

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
    codename = None
    if request.method == 'POST':
        save_file_context(remote_addr,
                request.form['preseed'].replace("\r\n", "\n"),
                request.form['late_command'].replace("\r\n", "\n"),
                request.form['codename'])
        codename = request.form['codename']
    else: # request.method == 'GET'
        codename = request.cookies.get('codename')
    # Sanity check
    if codename and codename in series:
        pass
    else:
        codename = None
    preseed = get_file_context(remote_addr, 'preseed.cfg', codename)
    late_command = get_file_context(remote_addr, 'late_command', codename)
    option = '<option value="all">all</option>'
    for each in series:
        option = option + "\n          <option value=\"{codename}\"".format(codename=each)
        if codename == each:
            option = option + " selected"
        option = option + ">{codename}</option>".format(codename=each)
    response = make_response(render_template('preseed.html',
        ip=remote_addr, preseed=preseed, late_command=late_command, option=option))
    if codename:
        response.set_cookie('codename', codename)
    else:
        response.set_cookie('codename', 'all')
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
