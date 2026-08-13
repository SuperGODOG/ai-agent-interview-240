> Lesson 0020 · 阶段三 · Java 并发 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0020 · JMM &amp; happens-before &amp; volatile 全面解析

这一课是并发编程的**地基**：**JMM (Java Memory Model)** 是 Java 语言层给出的抽象内存规范，屏蔽了不同 CPU 架构（x86/ARM）的差异；**happens-before** 是 JMM 给程序员的「可见性契约」，让你不必去背 CPU 指令；**volatile** 是这套体系里*最轻量的同步原语*，成本远低于 `synchronized`，但也*不能替代锁*。面试的高频套路是「JMM → 三大问题 → volatile 语义 → DCL 单例 → 为什么不保证原子性」一条链问穿，能不能答出层次感，是判断你懂不懂并发的分水岭。原文见 。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Java 内存模型 JMM 是什么？和 JVM 内存结构（堆/栈/方法区）是同一个东西吗？</summary>

**完全不同的两个概念**。JMM 是一套「线程之间怎么通过共享变量通信」的*抽象规范*（属于 Java 语言层的并发契约）；JVM 内存结构是 *运行时数据区的物理划分*（堆、方法区、虚拟机栈、本地方法栈、程序计数器）。JMM 关心「可见性、原子性、有序性」；JVM 内存结构关心「对象存哪儿、方法怎么调用」。第 1 题会展开。

</details>

<details>

<summary>Q0.2 `volatile int i;` 然后 `i++;`，多线程下能保证 `i` 一定正确吗？</summary>

**不能**。`volatile` 只保证「读」和「写」两个动作各自可见，但 `i++` 是「读 → 加 1 → 写」三步复合操作，中间会被别的线程插入。要原子累加得用 `AtomicInteger` 或 `synchronized`。第 6 题会用代码演示丢更新。

</details>

## 面试场景 1：什么是 JMM (Java Memory Model)？为什么需要它？⭐核心

🎤 面试官

你能说一下 Java 内存模型是什么吗？为什么 Java 要搞一套 JMM？

🧑‍💻 你

**JMM 是 Java 语言层定义的一套并发内存规范**，它规定了「线程之间如何通过共享变量交互」「一个线程对共享变量的写，什么时候对另一个线程可见」以及「哪些指令可以重排、哪些不能重排」。

需要 JMM 的根本原因是 **CPU 架构差异**：

- x86 是*强内存模型*（Total Store Order），写操作基本按序对其他核心可见；

- ARM/PowerPC 是*弱内存模型*，需要显式内存屏障才能保证顺序；

- 再加上 CPU 有 L1/L2/L3 *多级缓存*、*写缓冲区 (Store Buffer)*、*失效队列 (Invalidate Queue)*，一个线程写主存，别的线程未必立即看到。

如果没有 JMM，Java 程序员要写正确的并发代码就得懂每种 CPU 的指令。有了 JMM，程序员只需要遵守「happens-before」的抽象契约，JVM 会自动帮你在不同平台上插入合适的屏障。**JMM 的本质是「隔离层」，让 Java「一次编译，到处正确地并发运行」**。

追问 JMM 是不是就是 JVM 内存结构？

**不是**，这是最常见的混淆。JMM (Java Memory Model) 是*抽象的并发规范*，讨论「线程间可见性、原子性、有序性」的规则，抽象概念是「主内存」和「工作内存」。JVM 内存结构（或叫「运行时数据区」）是*物理的内存划分*，包括堆、方法区、虚拟机栈、本地方法栈、程序计数器，讨论「对象放哪儿、方法怎么调用」。两者甚至不在一个抽象层次：JMM 是规范，JVM 内存结构是实现。

## 面试场景 2：主内存 vs 工作内存 & 8 种原子操作 ⭐核心

🎤 面试官

JMM 里的主内存和工作内存分别是什么？它们对应硬件的哪一层？

🧑‍💻 你

JMM 定义了两个抽象概念：

- **主内存 (Main Memory)**：存储所有*共享变量*（实例字段、静态字段、数组元素）。物理对应*堆内存 + 方法区*，硬件上对应*DRAM 主存*。

- **工作内存 (Working Memory)**：每个线程*私有*的变量副本区。物理对应*虚拟机栈的一部分*，硬件上对应*CPU 寄存器 + L1/L2 缓存 + Store Buffer*。

