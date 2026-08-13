> Lesson 0022 · 阶段三 · 并发编程 · ⭐⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0022 · Atomic 原子类家族

这一课覆盖 。上一课  讲了 CAS 的机制，这一课看 CAS 在 JDK 里长出的**五大家族**：基本类型、引用类型、数组类型、字段更新器、累加器。重点看 `LongAdder` 的分片思想 —— 这是 `ConcurrentHashMap.size()` 的同款套路，也是高并发计数的标准答案。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `AtomicInteger.incrementAndGet()` 是不是原子的？靠什么保证？</summary>

是原子的。靠 CAS 自旋（`Unsafe.compareAndSwapInt`）—— `do { v = get(); } while (!cas(v, v+1))`。字段本身是 `volatile` 保证可见性。第 2 题细讲。

</details>

<details>

<summary>Q0.2 `LongAdder` 和 `AtomicLong` 什么时候用哪个？</summary>

高并发计数（QPS 统计、点赞计数）用 `LongAdder`，写快很多；*需要读到精确值*用 `AtomicLong`，因为 `LongAdder.sum()` 是快照可能不准。第 7、8 题细讲。

</details>

## 面试场景 1：Atomic 家族全景（五大分类）

🎤 面试官

说说 `java.util.concurrent.atomic` 包下有哪几类原子类？

🧑‍💻 你

分类代表类作用

**基本类型**`AtomicInteger` / `AtomicLong` / `AtomicBoolean`单个数值/布尔的原子更新
**引用类型**`AtomicReference` / `AtomicStampedReference` / `AtomicMarkableReference`对象引用的原子更新；后两个解决 ABA
**数组类型**`AtomicIntegerArray` / `AtomicLongArray` / `AtomicReferenceArray`数组**元素级**原子更新（比 volatile 数组细粒度）
**字段更新器**`AtomicIntegerFieldUpdater` / `AtomicLongFieldUpdater` / `AtomicReferenceFieldUpdater`对已有类的 `volatile` 字段做原子更新（无需改字段类型，省包装对象）
**累加器**（JDK 8+）`LongAdder` / `DoubleAdder` / `LongAccumulator` / `DoubleAccumulator`高并发下的分片累加，比 `AtomicLong` 快数倍

## 面试场景 2：AtomicInteger 的原理（★核心）

🧑‍💻 你

核心字段就两个：

```
public class AtomicInteger extends Number {
private static final Unsafe unsafe = Unsafe.getUnsafe();
private static final long valueOffset;               // value 字段的内存偏移

static {
try {
valueOffset = unsafe.objectFieldOffset(
AtomicInteger.class.getDeclaredField("value"));
} catch (Exception ex) { throw new Error(ex); }
}

private volatile int value;                          // ← 关键：volatile 保证可见性
}
```

`getAndIncrement` 的实现是 CAS 自旋：

```
public final int getAndIncrement() {
return unsafe.getAndAddInt(this, valueOffset, 1);
}

// Unsafe 的实现
public final int getAndAddInt(Object o, long offset, int delta) {
int v;
do {
v = getIntVolatile(o, offset);
} while (!compareAndSwapInt(o, offset, v, v + delta));
return v;
}
```

本质是**「volatile 保证可见性 + CAS 保证原子性」**的组合。

追问 为什么 `value` 要用 `volatile`？CAS 不是就够了吗？

CAS 只保证「读-改-写」的原子性，**不保证读到的是最新值**。如果不加 volatile，线程 A 更新的值可能一直待在 CPU 缓存里，线程 B 的 CAS 会一直失败（读到旧值）陷入无限循环。volatile 保证 `getIntVolatile` 强制从主存读，也保证 CAS 成功后立刻刷回。

## 面试场景 3：AtomicInteger 常用方法速查

方法语义

`get()` / `set(v)`读/写（volatile 语义）
`getAndSet(v)`原子交换：返回旧值，设新值
`compareAndSet(exp, upd)`裸 CAS：等于 exp 才改为 upd，返回 boolean
`getAndIncrement()` / `incrementAndGet()`+1，前者返旧值后者返新值
`getAndDecrement()` / `decrementAndGet()`-1
`getAndAdd(delta)` / `addAndGet(delta)`加 delta
`getAndUpdate(fn)` / `updateAndGet(fn)`（JDK 8+）用 Lambda 定义变换：`a.updateAndGet(x -> x * 2)`
`getAndAccumulate(x, biFn)`（JDK 8+）用二元函数累积：`a.accumulateAndGet(3, Math::max)`
`lazySet(v)`不带内存屏障的 set，性能高但无跨线程可见性保证；用于「反正读者会通过其他手段感知」的场景

