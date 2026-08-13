> Lesson 0029 · 阶段三 · 并发编程（收尾） · ⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 处追问

# 0029 · 虚拟线程（Project Loom）

从 **JDK 21 GA** 起，虚拟线程（*Virtual Thread*）正式脱离预览成为标准特性（JEP 444）。它是 *Project Loom* 五年打磨的成果，也是并发编程 20 年来最大的一次范式转变 —— **让「阻塞代码写起来跟同步一样，性能却像异步」**。这一课是*阶段三 · 并发编程*的收尾课，把前面 11 课（、、、……）串成一条历史线：*OS 线程 → 线程池 → CompletableFuture → 虚拟线程*。

面试考察度正在急剧上升 —— 2024 年后大厂 Java 岗几乎必问「知不知道虚拟线程？」「跟线程池什么关系？」「pinning 是什么？」。这一课我们把这些高频题一次讲透。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 虚拟线程和平台线程是什么关系？是替代？还是共存？</summary>

**共存 + 承载**。虚拟线程运行时需要「挂载 mount」到一个平台线程（叫 *carrier thread 载体线程*）上执行；阻塞时会「卸载 unmount」，载体线程去跑其他虚拟线程。所以虚拟线程不是替代平台线程，而是**用少量平台线程承载海量虚拟线程**。面试场景 1、5 展开。

</details>

<details>

<summary>Q0.2 既然虚拟线程这么便宜，那我把它们放进 `ThreadPoolExecutor` 池化管理，性能会更好吗？</summary>

**不会，反而更差**。池化的意义是*复用昂贵资源*；虚拟线程本身就是「用完即弃」的廉价品，池化反而限制并发数。正确姿势是 `Executors.newVirtualThreadPerTaskExecutor()`——「每个任务一个虚拟线程」。面试场景 7 展开。

</details>

## 面试场景 1：什么是虚拟线程？（★核心）

🎤 面试官

虚拟线程是 JDK 21 新加的特性，你能讲讲它是什么吗？

🧑‍💻 你

虚拟线程是 **JVM 层调度的用户态轻量线程**，由 JEP 444 在 JDK 21 GA 正式落地，属于 *Project Loom* 项目的核心产物。

三个关键点：

- **不由 OS 调度**：传统 `java.lang.Thread` 是「1:1 映射到 OS 内核线程」的重量级对象；虚拟线程是纯 Java 对象，调度权在 JVM 手里。

- **由载体线程承载**：JVM 内置一个 `ForkJoinPool` 作为「载体线程池 carrier pool」，虚拟线程运行时会 *mount*（挂载）到某个载体线程上占用 CPU；阻塞时 *unmount*（卸载）让出载体。

- **数量可达几百万**：一个虚拟线程栈只有几百字节到几 KB（存在堆上，按需扩缩），一个平台线程栈默认 1 MB。同样内存下虚拟线程数是平台线程的 *数千倍*。

官方类比：*操作系统把虚拟内存映射到物理内存，JVM 把大量虚拟线程映射到少量平台线程*。

追问 虚拟线程的栈保存在哪？跟平台线程有什么不同？

虚拟线程的栈以 **Continuation 对象** 的形式保存在**堆上**（GC 可回收），按方法调用深度*按需扩缩容*。平台线程的栈是在创建时由 OS 一次性分配的一大块虚拟内存（默认 `-Xss1m`），固定大小、不会缩。这就是虚拟线程能同时跑百万级的根本原因 —— **栈是「用多少占多少」而不是「预留 1 MB 无论用不用」**。

## 面试场景 2：虚拟线程 vs 平台线程（★核心）

🎤 面试官

虚拟线程和普通的（平台）线程有什么区别？各自的极限在哪？

维度平台线程 Platform Thread虚拟线程 Virtual Thread

