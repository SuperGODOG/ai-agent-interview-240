> Lesson 0027 · 阶段三 · 并发编程 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 8 个追问

# 0027 · 线程池最佳实践 &amp; 常见错误 &amp; 参数选型 &amp; 动态线程池

上一课  讲清楚了 `ThreadPoolExecutor` *怎么工作*：7 参数、执行流程、拒绝策略、`ctl`、`Worker`。这一课换视角，讲**怎么用对**—— 线程池是 Java 后端生产事故的*常客*：*OOM、任务丢失、事务错乱、监控黑洞、上下文污染*，几乎每家公司都踩过。

面试官问「你线上遇到过什么线程池坑」时，判分点不在你能不能背 7 参数（那是*基本盘*），而在能不能**说出踩过的具体坑 + 排查过程 + 修复方案**。这节课 10 个场景全是踩坑现场，每个都是拿真金白银换来的。答完你就有素材了。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 CPU 密集型任务和 IO 密集型任务，`corePoolSize` 该怎么选？公式记住没？</summary>

CPU 密集：`N+1`（N 是 CPU 核数），一个多出来的线程用于抵消偶尔的缺页/短 IO；IO 密集：`2N` 起步，更精确用 Little 定律 `N × (1 + WT/ST)`，WT 是等待时间、ST 是计算时间。第 3 场景细讲。

</details>

<details>

<summary>Q0.2 线程池 + `ThreadLocal` 组合最经典的 bug 是什么？</summary>

**脏数据泄漏**：线程池复用同一个 `Thread`，前一个任务写进 `ThreadLocal` 的值没清，下一个任务读到就是上一个人的数据 —— 用户 A 的订单被写到用户 B 的账户里。第 4 场景细讲，解决办法：任务结束 `remove()`，或用 TransmittableThreadLocal。

</details>

## 面试场景 1：为什么阿里 Java 手册禁用 `Executors.newXXX`？⭐经典

🎤 面试官

《阿里 Java 开发手册》里有一条：「线程池不允许使用 `Executors` 创建，而是通过 `ThreadPoolExecutor` 的方式」。你能说说为什么吗？

🧑‍💻 你

因为 `Executors` 的四个静态工厂方法都**藏着 OOM 陷阱**，全部违反上一课讲的*「有界」*原则。核心问题是：任务队列或线程数是 *无界* 的，突发流量下资源会被打穿。挨个看：

工厂方法底层实现OOM 触发点

`newFixedThreadPool(n)`
`corePool = max = n`，队列 `LinkedBlockingQueue`（默认容量 `Integer.MAX_VALUE`）
队列无界，堆积任务 → 堆内存 OOM

`newSingleThreadExecutor()`
同上，只不过 `n=1`
同上

`newCachedThreadPool()`
`corePool=0, max=Integer.MAX_VALUE`，队列用 `SynchronousQueue`（不存储）
最大线程数无界 → 疯狂建线程 → 栈内存 OOM / 系统 native OOM

`newScheduledThreadPool(n)`
`max=Integer.MAX_VALUE`，队列 `DelayedWorkQueue`（无界）
延时任务堆积 → 堆 OOM

四种全是「无界」。*面试官等的就是这句总结*：**无论是任务队列无界还是线程数无界，一旦上游流量超预期，进程必然被 OOM 或系统 kill**。

真实事故 某电商大促预热，用 `Executors.newFixedThreadPool(200)` 处理商品详情异步预加载。促销开始瞬间 QPS 从 500 涨到 5 万，200 个线程处理不过来，任务疯狂塞进无界 `LinkedBlockingQueue`，10 秒后 Old GC、20 秒后 `OutOfMemoryError: Java heap space`，商品详情整个服务挂掉。事后复盘就一句话：把 `Executors.newFixedThreadPool` 换成 `new ThreadPoolExecutor` + `ArrayBlockingQueue(2000)`，事情就没了。

追问 那为什么 JDK 官方还提供 `Executors`？不是自己挖坑吗？

历史包袱 + 教学定位。`Executors` 在 JDK 5 引入时是为了*让新人快速上手* —— 一行代码就能拿到能跑的线程池，不用理解 7 参数。*教学用途* 是它的原意。JDK 8 之后 Doug Lea 也在 `Executors` 类的注释里加了「production code should generally use the constructors of `ThreadPoolExecutor`」。所以现在它更像一个反面教材。

