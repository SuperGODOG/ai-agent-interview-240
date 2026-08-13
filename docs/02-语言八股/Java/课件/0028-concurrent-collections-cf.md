> Lesson 0028 · 阶段三 · 并发编程 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 11 个面试场景 · 4 段可跑代码 · 5 道自测

# 0028 · 并发容器全览 & CompletableFuture 异步编程

这一课把  两篇文章合并讲：和。**并发容器**部分是集合章节的重复整理 —— 前面已经深挖过 CHM（0015）和 CoW（0016）以及 `BlockingQueue`，这里做一次「体系化清单」式回顾，把 *ConcurrentSkipListMap* 和 *ConcurrentLinkedQueue* 这两个之前没讲透的成员补上。**CompletableFuture**部分则是异步编程的现代方案 —— Java 8 引入，取代裸 `Future`，是「串多个下游服务」这类聚合场景的必备武器，也是并发面试的高频加分项。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `CopyOnWriteArrayList` 和 `Collections.synchronizedList` 什么场景各自更合适？</summary>

CoW 适合**读远多于写**（配置表、白名单、监听器列表）：读完全无锁；但每次写都要复制整个数组，写多会内存爆炸。`synchronizedList` 适合**读写比接近**的场景：读写都要抢同一把 `Monitor`，但单次操作不用分配新数组。第 3 题会详细展开。

</details>

<details>

<summary>Q0.2 `CompletableFuture.supplyAsync(...)` 不显式传线程池，默认走哪个池？有什么问题？</summary>

默认走 `ForkJoinPool.commonPool()`。三个问题：① 里面的线程是**守护线程**（main 一退出就被杀）；② 线程数是 `CPU-1`，做 IO 密集任务会打满；③ **全局共享** —— 你、Stream 的 parallel、其它库全用同一个池，一个业务卡死会波及所有 CF 使用者。生产环境必须显式传自己的池。第 11 题会详讲。

</details>

## 面试场景 1：JUC 提供了哪些并发容器？

🎤 面试官

`java.util.concurrent` 包里都提供了哪些并发容器？你按类别给我梳理一下。

🧑‍💻 你

按数据结构分五大类：

类别并发容器对应的非线程安全版本典型场景

哈希表`ConcurrentHashMap``HashMap`高并发 K-V 缓存
列表`CopyOnWriteArrayList``ArrayList`读多写少（监听器、白名单）
集合`CopyOnWriteArraySet``HashSet`底层就是 CoWList，去重版
非阻塞队列`ConcurrentLinkedQueue`／`ConcurrentLinkedDeque``LinkedList`高并发无界队列、日志缓冲
阻塞队列`ArrayBlockingQueue`／`LinkedBlockingQueue`／`PriorityBlockingQueue`／`DelayQueue`／`SynchronousQueue`／`LinkedTransferQueue`—生产者消费者、线程池 workQueue
有序 Map/Set`ConcurrentSkipListMap`／`ConcurrentSkipListSet``TreeMap`／`TreeSet`需要有序 + 并发（排行榜、时间窗口）

核心思想：**用更细粒度的锁或 CAS 无锁算法，替代 `Hashtable`／`Collections.synchronizedXxx` 那种「整个对象一把锁」的粗暴同步**，从而在高并发下获得数量级的吞吐提升。

追问 为什么没有 `ConcurrentArrayList`？

因为 `ArrayList` 底层是**连续数组**，一次 `set(i, v)` 只改一个元素，加细粒度锁没有明显收益；`add` 时可能触发扩容 + 整段搬移，天然需要独占。要并发列表只有两条路：① CoW（读无锁，写复制整个数组）② 用 `synchronizedList`（读写都抢同一把锁）。JUC 没做 `ConcurrentArrayList`，是因为这两种方案已经覆盖了「读多写少」和「读写均衡」两个主要场景。

## 面试场景 2：ConcurrentHashMap vs Hashtable vs Collections.synchronizedMap

🎤 面试官

线程安全的 Map 有三种：`Hashtable`、`Collections.synchronizedMap`、`ConcurrentHashMap`，区别是什么？

