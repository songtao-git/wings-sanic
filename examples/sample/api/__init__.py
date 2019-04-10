from wings_sanic import WingsBluePrint
from .content import content

api = WingsBluePrint.group(content)