## 面试场景 2：正确姿势 —— 自己 `new ThreadPoolExecutor`

🎤 面试官

你说要自己 new，那你写一个生产可用的线程池给我看看，每个参数为什么这么设？

🧑‍💻 你

一个「合格」的生产线程池必须显式配齐 7 参数 + *命名 `ThreadFactory`* + *明确的拒绝策略*：

```
ThreadPoolExecutor orderPool = new ThreadPoolExecutor(
16,                                     // corePoolSize，根据业务算出来
32,                                     // maximumPoolSize，一般 2×core 起步
60L, TimeUnit.SECONDS,                  // 空闲线程 60s 回收
new ArrayBlockingQueue<>(2000),         // ⭐ 有界队列，防止 OOM
new ThreadFactoryBuilder()              // Guava 的构造器，也可自实现
.setNameFormat("order-pool-%d")     // ⭐ 命名，排查栈时一眼定位
.setDaemon(false)                   // 生产任务不要 daemon
.setUncaughtExceptionHandler((t, e) ->
log.error("[{}] uncaught", t.getName(), e))
.build(),
new ThreadPoolExecutor.CallerRunsPolicy() // ⭐ 反压，宁可慢不能丢
);
```

五个关键点：

1. **有界队列**：`ArrayBlockingQueue` 容量必须是*业务能承受*的数字，不是拍脑袋。经验值：单次任务耗时 × 队列长度 ≈ 用户容忍等待时间。

2. **命名 `ThreadFactory`**：默认 `Executors.defaultThreadFactory()` 名字是 `pool-1-thread-3`，线上一栈全是 pool-1、pool-2 根本看不出是哪个业务。*命名是排查的先决条件*。

3. **`UncaughtExceptionHandler`**：兜底日志，防止异常被吞（第 5 场景细讲）。

4. **拒绝策略明确写**：不要偷懒用默认的 `AbortPolicy`，根据业务选（第 7 场景细讲 `CallerRunsPolicy`）。

5. **`allowCoreThreadTimeOut(true)`**：低峰期允许核心线程也回收，省资源。这个是可选项，看业务。

追问 `ThreadFactory` 如果不用 Guava，纯 JDK 怎么写？

简单实现一个匿名类就行：

```
ThreadFactory f = new ThreadFactory() {
private final AtomicInteger n = new AtomicInteger(1);
@Override public Thread newThread(Runnable r) {
Thread t = new Thread(r, "order-pool-" + n.getAndIncrement());
t.setDaemon(false);
t.setUncaughtExceptionHandler((th, e) ->
log.error("[{}] uncaught", th.getName(), e));
return t;
}
};
```

建议封成工具类复用，别每次都写匿名类。Spring 也自带 `CustomizableThreadFactory` 可以直接用。

## 面试场景 3：线程数怎么定？CPU 密集 vs IO 密集 ⭐经典

🎤 面试官

你上面写的 `corePoolSize = 16`，怎么定出来的？如果任务变成纯计算的，怎么调？

🧑‍💻 你

看任务是 **CPU 密集**还是**IO 密集**，公式不同：

任务类型公式直觉典型场景

CPU 密集
`N + 1`
线程数≈核数，跑满 CPU 就够；多的 1 是缓冲
加密解密、图像处理、复杂计算、序列化/反序列化

IO 密集（经验）
`2 × N`
IO 时 CPU 闲着，多加线程能重叠 IO
REST 调用、数据库查询、Redis、消息队列

IO 密集（精确）
`N × (1 + WT / ST)`
Little 定律：WT=等待时间，ST=计算时间
压测得到 WT/ST 精确比例后用

*N 是 `Runtime.getRuntime().availableProcessors()`*。举例：8 核机器跑 HTTP 调用（假设 90% 时间等 IO，10% 时间处理），`N × (1 + 9/1) = 8 × 10 = 80`，比拍脑袋 `2N=16` 更贴合实际。

追问 CPU 密集为什么是 N+1 而不是 N？

Doug Lea 在《Java Concurrency in Practice》里给出的解释：*+1 是给「偶尔的缺页中断、GC 停顿、极短的 IO」保留缓冲*。假如恰好设 N，任何一个线程被短暂挂起（比如 minor GC），就有一个 CPU 核心闲下来。多一个线程可以补位，让 CPU 利用率始终≈100%。代价只是极小的上下文切换开销，很划算。

