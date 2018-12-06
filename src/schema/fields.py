# -*- coding: utf-8 -*-
import datetime
import decimal
import numbers
import re
import uuid
from collections import Iterable, OrderedDict

from sanic import exceptions

from . import datetime_helper
from .undefined import Undefined
from typing import Sequence, Mapping


def loop_primitive(obj, spec):
    if obj is None:
        return None
    if hasattr(obj, 'to_primitive') and callable(getattr(obj, 'to_primitive')):
        return obj.to_primitive()
    if isinstance(obj, (int, float, bool, str)):
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
    return str(obj)


def loop_native(value, spec):
    pass


class FieldMeta(type):
    """
    Meta class for BaseField. Merges `MESSAGES` dict and accumulates
    validator methods.
    """

    def __new__(mcs, name, bases, attrs):
        messages = {}
        validators = OrderedDict()

        for base in reversed(bases):
            if hasattr(base, 'MESSAGES'):
                messages.update(base.MESSAGES)

            if hasattr(base, "_validators"):
                validators.update(base._validators)

        if 'MESSAGES' in attrs:
            messages.update(attrs['MESSAGES'])

        attrs['MESSAGES'] = messages

        for attr_name, attr in attrs.items():
            if attr_name.startswith("validate_"):
                validators[attr_name[9:]] = attr

        attrs["_validators"] = validators

        return type.__new__(mcs, name, bases, attrs)


class BaseField(metaclass=FieldMeta):
    """A base class for Fields in a Model. Instances of this
    class may be added to subclasses of ``Model`` to define a model schema.

    Validators that need to access variables on the instance
    can be defined be implementing methods whose names start with ``validate_``
    and accept one parameter (in addition to ``self``)

    :param label:
        Brief human-readable label
    :param help_text:
        Explanation of the purpose of the field. Used for help, tooltips, 
        documentation, etc.
    :param required:
        Invalidate field when value is None or is not supplied. 
        Default: False.
    :param default:
        When no data is provided default to this value. May be a callable.
        Default: Undefined.
    :param choices:
        A list of valid choices. This is the last step of the validator
        chain.
    :param validators:
        A list of callables. Each callable receives the value after it has been
        converted into a rich python type. Default: []
    :param serialize_when_none:
        Dictates if the field should appear in the serialized data even if the value is None. 
        Default: True.
    :param messages:
        Override the error messages with a dict. You can also do this by
        subclassing the Type and defining a `MESSAGES` dict attribute on the
        class. A metaclass will merge all the `MESSAGES` and override the
        resulting dict with instance level `messages` and assign to
        `self.messages`.
    """
    primitive_type = None
    native_type = None

    MESSAGES = {
        'required': "{0}必填",
        'choices': "{0}是{1}其中之一.",
    }

    def __init__(self, label, help_text=None, required=False,
                 default=Undefined, choices=None, validators=None,
                 serialize_when_none=True, messages=None):
        super().__init__()
        if not label or not isinstance(label, str):
            raise ValueError('label must be a effective string')
        self.label = label
        self.help_text = help_text
        self.required = required
        self._default = default
        if choices and (isinstance(choices, str) or not isinstance(choices, Iterable)):
            raise TypeError('"choices" must be a non-string Iterable')
        self.choices = choices

        self.validators = list(self._validators.values())
        if validators:
            self.validators += list(validators)
        self.serialize_when_none = serialize_when_none
        self.messages = dict(self.MESSAGES, **(messages or {}))

        self.name = None
        self.owner_model = None

    def __repr__(self):
        type_ = "%s(%s) instance" % (self.__class__.__name__, self._repr_info() or '')
        model = " on %s" % self.owner_model.__name__ if self.owner_model else ''
        field = " as '%s'" % self.name if self.name else ''
        return "<%s>" % (type_ + model + field)

    def _repr_info(self):
        return None

    def _setup(self, field_name, owner_model):
        """Perform late-stage setup tasks that are run after the containing model
        has been created.
        """
        self.name = field_name
        self.owner_model = owner_model

    @property
    def default(self):
        default = self._default
        if callable(default):
            default = default()
        return default

    def pre_setattr(self, value):
        return value

    def to_primitive(self, value):
        """Convert internal data to a value safe to serialize.
        """
        return to_primitive(value)

    def to_native(self, value):
        """
        Convert untrusted data to a richer Python construct.
        """
        return value

    def validate(self, value):
        value = self.to_native(value)

        for validator in self.validators:
            validator(value)

        return value

    def validate_required(self, value):
        if self.required and (value is None or value is Undefined):
            raise exceptions.InvalidUsage(self.messages['required'].format(self.label))

    def validate_choices(self, value):
        if self.choices is not None:
            if value not in self.choices:
                raise exceptions.InvalidUsage(self.messages['choices'].format(self.label, self.choices))


