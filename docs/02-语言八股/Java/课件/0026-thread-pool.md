> Lesson 0026 · 阶段三 · 并发编程 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0026 · 线程池详解：核心 7 参数 & 执行流程 & 拒绝策略 & ctl

线程池是 Java 后端并发章节的**第二座硬山**（第一座是上一章 ）。面试官一旦聊到并发，几乎必问：**「7 个参数说一下」「执行流程画一下」「4 种拒绝策略」「ctl 高 3 位低 29 位怎么算的」「Worker 为啥继承 AQS」**。这一课把这些高频问题一次性打穿，下一课  讲最佳实践与线上调参。

为什么线程池这么重要？因为它是 Java 后端 *所有* 异步处理的基石：Tomcat 的请求处理、Dubbo 的 RPC 调用、Kafka Consumer 的消费、@Async 注解、CompletableFuture ——底下全是线程池。参数配错一个字段，线上就会 OOM、Full GC 或响应雪崩。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `ThreadPoolExecutor` 的 7 大核心参数是哪 7 个？（能背几个算几个）</summary>

`corePoolSize`、`maximumPoolSize`、`keepAliveTime`、`TimeUnit unit`、`BlockingQueue<Runnable> workQueue`、`ThreadFactory threadFactory`、`RejectedExecutionHandler handler`。第 2 场景逐个拆。

</details>

<details>

<summary>Q0.2 核心线程满了之后，新任务是先入队列，还是先扩线程到 maximumPoolSize？</summary>

**先入队列**。只有队列也满了才扩线程。这是线程池最反直觉的设计，第 3 场景和追问细讲设计哲学。

</details>

## 面试场景 1：为什么要用线程池？

🎤 面试官

先聊个简单的 —— 为什么 Java 里要用线程池？直接 `new Thread().start()` 不行吗？

🧑‍💻 你

裸 `new Thread` 在生产环境几乎是*不可接受*的，线程池带来四个不可替代的收益：

- **降低创建/销毁开销**：Java 线程和 OS 内核线程 1:1 绑定，创建一个线程要陷内核态、分配 1MB 栈空间；线程池*复用*已有线程执行新任务，只有第一次创建有开销。

- **控制并发数，防资源耗尽**：不限制线程数的话，一个突发流量能直接把 CPU、内存、文件描述符打爆。线程池用 `maximumPoolSize` 兜底。

- **提供任务队列，削峰填谷**：来不及处理的任务先排队，让下游压力平滑而不是尖刺。

- **统一管理便于监控**：`getActiveCount()`、`getQueue().size()`、`getCompletedTaskCount()` 可以直接暴露到 Prometheus。

追问 那我为每个请求 `new Thread` 会有什么后果？

三个致命问题：**(1) 性能塌**—— 高 QPS 下 CPU 大量时间花在线程上下文切换和栈分配；**(2) OOM**—— 每个线程默认 1MB 栈，几千个线程就能吃掉几个 GB；**(3) 无法治理**—— 线程没名字、没监控、抛异常没兜底，出问题只能看堆栈慢慢猜。所以《阿里 Java 开发手册》强制规定「线程资源必须通过线程池提供」。

## 面试场景 2：ThreadPoolExecutor 的 7 大核心参数 ⭐必背

🎤 面试官

把 `ThreadPoolExecutor` 的构造函数 7 个参数背一下，每个一句话说清楚。

🧑‍💻 你

完整签名：

```
public ThreadPoolExecutor(
int corePoolSize,                    // 1. 核心线程数
int maximumPoolSize,                 // 2. 最大线程数
long keepAliveTime,                  // 3. 非核心线程空闲存活时长
TimeUnit unit,                       // 4. 时间单位
BlockingQueue<Runnable> workQueue,   // 5. 任务队列
ThreadFactory threadFactory,         // 6. 线程工厂
RejectedExecutionHandler handler)    // 7. 拒绝策略
```

- **corePoolSize**：常驻线程数。即使空闲也不回收（除非开 `allowCoreThreadTimeOut`）。

