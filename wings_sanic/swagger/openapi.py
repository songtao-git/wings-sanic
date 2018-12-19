import inspect
import os
import re
from itertools import repeat

from sanic.blueprints import Blueprint
from sanic.response import json
from sanic.views import CompositionView

from wings_sanic import settings, utils, serializers
from wings_sanic.views import get_response_shape

blueprint = Blueprint('swagger', url_prefix='swagger')

_spec = {}


def __summary_description(doc_string):
    doc_string = (doc_string or "").strip()
    s = doc_string.split('\n', 1)
    if len(s) == 1:
        s.append("")
    return s[0].strip(), s[1].strip()


@blueprint.listener('before_server_start')
def build_spec(app, loop):
    _spec['swagger'] = '2.0'
    _spec.update(settings.get('SWAGGER'))

    # --------------------------------------------------------------- #
    # Paths
    # --------------------------------------------------------------- #
    paths = {}
    # tags =
    for uri, route in app.router.routes_all.items():
        if uri.startswith("/swagger"):
            continue

        # Build list of methods and their handler functions
        handler_type = type(route.handler)
        if handler_type is CompositionView:
            method_handlers = route.handler.handlers.items()
        else:
            method_handlers = zip(route.methods, repeat(route.handler))

        methods = {}
        for _method, _handler in method_handlers:
            metadata = _handler.metadata
            if _method == 'OPTIONS' or metadata.swagger_exclude:
                continue
            parameters = []
            # header
            for name, field in (utils.get_value(metadata.header_serializer, 'fields') or {}).items():
                parameter = field.openapi_spec()
                parameter.update({'in': 'header'})
                parameters.append(parameter)

            # path
            for name, field in (utils.get_value(metadata.path_serializer, 'fields') or {}).items():
                parameter = field.openapi_spec()
                parameter.update({'in': 'path', 'required': True})
                parameters.append(parameter)

            # query
            for name, field in (utils.get_value(metadata.query_serializer, 'fields') or {}).items():
                parameter = field.openapi_spec()
                parameter.update({'in': 'query'})
                parameters.append(parameter)

            # body
            if metadata.body_serializer:
                spec = metadata.body_serializer.openapi_spec()
                parameters.append({
                    'in': 'body',
                    'name': 'body',
                    'required': True,
                    'schema': spec
                })

            # response
            response_spec = None
            if metadata.response_serializer:
                response_spec = metadata.response_serializer.openapi_spec()
            response_shape = get_response_shape(metadata.context)
            response_spec = response_shape.swagger(response_spec)

            summary, description = __summary_description(inspect.cleandoc(_handler.__doc__ or ""))

            endpoint = {
                'operationId': utils.meth_str(_handler),
                'summary': summary,
                'description': description,
                'consumes': ['application/json'],
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

            methods[_method.lower()] = endpoint

        uri_parsed = uri
        for parameter in route.parameters:
            uri_parsed = re.sub('<' + parameter.name + '.*?>', '{' + parameter.name + '}', uri_parsed)

        paths[uri_parsed] = methods

    # --------------------------------------------------------------- #
    # Definitions
    # --------------------------------------------------------------- #

    _spec['definitions'] = {cls.__name__: definition for cls, (obj, definition) in serializers.definitions.items()}

    _spec['paths'] = paths


@blueprint.route('/openapi.json')
def spec(request, *args, **kwargs):
    return json(_spec)


dir_path = os.path.dirname(os.path.realpath(__file__))
blueprint.static('/', dir_path + '/index.html')
blueprint.static('/', dir_path)
