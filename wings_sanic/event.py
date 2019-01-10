# -*- coding: utf-8 -*-
import asyncio
import contextvars
import json
import logging
import uuid
from functools import wraps

from . import datetime_helper, registry, context_var, settings, utils

logger = logging.getLogger(__name__)


class DomainEvent:
    def __init__(self, event_name, **kwargs):
        if 'version' in kwargs:
            kwargs['version'] = kwargs['version'] + 1
        self.occur_on = datetime_helper.get_utc_time()
        self.event_name = event_name
        self.__dict__.update(kwargs)


def __get_mq_server(server_name):
    server = registry.get(server_name, 'mq_servers')
    if not server:
        raise Exception('cannot find named "{0}" mq_server'.format(server_name))
    return server


async def publish(event: DomainEvent, mq_server='default', send_after_done=True):
    """
    发送事件
    """
    await publish_message(event.event_name, event, mq_server, send_after_done)


async def publish_message(routing_key: str, message, mq_server='default', send_after_done=True):
    """
    发送消息
    """
    ctx_delivery = {}
    for k, v in context_var.get().items():
        if k not in settings.get('IGNORE_CONTEXT_WHEN_DELIVERY'):
            ctx_delivery[k] = v
    body = {
        'message': utils.to_primitive(message),
        'context': ctx_delivery
    }
    body = json.dumps(body)
    server = __get_mq_server(mq_server)
    if send_after_done:
        context_var.get()['messages'].append({'mq_server': server, 'body': body, 'routing_key': routing_key})
    else:
        await server.publish(routing_key, body)


def handler(event_name, mq_server='default', msg_type=DomainEvent, timeout=None, max_retry=None):
    """
    添加事件处理器的装饰器
    :param event_name: 事件名
    :param mq_server: mq_server名字
    :param msg_type: 将接受到的内容转化成该msg_type对应的类型，如果为None或者转化不成功则返回原字符串
    :param timeout: 处理的超时时长，默认值10秒，优先级 默认值 < settings设置 < 装饰器设置
    :param max_retry: 最大重试次数，默认值-1(无限重试)，优先级 默认值 < settings设置 < 装饰器设置
    :return: 
    """
    timeout = timeout if timeout is not None else settings.get('EVENT_HANDLE_TIMEOUT')
    timeout = timeout if timeout is not None else 10
    max_retry = max_retry if max_retry is not None else settings.get('EVENT_MAX_RETRY')
    max_retry = max_retry if max_retry is not None else -1

    def decorator(func):
        @wraps(func)
        async def wrapper(content, retried_count):
            server = __get_mq_server(mq_server)
            data = utils.instance_from_json(content)
            ctx = utils.get_value(data, 'context', {})
            ctx['trace_id'] = utils.get_value(ctx, 'trace_id', str(uuid.uuid4().hex))
            ctx['messages'] = []
            context_var.set(ctx)

            message = utils.get_value(data, 'message', data)
            message = utils.instance_from_json(message, cls=msg_type)
            try:
                if asyncio.iscoroutinefunction(func):
                    fu = asyncio.ensure_future(func(message), loop=server.loop)
                else:
                    context = contextvars.copy_context()
                    fu = server.loop.run_in_executor(None, context.run, func, message)
                await asyncio.wait_for(fu, timeout, loop=server.loop)
                commit_events()
                logger.info(
                    f'handle message success. event_name:{event_name}, handler:{utils.meth_str(func)}, '
                    f'retried_count: {retried_count}')
            except Exception as ex:
                error_info = f"event_name: {event_name}, handler: {utils.meth_str(func)}, " \
                             f"retried_count: {retried_count}, messages: \n{message}"
                logger.error(error_info, exc_info=ex)
                raise ex
            finally:
                context_var.set(None)

        # 将handler注册到registry，app启动后初始化订阅
        handlers_cur = registry.get(mq_server, 'event_handlers') or set()
        handlers_cur.add((event_name, wrapper, max_retry))
        registry.set(mq_server, handlers_cur, 'event_handlers')

        return func

    return decorator


def commit_events():
    try:
        messages = utils.get_value(context_var.get(), 'messages', [])
        for i in messages:
            server = i['mq_server']
            asyncio.run_coroutine_threadsafe(server.publish(i['routing_key'], i['body']), server.loop)
    except Exception as ex:
        logger.error('send event error', exc_info=ex)
