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
        return serializers.serializer_from(params)

    def __init__(
            self,
            uri,
            method,
            tags=None,
            query_params=None,
            body_serializer=None,
            header_params=None,
            path_params=None,
            response_serializer=None,
            success_code=200,
            context=None,
            swagger_exclude=False,
            swagger_group: dict = None
    ):
        self.uri = uri
        self.method = method
        self.tags = list(set(tags or []))
        self.success_code = success_code
        self.path_serializer = self.sure_serializer(path_params)
        self.query_serializer = self.sure_serializer(query_params)
        self.header_serializer = self.sure_serializer(header_params)

        self.body_serializer = self.sure_serializer(body_serializer)

        self.response_serializer = self.sure_serializer(response_serializer)
        self.context = context
        self.swagger_exclude = swagger_exclude
        self.swagger_group = swagger_group

        fields_from_path = set(self.path_name_re.findall(uri))
        fields_from_serializer = set(getattr(self.path_serializer, 'fields', {}).keys())
        if fields_from_path != fields_from_serializer:
            raise ValueError('fields from path(%s) not match fields from path_params(%s)' %
                             (fields_from_path, fields_from_serializer))
