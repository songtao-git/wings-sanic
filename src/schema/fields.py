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
        self.label = label
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

        self.name = None
        self.owner_model = None
        self.parent_field = None
        self.typeclass = self.__class__
        self.is_compound = False

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
        return value

    def to_native(self, value):
        """
        Convert untrusted data to a richer Python construct.
        """
        return value

    def validate(self, value):
        """
        Validate the field and return a converted value or raise a
        ``InvalidUsage`` with a list of errors raised by the validation
        chain. Stop the validation process from continuing through the
        validators by raising ``StopValidationError`` instead of ``ValidationError``.

        """
        if self.is_compound:
            self.to_native(value)

        for validator in self.validators:
            validator(value)

        return value

    def check_required(self, value):
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

    def to_primitive(self, value):
        return str(value)


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

    def to_primitive(self, value):
        return datetime_helper.get_date_str(value)


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

    def to_primitive(self, value):
        return datetime_helper.get_time_str(value)


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
        @((?!-)[A-Z0-9-]{1,63}(?<!-)\.)+[A-Z]{2,63})$"""
        % {
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


class CompoundField(BaseField):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_compound = True
        try:
            self.field.parent_field = self
        except AttributeError:
            pass

    def _setup(self, field_name, owner_model):
        # Recursively set up inner fields.
        if hasattr(self, 'field'):
            self.field._setup(None, owner_model)
        super()._setup(field_name, owner_model)

    def to_native(self, value, context=None):
        context = context or get_export_context(to_native_converter)
        return to_native_converter(self, value, context)

    def to_primitive(self, value, context=None):
        context = context or get_export_context(to_primitive_converter)
        return to_primitive_converter(self, value, context)

    def _init_field(self, field, options):
        """
        Instantiate the inner field that represents each element within this compound type.
        In case the inner field is itself a compound type, its inner field can be provided
        as the ``nested_field`` keyword argument.
        """
        if not isinstance(field, BaseType):
            nested_field = options.pop('nested_field', None) or options.pop('compound_field', None)
            if nested_field:
                field = field(field=nested_field, **options)
            else:
                field = field(**options)
        return field


class ModelType(CompoundType):
    """A field that can hold an instance of the specified model."""

    primitive_type = dict

    @property
    def native_type(self):
        return self.model_class

    @property
    def fields(self):
        return self.model_class.fields

    @property
    def model_class(self):
        if self._model_class:
            return self._model_class

        model_class = import_string(self.model_name)
        self._model_class = model_class
        return model_class

    def __init__(self,
                 model_spec,  # type: typing.Type[T]
                 **kwargs):
        # type: (...) -> T

        if isinstance(model_spec, ModelMeta):
            self._model_class = model_spec
            self.model_name = self.model_class.__name__
        elif isinstance(model_spec, string_type):
            self._model_class = None
            self.model_name = model_spec
        else:
            raise TypeError("ModelType: Expected a model, got an argument "
                            "of the type '{}'.".format(model_spec.__class__.__name__))

        super(ModelType, self).__init__(**kwargs)

    def _repr_info(self):
        return self.model_class.__name__

    def _mock(self, context=None):
        return self.model_class.get_mock_object(context)

    def _setup(self, field_name, owner_model):
        # Resolve possible name-based model reference.
        if not self._model_class:
            if self.model_name == owner_model.__name__:
                self._model_class = owner_model
            else:
                pass  # Intentionally left blank, it will be setup later.
        super(ModelType, self)._setup(field_name, owner_model)

    def pre_setattr(self, value):
        if value is not None \
          and not isinstance(value, Model):
            if not isinstance(value, dict):
                raise ConversionError(_('Model conversion requires a model or dict'))
            value = self.model_class(value)
        return value

    def _convert(self, value, context):
        field_model_class = self.model_class
        if isinstance(value, field_model_class):
            model_class = type(value)
        elif isinstance(value, dict):
            model_class = field_model_class
        else:
            raise ConversionError(
                _("Input must be a mapping or '%s' instance") % field_model_class.__name__)
        if context.convert and context.oo:
            return model_class(value, context=context)
        else:
            return model_class.convert(value, context=context)

    def _export(self, value, format, context):
        if isinstance(value, Model):
            model_class = type(value)
        else:
            model_class = self.model_class
        return export_loop(model_class, value, context=context)


class ListType(CompoundType):
    """A field for storing a list of items, all of which must conform to the type
    specified by the ``field`` parameter.

    Use it like this::

        ...
        categories = ListType(StringType)
    """

    primitive_type = list
    native_type = list

    def __init__(self,
                 field,  # type: T
                 min_size=None, max_size=None, **kwargs):
        # type: (...) -> typing.List[T]

        self.field = self._init_field(field, kwargs)
        self.min_size = min_size
        self.max_size = max_size

        validators = [self.check_length] + kwargs.pop("validators", [])

        super(ListType, self).__init__(validators=validators, **kwargs)

    @property
    def model_class(self):
        return self.field.model_class

    def _repr_info(self):
        return self.field.__class__.__name__

    def _mock(self, context=None):
        random_length = get_value_in(self.min_size, self.max_size)

        return [self.field._mock(context) for dummy in range(random_length)]

    def _coerce(self, value):
        if isinstance(value, list):
            return value
        elif isinstance(value, (string_type, Mapping)): # unacceptable iterables
            pass
        elif isinstance(value, Sequence):
            return value
        elif isinstance(value, Iterable):
            return value
        raise ConversionError(_('Could not interpret the value as a list'))

    def _convert(self, value, context):
        value = self._coerce(value)
        data = []
        errors = {}
        for index, item in enumerate(value):
            try:
                data.append(context.field_converter(self.field, item, context))
            except BaseError as exc:
                errors[index] = exc
        if errors:
            raise CompoundError(errors)
        return data

    def check_length(self, value, context):
        list_length = len(value) if value else 0

        if self.min_size is not None and list_length < self.min_size:
            message = ({
                True: _('Please provide at least %d item.'),
                False: _('Please provide at least %d items.'),
            }[self.min_size == 1]) % self.min_size
            raise ValidationError(message)

        if self.max_size is not None and list_length > self.max_size:
            message = ({
                True: _('Please provide no more than %d item.'),
                False: _('Please provide no more than %d items.'),
            }[self.max_size == 1]) % self.max_size
            raise ValidationError(message)

    def _export(self, list_instance, format, context):
        """Loops over each item in the model and applies either the field
        transform or the multitype transform.  Essentially functions the same
        as `transforms.export_loop`.
        """
        data = []
        _export_level = self.field.get_export_level(context)
        if _export_level == DROP:
            return data
        for value in list_instance:
            shaped = self.field.export(value, format, context)
            if shaped is None:
                if _export_level <= NOT_NONE:
                    continue
            elif self.field.is_compound and len(shaped) == 0:
                if _export_level <= NONEMPTY:
                    continue
            data.append(shaped)
        return data


class DictType(CompoundType):
    """A field for storing a mapping of items, the values of which must conform to the type
    specified by the ``field`` parameter.

    Use it like this::

        ...
        categories = DictType(StringType)

    """

    primitive_type = dict
    native_type = dict

    def __init__(self, field, coerce_key=None, **kwargs):
        # type: (...) -> typing.Dict[str, T]

        self.field = self._init_field(field, kwargs)
        self.coerce_key = coerce_key or str
        super(DictType, self).__init__(**kwargs)

    @property
    def model_class(self):
        return self.field.model_class

    def _repr_info(self):
        return self.field.__class__.__name__

    def _convert(self, value, context, safe=False):
        if not isinstance(value, Mapping):
            raise ConversionError(_('Only mappings may be used in a DictType'))

        data = {}
        errors = {}
        for k, v in iteritems(value):
            try:
                data[self.coerce_key(k)] = context.field_converter(self.field, v, context)
            except BaseError as exc:
                errors[k] = exc
        if errors:
            raise CompoundError(errors)
        return data

    def _export(self, dict_instance, format, context):
        """Loops over each item in the model and applies either the field
        transform or the multitype transform.  Essentially functions the same
        as `transforms.export_loop`.
        """
        data = {}
        _export_level = self.field.get_export_level(context)
        if _export_level == DROP:
            return data
        for key, value in iteritems(dict_instance):
            shaped = self.field.export(value, format, context)
            if shaped is None:
                if _export_level <= NOT_NONE:
                    continue
            elif self.field.is_compound and len(shaped) == 0:
                if _export_level <= NONEMPTY:
                    continue
            data[key] = shaped
        return data