追问 那 `maximumPoolSize` 怎么定？也是 `2N` 吗？

没有铁律。**常见做法：`max = 2 × core`**，让流量高峰时能弹一倍容量。但也有反常识的观点：*如果队列足够大，`max` 完全可以等于 `core`*—— 因为核心线程占满后先入队，队列不满永远不会创建到 `max`。真正决定容量的是 `core + queue`，`max - core` 只是*队列满时的最后一层缓冲*。所以稳态业务用 `max = core` + 大队列，突发业务用 `max = 2 × core` + 小队列。

追问 混合型任务（既有 CPU 又有 IO）怎么办？

三种做法：**(1) 拆**：把 IO 部分和 CPU 部分拆成两个池，分别按各自公式；**(2) 压测**：用两个池不现实的话，直接压测调参 —— 从 `2N` 起步，逐步加，观察 CPU 利用率和 P99 延迟，出现拐点就停；**(3) Reactor**：真正的高并发混合型场景，考虑 WebFlux/Netty 这类 *event loop* 架构，用少量线程 + NIO 处理海量连接，不再玩「多线程 vs 少线程」这一套。

追问 线程池的队列该怎么选？

四类主流选型：**(1) `ArrayBlockingQueue`**：*有界优先*，最推荐的生产队列，容量强制；**(2) `LinkedBlockingQueue`**：吞吐更高（头尾锁分离），但*必须传 capacity*，不然是无界坑；**(3) `PriorityBlockingQueue`**：按优先级出队，任务必须实现 `Comparable`，注意*无界*；**(4) `DelayQueue`**：延时任务，`ScheduledThreadPoolExecutor` 底层就是它；**(5) `SynchronousQueue`**：不存储，来一个必须有线程接，`newCachedThreadPool` 底层用它 —— 但因此配合无界 `max` 才有意义。

## 面试场景 4：线程池 + `ThreadLocal` 的经典 bug ⭐经典

🎤 面试官

线程池和 `ThreadLocal` 一起用，你遇到过什么问题？

🧑‍💻 你

最经典的是**脏数据泄漏**。线程池会*复用线程*，Task A 在 `ThreadLocal` 里塞了 userId=1001，跑完没清，线程回池；Task B 拿到这个线程执行时读 `ThreadLocal`，读到的还是 1001 —— 用户 B 的操作被记到用户 A 头上。真踩过就永远忘不掉。

```
// 举例：一个「污染」现场
private static final ThreadLocal<Long> USER_ID = new ThreadLocal<>();

pool.execute(() -> {
USER_ID.set(1001L);
doBusiness();          // 忘了 remove
});

pool.execute(() -> {
Long uid = USER_ID.get();   // ⚠️ 可能拿到 1001，不是 null
audit(uid);
});
```

三种解决方案：

1. **手动 `remove()`**：任务前后各清一次，最保险，但侵入代码：

```
pool.execute(() -> {
try {
USER_ID.set(1001L);
doBusiness();
} finally {
USER_ID.remove();       // ⭐ 必须
}
});
```

2. **包一层装饰器**：用 `ExecutorService` 的装饰器统一在 `submit`/`execute` 前后 `remove`，业务无感知。适合团队协作。

3. **用 TransmittableThreadLocal (TTL)**：阿里开源，*不仅解决泄漏，还能把父线程的 `ThreadLocal` 值传递到线程池的子线程* —— 后者是 `InheritableThreadLocal` 在线程池场景下的失效痛点。生产强烈推荐。

追问 `InheritableThreadLocal` 在线程池里为什么失效？

`InheritableThreadLocal` 的复制发生在 *`new Thread()` 的构造时刻*（子线程 inherit 父线程的值）。但线程池的线程是*启动时创建一次*，之后一直复用 —— 后续任务提交时，线程*早就存在*了，不会再走一次「继承」，所以拿不到调用方最新的 `ThreadLocal` 值。TTL 的解决办法是：*在任务被 `submit` 时快照父线程的值，在 `run` 时手动回放，跑完再清*。上一课  也讲过 `ThreadLocalMap` 弱引用泄漏的坑，两个坑组合起来威力更大。

## 面试场景 5：线程池 + 异常吞噬

🎤 面试官

线程池提交的任务抛了异常，你怎么发现？

🧑‍💻 你

*这是灵魂拷问* —— 因为很多人写完 `submit` 就完事了，异常被 `Future` 静默吞掉，永远发现不了。核心区别：

