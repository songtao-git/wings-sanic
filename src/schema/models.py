# -*- coding: utf-8 -*-
import inspect
from collections import OrderedDict

from .undefined import Undefined
from .fields import BaseField
from copy import deepcopy


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
                validators[attr_name[9:]] = attr
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


class Serializer(metaclass=SerializerMeta):

    """
    A serializer instance used to `to_native`(validate) or `to_primitive` the input data
    :param dict fields:
        KeyValuePair(field_name: str, field: BaseField), the `fields` and
        serializer's declared fields will compose final `fields`.
    :param bool partial:
        Allow partial data to validate. Essentially drops the ``required=True``
        settings from field definitions. Default: False
    :param bool many:
        omit a list if `many=True`. Default: False
    :param validators:
        A list of callables. Each callable receives the value after it has been
        converted into a rich python type. Default: []
    """

    def __init__(self, fields=None, partial=False, many=False, validators=None):
        self.fields = deepcopy(self._fields)
        if fields:
            self.fields.update(fields)
        self.validators = list(self._validators.values())
        if validators:
            self.validators += list(validators)
        self.partial = partial
        self.many = many

    def validate(self, partial=False, convert=True, app_data=None, **kwargs):
        """
        Validates the state of the model. If the data is invalid, raises a ``DataError``
        with error messages.

        :param bool partial:
            Allow partial data to validate. Essentially drops the ``required=True``
            settings from field definitions. Default: False
        :param convert:
            Controls whether to perform import conversion before validating.
            Can be turned off to skip an unnecessary conversion step if all values
            are known to have the right datatypes (e.g., when validating immediately
            after the initial import). Default: True
        """
        if not self._data.converted and partial:
            return  # no new input data to validate
        try:
            data = self._convert(validate=True,
                partial=partial, convert=convert, app_data=app_data, **kwargs)
            self._data.valid = data
        except DataError as e:
            valid = dict(self._data.valid)
            valid.update(e.partial_data)
            self._data.valid = valid
            raise
        finally:
            self._data.converted = {}

    def to_native(self, role=None, app_data=None, **kwargs):
        return to_native(self._schema, self, role=role, app_data=app_data, **kwargs)

    def to_primitive(self, role=None, app_data=None, **kwargs):
        return to_primitive(self._schema, self, role=role, app_data=app_data, **kwargs)