- **maximumPoolSize**：最多能开到多少线程 = 核心 + 非核心之和的上限。

- **keepAliveTime + unit**：非核心线程空闲多久没拿到任务就被回收（比如 `60L, SECONDS`）。

- **workQueue**：等待执行的任务队列，常见 `ArrayBlockingQueue`（有界数组）、`LinkedBlockingQueue`（无界链表，慎用！）、`SynchronousQueue`（无缓冲直接交付）、`PriorityBlockingQueue`（优先级）。详见 。

- **threadFactory**：创建线程用的工厂，重点是*给线程起有意义的名字*（否则日志里全是 `pool-1-thread-1`）。

- **handler**：任务被拒绝时怎么办，4 种内置策略见第 4 场景。

追问 为什么 `threadFactory` 一定要自定义？

核心是**可观测性**。默认工厂 `Executors.defaultThreadFactory()` 起的名字是 `pool-N-thread-M`，线上排查问题时看到 `pool-3-thread-7` 你根本不知道这是订单线程池还是消息线程池。自定义工厂用 `Guava` 的 `ThreadFactoryBuilder` 起个业务名如 `order-pool-%d`，jstack、arthas、堆 dump 里都能一眼看出来。顺便还能挂上 `UncaughtExceptionHandler` 兜底异常。

追问 `keepAliveTime` 只对非核心线程生效吗？

**默认是**。核心线程一旦创建就常驻，即使空闲。但可以调 `allowCoreThreadTimeOut(true)` 让核心线程也走超时回收 —— 用于「白天有活、晚上完全没活」这种场景，能省点内存。生产环境慎开，因为下次流量到来时又要重新创建，反而拖累响应时间。

## 面试场景 3：线程池执行任务的完整流程 ⭐必背

🎤 面试官

把 `execute(task)` 提交一个任务之后的完整流程画一下。

🧑‍💻 你

五步决策，按顺序判断：

```
submit task
│
▼
① workerCount < corePoolSize ?
│  是 → 【创建核心线程】执行任务 ✓
│
否
▼
② workQueue.offer(task) 成功 ?
│  是 → 任务入队，等待被线程取出 ✓
│
否（队列已满）
▼
③ workerCount < maximumPoolSize ?
│  是 → 【创建非核心线程】执行任务 ✓
│
否
▼
④ 【触发拒绝策略】handler.rejectedExecution(task, executor)
✗

（旁路） 非核心线程空闲超 keepAliveTime → 被回收
```

关键源码简化版：

```
public void execute(Runnable command) {
int c = ctl.get();
// 步骤 ①
if (workerCountOf(c) < corePoolSize) {
if (addWorker(command, true)) return;
c = ctl.get();
}
// 步骤 ②
if (isRunning(c) && workQueue.offer(command)) {
// 二次校验：入队后如果池被 shutdown 要回滚
int recheck = ctl.get();
if (!isRunning(recheck) && remove(command))
reject(command);
else if (workerCountOf(recheck) == 0)
addWorker(null, false);  // 兜底：至少留一个线程消费队列
}
// 步骤 ③
else if (!addWorker(command, false))
// 步骤 ④
reject(command);
}
```

追问 core < max，那 core 满了为什么先入队而不是先扩到 max？这不是很反直觉？

这是**线程池的设计哲学**：*宁可让任务等一等，也不轻易扩线程*。核心原因有二 —— (1) 创建线程本身有开销（陷内核态、分配栈），能不创建就不创建；(2) 更多的线程 ≠ 更高的吞吐，反而会加剧 CPU 上下文切换。所以 JUC 的作者 Doug Lea 的选择是：**只在队列都撑不住的极端情况下才扩线程**，扩到 max 是最后的救命稻草。这也是为什么用 `LinkedBlockingQueue` 无界队列时 `maximumPoolSize` 完全失效 —— 队列永远满不了，永远进不了步骤 ③。

追问 源码里 offer 成功后为什么还要 recheck？

