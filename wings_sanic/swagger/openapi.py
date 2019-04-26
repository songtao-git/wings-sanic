import copy
import inspect
import os
import re
from itertools import repeat

from sanic.blueprints import Blueprint
from sanic.response import json
from sanic.views import CompositionView

from wings_sanic import settings, utils, serializers
from wings_sanic.views import get_response_shape

blueprint = Blueprint('swagger', url_prefix='/swagger')

_spec = {}


def __summary_description(doc_string):
    doc_string = (doc_string or "").strip()
    s = doc_string.split('\n', 1)
    if len(s) == 1:
        s.append("")
    return s[0].strip(), s[1].strip()


def __update_definitions(group_spec, serializer):
    # 解析serializer
    if isinstance(serializer, serializers.BaseSerializer):
        serializer = serializer.child if isinstance(serializer, serializers.ListSerializer) else serializer
        cls_str = utils.cls_str_of_obj(serializer)
        if cls_str in serializers.definitions:
            group_spec['definitions'][cls_str] = serializers.definitions[cls_str]
        # 递归解析serializer的fields(其中可能存在SerializerField)
        for field in serializer.fields.values():
            __update_definitions(group_spec, field)
    # 解析field
    if isinstance(serializer, serializers.SerializerField):
        __update_definitions(group_spec, serializer.serializer)
    if isinstance(serializer, serializers.ListField):
        __update_definitions(group_spec, serializer.field)


@blueprint.listener('before_server_start')
def build_spec(app, loop):
    for uri, route in app.router.routes_all.items():
        if uri.startswith(f"{settings.GLOBAL_URL_PREFIX}/swagger"):
            continue

        # Build list of methods and their handler functions
        handler_type = type(route.handler)
        if handler_type is CompositionView:
            method_handlers = route.handler.handlers.items()
        else:
            method_handlers = zip(route.methods, repeat(route.handler))

        # format path parameters '<param>' to '{param}'
        uri_parsed = uri
        for parameter in route.parameters:
            uri_parsed = re.sub('<' + parameter.name + '.*?>', '{' + parameter.name + '}', uri_parsed)

        for _method, _handler in method_handlers:
            metadata = utils.get_value(_handler, 'metadata')
            if _method == 'OPTIONS' or not metadata or metadata.swagger_exclude:
                continue

            # ensure group info
            group = metadata.swagger_group or 'default'
            if not isinstance(group, dict):
                group = {'title': str(group)}
            group_title = group.get('title', None) or 'default'
            if group_title not in _spec:
                _spec[group_title] = copy.deepcopy(settings.get('SWAGGER'))
                _spec[group_title].update({
                    'swagger': '2.0',
                    'definitions': {},
                    'paths': {},
                })
                _spec[group_title]['info'].update(group)

            group_spec = _spec[group_title]
            if uri_parsed not in group_spec['paths']:
                group_spec['paths'][uri_parsed] = {}

            # generate path
            parameters = []
            # header
            for name, field in (utils.get_value(metadata.header_serializer, 'fields') or {}).items():
                parameter = field.openapi_spec()
                parameter.update({'in': 'header'})
                parameters.append(parameter)
                __update_definitions(group_spec, metadata.header_serializer)

            # path
            for name, field in (utils.get_value(metadata.path_serializer, 'fields') or {}).items():
                parameter = field.openapi_spec()
                parameter.update({'in': 'path', 'required': True})
                parameters.append(parameter)
                __update_definitions(group_spec, metadata.path_serializer)

            # query
            for name, field in (utils.get_value(metadata.query_serializer, 'fields') or {}).items():
                parameter = field.openapi_spec()
                parameter.update({'in': 'query'})
                parameters.append(parameter)
                __update_definitions(group_spec, metadata.query_serializer)

            # body
            has_file_filed = False
            if metadata.body_serializer:
                body_spec = metadata.body_serializer.openapi_spec()
                import wings_sanic
                for _, f in metadata.body_serializer.fields.items():
                    if isinstance(f, wings_sanic.FileField):
                        has_file_filed = True
                        break

                if not has_file_filed:
                    parameters.append({
                        'in': 'body',
                        'name': 'body',
                        'required': True,
                        'schema': body_spec
                    })
                else:
                    cls_str = utils.cls_str_of_obj(metadata.body_serializer)
                    if cls_str in serializers.definitions:
                        body_spec = serializers.definitions[cls_str]
                    for name, field_spec in body_spec.get('properties', {}).items():
                        parameters.append({
                            'in': 'formData',
                            'name': name,
                            **field_spec
                        })

                __update_definitions(group_spec, metadata.body_serializer)

            # response
            response_spec = None
            if metadata.response_serializer:
                response_spec = metadata.response_serializer.openapi_spec()

                __update_definitions(group_spec, metadata.response_serializer)

            response_shape = get_response_shape(metadata.context)
            response_spec = response_shape.swagger(response_spec)

            summary, description = __summary_description(inspect.cleandoc(_handler.__doc__ or ""))

            endpoint = {
                'operationId': utils.meth_str(_handler),
                'summary': summary,
                'description': description,
                'consumes': ['multipart/form-data'] if has_file_filed else ['application/json'],
                'produces': ['application/json'],
                'tags': metadata.tags,
                'parameters': parameters,
                'responses': {
                    "200": {
                        "description": None,
                        "examples": None,
                        "schema": response_spec
                    }
                },
            }

            group_spec['paths'][uri_parsed][_method.lower()] = endpoint


@blueprint.route('/group/')
def spec_group(request, *args, **kwargs):
    # default第一个，其他是排序后的结果
    groups = [{'name': title, 'url': f'{settings.GLOBAL_URL_PREFIX}/swagger/openapi/?group={title}'}
              for title, _ in _spec.items() if title != 'default']
    groups.sort(key=lambda i: i['name'])
    groups.insert(0, {'name': 'default', 'url': f'{settings.GLOBAL_URL_PREFIX}/swagger/openapi/?group=default'})
    return json(groups)


@blueprint.route('/openapi/')
def spec(request, *args, **kwargs):
    title = utils.get_value(request.raw_args, 'group') or 'default'
    return json(_spec[title])


dir_path = os.path.dirname(os.path.realpath(__file__))
blueprint.static('/', dir_path)
blueprint.static('//', dir_path + '/index.html')
