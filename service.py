#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv, os, re
from datetime import datetime
from flask import Flask, Response, request, render_template, make_response
from markupsafe import Markup


def get_supported_distro_series_current_release(csv_file_path, eol_columns):
    """
    Retrieves currently supported series from a distro-info CSV file.
    Only series with a 'release' date on or before the current date are considered.
    Support status is determined by the latest End of Life (EOL) date among specified EOL columns.

    Args:
        csv_file_path (str): The path to the distro-info CSV file.
        eol_columns (list): A list containing the names of all relevant End of Life (EOL) date columns.

    Returns:
        list: A list of 'series' names for all currently supported distributions
              that have been released on or before the current date.
    """
    supported_series = []
    # Set the current date as the reference for determining support status
    # Current date is June 10, 2025
    current_date = datetime.now().date()

    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                series = row.get("series")
                release_date_str = row.get("release")

                # Skip if 'series' or 'release' date is missing
                if not series or not release_date_str:
                    continue

                try:
                    release_date = datetime.strptime(
                        release_date_str, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    # Skip if release date format is invalid
                    continue

                # Only proceed if the release date is on or before the current date
                if release_date > current_date:
                    continue  # Skip future releases

                latest_eol_date_for_row = None

                # Find the latest EOL date among all specified EOL columns for the current row
                for col_name in eol_columns:
                    eol_date_str = row.get(col_name)
                    if eol_date_str:
                        try:
                            current_eol_date = datetime.strptime(
                                eol_date_str, "%Y-%m-%d"
                            ).date()
                            if (
                                latest_eol_date_for_row is None
                                or current_eol_date > latest_eol_date_for_row
                            ):
                                latest_eol_date_for_row = current_eol_date
                        except ValueError:
                            # Ignore invalid date formats in CSV for EOL
                            pass

                # A series is considered supported if:
                # 1. It has a latest EOL date and that date is in the future
                # OR
                # 2. It's a special continuously supported series (like Debian's 'sid', 'experimental')
                #    and has a release date on or before today, but no explicit EOL date.
                if latest_eol_date_for_row and latest_eol_date_for_row > current_date:
                    supported_series.append(series)
                elif series in ["sid", "experimental"] and not latest_eol_date_for_row:
                    # For 'sid' and 'experimental', they are considered continuously supported.
                    # We've already filtered by release_date <= current_date, so no explicit EOL check is needed here for them.
                    supported_series.append(series)

    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return []

    return supported_series


debian_file_path = "/usr/share/distro-info/debian.csv"
# Define Debian's EOL column names
debian_eol_columns = ["eol", "eol-lts", "eol-elts"]
debian_supported_series = get_supported_distro_series_current_release(
    debian_file_path, debian_eol_columns
)

ubuntu_file_path = "/usr/share/distro-info/ubuntu.csv"
# Define Ubuntu's EOL column names
ubuntu_eol_columns = ["eol", "eol-server", "eol-esm"]
ubuntu_supported_series = get_supported_distro_series_current_release(
    ubuntu_file_path, ubuntu_eol_columns
)

supported = list(reversed(debian_supported_series)) + list(
    reversed(ubuntu_supported_series)
)

app = Flask(__name__)
_pattern = re.compile("^([0-9a-f]{8})$")


def get_file_path(remote_addr, file_name, series=None, code=None):
    if code and code == "default":
        return os.path.join(app.root_path, file_name)

    ip_addr = ""
    if code and _pattern.match(code):
        for i in (0, 2, 4, 6):
            ip_addr = ip_addr + str(int("0x" + code[i : i + 2], 16)) + "."
        else:
            ip_addr = ip_addr[:-1]

    if series and series in supported:
        if ip_addr:
            file_path = os.path.join(app.root_path, "ip", ip_addr, series, file_name)
            if os.path.exists(file_path):
                return file_path
            file_path = os.path.join(app.root_path, "ip", ip_addr, file_name)
            if os.path.exists(file_path):
                return file_path

        file_path = os.path.join(app.root_path, "ip", remote_addr, series, file_name)
        if os.path.exists(file_path):
            return file_path

    if ip_addr:
        file_path = os.path.join(app.root_path, "ip", ip_addr, file_name)
        if os.path.exists(file_path):
            return file_path

    file_path = os.path.join(app.root_path, "ip", remote_addr, file_name)
    if os.path.exists(file_path):
        return file_path

    return os.path.join(app.root_path, file_name)


def get_file_context(remote_addr, file_name, series=None, code=None):
    file_path = get_file_path(remote_addr, file_name, series, code)
    with open(file_path) as f:
        return f.read()


def save_file_context(remote_addr, preseed, late_command, series=None):
    # Sanity check
    if series and series in supported:
        folder = os.path.join(app.root_path, "ip", remote_addr, series)
        if not os.path.exists(folder):
            os.makedirs(folder)
    else:
        folder = os.path.join(app.root_path, "ip", remote_addr)
        if not os.path.exists(folder):
            os.makedirs(folder)
    file_path = os.path.join(folder, "preseed.cfg")
    with open(file_path, "w") as f:
        f.write(preseed + "\n")
    file_path = os.path.join(folder, "late_command")
    with open(file_path, "w") as f:
        f.write(late_command + "\n")


@app.route("/", methods=["GET", "POST"])
def index():
    remote_addr = request.remote_addr
    if request.url_root.endswith("d-i/"):
        url_root = request.url_root
    else:
        url_root = request.url_root + "d-i/"
    series = None
    code = None
    if request.method == "POST":
        save_file_context(
            remote_addr,
            request.form["preseed"].replace("\r\n", "\n").rstrip(),
            request.form["late_command"].replace("\r\n", "\n").rstrip(),
            request.form["series"],
        )
        series = request.form["series"]
    else:  # request.method == 'GET'
        series = request.args.get("series")
        if not series:
            series = request.cookies.get("series")
        code = request.args.get("share")
    # Sanity check
    if series and series in supported:
        pass
    else:
        series = "any"
    preseed_path = url_root + series + "/preseed.cfg"
    late_command_path = url_root + series + "/late_command"
    preseed = get_file_context(remote_addr, "preseed.cfg", series, code)
    late_command = get_file_context(remote_addr, "late_command", series, code)
    option = '<option value="any">any</option>'
    for each in supported:
        option = option + '\n          <option value="{series}"'.format(series=each)
        if series == each:
            option = option + " selected"
        option = option + ">{series}</option>".format(series=each)
    code = "%02x%02x%02x%02x" % tuple(int(num) for num in remote_addr.split("."))
    share = request.url_root + "?share=" + code + "&series=" + series
    response = make_response(
        render_template(
            "preseed.html",
            ip=remote_addr,
            preseed=preseed.rstrip(),
            late_command=late_command.rstrip(),
            preseed_path=preseed_path,
            late_command_path=late_command_path,
            option=option,
            share=share,
            url_root=request.url_root,
        )
    )
    response.set_cookie("series", series)
    return response


@app.route("/<series>/preseed.cfg")
@app.route("/d-i/<series>/preseed.cfg")
def preseed(series):
    file_path = get_file_path(request.remote_addr, "preseed.cfg", series)
    if request.url_root.endswith("d-i/"):
        url_root = request.url_root
    else:
        url_root = request.url_root + "d-i/"
    late_command = "\nd-i preseed/late_command string\
 in-target wget {url}{series}/late_command ;\
 in-target sh late_command ;\
 in-target rm late_command\n".format(
        url=url_root, series=series
    )
    with open(file_path) as f:
        return Response(f.read() + late_command, mimetype="text/plain")


@app.route("/<series>/late_command")
@app.route("/d-i/<series>/late_command")
def late_command(series):
    file_path = get_file_path(request.remote_addr, "late_command", series)
    with open(file_path) as f:
        return Response(f.read(), mimetype="text/plain")