这是**并发场景下的时序兜底**。两个隐患：(1) 从判断 `isRunning(c)` 到 `offer` 之间，另一个线程可能已经调了 `shutdown()`，任务入队后没人处理；(2) 从 offer 成功到 recheck 之间，所有 worker 可能都退出了（比如都超时了），队列里有任务却没消费者。所以 recheck 干两件事：状态变了就把任务移除并拒绝；worker 数为 0 就补一个非核心线程当消费者。

## 面试场景 4：4 种拒绝策略 ⭐必背

🎤 面试官

JDK 自带哪几种拒绝策略？各自什么场景？

🧑‍💻 你

4 种，都是 `ThreadPoolExecutor` 的静态内部类：

策略行为适用场景

`AbortPolicy`（默认）
抛 `RejectedExecutionException`
核心业务：宁可让调用方感知失败去重试，也不能悄悄丢

`CallerRunsPolicy`
由*调用者线程*自己执行这个任务
不允许丢，且能接受降速 —— 天然反压

`DiscardPolicy`
静默丢弃，什么也不做
非关键路径：日志、埋点、监控上报

`DiscardOldestPolicy`
丢掉队列头（最老的）任务，然后重试提交当前任务
只关心「最新」数据的场景，如实时行情推送

追问 `CallerRunsPolicy` 有什么妙用？

它是**天然的反压（back-pressure）机制**。想象生产者是主线程在快速 submit 任务，一旦线程池满了，主线程会被迫自己执行这个任务 —— 这个执行期间它*没办法继续提交新任务*，等于自动降速了。比 `AbortPolicy` 抛异常温和得多（异常处理不当就直接崩了），比 `DiscardPolicy` 又不会丢任务。缺点是：如果调用者线程是 Web 容器的 Tomcat 线程，会占住 HTTP 连接影响响应；如果是主线程，会阻塞整个流程。**用在异步任务的提交端最合适**。

追问 想在拒绝时把任务打到 MQ 里做兜底，怎么做？

自己实现 `RejectedExecutionHandler` 接口即可：`public void rejectedExecution(Runnable r, ThreadPoolExecutor executor)`，在里面把任务序列化后发到 Kafka/RocketMQ，由消费者慢慢处理。这是生产环境很常见的做法，业界的 `Dubbo`、`Netty` 都有自定义拒绝策略，比如 `Dubbo` 的策略会在拒绝时打印线程堆栈到日志，方便排查。

## 面试场景 5：ctl 字段的位运算 ⭐核心

🎤 面试官

`ThreadPoolExecutor` 里的 `ctl` 字段是什么？为什么要用位运算？

🧑‍💻 你

`ctl` 是线程池的**核心控制字段**，一个 `AtomicInteger`（32 位）同时存了两个东西：

```
private final AtomicInteger ctl = new AtomicInteger(ctlOf(RUNNING, 0));

private static final int COUNT_BITS = Integer.SIZE - 3;              // 29
private static final int COUNT_MASK = (1 << COUNT_BITS) - 1;         // 低 29 位全 1

// 5 种状态（高 3 位）
private static final int RUNNING    = -1 << COUNT_BITS;   // 111 000...0
private static final int SHUTDOWN   =  0 << COUNT_BITS;   // 000 000...0
private static final int STOP       =  1 << COUNT_BITS;   // 001 000...0
private static final int TIDYING    =  2 << COUNT_BITS;   // 010 000...0
private static final int TERMINATED =  3 << COUNT_BITS;   // 011 000...0

// 分离
private static int runStateOf(int c)      { return c & ~COUNT_MASK; }  // 取高 3 位
private static int workerCountOf(int c)   { return c &  COUNT_MASK; }  // 取低 29 位
private static int ctlOf(int rs, int wc)  { return rs | wc; }          // 合成
```

为什么这么设计？**一次原子操作同时修改状态和 workerCount**。如果用两个字段，就要加锁或者 CAS 两次，很难保证一致性（想象状态改到 SHUTDOWN 时 workerCount 还在 +1，就乱了）。合成一个 int 之后，一次 `ctl.compareAndSet(...)` 就能同时改这两件事。