🧑‍💻 你

维度HashtableCollections.synchronizedMapConcurrentHashMap

锁粒度整个 Hashtable（`synchronized` 方法）整个 Map（内部 `mutex`）JDK7 分段锁 Segment；JDK8 桶头节点 `synchronized` + CAS
并发度1（全表串行）1桶数量（几十到几万）
null key/value不允许取决于底层 Map不允许
迭代fail-fast需要外部加锁弱一致性（不抛 CME，但不保证看到并发的最新修改）
性能差（全表锁）差（全表锁）好（细粒度 + CAS）
推荐已过时只在遗留代码里出现**唯一推荐**

今天写新代码，只有 `ConcurrentHashMap` 一个选项。`Hashtable` 从设计上就是「祖传遗物」，`synchronizedMap` 只在包一个第三方 Map（如 `LinkedHashMap` 需要保持插入顺序）时才用。

追问 ConcurrentHashMap 的 JDK 7 → JDK 8 的锁粒度是如何变化的？

JDK 7 是 **Segment 分段锁**：整个表分成 16 个 `Segment`（继承 `ReentrantLock`），每段一把锁，理论并发度 16。JDK 8 把 `Segment` 去掉了，改成**桶头节点 `synchronized`**：数组的每个桶（bin）就是一把锁；空桶时用 CAS 直接放；有节点时对头节点 `synchronized`。*锁粒度从「1/16 表」变成「1/N 表」*（N 是桶数），并发度大大提升。0015 有 `putVal` 源码级细讲。

## 面试场景 3：CopyOnWriteArrayList vs Vector vs Collections.synchronizedList

🎤 面试官

线程安全 List 的三种做法各自什么场景？

🧑‍💻 你

维度VectorCollections.synchronizedListCopyOnWriteArrayList

同步方式每个方法 `synchronized`内部 `mutex`，方法级同步写时复制 + `ReentrantLock`
读操作加锁加锁**完全无锁**（读当前数组引用）
写操作加锁加锁复制新数组 → 修改 → CAS 替换引用
迭代一致性fail-fast需要外部加锁**快照隔离**（迭代期间数组不变）
内存开销低低高（写时复制整个数组）
典型场景—读写比均衡读远多于写（配置、监听器、白名单）

**CoW 的核心权衡**：用「写时复制的空间成本」换「读的零锁开销」和「迭代的强一致性」。所以写多就废 —— 每 `add` 一个元素就要复制整个数组，10 万元素的 List 加一次要复制 400KB，GC 立刻抖。0016 有 `add` 源码级细讲。

追问 Spring 的 `ApplicationEventMulticaster` 为什么用 `CopyOnWriteArraySet` 存监听器？

因为「注册监听器」是应用启动时的极低频操作（几十次），而「发布事件」是运行期的高频操作（每秒可能几万次）—— 完美的**读多写少**场景。用 CoWSet 让事件分发时完全无锁遍历，加监听器时才复制一次，代价可以忽略。

## 面试场景 4：ConcurrentSkipListMap vs TreeMap + synchronized

🎤 面试官

需要一个「有序 + 线程安全」的 Map，你用什么？为什么不是给 `TreeMap` 加锁？

🧑‍💻 你

用 `ConcurrentSkipListMap`。它底层是**跳表（Skip List）**，不是红黑树。选它而不是「`TreeMap` + 全表锁」的三个理由：

1. **锁粒度更细**：跳表插入/删除只影响链表节点的前驱和后继指针，用 CAS 就能完成，不需要全表锁；红黑树插入可能触发*旋转和变色*，往往波及祖父、叔父等多个节点，加细粒度锁很难。所以 TreeMap 只能整表 `synchronized`，并发度=1。

2. **时间复杂度相同**：跳表查/插/删都是 O(log n)，和红黑树一样。多层链表 + 概率抛硬币决定节点层高，期望复杂度稳定。

3. **实现更简单**：跳表就是「多层链表」，代码几百行；红黑树颜色反转的边界条件极多，做并发红黑树几乎是学术难题（`ConcurrentSkipListMap` 作者 Doug Lea 本人就说过）。

