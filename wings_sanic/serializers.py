# -*- coding: utf-8 -*-
import datetime
import decimal
import inspect
import json
import numbers
import re
import uuid
from collections import Iterable, OrderedDict
from typing import Sequence, Mapping

import six
from sanic import exceptions, request

from . import datetime_helper, utils, settings

__all__ = ['UUIDField', 'StringField', 'NumberField', 'IntField', 'FloatField', 'DecimalField', 'BooleanField',
           'DateTimeField', 'DateField', 'TimestampField', 'EmailField', 'PhoneField', 'IDField', 'SerializerField',
           'ListField', 'JsonField', 'Serializer', 'ListSerializer', 'FileField']


class Undefined:
    """A type and singleton value (like None) to represent fields that
    have not been initialized.
    """
    _instance = None

    def __str__(self):
        return 'Undefined'

    def __repr__(self):
        return 'Undefined'

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __lt__(self, other):
        self._cmp_err(other, '<')

    def __gt__(self, other):
        self._cmp_err(other, '>')

    def __le__(self, other):
        self._cmp_err(other, '<=')

    def __ge__(self, other):
        self._cmp_err(other, '>=')

    def _cmp_err(self, other, op):
        raise TypeError("unorderable types: {0}() {1} {2}()".format(
            self.__class__.__name__, op, other.__class__.__name__))

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        elif cls is not Undefined:
            raise TypeError("type 'UndefinedType' is not an acceptable base type")
        return cls._instance

    def __init__(self):
        pass

    def __setattr__(self, name, value):
        raise TypeError("'UndefinedType' object does not support attribute assignment")


Undefined = Undefined()

definitions = {}


# ---------------------- Field -----------------------

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
                validators[attr_name] = 1

        attrs["_validators"] = validators

        return type.__new__(mcs, name, bases, attrs)


