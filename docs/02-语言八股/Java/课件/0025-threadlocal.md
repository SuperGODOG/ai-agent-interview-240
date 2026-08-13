> Lesson 0025 · 阶段三 · 并发编程 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 8+ 追问

# 0025 · ThreadLocal 详解：原理 & 内存泄漏 & InheritableThreadLocal & TTL

这一课覆盖 的全部核心考点。`ThreadLocal` 是「线程本地存储」——每个线程各自持有一份变量副本，看起来只是「换了个位置存变量」，实则暗坑极多：**内存泄漏、线程池残留、异步不透传**，是中高级 Java 面试反复被打的位置。

把这一课吃透，你就能拿到三条 hard-mode 答题链路：**「ThreadLocal 的 key 为什么是弱引用？」→ 「那 value 呢？」→ 「所以泄漏的真凶是谁？怎么破？」**——这一串下来，面试官基本就点头了。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `ThreadLocal` 存的数据到底存在哪个对象里？是 `ThreadLocal` 自己吗？</summary>

**不是。**数据存在每个 `Thread` 对象内部的 `ThreadLocal.ThreadLocalMap threadLocals` 字段里；`ThreadLocal` 只是当 key 用，它自己不装 value。第 2 题会画出完整数据结构。

</details>

<details>

<summary>Q0.2 用完 `ThreadLocal` 必须调 `remove()`，为什么？不调会怎么样？</summary>

因为 `Entry` 的 **key 是弱引用（ThreadLocal 可被 GC）而 value 是强引用**。线程池里 Thread 长期存活 → `ThreadLocalMap` 一直在 → key 被 GC 变 null 后 value 却仍被强引用挂着 → **内存泄漏**。第 5 题详解泄漏链条。

</details>

## 面试场景 1：ThreadLocal 是什么？解决什么问题？

🎤 面试官

先说一下 `ThreadLocal` 是什么，什么场景下会用它？

🧑‍💻 你

`ThreadLocal` 提供**线程本地变量（Thread Local Variable）**：每个访问它的线程都拥有一份独立的变量副本，多线程之间互不干扰、天然线程隔离。它换了个思路解决共享变量的线程安全问题——*不共享，就没有并发问题*。

典型场景：

- **SimpleDateFormat 复用**：`SimpleDateFormat` 内部有可变状态非线程安全，用 `ThreadLocal` 给每个线程各存一份就安全了。

- **Spring 事务传播**：`TransactionSynchronizationManager` 用 `ThreadLocal` 存当前线程绑定的数据库 `Connection`，同一线程多次调用共享同一个连接、同一个事务。

- **Spring Security 认证上下文**：`SecurityContextHolder` 用 `ThreadLocal` 存当前登录用户的 `Authentication`，业务代码 `SecurityContextHolder.getContext()` 就能拿到。

- **MDC 链路追踪**：SLF4J 的 `MDC`（Mapped Diagnostic Context）用 `ThreadLocal` 存 `traceId`，一次请求全链路日志都能带上同一个 traceId。

- **Web 请求上下文**：Spring 的 `RequestContextHolder` 让你在任何地方拿到当前 `HttpServletRequest`。

追问 `ThreadLocal` 和 `synchronized`、锁的思路本质区别是什么？

锁是**「让并发访问串行化」**——大家都能看到共享变量，但同一时刻只能一个线程动。`ThreadLocal` 是**「用空间换时间，直接不共享」**——每个线程各拿自己的副本，压根不存在竞争。**能用 `ThreadLocal` 解决的问题，性能一般比锁好；但语义完全不同**——`ThreadLocal` 存的东西线程之间是不可见的，如果业务需要跨线程共享，只能用锁 + 共享变量。

## 面试场景 2：ThreadLocal 的底层原理（★核心）

🎤 面试官

`threadLocal.set(x)` 这一步，值 `x` 到底存到了哪里？

🧑‍💻 你

存到了**「当前线程」那个 `Thread` 对象自己身上**——不是存在 `ThreadLocal` 里。核心数据结构长这样：

```
Thread 对象 (每个线程一个)
└─ ThreadLocal.ThreadLocalMap threadLocals   // 私有字段
└─ Entry[] table                         // 数组（不是链表！）
└─ Entry extends WeakReference<ThreadLocal<?>>
├─ key   → ThreadLocal 对象（弱引用）
└─ value → 你 set 进去的值（强引用）
```

