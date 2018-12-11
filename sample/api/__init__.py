from wings_sanic.blueprints import WingsBluePrint
from .content import content

api = WingsBluePrint.group(content, url_prefix='/api')
