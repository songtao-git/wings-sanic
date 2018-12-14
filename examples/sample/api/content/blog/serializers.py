import wings_sanic


class CreateBlogSerializer(wings_sanic.Serializer):
    title = wings_sanic.StringField("博客标题", required=True)
    content = wings_sanic.StringField("博客内容")


class SimpleBlogSerializer(wings_sanic.Serializer):
    id = wings_sanic.IntField('博客Id', required=True)
    title = wings_sanic.StringField("博客标题", required=True)


class DetailBlogSerializer(wings_sanic.Serializer):
    id = wings_sanic.IntField('博客Id', required=True)
    title = wings_sanic.StringField("博客标题", required=True)
    content = wings_sanic.StringField("博客内容")