典型场景：**时间窗口聚合、排行榜、按分数排序的排队队列** —— 需要按 key 有序遍历，同时多线程读写。

追问 ConcurrentSkipListMap 的插入是几阶复杂度？多线程扩展性好在哪？

期望 **O(log n)**。跳表节点分层，最下层是完整链表，往上每层节点数期望减半。查找从最高层往下走，每层平摊 O(1)，共 O(log n) 层。插入时先 O(log n) 定位，再**用 CAS 修改前驱节点的 `next` 指针** —— 每个 CAS 只影响一对相邻节点，多线程只有*操作到相邻位置*才会冲突，其它位置完全并行。相比之下 TreeMap 一次插入可能引发从叶到根的旋转，要锁住整棵子树，扩展性差得多。

## 面试场景 5：ConcurrentLinkedQueue —— 无锁队列 vs 阻塞队列

🎤 面试官

`ConcurrentLinkedQueue` 和 `BlockingQueue` 有什么区别？什么时候用哪个？

🧑‍💻 你

维度ConcurrentLinkedQueueBlockingQueue（如 `LinkedBlockingQueue`）

底层同步**CAS 无锁**（Michael-Scott 算法）`ReentrantLock` + `Condition`
空/满时的行为`poll()` 返回 `null`，`offer()` 永远成功（无界）可阻塞：`take()`／`put()`
是否支持容量限制不支持（无界）支持
适用场景生产者消费者速率相近，不需要背压需要背压、限流、生产者消费者速率不匹配
性能特点无锁 → 高并发下吞吐极高有锁 → 但阻塞语义省 CPU（不用忙轮询）

选型口诀：**「要背压/限流选 BlockingQueue，要极致吞吐选 ConcurrentLinkedQueue」**。线程池的 `workQueue` 之所以用 `BlockingQueue`，就是因为需要「队列满时让提交者等」这个语义 —— 无锁队列做不到。

追问 Michael-Scott 无锁队列的核心思想是什么？为什么需要维护 `head` 和 `tail` 两个指针？

Michael-Scott 队列是 1996 年提出的经典无锁队列算法。核心是**把入队和出队解耦**：`head` 指向队头哨兵节点（出队用），`tail` 指向队尾（入队用）。入队时 CAS 修改 `tail.next`；出队时 CAS 修改 `head`。*关键难点*是 `tail` 可能「滞后」—— 一个线程入队 CAS 了 `tail.next` 但还没来得及推进 `tail`，此时其它线程能通过检查 `tail.next != null` 帮忙推进（这叫「helping 机制」）。这就是无锁队列的精髓：**失败线程帮成功线程完成收尾**，保证整体永不阻塞。

追问 BlockingQueue 有几种主要实现？各自差别？

六种，面试常问前三种：

- `ArrayBlockingQueue`：**数组 + 有界**，一把 `ReentrantLock`（读写共用），支持公平锁。

- `LinkedBlockingQueue`：**链表 + 可指定容量（默认 `Integer.MAX_VALUE` 近似无界）**，*两把锁*（putLock/takeLock），读写可并行，吞吐比 `ArrayBlockingQueue` 高。

- `PriorityBlockingQueue`：**二叉堆 + 无界**，元素按 `Comparable` 或 `Comparator` 排序。

- `DelayQueue`：延迟队列，元素到期才能被取出，用于定时任务（`ScheduledThreadPoolExecutor` 内部用它）。

- `SynchronousQueue`：**零容量**，每次 `put` 必须等一个 `take` 配对 —— `Executors.newCachedThreadPool()` 用它做「直接交手」。

- `LinkedTransferQueue`：`LinkedBlockingQueue` 的加强版，支持 `transfer()`（等消费者取走才返回）。

## 面试场景 6：CompletableFuture 是什么？相比 Future 好在哪？⭐核心

🎤 面试官

你项目里用过 `CompletableFuture` 吗？它比传统 `Future` 好在哪？

🧑‍💻 你

