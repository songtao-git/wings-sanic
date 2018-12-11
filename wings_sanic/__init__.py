# coding: utf-8
import asyncio
import logging

logger = logging.getLogger('wings_sanic')

__all__ = ['registry', 'inspector', 'DEFAULT_CONTEXT']

DEFAULT_CONTEXT = {}


class registry:
    def __init__(self):
        self._data = {}

    def set(self, k, v, group=None):
        if not group:
            group = '__default'
        if group not in self._data:
            self._data[group] = {}
        self._data[group][k] = v

    def get(self, k, group=None):
        if not group:
            group = '__default'
        val = self._data.get(group, {}).get(k, None)
        return val


registry = registry()


class inspector:
    """ 巡查员，定期巡查任务并执行
    """

    def __init__(self):
        self._count = 0  # 次数
        self._interval = 1  # 间隔(秒)
        self.tasks = []

    def start(self):
        """ 启动
        """
        loop = registry.get('event_loop') or asyncio.get_event_loop()
        if self._count % 30 == 0:
            logger.info('inspector working, count: %s', self._count)
        loop.call_later(self._interval, self.start)

        for task in self.tasks:
            func = task['func']
            args = task['args']
            interval = task['interval']
            if self._count % interval != 0:
                continue
            if asyncio.iscoroutinefunction(func):
                loop.create_task(func(*args))
            else:
                loop.call_soon(func, *args)

        self._count += 1
        if self._count > 9999999:
            self._count = 1

    def register(self, func, *args, interval=1):
        """ 注册一个任务, 并制定间隔时间执行
        @param func 执行的函数
        @param interval 间隔时间, 单位秒
        """
        t = {
            'func': func,
            'args': args,
            'interval': interval
        }
        self.tasks.append(t)


inspector = inspector()
