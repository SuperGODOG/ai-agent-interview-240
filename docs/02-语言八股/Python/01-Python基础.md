# 12 · Python 基础八股

## 一、语言特性

### 解释型还是编译型
- Python 是"解释型 + 字节码"：源码先编译成 .pyc 字节码（编译步骤），再由 CPython 虚拟机逐条解释执行（解释步骤）。
- 动态语言：变量类型在运行时确定，不需要声明类型。
- 强类型：不同类型之间不会隐式转换（"1" + 1 直接报错，不像 JS 自动转）。

### GIL（必考，详见并发篇）
- CPython 有全局解释器锁，同一时刻只有一个线程执行 Python 字节码；IO 密集友好、CPU 密集受限制。

## 二、可变 vs 不可变对象（必考）

### 分类
- 不可变：int、float、str、tuple、frozenset、bytes、bool
- 可变：list、dict、set、bytearray、自定义对象（默认）

### 关键点
- 不可变对象"修改"实际上是创建新对象，原对象不变（str + 会生成新字符串）。
- tuple 不可变指"引用不可变"：`t = ([1], 2)`，t[0] 指向的 list 可以改。
- 函数默认参数、全局共享、字典 key 的哈希，都和可变性相关。

### is 和 ==
- `==` 比较值（调用 __eq__）；`is` 比较身份（内存地址）。
- 小整数缓存：-5 ~ 256 是单例，`a = 256; b = 256; a is b` 为 True；257 则 False（CPython 实现细节）。
- 字符串驻留：短字符串/标识符可能复用同一对象，但不保证，别依赖 is 比较字符串。

## 三、参数传递（高频）

- Python 传参是"传对象引用"（pass-by-object-reference）：把对象的引用拷贝给形参。
- 形参重新赋值不影响实参；但通过引用修改可变对象的内容会影响实参。
```python
def f(lst):
    lst.append(1)   # 影响外部
    lst = [2]       # 只改局部引用，不影响外部
```
- 可变默认参数陷阱：
```python
def f(x, lst=[]):   # 默认列表是同一个对象，多次调用会累积
    lst.append(x)
    return lst
```
- 正确写法：`def f(x, lst=None): lst = [] if lst is None else lst`。

### *args / **kwargs
- `*args` 收集多余位置参数成 tuple；`**kwargs` 收集关键字参数成 dict。
- 解包：`f(*[1,2])`、`f(**{"a": 1})`。

## 四、深拷贝 vs 浅拷贝（必考）

- 浅拷贝：只复制最外层容器，内部元素还是共享引用（list[:]、copy.copy()、list()、dict.copy()）。
- 深拷贝：递归复制所有层级（copy.deepcopy()），内部元素也独立。
- deepcopy 用 memo 记录已拷贝对象：支持循环引用、避免重复拷贝。
- 嵌套列表坑：
```python
a = [[0]] * 3      # 三个元素是同一个列表！
a[0][0] = 1        # 三处全变
b = [[0] for _ in range(3)]  # 才是三个独立列表
```

## 五、装饰器（必考 + 手撕）

### 本质
- 装饰器是"接收函数、返回函数"的高阶函数，语法糖 `@decorator` 等价于 `func = decorator(func)`。
```python
def log(func):
    @functools.wraps(func)          # 保留原函数 __name__/__doc__
    def wrapper(*args, **kwargs):
        print("before")
        result = func(*args, **kwargs)
        print("after")
        return result
    return wrapper
```

### 为什么用 functools.wraps
- 不包的话 wrapper 的 __name__/__doc__ 会覆盖原函数信息，影响调试和文档。

### 带参数装饰器（三层嵌套）
```python
def repeat(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n): func(*args, **kwargs)
        return wrapper
    return decorator
```

### 类装饰器 / 装饰器带状态
- 用类实现：实现 `__call__`，实例本身可保存状态（计数、缓存）。
- 常见应用：日志、鉴权、缓存（lru_cache）、重试、性能计时。

## 六、迭代器 / 生成器（必考）

### 迭代器协议
- 实现 `__iter__`（返回自身）和 `__next__`（取下一个，StopIteration 结束）；for 循环就是不断调 next。
- 可迭代对象（Iterable）有 __iter__；迭代器（Iterator）自身可迭代且有 __next__。list/dict/set/str/tuple 都是可迭代的，但不是迭代器（iter() 转换后才是）。

### 生成器
- 函数里出现 yield 就是生成器函数，调用返回生成器对象（惰性）。
```python
def gen():
    yield 1
    yield 2
```
- send() 给生成器传值；生成器表达式 `(x*x for x in range(10))` 是惰性的，列表推导 `[x*x for x in range(10)]` 一次性建列表。
- 为什么用生成器：省内存（大文件逐行读、无限序列）、惰性计算、实现协程（旧式）。

## 七、常用语法与内建

- 列表推导式：`[x*2 for x in lst if x > 0]`；字典推导、集合推导。
- lambda：匿名单表达式函数；map/filter/reduce（functools.reduce）。
- zip：并行迭代多个可迭代对象；enumerate：带索引；sorted(key=, reverse=)；all/any。
- collections：defaultdict（缺键给默认值）、Counter（计数）、deque（双向队列）、namedtuple（具名元组）、OrderedDict（dict 3.7+ 已有序）。
- 链式比较：`1 < x < 10` 是 Python 特性。
- bool 是 int 子类：`True == 1`、`True + 1 == 2`。
- 浮点精度：`0.1 + 0.2 != 0.3`，用 decimal.Decimal 或 round 处理。

## 八、Python 2 vs 3（考察频率下降，但偶尔问）

- print 语句 → print() 函数
- 整数除法：2 / 5 从 0 变成 0.4（// 才是整除）
- range() 惰性（替代 xrange）
- 字符串：默认 unicode（不再有 unicode() 函数）
- 字典无序 → 有序（3.7+ 语言规范）
- 异常语法、super() 简化、类型注解（3.5+）

## 九、常问追问

1. 为什么说 str 不可变？→ 修改生成新对象；不可变对象可安全作 dict key、可哈希。
2. 浅拷贝和深拷贝区别，嵌套列表怎么复制？→ copy.copy/deepcopy；[[0]*n for _ in range(m)]。
3. 装饰器为什么需要 functools.wraps？→ 保留原函数元信息。
4. 生成器和迭代器区别？→ 生成器是特殊的迭代器，惰性；迭代器是协议。
5. 可变默认参数有什么坑？→ 默认值在定义时求值，是同一个对象。
6. is 和 == 区别？→ 身份 vs 值；整数缓存范围。
7. Python 里怎么判断两个 list 相等？→ == 逐元素；is 不行。
8. 字典 3.7 后为什么有序？→ 实现改为紧凑数组，插入序保留（语言规范 3.7+）。
9. 为什么 dict 的 key 必须可哈希？→ 哈希表需要 hash() 定位 + 相等比较；list 可变不能做 key。
10. yield 和 return 区别？→ return 结束函数返回值；yield 暂停并产出值，可多次。
