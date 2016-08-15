import re
import os
import json
import functools
import StringIO
import flask
import requests
import heroku
from unipath import Path

from flask.ext.cacheify import init_cacheify

app = flask.Flask(__name__, template_folder=Path(__file__).ancestor(1).child("templates"))
app.config.from_object(os.environ.get('APP_SETTINGS', 'config.DevelopmentConfig'))
app.cache = init_cacheify(app)
try:
    app.cloud = heroku.from_key(os.environ['HEROKU_KEY'])
except requests.exceptions.RequestException:
    print "[heroku]: failed to connect to cloud service"
    app.cloud = None
else:
    app.heroku_app = app.cloud.apps[os.environ['HEROKU_APP']]
app.default_timeout = 10 if app.config['DEBUG'] else (60 * 60)
app.templates = {}


def get_template(url, prefix='html'):
    key = prefix + '-' + url.split('/')[-1]
    print "[template]: getting " + key + "..."
    template = app.cache.get(key)
    if not template:
        print "[template]: not found in cache"
        try:
            print "[template]: requesting from " + url + "..."
            response = requests.get(url, timeout=3)
            if response.ok:
                template = response.content
                app.cache.set(key, template, app.default_timeout)
                print "[template]: " + key + " stored in cache"
            else:
                print "[template]: failed to get " + url
                print "[template]: " + str(response.status_code)
                return ''
        except requests.exceptions.RequestException:
            print "[template]: connection failed to " + url
            return ''
    else:
        print "[template]: using cache"
    return template


def templated(key=None, **func_kw):
    def templated_decorator(func):
        func.key = key or hash(func)
        @functools.wraps(func)
        def wraps(*args, **kwargs):
            app.templates[func.key] = get_template(**func_kw)
            return func(*args, **kwargs)
        return wraps
    return templated_decorator


@app.route('/', methods=['GET'])
@app.cache.cached(timeout=app.default_timeout)
@templated(key='index', url=os.environ['INDEX_HTML_URL'])
def index():
    template = app.templates.get(index.key)
    if not template:
        return '', 404
    return flask.render_template_string(template), 200


@app.route('/main.css', methods=['GET'])
@app.cache.cached(timeout=app.default_timeout)
@templated(key='main', url=os.environ['MAIN_CSS_URL'], prefix='css')
def main():
    template = app.templates.get(main.key)
    if not template:
        return '', 404
    file_handle = StringIO.StringIO()
    file_handle.write(template)
    file_handle.seek(0)
    return flask.send_file(file_handle, attachment_filename="main.css")


@app.route('/set', methods=['GET'])
def set_url():
    params = flask.request.args
    if app.cloud is None:
        return 'offline', 200
    if params.get('key', '') == app.config['SECRET_KEY']:
        route = params.get('route')
        url = params.get('url')
        suffix = '_{}_URL'.format(params.get('type', 'html'))
        if route and url:
            template_key = (route + suffix).upper()
            app.heroku_app.config[template_key] = url
            return 'done', 200
    return 'denied', 200


def warmup():
    for key, value in os.environ.items():
        if key.endswith('HTML_URL'):
            get_template(value)
        elif key.endswith('CSS_URL'):
            get_template(value, 'css')


if __name__ == "__main__":
    warmup()
    app.run(debug=app.config.get('DEBUG', True))
