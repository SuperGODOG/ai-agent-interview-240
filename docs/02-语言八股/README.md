# 语言八股文：Java / Python / Go 面试复习手册

> 面向后端与 AI Agent 岗的语言级面试八股：**Java 11 篇 + Python 3 篇 + Go 5 篇**，按"考点 + 要点 + 代码示例 + 常问追问"组织，适合面试前手撕复习（先合上答案自问自答，再对照）。

---

## 为什么要有语言八股

AI Agent 岗的面试不只是 Agent 架构题——语言基础（Java 并发、JVM、Go GMP、Python GIL）是每轮面试的前置关卡。本目录与 [01-面试八股文](../01-面试八股文/01-Agent应用开发.md)（Agent 真题 240 道）互补：**Agent 题决定你能不能进，语言题决定你能走多远**。

---

## Java（11 篇 + 学习路线图）

> 国内后端面试主战场：集合 / 并发 / JVM / Spring / MySQL / Redis / 网络 / OS / MQ / 高并发锁 / 设计模式

| 篇 | 内容 | 优先级 |
|----|------|--------|
| [00-学习路线图](Java/00-学习路线图.md) | 8 阶段 3-6 个月 Java 后端备战路线 | ⭐⭐⭐⭐ |
| [01-Java集合](Java/01-Java集合.md) | HashMap / ConcurrentHashMap / List 底层 | ★★★★★ |
| [02-并发编程](Java/02-并发编程.md) | synchronized / volatile / CAS / 线程池 / ThreadLocal | ★★★★★ |
| [03-JVM](Java/03-JVM.md) | 内存区域 / GC / 类加载 / JMM / 调优 | ★★★★★ |
| [04-Spring](Java/04-Spring.md) | IOC / AOP / 循环依赖 / Boot 自动配置 / MVC | ★★★★★ |
| [05-MySQL](Java/05-MySQL.md) | 索引 / 事务 / MVCC / 锁 / explain | ★★★★☆ |
| [06-Redis](Java/06-Redis.md) | 数据结构 / 持久化 / 缓存三兄弟 / 分布式锁 | ★★★★☆ |
| [07-计算机网络](Java/07-计算机网络.md) | TCP / HTTP / HTTPS / 状态码 | ★★★★☆ |
| [08-操作系统](Java/08-操作系统.md) | 进程线程 / 死锁 / 虚拟内存 | ★★★☆☆ |
| [09-消息队列](Java/09-消息队列.md) | 可靠性 / 顺序 / 重复消费 / 积压 | ★★★☆☆ |
| [10-高并发锁](Java/10-高并发锁.md) | 秒杀 / 超卖 / 幂等 / 限流 | ★★★☆☆ |
| [11-设计模式](Java/11-设计模式.md) | 单例 / 工厂 / 代理 / 策略 | ★★★☆☆ |

## Python（3 篇）

> AI 岗 Python 基础：GIL / 可变不可变 / 并发模型 / 进阶陷阱

| 篇 | 内容 | 优先级 |
|----|------|--------|
| [01-Python基础](Python/01-Python基础.md) | 解释型/编译型 / GIL / 可变不可变 / 装饰器 | ★★★★★ |
| [02-Python并发](Python/02-Python并发.md) | 多线程 / 多进程 / asyncio / GIL 真相 | ★★★★★ |
| [03-Python进阶](Python/03-Python进阶.md) | 元类 / 描述符 / 内存管理 / 常见坑 | ★★★★☆ |

## Go（5 篇）

> 云原生 / 后端 Go 岗：GMP / channel / GC / 陷阱合集

| 篇 | 内容 | 优先级 |
|----|------|--------|
| [01-Go基础](Go/01-Go基础.md) | slice/map 底层 / defer / panic-recover / 接口 | ★★★★★ |
| [02-Go并发](Go/02-Go并发.md) | goroutine / channel / GMP / sync / context | ★★★★★ |
| [03-Go内存与GC](Go/03-Go内存与GC.md) | 逃逸分析 / 三色标记 / 混合写屏障 / pprof | ★★★★☆ |
| [04-Go进阶与陷阱](Go/04-Go进阶与陷阱.md) | 反射 / 标准库 / 性能优化 / 坑合集 | ★★★★☆ |
| [05-Go与Python对比](Go/05-Go与Python对比.md) | 语言特性对比（学 Go 引导篇） | ★★★☆☆ |

---

## 复习顺序建议

1. **Java 岗**：集合 → 并发 → JVM → Spring → MySQL → Redis（第一梯队，几乎必考），再补网络/OS/MQ/锁/设计模式
2. **Python/AI 岗**：Python 基础 → 并发（GIL 必考）→ 进阶陷阱，配合 [01-Agent应用开发](../01-面试八股文/01-Agent应用开发.md) 的 182 道 Agent 真题
3. **Go 岗**：Go 基础 → 并发（GMP 重头戏）→ 内存与 GC → 进阶陷阱
4. **临考速过**：每个文件的"考前速过清单"（如 Go 的 slice/map/defer/GMP 清单）是最佳冲刺材料
