# -*- coding: utf-8 -*-
from functools import wraps

from sanic.response import HTTPResponse

from .serializers import BaseSerializer


def route(app_or_blueprint,
          path: str,
          method: str = 'GET',
          success_code=200,
          host=None,
          strict_slashes=None,
          stream=False,
          version=None,
          name=None,
          query_serializer: BaseSerializer = None,
          body_serializer: BaseSerializer = None,
          header_serializer: BaseSerializer = None,
          path_serializer: BaseSerializer = None,
          response_serializer: BaseSerializer = None,
          tags: list = None,
          context: dict = None):
    """ extension for Sanic's route. Contains parameters for wings framework.

    :param app_or_blueprint:

    :param path: the path for the handler to represent.

    :param host:

    :param strict_slashes:

    :param stream:

    :param version:

    :param name:

    :param method: the method this function should respond to. Default GET.

    :param success_code:

    :param query_serializer: the arguments that should be query parameters.
           By default, all arguments are query_or path parameters for a GET request.

    :param body_serializer: the arguments that should be body parameters.
           By default, all arguments are either body or path parameters for a non-GET request.
           the whole body is validated against a single object.

    :param header_serializer: the arguments that should be passed into the header.

    :param path_serializer: the arguments that are specified by the path. By default, arguments
           that are found in the path are used first before the query_parameters and body_parameters.

    :param response_serializer: response spec

    :param tags: used for swagger tags

    :param context: maybe contains 'response_shape' to custom final response format.
    """
    method = method.upper()

    metadata = HandlerMetaData(path=path,
                               method=method,
                               tags=tags,
                               success_code=success_code,
                               query_serializer=query_serializer,
                               body_serializer=body_serializer,
                               header_serializer=header_serializer,
                               path_serializer=path_serializer,
                               response_serializer=response_serializer,
                               context=context)

    def decorator(raw_handler):

        @wraps(raw_handler)
        async def handler(request, *args, **kwargs):
            exc, result = None, None
            try:
                kwargs = await extract_params(request, metadata)
                result = await raw_handler(request, **kwargs)
            except Exception as e:
                exc = e
            content_type = request.headers.get("Content-Type", "application/json")
            response = process_result(
                metadata, result, exc, content_type
            )
            return response

        handler.meta_data = metadata

        app_or_blueprint.add_route(handler=handler, uri=path, methods=[method], host=host,
                                   strict_slashes=strict_slashes, version=version,
                                   name=name, stream=stream)

        return handler

    return decorator


class HandlerMetaData:
    def __init__(
            self,
            path,
            method,
            tags=None,
            query_serializer=None,
            body_serializer=None,
            header_serializer=None,
            path_serializer=None,
            response_serializer=None,
            success_code=200,
            context=None,
    ):
        self.path = path
        self.method = method
        self.tags = set(tags or [])
        self.success_code = success_code
        self.query_serializer = query_serializer
        self.body_serializer = body_serializer
        self.header_serializer = header_serializer
        self.path_serializer = path_serializer
        self.response_serializer = response_serializer
        self.context = context


async def extract_params(request, metadata):
    body_params = metadata.body_serializer.validate(request.json) if metadata.body_serializer else request.json
    query_params = metadata.query_serializer.validate(request.json) if metadata.query_serializer else request.json
    header_params = metadata.header_serializer.validate(request.json) if metadata.header_serializer else request.json
    path_params = metadata.path_serializer.validate(request.json) if metadata.path_serializer else request.json

    return {
        'body': body_params,
        'query': query_params,
        'header': header_params,
        'path': path_params
    }


def process_result(metadata, result, exc, content_type):
    """
    process a result:

    transmute_func: the transmute_func function that returned the response.

    context: the transmute_context to use.

    result: the return value of the function, which will be serialized and
            returned back in the API.

    exc: the exception object. For Python 2, the traceback should
         be attached via the __traceback__ attribute. This is done automatically
         in Python 3.

    content_type: the content type that request is requesting for a return type.
                  (e.g. application/json)
    """
    # if isinstance(result, Response):
    #     response = result
    # else:
    #     response = Response(
    #         result=result, code=transmute_func.success_code, success=True
    #     )
    # if exc:
    #     if isinstance(exc, APIException):
    #         response.result = "invalid api use: {0}".format(str(exc))
    #         response.success = False
    #         response.code = exc.code
    #     else:
    #         reraise(type(exc), exc, getattr(exc, "__traceback__", None))
    # else:
    #     return_type = transmute_func.get_response_by_code(response.code)
    #     if return_type:
    #         response.result = context.serializers.dump(return_type, response.result)
    # try:
    #     content_type = str(content_type)
    #     serializer = context.contenttype_serializers[content_type]
    # except NoSerializerFound:
    #     serializer = context.contenttype_serializers.default
    #     content_type = serializer.main_type
    # # if response.success:
    # #     result = context.response_shape.create_body(attr.asdict(response))
    # #     response.result = result
    # else:
    #     response.result = attr.asdict(response)
    # body = serializer.dump(response.result)
    # # keeping the return type a dict to
    # # reduce performance overhead.
    # return {
    #     "body": body,
    #     "code": response.code,
    #     "content-type": content_type,
    #     "headers": response.headers,
    # }
    if exc:
        raise exc
    return result