`CompletableFuture` 是 Java 8 引入的异步编程类，实现了 `Future` 和 `CompletionStage` 两个接口。核心解决 `Future` 的四大痛点：

能力FutureCompletableFuture

获取结果只能 `get()` 阻塞，或 `isDone()` 轮询**回调**：完成后自动触发 `thenApply`/`thenAccept`
任务编排不支持**链式组合**（`thenCompose`）、**并行组合**（`thenCombine`）
多任务聚合不支持`allOf`（全部完成）、`anyOf`（任一完成）
异常处理只在 `get()` 时抛 `ExecutionException``exceptionally`/`handle`/`whenComplete` 声明式处理

本质上，`Future` 是「异步任务的*句柄*」，你只能被动等结果；`CompletableFuture` 是「异步计算的*阶段（Stage）*」，能编排一整条流水线 —— 这就是名字里 *Completion**Stage*** 的含义。

典型业务价值：**并行调多个下游服务，把「串行等待时间之和」压缩到「最长那个」**。比如详情页要同时拉用户、商品、评论、库存 4 个服务，每个 100ms —— 串行 400ms，用 `CompletableFuture` 并行只要 100ms。

追问 `CompletionStage` 接口有什么用？为什么 `CompletableFuture` 要实现它？

`CompletionStage` 是异步编程的**抽象接口**，定义了「一个异步计算阶段完成后能触发下一个阶段」的语义 —— 大约 40 个方法（`thenApply`/`thenCompose`/`thenCombine` 等）。`CompletableFuture` 是它唯一的官方实现类。这个接口的作用是：*让「异步流水线的编排」和「具体实现」解耦*。将来 JDK 或第三方要出新的异步框架（如 Reactor 的 `Mono`），可以复用 `CompletionStage` 的心智模型。

## 面试场景 7：CompletableFuture 的三种创建方式

🧑‍💻 你

常用四种，前三种是「异步启动」，第四种是「构造已完成的」：

方式签名是否有返回值用途

`runAsync(Runnable)`返回 `CompletableFuture<Void>`无「触发即忘」的异步动作（写日志、发通知）
`supplyAsync(Supplier<U>)`返回 `CompletableFuture<U>`有需要拿到异步结果的场景（**最常用**）
`completedFuture(v)`返回 `CompletableFuture<U>`（已完成）有把一个同步的值包装成 CF，方便和其它 CF 组合
`new CompletableFuture<>()`手动通过 `complete(v)`/`completeExceptionally(e)` 结束—把回调风格 API 桥接到 CF（如 Netty 的 `ChannelFuture`）

`runAsync` 和 `supplyAsync` 都有两个重载：只传 lambda，或再传一个 `Executor`。**生产环境永远用带 `Executor` 的版本**（原因见第 11 题）。

## 面试场景 8：回调 API 三大家族 ⭐核心

🎤 面试官

`thenApply`、`thenAccept`、`thenRun` 有什么区别？`thenCompose` 和 `thenCombine` 又是干什么的？

🧑‍💻 你

把 `CompletableFuture` 的方法按「输入输出」分三大家族：

### 家族一：单任务后置处理（用前一个 CF 的结果）

方法参数返回类比 Stream

`thenApply(Function<T,R>)`拿到 `T`，返回 `R``CF<R>`类似 `map`
`thenAccept(Consumer<T>)`拿到 `T`，无返回`CF<Void>`类似 `forEach`
`thenRun(Runnable)`不看结果`CF<Void>`只关心「完成了」这个事件

### 家族二：任务的链式依赖（前一个的结果送给一个「返回 CF 的函数」）

`thenCompose(Function<T, CompletionStage<R>>)` —— **类比 `flatMap`**。用于「第二个异步任务依赖第一个的结果」，避免出现 `CompletableFuture<CompletableFuture<R>>` 这种嵌套。

```
// 场景：先根据用户 ID 查用户，再根据用户所在地查天气
CompletableFuture<Weather> weather =
getUser(userId)                     // CF<User>
.thenCompose(u -> getWeather(u.getCity()));  // Function<User, CF<Weather>>
// 如果这里用 thenApply，得到的会是 CF<CF<Weather>> —— 嵌套地狱
```

