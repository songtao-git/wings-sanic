# -*- coding: utf-8 -*-
import os

working_settings = {}

DEFAULTS = {
    'PROJECT_NAME': os.environ.get('PROJECT_NAME', ''),
    'PROJECT_VERSION': os.environ.get('PROJECT_VERSION', ''),
    'HTTP_PORT': 80,
    'CORS': False,
    'DEBUG': False,

    'LOG': {
        'version': 1,
        'disable_existing_loggers': False,
        'loggers': {
            "": {
                "level": 'WARNING',
                "handlers": ["default"],
                'propagate': False,
            },
            'wings_sanic': {
                "level": 'INFO',
                "handlers": ["wings_sanic"],
                'propagate': False,
            }
        },
        'handlers': {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": 'WARNING',
            },
            "wings_sanic": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": 'INFO',
            }
        },
        'formatters': {
            "json": {
                "class": "wings_sanic.log_formatter.JsonFormatter"
            }
        },
    },

    'BLUEPRINTS': [],

    'WORKERS': 1,
    'RESPONSE_SHAPE': 'wings_sanic.views.ResponseShapeCodeDataMsg',
    'EXCEPTION_HANDLER': 'wings_sanic.views.exception_handler',

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
    }
}


def load(**user_settings):
    working_settings.update(DEFAULTS)
    working_settings.update(user_settings)


def get(attr):
    try:
        # Check if present in user settings
        return working_settings[attr]
    except KeyError:
        raise AttributeError("Invalid setting: '%s'" % attr)
