import re
import os
import json
import flask
import requests
import heroku
from unipath import Path

from flask.ext.cacheify import init_cacheify

app = flask.Flask(__name__, template_folder=Path(__file__).ancestor(1).child("templates"))
app.config.from_object(os.environ.get('APP_SETTINGS', 'config.DevelopmentConfig'))
app.cache = init_cacheify(app)
app.cloud = heroku.from_key(os.environ['HEROKU_KEY'])
app.heroku_app = app.cloud.apps[os.environ['HEROKU_APP']]


def get_template(url, prefix='html'):
    key = prefix + '-' + url.split('/')[-1]
    template = app.cache.get(key)
    if not template:
        response = requests.get(url)
        if response.ok:
            template = response.content
            app.cache.set(key, template, 60 * 10)
        else:
            return ''
    return template


@app.route('/', methods=['GET'])
@app.cache.cached(timeout=60 * 60)
def index():
    template = get_template(index.html_url)
    return flask.render_template_string(template), 200
index.html_url = os.environ['INDEX_HTML_URL']


@app.route('/set', methods=['GET'])
def set_url():
    params = flask.request.args
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
