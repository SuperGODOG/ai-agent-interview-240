> Lesson 0019 · 阶段三 · 并发编程 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0019 · synchronized 深入 & 锁升级

`synchronized` 是并发面试的**守门员**——几乎没有一个 Java 后端面试能绕过它。但真正拉开档次的不是「synchronized 是什么」，而是「**它怎么升级**」「**Mark Word 里藏了什么**」「**它和 ReentrantLock 到底谁强**」。这一课把  和  里 synchronized 相关的所有考点串起来讲透。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `synchronized` 修饰实例方法、静态方法、代码块 `synchronized(obj)`，分别锁的是什么？</summary>

实例方法锁 `this`（当前对象实例）；静态方法锁 `Class` 对象（该类唯一）；代码块锁括号里指定的对象。三者互不干扰——静态方法和实例方法用的是*两把不同的锁*。

</details>

<details>

<summary>Q0.2 `synchronized` 从 JDK 6 之后会走哪几个锁状态？状态之间能双向切换吗？</summary>

四个状态：**无锁 → 偏向锁 → 轻量级锁 → 重量级锁**。*只能升级，不能降级*——这是 HotSpot 的历史决策，为了实现简单。JDK 15+ 偏向锁默认关闭，JDK 18+ 彻底移除相关参数。

</details>

## 面试场景 1：synchronized 的三种用法，分别锁什么？

🎤 面试官

`synchronized` 有三种使用方式，你能分别说说它们锁的是谁吗？

🧑‍💻 你

1. **修饰实例方法**：锁 `this`（当前对象实例）。同一个对象的所有 synchronized 实例方法互斥；不同对象各自持有各自的锁。

2. **修饰静态方法**：锁 `ClassName.class`（类对象，JVM 里唯一）。*所有实例*共享同一把锁——只要一个线程在跑该类的任意 synchronized static 方法，其他线程都得等。

3. **修饰代码块** `synchronized(lockObject) { ... }`：锁括号里指定的对象。粒度最细，可以只锁需要保护的那几行。

```
public class Demo {
public synchronized void a()        { }  // 锁 this
public static synchronized void b() { }  // 锁 Demo.class
public void c() {
synchronized (this) { }              // 等价于 a()
}
public void d() {
synchronized (Demo.class) { }        // 等价于 b()
}
}
```

陷阱 别用 `synchronized(String)` —— 字符串常量池会把字面量 `"lock"` 变成全 JVM 唯一的对象，等于把锁范围放大到**整个进程里所有用同一字符串的地方**，容易造成毫不相干的代码互相阻塞。也别用 `synchronized(Integer.valueOf(1))`——IntegerCache 会返回同一个对象，同样问题。*老老实实 `private final Object lock = new Object();`*

追问 synchronized 修饰 static 方法的锁范围有多大？

整个 `Class` 对象。`Class` 对象在一个 `ClassLoader` 里只有一份，所以**该类的所有实例都共享同一把静态锁**。假如 `Demo` 类有 1000 个实例，任一线程正在跑某个实例的 synchronized static 方法，其他 999 个实例上的任何 synchronized static 方法都会被阻塞。而实例方法的锁只作用于「同一个对象」，粒度小得多。

## 面试场景 2：synchronized 底层是怎么实现的？（★核心）

🎤 面试官

synchronized 的底层实现原理你了解吗？字节码层面和 JVM 层面分别是什么？

🧑‍💻 你

分两层看：

**字节码层面**——

- 同步**代码块**：编译成 `monitorenter` 和 `monitorexit` 两条指令。`monitorenter` 出现一次，`monitorexit` 会出现*两次*——一次是正常出口，一次挂在异常表里保证抛异常时也能释放锁。

- 同步**方法**：不生成 monitor 指令，而是在方法的访问标志上加一个 `ACC_SYNCHRONIZED` flag。JVM 遇到带这个 flag 的方法，进入前隐式 monitorenter、退出前隐式 monitorexit。

**JVM 层面**——两种指令最终都是操作 **Monitor**（HotSpot 里叫 `ObjectMonitor`，C++ 实现的一个对象），关键字段：

