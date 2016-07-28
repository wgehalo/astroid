# Copyright (c) 2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""Astroid hooks for understanding functools library module."""

import astroid
from astroid.interpreter import util as interpreter_util
from astroid.interpreter import objects
from astroid.interpreter import objectmodel
from astroid import MANAGER


LRU_CACHE = 'functools.lru_cache'


class LruWrappedModel(objectmodel.FunctionModel):
    """Special attribute model for functions decorated with functools.lru_cache.

    The said decorators patches at decoration time some functions onto
    the decorated function.
    """

    @property
    def py__wrapped__(self):
        return self._instance

    @property
    def pycache_info(self):
        cache_info = astroid.extract_node('''
        from functools import _CacheInfo
        _CacheInfo(0, 0, 0, 0)
        ''')
        class CacheInfoBoundMethod(objects.BoundMethod):
            def infer_call_result(self, caller, context=None):
                yield interpreter_util.safe_infer(cache_info)

        return CacheInfoBoundMethod(proxy=self._instance, bound=self._instance)

    @property
    def pycache_clear(self):
        node = astroid.extract_node('''def cache_clear(self): pass''')
        return objects.BoundMethod(proxy=node, bound=self._instance.parent.scope())


class LruWrappedFunctionDef(astroid.FunctionDef):
    special_attributes = LruWrappedModel()


def _transform_lru_cache(node, context=None):
    # TODO: this needs the zipper, because the new node's attributes
    # will still point to the old node.
    # TODO: please check https://github.com/PyCQA/astroid/issues/354 as well.
    new_func = LruWrappedFunctionDef(name=node.name, doc=node.name,
                                     lineno=node.lineno, col_offset=node.col_offset,
                                     parent=node.parent)
    new_func.postinit(node.args, node.body, node.decorators, node.returns)
    return new_func


def _looks_like_lru_cache(node):
    """Check if the given function node is decorated with lru_cache."""
    if not node.decorators:
        return False

    for decorator in node.decorators.nodes:
        if not isinstance(decorator, astroid.Call):
            continue

        func = interpreter_util.safe_infer(decorator.func)
        if func in (None, astroid.Uninferable):
            continue

        if isinstance(func, astroid.FunctionDef) and func.qname() == LRU_CACHE:
            return True
    return False


MANAGER.register_transform(astroid.FunctionDef, _transform_lru_cache,
                           _looks_like_lru_cache)
