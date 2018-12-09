# -*- coding: utf-8 -*-
import re

from . import serializers


class HandlerMetaData:
    path_name_re = re.compile(r'<(.+?)>')

    def sure_serializer(self, params):
        if params is None:
            return None
        if isinstance(params, serializers.BaseSerializer):
            return params
        assert isinstance(params, dict)
        return serializers.Serializer(fields=params)

    def __init__(
            self,
            path,
            method,
            tags=None,
            query_params=None,
            body_serializer=None,
            header_params=None,
            path_params=None,
            response_serializer=None,
            success_code=200,
            context=None,
    ):
        self.path = path
        self.method = method
        self.tags = set(tags or [])
        self.success_code = success_code
        self.path_serializer = self.sure_serializer(path_params)
        self.query_serializer = self.sure_serializer(query_params)
        self.body_serializer = self.sure_serializer(body_serializer)
        self.header_serializer = self.sure_serializer(header_params)
        self.response_serializer = self.sure_serializer(response_serializer)
        self.context = context

        fields_from_path = set(self.path_name_re.findall(path))
        fields_from_serializer = set(getattr(self.path_serializer, 'fields', {}).keys())
        if fields_from_path != fields_from_serializer:
            raise ValueError('fields from path(%s) not match fields from path_params(%s)' %
                             (fields_from_path, fields_from_serializer))
