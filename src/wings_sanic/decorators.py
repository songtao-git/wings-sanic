# -*- coding: utf-8 -*-
from .serializers import BaseSerializer


def route(app_or_blueprint,
          path: str,
          method: str = 'GET',
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

    def decorator(f):
        f.query_serializer = query_serializer
        f.body_serializer = body_serializer
        f.header_serializer = header_serializer
        f.path_serializer = path_serializer
        f.response_serializer = response_serializer
        f.tags = tags
        f.context = context
        app_or_blueprint.add_route(handler=f, uri=path, methods=[method.upper()], host=host,
                                   strict_slashes=strict_slashes, version=version,
                                   name=name, stream=stream)
        return f

    return decorator
