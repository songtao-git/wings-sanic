# -*- coding: utf-8 -*-
from typing import Sequence, Mapping
import datetime
from . import datetime_helper


def to_primitive(obj):
    if obj is None:
        return None
    if hasattr(obj, 'to_primitive') and callable(getattr(obj, 'to_primitive')):
        return obj.to_primitive()
    if isinstance(obj, str):
        return obj
    if isinstance(obj, datetime.datetime):
        return datetime_helper.get_time_str(obj)
    if isinstance(obj, datetime.date):
        return datetime_helper.get_date_str(obj)
    if isinstance(obj, Sequence):
        return [to_primitive(e) for e in obj]
    elif isinstance(obj, Mapping):
        return dict(
            (k, to_primitive(v)) for k, v in obj.items()
        )
    return obj