### 家族三：两个独立任务的合并（并行做，都完成后聚合）

方法参数行为

`thenCombine(other, BiFunction)`另一个 CF + 合并函数两个都完成后合并结果，返回新 CF
`thenAcceptBoth(other, BiConsumer)`另一个 CF + 消费者两个都完成后消费，无返回值
`runAfterBoth(other, Runnable)`另一个 CF + Runnable两个都完成后跑，不看结果
`applyToEither(other, Function)`另一个 CF + 转换函数任一完成就用其结果（*竞速*）

追问 `thenApply` 和 `thenApplyAsync` 有什么区别？

核心区别在**「回调在哪个线程执行」**：

- `thenApply`：不指定线程池。如果前一个 CF 还没完成，回调在*完成前一个 CF 的那个线程*里跑；如果前一个 CF 已经完成，则可能在*当前调用 `thenApply` 的线程*里同步跑。

- `thenApplyAsync`：显式指定线程池。回调一定丢到指定池里异步执行。如果不传池参数，默认走 `ForkJoinPool.commonPool()`。

**生产建议**：永远用 `xxxAsync(fn, myExecutor)`。不加 `Async` 的写法容易出现「回调把执行任务的线程霸占了」—— 比如 IO 线程池的线程本来该赶紧回去接下一个请求，结果被回调里的重逻辑拖住。

## 面试场景 9：多任务组合 —— allOf / anyOf

🎤 面试官

「同时调 3 个下游服务，全部返回后合并结果」怎么用 `CompletableFuture` 写？

🧑‍💻 你

用 `CompletableFuture.allOf`：

```
CompletableFuture<User>    f1 = CompletableFuture.supplyAsync(() -> userService.get(id), pool);
CompletableFuture<Product> f2 = CompletableFuture.supplyAsync(() -> productService.get(id), pool);
CompletableFuture<Stock>   f3 = CompletableFuture.supplyAsync(() -> stockService.get(id), pool);

CompletableFuture<DetailVO> result =
CompletableFuture.allOf(f1, f2, f3)
.thenApply(v -> new DetailVO(f1.join(), f2.join(), f3.join()));

DetailVO vo = result.get(500, TimeUnit.MILLISECONDS);   // 超时兜底
```

关键点：

1. `allOf` 返回 `CompletableFuture<Void>` —— 不携带结果，只标记「都完成了」。

2. 取真实结果要通过 `fN.join()`（或 `get()`）。因为已经在 `allOf` 后触发，此时 `join()` 不会阻塞。

3. 务必带**超时**（`result.get(500, MS)`），防止某个下游卡死拖挂整个请求。

`anyOf(f1, f2, f3)` 语义相反：任何一个完成就返回，用于**「多路竞速」**（如同时查主库和缓存，谁快用谁）。

追问 `allOf` 里某个任务抛异常会怎样？

整个组合 CF 会被标记为**异常完成**，`get()`／`join()` 时抛 `CompletionException`（包装原始异常）。*其它已经完成或还在跑的任务并不会被取消* —— 它们继续跑，但结果被丢弃。如果需要「单个失败也不影响其它」，要在每个子 CF 里各自 `exceptionally(e -> null)` 兜底，再在 `allOf` 后判空。

## 面试场景 10：异常处理 —— exceptionally / handle / whenComplete

🎤 面试官

`CompletableFuture` 的异常怎么处理？这三个方法有什么区别？

🧑‍💻 你

方法触发时机参数能改结果吗典型用途

`exceptionally(Function<Throwable, T>)`仅异常时`Throwable`能（返回降级值）异常降级：查缓存失败返回默认值
`handle(BiFunction<T, Throwable, R>)`正常或异常都触发`(T, Throwable)`（其一为 null）能把结果和异常统一转成一个响应对象
`whenComplete(BiConsumer<T, Throwable>)`正常或异常都触发`(T, Throwable)`不能（观察式）打日志、埋点、资源清理

