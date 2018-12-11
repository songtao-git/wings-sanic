from wings_sanic import serializers


class CreateBlogSerializer(serializers.Serializer):
    title = serializers.StringField("博客标题", required=True)
    content = serializers.StringField("博客内容")


class SimpleBlogSerializer(serializers.Serializer):
    id = serializers.IntField('博客Id', required=True)
    title = serializers.StringField("博客标题", required=True)


class DetailBlogSerializer(serializers.Serializer):
    id = serializers.IntField('博客Id', required=True)
    title = serializers.StringField("博客标题", required=True)
    content = serializers.StringField("博客内容")