陷阱 状态值大小关系：`RUNNING < SHUTDOWN < STOP < TIDYING < TERMINATED`（因为 RUNNING 是 `-1 << 29`，是*负数*，最小）。所以源码里判断「是否 RUNNING」只需 `c < SHUTDOWN`，判断「是否已 STOP 及之后」用 `c >= STOP`，位运算加数值比较双管齐下，非常精妙。

追问 低 29 位存 workerCount 够用吗？

够。29 位能表示 `2²⁹ - 1 ≈ 5.36 亿` 个线程，远超任何真实场景（能开几万个线程 OS 就崩了）。JDK 注释里也提到「如果未来真的需要更多线程，可以扩展 `ctl` 到 `AtomicLong`」，暂时没这个需求。

## 面试场景 6：线程池的 5 种状态转换

🎤 面试官

线程池有几种状态？之间怎么转换？

🧑‍💻 你

状态值含义如何进入

`RUNNING`-1接受新任务，处理队列任务构造完就是这个状态
`SHUTDOWN`0**不接新任务**，但处理完队列已有任务调用 `shutdown()`
`STOP`1不接新任务、**不处理队列**、中断正在跑的调用 `shutdownNow()`
`TIDYING`2所有任务已终止，workerCount = 0，准备执行 `terminated()` 钩子SHUTDOWN 且队列/工作线程都空；或 STOP 且工作线程为 0
`TERMINATED`3钩子 `terminated()` 执行完毕，线程池彻底结束TIDYING 状态下 `terminated()` 调用完

转换图：

```
shutdown()
RUNNING ─────────────────► SHUTDOWN
│                          │
│ shutdownNow()             │ 队列空 & workerCount=0
│                          ▼
└──────────► STOP ─────► TIDYING
│ terminated() 执行完
▼
TERMINATED
```

追问 线程池怎么优雅关闭？

标准三步走：**(1) `shutdown()`** 切换到 SHUTDOWN 状态，不再接受新任务，但队列里的存量任务会跑完；**(2) `awaitTermination(timeout, unit)`** 阻塞等待一段合理时间（比如 30s），让队列任务有机会自然结束；**(3) 如果超时仍没完，`shutdownNow()`** 切换到 STOP，中断所有正在跑的线程并返回队列里没执行的任务列表，交给上层处理（重试或落库）。这套流程在 Spring 的 `DisposableBean.destroy()` 里非常常见。

追问 `shutdown()` 和 `shutdownNow()` 具体区别？

三点：**(1) 状态不同** —— 前者进 SHUTDOWN，后者进 STOP；**(2) 队列处理不同** —— 前者队列任务会跑完，后者队列被清空且返回 `List<Runnable>`；**(3) 中断不同** —— 前者只中断空闲 worker，正在执行的任务能跑完，后者对*所有* worker 调 `interrupt()`（但注意：中断只是发信号，任务本身如果没检查 `isInterrupted()` 或没抛 `InterruptedException`，还是会继续跑）。

## 面试场景 7：Worker 是什么？为什么继承 AQS 而且不可重入？

🎤 面试官

线程池里的 `Worker` 内部类了解吗？它为什么要继承 `AQS`？

🧑‍💻 你

`Worker` 是线程池里**工作线程的封装**，每个 Worker 里持有一个 `Thread thread`（就是真正干活的 OS 线程）和一个 `Runnable firstTask`（第一个任务）。它的生命周期就是 `runWorker()` 里的 while 循环：不停从 `workQueue` 里 `getTask()`，拿到就执行，拿不到就退出。

它继承 `AbstractQueuedSynchronizer`（AQS，见 ）实现了一个**不可重入的独占锁**，用 `state = 0/1` 表示*是否正在执行任务*：

```
private final class Worker
extends AbstractQueuedSynchronizer implements Runnable {

// state = -1 初始化中（禁止中断）
// state = 0  空闲，可以被中断（shutdown 时会中断它）
// state = 1  正在执行任务，不能被中断（防止 shutdown 打断业务）

protected boolean isHeldExclusively() { return getState() != 0; }

protected boolean tryAcquire(int unused) {
if (compareAndSetState(0, 1)) {   // CAS 0→1，抢到就锁定
setExclusiveOwnerThread(Thread.currentThread());
return true;
}
return false;  // 不允许重入
}
}
```