## 面试场景 4：AtomicReference 家族（三兄弟）

🧑‍💻 你

- **`AtomicReference<V>`**：对任意对象引用做 CAS。比较的是*引用地址*（`==`）不是 `equals`。典型场景：无锁链表节点交换、原子替换配置对象。

- **`AtomicStampedReference<V>`**：CAS 带 `int stamp` 版本号 —— 解决 ABA（上一课 0021 例子）。每次修改版本号 +1，即使引用一样，版本号不同也 CAS 失败。

- **`AtomicMarkableReference<V>`**：CAS 带 `boolean mark` —— 适合「只关心是否被修改过」而不是「修改了几次」的场景（比如无锁跳表节点删除标记）。

```
AtomicReference<String> ref = new AtomicReference<>("A");
ref.compareAndSet("A", "B");              // ✅ 引用相等

// 陷阱：引用比较不是 equals
String s1 = new String("hello");
String s2 = new String("hello");
AtomicReference<String> r = new AtomicReference<>(s1);
r.compareAndSet(s2, "world");             // ❌ 失败，s1 != s2（对象引用不同）
```

## 面试场景 5：Atomic 数组类型

🧑‍💻 你

`AtomicIntegerArray` 让**数组的每个元素**都能做 CAS 更新，比 `volatile int[]` 强：`volatile int[]` 只保证「数组引用」的可见性，不保证「元素」的原子更新。

```
AtomicIntegerArray arr = new AtomicIntegerArray(new int[]{1, 2, 3, 4, 5});
arr.getAndIncrement(2);                    // 索引 2 的元素 +1
arr.compareAndSet(0, 1, 100);              // 索引 0 的元素 从 1 → 100
System.out.println(arr);                   // [100, 2, 4, 4, 5]
```

典型用途：并发场景的直方图/计数桶、位图、无锁哈希表。

## 面试场景 6：字段更新器（Field Updater）

🎤 面试官

为什么 JDK 要提供 `AtomicIntegerFieldUpdater`？直接用 `AtomicInteger` 不行吗？

🧑‍💻 你

行是行，但**省内存**。`AtomicInteger` 是包装类，每实例除了 `int` 值本身还有对象头 + `Unsafe` 静态引用 —— 每个约 16-24 字节。如果一个类要有百万个实例、每个都带一个原子整数字段，用 `AtomicInteger` 就多用几十 MB。

用 `AtomicIntegerFieldUpdater` 可以对*已有的 volatile 字段*做原子更新，字段还是原始 `int`：

```
public class Counter {
volatile int count;                    // ← 普通 volatile int，不是 AtomicInteger

private static final AtomicIntegerFieldUpdater<Counter> UPDATER
= AtomicIntegerFieldUpdater.newUpdater(Counter.class, "count");

public void inc() {
UPDATER.incrementAndGet(this);     // 反射拿到字段偏移，走 CAS
}
}
```

硬性要求：字段必须 **`volatile`**；**不能 `static`**；**不能 `final`**；必须可通过反射访问。AQS 内部大量用 field updater 来更新 `state`、`waitStatus` 等 —— 就是为了省内存和减少对象层次。

## 面试场景 7：LongAdder 的原理（★核心）

🎤 面试官

`LongAdder` 为什么比 `AtomicLong` 快？

🧑‍💻 你

核心思想：**把一个热点变量拆成多个 Cell，各线程分散写**。

```
public class LongAdder {
volatile long base;                    // 无竞争时直接写 base
volatile Cell[] cells;                 // 竞争激烈时展开 Cell 数组

@sun.misc.Contended                    // ← 关键：防伪共享
static final class Cell {
volatile long value;
}
}
```

`add(x)` 流程：

1. 先 CAS `base` —— 无竞争时一次成功，直接结束。

2. 竞争到了 → 按 `Thread.probe` 哈希到 `cells[?]`，CAS 该 Cell。

3. 还失败 → 说明该 Cell 也竞争 → 换个 Cell 或扩容 `cells`。

`sum()`：

```
public long sum() {
long v = base;
if (cells != null) for (Cell c : cells) if (c != null) v += c.value;
return v;
}
```

