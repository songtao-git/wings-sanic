# -*- coding: utf-8 -*-

class MqServer:
    async def start(self):
        raise NotImplementedError

    async def publish(self, routing_key, content):
        raise NotImplementedError

    async def subscribe(self, routing_key: str, handler, max_retry=-1):
        raise NotImplementedError