```
ObjectMonitor {
_owner    = null   // 持有锁的线程指针
_count    = 0      // 重入次数（同一线程再进入就 ++）
_recursions = 0    // 递归深度（同 count）
_EntryList        // 阻塞等待获取锁的线程队列
_WaitSet          // 调用了 wait() 挂起的线程队列
_cxq              // ContentionQueue，新进来的竞争者先入这里
}
```

- 线程执行 monitorenter：尝试把 `_owner` 设为自己。成功则 `_count = 1`；如果 `_owner` 已经是自己，`_count++`（重入）；否则进入 `_EntryList` 阻塞。

- 线程执行 monitorexit：`_count--`，减到 0 才真正释放锁，唤醒 `_EntryList` 里的线程竞争。

- `Object.wait()`：把当前线程从 `_owner` 移到 `_WaitSet`，释放锁。`notify()`：从 `_WaitSet` 挑一个搬回 `_EntryList`。

追问 为什么 `monitorexit` 会出现两次？

为了**异常安全**。编译器给同步代码块生成一张异常表：*正常路径*一次 `monitorexit`；如果代码块里抛异常，异常处理器会兜底走*第二次* `monitorexit`，然后 `athrow` 把异常继续往上抛。这保证「无论正常返回还是异常退出，锁一定释放」。同步方法用 `ACC_SYNCHRONIZED` 标志，异常释放是 JVM 内部保证的，字节码里看不见。

追问 Monitor 到底是什么？和 Java 对象是什么关系？

Monitor 是「监视器」这个并发原语的具体实现。在 HotSpot 里叫 `ObjectMonitor`，是一个纯 C++ 对象（不是 Java 对象）。每个 Java 对象都*潜在地*关联一个 Monitor——但不是一开始就分配，而是**升级到重量级锁时按需创建**，通过对象头 Mark Word 里的指针指向它。所以「每个对象都能当锁」这句话，本质上是「每个对象都能按需绑定一个 Monitor」。

## 面试场景 3：对象头 Mark Word 里都放了什么？（★核心）

🎤 面试官

你知道 Java 对象头吗？Mark Word 里都存了什么？

🧑‍💻 你

HotSpot 里，一个普通 Java 对象由三部分构成：**对象头（Header）+ 实例数据（Instance Data）+ 对齐填充（Padding）**。对象头又分两块：

- **Mark Word**：64 位系统上占 8 字节，存 hashCode、GC 分代年龄、锁状态标志、指针等运行时数据。*字段布局随锁状态动态变化*。

- **Klass Pointer**：指向该对象类型元数据（`InstanceKlass`）。开启指针压缩后 4 字节，否则 8 字节。

**Mark Word 在 64 位 HotSpot 上的布局**（最后 2 位是锁标志位 `lock`，再前一位是偏向标志 `biased_lock`）：

```
|-------------------------------------------------------|--------------------|
|                  Mark Word (64 bits)                  |       状态         |
|-------------------------------------------------------|--------------------|
| unused:25 | hashCode:31 | unused:1 | age:4 | 0 |  01  |  无锁              |
|-------------------------------------------------------|--------------------|
| threadId:54 | epoch:2   | unused:1 | age:4 | 1 |  01  |  偏向锁            |
|-------------------------------------------------------|--------------------|
| ptr_to_lock_record:62                        |  00   |  轻量级锁          |
|-------------------------------------------------------|--------------------|
| ptr_to_heavyweight_monitor:62                |  10   |  重量级锁          |
|-------------------------------------------------------|--------------------|
| (empty):62                                   |  11   |  GC 标记           |
|-------------------------------------------------------|--------------------|
```

关键观察：

- 无锁状态下的 **identityHashCode** 一旦被计算并写入 Mark Word，该对象就*不能再进入偏向锁*（因为偏向锁位置要放 threadId，会覆盖 hashCode）。

- 轻量级和重量级都是把 Mark Word 整体替换成一个*指针*——原来的 hashCode/age 临时挪到别的地方保存（Lock Record 或 Monitor 内部）。