关键流程：`runWorker()` 里每次从队列拿到任务后 `w.lock()`（state 0→1），任务执行完 `w.unlock()`（state 1→0）。而 `shutdown()` 会遍历所有 Worker，对每个调用 `tryLock()`：*能拿到锁的说明它空闲，直接 interrupt；拿不到锁的说明它正在跑任务，不打断*。这就完美实现了「优雅关闭」—— 空闲的立刻走，正在干活的干完再走。

追问 为什么故意做成不可重入？

核心是**防止 `shutdown` 时线程正在跑任务被误中断**。假设 Worker 可重入，那当 `runWorker` 里正在执行业务任务 A（已经持锁），业务代码里如果调用了任何又需要抢这把锁的操作（比如 `setCorePoolSize()` 里会加 `mainLock`），就可能*递归拿到同一把 Worker 锁*，这时候 `shutdown` 的 `tryLock` 判定会失效。做成不可重入之后，任务执行期间锁被独占，任何嵌套操作都拿不到，语义就干净了：**「锁被持有 = 正在执行业务任务，不许打断」**。

追问 Worker 的 state 初始化时为什么是 -1？

为了**禁止刚创建还没启动的 Worker 被 shutdown 中断**。构造函数里 `setState(-1)`，此时 `tryLock` 会失败（因为它期望的是 0→1），`shutdown` 的中断逻辑就跳过这个 Worker。等 `runWorker` 开始跑，第一步就是 `w.unlock()`（其实是把 state 从 -1 强制刷成 0），这时候才允许被中断。这个小细节避免了「Worker 刚 new 出来 thread 还没 start，就被 shutdown 打了 interrupt」的时序问题。

## 面试场景 8：execute vs submit 的区别

🎤 面试官

`execute` 和 `submit` 有什么区别？

🧑‍💻 你

维度`execute``submit`

定义在`Executor` 接口`ExecutorService` 接口
参数只接 `Runnable`接 `Runnable` 或 `Callable<T>`
返回值void`Future<T>`
异常处理抛到 `UncaughtExceptionHandler` 或 `System.err`被 `FutureTask` 吞掉，`Future.get()` 时抛 `ExecutionException`
典型场景不关心结果的 fire-and-forget需要结果 / 需要抓异常

底层其实是同一套 —— `submit` 会把 `Runnable/Callable` 包装成 `FutureTask`，然后调 `execute(futureTask)`。所以说 `submit` = `execute` + `Future`。

追问 用 submit 提交，任务抛异常了但我没 `Future.get()`，会怎样？

**异常被静默吞掉**，你永远不会知道。因为 `FutureTask.run()` 会 catch 住任何 Throwable 存进 `outcome` 字段，只有 `get()` 时才会包装成 `ExecutionException` 抛出来。这是 `submit` 最坑的地方 —— 生产环境用 `submit` 却不 `get`，一旦业务代码有 NPE，日志里干干净净什么都没有，业务默默失败你还以为一切正常。**解决办法**：要么老老实实 `get`，要么用 `CompletableFuture` 挂 `exceptionally`，要么改用 `execute` 让异常暴露出来。

## 面试场景 9：线程池里的任务异常怎么处理？

🎤 面试官

接着上一题，那 `execute` 提交的任务里抛异常呢？

🧑‍💻 你

分三个层级处理，按优先级从高到低：

1. **任务内部 `try/catch`**：最推荐。任务内自己 catch 记录日志、上报监控，最可控。

2. **ThreadFactory 里给线程挂 `UncaughtExceptionHandler`**：兜底方案。线程栈上的异常一路上抛没被 catch 时会走这里。

3. **啥都不做**：JVM 默认行为 —— 异常打印到 `System.err`，*当前 Worker 线程直接死亡*，然后线程池会 `replaceWorker` 补一个新的。功能上不影响，但 *日志里可能什么都没有*（如果 System.err 没接到日志系统）。

