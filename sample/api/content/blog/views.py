from sanic import exceptions

from wings_sanic import serializers
from wings_sanic.blueprints import WingsBluePrint
from . import models
from .serializers import CreateBlogSerializer, SimpleBlogSerializer, DetailBlogSerializer

blog = WingsBluePrint('content_blog', url_prefix='/blog')


@blog.get('/', response_serializer=serializers.ListSerializer(child=SimpleBlogSerializer()))
async def blog_list(request, *args, **kwargs):
    return models.all()


@blog.post('/', body_serializer=CreateBlogSerializer(),
           response_serializer=DetailBlogSerializer())
async def blog_create(request, body, *args, **kwargs):
    instance = models.Blog(**body)
    models.save(instance)
    return instance


@blog.get('/<blog_id>', path_params={'blog_id': serializers.IntField('博客Id')},
          response_serializer=DetailBlogSerializer())
async def blog_detail(request, blog_id, *args, **kwargs):
    return models.get(blog_id)


@blog.delete('/<blog_id>', path_params={'blog_id': serializers.IntField('博客Id')})
async def blog_delete(request, blog_id, *args, **kwargs):
    models.delete(blog_id)


@blog.get('/exception/')
async def raise_exception(request, *args, **kwargs):
    """
    测试一个异常
    """
    raise exceptions.InvalidUsage('抛出的异常信息')