关键约束：**线程不能直接读写主内存，必须先把变量拷贝到工作内存操作，再刷回主内存**。线程之间不能直接通信，必须通过主内存中转。

整个交互被 JMM 规定为 **8 种不可再分的原子操作**：

操作作用对象说明

`lock`主内存把变量标识为某个线程独占
`unlock`主内存释放锁定，允许其他线程访问
`read`主内存 → 传输线把变量值从主内存读出，准备传输
`load`传输线 → 工作内存把 read 出来的值放入工作内存副本
`use`工作内存把变量值传给执行引擎（每次遇到需要用到变量的字节码指令）
`assign`工作内存把执行引擎的值赋给工作内存变量
`store`工作内存 → 传输线把工作内存的值传出，准备写回
`write`传输线 → 主内存把 store 出来的值写回主内存

**read + load** 必须成对且顺序执行（可不连续），**store + write** 同理。`lock/unlock` 是 `synchronized` 的底层实现依据。

追问 一个线程改了变量，另一个线程立即能看到吗？

**不一定**。修改后要经过 `assign → store → write` 才能进主内存，另一个线程还要 `read → load → use` 才能读到新值。而且如果没有 `volatile` 或锁的*刷新语义*，JIT 可能把工作内存的值缓存住迟迟不刷回主内存，另一个线程可能永远看不到（这就是「可见性问题」的本质）。

## 面试场景 3：并发三大问题 —— 原子性、可见性、有序性

🎤 面试官

并发编程的三大问题是什么？分别对应什么解决方案？

🧑‍💻 你

问题含义根源解决方案

**原子性**
一组操作要么全做完，要么都不做，中间不被打断
线程切换 + 复合操作（`i++` 是 3 步）
`synchronized` / `Lock` / `Atomic*`（CAS）

**可见性**
一个线程的写对其他线程立即可见
CPU 缓存 + 工作内存副本没刷回主内存
`volatile` / `synchronized` / `final`

**有序性**
代码执行顺序符合程序员的预期
编译器优化重排 + CPU 乱序执行 (OoOE)
`volatile`（禁止重排）/ `synchronized` / `happens-before` 规则

面试里能把「问题 → 根源 → 方案」串成完整的三段论，比零散背概念高级得多。

陷阱 `synchronized` **一把梭**三个都能解决，但性能代价最大。工程实践里应该「用最轻的工具」：只需要可见性 → `volatile`；只需要原子累加 → `AtomicInteger`；需要临界区互斥 → `synchronized`/`ReentrantLock`。

## 面试场景 4：happens-before 8 条规则 ⭐核心必背

🎤 面试官

happens-before 是什么？能不能列几条规则？

🧑‍💻 你

**happens-before** 是 JMM 给程序员的可见性契约。它定义了「如果 A happens-before B，那么 A 的所有操作结果，对 B 都是可见的」。注意它*不代表 A 一定先于 B 在时间上执行*，只要求「A 的结果对 B 可见」这层语义成立 —— JVM 可以自由重排，只要不违反契约。

常考 8 条规则：

1. **程序次序规则**：同一线程内，前面的操作 happens-before 后面的操作（*但允许重排，只要单线程结果不变*）。

2. **监视器锁规则**：对一个锁的 *unlock* happens-before 后续对这把锁的 *lock*。

3. **volatile 变量规则**：对一个 volatile 变量的*写* happens-before 后续对它的*读*。

4. **传递性**：A hb B，B hb C，则 A hb C。（*组合出复杂可见性的关键*）

5. **线程启动规则**：主线程调用 `thread.start()` happens-before 子线程内的任何操作。

6. **线程终止规则 (join)**：子线程内的所有操作 happens-before 主线程 `thread.join()` 成功返回。

7. **线程中断规则**：`thread.interrupt()` happens-before 被中断线程检测到中断（`isInterrupted()`/抛 `InterruptedException`）。

8. **对象终结规则**：对象构造完成（构造函数结束）happens-before `finalize()` 方法的开始。

追问 happens-before 和实际执行顺序是一回事吗？

**不是**。happens-before 只是*可见性契约*，规定「如果 A hb B，A 的结果对 B 可见」。JVM 完全可以对 A、B 做重排，只要不违反这层可见性。举个反例：`int a = 1; int b = 2;` 在程序次序上 a 先于 b，但两者互不依赖，JIT 可能真的先执行 b 再执行 a —— 只要最终两个变量的值对下游可见就行。