关键源码 `runWorker`：

```
try {
task.run();
afterExecute(task, null);
} catch (Throwable ex) {
thrown = ex;
throw new Error(ex);   // 让异常一路上抛
} finally {
...
}
// 上抛后 → 线程栈顶 → UncaughtExceptionHandler → 若没设则 System.err
```

追问 那 submit 里怎么让异常不被静默吞？

三种方式：**(1) 提交时保存 Future 引用，稍后 `future.get()`**—— get 会把异常包成 `ExecutionException` 抛出；**(2) 重写 `ThreadPoolExecutor.afterExecute(Runnable r, Throwable t)`**—— 对 `FutureTask` 类型的任务，可以调 `((Future<?>) r).get()` 反射出异常；**(3) 直接改用 `CompletableFuture.supplyAsync(task, pool).exceptionally(...)`**—— 现代 Java 更推荐这套。

## 面试场景 10：Executors 工厂方法为什么阿里禁用？⭐

🎤 面试官

《阿里 Java 开发手册》强制不允许用 `Executors` 创建线程池，为什么？

🧑‍💻 你

因为 `Executors` 四个便捷方法都有**无界/无上限的隐患**，直接引发 OOM。逐个看：

方法底层参数问题

`newFixedThreadPool(n)`
core = max = n；队列 = `new LinkedBlockingQueue<>()`
**队列无界**（默认容量 `Integer.MAX_VALUE`）；任务堆积到几百万条时堆内存爆炸

`newSingleThreadExecutor()`
core = max = 1；队列同上
同上，队列无界

`newCachedThreadPool()`
core = 0；**max = Integer.MAX_VALUE**；队列 = `SynchronousQueue`；`keepAlive = 60s`
**线程数无上限**；高 QPS 下几秒钟就能开出几万个线程，OS 直接崩

`newScheduledThreadPool(n)`
core = n；**max = Integer.MAX_VALUE**；队列 = `DelayedWorkQueue`（无界）
队列 + 线程数**双重无上限**

正确做法：**直接 `new ThreadPoolExecutor(...)`**，7 个参数*都自己指定*，队列必须有界，maximumPoolSize 必须限制，配合合适的拒绝策略。下一课  讲具体怎么配。

线上事故经典案例 某电商大促，某服务用 `Executors.newCachedThreadPool()` 处理订单异步写库。大促流量到来时，DB 变慢，任务处理跟不上；`SynchronousQueue` 是零容量的直接交付队列，交付不成功就走「创建新线程」分支，而 `maximumPoolSize = Integer.MAX_VALUE`—— 结果几秒内线程数从 100 涨到 3 万+，JVM 直接 `OutOfMemoryError: unable to create native thread`，整个服务雪崩。事后复盘：*如果一开始用 `ThreadPoolExecutor` 限死 max=200 + `CallerRunsPolicy`，就是 DB 慢 + 用户等待，而不是整个服务挂掉*。

追问 `SynchronousQueue` 为什么这么危险？

`SynchronousQueue` 是*零容量*的队列 —— 每个 `put` 必须等一个 `take` 才能成功。所以 `CachedThreadPool` 的策略是：只要没有*空闲线程*正在 take，就必然 offer 失败，然后走「创建新线程」的分支。这就意味着**只要下游变慢一点，线程数就直线上涨**，一点缓冲都没有。它适合的场景是「下游极快，一定拿得走」的中转，不适合真正的削峰。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：观察执行流程 —— 先入队，再扩线程

