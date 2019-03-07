# -*- coding: utf-8 -*-
import asyncio
import contextvars
import logging
import uuid

import aioamqp
import aioamqp.properties
import aioamqp.protocol

from wings_sanic import utils, context_var, event, settings
from wings_sanic.mq_server import BaseMqServer

logger = logging.getLogger(__name__)


class Consumer:
    def __init__(self, mq_server, queue, routing_key, handler, msg_type, timeout=10, max_retry=-1, subscribe=False):
        self.mq_server = mq_server
        self._queue = queue
        self.queue = queue
        self.routing_key = routing_key
        self.handler = handler
        self.msg_type = msg_type
        self.timeout = timeout
        self.channel = None
        self.max_retry = max_retry
        self.subscribe = subscribe

    def get_ttl(self, retry_count):
        """
        :param retry_count: 重试次数
        :return: 毫秒
        """
        if retry_count <= 0:
            return 0
        if retry_count > 7:
            return 3 * 60 * 1000
        return (1 << retry_count) * 1000

    async def __publish_to_retry_queue(self, body, retried_count):
        channel = await self.mq_server.connection.channel()
        properties = {'expiration': str(self.get_ttl(retried_count + 1)),
                      'headers': {'x-retry-count': retried_count + 1}}
        await channel.basic_publish(body, self.mq_server.retry_exchange, self.queue, properties=properties)
        await channel.close()

    async def __on_message(self, channel, body, envelope, properties):
        self.mq_server.loop.create_task(self.__handle_message(channel, body, envelope, properties))

    async def __handle_message(self, channel, body, envelope, properties):
        encoding = properties.content_encoding or 'utf-8'
        content = body.decode(encoding)
        logger.debug('receive message from mq: %s', content)

        data = utils.instance_from_json(content)
        headers = utils.get_value(data, 'headers', {})
        ctx = {'trace_id': utils.get_value(headers, 'X-TRACE-ID', '')}
        # 用户定制传递的消息头
        for k in settings.get('CONTEXT_WHEN_DELIVERY'):
            h_k = 'X-' + k.upper().replace('_', '-')
            ctx[k] = utils.get_value(headers, h_k)

        context_var.set(ctx)

        message = utils.get_value(data, 'payload', data)
        message = utils.instance_from_json(message, cls=self.msg_type)

        retried_count = (properties.headers or {}).get('x-retry-count', 0)
        retried_count = retried_count if retried_count >= 0 else 0

        try:
            if asyncio.iscoroutinefunction(self.handler):
                fu = asyncio.ensure_future(self.handler(message), loop=self.mq_server.loop)
            else:
                context = contextvars.copy_context()
                fu = self.mq_server.loop.run_in_executor(None, context.run, self.handler, message)
            await asyncio.wait_for(fu, self.timeout, loop=self.mq_server.loop)
            event.commit_events()
            logger.info(
                f'handle message success. event_name:{self.routing_key}, handler:{utils.meth_str(self.handler)}, '
                f'retried_count: {retried_count}')
        except Exception as ex:
            if self.max_retry < 0 or retried_count < self.max_retry:
                await self.__publish_to_retry_queue(body, retried_count)

            error_info = f"event_name: {self.routing_key}, handler: {utils.meth_str(self.handler)}, " \
                         f"retried_count: {retried_count}, messages: \n{content}"
            logger.error(error_info, exc_info=ex)

        finally:
            await channel.basic_client_ack(envelope.delivery_tag)
            context_var.set(None)

    async def start(self):
        self.channel = await self.mq_server.connection.channel()
        self.queue = f'{self._queue}_{str(uuid.uuid4().hex)}' if self.subscribe else self._queue
        if self.subscribe:
            await self.channel.queue_declare(self.queue, exclusive=True)
        else:
            await self.channel.queue_declare(self.queue, durable=True)
        await self.channel.queue_bind(self.queue, self.mq_server.work_exchange, routing_key=self.routing_key)
        await self.channel.basic_consume(self.__on_message, self.queue)