调度者OS 内核（内核态切换）JVM（用户态切换）
与 OS 线程关系1:1 绑定M:N（大量虚拟：少量载体）
栈内存固定 ~1 MB（`-Xss`）几百字节起，按需扩，存堆上
创建开销毫秒级（涉及系统调用）微秒级（就是分配一个 Java 对象）
切换开销1-10 μs（内核态陷入）~100 ns（纯用户态）
数量上限几千（受栈内存 + OS 限制）百万级（受堆内存）
阻塞 IO 的代价整个 OS 线程闲置只是 Continuation 挂起，载体去跑别人
适合场景CPU 密集、需要控制并发数IO 密集、Thread-per-Request 模型
ThreadLocal正常使用可用但要小心内存激增（数量大）
`Thread` API完全兼容完全兼容（*就是 `Thread` 子类*）

追问 虚拟线程也是 `java.lang.Thread` 吗？

**是的**。`Thread.ofVirtual().start(r)` 返回的对象是 `Thread` 的子类（内部叫 `VirtualThread`）。所以旧 API 全兼容：`Thread.currentThread()`、`Thread.sleep()`、`interrupt()`、`join()` 都能用。区别只是*调度机制*不同，用 `Thread.isVirtual()` 可以判断。

## 面试场景 3：虚拟线程解决的是什么历史问题？（★核心）

🎤 面试官

Java 有 `Executors`、有 `CompletableFuture`、有 Netty，为什么还需要虚拟线程？

🧑‍💻 你

关键词是 *Thread-per-Request*（每请求一线程）模型：

传统 Web 服务（Tomcat、Spring MVC）的处理模型是「一个请求进来，占一个线程一直干到响应回去」。请求里通常包含 DB 查询、RPC 调用、缓存访问 —— 这些都是 **IO 阻塞**。阻塞期间 OS 线程*什么都不做但仍然占着 1 MB 栈*。

于是形成了矛盾三角：

- 想扛高 QPS → 需要开大线程池 → OS 线程有几千的上限 → 扛不动百万连接。

- 改用异步（CompletableFuture / Netty） → 性能高 → 但代码变成回调地狱、debug 极难、异常处理反人类。

- 业务开发者只想「顺序写业务」，却被架构逼着学异步。

虚拟线程解决的正是这个矛盾：**写同步代码，享受异步性能**。IO 阻塞时 JVM 悄悄把虚拟线程从载体上摘走，载体去跑别的虚拟线程；IO 就绪时再把虚拟线程挂回来。整个过程对业务代码*完全透明*。

追问 Netty 在 JDK 21 之后还有必要吗？

**还需要**，但地位在变。Netty 擅长的是*网络协议栈层面*的事：零拷贝、epoll 事件循环、精细的内存池、TCP/HTTP2 编解码 —— 这些虚拟线程替代不了。但*业务处理层*的 handler 可以简化到直接用虚拟线程同步写 —— 不再需要 `CompletableFuture.thenCompose` 那种链式回调。所以未来是**「Netty 做网络 + 虚拟线程写业务」**的组合。

## 面试场景 4：虚拟线程有哪几种创建方式？

🧑‍💻 你

JDK 21 提供了四种创建方式，从简到全：

```
// 1. 最简：一行启动一个虚拟线程
Thread.startVirtualThread(() -> log("hi from " + Thread.currentThread()));

// 2. Builder 模式：可命名、可配 daemon、可拿到未启动的 Thread
Thread t = Thread.ofVirtual()
.name("worker-", 0)      // 前缀 + 起始编号
.start(runnable);

// 3. ThreadFactory：给框架/线程池用
ThreadFactory vtf = Thread.ofVirtual().factory();
Thread t2 = vtf.newThread(runnable);

// 4. Executor（业界最常用）：每个任务一个虚拟线程
try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {
for (int i = 0; i < 10_000; i++) {
int id = i;
exec.submit(() -> handleRequest(id));
}
} // try-with-resources 自动 shutdown + await
```

