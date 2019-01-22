# -*- coding: utf-8 -*-

import json
import logging
import socket
import sys
from collections import OrderedDict

from . import datetime_helper, settings, context_var


class JsonFormatter(logging.Formatter):
    def format(self, record):
        super().format(record)
        s = record.message
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text

        # 计算method_name
        method_name = ''
        cls_name = getattr(record, 'module', "")
        func_name = record.funcName
        count = 40
        f = sys._getframe()
        while f and f.f_code.co_name != func_name and count > 0:
            f = f.f_back
            count -= 1
        if f:
            func_frame = f if f.f_code.co_name == func_name else None
            caller = func_frame.f_locals.get('self', None) if func_frame else None
            try:
                if caller:
                    if not hasattr(caller, '__name__'):
                        caller = caller.__class__
                    cls_name = '%s.%s' % (caller.__module__, caller.__name__)
            except:
                pass
            finally:
                method_name = '{cls_name}.{func_name}'.format(cls_name=cls_name, func_name=func_name)
        msg = OrderedDict((
            ('@timestamp', datetime_helper.get_time_str()),
            ('level', record.levelname),
            ('project_name', settings.get('PROJECT_NAME')),
            ('project_version', settings.get('PROJECT_VERSION')),
            ("request_uri", getattr(record, 'request_uri', "")),
            ("spent", getattr(record, 'spent', None)),
            ("trace_id", (context_var.get() or {}).get('trace_id', '')),
            ("remote_ip", getattr(record, 'remote_ip', "")),
            ("local_ip", socket.gethostbyname(socket.gethostname())),
            ("logger_name", record.name),
            ("method_name", method_name),
            ("line_number", record.lineno),
            ("thread_name", record.threadName),
            ("message", s),
            ("stack_trace", record.stack_info),
        ))

        return json.dumps(msg)