class MqServer(BaseMqServer):
    def __init__(self, url, exchange, exchange_type='topic', reconnect_delay=5.0, loop=None, **kwargs):
        self.url = url
        self.work_exchange = exchange
        self.work_exchange_type = exchange_type
        self.retry_exchange = '%s_retry_exchange' % exchange
        self.retry_queue = '%s_retry_queue' % exchange
        self.reconnect_delay = reconnect_delay
        self.loop = loop or asyncio.get_event_loop()
        self.consumers = set()
        self.connection = None
        self.state = 'INIT'  # INIT -> CONNECTING -> CONNECTED -> RUNNING | CLOSED
        self.publishing_messages = asyncio.Queue(loop=loop)  # 后续可以使用数据库或者缓存来存储
        self.channel = None

    async def start(self):
        if self.state != 'INIT':
            raise Exception('mq_server(%s|%s) already started' % (self.url, self.work_exchange))
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.__connect_to_broker())
        self.loop.create_task(self.__publish_loop())

    async def dispose(self):
        self.state = 'CLOSED'
        old_connection, self.connection = self.connection, None
        self.channel = None
        try:
            await old_connection.close()
        except:
            pass

    async def __on_error(self, exc):
        await self.dispose()
        logger.error('Connection exception, reconnecting in %s seconds' % self.reconnect_delay, exc_info=exc)
        self.loop.call_later(self.reconnect_delay, lambda: self.loop.create_task(self.__connect_to_broker()))

    async def __connect_to_broker(self):
        try:
            if self.state not in ['INIT', 'CLOSED']:
                return
            self.state = 'CONNECTING'
            _, self.connection = await aioamqp.from_url(self.url, on_error=self.__on_error, loop=self.loop)
            self.channel = await self.connection.channel()
            self.state = 'CONNECTED'
            await self.__create_exchange()
            self.__start_consumers()

        except Exception as exc:
            await self.dispose()
            logger.error('Connecting failed, reconnecting in %s seconds' % self.reconnect_delay, exc_info=exc)
            self.loop.call_later(self.reconnect_delay, lambda: self.loop.create_task(self.__connect_to_broker()))

    async def __create_exchange(self):
        await self.channel.exchange_declare(self.work_exchange, self.work_exchange_type, durable=True)
        await self.channel.exchange_declare(self.retry_exchange, 'topic', durable=True)
        await self.channel.queue_declare(self.retry_queue, durable=True,
                                         arguments={"x-dead-letter-exchange": ''})
        await self.channel.queue_bind(self.retry_queue, self.retry_exchange, '#')

    def __start_consumers(self):
        for c in list(self.consumers):
            self.loop.create_task(c.start())
        self.state = 'RUNNING'

    async def __publish_loop(self):
        while True:
            if self.state not in ['CONNECTED', 'RUNNING']:
                await asyncio.sleep(1, loop=self.loop)
                continue
            routing_key, content = await self.publishing_messages.get()
            try:
                await asyncio.wait_for(
                    self.channel.basic_publish(content.encode('utf-8'), self.work_exchange, routing_key),
                    timeout=3, loop=self.loop)
                logger.debug('success publish message to (exchange: %s, routing_key: %s), and content is: %s',
                             self.work_exchange, routing_key, content)
            except Exception as ex:
                self.loop.create_task(self.publishing_messages.put((routing_key, content)))
                logger.error('fail publish message to (exchange: %s, routing_key: %s), and content is: %s',
                             self.work_exchange, routing_key, content, exc_info=ex)

    async def publish(self, routing_key, content):
        await self.publishing_messages.put((routing_key, content))

    async def subscribe(self, routing_key: str, handler, msg_type, timeout=10, max_retry=-1, subscribe=False):
        handler_path = utils.meth_str(handler)
        consumer = Consumer(mq_server=self,
                            queue=handler_path,
                            routing_key=routing_key,
                            handler=handler,
                            timeout=timeout,
                            msg_type=msg_type,
                            max_retry=max_retry,
                            subscribe=subscribe)

        self.consumers.add(consumer)
        if self.state == 'RUNNING':
            self.loop.create_task(consumer.start())
        logger.debug('add consumer(queue: %s, routing_key: %s) to %s:%s',
                     handler_path, routing_key, self.url, self.work_exchange)