追问 为什么要引入 happens-before 而不是直接说「一个线程改的，另一个立刻能看到」？

「立刻能看到」这个语义太强，等于要求所有写都直穿主存 —— 硬件性能会崩。JMM 用 happens-before 只对*关键操作*（volatile 写、锁释放、start/join）承诺可见性，其他操作允许 CPU/JIT 自由重排优化。这是**性能与正确性的折中**。

## 面试场景 5：volatile 的两大语义 ⭐核心

🎤 面试官

`volatile` 关键字到底做了什么？

🧑‍💻 你

`volatile` 给变量赋予两条语义：

1. **可见性**：

- 写 volatile 变量时，JMM 会立即把工作内存的值刷回主内存；

- 读 volatile 变量时，JMM 会强制从主内存重新加载（而不是用工作内存的副本）。

硬件层面对应 *写操作后加 StoreLoad 屏障* —— 在 x86 上通常是 `lock addl $0, (%rsp)` 指令，该指令会 flush store buffer 并让其他 CPU 缓存行失效。

2. **禁止指令重排**：JVM 会在 volatile 读写前后插入内存屏障：

- *volatile 写之前*：`StoreStore`（禁止普通写和 volatile 写重排）

- *volatile 写之后*：`StoreLoad`（禁止 volatile 写和后续读重排）

- *volatile 读之后*：`LoadLoad`（禁止 volatile 读和后续读重排）

- *volatile 读之后*：`LoadStore`（禁止 volatile 读和后续写重排）

但 volatile **不提供原子性**，也**不提供互斥**（多个线程可以同时读写同一 volatile 变量）。

追问 x86 架构下 volatile 的 StoreLoad 屏障对应什么 CPU 指令？

x86 通常用 `lock addl $0, (%rsp)` —— 一个「空操作 + lock 前缀」的组合。`lock` 前缀会：1) 锁总线或缓存行；2) flush 当前 CPU 的 store buffer；3) 使其他 CPU 的对应缓存行失效（走 MESI 协议的 Invalidate 消息）。也可以用 `mfence` 指令，但 HotSpot 更倾向 `lock` 前缀（在多数场景下延迟更低）。

## 面试场景 6：volatile 为什么不保证原子性？⭐经典

🎤 面试官

既然 volatile 保证可见性，为什么 `volatile int i; i++;` 在多线程下还会丢更新？

🧑‍💻 你

关键在于 `i++` 不是一条原子指令，而是 **3 步复合操作**：

1. `read + load`：从主内存读 `i` 到工作内存（假设读到 5）；

2. `use + assign`：执行加 1（工作内存里变成 6）；

3. `store + write`：写回主内存。

volatile 只保证「每一步单独的 read 和 write 都能看到最新值」，**不保证 3 步之间不被打断**。典型丢更新场景：

```
时刻 T1：线程 A 读 i = 5（放到工作内存）
时刻 T2：线程 B 读 i = 5（放到工作内存）
时刻 T3：线程 A 算出 6，写回主内存 → i = 6
时刻 T4：线程 B 算出 6，写回主内存 → i = 6（本应是 7，丢了一次更新）
```

正确做法：

- 用 `AtomicInteger.incrementAndGet()`（底层 CAS，无锁高效）；

- 用 `synchronized` 或 `ReentrantLock` 保护 `i++`；

- 用 `LongAdder`（高并发累加最快）。

追问 那 volatile 到底适合什么场景？

适合**「一写多读」的状态标志**和**「独立写、独立读」的引用发布**：

- 状态标志：`volatile boolean running = true;`，一个线程置 false，其他线程立即感知并退出。

- DCL 单例：`private volatile static Instance instance;`（下一节讲）。

- 发布不可变对象引用：一次性赋值，别的线程读取。

不适合**读改写**（`i++`、`count += n`）和**依赖旧值算新值**的场景。

## 面试场景 7：DCL 双重检查锁单例为什么必须用 volatile ⭐经典

🎤 面试官

你写一个线程安全的懒加载单例，然后解释为什么 `instance` 要加 volatile。

🧑‍💻 你

标准 DCL (Double-Checked Locking) 单例：

