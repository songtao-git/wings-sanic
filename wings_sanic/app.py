# -*- coding: utf-8 -*-
from functools import wraps

from sanic import Sanic

from wings_sanic import serializers, settings, views
from wings_sanic.metadata import HandlerMetaData

__all__ = ['WingsSanic']


class WingsSanic(Sanic):
    def wings_route(self,
                    uri: str,
                    method: str = 'GET',
                    host=None,
                    strict_slashes=True,
                    version=None,
                    name=None,
                    success_code=200,
                    header_params: serializers.BaseSerializer = None,
                    path_params: serializers.BaseSerializer = None,
                    query_params: serializers.BaseSerializer = None,
                    body_serializer: serializers.BaseSerializer = None,
                    response_serializer: serializers.BaseSerializer = None,
                    tags: list = None,
                    context: dict = None,
                    swagger_exclude: bool = False):
        """ extension for Sanic's route. Contains parameters for wings framework.

        :param uri: the path for the handler to represent.

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

        :param swagger_exclude: if True, Swagger Document will exclude this api.
        
        :return: decorated function
        """
        method = method.upper()

        context = context or {k: v for k, v in settings.get('DEFAULT_CONTEXT').items()}

        metadata = HandlerMetaData(uri=uri,
                                   method=method,
                                   tags=tags,
                                   success_code=success_code,
                                   header_params=header_params,
                                   path_params=path_params,
                                   query_params=query_params,
                                   body_serializer=body_serializer,
                                   response_serializer=response_serializer,
                                   context=context,
                                   swagger_exclude=swagger_exclude)

        def decorator(raw_handler):
            @wraps(raw_handler)
            async def handler(request, *args, **kwargs):
                if isinstance(metadata.context, dict):
                    from wings_sanic import context_var
                    context_var.get().update(metadata.context)
                kwargs = await views.extract_params(request, metadata)
                result = await raw_handler(request, **kwargs)
                response = await views.process_result(result, metadata)
                return response

            handler.metadata = metadata

            self.add_route(handler=handler, uri=uri, methods=frozenset({method}), host=host,
                           strict_slashes=strict_slashes, version=version,
                           name=name)

            return handler

        return decorator

    # Shorthand method decorators
    def get(self, uri,
            host=None,
            strict_slashes=True,
            version=None,
            name=None,
            success_code=200,
            header_params: serializers.BaseSerializer = None,
            path_params: serializers.BaseSerializer = None,
            query_params: serializers.BaseSerializer = None,
            response_serializer: serializers.BaseSerializer = None,
            tags: list = None,
            context: dict = None,
            swagger_exclude: bool = False):
        return self.wings_route(uri, method='GET', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                response_serializer=response_serializer,
                                context=context,
                                swagger_exclude=swagger_exclude)

    def post(self, uri,
             host=None,
             strict_slashes=True,
             version=None,
             name=None,
             success_code=201,
             header_params: serializers.BaseSerializer = None,
             path_params: serializers.BaseSerializer = None,
             query_params: serializers.BaseSerializer = None,
             body_serializer: serializers.BaseSerializer = None,
             response_serializer: serializers.BaseSerializer = None,
             tags: list = None,
             context: dict = None,
             swagger_exclude: bool = False):
        return self.wings_route(uri, method='POST', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                body_serializer=body_serializer,
                                response_serializer=response_serializer,
                                context=context,
                                swagger_exclude=swagger_exclude)

    def put(self, uri,
            host=None,
            strict_slashes=True,
            version=None,
            name=None,
            success_code=200,
            header_params: serializers.BaseSerializer = None,
            path_params: serializers.BaseSerializer = None,
            query_params: serializers.BaseSerializer = None,
            body_serializer: serializers.BaseSerializer = None,
            response_serializer: serializers.BaseSerializer = None,
            tags: list = None,
            context: dict = None,
            swagger_exclude: bool = False):
        return self.wings_route(uri, method='PUT', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                body_serializer=body_serializer,
                                response_serializer=response_serializer,
                                context=context,
                                swagger_exclude=swagger_exclude)

    def head(self, uri, host=None,
             strict_slashes=True,
             version=None,
             name=None,
             success_code=200,
             header_params: serializers.BaseSerializer = None,
             path_params: serializers.BaseSerializer = None,
             query_params: serializers.BaseSerializer = None,
             response_serializer: serializers.BaseSerializer = None,
             tags: list = None,
             context: dict = None,
             swagger_exclude: bool = False):
        return self.wings_route(uri, method='HEAD', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                response_serializer=response_serializer,
                                context=context,
                                swagger_exclude=swagger_exclude)

    def options(self, uri, host=None,
                strict_slashes=True,
                version=None,
                name=None,
                success_code=200,
                header_params: serializers.BaseSerializer = None,
                path_params: serializers.BaseSerializer = None,
                query_params: serializers.BaseSerializer = None,
                response_serializer: serializers.BaseSerializer = None,
                tags: list = None,
                context: dict = None,
                swagger_exclude: bool = False):
        return self.wings_route(uri, method='OPTIONS', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                response_serializer=response_serializer,
                                context=context,
                                swagger_exclude=swagger_exclude)

    def patch(self, uri, host=None,
              strict_slashes=True,
              version=None,
              name=None,
              success_code=200,
              header_params: serializers.BaseSerializer = None,
              path_params: serializers.BaseSerializer = None,
              query_params: serializers.BaseSerializer = None,
              body_serializer: serializers.BaseSerializer = None,
              response_serializer: serializers.BaseSerializer = None,
              tags: list = None,
              context: dict = None,
              swagger_exclude: bool = False):
        context = context or {k: v for k, v in settings.get('DEFAULT_CONTEXT').items()}
        context['partial'] = True

        return self.wings_route(uri, method='PATCH', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                body_serializer=body_serializer,
                                response_serializer=response_serializer,
                                context=context,
                                swagger_exclude=swagger_exclude)

    def delete(self, uri, host=None,
               strict_slashes=True,
               version=None,
               name=None,
               success_code=204,
               header_params: serializers.BaseSerializer = None,
               path_params: serializers.BaseSerializer = None,
               query_params: serializers.BaseSerializer = None,
               tags: list = None,
               context: dict = None,
               swagger_exclude: bool = False):
        return self.wings_route(uri, method='DELETE', host=host,
                                strict_slashes=strict_slashes, version=version,
                                name=name,
                                tags=tags,
                                success_code=success_code,
                                header_params=header_params,
                                path_params=path_params,
                                query_params=query_params,
                                context=context,
                                swagger_exclude=swagger_exclude)