class BaseField(metaclass=FieldMeta):
    """A base class for Fields in a Model. Instances of this
    class may be added to subclasses of ``Model`` to define a model wings_sanic.

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
    is_composition = False

    MESSAGES = {
        'required': "{0}必填",
        'choices': "{0}是{1}其中之一.",
    }

    def __init__(self, label=None, help_text=None, required=False,
                 default=Undefined, choices=None, validators=None,
                 serialize_when_none=True, messages=None, read_only=None, write_only=None):
        assert not (required and default is not Undefined), 'May not set both `required` and `default`'
        assert not (read_only and write_only), 'May not set both `read_only` and `write_only`'

        super().__init__()
        # if not label or not isinstance(label, str):
        #     raise ValueError('label must be a effective string')
        self._label = label
        self.help_text = help_text
        self.required = required
        self._default = default
        if choices and (isinstance(choices, str) or not isinstance(choices, Iterable)):
            raise TypeError('"choices" must be a non-string Iterable')
        self.choices = choices

        self.validators = [getattr(self, validator_name) for validator_name in self._validators]
        if validators:
            self.validators += list(validators)
        self.serialize_when_none = serialize_when_none
        self.messages = dict(self.MESSAGES, **(messages or {}))
        self.read_only = read_only
        self.write_only = write_only

        self.name = None
        self.owner_serializer = None

    def __repr__(self):
        if self._repr_info():
            type_ = "%s(%s) instance" % (self.__class__.__name__, self._repr_info())
        else:
            type_ = "%s instance" % (self.__class__.__name__)
        model = " on %s" % self.owner_serializer.__name__ if self.owner_serializer else ''
        field = " as '%s'" % self.name if self.name else ''
        return "<%s>" % (type_ + model + field)

    def _repr_info(self):
        return None

    def _setup(self, field_name, owner_serializer):
        """Perform late-stage setup tasks that are run after the containing model
        has been created.
        """
        self.name = field_name
        assert issubclass(owner_serializer, BaseSerializer), 'owner_model should be subclass of BaseSerializer'
        self.owner_serializer = owner_serializer

    @property
    def label(self):
        return self._label or self.name

    @property
    def default(self):
        default = self._default
        if callable(default):
            default = default()
        return default

    def _preproccess(self, value, context=None):
        return value

    def to_primitive(self, value, context=None):
        """Convert internal data to a value safe to serialize.
        """
        value = self._preproccess(value, context) if value is not None else None
        if value is None and self._default is not Undefined:
            value = self.default

        if value is None:
            return None

        if self.primitive_type is not None and not isinstance(value, self.primitive_type):
            return self.primitive_type(value)
        return value

    def to_native(self, value, context=None):
        """
        Convert untrusted data to a richer Python construct.
        """
        value = self._preproccess(value, context) if value is not None else None
        if value is None and self._default is not Undefined:
            value = self.default
        return value

    def validate(self, value, context=None):
        native_data = self.to_native(value, context)
        for validator in self.validators:
            if (native_data is None or native_data is Undefined) \
                    and validator != self.validate_required:
                continue
            validator(native_data, context)
        return native_data

    def validate_required(self, value, context=None):
        if self.required and (value is None or value is Undefined):
            raise exceptions.InvalidUsage(self.messages['required'].format(self.label))

    def validate_choices(self, value, context=None):
        if self.choices is not None:
            if value not in self.choices:
                raise exceptions.InvalidUsage(self.messages['choices'].format(self.label, self.choices))

    def openapi_spec(self):
        spec = {
            'required': self.required,
            'name': self.name,
            'description': ':'.join([i for i in [self.label, self.help_text] if i]),
        }
        if self.choices:
            spec['enum'] = self.choices
        if self.write_only is not None:
            spec['writeOnly'] = self.write_only
        if self.read_only is not None:
            spec['readOnly'] = self.read_only
        return spec


class UUIDField(BaseField):
    """A field that stores a valid UUID value.
    """
    primitive_type = str
    native_type = uuid.UUID

    MESSAGES = {
        'convert': "{0}的值{1}不能转为UUID",
    }

    def _preproccess(self, value, context=None):
        if not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(value)
            except (TypeError, ValueError):
                raise exceptions.InvalidUsage(self.messages['convert'].format(self.label, value))
        return value

    def openapi_spec(self):
        return {
            'type': 'string',
            **super().openapi_spec()
        }


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

    def __init__(self, label=None, regex=None, max_length=None, min_length=None, **kwargs):
        self.regex = re.compile(regex) if regex else None
        self.max_length = max_length
        self.min_length = min_length
        super().__init__(label, **kwargs)

    def _preproccess(self, value, context=None):
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            try:
                return str(value, 'utf-8')
            except UnicodeError:
                raise exceptions.InvalidUsage(self.messages['decode'].format(self.label))
        return str(value)

    def validate_length(self, value, context=None):
        length = len(value)
        if self.max_length is not None and length > self.max_length:
            raise exceptions.InvalidUsage(self.messages['max_length'].format(self.label, self.max_length))

        if self.min_length is not None and length < self.min_length:
            raise exceptions.InvalidUsage(self.messages['min_length'].format(self.label, self.min_length))

    def validate_regex(self, value, context=None):
        if self.regex is not None and self.regex.match(value) is None:
            raise exceptions.InvalidUsage(self.messages['regex'].format(self.label))

    def openapi_spec(self):
        return {
            'type': 'string',
            **super().openapi_spec()
        }


class NumberField(BaseField):
    """A generic number field.
    Converts to and validates against `number_type` parameter.
    :param strict: eg. `1.2` is not effective for IntField if `strict` is True; but effective if False
    """

    primitive_type = None
    native_type = None
    number_type = None
    MESSAGES = {
        'number_coerce': "{0}的值{1}不是有效的{2}",
        'number_min': "{0}的值应大于等于{1}",
        'number_max': "{0}的值应小于等于{1}",
    }

    def __init__(self, label=None, min_value=None, max_value=None, strict=True, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        self.strict = strict

        super().__init__(label, **kwargs)

    def _preproccess(self, value, context=None):
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

    def validate_range(self, value, context=None):
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

    def openapi_spec(self):
        return {
            "type": "integer",
            "format": "int64",
            **super().openapi_spec()
        }


class FloatField(NumberField):
    """A field that validates input as a Float
    """

    primitive_type = float
    native_type = float
    number_type = '浮点数'

    def openapi_spec(self):
        return {
            "type": "number",
            "format": "double",
            **super().openapi_spec()
        }


class DecimalField(NumberField):
    """A fixed-point decimal number field.
    """

    primitive_type = str
    native_type = decimal.Decimal
    number_type = '定点小数'

    def _preproccess(self, value, context=None):
        if isinstance(value, decimal.Decimal):
            return value

        if not isinstance(value, (str, bool)):
            value = value
        try:
            value = decimal.Decimal(value)
        except (TypeError, decimal.InvalidOperation):
            raise exceptions.InvalidUsage(
                self.messages['number_coerce'].format(self.label, value, self.number_type))

        return value

    def openapi_spec(self):
        return {
            "type": "string",
            **super().openapi_spec()
        }


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

    def _preproccess(self, value, context=None):
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

    def openapi_spec(self):
        return {
            "type": "boolean",
            **super().openapi_spec()
        }


class DateField(BaseField):
    """Convert to and from ISO8601 date value.
    """

    primitive_type = str
    native_type = datetime.date

    MESSAGES = {
        'parse': "{0}日期格式错误,有效格式是ISO8601日期格式(YYYY-MM-DD)"
    }

    def _preproccess(self, value, context=None):
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value

        try:
            return datetime_helper.parse_date(value)
        except (ValueError, TypeError):
            raise exceptions.InvalidUsage(self.messages['parse'].format(self.label))

    def to_primitive(self, value, context=None):
        value = super().to_primitive(value, context)
        if value is None:
            return None
        return datetime_helper.get_date_str(value)

    def openapi_spec(self):
        return {
            "type": "string",
            "format": "date",
            **super().openapi_spec()
        }


class DateTimeField(BaseField):
    """Convert to and from ISO8601 datetime value.
    """

    primitive_type = str
    native_type = datetime.datetime

    MESSAGES = {
        'parse': '{0}时间格式错误,有效格式是ISO8601时间格式',
    }

    def _preproccess(self, value, context=None):
        if isinstance(value, datetime.datetime):
            return datetime_helper.get_utc_time(value)
        try:
            return datetime_helper.parse_datetime(value)
        except (ValueError, TypeError):
            raise exceptions.InvalidUsage(self.messages['parse'].format(self.label))

    def to_primitive(self, value, context=None):
        value = super().to_primitive(value, context)
        if value is None:
            return None
        return datetime_helper.get_date_str(value)

    def openapi_spec(self):
        return {
            "type": "string",
            "format": "date-time",
            **super().openapi_spec()
        }


class TimestampField(BaseField):
    primitive_type = float
    native_type = datetime.datetime

    MESSAGES = {
        'parse': '{0}时间戳有误',
    }

    def _preproccess(self, value, context=None):
        if isinstance(value, datetime.datetime):
            return datetime_helper.get_utc_time(value)
        try:
            t = float(value)
            return datetime_helper.from_timestamp(t)
        except (ValueError, TypeError):
            raise exceptions.InvalidUsage(self.messages['parse'].format(self.label))

    def to_primitive(self, value, context=None):
        value = super().to_primitive(value, context)
        if value is None:
            return None
        return value.timestamp()

    def openapi_spec(self):
        return {
            "type": "number",
            "format": "double",
            **super().openapi_spec()
        }


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

    def validate_email(self, value, context=None):
        if not EmailField.EMAIL_REGEX.match(value):
            raise exceptions.InvalidUsage(self.messages['email'].format(self.label, value))


class PhoneField(StringField):
    """A field that validates input as a phone number.
    """

    MESSAGES = {
        'phone': "{0}的值{1}不是有效的电话号码",
    }

    PHONE_REGEX = re.compile(r"^1[3456789]\d{9}$")

    def validate_phone(self, value, context=None):
        if not PhoneField.PHONE_REGEX.match(value):
            raise exceptions.InvalidUsage(self.messages['phone'].format(self.label, value))


class IDField(StringField):
    """A field that validates input as a ID number.
    """

    MESSAGES = {
        'ID': "{0}的值{1}不是有效的身份证号码",
    }

    ID_REGEX = re.compile(r"(^\d{15}$)|(^\d{17}([0-9]|X)$)")

    def validate_ID(self, value, context=None):
        if not IDField.ID_REGEX.match(value):
            raise exceptions.InvalidUsage(self.messages['ID'].format(self.label, value))


class FileField(BaseField):
    """A field that validates input as a ID number.
    """

    MESSAGES = {
        'invalid': '{0}提交的的值不是有效的文件',
        'no_name': '{0}提交的值没有文件名',
        'empty': '{0}提交的值是一个空文件',
        'max_length': "{0}的内容太大了"
    }

    def __init__(self, label, file_url=None, allow_empty_file=False, max_length=None, **kwargs):
        self.max_length = max_length
        self.allow_empty_file = allow_empty_file
        self.file_url = file_url or settings.FILE_URL

        assert 'default' not in kwargs, 'FileField cannot set default'
        super().__init__(label, **kwargs)

    def to_native(self, value, context=None):
        value = super().to_native(value, context)

        if not isinstance(value, request.File):
            raise exceptions.InvalidUsage(self.messages['invalid'].format(self.label))

        if not value.name:
            raise exceptions.InvalidUsage(self.messages['no_name'].format(self.label))
        if not self.allow_empty_file and not len(value.body):
            raise exceptions.InvalidUsage(self.messages['empty'].format(self.label))
        if self.max_length and len(value.body) > self.max_length:
            raise exceptions.InvalidUsage(self.messages['max_length'].format(self.label))

        return value

    def to_primitive(self, value, context=None):
        value = super().to_primitive(value, context)
        if value is None:
            return None

        file_url = self.file_url or settings.FILE_URL
        if hasattr(value, 'name'):
            return (file_url or '') + value.name

        return (file_url or '') + value

    def openapi_spec(self):
        return {
            'type': 'file',
            **super().openapi_spec()
        }


class SerializerField(BaseField):
    """A field that can hold an instance of the specified model."""
    primitive_type = dict
    native_type = dict
    is_composition = True

    def __init__(self, label=None, serializer=None, **kwargs):
        assert 'default' not in kwargs, 'SerializerField cannot set default'
        if not isinstance(serializer, Serializer):
            raise TypeError('serializer must be instance of Serializer')
        serializer._setup(self)
        self.serializer = serializer
        super().__init__(label, **kwargs)

    def _repr_info(self):
        return self.serializer.__class__.__name__

    def to_native(self, value, context=None):
        value = super().to_native(value, context)
        if value is None:
            return None

        return self.serializer.to_native(value, context)

    def validate(self, value, context=None):
        value = self.serializer.validate(value, context) if value is not None else None
        for validator in self.validators:
            validator(value, context)
        return value

    def to_primitive(self, value, context=None):
        value = super().to_primitive(value, context)
        return self.serializer.to_primitive(value, context) if value is not None else None

    def openapi_spec(self):
        res = self.serializer.openapi_spec()
        res.update(super().openapi_spec())
        return res


class ListField(BaseField):
    """A field for storing a list of items, all of which must conform to the type
    specified by the ``field`` parameter.

    Use it like this::

        ...
        categories = ListField('类别', StringField('类别名称'))
    """

    primitive_type = list
    native_type = list
    is_composition = True

    def __init__(self, label=None, field=None, min_size=None, max_size=None, **kwargs):
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

    def _preproccess(self, value, context=None):
        value = super()._preproccess(value, context)
        if not value:
            return []
        value = self._coerce(value)
        return value

    def to_native(self, value, context=None):
        value = super().to_native(value, context)
        data = []
        for index, item in enumerate(value):
            try:
                item_data = self.field.to_native(item, context)
                if item_data:
                    data.append(item_data)
            except exceptions.SanicException as exc:
                raise exceptions.InvalidUsage('{0}的第{1}值有误:{2}'.format(self.label, index + 1, exc))
        return data

    def to_primitive(self, value, context=None):
        value = super().to_primitive(value, context)
        data = []
        for index, item in enumerate(value):
            try:
                item_data = self.field.to_primitive(item, context)
                if item_data:
                    data.append(item_data)
            except exceptions.SanicException as exc:
                raise exceptions.InvalidUsage('{0}的第{1}值有误:{2}'.format(self.label, index, exc))
        return data

    def validate(self, value, context=None):
        data = []
        if value:
            value = self._coerce(value)
            data = []
            for index, item in enumerate(value):
                try:
                    item_data = self.field.validate(item, context)
                    if item_data:
                        data.append(item_data)
                except exceptions.SanicException as exc:
                    raise exceptions.InvalidUsage('{0}的第{1}个值有误:{2}'.format(self.label, index, exc))

        for validator in self.validators:
            validator(data, context)

        return data

    def validate_length(self, value, context=None):
        list_length = len(value) if value else 0

        if self.min_size is not None and list_length < self.min_size:
            raise exceptions.InvalidUsage('{0}最少包含{1}项'.format(self.label, self.min_size))

        if self.max_size is not None and list_length > self.max_size:
            raise exceptions.InvalidUsage('{0}最多包含{1}项'.format(self.label, self.max_size))

    def openapi_spec(self):
        return {
            "type": "array",
            "items": self.field.openapi_spec(),
            **super().openapi_spec()
        }


class JsonField(BaseField):
    """A field for json.
    """

    primitive_type = None
    native_type = None
    is_composition = True

    def to_native(self, value, context=None):
        try:
            if isinstance(value, six.binary_type):
                value = value.decode('utf-8')
                return json.loads(value)
            elif isinstance(value, str):
                return json.loads(value)
            else:
                return utils.to_native(value)
        except (TypeError, ValueError):
            raise exceptions.InvalidUsage('{0}的值不是有效的json格式')

    def to_primitive(self, value, context=None):
        utils.to_primitive(value)

    def openapi_spec(self):
        return {
            "type": "object",
            "properties": None,
            **super().openapi_spec()
        }


# ---------------------- Serializer ------------------------

class SerializerMeta(type):
    """
    Metaclass for Serializer. 
    """

    def __new__(mcs, name, bases, attrs):
        """
        Meta class for Serializer. Merges `fields`, `validators` and `meta`.
        """

        # Structures used to accumulate meta info
        meta = OrderedDict()
        fields = OrderedDict()
        validators = OrderedDict()  # Model level
        current_fields = OrderedDict()

        # Accumulate info from parent classes
        for base in reversed(bases):
            # Copy parent fields
            fields.update(getattr(base, '_fields', {}))

            # Copy parent meta options
            meta.update(getattr(base, '_meta', {}))

            # Copy parent validators
            validators.update(getattr(base, '_validators', {}))

        for attr_name, attr in attrs.items():
            if attr_name.startswith('validate_'):
                validators[attr_name] = 1
            if isinstance(attr, BaseField):
                fields[attr_name] = attr
                current_fields[attr_name] = attr
            elif all([attr_name == 'Meta', inspect.isclass(attr)]):
                meta.update(attr.__dict__)

        attrs['_fields'] = fields
        attrs['_validators'] = validators
        attrs['_meta'] = meta

        cls = type.__new__(mcs, name, bases, attrs)
        # setup current model fields(field_name, owner_model)
        for attr_name, attr in current_fields.items():
            attr._setup(attr_name, cls)

        return cls


class BaseSerializer(metaclass=SerializerMeta):
    """
    Base class for Serializer
    :param validators:
        A list of callables. Each callable receives the value after it has been
        converted into a rich python type. Default: []
    """

    def __init__(self, validators=None):
        self.fields = OrderedDict(self._fields)
        self.validators = [getattr(self, validator_name) for validator_name in self._validators]
        if validators:
            self.validators += list(validators)

        self.parent_field = None

    def _setup(self, parent_field):
        assert isinstance(parent_field, BaseField), 'parent_field should be instance of BaseField'
        self.parent_field = parent_field

    def to_native(self, data, context=None):
        raise NotImplementedError

    def to_primitive(self, data, context=None):
        raise NotImplementedError

    def validate(self, data, context=None):
        raise NotImplementedError

    def openapi_spec(self):
        raise NotImplementedError


def field_from(data):
    if isinstance(data, BaseField):
        return data
    if isinstance(data, BaseSerializer):
        return SerializerField(serializer=data)
    if isinstance(data, dict):
        return SerializerField(serializer=serializer_from(data))
    if isinstance(data, list):
        assert len(data) == 1
        return ListField(field=field_from(data[0]))


def serializer_from(data):
    assert not isinstance(data, BaseField)
    if isinstance(data, BaseSerializer):
        return data
    if isinstance(data, dict):
        serializer = Serializer()
        for field_name, field_data in data.items():
            field = field_from(field_data)
            field._setup(field_name, serializer.__class__)
            serializer.fields[field_name] = field
        return serializer
    if isinstance(data, list):
        assert len(data) == 1
        return ListSerializer(child=serializer_from(data[0]))


class Serializer(BaseSerializer):
    def __init__(self, *args, **kwargs):
        kwargs.pop('many', None)
        super().__init__(*args, **kwargs)

        if self.__class__ != Serializer and self.__class__ not in definitions:
            definitions[utils.cls_str_of_obj(self)] = self.definition

    def __new__(cls, *args, **kwargs):
        # We override this method in order to automagically create
        # `ListSerializer` class instead when `many=True` is set.
        if kwargs.pop('many', False):
            return cls.many_init(*args, **kwargs)
        return super(Serializer, cls).__new__(cls)

    @classmethod
    def many_init(cls, *args, **kwargs):
        child_serializer = cls(*args, **kwargs)
        return ListSerializer(child=child_serializer)

    def to_native(self, data, context=None):
        if data is None or data is Undefined:
            return None
        native_data = {}
        for field_name, field in self.fields.items():

            if hasattr(data, field_name):
                field_data = getattr(data, field_name)
            elif isinstance(data, Mapping):
                field_data = data.get(field_name, None)
            else:
                field_data = None

            native_data[field_name] = field.to_native(field_data, context)
        return native_data

    def validate(self, data, context=None):
        """
        Validates the state of the model.
        """

        partial = utils.get_value(context, 'partial', False)
        data = self.to_native(data, context)

        if data is not None:
            validate_data = {}
            for field_name, field in self.fields.items():
                field_data = data.get(field_name, None)
                if field.read_only or (field_data is None and partial):
                    continue
                validate_data[field_name] = field.validate(field_data, context)
            data = validate_data

        for validator in self.validators:
            data = validator(data, context)
        return data

    def to_primitive(self, data, context=None):
        if data is None:
            return None
        primitive_data = {}
        for field_name, field in self.fields.items():
            serialize_when_none = utils.get_value(context,
                                                  'serialize_when_none',
                                                  utils.get_value(self._meta,
                                                                  'serialize_when_none',
                                                                  field.serialize_when_none))
            if hasattr(data, field_name):
                field_data = getattr(data, field_name)
            elif isinstance(data, Mapping):
                field_data = data.get(field_name, None)
            else:
                field_data = None

            if field.write_only or (field_data is None and not serialize_when_none):
                continue
            primitive_data[field_name] = field.to_primitive(field_data, context)
        return primitive_data

    @property
    def definition(self):
        properties = {}
        required = []
        for name, field in self.fields.items():
            item_spec = field.openapi_spec()
            item_spec.pop('name', None)

            properties[name] = item_spec

            if item_spec.pop('required', False):
                required.append(name)

        return {
            "type": "object",
            'required': required,
            "properties": properties
        }

    def openapi_spec(self):
        if self.__class__ != Serializer:
            return {
                "type": "object",
                "$ref": f"#/definitions/{utils.cls_str_of_obj(self)}",
            }
        return {
            "type": "object",
            "properties": {
                name: field.openapi_spec()
                for name, field in self.fields.items()
            }
        }


class ListSerializer(BaseSerializer):
    def __init__(self, child, **kwargs):
        if not isinstance(child, BaseSerializer):
            raise TypeError('child must be instance of BaseSerializer')
        self.child = child
        super().__init__(**kwargs)
        assert not self.fields, 'fields of ListSerializer should be empty'

    def ensure_sequence(self, value):
        if isinstance(value, list):
            return value
        elif isinstance(value, (str, Mapping)):  # unacceptable iterables
            pass
        elif isinstance(value, Sequence):
            return value
        elif isinstance(value, Iterable):
            return value
        raise exceptions.InvalidUsage('内容应是列表')

    def to_native(self, data, context=None):
        if data is None or data is Undefined:
            return []

        data = []
        for item in self.ensure_sequence(data):
            item_data = self.child.to_native(item, context)
            if item_data:
                data.append(item_data)

        return data

    def to_primitive(self, data, context=None):
        if data is None or data is Undefined:
            return []

        data = []
        for item in self.ensure_sequence(data):
            item_data = self.child.to_primitive(item, context)
            if item_data:
                data.append(item_data)

    def validate(self, data, context=None):
        data = self.to_native(data)
        if data:
            validated_data = []
            for index, item in enumerate(data):
                try:
                    validated_data.append(self.child.validate(item, context))
                except exceptions.SanicException as exc:
                    raise exceptions.InvalidUsage('第{0}个值有误:{1}'.format(index + 1, exc))
            data = validated_data

        for validator in self.validators:
            data = validator(data, context)
        return data

    def openapi_spec(self):
        return {
            "type": "array",
            "items": self.child.openapi_spec()
        }