```
public class Singleton {
private volatile static Singleton instance;   // ★ 必须 volatile

private Singleton() {}

public static Singleton getInstance() {
if (instance == null) {                    // 第 1 次检查：无锁快路径
synchronized (Singleton.class) {
if (instance == null) {            // 第 2 次检查：防止多线程都过了第 1 次
instance = new Singleton();    // ★ 危险点
}
}
}
return instance;
}
}
```

关键在 `instance = new Singleton()`，这行代码**不是原子的**，JVM 会拆成 3 步字节码：

1. **分配内存**：`memory = allocate();`

2. **初始化对象**：`ctorInstance(memory);`（调用构造函数）

3. **赋值引用**：`instance = memory;`（把地址赋给引用变量）

没有 `volatile`，JIT 允许把顺序重排为 **1 → 3 → 2**（因为在单线程视角结果一样，符合 as-if-serial）。这时候如果另一个线程恰好走到第 1 个 `if (instance == null)`，**会看到 instance 已经不为 null（步骤 3 完成），但对象还没构造完（步骤 2 没跑）**—— 直接返回一个半成品对象，用起来就是各种诡异 NPE 或字段默认值。

加了 `volatile`：步骤 3 的写前面有 `StoreStore` 屏障，禁止和步骤 2 重排；步骤 3 后面有 `StoreLoad` 屏障，确保其他线程读到 `instance` 时能看到构造完整的对象。

追问 DCL 的 volatile 如果去掉，「读到半成品对象」概率有多大？

取决于 CPU 架构和 JIT 优化。x86 强内存模型下这种重排概率极低（几乎观测不到）；ARM 弱内存模型下明显可以复现（Android 早期就踩过）。**但不能因为「x86 上少见」就不加 volatile** —— Java 程序声称跨平台正确，就必须遵守 JMM。而且 JIT 越来越激进，未来 x86 上也可能重排。

追问 有没有更简单的线程安全单例？

有，而且实践中更推荐：

- **静态内部类**：利用 JVM *类初始化*的天然线程安全（`<clinit>` 有锁），无需 volatile 无需锁。

- **枚举单例**：`public enum Singleton { INSTANCE; }` —— Effective Java 推荐，还能防反序列化和反射攻击。

DCL 主要考察你对 JMM 和重排的理解，工程里能用枚举就用枚举。第 0044 课会专门讲单例的 5 种写法对比。

## 面试场景 8：内存屏障 Memory Barrier 有哪几种？

🧑‍💻 你

JMM 抽象出 4 种内存屏障，用来禁止特定类型的重排：

屏障作用典型使用

`LoadLoad`禁止「读1」和「读2」重排volatile 读之后
`LoadStore`禁止「读」和后续「写」重排volatile 读之后
`StoreStore`禁止「写1」和「写2」重排volatile 写之前
`StoreLoad`禁止「写」和后续「读」重排（*最贵*）volatile 写之后

不同 CPU 架构对应不同指令：

- **x86（强内存模型）**：天然保证 `LoadLoad`/`LoadStore`/`StoreStore`，只需要在 volatile 写后插入 `lock addl` 或 `mfence` 提供 `StoreLoad`。

- **ARM（弱内存模型）**：4 种屏障都要显式指令，如 `dmb ish`、`dmb ishst`、`dmb ishld`。

这就是「同一份字节码，跨 CPU 都正确」的秘密 —— JVM 根据目标平台自动翻译屏障。

## 面试场景 9：as-if-serial 语义

🧑‍💻 你

**as-if-serial**：无论编译器和 CPU 怎么重排，*单线程*的执行结果不能改变。也就是「表现得就像顺序执行一样」。

```
double pi = 3.14;         // A
double r = 1.0;           // B
double area = pi * r * r; // C（依赖 A 和 B）
```

A、B 之间没有数据依赖，可以任意重排；C 依赖 A 和 B，绝不能重排到 A 或 B 之前 —— 否则单线程结果都不对。

**关键点**：as-if-serial 只保护*单线程*。多线程下，A 和 B 的重排完全可能被其他线程观察到（因为其他线程看不到「依赖关系」这个上下文）。所以多线程写共享变量时不能依赖代码书写顺序，必须用 volatile / synchronized 建立 happens-before 关系。