三个方法都有 `Async` 变体。使用示例：

```
CompletableFuture.supplyAsync(() -> queryUserFromDB(id), pool)
.exceptionally(e -> {
log.warn("DB fail, fallback to cache", e);
return queryUserFromCache(id);       // 降级
})
.whenComplete((user, err) -> {
metrics.record("query_user", err == null);   // 埋点
})
.thenAccept(user -> render(user));
```

追问 CompletableFuture 抛出的异常怎么才不会被吞？

三个关键点：

1. **一定要 `get()` 或 `join()`**：只做 `supplyAsync` 不接收结果的话，异常会永远静默 —— CF 不像 `Thread` 那样有 `UncaughtExceptionHandler`。

2. 用 `exceptionally`／`handle`／`whenComplete` **显式捕获**，不要指望上层 try-catch —— 异步任务的异常不会传到调用者的调用栈。

3. *如果只是「触发即忘」的场景*（`runAsync` 后不 join），至少要挂一个 `.whenComplete((r, e) -> { if (e != null) log.error(...); })`，否则异常吞得连日志都没有。

## 面试场景 11：默认线程池的陷阱 ⭐必考

🎤 面试官

`CompletableFuture.supplyAsync(fn)` 不传线程池，默认用哪个池？有什么问题？

🧑‍💻 你

默认走 **`ForkJoinPool.commonPool()`**。三个致命问题：

1. **守护线程**：`commonPool` 里的线程都是 `daemon=true`。主线程一退出，池里正在跑的 CF 直接被杀 —— 短命 CLI 程序里经常看到「任务好像没执行完」，就是这个原因。

2. **线程数太少**：默认大小是 `Runtime.availableProcessors() - 1`，8 核机器只有 7 个线程。做 CPU 密集任务够用，但 CF 常用于 *IO 密集*（远程调用），7 个线程扛不住几百 QPS。

3. **全局共享 → 相互干扰**：`commonPool` 被 JDK 内部（Stream 的 `parallel`）、第三方库、你自己的 CF 共用。*只要有一个业务把它打满，所有 CF 使用者都受影响* —— 排查起来极其痛苦。

解决办法：**自己建业务专属线程池，所有 `xxxAsync` 都显式传**。

```
ExecutorService bizPool = new ThreadPoolExecutor(
16, 32, 60L, TimeUnit.SECONDS,
new LinkedBlockingQueue<>(200),
new ThreadFactoryBuilder().setNameFormat("biz-cf-%d").build(),
new ThreadPoolExecutor.CallerRunsPolicy()
);

CompletableFuture.supplyAsync(() -> heavyIO(), bizPool)   // ← 一定要传池
.thenApplyAsync(this::process, bizPool)               // ← 后续回调也要传
.exceptionally(e -> fallback())
.whenCompleteAsync(this::metric, bizPool);
```

追问 如果每一步 `thenXxx` 都传同一个池，会不会因为「回调排队」死锁？

有可能。经典场景：`f = supplyAsync(A, pool).thenApplyAsync(B, pool)`，如果 A 里又 `join()` 了另一个走同一个池的 CF —— 你把池占满等自己，就是**线程池饥饿死锁**。*缓解办法*：① 按任务类型隔离池（IO 池 vs 计算池）；② 池要留出足够裕量；③ 避免在回调里再 `join()` 同池的 CF，改用 `thenCompose` 让它异步串起来。

陷阱 用 `Executors.newFixedThreadPool` 建业务池同样有坑 —— 它的队列是**无界 `LinkedBlockingQueue`**，被压太满会 OOM。生产环境永远用 `new ThreadPoolExecutor(...)` 手动构造，指定**有界队列 + 拒绝策略**（`CallerRunsPolicy` 或自定义回压）。这个话题下一节 0027《线程池最佳实践》深挖。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：ConcurrentSkipListMap 的有序遍历

