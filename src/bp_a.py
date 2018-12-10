from sanic import Blueprint

from wings_sanic import serializers
from wings_sanic.decorators import route

bp = Blueprint('test', url_prefix='/v1')


@route(bp,
       method='get',
       path="/<age>/",
       path_params={
           'age': serializers.IntField('年龄')
       },
       query_params={
           'id': serializers.StringField('身份证'),
       },
       response_serializer={
           'name': serializers.StringField('姓名'),
           'content1': serializers.StringField('内容')
       })
async def index(request, age, *args, **kwargs):
    """
    API Description: Transmute Get. This will show in the swagger page (localhost:8000/api/v1/).
    """
    return {'content': 'this is index', 'name': '', 'age': age}