追问 为什么调用了 `hashCode()` 之后就没法进入偏向锁了？

因为偏向锁的 Mark Word 布局把 threadId 放在 hashCode 原来的位置——两者是**互斥的**。Java 规范承诺 `hashCode()` 结果在对象生命周期内不变（未重写时用 identityHashCode），如果一个对象已经算过 hashCode 并写进 Mark Word，再进入偏向锁就得覆盖它，违反规范。所以 HotSpot 的策略是：*一旦对象曾经算过 identityHashCode，就直接跳过偏向锁，可能进入轻量级或重量级*。

## 面试场景 4：锁升级四阶段（★必背核心）

🎤 面试官

JDK 6 之后 synchronized 的锁升级过程你能完整讲一遍吗？

🧑‍💻 你

JDK 6 之前 synchronized 直接用重量级锁（走 OS Mutex，性能差）。JDK 6 引入「锁升级」——按竞争程度从轻到重逐级切换：

```
┌─── 无锁 (001) ───┐
│  Mark Word:      │  刚 new 出来的对象，没被任何线程加锁
│  hashCode + age  │
└──────┬───────────┘
│  一个线程首次 synchronized(obj)
▼
┌─── 偏向锁 (101) ─┐  JDK 15+ 默认关闭
│  Mark Word:      │  「反正只有一个线程用，别浪费 CAS」
│  threadId + age  │  下次同一线程再进入，只需比对 threadId
└──────┬───────────┘
│  第二个线程也来 synchronized
▼
┌─ 轻量级锁 (00) ──┐
│  Mark Word:      │  多线程但没同时争
│  ptr → Lock Rec  │  每个线程栈帧里放 Lock Record，用 CAS 抢
└──────┬───────────┘  CAS 抢失败 → 自旋若干次
│
│  自旋失败 / 竞争激烈
▼
┌─ 重量级锁 (10) ──┐
│  Mark Word:      │  真正的 ObjectMonitor
│  ptr → Monitor   │  抢不到就 park() 阻塞挂起（走 OS mutex）
└──────────────────┘
```

**阶段一 · 偏向锁（Biased Lock）**：假设「大多数情况一个锁只会被同一个线程反复获取」。首次进入时用 CAS 把 threadId 写进 Mark Word；*之后同一线程再进入，只需检查 Mark Word 里的 threadId 是自己就直接放行*，连 CAS 都省了。撤销偏向锁的代价很大——必须等 **全局安全点（safe point）**暂停所有线程，检查偏向线程是否还活着，再决定升级或恢复无锁。

**阶段二 · 轻量级锁（Lightweight Lock）**：一旦有第二个线程来抢，偏向锁升级为轻量级锁。JVM 在*抢锁线程的栈帧*里开辟一块叫 **Lock Record**（也叫 Displaced Mark Word）的空间，把对象的原 Mark Word 复制进去；然后用 **CAS** 把对象的 Mark Word 替换成「指向该 Lock Record 的指针 + 00 标志」。抢到就进入临界区；抢不到就**自旋**——不阻塞线程，一直循环 CAS 尝试。自旋适合*临界区极短*的场景，能省下 park/unpark 的上下文切换开销。

**阶段三 · 重量级锁（Heavyweight Lock）**：自旋到一定次数还没抢到，说明竞争激烈——升级为重量级锁。这时会创建一个真正的 `ObjectMonitor`，Mark Word 换成指向 Monitor 的指针 + 10。抢不到的线程调 `park()` 挂起（对应 OS mutex/futex），等释放时被 `unpark()` 唤醒。这时才真正涉及*用户态到内核态切换*——成本最高，但公平且不浪费 CPU。

**核心规则：锁只能升不能降。**

追问 为什么锁只能升级不能降级？

本质是**历史决策 + 实现复杂度**。降级要在运行时判断「竞争是不是真的消失了」，还要保证降级瞬间没有别的线程正在抢——需要暂停所有线程走安全点，成本高。而现代应用普遍是「一旦升到重量级，说明真的有并发」，降回去意义不大。JVM 在*特定 GC 阶段*会做一些降级（比如把 monitor deflate 掉），但对用户完全透明，不算通用能力。

