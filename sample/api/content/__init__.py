from .authors import authors
from .blog import blog
from wings_sanic.blueprints import WingsBluePrint

content = WingsBluePrint.group(authors, blog, url_prefix='/content')
