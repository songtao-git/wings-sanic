# -*- coding: utf-8 -*-
import asyncio
import json
import logging

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
    ctx = context_var.get() or {}
    # 默认必传递的信息
    ctx_delivery = {
        'X-TRACE-ID': ctx.get('trace_id', ''),
        'X-EVENT-NAME': routing_key,
        'X-OCCUR-ON': datetime_helper.now()
    }
    # 用户定制传递的消息头
    for key in settings.get('CONTEXT_WHEN_DELIVERY'):
        ctx_delivery['X-' + key.upper().replace('_', '-')] = utils.get_value(ctx, key)

    body = {
        'payload': message,
        'headers': ctx_delivery
    }
    body = json.dumps(utils.to_primitive(body))
    server = __get_mq_server(mq_server)

    # 立即发送
    # 1. context_var未设置，无法收集message
    # 2. 调用设置send_after_done=False
    if not ctx or not send_after_done:
        await server.publish(routing_key, body)
    else:
        messages = ctx.get('messages', [])
        messages.append({'mq_server': server, 'body': body, 'routing_key': routing_key})
        ctx['messages'] = messages


def handler(event_name, mq_server='default', msg_type=DomainEvent, timeout=None, max_retry=None, subscribe=False):
    """
    添加事件处理器的装饰器
    :param event_name: 事件名
    :param mq_server: mq_server名字
    :param msg_type: 将接受到的内容转化成该msg_type对应的类型，如果为None或者转化不成功则返回原字符串
    :param timeout: 处理的超时时长，默认值10秒，优先级 默认值 < settings设置 < 装饰器设置
    :param max_retry: 最大重试次数，默认值-1(无限重试)，优先级 默认值 < settings设置 < 装饰器设置
    :param subscribe: True是pub-sub模式, 否则producer-consumer模式
    :return: 
    """
    timeout = timeout if timeout is not None else settings.get('EVENT_HANDLE_TIMEOUT')
    timeout = timeout if timeout is not None else 10
    max_retry = max_retry if max_retry is not None else settings.get('EVENT_MAX_RETRY')
    max_retry = max_retry if max_retry is not None else -1

    def decorator(func):
        # 将handler注册到registry，app启动后初始化订阅
        handlers_cur = registry.get(mq_server, 'event_handlers') or set()
        handlers_cur.add((event_name, func, msg_type, timeout, max_retry, subscribe))
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