陷阱 as-if-serial 给了程序员「代码顺序执行」的错觉，但这个错觉只在单线程内成立。经典反例：一个线程做 `data = load(); ready = true;`，另一个线程做 `if (ready) use(data);` —— 单线程看两句无关，允许重排；多线程下另一个线程可能看到 `ready = true` 但 `data` 还是空。要么把 `ready` 声明为 volatile，要么用锁。

## 面试场景 10：synchronized 也能保证可见性和有序性吗？

🎤 面试官

都说 volatile 保证可见性和有序性，那 synchronized 呢？

🧑‍💻 你

**synchronized 三个都保证**：原子性、可见性、有序性。理由分别是：

- **原子性**：`monitorenter` / `monitorexit` 之间是*互斥临界区*，同一时刻只有一个线程能进入，天然原子。

- **可见性**：JMM 规定，*解锁前必须把工作内存的变量刷回主内存*（对应 `store + write`），*加锁时必须清空工作内存并重新从主内存读*（对应 `read + load`）。所以锁的进入和退出天然带可见性语义。

- **有序性**：`monitorenter`/`monitorexit` 是*屏障点*，临界区内的指令不能重排到临界区外，反之亦然。多个线程串行进入临界区，天然满足「按加锁顺序观察」的有序性。

**但 synchronized 内部允许重排**：临界区内两条无依赖的指令仍然可能被 JIT 重排 —— 只要单线程语义不变。有序性是*「线程间的有序性」*，不是*「指令级别不重排」*。

追问 volatile 和 synchronized 相比，性能差多少？该怎么选？

volatile 是*无锁*操作，成本只是几条 CPU 屏障指令；synchronized 涉及*加锁/解锁*（哪怕是偏向锁/轻量级锁也有 CAS 开销）、可能*线程阻塞*、*上下文切换*，一般贵一个数量级。选型原则：

- 只需要**可见性 + 有序性**（比如状态标志、单例引用）→ volatile；

- 需要**原子性**（复合操作、临界区）→ synchronized / Lock / Atomic。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：可见性问题 —— 没有 volatile 会「死循环」

```
public class VisibilityDemo {
// ★ 去掉 volatile 试试，多数 JIT 优化下子线程可能永远读不到 running = false
private static volatile boolean running = true;

public static void main(String[] args) throws InterruptedException {
Thread worker = new Thread(() -> {
long count = 0;
while (running) {              // 读 volatile 强制走主内存
count++;
}
System.out.println("worker 退出，count = " + count);
});
worker.start();

Thread.sleep(1000);
running = false;                   // 写 volatile 立即刷主内存
System.out.println("main 设置 running = false");
}
}
```

把 `volatile` 去掉，JIT 很可能把 `while (running)` 优化成 `while (true)`（因为它「看不到」别的线程会改 running），worker 线程永远不会退出。加上 volatile 后正常 1 秒退出。这是**可见性问题最直观的复现**。

### 验证 2：volatile 不保证原子性 —— i++ 丢更新

```
public class VolatileAtomicityDemo {
private static volatile int count = 0;

public static void main(String[] args) throws InterruptedException {
Thread[] threads = new Thread[10];
for (int i = 0; i < 10; i++) {
threads[i] = new Thread(() -> {
for (int j = 0; j < 10_000; j++) {
count++;               // ★ 非原子操作
}
});
threads[i].start();
}
for (Thread t : threads) t.join();
// 期望 100_000，实际每次运行都不同，通常在 50_000 ~ 99_000 之间
System.out.println("count = " + count);
}
}
```

10 个线程各累加 1 万次，期望值是 10 万，实际几乎每次都*少于* 10 万 —— 就是丢更新。改成 `AtomicInteger count = new AtomicInteger();` 和 `count.incrementAndGet();` 就会得到精确 100_000。

### 验证 3：DCL 单例 —— volatile 保护对象构造

```
public class Singleton {
// ★ 关键：volatile 禁止 new Singleton() 的 3 步重排
private volatile static Singleton instance;

private final int value;

private Singleton() {
// 模拟复杂构造过程
this.value = computeSomething();
}

public static Singleton getInstance() {
if (instance == null) {                        // 第 1 次检查：走无锁快路径
synchronized (Singleton.class) {
if (instance == null) {                // 第 2 次检查：加锁后再确认
instance = new Singleton();        // 分配 + 构造 + 赋值 3 步
}
}
}
return instance;
}

private int computeSomething() {
return 42;
}
}
```