关键三点：

1. **存储位置在 Thread，不在 ThreadLocal**。`Thread` 类有个字段 `ThreadLocal.ThreadLocalMap threadLocals`，每个线程都有自己的这个 Map。

2. **ThreadLocal 只是 key**。同一个 `ThreadLocal` 实例在不同线程里，会当作 key 去查那个线程自己的 `ThreadLocalMap`，取到各自的 value。

3. **set 流程**：`set(v)` → 拿到 `Thread.currentThread()` → 取它的 `threadLocals` → 以 `this`（即当前 `ThreadLocal` 对象）为 key 存进去。

看 JDK 源码就一目了然：

```
public void set(T value) {
Thread t = Thread.currentThread();
ThreadLocalMap map = getMap(t);       // return t.threadLocals
if (map != null) {
map.set(this, value);              // this = 当前 ThreadLocal 实例，作为 key
} else {
createMap(t, value);
}
}
```

追问 那如果一个线程用了 10 个不同的 `ThreadLocal`，是有 10 个 `ThreadLocalMap` 吗？

**不是，还是一个。**每个线程只有一个 `ThreadLocalMap`，10 个 `ThreadLocal` 就是这个 Map 里的 10 个 Entry，key 分别是那 10 个 `ThreadLocal` 对象。*Map 的所有权在 Thread，不在 ThreadLocal*——这是理解一切原理的基石。

## 面试场景 3：ThreadLocalMap 的结构（★核心）

🎤 面试官

`ThreadLocalMap` 和 `HashMap` 是一回事吗？结构上有什么区别？

🧑‍💻 你

不是一回事。`ThreadLocalMap` 是 `ThreadLocal` 内部单独实现的一个静态内部类，跟 `HashMap` 只是名字像。核心差异：

维度HashMapThreadLocalMap

冲突解决**链地址法**（拉链）+ JDK 8 后红黑树**开放寻址法**（线性探测）
Entry 结构`Node` 有 `next` 指针，形成链表`Entry` 就一个数组元素，无 `next`
key 引用类型强引用**弱引用**（`WeakReference<ThreadLocal>`）
hash 算法扰动函数 + `hashCode`斐波那契/黄金分割 `0x61c88647` 增量
扩容阈值0.75 * capacity2/3 * len，且触发时会先清理过期 key
初始容量1616

**Entry 定义**就是这几行：

```
static class Entry extends WeakReference<ThreadLocal<?>> {
Object value;                        // 强引用！
Entry(ThreadLocal<?> k, Object v) {
super(k);                         // key 作为弱引用交给父类 WeakReference
value = v;
}
}
```

——记住这两行：**key 弱引用，value 强引用**，是后面所有内存泄漏问题的源头。

追问 `ThreadLocalMap` 为什么用**开放寻址**而不是链地址（HashMap 那种）？

三个原因：

1. **数据量小**：一个线程里挂几十个 `ThreadLocal` 就顶天了，开放寻址常数因子小、无链表节点内存开销更划算。

2. **hash 冲突极少**：`HASH_INCREMENT = 0x61c88647`（黄金分割数）保证连续创建的 `ThreadLocal` 散列非常均匀。

3. **方便顺带清理**：开放寻址在线性探测过程中天然可以遍历相邻槽位，正好用来「顺路清理 key 为 null 的过期 Entry」——这是 `ThreadLocalMap` 的一个重要 side effect。链表结构做同样的事就麻烦得多。

追问 那个 `0x61c88647` 是什么？

是 **2^32 × (√5 - 1) / 2** 取整——黄金分割数在 32 位整数下的表示。每 new 一个 `ThreadLocal`，它的 `threadLocalHashCode` 就在类静态 AtomicInteger 上累加这个数。这个魔数的作用是让连续申请的 `ThreadLocal` 的 hash 结果在数组下标上分布得极其均匀（斐波那契散列），几乎无冲突。经典的常数设计。

## 面试场景 4：为什么 key 用弱引用？（★核心）

🎤 面试官

为什么 `Entry` 的 key 要用**弱引用**？如果改成强引用会怎样？

🧑‍💻 你

先看引用链：

```
Thread ──强──▶ ThreadLocalMap ──强──▶ Entry ──?──▶ ThreadLocal (key)
└──强──▶ value
```