追问 自旋锁的自旋次数怎么定的？

JDK 6 之前是固定次数（默认 10 次），可用 `-XX:PreBlockSpin` 调。JDK 6 之后引入 **自适应自旋**：如果这把锁上一次自旋*抢到了*，JVM 就允许它这次自旋更久；如果上次自旋*抢失败*，下次可能直接跳过自旋去阻塞。这样避免了「每次都白转 CPU」和「短临界区被过早挂起」两个极端。

## 面试场景 5：偏向锁为什么在 JDK 15+ 被弃用？

🎤 面试官

听说 JDK 15 之后偏向锁默认关闭了，为什么？

🧑‍💻 你

对，JEP 374（Disable and Deprecate Biased Locking）在 JDK 15 里默认禁用偏向锁，JDK 18 之后连启用参数 `-XX:+UseBiasedLocking` 都被标记 obsolete。原因：

1. **收益越来越小**——偏向锁的假设是「大多数锁只被单线程使用」。这假设在早期 JDK 5/6 时代成立（很多老代码用 `HashTable`、`Vector` 这些同步集合但实际只有一个线程用）。现代应用普遍多线程，而且大家都改用 `ConcurrentHashMap`、`CopyOnWriteArrayList`、`Atomic*`，偏向锁能优化到的场景越来越少。

2. **撤销成本很高**——一旦第二个线程来抢，撤销偏向锁要等全局安全点、暂停所有线程、扫描栈遍历*所有* Lock Record，非常昂贵。多线程越普遍，撤销就越频繁，反而**拖慢整体**。

3. **维护成本高**——偏向锁的代码在 HotSpot 里高度侵入锁子系统，和后续要引入的新特性（如 Loom 虚拟线程、新一代 GC）冲突多，重构负担重。

结论：偏向锁是特定时代的优化，「优化的净收益」变负后被移除是很正常的事。

## 面试场景 6：synchronized vs ReentrantLock 完整对比（★经典）

🎤 面试官

synchronized 和 ReentrantLock 有什么区别？怎么选？

维度synchronizedReentrantLock

实现层次JVM 关键字（字节码 + Monitor）Java API（`java.util.concurrent.locks`，基于 AQS）
加锁 / 释放自动进入、自动释放（含异常）手动 `lock()` / `unlock()`，必须放 `finally`
可重入✓（同线程 count++）✓（AQS 内部计数）
可中断✗ 一旦开始等锁就等到死✓ `lockInterruptibly()` 响应 `interrupt()`
超时获取✗✓ `tryLock(long, TimeUnit)`
公平性只支持非公平构造器传 `true` 变公平锁，默认非公平
Condition 数量1 个隐式（`wait`/`notify`）N 个显式 `newCondition()`，可分组唤醒
能否读取锁状态✗✓ `isHeldByCurrentThread()`、`getHoldCount()`、`getQueueLength()`
性能JDK 6+ 后经过大量优化，多数场景相当高竞争 + 需要高级特性时更灵活
易用性简单、少 bug、异常自动释放灵活，但忘记 `unlock` 就死锁

🧑‍💻 你的选型口诀

**能用 synchronized 就用 synchronized**——简单、异常安全、JIT 优化成熟。只有当你需要「超时」「可中断」「公平锁」「多条件变量」中的*任意一项*时，才切换到 `ReentrantLock`。

追问 JDK 6 之后 synchronized 性能能追上 ReentrantLock，具体做了哪些优化？

五大优化：**① 偏向锁**（单线程零 CAS）；**② 轻量级锁 + CAS**（无阻塞抢锁）；**③ 自适应自旋**（根据历史动态调整自旋次数）；**④ 锁消除**（逃逸分析消除无竞争的锁）；**⑤ 锁粗化**（合并相邻锁）。JDK 6 以前 synchronized 直接走重量级 monitor，慢 ReentrantLock 一个数量级；JDK 6 后差距基本抹平，简单场景 synchronized 甚至更快（少一层 AQS 抽象）。

