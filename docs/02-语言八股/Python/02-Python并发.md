# 13 · Python 并发与异步八股

## 一、线程 / 进程 / 协程 对比

| 维度 | 线程 threading | 进程 multiprocessing | 协程 asyncio |
| --- | --- | --- | --- |
| 调度 | 操作系统（内核） | 操作系统 | 事件循环（用户态） |
| 切换开销 | 中 | 大（要换地址空间） | 极小 |
| 共享数据 | 共享内存，需加锁 | 不共享，靠 IPC | 单线程内协作，天然安全 |
| 适用 | IO 密集 | CPU 密集 | IO 密集、高并发连接 |
| 受 GIL 影响 | 是（CPU 密集不加速） | 否（多进程独立解释器） | 否（单线程） |

选型口诀：IO 密集用线程/协程，CPU 密集用多进程，超高并发 IO 用 asyncio。

## 二、GIL（必考中的必考）

### 是什么
- Global Interpreter Lock：CPython 解释器级别的互斥锁，保证同一时刻只有一个线程执行 Python 字节码。

### 为什么存在
- CPython 的内存管理（引用计数）不是线程安全的；加 GIL 让解释器实现简单，避免为每个对象加细粒度锁。
- 历史包袱：早期单核时代的设计，移除 GIL 会大幅降低单线程性能（现在有 free-threaded 实验版本）。

### 影响
- 多线程对 IO 密集任务有效：IO 等待（read/write/sleep）会释放 GIL，其他线程可以跑。
- 多线程对 CPU 密集任务无效甚至更慢：要抢 GIL 加切换开销，1 个核的活在多线程下更慢。
- 不是所有操作都受 GIL 保护：字节码层面原子操作安全（如 list.append），但 `i += 1` 这类"读-改-写"多步操作不安全。

### 怎么绕过
1. CPU 密集：multiprocessing 多进程（每个进程独立 GIL）。
2. 用 C 扩展/numpy（C 代码执行时释放 GIL）。
3. 协程：单线程内协作式，不依赖 GIL。
4. 换解释器：Jython/IronPython（无 GIL），或 CPython 的 free-threaded 构建（3.13+ 实验）。

## 三、threading 多线程

### 基本用法
```python
import threading, time

lock = threading.Lock()          # 非可重入
rlock = threading.RLock()        # 可重入（同线程可多次 acquire）

def worker():
    with lock:                   # 自动 acquire/release
        ...

t = threading.Thread(target=worker)
t.start(); t.join()
```

### 线程安全（必答）
- GIL 保证的原子操作：list.append、list[i] 赋值、dict 单键操作等单条字节码。
- 不安全的复合操作：`counter += 1`、`dict[k] = dict.get(k, 0) + 1`，需要加锁或使用 Queue/原子容器。
- 协作工具：Lock/RLock、Condition（条件变量）、Event（事件通知）、Semaphore（信号量）、Barrier。
- 跨线程传数据用 queue.Queue（线程安全）。

### ThreadPoolExecutor
```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(fn, i) for i in range(100)]
    results = [f.result() for f in futures]
```
- 适合 IO 密集并发：HTTP 请求、数据库调用、文件 IO。

## 四、multiprocessing 多进程

### 为什么能加速 CPU
- 每个进程有独立解释器和内存空间，天然并行利用多核，绕开 GIL。

### 使用
```python
from multiprocessing import Pool

def square(x):
    return x * x

with Pool(processes=4) as pool:
    results = pool.map(square, range(100))
```

### 进程间通信
- Queue / Pipe：进程间传递数据。
- Manager：共享 dict/list/Value/Array（带代理，有开销）。
- 共享内存：multiprocessing.Value/Array 或 shared_memory（3.8+，最快）。
- 注意：进程不共享全局变量，普通变量在子进程是副本；必须用 IPC 或共享内存。

### 启动方式
- fork（Linux 默认，快，继承内存，但多线程 fork 有坑）、spawn（跨平台安全，慢，重新导入模块）、forkserver。
- 用 spawn 时，主模块要加 `if __name__ == "__main__":` 保护，否则无限递归创建进程（Windows/IDE 下常见报错）。

## 五、asyncio 协程（必考）

### 核心概念
- 事件循环 event loop：单线程循环，调度"就绪的协程"。
- async def 定义协程函数；调用返回协程对象，不会立即执行。
- await 挂起等待，让出控制权给事件循环。
- asyncio.run(main()) 是入口（创建循环、执行、关闭）。

```python
import asyncio

async def fetch(i):
    await asyncio.sleep(1)      # 模拟 IO
    return i

async def main():
    results = await asyncio.gather(fetch(1), fetch(2), fetch(3))
    print(results)              # 总耗时约 1s，不是 3s

asyncio.run(main())
```

### 什么时候用
- 大量网络/IO 连接（爬虫、网关、WebSocket、RPC 客户端）：单线程可以扛上万连接。
- 不适合：CPU 密集任务（会阻塞事件循环）——遇到 CPU 任务用 run_in_executor 丢线程池/进程池。

### 常见 API
- asyncio.gather / asyncio.create_task / asyncio.wait
- asyncio.timeout / asyncio.wait_for（超时）
- aiohttp（HTTP 客户端/服务端）、asyncpg / aiomysql（异步数据库）
- 同步库阻塞事件循环 → 用 loop.run_in_executor(None, sync_fn) 包装。

### 协程与生成器
- 协程是升级版生成器：都用 yield/await 让出执行；协程由事件循环驱动，生成器由迭代协议驱动。

## 六、线程池 vs 进程池 vs 协程 怎么选（场景题）

- 爬虫/网关/大量短请求：asyncio 或线程池（asyncio 更省资源）。
- 大量计算/机器学习/数据清洗：multiprocessing Pool。
- 混合：asyncio + run_in_executor(ProcessPoolExecutor) 把计算丢进程池。
- 内存受限、连接数超多：asyncio（线程池线程数有限，一个连接一个线程会爆）。

## 七、常见陷阱

- 多线程访问共享变量不加锁 → 计数丢失。
- 多进程修改全局变量 → 不生效（以为共享其实隔离）。
- asyncio 里调用同步阻塞函数（requests、time.sleep）→ 卡死整个循环，用 await asyncio.sleep 或 run_in_executor。
- 用 os.fork 配合多线程 → 子进程只保留调用线程，容易死锁。
- 死锁：多个锁获取顺序不一致；用 with/RLock 简化。

## 八、常问追问

1. GIL 到底是什么，为什么要移除不了？→ 引用计数线程安全 + 历史设计 + 单线程性能代价。
2. 多线程在 Python 里是不是没用？→ 错，IO 密集有用；CPU 密集没用。
3. 怎么让 Python 用满多核？→ multiprocessing、C 扩展、协程不行（单线程）。
4. `i += 1` 在多线程下安全吗？→ 不安全，读-改-写不是原子。
5. 协程和线程区别？→ 用户态调度 vs 内核调度；切换开销；并发数。
6. asyncio 里能做 CPU 密集计算吗？→ 可以但会阻塞循环，丢给 executor。
7. ProcessPoolExecutor 和 ThreadPoolExecutor 怎么选？→ CPU vs IO。
8. 为什么 spawn 需要 `if __name__ == "__main__"`？→ 子进程要重新导入主模块，防止递归创建进程。
9. queue.Queue 线程安全吗？→ 是，内部有锁；asyncio 用 asyncio.Queue。
10. 怎么排查 GIL 相关性能问题？→ cProfile 看热点、用进程池替换、检查是否大量锁竞争。