假设 key 用**强引用**：

1. 业务代码里 `ThreadLocal` 对象已经不再被引用（比如方法返回、局部变量作用域结束）。

2. 但 `Thread` 只要还活着，`ThreadLocalMap` 就在；`Entry` 里的 key 是强引用挂着 `ThreadLocal`；

3. 结果：**`ThreadLocal` 对象永远无法被 GC 回收**——只要这条 Thread 不死，这个 `ThreadLocal` 就活。

4. 线程池场景（Thread 复用），这些「已经没人用」的 `ThreadLocal` 会一直堆着 → 泄漏放大。

改成**弱引用**之后：

- 只要业务代码没有强引用指向 `ThreadLocal`，下一次 GC 就能把它回收。

- Entry 里的 key 会变成 `null`（弱引用被清理）。

- 至少 `ThreadLocal` 对象本身能释放。

陷阱 key 用弱引用**解决了 `ThreadLocal` 对象本身的泄漏**，但**没解决 value 的泄漏**——因为 value 依然是强引用。key 被 GC 之后变 null 的 Entry 叫「**过期 Entry / stale entry**」，如果不主动清理，value 会一直强引用堆着。这是下一题「内存泄漏真凶」的关键。

追问 为什么 value 不也用弱引用？

因为 value 是**业务真正要用的数据**。如果 value 也弱引用，业务代码 `threadLocal.get()` 拿回来的时候可能就是 `null`——那 `ThreadLocal` 就没意义了。key 是「查找钥匙」可以被 GC，value 是「存进去的东西」必须坚挺。这个设计不对称是**为了业务正确性**，代价就是需要程序员显式 `remove()` 来兜底。

## 面试场景 5：ThreadLocal 内存泄漏的完整链条（★经典）

🎤 面试官

能画出 `ThreadLocal` 内存泄漏的完整引用链条吗？谁是真凶？

🧑‍💻 你

完整链条：

```
Thread (线程池里长期存活)
└─强─▶ ThreadLocalMap
└─强─▶ Entry[]
└─强─▶ Entry
├─弱─▶ ThreadLocal 对象 ← 已被 GC，key = null
└─强─▶ value           ← ❌ 泄漏！释放不掉

↑
真凶就是这里
```

拆解一下：

1. **ThreadLocal 已被 GC**：外部业务代码不再持有它的强引用，弱引用自动清理，Entry.get() 返回 `null`。

2. **Entry 本身还在**：因为 `Entry[]` 数组对 Entry 是强引用，Entry 只有等 Map 主动清它才走。

3. **value 还在**：Entry 对 value 是强引用，Entry 不走 value 不走。

4. **Thread 还在**：线程池的 worker 线程*可能几个月不销毁*——ThreadLocalMap 就跟着不销毁，泄漏的 value 越堆越多。

所以泄漏真凶：**value 是强引用 + 线程长期存活 + 程序员没主动 `remove()`** 三者叠加。

陷阱 ThreadLocal 的清理机制**只是「顺带清理」，不是主动的定时清理**。`ThreadLocalMap` 会在 `set`/`get`/`remove` 过程中借机扫描相邻的过期 Entry，但如果这个 ThreadLocal 之后再没被使用（没调用 set/get/remove），过期 Entry 就一直挂着不会被扫到。**不能指望 JVM 自己给你清干净**。

追问 线程池 + `ThreadLocal` 有哪些典型 bug？

1. **上一个任务的残留值污染下一个任务**：线程 A 在任务 T1 里 `tl.set("uid=1")`，忘了 remove；T1 结束后线程 A 回到池里；下一次 T2 复用了线程 A，`tl.get()` 返回了「uid=1」——但 T2 是另一个用户的请求，用户越权！这是线上事故常见 root cause。

2. **内存泄漏累积**：Thread 长期存活，泄漏的 value 越堆越多，最终 OOM。

3. **异步透传不生效**：主线程 `tl.set("traceId=xxx")`，用线程池 submit 一个任务，任务里 `tl.get()` 是 `null`——ThreadLocal 天然不跨线程；`InheritableThreadLocal` 也不行（下面细讲）。

## 面试场景 6：怎么避免内存泄漏？

🎤 面试官

知道有泄漏风险，实际写代码怎么防？

🧑‍💻 你

