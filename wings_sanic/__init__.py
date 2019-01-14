# coding: utf-8
import asyncio
import contextvars
import logging

from wings_sanic import settings

logger = logging.getLogger('wings_sanic')


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

    def get_group(self, group=None):
        if not group:
            group = '__default'
        return self._data.get(group, {})


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
        report_interval = settings.get('INSPECTOR_REPORT_INTERVAL')
        if self._count % report_interval == 0:
            logger.info('inspector working, count: %s', self._count)
        loop.call_later(self._interval, self.start)

        self._count += 1
        if self._count > 9999999:
            self._count = 1

        for task in self.tasks:
            func = task['func']
            args = task['args']
            if self._count % task['interval'] != 0 or task['times'] == 0:
                continue
            if asyncio.iscoroutinefunction(func):
                loop.create_task(func(*args))
            else:
                loop.call_soon(func, *args)

            if task['times'] > 0:
                task['times'] -= 1

    def register(self, *args, interval=3, times=-1, func=None):
        """ 注册一个任务, 并制定间隔时间执行
        :param args 执行的函数时传入的参数列表
        :param func 执行的函数(可以通过装饰器添加)
        :param interval 间隔时间, 单位秒
        :param  times 重复执行次数, <0时一直重复, =0时不重复
        """
        if func:
            self.tasks.append({
                'func': func,
                'args': args,
                'interval': interval,
                'times': times
            })
        else:
            def decorator(func_wrapped):
                self.tasks.append({
                    'func': func_wrapped,
                    'args': args,
                    'interval': interval,
                    'times': times
                })
                return func
            return decorator


inspector = inspector()

# 当前上下文
context_var = contextvars.ContextVar('context_var', default=None)

from wings_sanic.app import WingsSanic
from wings_sanic.blueprints import WingsBluePrint
from wings_sanic.serializers import *