注意第 4 种：`newVirtualThreadPerTaskExecutor` 里的*「per task」*就是关键 —— **每个任务都新起一个虚拟线程，用完即弃，绝不复用**。这跟 `newFixedThreadPool` 完全相反。

追问 平台线程也有 Builder 吗？

有。`Thread.ofPlatform().name(...).daemon(true).start(r)` 就是新版的平台线程 Builder。旧的 `new Thread(r)` 依然能用（且默认就是平台线程）。这个新 API 主要是为了跟 `Thread.ofVirtual()` 对称，让代码可读性更好。

## 面试场景 5：虚拟线程的调度模型是怎样的？

🎤 面试官

虚拟线程是「用户态调度」，那具体是谁在调度？调度算法是什么？

🧑‍💻 你

调度器是 JVM 内置的一个 **`ForkJoinPool`**，并行度默认等于 `Runtime.getRuntime().availableProcessors()`，可以用 `-Djdk.virtualThreadScheduler.parallelism=N` 覆盖。它使用 *work-stealing* 算法，跟并行流用的 common pool 是同一套底层。

```
┌───────────────────────────────────────────────────────────┐
│  虚拟线程（可能百万个）                                     │
│  VT#1  VT#2  VT#3  ...  VT#999_999                        │
└─────────────────┬─────────────────────────────────────────┘
│ mount / unmount
▼
┌───────────────────────────────────────────────────────────┐
│  载体线程池 (ForkJoinPool，通常 = CPU 核数)                 │
│  Carrier#0   Carrier#1   Carrier#2   Carrier#3            │
└─────────────────┬─────────────────────────────────────────┘
│ 1:1
▼
OS 内核线程
```

核心动作是 **mount / unmount**：

1. **mount**：调度器挑一个 idle 的 carrier，把虚拟线程的 *Continuation*（保存的栈帧）恢复到 carrier 上执行。

2. 虚拟线程一直跑到 **遇到阻塞点**（`Thread.sleep`、`Socket.read`、`CompletableFuture.get` 等被 JDK 改造过的方法）。

3. **unmount**：JVM 把当前栈帧 *freeze* 成 Continuation 放回堆里，carrier 立即空闲、去跑下一个 mount。

4. IO 就绪时（epoll 通知）由调度器再挑一个 carrier 把虚拟线程 mount 回来 —— *不一定是原来的 carrier*。

追问 `Thread.sleep(1000)` 在虚拟线程里是什么行为？会占用载体吗？

**不占用载体**。JDK 21 已经把 `Thread.sleep` 改造成「先 unmount，然后向 JVM 定时器注册一个 1 秒后的唤醒回调，1 秒到再 mount 回去」。所以你可以放心 `Thread.sleep(3600_000)`，10 万个虚拟线程一起睡也不会消耗任何载体资源。*这和平台线程完全不同* —— 平台线程 sleep 时那个 OS 线程会真的被 park，资源仍然占着。

## 面试场景 6：pinning 陷阱（★经典）

🎤 面试官

虚拟线程有个叫 pinning 的问题你听说过吗？

🧑‍💻 你

**Pinning（钉住）**是虚拟线程当前最重要的性能陷阱 —— 某些场景虚拟线程*无法 unmount*，被强行「钉在」载体上直到执行完，退化成普通的平台线程行为。

JDK 21 中两个主要 pinning 场景：

1. **`synchronized` 块内部阻塞**：进入 `synchronized` 后，虚拟线程和载体线程绑定；如果块内又调用了 `Thread.sleep`、`IO`、`await()` 等阻塞操作，虚拟线程无法卸载，*载体也被占着*。

2. **native 方法执行期间**：JNI 调用中的栈帧不受 JVM 控制，无法 freeze 成 Continuation，因此必然 pin。

危害：如果高并发场景下大量虚拟线程 pin 住载体，载体池被打满，虚拟线程调度就失效了 —— 相当于回到线程池上限。

