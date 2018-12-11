from sanic import exceptions

import wings_sanic
from . import models
from . import serializers

blog = wings_sanic.WingsBluePrint('content_blog', url_prefix='/blog')


@blog.get('/', response_serializer=serializers.SimpleBlogSerializer(many=True))
async def blog_list(request, *args, **kwargs):
    return models.all()


@blog.post('/', body_serializer=serializers.CreateBlogSerializer(),
           response_serializer=serializers.DetailBlogSerializer())
async def blog_create(request, body, *args, **kwargs):
    instance = models.Blog(**body)
    models.save(instance)
    return instance


@blog.get('/<blog_id>', path_params={'blog_id': wings_sanic.IntField('博客Id')},
          response_serializer=serializers.DetailBlogSerializer())
async def blog_detail(request, blog_id, *args, **kwargs):
    return models.get(blog_id)


@blog.delete('/<blog_id>', path_params={'blog_id': wings_sanic.IntField('博客Id')})
async def blog_delete(request, blog_id, *args, **kwargs):
    models.delete(blog_id)


@blog.get('/exception/')
async def raise_exception(request, *args, **kwargs):
    """
    测试一个异常
    """
    raise exceptions.InvalidUsage('抛出的异常信息')