class UUIDField(BaseField):
    """A field that stores a valid UUID value.
    """
    primitive_type = str
    native_type = uuid.UUID

    MESSAGES = {
        'convert': "{0}的值{1}不能转为UUID",
    }

    def to_native(self, value):
        if not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(value)
            except (TypeError, ValueError):
                raise exceptions.InvalidUsage(self.messages['convert'].format(self.label, value))
        return value


class StringField(BaseField):
    """A Unicode string field."""
    primitive_type = str
    native_type = str

    MESSAGES = {
        'decode': "{0}的值不是utf-8编码格式",
        'max_length': "{0}的值长度不能超过{1}",
        'min_length': "{0}的值长度不能低于{1}",
        'regex': "{0}的值格式有误",
    }

    def __init__(self, label, regex=None, max_length=None, min_length=None, **kwargs):
        self.regex = re.compile(regex) if regex else None
        self.max_length = max_length
        self.min_length = min_length
        super().__init__(label, **kwargs)

    def to_native(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            try:
                return str(value, 'utf-8')
            except UnicodeError:
                raise exceptions.InvalidUsage(self.messages['decode'].format(self.label))
        return str(value)

    def validate_length(self, value):
        length = len(value)
        if self.max_length is not None and length > self.max_length:
            raise exceptions.InvalidUsage(self.messages['max_length'].format(self.label, self.max_length))

        if self.min_length is not None and length < self.min_length:
            raise exceptions.InvalidUsage(self.messages['min_length'].format(self.label, self.min_length))

    def validate_regex(self, value):
        if self.regex is not None and self.regex.match(value) is None:
            raise exceptions.InvalidUsage(self.messages['regex'].format(self.label))


class NumberField(BaseField):
    """A generic number field.
    Converts to and validates against `number_type` parameter.
    :param strict: eg. `1.2` is not effective for IntField if `strict` is True; but effective if False
    """

    primitive_type = None
    native_type = None
    number_type = None
    MESSAGES = {
        'number_coerce': "{0}的值{1}不能转化成{2}",
        'number_min': "{0}的值应大于等于{1}",
        'number_max': "{0}的值应小于等于{1}",
    }

    def __init__(self, label, min_value=None, max_value=None, strict=False, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        self.strict = strict

        super().__init__(label, **kwargs)

    def to_native(self, value):
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, self.native_type):
            return value
        try:
            native_value = self.native_type(value)
        except (TypeError, ValueError):
            pass
        else:
            if self.native_type is float:  # Float conversion is strict enough.
                return native_value
            if not self.strict or native_value == value:
                return native_value
            if isinstance(value, (str, numbers.Integral)):
                return native_value

        raise exceptions.InvalidUsage(self.messages['number_coerce'].format(self.label, value, self.number_type))

    def validate_range(self, value):
        if self.min_value is not None and value < self.min_value:
            raise exceptions.InvalidUsage(self.messages['number_min'].format(self.label, self.min_value))

        if self.max_value is not None and value > self.max_value:
            raise exceptions.InvalidUsage(self.messages['number_max'].format(self.label, self.max_value))

        return value


class IntField(NumberField):
    """A field that validates input as an Integer
    """

    primitive_type = int
    native_type = int
    number_type = '整数'


class FloatField(NumberField):
    """A field that validates input as a Float
    """

    primitive_type = float
    native_type = float
    number_type = '小数'


class DecimalField(NumberField):
    """A fixed-point decimal number field.
    """

    primitive_type = str
    native_type = decimal.Decimal
    number_type = '定点小数'

    def to_primitive(self, value):
        return str(value)

    def to_native(self, value):
        if isinstance(value, decimal.Decimal):
            return value

        if not isinstance(value, (str, bool)):
            value = value
        try:
            value = decimal.Decimal(value)
        except (TypeError, decimal.InvalidOperation):
            raise exceptions.InvalidUsage(self.messages['number_coerce'].format(self.label, value, self.number_type))

        return value


class BooleanField(BaseField):
    """A boolean field type. In addition to ``True`` and ``False``, coerces these
    values:

    + For ``True``: "True", "true", "1"
    + For ``False``: "False", "false", "0"

    """

    primitive_type = bool
    native_type = bool

    TRUE_VALUES = ('True', 'true', '1')
    FALSE_VALUES = ('False', 'false', '0')

    def to_native(self, value, context=None):
        if isinstance(value, str):
            if value in self.TRUE_VALUES:
                value = True
            elif value in self.FALSE_VALUES:
                value = False

        elif isinstance(value, int) and value in [0, 1]:
            value = bool(value)

        if not isinstance(value, bool):
            raise exceptions.InvalidUsage("{0}的值应是布尔值true或者false".format(self.label))

        return value


class DateField(BaseField):
    """Convert to and from ISO8601 date value.
    """

    primitive_type = str
    native_type = datetime.date

    MESSAGES = {
        'parse': "{0}日期格式错误,有效格式是ISO8601日期格式(YYYY-MM-DD)"
    }

    def to_native(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value

        try:
            return datetime_helper.parse_date(value)
        except (ValueError, TypeError):
            raise exceptions.InvalidUsage(self.messages['parse'].format(self.label))


class DateTimeField(BaseField):
    """Convert to and from ISO8601 datetime value.
    """

    primitive_type = str
    native_type = datetime.datetime

    MESSAGES = {
        'parse': '{0}时间格式错误,有效格式是ISO8601时间格式',
    }

    def to_native(self, value):
        if isinstance(value, datetime.datetime):
            return datetime_helper.get_utc_time(value)
        try:
            return datetime_helper.parse_datetime(value)
        except (ValueError, TypeError):
            raise exceptions.InvalidUsage(self.messages['parse'].format(self.label))


class TimestampField(BaseField):
    primitive_type = float
    native_type = datetime.datetime

    MESSAGES = {
        'parse': '{0}时间戳有误',
    }

    def to_native(self, value):
        if isinstance(value, datetime.datetime):
            return datetime_helper.get_utc_time(value)
        try:
            t = float(value)
            return datetime_helper.from_timestamp(t)
        except (ValueError, TypeError):
            raise exceptions.InvalidUsage(self.messages['parse'].format(self.label))

    def to_primitive(self, value):
        return value.timestamp()


class EmailField(StringField):
    """A field that validates input as an E-Mail-Address.
    """

    MESSAGES = {
        'email': "{0}的值{1}不是有效的邮箱",
    }

    EMAIL_REGEX = re.compile(r"""^(
        ( ( [%(atext)s]+ (\.[%(atext)s]+)* ) | ("( [%(qtext)s\s] | \\[%(vchar)s\s] )*") )
        @((?!-)[A-Z0-9-]{1,63}(?<!-)\.)+[A-Z]{2,63})$""" % {
        'atext': '-A-Z0-9!#$%&\'*+/=?^_`{|}~',
        'qtext': '\x21\x23-\x5B\\\x5D-\x7E',
        'vchar': '\x21-\x7E'
    },
                             re.I + re.X)

    def validate_email(self, value):
        if not EmailField.EMAIL_REGEX.match(value):
            raise exceptions.InvalidUsage(self.messages['email'].format(self.label, value))


class PhoneField(StringField):
    """A field that validates input as a phone number.
    """

    MESSAGES = {
        'phone': "{0}的值{1}不是有效的电话号码",
    }

    PHONE_REGEX = re.compile(r"^1[3456789]\d{9}$")

    def validate_phone(self, value):
        if not PhoneField.PHONE_REGEX.match(value):
            raise exceptions.InvalidUsage(self.messages['phone'].format(self.label, value))


class IDField(StringField):
    """A field that validates input as a ID number.
    """

    MESSAGES = {
        'ID': "{0}的值{1}不是有效的身份证号码",
    }

    ID_REGEX = re.compile(r"(^\d{15}$)|(^\d{17}([0-9]|X)$)")

    def validate_ID(self, value):
        if not IDField.ID_REGEX.match(value):
            raise exceptions.InvalidUsage(self.messages['ID'].format(self.label, value))


class ModelField(BaseField):
    """A field that can hold an instance of the specified model."""
    primitive_type = dict

    def __init__(self, label, model_spec, **kwargs):
        self.model_spec = model_spec
        super().__init__(label, **kwargs)

    def _repr_info(self):
        return self.model_spec.__name__

    def pre_setattr(self, value):
        if isinstance(value, self.model_spec):
            return value
        if isinstance(value, dict):
            return self.model_spec(value)
        raise exceptions.ServerError('{0}的值设置失败, 应是{1}或者字典类型'.format(self.label, self.model_spec.__name__))

    def to_native(self, value):
        if isinstance(value, self.model_spec):
            return value
        if isinstance(value, dict):
            return self.model_spec(value)
        raise exceptions.ServerError('{0}的值应是{1}或者字典类型'.format(self.label, self.model_spec.__name__))


class ListField(BaseField):
    """A field for storing a list of items, all of which must conform to the type
    specified by the ``field`` parameter.

    Use it like this::

        ...
        categories = ListField('类别', StringType())
    """

    primitive_type = list
    native_type = list

    def __init__(self, label, field, min_size=None, max_size=None, **kwargs):
        if not isinstance(field, BaseField):
            raise TypeError('field must be instance of BaseField')
        self.field = field
        self.min_size = min_size
        self.max_size = max_size
        super().__init__(label, **kwargs)

    def _repr_info(self):
        return self.field.__class__.__name__

    def _coerce(self, value):
        if isinstance(value, list):
            return value
        elif isinstance(value, (str, Mapping)):  # unacceptable iterables
            pass
        elif isinstance(value, Sequence):
            return value
        elif isinstance(value, Iterable):
            return value
        raise exceptions.InvalidUsage('{0}应是列表'.format(self.label))

    def to_native(self, value):
        value = self._coerce(value)
        data = []
        for index, item in enumerate(value):
            try:
                data.append(self.field.to_native(item))
            except exceptions.SanicException as exc:
                raise exceptions.InvalidUsage('{0}的第{1}值有误:{2}'.format(self.label, index, exc))
        return data

    def validate_length(self, value):
        list_length = len(value) if value else 0

        if self.min_size is not None and list_length < self.min_size:
            raise exceptions.InvalidUsage('{0}最少包含{1}项'.format(self.label, self.min_size))

        if self.max_size is not None and list_length > self.max_size:
            raise exceptions.InvalidUsage('{0}最多包含{1}项'.format(self.label, self.max_size))


class DictType(BaseField):
    """A field for storing a mapping of items.
    """

    primitive_type = dict
    native_type = dict

    def to_native(self, value):
        if not isinstance(value, Mapping):
            raise exceptions.InvalidUsage('{0}应是字典类型'.format(self.label))
        return dict(value)