**唯一靠谱的做法：用完必须 `remove()`，并且放 `try-finally` 里保底。**

```
ThreadLocal<User> holder = new ThreadLocal<>();

try {
holder.set(user);
// ... 业务逻辑 ...
} finally {
holder.remove();           // ← 无论正常/异常都要执行
}
```

`remove()` 会把当前 Entry 从 `ThreadLocalMap` 里直接删掉（`expungeStaleEntry`），value 强引用释放，Entry 数组槽位归零。

框架层面已经做的兜底：

- **Spring MVC**：`DispatcherServlet` 在请求处理结束的 `finally` 里调 `RequestContextHolder.resetRequestAttributes()`，清掉当前请求绑定的 `ThreadLocal`。

- **Spring Security**：`SecurityContextPersistenceFilter` 在 `finally` 里调 `SecurityContextHolder.clearContext()`。

- **MDC**：日志框架通常在 Filter/Interceptor 的 `afterCompletion` 里 `MDC.clear()`。

- **自定义线程池**：可以重写 `ThreadPoolExecutor.afterExecute()`，任务执行完之后统一清理已知的 `ThreadLocal`。

追问 Spring 的 `RequestContextHolder` 是怎么保证请求结束一定清 `ThreadLocal` 的？

入口在 `FrameworkServlet.processRequest()`，简化后：

```
try {
RequestContextHolder.setRequestAttributes(newAttributes);
// ... 分发到 Controller ...
} finally {
RequestContextHolder.resetRequestAttributes();   // ← try-finally 兜底
}
```

就是 `try-finally` 模式的教科书应用。所以你写业务代码用 `RequestContextHolder` 不用担心泄漏——Spring 已经兜底了。*但你自己 new 出来的 ThreadLocal 就得自己兜底*。

## 面试场景 7：ThreadLocal 的 get/set/remove 流程简析

🧑‍💻 你

三个方法都建立在 **「先算 hash 定位槽 → 开放寻址线性探测 → 顺路清理过期 Entry」**这个套路上。

**① set(value)**：

```
1. i = key.threadLocalHashCode & (len - 1)   // 算槽位
2. 从 tab[i] 开始线性探测：
├─ 槽为空          → 直接放 Entry(key, value)
├─ key 命中当前 tl → 覆盖 value
├─ key == null    → replaceStaleEntry() 清理并复用
└─ 都不是         → nextIndex(i, len)，继续探测
3. 探测过程结束后 cleanSomeSlots() 启发式清理若干个过期槽
4. 若 size ≥ threshold → rehash（先全量清理，再判断是否 resize 到 2 倍）
```

**② get()**：

```
1. 直接算 i，看 tab[i] 是否命中当前 tl → 命中直接返回 value（O(1) 快路径）
2. 未命中 → getEntryAfterMiss() 沿线性探测查找
3. 探测过程中遇到 key == null 的槽 → expungeStaleEntry() 就地清理
4. 找到就返回 value；探测到空槽仍未命中 → 返回 null（会走 setInitialValue）
```

**③ remove(key)**：

```
1. 算 i，线性探测找到 key 匹配的 Entry
2. entry.clear()          // 主动断开弱引用（key 置空）
3. expungeStaleEntry(i)    // 从 i 开始向后扫描，清理所有 key == null 的槽
// 同时把非过期槽 rehash 到更近位置（连续段整理）
```

核心观察：**清理时机不是主动定时，而是「顺路」**——每次 set/get/remove 都可能触发局部清理。所以「不再使用的 ThreadLocal，不 remove 就永远清不到」这个论断是精准的。

追问 「探测式清理」（`expungeStaleEntry`）和「启发式清理」（`cleanSomeSlots`）的区别？

- **探测式清理**：从遇到过期槽的位置开始，*连续向后扫直到空槽*——把这一段里所有过期 Entry 都清掉，并对未过期 Entry 做 rehash 就近安置。深度清理，但只在一小段。

- **启发式清理**：`set` 完成后，从当前位置开始，扫 `log2(n)` 个槽，遇到过期就深度清理然后重置计数；扫完为止。轻量级、概率式，摊到每次 set 上开销可控。

两者组合：**探测式做「面」的深度清理，启发式做「点」的常规扫描**。

## 面试场景 8：InheritableThreadLocal 是什么？

🎤 面试官