## 面试场景 7：synchronized 是可重入的吗？

🧑‍💻 你

是的。同一线程再次进入已持有的锁不会阻塞——Monitor 里的 `_count`（重入计数）加 1，退出时减 1，减到 0 才真正释放。`ReentrantLock` 同理（AQS 的 state 字段做计数）。

```
public class ReentrantDemo {
public synchronized void outer() {
System.out.println("outer, count=1");
inner();  // 同一线程再次抢同一把锁，直接放行，count=2
}
public synchronized void inner() {
System.out.println("inner, count=2");
}
}
```

如果 synchronized *不*可重入，`outer()` 里调 `inner()` 就会自己把自己锁死——典型的**自锁死锁**。所以「可重入」是所有实用锁的基本要求。

追问 父类的 synchronized 方法，子类重写并调 `super`，会重入吗？

会。锁的粒度是*对象*不是*方法*——只要 `this` 是同一个对象，无论从子类进还是父类进，都能重入。同理，一个线程先调 `synchronized void a()`，在临界区里再调另一个 `synchronized void b()`，也能重入（因为锁的都是 `this`）。

## 面试场景 8：synchronized 会死锁吗？怎么避免？

🧑‍💻 你

会。经典死锁四条件：**互斥、持有并等待、不可剥夺、循环等待**。synchronized 天然满足前三条——只要你写出循环等待就能死锁。

```
Object a = new Object();
Object b = new Object();

// 线程 1
synchronized (a) {
Thread.sleep(100);
synchronized (b) { }  // 卡在这里等 b
}

// 线程 2
synchronized (b) {
Thread.sleep(100);
synchronized (a) { }  // 卡在这里等 a  → 死锁
}
```

**避免手段**：

1. **固定加锁顺序**：所有代码路径按同一个全局顺序获取锁（比如按对象 `System.identityHashCode` 排序）。破坏「循环等待」。

2. **带超时的 tryLock**：改用 `ReentrantLock.tryLock(timeout)`，抢不到就放弃并回滚。破坏「不可剥夺」。

3. **减少嵌套锁**：能一把锁解决就别用两把。

4. **用 jstack 定位**：线上死锁 `jstack <pid>` 会直接打出 *Found one Java-level deadlock*，报出哪些线程持有 / 等待哪些 monitor。

追问 jstack 是怎么检测出 Java 层死锁的？

JVM 维护每把锁的持有者线程和每个线程正在等待的锁。`jstack` 触发时会构造一张「线程—锁」的**等待图**，做环检测——如果发现环，就报死锁并把环上所有线程的栈都打出来。*但它只能检测到 synchronized 和 `java.util.concurrent.locks.Lock`*；如果你用 `CountDownLatch`、`Semaphore` 或者数据库锁形成的死锁，jstack 看不出来。

## 面试场景 9：锁消除 & 锁粗化（JIT 优化）

🧑‍💻 你

两项 JIT 编译时优化，都发生在 C2 编译阶段：

**锁消除（Lock Elimination）**：JIT 通过*逃逸分析*确定某个锁对象不可能被其他线程访问，直接把 `monitorenter`/`monitorexit` 抹掉。经典例子：

```
public String concat(String s1, String s2) {
StringBuffer sb = new StringBuffer();  // 只在方法内使用，未逃逸
sb.append(s1);   // StringBuffer.append 是 synchronized 方法
sb.append(s2);   // 但由于 sb 不逃逸，JIT 消除这些锁
return sb.toString();
}
```

**锁粗化（Lock Coarsening）**：连续对*同一把锁*的 lock/unlock，JIT 会合并成一次大范围加锁，避免反复进出临界区。

```
// 源码：3 次 lock/unlock
for (int i = 0; i < 100; i++) {
synchronized (lock) {  // 每次循环都进出
counter++;
}
}

// JIT 粗化后：1 次 lock/unlock
synchronized (lock) {
for (int i = 0; i < 100; i++) {
counter++;
}
}
```