如果去掉 `volatile`，某个线程可能通过第 1 个 `if (instance == null)` 时，`instance` 已被赋值但对象构造未完成（`value` 还是 0），拿到「半成品单例」。

### 验证 4：重排导致的多线程可见性问题（DCL 的等价模型）

```
public class ReorderDemo {
// 去掉 volatile，多线程下可能出现 x=0, y=0 的情况
private static /* volatile */ int a = 0;
private static /* volatile */ int b = 0;
private static int x, y;

public static void main(String[] args) throws Exception {
for (int i = 0; i < 1_000_000; i++) {
a = 0; b = 0; x = 0; y = 0;

Thread t1 = new Thread(() -> { a = 1; x = b; });
Thread t2 = new Thread(() -> { b = 1; y = a; });
t1.start(); t2.start();
t1.join();  t2.join();

if (x == 0 && y == 0) {
System.out.println("第 " + i + " 次出现 x=0 && y=0（发生了重排）");
break;
}
}
}
}
```

按顺序思考「a=1 → x=b」和「b=1 → y=a」，怎么都推不出 `x=y=0`。但在实际 CPU 上（尤其 x86 之外）会因为 store buffer 延迟出现这个「不可能」的结果。跑一晚上大概率能看到。加上 `volatile` 后就不会再出现 —— 这就是内存屏障的作用。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话解释 JMM 和 JVM 内存结构的区别。</summary>

JMM 是*抽象规范*，定义线程之间通过主内存/工作内存交互的可见性、原子性、有序性规则；JVM 内存结构是*物理划分*，指堆、方法区、虚拟机栈、本地方法栈、程序计数器五大运行时数据区。前者关心「并发行为」，后者关心「数据存放」。

</details>

<details>

<summary>Q2 happens-before 的传递性能带来什么好处？举个例子。</summary>

让你不必挨个证明每对操作的可见性，只需组合基本规则即可。例：主线程 `a = 1;`（普通写）→ `flag = true;`（volatile 写） 与 子线程 `if (flag)`（volatile 读）→ `read a`。由「程序次序 hb → volatile hb → 程序次序 hb」+传递性可得 `a = 1` hb `read a`，所以子线程读到的一定是 1。

</details>

<details>

<summary>Q3 volatile 变量能不能替代锁保证 `i++` 的原子性？为什么？</summary>

不能。`i++` 由「读 → 加 1 → 写」3 步组成，volatile 只保证单次读和单次写各自可见，不保证 3 步整体不被打断。多个线程可能同时读到旧值，各自加 1，写回同一个新值，导致丢更新。要用 `AtomicInteger` 或 `synchronized`。

</details>

<details>

<summary>Q4 DCL 单例里如果不加 volatile 会出什么问题？</summary>

其他线程可能通过第 1 个 `if (instance == null)` 拿到「引用已赋值但对象还没构造完」的半成品对象。因为 `new Singleton()` 是「分配内存 → 构造对象 → 赋值引用」3 步，JIT 可能把顺序重排为「分配 → 赋值引用 → 构造」，另一线程恰好在这个空窗看到非 null 的引用，返回后一用就 NPE 或读到默认值。

</details>

<details>

<summary>Q5 synchronized 保证可见性的底层原理是什么？</summary>

JMM 规定：*加锁*时必须清空工作内存中该锁保护的变量副本，重新从主内存加载（`read + load`）；*解锁*前必须把工作内存的修改刷回主内存（`store + write`）。因此「解锁 happens-before 后续加锁」这条规则天然保证：一个线程解锁前的所有写，对下一个加同一把锁的线程都可见。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JLS §17 · Threads and Locks —— happens-before 和 JMM 的官方规范原文

- Doug Lea · The JSR-133 Cookbook for Compiler Writers —— 内存屏障与 volatile 实现的经典参考

#### 🔗 关联课件

-  —— 上一课

-  —— 下一课

-  —— 解决 `i++` 原子性的正确姿势

-

#### 🧭 下一课预告

Lesson 0021：**CAS (Compare-And-Swap) 与 ABA 问题** —— volatile 只解决可见性，CAS 才是「无锁并发」的原子性基石。`AtomicInteger` 内部就是 CAS + volatile 的组合拳。

💬 有任何疑问 —— 「happens-before 到底怎么用来证明可见性？」「x86 上没 volatile 也能跑对，怎么办？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


