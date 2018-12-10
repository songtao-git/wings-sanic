# -*- coding: utf-8 -*-
from functools import wraps

from sanic.response import BaseHTTPResponse, json

from . import serializers
from .metadata import HandlerMetaData
from .serializers import BaseSerializer
from .views import ResponseShape
from . import settings, utils
import copy

__all__ = ['route']


def route(app_or_blueprint,
          path: str,
          method: str = 'GET',
          success_code=200,
          host=None,
          strict_slashes=None,
          version=None,
          name=None,
          header_params: BaseSerializer = None,
          path_params: BaseSerializer = None,
          query_params: BaseSerializer = None,
          body_serializer: BaseSerializer = None,
          response_serializer: BaseSerializer = None,
          tags: list = None,
          context: dict = None):
    """ extension for Sanic's route. Contains parameters for wings framework.

    :param app_or_blueprint:

    :param path: the path for the handler to represent.

    :param host:

    :param strict_slashes:

    :param version:

    :param name:

    :param method: the method this function should respond to. Default GET.

    :param success_code:

    :param header_params: the arguments that should be passed into the header.

    :param path_params: the arguments that are specified by the path. By default, arguments
           that are found in the path are used first before the query_parameters and body_parameters.

    :param query_params: the arguments that should be query parameters.
           By default, all arguments are query_or path parameters for a GET request.

    :param body_serializer: the arguments that should be body parameters.
           By default, all arguments are either body or path parameters for a non-GET request.
           the whole body is validated against a single object.

    :param response_serializer: response spec

    :param tags: used for swagger tags

    :param context: maybe contains 'response_shape' to custom final response format.
    """
    method = method.upper()

    metadata = HandlerMetaData(path=path,
                               method=method,
                               tags=tags,
                               success_code=success_code,
                               header_params=header_params,
                               path_params=path_params,
                               query_params=query_params,
                               body_serializer=body_serializer,
                               response_serializer=response_serializer,
                               context=context)

    def decorator(raw_handler):

        @wraps(raw_handler)
        async def handler(request, *args, **kwargs):
            kwargs = await extract_params(request, metadata)
            result = await raw_handler(request, **kwargs)
            response = await process_result(result, metadata)
            return response

        handler.metadata = metadata

        app_or_blueprint.add_route(handler=handler, uri=path, methods=[method], host=host,
                                   strict_slashes=strict_slashes, version=version,
                                   name=name)

        return handler

    return decorator


async def extract_params(request, metadata):
    params = {
        'header': None,
        'query': None,
        'path': None,
        'body': None
    }
    # header
    if metadata.header_serializer:
        params['header'] = metadata.header_serializer.validate(request.headers, metadata.context)
        params.update(params['header'])

    # query
    if metadata.query_serializer:
        query_data = {}
        # only field declared in `query_params` is effective.
        for f_n, f in metadata.query_serializer.fields.items():
            if f_n in request.args:
                if isinstance(f, serializers.ListField):
                    query_data[f_n] = set()
                    for i in request.args[f_n]:
                        query_data[f_n].update(i.split(','))  # match `?a=b,c,d&a=d`
                else:
                    query_data[f_n] = request.args[f_n][0]
        params['query'] = metadata.query_serializer.validate(query_data, metadata.context)
        params.update(params['query'])

    # path
    if metadata.path_serializer:
        params['path'] = metadata.path_serializer.validate(request.match_info, metadata.context)
        params.update(params['path'])

    # body
    if metadata.body_serializer:
        params['body'] = metadata.body_serializer.validate(request.json, metadata.context)

    return params


async def process_result(result, metadata):
    """
    process a result:

    transmute_func: the transmute_func function that returned the response.

    context: the transmute_context to use.

    result: the return value of the function, which will be serialized and
            returned back in the API.
    """

    if isinstance(result, BaseHTTPResponse):
        return result

    if metadata.response_serializer:
        result = metadata.response_serializer.to_primitive(result, metadata.context)
    else:
        result = utils.to_primitive(result)

    response_shape = utils.get_value(metadata.context, 'response_shape')
    if not response_shape:
        response_shape = utils.import_from_str(settings.get('RESPONSE_SHAPE'))
    if not issubclass(response_shape, ResponseShape):
        response_shape = ResponseShape

    result, code = response_shape.create_body(result, metadata.success_code)

    return json(body=result, status=code)
