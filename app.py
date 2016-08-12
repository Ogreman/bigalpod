import re
import os
import json
import flask
import requests
from unipath import Path

from flask.ext.cacheify import init_cacheify

app = flask.Flask(__name__, template_folder=Path(__file__).ancestor(1).child("templates"))
app.config.from_object(os.environ.get('APP_SETTINGS', 'config.DevelopmentConfig'))
app.cache = init_cacheify(app)


def get_template(url):
    key = 'html-' + url.split('/')[-1]
    html = app.cache.get(key)
    if not html:
        response = requests.get(url)
        if response.ok:
            html = response.content
            app.cache.set(key, html, 60 * 10)
        else:
            return ''
    return html


@app.route('/', methods=['GET'])
@app.cache.cached(timeout=60 * 60)
def index():
    template = get_template(index.template_url)
    return flask.render_template_string(template), 200
index.template_url = os.environ['INDEX_TEMPLATE_URL']


if __name__ == "__main__":
    app.run(debug=app.config.get('DEBUG', True))