- `execute(Runnable)`：任务抛异常，会走线程的 `UncaughtExceptionHandler`，能记日志。

- `submit(Runnable/Callable)`：任务抛异常被包进返回的 `Future`，*只有调用 `future.get()` 才会重新抛出*；不 `get()`，异常永远看不到。

```
// ❌ 反例：异常永远被吞
pool.submit(() -> {
throw new RuntimeException("boom!");
});
// 控制台一片安静，业务出错都不知道

// ✅ 正解 1：submit + 主动 get
Future<?> f = pool.submit(() -> { throw new RuntimeException("boom!"); });
try {
f.get();                            // 这里会抛 ExecutionException
} catch (ExecutionException e) {
log.error("task failed", e.getCause());
}

// ✅ 正解 2：改用 execute，交给 UEH
pool.execute(() -> {
try {
doBusiness();
} catch (Exception e) {
log.error("task failed", e);    // ⭐ 手动兜底最保险
}
});
```

推荐组合拳：**每个任务外层包 `try-catch` + 线程池装 `UncaughtExceptionHandler` + 使用 `submit` 时必须 `get()` 或用 `CompletableFuture.exceptionally`**。三重保险，一个都不能省。

追问 `CompletableFuture` 的异常处理和 `Future` 有什么不同？

`CompletableFuture` 提供了链式 API：`.exceptionally(ex -> ...)` 捕获异常并给一个兜底值、`.handle((v, ex) -> ...)` 同时处理成功/失败、`.whenComplete((v, ex) -> log)` 只打日志不改结果。*比 `Future.get()` 优雅得多，也不会遗漏*。生产代码里 *90% 的异步都建议用 `CompletableFuture`*，只在需要取消/超时的场景才用底层 `Future`。下一课  会展开。

## 面试场景 6：线程池 + 数据库连接池 + 事务上下文 ⭐真实事故

🎤 面试官

Spring 的 `@Transactional` 方法里，你 `pool.submit` 一个子任务去写另一张表，会怎样？

🧑‍💻 你

**子任务不在事务里**。这是 Spring 事务模型的*致命交叉点*：`@Transactional` 依赖 `ThreadLocal`（`TransactionSynchronizationManager`）保存当前 `Connection`，只对*当前线程*可见。你 `submit` 提交任务到线程池，子任务跑在*另一个线程*上，拿不到主线程的 `Connection`，会从连接池*新拿一个* —— 结果就是：

- 主事务里插了 5 条数据，子线程插的第 6 条走的是*另一个连接、另一个事务*。

- 主事务回滚，前 5 条撤销，第 6 条*已经提交* —— 数据不一致。

- 更糟：主事务还没 commit，子线程去读同一行，读不到（另一个连接看不到未提交数据）—— 死锁 or 空返回。

三种解法：

1. **不要在 `@Transactional` 里 `submit`**：最简单，把异步移到事务方法之外。*「同步事务先提交，再异步做其他事」*。

2. **子任务用 `TransactionTemplate` 显式开新事务**：明确子任务是新事务，语义清晰。

3. **用消息队列解耦**：主事务里发 MQ 消息（可靠消息 or *本地消息表*），子逻辑在消费者里做，天然分布式事务。

真实事故 某支付业务，主事务里扣款 + `pool.submit` 发通知短信 + 记流水。发布后偶发问题：*用户收到短信但账户没扣钱*。排查发现主事务因为唯一键冲突回滚了，但异步的「记流水 + 发短信」用的是别的连接和别的线程，早就 commit 完了。修复方案：把发短信和记流水挪到 `TransactionSynchronizationManager.registerSynchronization` 里的 `afterCommit()` 回调，只有主事务真正 commit 后才触发。

## 面试场景 7：`CallerRunsPolicy` 反压模式

🎤 面试官

4 种拒绝策略，什么时候用 `CallerRunsPolicy`？

🧑‍💻 你

`CallerRunsPolicy` 是**「反压」** —— 线程池满时，让*提交者线程自己执行任务*。这带来一个精妙的副作用：*提交者被占用，无法继续 `submit`，上游自然减速*。这是「宁可慢也不能丢」场景的首选：

- **订单入库**：丢一单就是丢钱，情愿慢，不能丢。

- **监控上报**：日志/指标丢了排查故障没依据，情愿采集变慢。

