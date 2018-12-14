# -*- coding: utf-8 -*-
from sanic.response import json, BaseHTTPResponse

from wings_sanic import utils, serializers, settings


class ResponseShape:
    """
    result shapes define the return format of the
    response.
    """

    @staticmethod
    def create_body(result, status_code):
        """
        :param result: success result
        :param status_code: 
        :return: a tuple (final result, status_code)
        """
        return result, status_code

    @staticmethod
    def swagger(result_schema):
        """
        given the schema of the inner
        result object, return back the
        swagger schema representation.
        """
        return result_schema


class ResponseShapeCodeDataMsg(ResponseShape):
    """
    return back an object with the result nested,
    providing a little more context on the result:

    {
        "code": int,
        "data": result,
        "msg": str
    }
    """

    @staticmethod
    def create_body(result, status_code):
        code = 0 if int(status_code / 100) == 2 else status_code
        status_code = 200
        result = {
            'code': code,
            'data': result,
            'msg': '操作成功' if code == 0 else result
        }
        return result, status_code

    @staticmethod
    def swagger(result_schema):
        if result_schema is None:
            result_schema = {'type': 'object', 'description': '空值', 'nullable': True}
        return {
            "title": "SuccessObject",
            "type": "object",
            "properties": {
                "code": {"type": "number", "description": "返回码:0或2xx成功，其他失败"},
                "data": result_schema,
                "msg": {"type": "string", "description": "友好可读消息, 失败时返回错误信息"}
            },
            "required": ["code", "data", "msg"],
        }


def get_response_shape(context=None):
    response_shape = utils.get_value(context, 'response_shape')
    if isinstance(response_shape, str):
        response_shape = utils.import_from_str(response_shape)
    if not response_shape or not issubclass(response_shape, ResponseShape):
        response_shape = ResponseShape
    return response_shape


def exception_handler(request, exception):
    context = {k: v for k, v in settings.get('DEFAULT_CONTEXT').items()}
    response_shape = get_response_shape(context)

    result = utils.get_value(exception, 'message', str(exception))
    code = utils.get_value(exception, 'status_code', 500)
    result, code = response_shape.create_body(result, code)
    return json(body=result, status=code)


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

    response_shape = get_response_shape(metadata.context)

    result, code = response_shape.create_body(result, metadata.success_code)

    return json(body=result, status=code)
