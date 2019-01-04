import wings_sanic
from wings_sanic import application, settings, event, utils

# -----------  user settings -------------
dev_settings = {
    'DEFAULT_CONTEXT': {
        'response_shape': 'wings_sanic.views.ResponseShapeCodeDataMsg'
    },

    'MQ_SERVERS': {
        'default': {
            'server': 'wings_sanic.mq_servers.rabbitmq_server.MqServer',
            'url': 'amqp://test:123456@172.16.6.15:5672',
            'exchange': 'songtao',
            'reconnect_delay': 5.0
        }
    },

    'SWAGGER': {
        'info': {
            "version": '1.0.0',
            "title": 'Authors API'
        },
        'schemes': ['http']
    },
    'HTTP_PORT': 8080,
    'DEBUG': True,
    # 'DEV': True,
    'CORS': True
}
settings.load(**dev_settings)

authors_db = {
    1: {'name': '张三', 'phone': '17788661234', 'id': 1, 'password': '123456'}
}


def get_author_id():
    author_id = getattr(get_author_id, 'author_id', 1) + 1
    setattr(get_author_id, 'author_id', author_id)
    return author_id


class Author(wings_sanic.Serializer):
    id = wings_sanic.IntField('Id', read_only=True)
    name = wings_sanic.StringField("姓名", required=True)
    phone = wings_sanic.PhoneField('电话', required=True)
    password = wings_sanic.StringField('密码', required=True, write_only=True)


authors = wings_sanic.WingsBluePrint('authors', url_prefix='api/authors')


@authors.get('/', response_serializer=Author(many=True))
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
    await event.publish(event.DomainEvent('AuthorCreated', **body))
    return body


@authors.get('/<author_id>/',
             path_params={'author_id': wings_sanic.IntField('作者Id')},
             response_serializer=Author())
async def author_detail(request, author_id, *args, **kwargs):
    """
    获取指定id的author详情
    """
    return authors_db.get(author_id, None)


@event.handler('AuthorCreated')
async def handle_author_created(evt):
    print(utils.to_primitive(evt))


# --------------------- main -----------------
if __name__ == '__main__':
    application.app.blueprint(authors)
    application.start()