解决方案：

- 把 `synchronized` 换成 `ReentrantLock`。`ReentrantLock` 基于  纯 Java 实现，park 时会走虚拟线程感知的 `LockSupport.park`，能正常 unmount。

- 用 `-Djdk.tracePinnedThreads=short|full` 在启动参数里开启诊断，运行时 pinning 会打印堆栈。

- **JDK 24（JEP 491）**已经解决了 `synchronized` pinning 问题 —— `synchronized` 阻塞时也能 unmount。所以未来这个坑会消失，但 **native 方法 pinning 是永远无法解** 的。

追问 pinning 到底是怎么发生的？为什么 `synchronized` 会 pin 而 `ReentrantLock` 不会？

**底层原因是 monitor 的实现**。`synchronized` 依赖 JVM 层的 *object monitor*，monitor 持有者被记录成「某个 OS 线程 ID」。如果这时把虚拟线程从载体上摘走，切换到另一个载体继续，OS 线程 ID 就变了 —— monitor 的持有者信息就错乱了（*可重入计数、等待队列都基于 OS 线程*）。所以 JVM 干脆禁止在 `synchronized` 内部 unmount。`ReentrantLock` 完全是 Java 层实现（ 队列 + `LockSupport.park`），持有者记录的是 `Thread` 对象引用而不是 OS 线程 ID，虚拟线程切换载体不会影响它。JDK 24 通过重新设计 monitor 才把这个历史包袱解掉。

## 面试场景 7：虚拟线程 vs 线程池（不要池化！）

🎤 面试官

那我把虚拟线程放进 `ThreadPoolExecutor`，是不是就能既复用又不阻塞了？

🧑‍💻 你

**大错特错**。虚拟线程*不需要池化*，也*不应该池化*。原因有三：

1. **创建成本已经忽略不计**：池化的初衷是「线程创建太贵，复用一下」。虚拟线程创建 ≈ new 一个 Java 对象，几百纳秒，池化省不了什么。

2. **池化会强行限制并发**：`newFixedThreadPool(200)` 意味着同时最多 200 个任务在跑；但虚拟线程的强项就是「让 100 万个任务同时挂起等 IO」。池化把这个优势砍没了。

3. **ThreadLocal 语义会错乱**：`ThreadLocal` 绑定的是*虚拟线程*本身。如果虚拟线程被复用（池化的核心），ThreadLocal 里上个任务的脏数据可能泄露给下个任务。

正确姿势：`Executors.newVirtualThreadPerTaskExecutor()` —— 每个任务新建一个虚拟线程，任务结束虚拟线程即被 GC。

陷阱 **不要用「虚拟线程 + `Semaphore`」土制线程池**。如果你的目的是限流下游（如控制 DB 连接池并发），*该限流的是下游资源本身*（用 HikariCP 的 `maximumPoolSize`、用 `Semaphore` 保护稀缺资源），而不是限制虚拟线程数量。虚拟线程应该「随便开」，让它们排队等下游资源就行。

## 面试场景 8：ThreadLocal 在虚拟线程里怎么办？ScopedValue 是什么？

🎤 面试官

虚拟线程数量可以到百万级，那 `ThreadLocal` 存的东西不是会撑爆内存？

🧑‍💻 你

确实是隐患。`ThreadLocal` 存储的对象数量正比于线程数量，虚拟线程从几千飙到几十万时，全局的 `ThreadLocal` 存储可能爆炸。

官方给了三条建议：

- **能不用就不用**：审计代码里的 `ThreadLocal`，尤其是 MDC、事务上下文、缓存对象。

- **必须用就用 `ThreadLocal` 而不是 `InheritableThreadLocal`**：后者会在虚拟线程创建时复制，代价高。

- **用 JEP 446/464 的 `ScopedValue` 替代（JDK 21 预览，JDK 25 正式）**。

