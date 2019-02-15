# -*- coding: utf-8 -*-


class BaseMqServer:
    async def start(self):
        raise NotImplementedError

    async def publish(self, routing_key: str, content: str):
        raise NotImplementedError

    async def subscribe(self, routing_key: str, handler, msg_type, timeout=10, max_retry=-1, subscribe=False):
        raise NotImplementedError
