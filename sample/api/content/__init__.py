from .authors import authors
from .blog.views import blog
from wings_sanic import WingsBluePrint

content = WingsBluePrint.group(authors, blog, url_prefix='/content')