粗化在**循环体内**特别有用，能显著减少 monitor 操作次数。

## 面试场景 10：公平锁 vs 非公平锁

🧑‍💻 你

**非公平锁**：允许「插队」——新来的线程 tryAcquire 时不看队列，直接和刚释放锁瞬间被唤醒的老线程抢一次。`synchronized` 就是非公平的；`ReentrantLock` 默认也是非公平（`new ReentrantLock()`）。

**公平锁**：严格按 FIFO 顺序——新线程 tryAcquire 前先看队列，队里有人排队就*直接进队末尾*，不插队。`new ReentrantLock(true)` 打开公平模式。

维度非公平锁公平锁

吞吐量高（减少上下文切换）低（每次都要唤醒队首）
饥饿风险存在（某线程可能永远抢不到）无
响应时间抖动大小
默认选择synchronized、ReentrantLock 默认需显式开启

非公平之所以是默认，是因为*大多数场景下吞吐 > 公平*——插队能省一次线程唤醒。除非业务确实容忍不了饥饿（比如实时系统），否则用默认。

追问 synchronized 保证的三大内存语义是什么？

都保证：**① 原子性**——同一时刻只有一个线程能进入临界区，临界区内的复合操作对外部原子。**② 可见性**——JMM 规定 `monitorexit` 时把本地内存的写*刷回主内存*，`monitorenter` 时把主内存的读*重新加载*，等价于 volatile 的 happens-before。**③ 有序性**——虽然临界区*内部*指令仍可重排，但临界区作为一个整体不会被 JVM/CPU 重排到临界区外，等于建立了「以锁为边界」的 happens-before 关系。

## 💻 代码验证

### 验证 1：`javap -v` 看 monitorenter / monitorexit / ACC_SYNCHRONIZED

```
// SyncDemo.java
public class SyncDemo {
private final Object lock = new Object();

public void block() {
synchronized (lock) {
System.out.println("hi");
}
}

public synchronized void method() {
System.out.println("hi");
}
}
```

```
$ javac SyncDemo.java
$ javap -v -p SyncDemo

// ---- block() 部分 ----
public void block();
flags: (0x0001) ACC_PUBLIC
Code:
0: aload_0
1: getfield      #7    // Field lock
4: dup
5: astore_1
6: monitorenter        // ← 进入
...
15: monitorexit         // ← 正常出口
16: goto          24
19: astore_2
20: aload_1
21: monitorexit         // ← 异常出口
22: aload_2
23: athrow
Exception table:            // ← 兜底异常表
from    to  target type
6    16    19   any

// ---- method() 部分 ----
public synchronized void method();
flags: (0x0021) ACC_PUBLIC, ACC_SYNCHRONIZED   // ← flag 上标记
Code:
0: getstatic     #13   // System.out
3: ldc           #19   // "hi"
5: invokevirtual #21   // println
8: return
// 注意：没有 monitorenter/monitorexit！
```

### 验证 2：可重入 —— 同一线程重复进入同一把锁

```
public class ReentrantDemo {
public static synchronized void outer() {
System.out.println("outer, thread=" + Thread.currentThread().getName());
inner();
}
public static synchronized void inner() {
System.out.println("inner, thread=" + Thread.currentThread().getName());
}
public static void main(String[] args) {
outer();  // 正常打印两行，不会死锁
}
}
```

### 验证 3：手写一个死锁，用 jstack 观测

```
public class DeadlockDemo {
static final Object A = new Object();
static final Object B = new Object();

public static void main(String[] args) throws Exception {
new Thread(() -> {
synchronized (A) {
sleep(100);
synchronized (B) { System.out.println("t1 got B"); }
}
}, "t1").start();

new Thread(() -> {
synchronized (B) {
sleep(100);
synchronized (A) { System.out.println("t2 got A"); }
}
}, "t2").start();

// 跑起来后另开终端: jps 找到 pid，然后 jstack <pid>
// 输出末尾会看到：Found one Java-level deadlock
}
static void sleep(long ms) {
try { Thread.sleep(ms); } catch (InterruptedException e) { }
}
}
```