把「一个变量的高频写」变成「多个变量的低频写 + 一次求和读」。**写吞吐随核数线性扩展**；代价是读时求和 O(cells 数量)、内存占用大一些、以及 `sum` 不是原子快照。

追问 `@Contended` 是干嘛的？

防止**伪共享（false sharing）**。CPU 缓存以 cache line 为单位（一般 64 字节），如果两个 Cell 的 `value` 在同一 cache line 里，即使两个线程各写各的 Cell，仍会因为 cache line 独占权反复失效，性能雪崩。`@Contended` 让 JVM 给字段前后各填 128 字节，把它单独放在一个 cache line 里。启用需 `-XX:-RestrictContended`。

## 面试场景 8：LongAdder vs AtomicLong 完整对比

维度AtomicLongLongAdder

数据结构单个 volatile longbase + Cell[] 数组
写性能（低竞争）相当相当
写性能（高竞争）差（CAS 一直失败）**好几十倍**（分片）
读性能O(1)O(cells 数)
读一致性强（精确瞬时值）弱（求和期间可能被写入，结果近似）
内存占用小大（Cell + padding）
典型用途需要精确计数、序号生成高并发统计、监控指标（QPS、点赞）

陷阱 别以为「LongAdder 就是升级版 AtomicLong」。`sum()` 不是原子快照 —— 求和期间其他线程写入的值可能算进也可能算不进。*需要读到精确值*（比如原子序号生成器 `ID_SEQ.incrementAndGet()`）必须用 `AtomicLong`。

## 面试场景 9：LongAccumulator vs LongAdder

🧑‍💻 你

`LongAdder` 只做加法；`LongAccumulator` 支持任意二元函数，本质是「可自定义累积规则的 Adder」：

```
// 求最大值
LongAccumulator max = new LongAccumulator(Long::max, Long.MIN_VALUE);
max.accumulate(5); max.accumulate(3); max.accumulate(8);
System.out.println(max.get());              // 8

// 求乘积
LongAccumulator product = new LongAccumulator((a, b) -> a * b, 1);
product.accumulate(2); product.accumulate(3); product.accumulate(4);
System.out.println(product.get());          // 24
```

只要函数**可交换、可结合**（因为多线程并发累积顺序不定），就能用 `LongAccumulator`。求和/最大值/最小值/乘积都可以。

## 面试场景 10：实际应用 & 选型建议

🧑‍💻 你

- **普通计数器（低并发）**：`AtomicInteger` / `AtomicLong`，简单直接。

- **高并发监控指标**（QPS、访问量、点赞数）：`LongAdder`，读不精确无所谓。

- **精确序号生成**（订单号、日志序号）：`AtomicLong`，需要精确瞬时值。

- **状态机切换**：`AtomicReference<State>` + `compareAndSet`，用于状态原子迁移。

- **对象池节点复用**：`AtomicStampedReference`，避免 ABA。

- **类里已有字段要原子更新**：`AtomicIntegerFieldUpdater` 省内存。AQS 就是最典型的例子。

- **直方图/计数桶**：`AtomicIntegerArray`，元素级 CAS。

- **自定义累积规则**：`LongAccumulator`，比如无锁 min/max。

## 💻 代码验证

### 验证 1：AtomicInteger 常用方法

```
import java.util.concurrent.atomic.AtomicInteger;

AtomicInteger a = new AtomicInteger(10);
System.out.println(a.getAndIncrement());    // 10  返回旧值再 +1 → 11
System.out.println(a.incrementAndGet());    // 12  先 +1 再返回 → 12
System.out.println(a.getAndAdd(5));         // 12  返回旧值再 +5 → 17
System.out.println(a.addAndGet(3));         // 20
System.out.println(a.compareAndSet(20, 100));   // true → 100
System.out.println(a.compareAndSet(20, 999));   // false（已经不是 20）
System.out.println(a.updateAndGet(x -> x * 2)); // 200
System.out.println(a.accumulateAndGet(50, Math::max));  // 200（200 > 50）
```

### 验证 2：LongAdder vs AtomicLong 性能对比

