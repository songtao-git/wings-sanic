# -*- coding: utf-8 -*-
import datetime
import decimal
import inspect
import json
import os
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


def instance_from_json(data, cls=None):
    """
    如果cls有值, 则将data_string转化成对应的instance(s)
    否则，转化成python内置类型
    转化失败时：
        如果cls是None, 则返回原字符串
        否则，返回None
    :param data: json结构的字符串
    :param cls: type of class
    :return: 
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    data = to_native(data)

    if not cls:
        return data

    if isinstance(data, Mapping):
        try:
            return cls(**data)
        except:
            return None

    if isinstance(data, Sequence) and not isinstance(data, str):
        result = []
        for i in data:
            item_result = instance_from_json(i)
            if item_result:
                result.append(item_result)
        return result or None

    return None


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


def cls_str_of_meth(meth, separator='.'):
    if meth is None:
        return None
    mod = inspect.getmodule(meth)
    cls = meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
    return f'{mod.__name__}.{cls}'.replace('.', separator)


def cls_str_of_obj(obj, separator='.'):
    if obj is None:
        return None
    return f'{obj.__class__.__module__}.{obj.__class__.__name__}'.replace('.', separator)


def cls_str_of_cls(cls, separator='.'):
    if cls is None:
        return None
    return f'{cls.__module__}.{cls.__name__}'.replace('.', separator)


def meth_str(meth, separator='.'):
    if meth is None:
        return None
    return f'{meth.__module__}.{meth.__qualname__}'.replace('.', separator)


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


def __load(path):
    for item in os.listdir(path):
        item_path = '%s/%s' % (path, item)
        if item.endswith('.py'):
            __import__('{pkg}.{mdl}'.format(pkg=path.replace('/', '.'), mdl=item[:-3]))
        elif os.path.isdir(item_path):
            load_path(item_path)


def load_path(*path):
    """加载某目录下所有的.py文件，可用于加载某目录下所有的event handlers时"""
    for p in path:
        __load(p)
