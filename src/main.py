import json
import os

from wings_sanic import application, settings, DEFAULT_CONTEXT, views

# -----------  dev settings -------------
dev_settings = {
    'BLUEPRINTS': [
        'test.bp'
    ],

    'SWAGGER': {
        'info': {
            "version": os.environ.get('PROJECT_VERSION', '1.0.0'),
            "title": 'Wings-Sanic Sample',
            "description": 'test for wings-sanic',
            "termsOfService": None,
            "contact": {
                "email": None
            },
            "license": {
                "email": None,
                "url": None
            }
        },
        'schemes': ['http']
    },
    'DEBUG': True
}
settings.load(**dev_settings)

DEFAULT_CONTEXT['response_shape'] = views.ResponseShapeCodeDataMsg

# ----------- use config that is from environ to cover dev_settings ----------
config_json = os.environ.get('CONFIG', '')
if config_json:
    try:
        conf = json.loads(config_json)
        if conf and isinstance(conf, dict):
            settings.load(**conf)
    except:
        pass

# --------------------- main -----------------
if __name__ == '__main__':
    application.start()