- **Kafka Consumer 处理**：消费速率必须 ≤ 处理速率，否则 lag 越拉越大直到 rebalance。

4 种策略对比：

策略行为典型场景

`AbortPolicy`（默认）抛 `RejectedExecutionException`快速失败，让上游立即感知
`CallerRunsPolicy`提交者线程自己执行反压，不能丢任务
`DiscardPolicy`静默丢弃非关键日志、可有可无的埋点
`DiscardOldestPolicy`丢队首最旧的，塞新的进去只关心最新数据，如实时行情

生产上还有*第 5 种：自定义策略* —— 一般把任务写到 *Kafka/本地磁盘/DLQ 死信队列*，避免真的丢。

追问 `CallerRunsPolicy` 有没有坑？

有两个：**(1) 提交者线程被占用** —— 如果提交者是 Web 请求线程（Tomcat 线程），会直接*阻塞 HTTP 响应*；如果提交者是 *MQ 消费线程*，会阻塞消费。所以适合*后台线程*提交，不适合 *用户请求线程*提交。**(2) 破坏了「隔离」** —— 本来提交者只是提交，现在被迫处理业务，异常也算在提交者头上，日志和监控会有点错乱。

追问 线程池怎么优雅关闭？`shutdown` 和 `shutdownNow` 区别？

`shutdown()`：*拒绝新任务，队列里已有的继续执行完*；`shutdownNow()`：*拒绝新任务 + 清空队列 + 对正在跑的线程发 `interrupt`，返回队列里未执行的任务列表*。*优雅关闭三步曲*：

```
pool.shutdown();                                    // 1. 停止收新任务
if (!pool.awaitTermination(30, TimeUnit.SECONDS)) { // 2. 等 30s
pool.shutdownNow();                             // 3. 还没完，强制中断
pool.awaitTermination(10, TimeUnit.SECONDS);    //    再等 10s 让中断生效
}
```

Spring Boot 里推荐通过 `@PreDestroy` 或 `ExecutorConfigurationSupport.setWaitForTasksToCompleteOnShutdown(true)` 交给容器管理。

## 面试场景 8：共享线程池 vs 独立线程池 ⭐核心设计

🎤 面试官

公司要求节约资源，让所有业务共用一个大线程池，你有什么看法？

🧑‍💻 你

**坚决反对**。共享大池是*并发系统雪崩的最大放大器*：*一个业务打满，所有业务全瘫*。这也是 Hystrix / Sentinel 从设计之初就强调「线程池隔离」的原因。

举个典型翻车链路：

1. 共享池 core=50、queue=1000。业务 A 调下游 API，正常 10ms 返回，占用极少。

2. 某天下游 API 抖动，A 的调用变成 5s 一次。

3. A 的任务开始堆积，很快占满 50 个线程 + 1000 队列。

4. 业务 B（订单）、C（支付）也来提交任务，一律被拒。

5. 结果：*一个不重要的 API 抖动，把整个系统的订单、支付全干趴*。

正确做法：**按业务隔离**：

- **核心业务独占线程池**：订单、支付各自独立，参数按业务 QPS 定。

- **非核心业务共享一个「杂物池」**：日志上报、埋点、通知这种非关键的可以合并，但注意*整个杂物池打满不影响核心*。

- **下游依赖分池**：调 A 服务的线程池和调 B 服务的分开 —— A 抖动不会拖累 B。

补充坑 共享池还有一个鲜为人知的*死锁*陷阱：如果父任务在池内 `submit` 子任务，然后 `get()` 等子任务返回，一旦父任务占满所有线程，子任务永远排在队列里等不到执行，父任务 `get()` 阻塞 —— *循环依赖死锁*。`ForkJoinPool` 用 work stealing 解决这个问题，普通 `ThreadPoolExecutor` 唯一的解药就是*父子分池*。

追问 那分池的粒度怎么定？总不能一个接口一个池吧？

经验粒度：**按「故障域」分** —— 会一起挂的分一组，独立挂的独立分池。*「同一个下游 + 同一个业务重要度」为一个池*。具体：*(1) 核心业务 & 非核心业务*拆开；*(2) 慢任务和快任务*拆开（慢任务把线程占住会拖死快任务）；*(3) 高 QPS 和低 QPS*拆开。一般 10-30 个池是合理规模，超过就要考虑用 *Sentinel 线程池模式* 或者 *Bulkhead* 模式统一管。