```
// 传统 ThreadLocal
static final ThreadLocal<User> CURRENT_USER = new ThreadLocal<>();
CURRENT_USER.set(user);         // 可能被子代码覆盖，泄漏风险
try { handle(); }
finally { CURRENT_USER.remove(); }

// 新的 ScopedValue（结构化 + 不可变 + 显式作用域）
static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();
ScopedValue.where(CURRENT_USER, user).run(() -> handle());
// 作用域外自动清理，不可能忘记 remove()
```

ScopedValue 的优势：

- **不可变**：一旦 bind 后子代码只能读不能改，杜绝「隐式修改上下文」的 bug。

- **作用域明确**：Lambda 结束值就消失，不需要手动 `remove()`。

- **更省内存**：不需要每个线程一份 `ThreadLocalMap`，用一种类似「继承链」的机制存储。

- **与结构化并发（Structured Concurrency）配合**：子任务能自动继承 ScopedValue，无需 `InheritableThreadLocal` 的复制开销。

追问 我用了 SLF4J 的 MDC 做日志链路追踪，虚拟线程下会有问题吗？

会。MDC 底层就是 `ThreadLocal`。切到虚拟线程后：(1) 数量激增可能撑爆内存；(2) 虚拟线程 unmount 到别的载体上时，MDC 的值会跟着虚拟线程走（因为绑定的是*虚拟线程*，不是 carrier），所以链路追踪逻辑是**正确的**；但如果你把 MDC 值 put 到*载体线程*上（比如某些老中间件的 hack），就会串号。建议升级到支持虚拟线程的日志框架版本（Logback 1.4+、Log4j2 2.20+）。

## 面试场景 9：虚拟线程的适用场景 & 不适用场景

场景类型适合虚拟线程？说明

HTTP 服务处理（Web/RPC）✅ 极其适合Thread-per-Request 模型 + 大量 IO，虚拟线程的最佳战场
DB 查询（JDBC）✅ 适合阻塞式 API 能自然 unmount；注意连接池上限依然是硬约束
下游 RPC 调用✅ 适合大量 HTTP client 并发调用，比 CompletableFuture 编排更简单
爬虫 / 抓取✅ 适合百万虚拟线程同时 hold 连接不再是问题
CPU 密集计算（图像处理、加解密、编解码）❌ 不适合计算不阻塞，虚拟线程没有优势；*还是用 `ForkJoinPool` 或平台线程池*
需要限流的场景⚠️ 需搭配虚拟线程本身不限流；用 `Semaphore` 或下游资源池限
与 `synchronized` 大量交互的老代码⚠️ JDK 21 有 pinning 风险先测试或升级到 JDK 24
持有大量 `ThreadLocal` 数据⚠️ 需谨慎迁移到 `ScopedValue`

追问 Spring Boot 3.2 怎么开启虚拟线程？效果如何？

一行配置：`spring.threads.virtual.enabled=true`。生效后：(1) 内嵌 Tomcat/Jetty/Undertow 的工作线程改成虚拟线程；(2) `@Async` 默认走虚拟线程；(3) `WebFlux` 反而不受影响（它本身是非阻塞的）。实测在*IO 密集*业务下，同样 CPU 能扛的 QPS 提升 3-10 倍，代码零改动。*但一定要审计三点*：老代码里的 `synchronized`、老的连接池上限、大对象 `ThreadLocal`。

## 面试场景 10：虚拟线程会取代线程池吗？

🎤 面试官

那以后是不是就没有 `ThreadPoolExecutor` 什么事了？

🧑‍💻 你

**不会取代**。虚拟线程解决的是*「IO 阻塞时 OS 线程被浪费」*这一个问题；线程池的其他职责它接不下来：

1. **CPU 密集任务**：虚拟线程没优势 —— 这类任务不阻塞，unmount 没意义，反而多了 mount/unmount 开销。*老老实实用平台线程池 + `ForkJoinPool`*。