如果我在主线程 `set` 了值，然后 new 一个子线程，子线程能拿到吗？

🧑‍💻 你

普通 `ThreadLocal` **拿不到**——ThreadLocal 是「线程私有」，子线程有自己独立的 `ThreadLocalMap`。

如果需要父子线程传递，用 `InheritableThreadLocal`（JDK 自带）。原理：`Thread` 类除了 `threadLocals` 还有个 `inheritableThreadLocals` 字段；在 `new Thread()` 时（`Thread.init()` 里）会检查父线程的 `inheritableThreadLocals`，如果非空就**拷贝一份**给子线程：

```
// Thread.init() 简化版
if (inheritThreadLocals && parent.inheritableThreadLocals != null) {
this.inheritableThreadLocals =
ThreadLocal.createInheritedMap(parent.inheritableThreadLocals);
}
```

陷阱 `InheritableThreadLocal` **只在「子线程被 new 出来的那一刻」拷贝一次**！之后父线程改值，子线程看不到；子线程改值，父线程也看不到——是一次性快照，不是引用共享。而且更重要的坑：**线程池场景里没用**——线程池的 Thread 是*预先创建、反复复用*的，一开始 new 时父线程根本还没 set 值，等到任务 submit 时 Thread 早就存在了，压根不会再触发拷贝。

追问 那 `InheritableThreadLocal` 真实场景有什么用？

用途其实很窄：只在**用户自己 new 一次性子线程**的场景（现在几乎没人这么写了）。绝大多数生产环境都是线程池，`InheritableThreadLocal` 派不上用场。真要做「异步任务里透传上下文」——用下一题的 **TransmittableThreadLocal**。

## 面试场景 9：TransmittableThreadLocal（TTL，阿里方案）

🎤 面试官

线程池场景下 `InheritableThreadLocal` 失效，怎么解决？

🧑‍💻 你

用阿里开源的 **TransmittableThreadLocal（TTL）**——`com.alibaba:transmittable-thread-local`。核心思路是**「提交 → 捕获 → 回放 → 恢复」四步走**：

```
父线程 (业务)                        子线程 (线程池 worker)
────────────                        ─────────────────────
ttl.set("traceId=X")
│
▼
executor.submit(
TtlRunnable.get(task) )   ─┐
│                          │  ① capture: 把父线程当前 TTL 值 snapshot
│                          │  （在 submit 那一瞬间执行）
│                          ▼
│                        任务开始执行前
│                          │  ② replay: 把 snapshot 装载到 worker 线程
│                          ▼
│                        执行 task.run()
│                          │  这时 ttl.get() = "traceId=X" ✅
│                          ▼
│                        执行完毕
│                          │  ③ restore: 恢复 worker 线程原本的 TTL
▼
下一个任务不会被污染
```

使用方式常见两种：

1. **包装 Runnable**：`executor.submit(TtlRunnable.get(runnable))`。

2. **包装线程池**：`Executor ttlExecutor = TtlExecutors.getTtlExecutor(rawExecutor);` 之后 submit 任何普通 Runnable 都会自动透传。

还有更透明的方案——TTL 提供 JavaAgent，用字节码增强所有 `Runnable`/`Callable`，业务代码零改造。

追问 TTL 为什么能解决 `InheritableThreadLocal` 解决不了的问题？

`InheritableThreadLocal` 的传递时机是「Thread 构造函数里」——线程池里 Thread 早就构造完了，传递机会已经错过。TTL 的传递时机是「任务提交时」——每 submit 一次任务都重新 snapshot 一次；线程池 worker 复用时先*替换*自己的上下文为 snapshot、任务执行完再*恢复*——所以既能透传，又不会污染下一个任务。**时机对了，问题就解了**。

追问 TTL 有性能开销吗？

有，但可控：**每次 submit 需要遍历一次 TTL 的注册表做 snapshot，任务开始前 replay，结束后 restore**——大约多了 3 次哈希表操作。对绝大多数业务（一次请求几毫秒到几十毫秒）开销可以忽略。TPS 极高的短任务场景（微秒级）需要评估。

## 面试场景 10：ThreadLocal 的经典应用

🧑‍💻 你

面试可以点名到的 5 个经典应用：

1. **Web 请求上下文（RequestContextHolder）**：Spring 把 `HttpServletRequest`、`HttpServletResponse`、locale 等信息放 `ThreadLocal`，让你在任何深度的 Service/DAO 层都能 `RequestContextHolder.getRequestAttributes()` 拿到。