### 验证 4：ReentrantLock 演示 synchronized 做不到的三件事

```
import java.util.concurrent.locks.*;
import java.util.concurrent.TimeUnit;

public class ReentrantLockPower {
private final ReentrantLock lock = new ReentrantLock(true);  // 公平锁
private final Condition notFull  = lock.newCondition();      // 多 Condition
private final Condition notEmpty = lock.newCondition();

// ① 可中断
public void interruptible() throws InterruptedException {
lock.lockInterruptibly();       // 等锁时能被 interrupt() 打断
try { /* ... */ }
finally { lock.unlock(); }
}

// ② 带超时的 tryLock
public boolean withTimeout() throws InterruptedException {
if (!lock.tryLock(500, TimeUnit.MILLISECONDS)) {
return false;               // 抢不到就放弃
}
try { return true; }
finally { lock.unlock(); }
}

// ③ 多个 Condition，选择性唤醒
public void producer() throws InterruptedException {
lock.lock();
try {
while (full()) notFull.await();
put();
notEmpty.signal();          // 只唤醒消费者，不打扰其他生产者
} finally { lock.unlock(); }
}

private boolean full()  { return false; }
private void    put()   { }
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `synchronized` 修饰实例方法、静态方法、代码块，分别锁什么？三者能同时被不同线程进入吗？</summary>

实例方法锁 `this`；静态方法锁 `Class` 对象；代码块锁指定对象。**能**——静态和实例方法用的是不同的锁（`Class` vs `this`），线程 A 跑 static 方法的同时，线程 B 可以跑同一对象的 synchronized 实例方法。

</details>

<details>

<summary>Q2 同步代码块和同步方法在字节码层面有什么区别？</summary>

代码块用 `monitorenter`/`monitorexit` 两条指令（`monitorexit` 出现两次以保证异常安全）。方法不用 monitor 指令，改在方法访问标志上加 `ACC_SYNCHRONIZED` flag，JVM 隐式加锁解锁。

</details>

<details>

<summary>Q3 完整讲一遍锁升级的四个阶段，每阶段 Mark Word 存什么。</summary>

**无锁 (001)**: hashCode + age；**偏向锁 (101)**: threadId + epoch + age；**轻量级锁 (00)**: 指向栈帧 Lock Record 的指针；**重量级锁 (10)**: 指向 ObjectMonitor 的指针。只能单向升级不能降级。JDK 15+ 偏向锁默认关闭。

</details>

<details>

<summary>Q4 synchronized vs ReentrantLock，选型的核心决策点是什么？</summary>

默认用 synchronized（简单、异常安全、JIT 优化好）。*只有当你需要以下之一时*才切 ReentrantLock：① 可中断等锁（`lockInterruptibly`）；② 超时等锁（`tryLock(t)`）；③ 公平锁；④ 多个 Condition 分组唤醒；⑤ 需要读取锁状态。

</details>

<details>

<summary>Q5 锁消除和锁粗化是什么？举个例子。</summary>

都是 JIT 优化。**锁消除**：逃逸分析发现锁对象不逃出方法，直接去掉 monitor 指令（例：方法内 `new StringBuffer()` 的 `append` 调用）。**锁粗化**：合并相邻的 `lock/unlock`（例：循环体里每次迭代都 synchronized 同一对象，粗化成一次 lock 覆盖整个循环）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

- JEP 374 · Disable and Deprecate Biased Locking —— 偏向锁弃用官方 JEP

- JVMS §6.5 · `monitorenter` / `monitorexit` —— 字节码指令官方规范

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0020：**volatile & JMM 内存模型** —— synchronized 的近亲，只保证可见性和有序性，不保证原子性。面试频次同样极高。

💬 有任何疑问 —— 「Lock Record 里到底存什么？」「偏向锁撤销的具体流程？」「重量级锁的 park/unpark 是怎么实现的？」—— 直接问我。我是你的老师，也是你的追问陪练。