```
import java.util.concurrent.ConcurrentSkipListMap;

public class SkipListDemo {
public static void main(String[] args) {
ConcurrentSkipListMap<Integer, String> map = new ConcurrentSkipListMap<>();
map.put(3, "c");
map.put(1, "a");
map.put(2, "b");

// 天然按 key 升序遍历
map.forEach((k, v) -> System.out.println(k + " -> " + v));
// 1 -> a
// 2 -> b
// 3 -> c

// 范围查询（TreeMap 才有的 API，ConcurrentHashMap 没有）
System.out.println(map.headMap(3));   // {1=a, 2=b}
System.out.println(map.firstKey());   // 1
System.out.println(map.lastKey());    // 3
}
}
```

### 验证 2：CopyOnWriteArrayList 的迭代快照隔离

```
import java.util.Iterator;
import java.util.concurrent.CopyOnWriteArrayList;

public class CowIterationSnapshot {
public static void main(String[] args) {
CopyOnWriteArrayList<String> list = new CopyOnWriteArrayList<>();
list.add("A"); list.add("B"); list.add("C");

Iterator<String> it = list.iterator();  // 拿到快照
list.add("D");                          // 迭代期间修改，不会 CME

while (it.hasNext()) {
System.out.println(it.next());      // 只输出 A B C（快照里的）
}
System.out.println("Now list = " + list);  // [A, B, C, D]
}
}
```

### 验证 3：CompletableFuture 链式组合（thenCompose vs thenCombine）

```
import java.util.concurrent.*;

public class CFPipelineDemo {

static ExecutorService pool = Executors.newFixedThreadPool(4);

// 模拟三个下游服务
static CompletableFuture<String> getUser(long id) {
return CompletableFuture.supplyAsync(() -> {
sleep(100); return "User#" + id;
}, pool);
}
static CompletableFuture<String> getCity(String user) {
return CompletableFuture.supplyAsync(() -> {
sleep(100); return user + "@Beijing";
}, pool);
}
static CompletableFuture<Integer> getWeather(String city) {
return CompletableFuture.supplyAsync(() -> {
sleep(100); return 25;   // 摄氏度
}, pool);
}

public static void main(String[] args) throws Exception {
long t0 = System.currentTimeMillis();

// 场景 A：thenCompose —— 后一个依赖前一个（串行流水线）
CompletableFuture<Integer> pipeline =
getUser(1L)
.thenCompose(user -> getCity(user))    // User → City
.thenCompose(city -> getWeather(city));// City → Weather

System.out.println("weather = " + pipeline.get());              // 25
System.out.println("elapsed = " + (System.currentTimeMillis() - t0) + "ms"); // ~300ms

// 场景 B：thenCombine —— 两个独立任务并行
long t1 = System.currentTimeMillis();
CompletableFuture<String> u1 = getUser(1L);
CompletableFuture<String> u2 = getUser(2L);
CompletableFuture<String> both = u1.thenCombine(u2, (a, b) -> a + " + " + b);

System.out.println("both = " + both.get());                     // User#1 + User#2
System.out.println("elapsed = " + (System.currentTimeMillis() - t1) + "ms"); // ~100ms

// 场景 C：allOf 聚合多个并行任务
long t2 = System.currentTimeMillis();
CompletableFuture<String> a = getUser(1L);
CompletableFuture<String> b = getUser(2L);
CompletableFuture<String> c = getUser(3L);
CompletableFuture<String> agg = CompletableFuture.allOf(a, b, c)
.thenApply(v -> String.join(", ", a.join(), b.join(), c.join()));

System.out.println("all = " + agg.get());                       // User#1, User#2, User#3
System.out.println("elapsed = " + (System.currentTimeMillis() - t2) + "ms"); // ~100ms

pool.shutdown();
}

static void sleep(long ms) {
try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
}
}
```

观察点：**串行 300ms、两两并行 100ms、三个并行 100ms**。这就是 `CompletableFuture` 相比裸 `Future.get()` 串行调用的巨大收益。

### 验证 4：异常处理与超时兜底

