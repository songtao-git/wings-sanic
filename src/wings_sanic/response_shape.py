# -*- coding: utf-8 -*-


class ResponseShape:
    """
    result shapes define the return format of the
    response.
    """

    @staticmethod
    def create_body(result, success_code, exc):
        """
        :param result: success result
        :param success_code: success code
        :param exc: exception
        :return: a tuple (final result, code)
        """
        if exc:
            return getattr(exc, 'message', str(exc)), getattr(exc, 'status_code', 500)
        return result, success_code

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
    def create_body(result, success_code, exc):
        code = 200
        if exc:
            result = {
                'code': getattr(exc, 'status_code', 500),
                'data': result,
                'msg': getattr(exc, 'message', str(exc))
            }
            return result, code
        else:
            result = {
                'code': success_code,
                'data': result,
                'msg': 'success'
            }
        return result, code

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
