from wings_sanic import serializers
from wings_sanic.blueprints import WingsBluePrint

bp = WingsBluePrint('test', url_prefix='/v1')


@bp.get("/<age>/",
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
    接口名
    """
    return {'content': 'this is index', 'name': '', 'age': age}


class Rep(serializers.Serializer):
    id = serializers.IDField('身份证', required=True)


@bp.post("/<age>/",
         path_params={
             'age': serializers.IntField('年龄')
         },
         query_params={
             'id': serializers.StringField('身份证'),
         },
         response_serializer={
             'name': serializers.StringField('姓名'),
             'content1': serializers.StringField('内容')
         },
         body_serializer=Rep())
async def index_create(request, age, *args, **kwargs):
    """
    API Description: Transmute Get. This will show in the swagger page (localhost:8000/api/v1/).
    """
    return {'content': 'this is index', 'name': '', 'age': age}
