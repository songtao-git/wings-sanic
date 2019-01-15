# -*- coding: utf-8 -*-

import asyncio
import logging
import logging.config
import uuid

import uvloop
from sanic.exceptions import NotFound
from sanic.response import redirect
from sanic_cors import CORS

from wings_sanic import settings, utils, serializers, registry, inspector, context_var, event
from wings_sanic.app import WingsSanic
from wings_sanic.mq_server import BaseMqServer
from wings_sanic.swagger import swagger_blueprint

app = WingsSanic()
registry.set('app', app)


@app.middleware('request')
def init_context(request):
    context_var.set({
        'trace_id': request.headers.get('X-TRACE-ID', '') or str(uuid.uuid4().hex),
        'messages': []
    })
    context_var.get().update(settings.get('DEFAULT_CONTEXT'))


@app.middleware('response')
def reset_context(request, response):
    exception = getattr(response, 'exception', None)
    if not exception:
        event.commit_events()
    context_var.set(None)


@app.middleware('response')
def log_response(request, response):
    logger = logging.getLogger('wings_sanic')
    full_path = request.path + ('?%s' % request.query_string if request.query_string else '')
    request_url = '{0} {1}'.format(request.method, full_path)
    extra = {
        'remote_ip': request.remote_addr,
        'request_uri': request_url,
    }

    exception = getattr(response, 'exception', None)

    if exception:
        message = "request_url: {request_url}" \
                  "\nrequest_body: {body}" \
                  "\nstatus_code: {status_code}" \
                  "\nresponse_content: {response}" \
            .format(request_url=request_url, body=request.body,
                    response=response.body, status_code=response.status)
        if getattr(exception, 'code', 500) / 100 == 5:
            logger.error(message, extra=extra, exc_info=exception, stack_info=True)
        else:
            logger.warning(message, extra=extra, exc_info=exception)
    # 正常请求，记录少量信息
    else:
        message = '%s %s' % (request_url, response.status)
        logger.info(message, extra=extra)


def start():
    """
    before start application, you need load your user_settings 
    by `wings_sanic.settings.load(**user_settings)`
    :return: 
    """
    if not settings.get('DEV'):
        logging.config.dictConfig(settings.get('LOG'))

    if settings.get('CORS'):
        CORS(app, automatic_options=True, supports_credentials=True)

    app.config.update(settings.working_settings)

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    # when DEBUG==True, swagger document is available
    if settings.get('DEBUG'):
        app.blueprint(swagger_blueprint)

        @app.exception(NotFound)
        def handle_404_redirect(request, exception):
            return redirect('/swagger/')

    for bp_str in settings.get('BLUEPRINTS'):
        bp = utils.import_from_str(bp_str)
        app.blueprint(bp)

    @app.exception(Exception)
    def handle_exception(request, exception):
        exception_handler = utils.import_from_str(settings.get('EXCEPTION_HANDLER'))
        response = exception_handler(request, exception)
        # set exception to response convenience for `log_response`
        setattr(response, 'exception', exception)
        return response

    @app.get('/ping/', response_serializer={'ping': serializers.StringField('Ping-Pong', required=True)})
    async def ping(request, *args, **kwargs):
        return {'ping': 'pong'}

    @app.listener('after_server_start')
    async def inspector_start_working(sanic, loop):
        registry.set('event_loop', loop)
        loop.call_soon(inspector.start)

    @app.listener('after_server_start')
    async def start_mq_servers(sanic, loop):
        # init and start mq_server
        for server_name, params in settings.get('MQ_SERVERS').items():
            server_cls = utils.import_from_str(params.pop('server'))
            if not issubclass(server_cls, BaseMqServer):
                raise Exception(
                    f'{utils.cls_str_of_cls(server_cls)} is not subclass of {utils.cls_str_of_cls(BaseMqServer)}')
            server = server_cls(loop=loop, **params)
            registry.set(server_name, server, 'mq_servers')
            loop.create_task(server.start())

        # subscribe handlers
        for server_name, handlers in registry.get_group('event_handlers').items():
            server = registry.get(server_name, 'mq_servers')
            if not server:
                raise Exception(f'cannot find named "{server_name}" mq_server')
            for event_name, handler, max_retry in handlers:
                await server.subscribe(routing_key=event_name, handler=handler, max_retry=max_retry)

    app.run(host="0.0.0.0", port=settings.get('HTTP_PORT'), workers=settings.get('WORKERS'),
            debug=settings.get('DEBUG'), access_log=settings.get('DEV'))
