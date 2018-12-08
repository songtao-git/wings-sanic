from sanic import Sanic, Blueprint
from sanic.response import json
from wings_sanic.decorators import route


app = Sanic()

@route(app, "/api/v1/user/", "POST")
async def test_transmute(request):
    """
    API Description: Transmute Get. This will show in the swagger page (localhost:8000/api/v1/).
    """
    return {
        "user": 'sss',
    }


@route(app, "/", method='get')
# @app.route('/index/', methods=['GET'])
async def index(request, *args, **kwargs):
    """
    API Description: Transmute Get. This will show in the swagger page (localhost:8000/api/v1/).
    """
    return json({'content': 'this is index'})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
