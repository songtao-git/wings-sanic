# -*- coding: utf-8 -*-
import os

working_settings = {}

DEFAULTS = {
    'PROJECT_NAME': os.environ.get('PROJECT_NAME', ''),
    'PROJECT_VERSION': os.environ.get('PROJECT_VERSION', ''),
    'HTTP_PORT': 80,
    'WORKERS': 1,
    'INSPECTOR_REPORT_INTERVAL': 30,

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

    # default LOG(JsonFormatter) is useful for elk, but not friendly for develop debug.
    # for convenience for develop, set True, then use sanic's log and its access_log is available
    'DEV': False,
    'CORS': False,
    'DEBUG': False,

    'BLUEPRINTS': [],
    'DEFAULT_CONTEXT': {
        'response_shape': 'wings_sanic.views.ResponseShape',
        'serialize_when_none': True
    },
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
    },
    'MQ_SERVERS': {
        # 'default': {
        #     'server': 'wings_sanic.events.rabbitmq_server.MqServer',
        #     'url': 'amqp://guest:guest@127.0.0.1:5672',
        #     'exchange': 'test',
        #     'exchange_type': 'topic',
        #     'reconnect_delay': 5.0
        # }
    },
    'EVENT_HANDLE_TIMEOUT': 10,
    'EVENT_MAX_RETRY': -1,

    # rpc， mq传递上下文信息时忽略的key
    'IGNORE_CONTEXT_WHEN_DELIVERY':[
        'messages',
        'response_shape',
        'serialize_when_none'
    ]
}


def load(**user_settings):
    working_settings.update(user_settings)


def get(attr):
    try:
        # Check if present in user settings
        return working_settings[attr]
    except KeyError:
        try:
            return DEFAULTS[attr]
        except KeyError:
            raise AttributeError("Invalid setting: '%s'" % attr)
