# -*- coding: utf-8 -*-
import os

working_settings = {}

DEFAULTS = {
    'PROJECT_NAME': os.environ.get('PROJECT_NAME', ''),
    'PROJECT_VERSION': os.environ.get('PROJECT_VERSION', ''),
    'HTTP_PORT': 80,
    'WORKERS': 1,
    'INSPECTOR_REPORT_INTERVAL': 30,

    'DEV': False,
    'CORS': False,
    'DEBUG': False,

    'LOG_LEVEL': {
        'other': 'WARNING',
        'wings_sanic': 'INFO',
        'project': 'INFO'
    },
    'GLOBAL_URL_PREFIX': '',
    'FILE_URL': '',
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

    # rpc， mq传递上下文信息时传递指定的key, 加入headers时，
    # 1. 自动加X-前缀
    # 2. 转化为大些
    # 3. _转化为-
    'CONTEXT_WHEN_DELIVERY': []
}


def load(**user_settings):
    working_settings.update(user_settings)


def get(attr):
    try:
        # Check if present in user settings
        return working_settings[attr]
    except KeyError:
        # default LOG(JsonFormatter) is useful for elk, but not friendly for develop debug.
        # for convenience for develop, set True, then use sanic's log and its access_log is available
        if attr == 'LOGGING_CONFIG':
            return {
                'version': 1,
                'disable_existing_loggers': False,
                'loggers': {
                    "": {
                        "level": get('LOG_LEVEL').get('other', 'WARNING'),
                        "handlers": ["default"],
                        'propagate': False,
                    },
                    'wings_sanic': {
                        "level": get('LOG_LEVEL').get('wings_sanic', 'INFO'),
                        "handlers": ["wings_sanic"],
                        'propagate': False,
                    },
                    'project': {
                        "level": get('LOG_LEVEL').get('project', 'INFO'),
                        "handlers": ["project"],
                        'propagate': False,
                    }
                },
                'handlers': {
                    "default": {
                        "class": "logging.StreamHandler",
                        "formatter": "json",
                        "level": get('LOG_LEVEL').get('other', 'WARNING'),
                    },
                    "wings_sanic": {
                        "class": "logging.StreamHandler",
                        "formatter": "json",
                        "level": get('LOG_LEVEL').get('wings_sanic', 'INFO'),
                    },
                    "project": {
                        "class": "logging.StreamHandler",
                        "formatter": "json",
                        "level": get('LOG_LEVEL').get('project', 'INFO'),
                    }
                },
                'formatters': {
                    "json": get('DEV') and
                            {
                                "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
                                "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
                                "class": "logging.Formatter",
                            } or
                            {
                                "class": "wings_sanic.log_formatter.JsonFormatter"
                            }
                }
            }
        try:
            return DEFAULTS[attr]
        except KeyError:
            raise AttributeError("Invalid setting: '%s'" % attr)


def __getattr__(name):
    return get(name)