2. **资源保护 / 限流**：线程池 `corePoolSize` 天然是「并发数上限」的实现。如果你希望「同时只允许 8 个任务操作某个共享文件」，用固定大小的平台线程池最省心。

3. **控制下游 RPS**：调用第三方 API 有 QPS 限制时，需要显式并发上限。虚拟线程配合 `Semaphore` 也行，但线程池语义更清晰。

4. **需要 named / 优先级线程**：某些场景（GC 线程、定时任务）需要绑定 OS 线程属性，只能用平台线程。

未来的正确姿势是**两种模型并存**：IO 任务用虚拟线程（`newVirtualThreadPerTaskExecutor`），CPU / 限流任务用平台线程池（`ThreadPoolExecutor` / `ForkJoinPool`）。

## 💻 代码验证（打开 JDK 21+ 跑一遍）

### 验证 1：100 万虚拟线程同时 sleep（挑战平台线程做不到的事）

```
import java.time.Duration;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

public class MillionVirtualThreads {
public static void main(String[] args) throws Exception {
var counter = new AtomicInteger();
long start = System.currentTimeMillis();

try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {
for (int i = 0; i < 1_000_000; i++) {
exec.submit(() -> {
try {
Thread.sleep(Duration.ofSeconds(2));  // 假装 IO
counter.incrementAndGet();
} catch (InterruptedException ignored) {}
});
}
} // 等所有任务完成再退出

System.out.printf("完成任务数: %d, 耗时: %d ms%n",
counter.get(), System.currentTimeMillis() - start);
}
}
// 输出（16 核机器实测）：
// 完成任务数: 1000000, 耗时: ~5000 ms
// 换成平台线程池：直接 OutOfMemoryError（1M × 1MB stack = 1TB 内存）
```

### 验证 2：识别虚拟线程 vs 平台线程

```
public class WhoAmI {
public static void main(String[] args) throws InterruptedException {
Thread pt = Thread.ofPlatform().name("plat-1").unstarted(WhoAmI::print);
Thread vt = Thread.ofVirtual().name("virt-1").unstarted(WhoAmI::print);
pt.start(); vt.start();
pt.join(); vt.join();
}
static void print() {
Thread t = Thread.currentThread();
System.out.printf("name=%s, isVirtual=%s, class=%s%n",
t.getName(), t.isVirtual(), t.getClass().getName());
}
}
// 输出：
// name=plat-1, isVirtual=false, class=java.lang.Thread
// name=virt-1, isVirtual=true,  class=java.lang.VirtualThread
```

### 验证 3：pinning 诊断（`synchronized` 里做 IO）

```
// 启动参数加：-Djdk.tracePinnedThreads=full
public class PinningDemo {
private static final Object LOCK = new Object();

public static void main(String[] args) throws Exception {
try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {
for (int i = 0; i < 100; i++) {
exec.submit(() -> {
synchronized (LOCK) {           // ← 进入 monitor
try { Thread.sleep(1000); } // ← 阻塞，触发 pinning
catch (InterruptedException e) {}
}
});
}
}
}
}
// 控制台会打印类似：
// Thread[#42,ForkJoinPool-1-worker-1,5,CarrierThreads]
//     java.base/java.lang.VirtualThread$VThreadContinuation.onPinned(...)
//     app//PinningDemo.lambda$main$0(PinningDemo.java:9) <== monitors:1

// 修复：把 synchronized 换成 ReentrantLock
private static final ReentrantLock LOCK = new ReentrantLock();
LOCK.lock();
try { Thread.sleep(1000); } catch (InterruptedException e) {}
finally { LOCK.unlock(); }
// pinning 消失
```

### 验证 4：ScopedValue 用法（JDK 21 预览，用 `--enable-preview`）