## 面试场景 9：动态线程池的实现思路

🎤 面试官

线程池参数上线后发现设错了，需要重启才能调？

🧑‍💻 你

*不需要*。`ThreadPoolExecutor` 从 JDK 6 就提供了 setter，运行时可以直接改：

- `setCorePoolSize(int)`：改核心线程数（会立刻调整）。

- `setMaximumPoolSize(int)`：改最大线程数。

- `setKeepAliveTime(long, TimeUnit)`：改回收时间。

- `allowCoreThreadTimeOut(boolean)`：让核心线程也参与回收。

但队列容量 *不能* 动态改（`ArrayBlockingQueue.capacity` 是 `final`）。真需要改队列容量的话，有两种思路：*(1) 继承 `LinkedBlockingQueue` 用反射把 `capacity` 字段改为可变；(2) 直接换一个新线程池，老的 `shutdown`*。

动态线程池的产品化落地：

项目作者特点

**DynamicTp**美团系接 Nacos/Apollo/ZK，配置改动实时推送到应用；带监控告警
**Hippo4j**OpenGoofy 社区独立管理端，可视化配置，多租户，全链路监控
**Spring Boot Actuator**官方暴露 `/actuator/metrics`，简单可视化但不能改配置

选型建议：*小团队 DynamicTp（够用轻量），中大型公司 Hippo4j（有独立控制台）*。

追问 Spring `@Async` 默认线程池是什么？有什么坑？

Spring 5 之前默认是 `SimpleAsyncTaskExecutor` —— 这货*每次调用都新建一个线程*，跟裸 `new Thread` 一样没有池化，是*生产环境的雷*。*解决方案*：在 `@Configuration` 里注册一个 `ThreadPoolTaskExecutor` 的 Bean，通过 `AsyncConfigurer.getAsyncExecutor()` 显式指定，或直接 `@Async("myPool")` 按名字引用。Spring Boot 3.2 之后如果启用了 virtual thread 才会默认改成 `VirtualThreadTaskExecutor`，其他情况仍是老坑。*面试常见追问，一定要能答出来*。

## 面试场景 10：线程池监控指标

🎤 面试官

线上线程池，你怎么知道它是不是健康的？

🧑‍💻 你

`ThreadPoolExecutor` 自带一堆 getter，把它们采集到 Prometheus / Grafana，就能看到全貌：

指标方法含义 & 告警阈值

活跃线程数`getActiveCount()`正在执行任务的线程数
当前线程数`getPoolSize()`池中当前线程总数
历史最大线程数`getLargestPoolSize()`曾经达到过的最大值 —— *如果=max，说明扩过顶*
总提交任务数`getTaskCount()`累计提交（含已完成、执行中、排队中）
已完成任务数`getCompletedTaskCount()`累计完成
队列大小`getQueue().size()`当前排队任务数（对比 `getQueue().remainingCapacity()` 看水位）

三条核心告警规则：

1. **`activeCount / poolSize > 80%` 持续 5 分钟**：说明容量吃紧，需要扩 `core`。

2. **队列使用率 > 70%**：说明处理速度跟不上提交速度，同上。

3. **拒绝次数 > 0**：一旦发生就报警 —— 拒绝意味着有任务被丢或被降级。

拒绝次数需要包一层 `RejectedExecutionHandler` 自己计数：

```
AtomicLong rejectedCount = new AtomicLong();
RejectedExecutionHandler wrap = (r, e) -> {
rejectedCount.incrementAndGet();                 // ⭐ 打点
log.warn("task rejected, count={}", rejectedCount.get());
new ThreadPoolExecutor.CallerRunsPolicy().rejectedExecution(r, e);
};
```

追问 怎么判断线程池是否「健康」？给一个综合公式。

综合看四个维度：*(1) 利用率* `activeCount / maximumPoolSize` —— 长期 >80% 说明容量不够；长期 <20% 说明池设大了浪费。*(2) 队列水位* `queue.size() / queue.capacity()` —— 长期 >70% 就要报警。*(3) 拒绝率* `rejected / totalSubmit` —— 大于 0.1% 就该扩容或降级。*(4) 任务平均耗时*（自己埋点）—— 突然涨说明下游异常，快看依赖。四个都健康才是真健康。

## 💻 代码验证

### 验证 1：`Executors.newFixedThreadPool` 演示 OOM

