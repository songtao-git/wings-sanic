from sanic import Sanic, Blueprint
from sanic.response import json

from wings_sanic import serializers
from wings_sanic.decorators import route
from wings_sanic.response_shape import ResponseShapeCodeDataMsg
from wings_sanic import config

app = Sanic()

bp = Blueprint('test', url_prefix='/v1')


@route(bp,
       method='get',
       path="/<age>/",
       path_params={
           'age': serializers.IntField('年龄')
       },
       query_params={
           'id': serializers.StringField('身份证'),
       })
async def index(request, age, *args, **kwargs):
    """
    API Description: Transmute Get. This will show in the swagger page (localhost:8000/api/v1/).
    """
    return {'content': 'this is index', 'name': '', 'age': age}
    # return json({'content': 'this is index', 'name': age})

app.blueprint(bp)

if __name__ == "__main__":
    config.DEFAULT_CONTEXT['response_shape'] = ResponseShapeCodeDataMsg
    app.run(host='0.0.0.0', port=8080)