2. **Spring Security 的 SecurityContextHolder**：默认 strategy 就是 `ThreadLocalSecurityContextHolderStrategy`——当前登录用户信息挂在 `ThreadLocal`，业务里 `SecurityContextHolder.getContext().getAuthentication()` 即可拿到。

3. **链路追踪 traceId（MDC）**：SLF4J 的 `MDC` 用 `ThreadLocal` 存键值对，日志 pattern `%X{traceId}` 就能把 traceId 输出到每一行日志——同一请求全链路串联。

4. **SimpleDateFormat 复用**：`SimpleDateFormat` 非线程安全，用 `ThreadLocal.withInitial(() -> new SimpleDateFormat(...))` 让每个线程各持一份。JDK 8 之后更推荐用不可变的 `DateTimeFormatter`，但老代码还大量存在。

5. **数据库事务 Connection 绑定**：Spring 的 `TransactionSynchronizationManager` 把当前线程绑定的 `Connection` 存 `ThreadLocal`，同一线程内多次 `DataSourceUtils.getConnection()` 拿到的是同一个连接——保证同一事务。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：基本使用 + 线程隔离

```
public class ThreadLocalBasic {
private static final ThreadLocal<String> TL = new ThreadLocal<>();

public static void main(String[] args) throws InterruptedException {
Thread t1 = new Thread(() -> {
TL.set("hello from t1");
sleep(100);
System.out.println("t1 read: " + TL.get());   // hello from t1
});
Thread t2 = new Thread(() -> {
TL.set("hello from t2");
sleep(200);
System.out.println("t2 read: " + TL.get());   // hello from t2
});
t1.start(); t2.start();
t1.join();  t2.join();
System.out.println("main read: " + TL.get());     // null（主线程没 set）
}
static void sleep(long ms) {
try { Thread.sleep(ms); } catch (InterruptedException e) {}
}
}
```

### 验证 2：SimpleDateFormat 的经典用法

```
public class SdfPerThread {
// 每个线程各自持有一份 SimpleDateFormat，避免并发解析出错
private static final ThreadLocal<SimpleDateFormat> SDF =
ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd HH:mm:ss"));

public static String format(Date d) {
return SDF.get().format(d);
}

public static void main(String[] args) throws Exception {
ExecutorService pool = Executors.newFixedThreadPool(4);
for (int i = 0; i < 8; i++) {
pool.submit(() -> System.out.println(
Thread.currentThread().getName() + " → " + format(new Date())
));
}
pool.shutdown();
}
}
```

### 验证 3：线程池残留污染（★经典 bug）

```
public class PoolResidueBug {
private static final ThreadLocal<String> USER = new ThreadLocal<>();

public static void main(String[] args) throws Exception {
ExecutorService pool = Executors.newSingleThreadExecutor();

// 任务 1：设置 uid=alice 但忘了 remove
pool.submit(() -> {
USER.set("alice");
System.out.println("task-1 uid=" + USER.get());
// ❌ 忘了 USER.remove()
});

// 任务 2：期望 uid=null（新用户），实际拿到了 alice！
pool.submit(() -> {
System.out.println("task-2 uid=" + USER.get());   // alice ← 越权！
});

pool.shutdown();
}
}
// 输出：
//   task-1 uid=alice
//   task-2 uid=alice   ← ❌ 严重生产 bug
```

陷阱 上面这段代码在生产环境完全可能变成**越权访问**——A 用户 请求残留的 `ThreadLocal` 让 B 用户请求看到 A 的身份。这是线上真实事故常见 root cause，务必 `try-finally + remove()`。

### 验证 4：try-finally 正确姿势

```
public class ThreadLocalCorrect {
private static final ThreadLocal<String> USER = new ThreadLocal<>();

public static void handleRequest(String uid, Runnable business) {
try {
USER.set(uid);
business.run();
} finally {
USER.remove();          // ← 保底清理
}
}
}
```

### 验证 5：InheritableThreadLocal 在线程池里失效