```
// 启动参数： -Xmx64m -Xms64m
public class ExecutorsOom {
public static void main(String[] args) {
ExecutorService pool = Executors.newFixedThreadPool(2);
for (int i = 0; i < 1_000_000; i++) {
int id = i;
pool.execute(() -> {
try { Thread.sleep(60_000); } catch (Exception ignore) {}
System.out.println("task " + id);
});
}
}
}
// 几秒后就抛：
// Exception in thread "main" java.lang.OutOfMemoryError: Java heap space
// 原因：LinkedBlockingQueue 无界，把 100 万个 Runnable 全塞进堆里
```

### 验证 2：`ThreadLocal` 泄漏 & TTL 修复对比

```
import com.alibaba.ttl.TransmittableThreadLocal;
import com.alibaba.ttl.threadpool.TtlExecutors;

public class TtlDemo {
// ❌ 普通 ThreadLocal，任务间会泄漏
private static final ThreadLocal<String> DIRTY = new ThreadLocal<>();
// ✅ TTL，配合 TtlExecutors.getTtlExecutorService 使用
private static final ThreadLocal<String> CLEAN = new TransmittableThreadLocal<>();

public static void main(String[] args) throws Exception {
ExecutorService raw = Executors.newSingleThreadExecutor();
ExecutorService wrapped = TtlExecutors.getTtlExecutorService(raw);

DIRTY.set("A");
raw.submit(() -> {
System.out.println("DIRTY in task1 = " + DIRTY.get());   // null，普通 TL 不跨线程
}).get();
raw.submit(() -> {
DIRTY.set("leaked");                                     // 忘 remove
}).get();
raw.submit(() -> {
System.out.println("DIRTY in task3 = " + DIRTY.get());   // leaked！⚠️ 脏数据
}).get();

CLEAN.set("B");
wrapped.submit(() -> {
System.out.println("CLEAN in task = " + CLEAN.get());    // B，值被正确传递
}).get();
}
}
```

### 验证 3：`submit` 吞异常 vs `execute` 抛出来

```
public class ExceptionSwallowed {
public static void main(String[] args) throws Exception {
ThreadPoolExecutor pool = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS,
new LinkedBlockingQueue<>(10),
r -> {
Thread t = new Thread(r, "demo-worker");
t.setUncaughtExceptionHandler((th, e) ->
System.err.println("UEH caught: " + e.getMessage()));
return t;
});

// ❌ submit：异常被 Future 吞掉，控制台一片安静
pool.submit(() -> { throw new RuntimeException("submit-boom"); });

Thread.sleep(500);
System.out.println("--- submit 后无输出 ---");

// ✅ execute：异常走 UEH，会打印
pool.execute(() -> { throw new RuntimeException("execute-boom"); });

Thread.sleep(500);
pool.shutdown();
}
}
// 输出：
// --- submit 后无输出 ---
// UEH caught: execute-boom
```

### 验证 4：动态调整核心线程数

```
public class DynamicResize {
public static void main(String[] args) throws Exception {
ThreadPoolExecutor pool = new ThreadPoolExecutor(
2, 4, 60, TimeUnit.SECONDS,
new ArrayBlockingQueue<>(100));

for (int i = 0; i < 20; i++) {
pool.execute(() -> {
try { Thread.sleep(2000); } catch (Exception ignore) {}
});
}
System.out.println("before resize: pool=" + pool.getPoolSize()
+ ", active=" + pool.getActiveCount());

pool.setCorePoolSize(8);                    // ⭐ 运行时改核心线程
pool.setMaximumPoolSize(16);
Thread.sleep(500);

System.out.println("after resize: pool=" + pool.getPoolSize()
+ ", active=" + pool.getActiveCount());
pool.shutdown();
}
}
// 输出示意：
// before resize: pool=2, active=2
// after resize: pool=8, active=8
```

### 验证 5：线程池监控埋点（30s 采集一次）

