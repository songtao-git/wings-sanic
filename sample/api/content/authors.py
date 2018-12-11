from wings_sanic import serializers
from wings_sanic.blueprints import WingsBluePrint

authors = WingsBluePrint('content_authors', url_prefix='/authors')


class Author(serializers.Serializer):
    id = serializers.IntField('Id', read_only=True)
    name = serializers.StringField("姓名", required=True)
    phone = serializers.PhoneField('电话', required=True)
    password = serializers.StringField('密码', required=True, write_only=True)


authors_db = {
    1: {'name': 'songtao', 'phone': '17788661047', 'id': 1, 'password': '123456'}
}


def get_author_id():
    author_id = getattr(get_author_id, 'author_id', 1) + 1
    setattr(get_author_id, 'author_id', author_id)
    return author_id


@authors.get('/', response_serializer=serializers.ListSerializer(child=Author()))
async def list_authors(request, *args, **kwargs):
    """
    authors列表
    返回authors列表，不分页
    """
    return authors_db.values()


@authors.post('/', body_serializer=Author(), response_serializer=Author())
async def create_author(request, body, *args, **kwargs):
    """
    新建author
    """
    author_id = get_author_id()
    body['id'] = author_id
    authors_db[author_id] = body
    return body


@authors.get('/<author_id>/',
             path_params={'author_id': serializers.IntField('作者Id')},
             response_serializer=Author())
async def author_detail(request, author_id, *args, **kwargs):
    """
    获取指定id的author详情
    """
    return authors_db.get(author_id, None)