```
import java.util.concurrent.*;

public class CFExceptionDemo {
public static void main(String[] args) throws Exception {
// exceptionally：异常降级
String r1 = CompletableFuture
.<String>supplyAsync(() -> { throw new RuntimeException("boom"); })
.exceptionally(e -> "fallback:" + e.getMessage())
.get();
System.out.println(r1);   // fallback:java.lang.RuntimeException: boom

// handle：无论成功失败都处理，可返回不同类型
Integer r2 = CompletableFuture
.supplyAsync(() -> "hello")
.handle((v, e) -> e == null ? v.length() : -1)
.get();
System.out.println(r2);   // 5

// whenComplete：观察但不改结果（记日志、埋点）
CompletableFuture
.supplyAsync(() -> "world")
.whenComplete((v, e) -> System.out.println("done: v=" + v + " e=" + e))
.thenAccept(System.out::println);

// JDK 9+ 超时（否则要 orTimeout / completeOnTimeout）
try {
CompletableFuture
.supplyAsync(() -> { try { Thread.sleep(2000); } catch (Exception ignored) {} return "slow"; })
.orTimeout(500, TimeUnit.MILLISECONDS)
.get();
} catch (ExecutionException e) {
System.out.println("timed out: " + e.getCause());  // TimeoutException
}
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `Hashtable`、`Collections.synchronizedMap`、`ConcurrentHashMap` 三者的锁粒度差别？</summary>

前两者都是「整个 Map 一把锁」，并发度=1；`ConcurrentHashMap` 在 JDK 7 是 16 段分段锁，JDK 8 变成「每个桶头节点 `synchronized`」，并发度=桶数。新代码只用 `ConcurrentHashMap`。

</details>

<details>

<summary>Q2 需要「有序 + 线程安全」的 Map，为什么选 `ConcurrentSkipListMap` 而不是 `TreeMap + synchronized`？</summary>

跳表插入/删除只需要 CAS 修改相邻节点的指针，锁粒度极细；红黑树插入可能触发跨多个节点的旋转和变色，只能整表锁。跳表和红黑树的期望复杂度都是 O(log n)，但跳表在并发下扩展性远好于加锁的 TreeMap。

</details>

<details>

<summary>Q3 `ConcurrentLinkedQueue` 和 `BlockingQueue` 什么场景选哪个？</summary>

要背压/限流（队列满时阻塞生产者）选 `BlockingQueue`；要极致吞吐且不需要背压选 `ConcurrentLinkedQueue`（CAS 无锁）。线程池的 `workQueue` 用前者，因为需要「满时让提交者等」的语义。

</details>

<details>

<summary>Q4 `thenApply`、`thenCompose`、`thenCombine` 三者的区别？</summary>

`thenApply` 类似 `map`，把结果做同步转换；`thenCompose` 类似 `flatMap`，把结果送给一个「返回 CF 的函数」，用于链式异步依赖；`thenCombine` 是两个独立 CF 都完成后合并 —— 两个任务可以并行跑，最后聚合结果。

</details>

<details>

<summary>Q5 为什么生产环境不能用 `CompletableFuture.supplyAsync(fn)`（不传池）？</summary>

默认走 `ForkJoinPool.commonPool()`：① 里面是守护线程，主线程一退就被杀；② 线程数 `CPU-1`，做 IO 密集任务扛不住；③ 全局共享，任何库/业务都用它，一个卡死会波及所有 CF 使用者。必须用 `ThreadPoolExecutor` 手动建业务专属池，所有 `xxxAsync` 都显式传。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

- JDK 21 · `CompletableFuture` API —— 官方 40+ 方法一览

- Michael & Scott (1996) · Simple, Fast, and Practical Non-Blocking and Blocking Concurrent Queue Algorithms —— `ConcurrentLinkedQueue` 算法原论文

#### 🔗 关联课件

-  —— CHM 深挖

-  —— CoW 深挖

-  —— 上一课（自定义池）

-  —— 下一课（阶段三收尾）

#### 🧭 下一课预告

Lesson 0029：**虚拟线程（Virtual Thread）** —— JDK 21 正式落地的轻量级线程，一台机器能跑百万级并发。阶段三「并发编程」的收尾之作。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