```
public class PoolMonitor {
public static void start(ThreadPoolExecutor pool, String name) {
ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(
r -> { Thread t = new Thread(r, "pool-monitor"); t.setDaemon(true); return t; });

scheduler.scheduleAtFixedRate(() -> {
int active = pool.getActiveCount();
int size = pool.getPoolSize();
int max = pool.getMaximumPoolSize();
long completed = pool.getCompletedTaskCount();
int queued = pool.getQueue().size();
double utilization = (max == 0) ? 0 : (active * 1.0 / max);

System.out.printf(
"[%s] active=%d, pool=%d/%d, completed=%d, queue=%d, util=%.1f%%%n",
name, active, size, max, completed, queued, utilization * 100);

// 简单告警
if (utilization > 0.8) {
System.err.println("[" + name + "] ⚠️ utilization > 80%, consider scale up");
}
}, 0, 30, TimeUnit.SECONDS);
}
}
// 生产上把 println 换成 Prometheus/Micrometer 打点：
// meterRegistry.gauge("pool.active", Tags.of("name", name), pool, ThreadPoolExecutor::getActiveCount);
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 阿里手册为什么禁 `Executors.newXXX`？两句话总结。</summary>

四个工厂方法都藏着无界隐患：`newFixed`/`newSingle`/`newScheduled` 用无界队列（`LinkedBlockingQueue`/`DelayedWorkQueue`），任务堆积 → 堆 OOM；`newCached` `maximumPoolSize=Integer.MAX_VALUE`，线程数爆炸 → 栈 OOM 或系统级 OOM。生产必须自己 `new ThreadPoolExecutor` + 有界队列。

</details>

<details>

<summary>Q2 CPU 密集 vs IO 密集的线程数公式，各是什么？为什么 CPU 密集是 N+1？</summary>

CPU 密集 = `N+1`（N 是核数）；IO 密集 = `2N` 起步，精确公式 `N × (1 + WT/ST)`。CPU 密集 +1 是给「偶尔的缺页、GC、短 IO」保留缓冲，让 CPU 空闲时有线程能立刻补位，避免 CPU 利用率跌下 100%。

</details>

<details>

<summary>Q3 线程池 + `ThreadLocal` 的经典 bug 是什么？三种解法列一下。</summary>

脏数据泄漏：线程复用导致前一任务的 `ThreadLocal` 值污染后一任务。解法：*(1) `try-finally` 主动 `remove()`；(2) 用装饰器统一在任务前后清；(3) 用 `TransmittableThreadLocal`（TTL），既解决泄漏又能跨线程池传递值*。

</details>

<details>

<summary>Q4 `submit` 和 `execute` 提交任务，异常处理有什么不同？</summary>

`execute` 抛出的异常会走线程的 `UncaughtExceptionHandler`，能被记录；`submit` 抛出的异常被包进返回的 `Future`，*只有调用 `future.get()` 才会重新抛出*，不 `get()` 永远看不到 —— 生产严重 bug 常因此被吞噬。三重保险：任务内 `try-catch` + `UEH` + `submit` 后必须 `get`（或换 `CompletableFuture.exceptionally`）。

</details>

<details>

<summary>Q5 为什么共享大线程池是危险的？分池的粒度怎么定？</summary>

一个业务打满池会拖垮所有业务，等于把「故障隔离」这件事完全放弃了。分池粒度按*「故障域」*：*(1) 核心 vs 非核心*拆开；*(2) 慢任务 vs 快任务*拆开；*(3) 不同下游依赖*拆开。*核心业务独占，非核心可以合并杂物池，一般 10-30 个池为宜*。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- alibaba/transmittable-thread-local · TTL 项目主页 —— 线程池 + ThreadLocal 的官方推荐解法

- dromara/dynamic-tp · 美团系动态线程池 —— 生产可用的动态线程池实现

- opengoofy/hippo4j · Hippo4j 动态线程池 —— 带独立管理端的动态线程池

- JDK 21 · `ThreadPoolExecutor` API —— getter/setter 官方文档

#### 🔗 关联课件

-  —— 上一课，先理解「怎么工作」再看「怎么用对」

-  —— `ThreadLocalMap` 弱引用底层，本课第 4 场景的前置

-  —— 队列选型的完整对比，本课第 2、3 场景的前置

-  —— 下一课，异步编程的现代姿势

#### 🧭 下一课预告

Lesson 0028：**CompletableFuture & 并发集合工具类** —— 抛开原始 `Future`，用链式 API 组合异步任务、优雅处理超时和异常、玩转编排。是线程池篇章的*好用姿势*收官。

💬 有任何疑问 ——「这个参数在我们业务里应该设多少？」「异步事务这个坑我们也踩了，怎么彻底解？」「动态线程池选 DynamicTp 还是 Hippo4j？」—— 直接问我。我是你的老师，也是你的追问陪练。