```
import java.util.concurrent.*;

public class ThreadPoolFlow {
public static void main(String[] args) throws Exception {
// core=2, max=4, 队列容量=2；共可容纳 4 线程 + 2 排队 = 6 个任务
ThreadPoolExecutor pool = new ThreadPoolExecutor(
2, 4, 60L, TimeUnit.SECONDS,
new ArrayBlockingQueue<>(2),
r -> {
Thread t = new Thread(r);
t.setName("demo-" + t.getId());
return t;
},
new ThreadPoolExecutor.AbortPolicy());

for (int i = 1; i <= 7; i++) {
final int id = i;
try {
pool.execute(() -> {
System.out.printf("task-%d run on %s | active=%d queue=%d%n",
id, Thread.currentThread().getName(),
pool.getActiveCount(), pool.getQueue().size());
try { Thread.sleep(2000); } catch (InterruptedException e) {}
});
System.out.printf("submit task-%d OK, pool=%d queue=%d%n",
id, pool.getPoolSize(), pool.getQueue().size());
} catch (RejectedExecutionException e) {
System.out.printf("submit task-%d REJECTED%n", id);
}
}
pool.shutdown();
}
}
// 观察点：
// task-1、task-2 直接创建核心线程执行；
// task-3、task-4 入队；
// task-5、task-6 队列满，扩到非核心线程；
// task-7 被 AbortPolicy 拒绝抛异常。
```

### 验证 2：4 种拒绝策略对比

```
import java.util.concurrent.*;

public class RejectPolicyDemo {
public static void main(String[] args) throws Exception {
// 用不同的 handler 分别跑一遍，观察输出
run(new ThreadPoolExecutor.AbortPolicy(),         "Abort");
run(new ThreadPoolExecutor.CallerRunsPolicy(),    "CallerRuns");
run(new ThreadPoolExecutor.DiscardPolicy(),       "Discard");
run(new ThreadPoolExecutor.DiscardOldestPolicy(), "DiscardOldest");
}

static void run(RejectedExecutionHandler h, String tag) throws Exception {
ThreadPoolExecutor pool = new ThreadPoolExecutor(
1, 1, 0L, TimeUnit.MILLISECONDS,
new ArrayBlockingQueue<>(1), h);

System.out.println("--- policy=" + tag + " ---");
for (int i = 1; i <= 4; i++) {
final int id = i;
try {
pool.execute(() -> {
System.out.printf("  [%s] run task-%d on %s%n",
tag, id, Thread.currentThread().getName());
try { Thread.sleep(500); } catch (InterruptedException ignore) {}
});
System.out.printf("  [%s] submit task-%d OK%n", tag, id);
} catch (RejectedExecutionException e) {
System.out.printf("  [%s] submit task-%d threw REJECT%n", tag, id);
}
}
pool.shutdown();
pool.awaitTermination(5, TimeUnit.SECONDS);
}
}
// 观察：
// Abort         → 后面几个任务直接抛 RejectedExecutionException
// CallerRuns    → 主线程 main 亲自执行了被拒的任务
// Discard       → 被拒任务静默消失，不报错
// DiscardOldest → 队列头老任务被丢，新任务塞进去
```

### 验证 3：submit 静默吞异常的坑

```
import java.util.concurrent.*;

public class SubmitSwallowsException {
public static void main(String[] args) throws Exception {
ExecutorService pool = Executors.newSingleThreadExecutor();

// ① 用 execute：异常会打印到 System.err
pool.execute(() -> {
System.out.println("execute task run");
throw new RuntimeException("boom-from-execute");
});

Thread.sleep(200);

// ② 用 submit 但不 get：异常被吞
pool.submit(() -> {
System.out.println("submit task run");
throw new RuntimeException("boom-from-submit-silent");
});

Thread.sleep(200);

// ③ 用 submit 并 get：异常在 get 时抛出
Future<?> f = pool.submit(() -> {
System.out.println("submit task with get run");
throw new RuntimeException("boom-from-submit-with-get");
});
try {
f.get();
} catch (ExecutionException e) {
System.out.println("caught: " + e.getCause().getMessage());
}

pool.shutdown();
}
}
// 观察：
// ① 会看到红色的异常堆栈
// ② 静悄悄，没有任何输出 —— 生产环境这就是 bug 隐身的原因！
// ③ 显式抛出 boom-from-submit-with-get
```

### 验证 4：Executors.newCachedThreadPool 的线程爆炸