```
public class InheritableFail {
private static final InheritableThreadLocal<String> ITL =
new InheritableThreadLocal<>();

public static void main(String[] args) throws Exception {
// 场景 A：new Thread 有效
ITL.set("v-A");
new Thread(() -> System.out.println("newThread: " + ITL.get())).start();
// 输出：newThread: v-A  ✅

Thread.sleep(200);

// 场景 B：线程池失效
ExecutorService pool = Executors.newSingleThreadExecutor();
pool.submit(() -> System.out.println("pool-first: " + ITL.get()));
// ↑ pool worker 创建时 main 已经 set 过，能拿到 v-A
Thread.sleep(100);

ITL.set("v-B");     // 之后 main 改成 v-B
pool.submit(() -> System.out.println("pool-second: " + ITL.get()));
// ↑ 输出还是 v-A，因为 worker 线程早已构造完，v-B 拷贝不进去 ❌

pool.shutdown();
}
}
```

运行结果直观展示：**线程池 + InheritableThreadLocal 只在 worker 首次创建的那一瞬间有效，之后父线程变更完全传不进去**——这就是为什么要 TTL。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `ThreadLocal.set(x)` 存进去的 `x` 到底存到了哪个对象里？</summary>

存到当前线程 `Thread` 对象的 `ThreadLocal.ThreadLocalMap threadLocals` 字段里，以当前 `ThreadLocal` 实例本身为 key。**数据的所有权在 Thread 上，不在 ThreadLocal 上**——ThreadLocal 只当 key 用。

</details>

<details>

<summary>Q2 `ThreadLocalMap` 和 `HashMap` 在冲突解决上最大的区别是什么？为什么这么设计？</summary>

`ThreadLocalMap` 用**开放寻址（线性探测）**，`HashMap` 用**链地址法（拉链 + JDK 8 后红黑树）**。理由：ThreadLocalMap 数据量小（一个线程通常几十个 ThreadLocal 顶天）+ 黄金分割数 `0x61c88647` 让 hash 分布极均匀 + 线性探测天然方便顺路清理过期 Entry。

</details>

<details>

<summary>Q3 内存泄漏的完整链条是怎样的？真凶是谁？</summary>

链条：`Thread`（线程池长期存活）→ `ThreadLocalMap` → `Entry[]` → `Entry`（key 是弱引用，ThreadLocal 被 GC 后 key = null）→ **value（强引用不释放）**。真凶是「value 强引用 + 线程长期存活 + 程序员没主动 `remove()`」三者叠加。

</details>

<details>

<summary>Q4 为什么 key 用弱引用、value 用强引用，这种不对称设计的取舍是什么？</summary>

key 弱引用是**为了避免 ThreadLocal 对象本身被 Map 永久挂住无法 GC**；value 强引用是**为了保证业务能可靠地 get() 到值**——如果 value 也弱引用，随时会被回收，ThreadLocal 就丧失存储语义。代价是可能泄漏 value，需要程序员 `remove()` 兜底。

</details>

<details>

<summary>Q5 `InheritableThreadLocal` 和 `TransmittableThreadLocal`（TTL）分别解决什么问题？为什么线程池场景 `InheritableThreadLocal` 失效？</summary>

`InheritableThreadLocal` 解决**父线程 new 子线程时的一次性上下文拷贝**——但拷贝时机在 `Thread.init()`，线程池 worker 早就构造完，之后 submit 任务时压根不会再触发拷贝，所以失效。**TTL**（阿里开源）把传递时机改到「任务提交时」：submit 时 capture 父线程当前 TTL、任务开始前 replay 到 worker、任务结束后 restore worker 原值——所以线程池场景也能正确透传且不污染下一个任务。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Alibaba TransmittableThreadLocal（TTL）· GitHub —— TTL 源码 + JavaAgent 用法

- JDK 21 · `java.lang.ThreadLocal` API —— 官方文档

#### 🔗 关联课件

- （上一课）

- （下一课，线程池 + ThreadLocal 就是本课陷阱的高发现场）

#### 🧭 下一课预告

Lesson 0026：**线程池核心参数 & 拒绝策略 & 阻塞队列**——本课反复出现的「线程池 + ThreadLocal 残留污染」问题，在下一课会完整展开线程池的生命周期和最佳实践。

💬 有任何疑问 ——「remove() 到底会不会把 Entry 数组槽位清空？」「TTL 和 Reactor Context 有什么区别？」「Spring @Async 场景要不要手动包 TtlRunnable？」—— 直接问我。我是你的老师，也是你的追问陪练。


