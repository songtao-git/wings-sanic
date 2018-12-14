# -*- coding: utf-8 -*-
import json
import os

from wings_sanic import application, settings

# -----------  dev settings -------------
dev_settings = {
    'BLUEPRINTS': [],
    'DEFAULT_CONTEXT': {
        'response_shape': 'wings-sanic.views.ResponseShapeCodeDataMsg'
    },
    'SWAGGER': {
        'info': {
            "version": os.environ.get('PROJECT_VERSION', '1.0.0'),
            "title": os.environ.get('PROJECT_NAME', 'API'),
            "description": '',
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
    'DEBUG': True,
    'DEV': True,
    'CORS': True
}
settings.load(**dev_settings)

# ----------- use config that is from environ to cover dev_settings ----------
config_json = os.environ.get('CONFIG', '')
if config_json:
    try:
        conf = json.loads(config_json)
        if conf and isinstance(conf, dict):
            settings.load(**conf)
    except:
        pass


# ---------------- do init project. for example: init redis -------------------
@application.app.listener('after_server_start')
async def init_project(sanic, loop):
    pass


# --------------------- main -----------------
if __name__ == '__main__':
    application.start()
