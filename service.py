#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re
from flask import Flask, Response, Markup, request, render_template, make_response

from distro_info import DebianDistroInfo, UbuntuDistroInfo

debian = DebianDistroInfo()
ubuntu = UbuntuDistroInfo()

supported = list(reversed(debian.supported())) + list(reversed(ubuntu.supported()))

app = Flask(__name__)
_pattern = re.compile("^([0-9a-f]{8})$")

def get_file_path(remote_addr, file_name, series=None, code=None):
    if code and code == "default":
        return os.path.join(app.root_path, file_name)

    ip_addr = ''
    if code and _pattern.match(code):
        for i in (0,2,4,6):
            ip_addr = ip_addr + str(int("0x" + code[i:i+2], 16)) + '.'
        else:
            ip_addr = ip_addr[:-1]

    if series and series in supported:
        if ip_addr:
            file_path = os.path.join(app.root_path, 'ip', ip_addr, series, file_name)
            if os.path.exists(file_path):
                return file_path
            file_path = os.path.join(app.root_path, 'ip', ip_addr, file_name)
            if os.path.exists(file_path):
                return file_path

        file_path = os.path.join(app.root_path, 'ip', remote_addr, series, file_name)
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

def get_file_context(remote_addr, file_name, series=None, code=None):
    file_path = get_file_path(remote_addr, file_name, series, code)
    with open(file_path) as f:
        return f.read().decode("utf-8")

def save_file_context(remote_addr, preseed, late_command, series=None):
    # Sanity check
    if series and series in supported:
        folder = os.path.join(app.root_path, 'ip', remote_addr, series)
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
    series = None
    code = None
    if request.method == 'POST':
        save_file_context(remote_addr,
                request.form['preseed'].replace("\r\n", "\n").rstrip(),
                request.form['late_command'].replace("\r\n", "\n").rstrip(),
                request.form['series'])
        series = request.form['series']
    else: # request.method == 'GET'
        series = request.args.get('series')
        if not series:
            series = request.cookies.get('series')
        code = request.args.get('share')
    # Sanity check
    if series and series in supported:
        pass
    else:
        series = 'any'
    preseed_path = url_root + series + "/preseed.cfg"
    late_command_path = url_root + series + "/late_command"
    preseed = get_file_context(remote_addr, 'preseed.cfg', series, code)
    late_command = get_file_context(remote_addr, 'late_command', series, code)
    option = '<option value="any">any</option>'
    for each in supported:
        option = option + "\n          <option value=\"{series}\"".format(series=each)
        if series == each:
            option = option + " selected"
        option = option + ">{series}</option>".format(series=each)
    code = "%02x%02x%02x%02x" % tuple(int(num) for num in remote_addr.split('.'))
    share = request.url_root + "?share=" + code + "&series=" + series
    response = make_response(render_template('preseed.html',
        ip=remote_addr,
        preseed=preseed.rstrip(),
        late_command=late_command.rstrip(),
        preseed_path=preseed_path,
        late_command_path=late_command_path,
        option=option,
        share=share,
        url_root=request.url_root))
    response.set_cookie('series', series)
    return response

@app.route('/<series>/preseed.cfg')
@app.route('/d-i/<series>/preseed.cfg')
def preseed(series):
    file_path = get_file_path(request.remote_addr, 'preseed.cfg', series)
    if request.url_root.endswith("d-i/"):
        url_root = request.url_root
    else:
        url_root = request.url_root + "d-i/"
    late_command = "\nd-i preseed/late_command string\
 in-target wget {url}{series}/late_command ;\
 in-target sh late_command ;\
 in-target rm late_command\n".format(url=url_root, series=series)
    with open(file_path) as f:
        return Response(f.read().decode("utf-8") + late_command, mimetype='text/plain')

@app.route('/<series>/late_command')
@app.route('/d-i/<series>/late_command')
def late_command(series):
    file_path = get_file_path(request.remote_addr, 'late_command', series)
    with open(file_path) as f:
        return Response(f.read().decode("utf-8") , mimetype='text/plain')
