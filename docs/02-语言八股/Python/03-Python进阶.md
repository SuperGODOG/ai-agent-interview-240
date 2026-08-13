# 14 · Python 进阶与陷阱八股

## 一、内存管理与垃圾回收（必考）

### 机制
- CPython 用"引用计数为主 + 标记清除 + 分代回收"。
1. 引用计数：每个对象记录被引用次数，归 0 立即回收；缺点：无法处理循环引用。
2. 标记清除：解决循环引用（容器对象），GC 时从根对象出发标记可达，清除不可达。
3. 分代回收：对象分 0/1/2 代，新对象进 0 代，存活晋升；0 代回收最频繁，减少全量扫描开销。
- gc 模块：gc.collect() 手动回收、gc.disable() 关闭（慎用）。

### 循环引用
```python
a = []; b = []; a.append(b); b.append(a)   # 互相引用，引用计数不为 0
```
- 靠标记清除处理；弱引用 weakref 可避免产生强引用环（缓存、观察者模式常用）。

### 内存优化
- 生成器替代列表、__slots__ 减少实例 dict 开销、复用对象、避免大对象长期持有、用 array/struct 存数值。
- 常见内存泄漏：全局缓存无限增长、闭包持有大对象、循环里残留引用、C 扩展未释放。

## 二、__new__ vs __init__（高频）

- `__new__(cls, ...)`：创建并返回实例，发生在 __init__ 之前，第一个参数是类（classmethod 语义）；用于不可变对象和单例。
- `__init__(self, ...)`：初始化已创建实例，返回 None。
```python
class Singleton:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
- 经典单例也可用元类实现（拦截 __call__）。

## 三、元类 metaclass（进阶必考）

### 是什么
- 元类是"创建类的类"：默认 type；`class A: pass` 本质是 `A = type("A", (), {})`。
- 自定义元类：继承 type，重写 __new__/__init__，通过 `class A(metaclass=MyMeta)` 使用。

```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Config(metaclass=SingletonMeta):
    pass
```

### 应用
- 单例、ORM（SQLAlchemy 声明式）、API 校验框架、自动注册（插件系统）。
- 与装饰器区别：元类在类定义时介入整个类，装饰器只包装函数/类。

## 四、上下文管理器（必考）

### 协议
- with 语句调用 __enter__（进入，返回值赋给 as 变量）和 __exit__(exc_type, exc_value, tb)（退出，返回 True 表示吞掉异常）。
```python
class FileManager:
    def __enter__(self): return self
    def __exit__(self, *exc_info):
        self.close()
        return False        # 不吞异常
```
- contextlib 简化：@contextmanager 装饰生成器，yield 前后分别是进入/退出逻辑。
```python
from contextlib import contextmanager

@contextmanager
def timer():
    start = time.time()
    try:
        yield
    finally:
        print(time.time() - start)
```
- 应用：文件、锁（with lock）、数据库事务、资源清理。

## 五、描述符（进阶）

- 实现 `__get__`/`__set__`/`__delete__` 的类，作为另一个类的类属性使用时触发协议。
- property 就是描述符（fget/fset/fdel 包成 Property 对象）。
- 应用：类型校验（类型化字段）、ORM 字段、缓存属性。
```python
class Positive:
    def __set_name__(self, owner, name): self._name = name
    def __get__(self, obj, objtype=None):
        return obj.__dict__[self._name]
    def __set__(self, obj, value):
        if value < 0: raise ValueError("must be positive")
        obj.__dict__[self._name] = value
```

## 六、函数式工具与技巧

- functools.partial：固定部分参数。
- functools.lru_cache：结果缓存（纯函数可用），递归/计算加速神器。
- functools.singledispatch：按参数类型分发（泛型函数）。
- 闭包：内层函数引用外层变量，配合 nonlocal 修改外层变量；延迟绑定陷阱：
```python
funcs = [lambda: i for i in range(3)]   # 三个函数都返回 2（i 是同一个变量）
funcs = [lambda i=i: i for i in range(3)]  # 用默认参数快照
```

## 七、性能优化（场景题）

1. 先 profiling 再优化：cProfile / timeit / py-spy，别拍脑袋。
2. 多用内建函数和 C 实现：sum/max/min/join/sorted、dict/set 查找 O(1)。
3. 局部变量替代全局查找（局部更快）；避免属性链 `obj.a.b.c` 反复访问。
4. 用生成器/惰性计算省内存；大数据用 numpy/pandas（C 底层）。
5. 缓存：lru_cache、Redis、本地缓存。
6. 并发：IO 密集 asyncio/线程，CPU 密集多进程，瓶颈在 C 层用 Cython。
7. 字符串拼接用 "".join(list) 而不是循环 +=。
8. 循环内避免重复计算和重复创建对象；适当用 array/slots。

## 八、Python 常见坑合集（背）

1. 可变默认参数累积（见基础篇）。
2. 闭包延迟绑定（上面）。
3. `[[0]*n]*m` 是共享引用。
4. `dict.get` 不区分"键不存在"和"值为 None"，需要区分用 `if key in d`。
5. 浮点精度：0.1+0.2 != 0.3，用 Decimal。
6. 整数/字符串驻留：别依赖 is。
7. 在迭代 dict/list 时删除元素会出问题，用副本或列表推导重建。
8. `a = b = []` 同一对象。
9. except 不加类型会吞所有异常，尽量精确捕获。
10. 布尔是整数子类：`sum([True, False, True]) == 2`（有时是特性）。
11. 深浅拷贝混用导致部分共享。
12. 异常性能：不要用异常做正常流程控制（try/except 有开销）。

## 九、设计模式在 Python 中的常见实现（串讲）

- 单例：__new__ 或元类（见上）；模块天然单例（模块只导入一次）。
- 工厂：函数返回不同对象即可，动态语言实现更简单。
- 代理：functools.wraps 包装函数、__getattr__ 转发实现动态代理。
- 策略：函数即对象，直接传函数/字典映射，比 Java 更轻量。
- 观察者：事件回调/weakref 列表；适配器：鸭子类型天然适配。

## 十、常问追问

1. Python 为什么会有循环引用泄漏？→ 引用计数无法处理环，靠标记清除。
2. __new__ 和 __init__ 哪个先执行？→ __new__ 先，__init__ 后。
3. 元类能做什么？→ 类创建时拦截/改类；ORM、单例、注册。
4. with 语句异常会怎么处理？→ __exit__ 收到异常信息，返回 True 吞掉，否则抛。
5. property 是什么实现的？→ 描述符。
6. 怎么判断代码瓶颈？→ cProfile/line_profiler 看热点，再针对性优化。
7. __slots__ 有什么用？→ 去掉实例 __dict__，省内存但不能再动态加属性。
8. weakref 有什么用？→ 不强引用目标，缓存/观察者避免循环引用。
9. lru_cache 为什么要求参数可哈希？→ 用 dict 做缓存。
10. 生产环境 Python 服务怎么排查内存上涨？→ tracemalloc、gc 统计、dump 分析、监控 RSS。
