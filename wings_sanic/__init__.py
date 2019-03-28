# coding: utf-8
import asyncio
import contextvars
import logging
import uuid

from wings_sanic import settings

wings_logger = logging.getLogger('wings_sanic')
logger = logging.getLogger('project')

# 当前上下文
context_var = contextvars.ContextVar('context_var', default=None)


class registry:
    def __init__(self):
        self.__dict__ = {}
        # self._data = {}

    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self.set(key, value)

    def set(self, k, v, group=None):
        if not group:
            group = '__default'
        if group not in self.__dict__:
            self.__dict__[group] = {}
        self.__dict__[group][k] = v

    def get(self, k, group=None):
        if not group:
            group = '__default'
        val = self.__dict__.get(group, {}).get(k, None)
        return val

    def get_group(self, group=None):
        if not group:
            group = '__default'
        return self.__dict__.get(group, {})


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
            wings_logger.info('inspector working, count: %s', self._count)
        loop.call_later(self._interval, self.start)

        self._count += 1
        if self._count > 9999999:
            self._count = 1

        def done_callback(future):
            from wings_sanic import event
            if not future.exception():
                event.commit_events()
            context_var.set(None)

        for task in self.tasks:
            func = task['func']
            args = task['args']
            if self._count % task['interval'] != 0 or task['times'] == 0:
                continue

            context_var.set({
                'trace_id': str(uuid.uuid4().hex),
                'messages': []
            })

            if asyncio.iscoroutinefunction(func):
                fu = asyncio.ensure_future(func(*args), loop=loop)
            else:
                context = contextvars.copy_context()
                fu = loop.run_in_executor(None, context.run, func, *args)
            fu.add_done_callback(done_callback)

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

from wings_sanic.app import WingsSanic
from wings_sanic.blueprints import WingsBluePrint
from wings_sanic.serializers import *
