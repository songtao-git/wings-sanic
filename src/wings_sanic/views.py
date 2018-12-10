# -*- coding: utf-8 -*-
from sanic.response import json

from wings_sanic import settings, utils


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
        return {
            "title": "SuccessObject",
            "type": "object",
            "properties": {
                "code": {"type": "number"},
                "data": result_schema,
                "msg": {"type": "string"}
            },
            "required": ["code", "data", "msg"],
        }


def exception_handler(request, exception):
    response_shape = utils.import_from_str(settings.get('RESPONSE_SHAPE'))
    if not issubclass(response_shape, ResponseShape):
        response_shape = ResponseShape
    result = utils.get_value(exception, 'message', str(exception))
    code = utils.get_value(exception, 'status_code', 500)
    result, code = response_shape.create_body(result, code)
    return json(body=result, status=code)
