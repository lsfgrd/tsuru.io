# Copyright 2013 Globo.com. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import requests
import os
import pymongo
from flask import Flask, render_template, g, request, redirect, url_for

app = Flask(__name__)
MONGO_URI = os.environ.get("MONGO_URI", "localhost:27017")
MONGO_USER = os.environ.get("MONGO_USER", "")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD", "")
MONGO_DATABASE_NAME = os.environ.get("MONGO_DATABASE_NAME", "test")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")


@app.route("/")
def index():
    return render_template("index.html", facebook_app_id=FACEBOOK_APP_ID,
                                         github_client_id=GITHUB_CLIENT_ID), 200


@app.route("/confirmation")
def confirmation():
    return render_template("confirmation.html"), 200


@app.route("/register/facebook", methods=["POST"])
def facebook_register():
    if not has_token(request.form):
        return "Could not obtain access token from facebook.", 400
    url = "https://graph.facebook.com/me?fields=first_name,last_name,email&access_token={0}".format(request.form["access_token"])
    response = requests.get(url)
    info = response.json()
    user = {"first_name": info["first_name"],
            "last_name": info["last_name"],
            "email": info["email"]}
    g.db.users.insert(user)
    return redirect(url_for("confirmation"))


@app.route("/register/github", methods=["GET"])
def github_register():
    code = request.args.get("code")
    if code is None:
        return "Could not obtain code access to github.", 400
    data = "client_id={0}&code={1}&client_secret={2}".format(GITHUB_CLIENT_ID, code, GITHUB_CLIENT_SECRET)
    headers = {"Accept": "application/json"}
    url = "https://github.com/login/oauth/access_token"
    response = requests.post(url, data=data, headers=headers)
    token = response.json().get("access_token")
    if token is None or token == "":  # test me
        return "Could not obtain access token from github.", 400
    url = "https://api.github.com/user?access_token={0}".format(token)
    response = requests.get(url, headers=headers)
    info = response.json()
    first_name, last_name = parse_github_name(info)
    user = {"first_name": first_name,
            "last_name": last_name,
            "email": info["email"]}
    g.db.users.insert(user)
    return redirect(url_for("confirmation"))


def parse_github_name(info):
    splitted = info["name"].split(" ")
    if len(splitted) > 1:
        return splitted[0], splitted[-1]
    return splitted[0], ""


def has_token(form):
    if "access_token" not in form.keys():
        return False
    if not form["access_token"] or form["access_token"] == "":
        return False
    return True


@app.before_request
def before_request():
    g.conn, g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    g.conn.close()


def connect_db():
    mongo_uri_port = MONGO_URI.split(":")
    host = mongo_uri_port[0]
    port = int(mongo_uri_port[1])
    conn = pymongo.Connection(host, port)
    return conn, conn[MONGO_DATABASE_NAME]


if __name__ == "__main__":
    app.run()
