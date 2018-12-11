# -*- coding: utf-8 -*-
import datetime
import decimal
import inspect
from typing import Sequence, Mapping

from wings_sanic import datetime_helper


def instance_to_dict(instance):
    """
    Convert instance to dict
    """
    if not hasattr(instance, '__dict__'):
        return None
    data = {}
    for k, v in instance.__dict__.items():
        if k.startswith('__'):
            continue
        if k.startswith('_'):
            continue
        if callable(v):
            continue
        data[k] = v
    return data


def to_native(obj):
    """Convert obj to a richer Python construct. The obj can be anything
    """
    if obj is None:
        return None
    if isinstance(obj, (int, float, bool, datetime.datetime, datetime.date, decimal.Decimal)):
        return obj
    elif isinstance(obj, str):
        value = datetime_helper.parse_datetime(obj)
        if not value:
            value = datetime_helper.parse_date(obj)
        return value or obj

    if hasattr(obj, 'to_native') and callable(obj.to_native) \
            and len(inspect.signature(obj.to_native).parameters) == 1:
        return obj.to_native()

    if hasattr(obj, '__dict__'):
        obj = instance_to_dict(obj)

    if isinstance(obj, Sequence):
        return [to_native(item) for item in obj]
    if isinstance(obj, Mapping):
        return dict(
            (k, to_native(v)) for k, v in obj.items()
        )
    return obj


def to_primitive(obj):
    """Convert obj to a value safe to serialize.
    """
    if obj is None:
        return None
    if hasattr(obj, 'to_primitive') and callable(obj.to_primitive) \
            and len(inspect.signature(obj.to_primitive).parameters) == 1:
        return obj.to_primitive()
    data = to_native(obj)
    if isinstance(data, (int, float, bool, str)):
        return data
    if isinstance(data, datetime.datetime):
        return datetime_helper.get_time_str(obj)
    if isinstance(data, datetime.date):
        return datetime_helper.get_date_str(obj)
    if isinstance(data, Sequence):
        return [to_primitive(e) for e in data]
    elif isinstance(data, Mapping):
        return dict(
            (k, to_primitive(v)) for k, v in data.items()
        )
    return str(data)


def get_value(instance_or_dict, name, default=None):
    if isinstance(instance_or_dict, Mapping):
        return instance_or_dict.get(name, default)
    return getattr(instance_or_dict, name, default)


def cls_str_of_meth(meth):
    mod = inspect.getmodule(meth)
    cls = meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
    return '{0}.{1}'.format(mod.__name__, cls)


def cls_str_of_obj(obj):
    return '{0}.{1}'.format(obj.__class__.__module__, obj.__class__.__name__)


def cls_str_of_cls(cls):
    return '{0}.{1}'.format(cls.__module__, cls.__name__)


def meth_str(meth):
    return '{0}.{1}'.format(meth.__module__, meth.__qualname__)


def import_from_str(obj_path):
    module_name, obj_name = obj_path.rsplit('.', 1)
    module_meta = __import__(module_name, globals(), locals(), [obj_name])
    obj_meta = getattr(module_meta, obj_name)
    return obj_meta


# Removes all null values from a dictionary
def remove_nulls(dictionary, deep=True):
    return {
        k: remove_nulls(v, deep) if deep and type(v) is dict else v
        for k, v in dictionary.items()
        if v is not None
    }