```
import java.util.concurrent.atomic.*;

public class AdderBench {
public static void main(String[] args) throws Exception {
int threads = 16, times = 5_000_000;

AtomicLong al = new AtomicLong();
long t1 = bench(threads, () -> { for (int i=0;i<times;i++) al.incrementAndGet(); });
System.out.printf("AtomicLong: %.2f ms  final=%d%n", t1/1e6, al.get());

LongAdder la = new LongAdder();
long t2 = bench(threads, () -> { for (int i=0;i<times;i++) la.increment(); });
System.out.printf("LongAdder : %.2f ms  final=%d%n", t2/1e6, la.sum());
}

static long bench(int nt, Runnable r) throws Exception {
Thread[] ts = new Thread[nt];
for (int i=0;i<nt;i++) ts[i] = new Thread(r);
long s = System.nanoTime();
for (Thread t : ts) t.start();
for (Thread t : ts) t.join();
return System.nanoTime() - s;
}
}
// 典型结果（8 核机器）：
// AtomicLong: 3800 ms   final=80000000
// LongAdder :  420 ms   final=80000000
// ← LongAdder 快 9-10 倍
```

### 验证 3：AtomicIntegerFieldUpdater 用法

```
import java.util.concurrent.atomic.AtomicIntegerFieldUpdater;

public class UserVisitCount {
volatile int visits;                    // ← 普通 volatile int

private static final AtomicIntegerFieldUpdater<UserVisitCount> V
= AtomicIntegerFieldUpdater.newUpdater(UserVisitCount.class, "visits");

public void visit() {
V.incrementAndGet(this);            // 原子 +1
}

public static void main(String[] args) throws Exception {
UserVisitCount u = new UserVisitCount();
Thread[] ts = new Thread[8];
for (int i=0;i<ts.length;i++) ts[i] = new Thread(() -> {
for (int j=0;j<100_000;j++) u.visit();
});
for (Thread t : ts) t.start();
for (Thread t : ts) t.join();
System.out.println(u.visits);       // 800000 精确
}
}
```

### 验证 4：AtomicReference 状态机迁移

```
import java.util.concurrent.atomic.AtomicReference;

enum State { INIT, RUNNING, STOPPED }

public class StateMachine {
private final AtomicReference<State> state = new AtomicReference<>(State.INIT);

public boolean start() {
return state.compareAndSet(State.INIT, State.RUNNING);      // 只能从 INIT 转
}
public boolean stop() {
return state.compareAndSet(State.RUNNING, State.STOPPED);   // 只能从 RUNNING 转
}

public static void main(String[] args) {
StateMachine m = new StateMachine();
System.out.println(m.start());   // true
System.out.println(m.start());   // false（重复启动被拒绝）
System.out.println(m.stop());    // true
System.out.println(m.stop());    // false（已经 stopped）
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 AtomicInteger 保证原子性和可见性各靠什么？</summary>

原子性靠 `Unsafe.compareAndSwapInt`（CPU 的 CAS 指令）；可见性靠 `value` 字段的 `volatile`。缺一不可。

</details>

<details>

<summary>Q2 `AtomicIntegerFieldUpdater` 适合什么场景？字段有什么硬性要求？</summary>

类实例数量极多、每个都要有原子字段时省内存。字段必须 `volatile`、非 `static`、非 `final`、可反射访问。AQS 大量用它。

</details>

<details>

<summary>Q3 LongAdder 相比 AtomicLong 的核心机制是什么？代价是什么？</summary>

机制：把热点变量拆成 base + Cell[] 分片，各线程 CAS 自己的 Cell，读时求和。代价：读慢（O(cells)）、读不精确（sum 非原子快照）、内存占用大（Cell + Contended padding）。

</details>

<details>

<summary>Q4 `@Contended` 注解解决什么问题？</summary>

解决伪共享 false sharing。让字段独占一个 CPU cache line，避免多个字段在同 cache line 上导致 core 间反复失效。JVM 需要 `-XX:-RestrictContended` 才对用户代码生效。

</details>

<details>

<summary>Q5 生成全局唯一订单号，该用 AtomicLong 还是 LongAdder？为什么？</summary>

必须 `AtomicLong`。订单号要精确瞬时值不能重复，`AtomicLong.incrementAndGet` 提供强一致原子递增；`LongAdder.sum` 是近似值不能保证唯一性。

</details>

#### 📖 原文

-

- JDK · `java.util.concurrent.atomic` 包总览

- JEP 142 · Reduce Cache Contention on Specified Fields（`@Contended` 的 JEP）

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0023：**AQS 详解** —— 并发章节最难的一节。ReentrantLock、Semaphore、CountDownLatch 的共同底盘，state + CLH 队列 + 模板方法，一次讲透。

💬 想问「伪共享具体怎么发生？」「LongAdder 的 Cell 数组怎么扩容？」「lazySet 什么时候用？」—— 都可以直接问我。