```
public class ScopedValueDemo {
static final ScopedValue<String> USER = ScopedValue.newInstance();

public static void main(String[] args) {
ScopedValue.where(USER, "alice").run(() -> {
System.out.println("outer: " + USER.get());   // alice
deeperCall();
});
// 出了 run() 作用域后 USER.get() 会抛异常，无需 remove()
}

static void deeperCall() {
System.out.println("inner: " + USER.get());       // alice（自动继承）
// USER 是不可变的：这里编译期就没有 set() 方法
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 一句话解释虚拟线程和平台线程的关系。</summary>

虚拟线程是 JVM 层调度的用户态轻量线程，运行时会 mount 到平台线程（载体线程）上执行；阻塞时 unmount，释放载体去跑其他虚拟线程。二者是「M:N」承载关系，不是替代关系。

</details>

<details>

<summary>Q2 为什么虚拟线程不需要池化？</summary>

因为虚拟线程创建开销极低（≈ new 一个 Java 对象），池化省不了成本；反而池化会限制并发数、丧失虚拟线程「百万并发」的优势；此外池化复用会让 `ThreadLocal` 语义错乱。正确姿势是 `Executors.newVirtualThreadPerTaskExecutor()`，每任务一虚拟线程。

</details>

<details>

<summary>Q3 什么是 pinning？如何避免？</summary>

Pinning 指虚拟线程无法从载体线程 unmount 的情况，主要发生在 `synchronized` 块内和 native 方法执行时。危害是载体池被占满，虚拟线程调度失效。规避方式：把 `synchronized` 换成 `ReentrantLock`；开启 `-Djdk.tracePinnedThreads=full` 诊断；升级到 JDK 24（JEP 491 已经解决了 `synchronized` pinning）。

</details>

<details>

<summary>Q4 `Thread.sleep(60_000)` 在虚拟线程和平台线程上表现有何不同？</summary>

平台线程：真的 park 掉一个 OS 线程 60 秒，那 1 MB 栈也一直占着。虚拟线程：JVM 会 unmount 虚拟线程、向定时器注册回调，载体线程立即空闲去跑其他虚拟线程；60 秒后再把虚拟线程 mount 回某个载体。所以虚拟线程 sleep 几乎不消耗任何资源。

</details>

<details>

<summary>Q5 CPU 密集任务能不能用虚拟线程加速？</summary>

不能。虚拟线程解决的是 IO 阻塞浪费问题，CPU 密集任务不阻塞、没有 unmount 机会，反而增加了 mount/unmount 开销。CPU 密集应该用 `ForkJoinPool` 或平台线程池，并发数控制在 CPU 核数附近。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JEP 444 · Virtual Threads —— JDK 21 GA 官方规范

- JEP 491 · Synchronize Virtual Threads without Pinning —— JDK 24 修复 pinning

- JEP 464 · Scoped Values (2nd Preview) —— `ThreadLocal` 的现代替代

- Oracle · Virtual Threads Guide —— JDK 官方指南

#### 🔗 关联课件

- （上一课）

- （虚拟线程的历史起点）

- （`ReentrantLock` 为何不 pin）

- ``（为何不能池化虚拟线程）

- （下一课，阶段四起点）

#### 🧭 下一课预告 · 阶段切换

并发编程篇到此收官。**阶段四 · JVM** 正式开启：**Lesson 0030 · JVM 概览 & 面试题总结**—— 先鸟瞰 JVM 内存模型、类加载、GC 三大板块，把后续课要用到的地图先展开，让你带着结构感啃 JVM 硬骨头。

💬 阶段三的并发编程告一段落，你可以把 *0018-0029* 整个串一遍看看：*线程基础 → synchronized → volatile → CAS → 原子类 → AQS → ReentrantLock → ThreadLocal → 线程池 → 并发容器 → 虚拟线程*。这是一条完整的历史演进线。任何一节觉得虚，直接回来问我 —— 我会陪你把每个坑都填实。