```
import java.util.concurrent.*;

public class CachedPoolExplode {
public static void main(String[] args) throws Exception {
ExecutorService pool = Executors.newCachedThreadPool();
ThreadPoolExecutor tpe = (ThreadPoolExecutor) pool;

// 模拟下游变慢：每个任务睡 30s
for (int i = 1; i <= 5000; i++) {
pool.execute(() -> {
try { Thread.sleep(30000); } catch (InterruptedException ignore) {}
});
if (i % 500 == 0) {
System.out.printf("submitted=%d, poolSize=%d, active=%d%n",
i, tpe.getPoolSize(), tpe.getActiveCount());
}
}
// 结局大概率：
// java.lang.OutOfMemoryError: unable to create native thread
// 因为线程数一直在涨，OS 已经不给你分配更多线程
pool.shutdown();
}
}
// ⚠️ 这段代码请在有充足 swap 的机器上跑，且随时准备 kill -9
// 目的是让你直观感受到 CachedThreadPool 的失控
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 手写 `ThreadPoolExecutor` 的 7 个参数和它们的作用。</summary>

`corePoolSize`（常驻线程数）、`maximumPoolSize`（最大线程数）、`keepAliveTime`+`TimeUnit`（非核心线程空闲超时回收时长）、`BlockingQueue<Runnable>`（等待队列）、`ThreadFactory`（线程工厂，给线程命名）、`RejectedExecutionHandler`（拒绝策略）。

</details>

<details>

<summary>Q2 描述 `execute(task)` 的完整决策路径。</summary>

① workerCount < corePoolSize → 创建核心线程；② 否则 offer 到 workQueue，成功则等待被消费；③ 队列满且 workerCount < maximumPoolSize → 创建非核心线程；④ 都不行 → 触发拒绝策略。关键：优先入队而非扩线程。

</details>

<details>

<summary>Q3 ctl 字段的位分布是什么？为什么这样设计？</summary>

高 3 位存线程池状态（5 种），低 29 位存 workerCount。设计目的是**一次 CAS 同时修改状态和线程数**，保证状态转换和线程计数的原子一致性 —— 若分成两个字段，两次 CAS 之间的中间态会导致并发混乱。

</details>

<details>

<summary>Q4 Worker 为什么要继承 AQS 而且是不可重入的？</summary>

继承 AQS 是为了用 `state = 0/1` 表示「是否正在执行任务」；`shutdown()` 遍历所有 Worker `tryLock()`，能拿到（state=0）说明空闲可中断，拿不到（state=1）说明正在跑任务，不打断。**不可重入**是故意的：防止业务代码嵌套调用意外拿到 Worker 锁，导致「正在执行」的语义失效。

</details>

<details>

<summary>Q5 为什么阿里禁用 Executors 的 4 个工厂方法？</summary>

`newFixedThreadPool` 和 `newSingleThreadExecutor` 用无界 `LinkedBlockingQueue`（默认容量 `Integer.MAX_VALUE`），任务堆积 OOM；`newCachedThreadPool` 和 `newScheduledThreadPool` 的 `maximumPoolSize = Integer.MAX_VALUE`，线程数无上限，高并发下会 `unable to create native thread`。生产必须用 `new ThreadPoolExecutor(...)` 显式指定所有参数并有界。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.util.concurrent.ThreadPoolExecutor` —— 参数、状态转换权威文档

- `ThreadPoolExecutor.java` 源码 —— ctl、Worker、runWorker 都在这一个文件里，2000 行左右

#### 🔗 关联课件

- （上一课）

-

-

-

#### 🧭 下一课预告

Lesson 0027：**线程池最佳实践 & 参数调优** —— 核心线程数怎么算（CPU 密集 vs IO 密集）、队列大小怎么定、生产事故案例、动态调参（美团 DynamicTp）、Spring 的 `@Async` 默认池的坑。

💬 有任何疑问 —— 「ctl 的位运算再讲讲？」「Worker 的 state -1 是什么魔法？」「面试真的会问 runWorker 源码吗？」—— 直接问我。我是你的老师，也是你的追问陪练。


