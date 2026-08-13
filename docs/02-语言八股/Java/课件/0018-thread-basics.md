> Lesson 0018 · 阶段三 · 并发编程 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0018 · 线程基础 & 生命周期 & Thread vs Runnable & 常用方法陷阱

欢迎进入 **阶段三 · 并发编程**。前两个阶段我们攻下了 Java 基础和集合，这里开始正式面对面试官眼里的"分水岭"—— *并发能力直接决定薪资等级*。而并发的一切故事，都要从最原始的一个词说起：**线程（Thread）**。

这一课覆盖 的开头核心章节。开场三连击几乎是雷打不动的：**「进程和线程什么区别？」「线程有哪几种状态？」「start() 和 run() 有什么区别？」**—— 答不上来这三个问题，后面 synchronized / volatile / AQS / 线程池 全部白搭。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Java 中一个 `Thread` 对象一共有几种状态？分别是什么？</summary>

6 种：`NEW` / `RUNNABLE` / `BLOCKED` / `WAITING` / `TIMED_WAITING` / `TERMINATED`。注意 Java 的 `RUNNABLE` 把 OS 层面的 READY 和 RUNNING 合并了。第 6 题细讲。

</details>

<details>

<summary>Q0.2 `new Thread(r).start()` 和 `new Thread(r).run()` 区别是什么？</summary>

前者是 JVM 帮你开一个新线程，异步跑 `r.run()`；后者只是在当前线程直接调用了一个普通方法，压根没开新线程。第 7 题是经典陷阱题。

</details>

## 面试场景 1：进程 vs 线程 vs 协程

🎤 面试官

先来个开胃菜：进程、线程、协程三者有什么区别？

🧑‍💻 你

三个概念是从粗到细的执行单位：

- **进程 (Process)**：操作系统资源分配的基本单位。每个进程*独立地址空间*、独立文件描述符表、独立信号处理表。进程之间要通信必须走 IPC（管道、共享内存、Socket）。

- **线程 (Thread)**：CPU 调度的基本单位。同一进程内的多个线程*共享堆和方法区*，但每个线程有自己的*程序计数器、虚拟机栈、本地方法栈*。所以线程间通信直接读写共享变量就行，但也因此才需要 `synchronized`、`volatile` 这些同步机制。

- **协程 (Coroutine)**：*用户态*的轻量执行流，由应用层（不是内核）调度。切换不用陷入内核，几十 ns 就搞定，一个线程能跑几万个协程。Go 的 goroutine、Kotlin 的 coroutine 都是这一类。Java 21 正式推出的 **虚拟线程 (Virtual Thread)** 本质是 JVM 调度的协程，用少量平台线程复用海量虚拟线程。

追问 为什么说线程比进程"轻量"？切换开销具体差在哪？

进程切换要换整套**页表 (page table)**、刷 **TLB (Translation Lookaside Buffer)**、换文件描述符表、换信号处理表；线程切换*只换寄存器和内核栈*（页表都不用动，因为共享地址空间）。前者微秒级，后者纳秒级。协程更狠，连内核态都不进，纯用户态跳转，只切几个寄存器。所以「万级并发用线程池，百万并发上虚拟线程」是主流选择。

## 面试场景 2：并发 vs 并行 vs 串行 vs 异步

🎤 面试官

并发和并行是同一个东西吗？异步又是什么？

🧑‍💻 你

- **串行 (Serial)**：任务一个接一个执行。做完 A 才能做 B。

- **并发 (Concurrency)**：*宏观上*多个任务在同一时间段内推进，*微观上*可能是交替执行。单核 CPU 靠时间片轮转也能"并发"跑多个线程。

- **并行 (Parallelism)**：*物理上*同一时刻多个任务在多个 CPU 核心上真正同时执行。必须多核才可能有并行。

- **异步 (Asynchronous)**：一种*调用模式*—— 发起调用后立刻返回，不阻塞等待结果，等结果就绪再回调 / poll。对立面是**同步 (Synchronous)**。异步不一定并发，但常常和并发配合。

一句话记住：**并发是"看起来同时"，并行是"真的同时"，异步是"我不等你"**。

追问 单核 CPU 能"并行"吗？

**不能**。单核在任意时刻只有一个执行流，最多做到"并发"—— 通过 OS 的时间片轮转让人*感觉*多任务同时跑。要真正并行必须多核 / 多 CPU。所以以前教科书讲的"多线程一定更快"是个错误暗示，见下一题。

## 面试场景 3：为什么要用多线程？多线程一定更快吗？

🎤 面试官

既然多线程这么复杂，为什么还非要用它？多线程一定比单线程快吗？

🧑‍💻 你

用多线程的三个理由：

1. **压榨多核 CPU**：现代服务器动辄几十核，单线程只用一个核就是极大浪费。

2. **提升 I/O 密集型吞吐**：一个线程发起 I/O 时会阻塞挂起，其它线程可以趁机干活。数据库查询、RPC 调用、文件读写都是典型场景。

3. **响应性**：GUI / 服务端把耗时操作丢到后台线程，主线程持续响应用户 / 请求。

但**多线程不一定快**，有 3 个坑：

- **上下文切换开销**：线程数 >> 核数时，切换本身就吃 CPU（几微秒 / 次）；切换过程还会导致 **CPU 缓存 (L1/L2) 失效**，下次运行要重新加载。

- **锁竞争**：多线程访问共享资源要加锁，抢不到锁的线程会 `BLOCKED`，等价于串行；重竞争场景下还有大量线程唤醒 / 挂起系统调用。

- **纯 CPU 密集型任务**：比如死循环计算 π，开的线程数超过核数只会拖慢速度，不如直接单线程跑满一个核。

陷阱 面试官爱问：「一个 4 核 CPU，处理纯 CPU 密集型任务，开多少线程最合适？」标准答案是**核数 或 核数 + 1**（后者是留一个作缓冲，防某个线程偶尔 I/O 或缺页）。开更多线程只会因上下文切换降速。I/O 密集型才是「核数 × (1 + 等待时间 / 计算时间)」这个大家伙。

## 面试场景 4：Java 中创建线程的几种方式

🎤 面试官

Java 里创建一个线程，你能列几种方式？

🧑‍💻 你

常见 6 种，按历史顺序：

1. **继承 `Thread`**：`class MyThread extends Thread { public void run() {...} }`。简单但吃掉唯一的继承名额。

2. **实现 `Runnable`**：`new Thread(() -> {...}).start()`。工程上最推荐，因为 `Runnable` 只是"一段任务"，可以被复用、被线程池调度。

3. **实现 `Callable` + `FutureTask`**：和 `Runnable` 类似，但 `call()` 有返回值、可以抛受检异常。用 `FutureTask` 包装后交给 `Thread` 或线程池。

4. **线程池 `ExecutorService`**：`Executors.newFixedThreadPool(n).submit(task)`。*生产环境标准做法*—— 复用线程、控制并发数、统一异常处理。

5. **CompletableFuture (JDK 8+)**：`CompletableFuture.supplyAsync(() -> ...)`。适合*异步编排*—— 链式 `thenApply` / `thenCombine`，无锁 pipeline。

6. **虚拟线程 (JDK 21+)**：`Thread.ofVirtual().start(task)` 或 `Executors.newVirtualThreadPerTaskExecutor()`。轻量到可以"每请求一线程"，一台机器起百万个都不成问题。

严格说 JVM 层只有一种方式—— `new Thread().start()`，其它写法本质上都会最终走到它（或 `Thread.startVirtualThread`）。区分它们主要是*API 抽象层次*不同。

追问 `Runnable` 和 `Callable` 有什么区别？

三点区别：**(1)** `Runnable.run()` 无返回值，`Callable.call()` 返回泛型 `V`；**(2)** `run()` 不能抛受检异常，`call()` 可以 `throws Exception`；**(3)** `Runnable` 可以直接给 `new Thread()`，`Callable` 得包装成 `FutureTask` 或交给 `ExecutorService.submit()` 才能跑。要返回结果或要抛异常，选 `Callable`；否则默认 `Runnable`。

## 面试场景 5：Thread vs Runnable —— 到底该继承还是实现？★经典

🎤 面试官

都能创建线程，为什么工程里几乎见不到 `extends Thread`？

🧑‍💻 你

维度继承 Thread实现 Runnable

关系是-a Thread（is-a）有-a 任务（has-a）
继承限制吃掉唯一的单继承名额不影响继承其它类
任务复用任务和线程强绑定，一个任务只能跑一次同一个 `Runnable` 可以交给多个线程 / 线程池反复执行
与线程池配合不友好（线程池要管理自己的线程实例）天然契合（`execute(Runnable)`）
面向对象混淆"任务"和"载体"关注点分离更符合 SRP

所以工程规范是**「面向任务编程」**—— 写 `Runnable` / `Callable`，扔给 `ExecutorService` 或 `CompletableFuture`，别自己 `new Thread`，更别 `extends Thread`。阿里巴巴《Java 开发手册》明确禁止"手动 `new Thread`"。

追问 为什么阿里手册禁止手动 `new Thread`？

三个原因：**(1) 缺乏资源管控**—— 手动 new 出来的线程没有上限，高并发下能把 OOM 打出来；**(2) 缺乏统一命名**—— 出问题时 `jstack` 看到一堆 `Thread-0/1/2`，根本定位不到业务；**(3) 生命周期无管理**—— 线程结束后不能复用，创建 / 销毁开销大。解决方案：统一用 `ThreadPoolExecutor`，通过 `ThreadFactory` 起有意义的名字。

## 面试场景 6：Java 线程的 6 种状态 ★核心

🎤 面试官

画一下 Java 线程的状态转换图。

🧑‍💻 你

Java 的 `Thread.State` 枚举一共 6 种，画成状态机是这样：

```
new Thread(r)
│
▼
┌─────┐
│ NEW │
└─────┘
│  start()
▼
┌─────────────────┐     synchronized 抢锁失败
│    RUNNABLE     │ ──────────────────────────► ┌─────────┐
│  (ready+running)│                              │ BLOCKED │
└─────────────────┘ ◄────────────────────────── └─────────┘
│  │  │             拿到锁
│  │  │
│  │  └── wait() / join() / LockSupport.park()
│  │                                       ┌─────────┐
│  │       ─────────────────────────────►  │ WAITING │
│  │           notify/notifyAll/unpark    └─────────┘
│  │       ◄─────────────────────────────
│  │
│  └───  sleep(t) / wait(t) / join(t) / parkNanos
│                                     ┌───────────────┐
│        ─────────────────────────►   │ TIMED_WAITING │
│             时间到 或 被唤醒         └───────────────┘
│        ◄─────────────────────────
│
│ run() 正常结束 / 抛异常
▼
┌────────────┐
│ TERMINATED │
└────────────┘
```

每个状态的定义：

- **NEW**：线程对象已创建但还没 `start()`。

- **RUNNABLE**：调用 `start()` 后的状态。*注意：Java 把 OS 的「就绪 Ready」和「运行 Running」合并成一个状态*—— 只要没被阻塞就是 RUNNABLE，具体是等 CPU 还是正在跑 CPU 不区分。

- **BLOCKED**：等待进入 `synchronized` 同步块 / 方法所需的*监视器锁 (monitor lock)*。只有 `synchronized` 抢锁失败会进 BLOCKED，`ReentrantLock.lock()` 抢不到锁进的是 WAITING（因为底层是 LockSupport.park）。

- **WAITING**：无限期等待，需要被别的线程*显式唤醒*。触发方式：`Object.wait()`（无参）、`Thread.join()`（无参）、`LockSupport.park()`。

- **TIMED_WAITING**：带超时的等待，时间到会自动醒。触发方式：`Thread.sleep(t)`、`Object.wait(t)`、`Thread.join(t)`、`LockSupport.parkNanos`、`LockSupport.parkUntil`。

- **TERMINATED**：`run()` 执行完毕（正常返回 / 抛出未捕获异常）。一个线程一旦进入 TERMINATED 就再也回不去了，`start()` 只能调一次。

追问 BLOCKED 和 WAITING 到底有什么区别？

关键在**唤醒机制**：

- **BLOCKED** 是*被动等待锁*—— 别的线程释放 `synchronized` 锁的瞬间，JVM 从等锁队列里挑一个 BLOCKED 线程直接变 RUNNABLE。不需要谁"主动通知"，锁一放就自动 candidate。

- **WAITING** 是*主动进入等待*—— 必须由持有 monitor 的其它线程调 `notify()` / `notifyAll()` 或 `LockSupport.unpark(t)` 才能被唤醒，等不到就一直等。

所以 BLOCKED 排队等门开，WAITING 是主动睡等叫醒服务。

追问 用 `ReentrantLock.lock()` 抢不到锁，线程是什么状态？

是 **WAITING**，不是 BLOCKED。因为 `ReentrantLock` 底层是 `AbstractQueuedSynchronizer`，抢不到就走 `LockSupport.park()`，而 `park()` 对应 WAITING 状态。这也解释了为什么 `jstack` 打印线程栈时，等 `synchronized` 和等 `ReentrantLock` 长相不一样。

## 面试场景 7：start() vs run() ★经典陷阱

🎤 面试官

看这段代码，打印什么？

```
Thread t = new Thread(() -> {
System.out.println("running in: " + Thread.currentThread().getName());
});
t.run();
t.start();
```

🧑‍💻 你

会打印：

```
running in: main         ← t.run() 只是在 main 线程里同步执行了普通方法
running in: Thread-0     ← t.start() 才是真正让 JVM 起了新线程
```

区别：

- `start()` 是 `Thread` 类的方法，内部通过 *native 方法 `start0()`* 调用 OS 的 `pthread_create` / `CreateThread`，创建新的内核线程；新线程被调度到时会自动执行 `run()`。**一个 Thread 对象的 `start()` 只能被调用一次**，第二次会抛 `IllegalThreadStateException`。

- `run()` 就是个普通实例方法，你直接调它跟调 `t.toString()` 没本质区别—— 在*当前线程*同步执行完再返回，压根没起新线程。

陷阱 面试官如果追问「`start()` 里到底做了什么？」答案是：**(1)** 校验线程状态必须是 NEW，否则抛 `IllegalThreadStateException`；**(2)** 把线程加进 `ThreadGroup`；**(3)** 调用 `native start0()`，让 OS 创建内核线程并把该线程注册到 JVM；**(4)** 新线程被调度到时执行 `Thread.run()`—— 而 `Thread.run()` 的默认实现是「如果构造时传了 `Runnable target`，就调 `target.run()`」。

## 面试场景 8：sleep() vs wait() ★经典

🎤 面试官

`Thread.sleep()` 和 `Object.wait()` 有什么区别？

🧑‍💻 你

维度`Thread.sleep(t)``Object.wait() / wait(t)`

定义位置`Thread` 类的*静态方法*`Object` 类的*实例方法*
是否释放锁**不释放**—— 抱着锁睡**释放**—— 释放当前对象的 monitor 锁
调用位置任何地方都能调必须在 `synchronized(obj)` 块 / 该对象的同步方法内，否则抛 `IllegalMonitorStateException`
唤醒方式时间到 或 被 `interrupt()`（会抛 `InterruptedException`）被 `obj.notify()` / `obj.notifyAll()` 唤醒 / 时间到 / 被 `interrupt()`
状态TIMED_WAITING无参 → WAITING；带超时 → TIMED_WAITING
典型用途延时、限速、退避重试线程间协作（生产者-消费者、条件等待）

一句话记忆：**sleep 是"我要休息"，wait 是"我等你叫我"**。

追问 为什么 `wait()` 定义在 `Object` 而不是 `Thread`？

因为 `wait/notify` 是围绕*对象监视器 (monitor)* 的机制—— **每个 Java 对象都自带一把锁**，所以 `wait/notify/notifyAll` 必然属于 `Object`。`obj.wait()` 的语义是「释放 `obj` 的 monitor，把当前线程挂到 `obj` 的等待队列」；而不是「让 Thread 类做点什么」。

追问 `wait()` 为什么必须在 `synchronized` 块里？

因为 `wait()` 的核心动作是**"释放锁并挂起"**—— 想释放锁，你得先持有锁。JDK 强制要求调 `obj.wait()` 时当前线程必须持有 `obj` 的 monitor，否则直接抛 `IllegalMonitorStateException`。这也是为什么 `wait/notify` 模式经典写法必带 `synchronized(obj) { while(...) obj.wait(); }`。用 `while` 而不是 `if` 是为了防*虚假唤醒 (spurious wakeup)*。

## 面试场景 9：join() 的作用

🎤 面试官

`Thread.join()` 干什么用的？

🧑‍💻 你

`t.join()` 的语义是：**"当前线程等待线程 t 执行结束后再继续"**。经典场景是主线程等所有子线程做完聚合结果：

```
Thread t1 = new Thread(() -> process("task-A"));
Thread t2 = new Thread(() -> process("task-B"));
t1.start(); t2.start();

t1.join();  // 主线程 park，等 t1 结束
t2.join();  // 再等 t2 结束

System.out.println("all done");
```

底层实现有点意思：`Thread.join()` 内部其实是**调用 `t.wait()`**—— 因为 JVM 保证一个线程在 `TERMINATED` 时会自动 `notifyAll()` 自己这个对象。所以 `join()` 是搭在 `wait/notify` 之上的方便封装。

追问 `join()` 会导致什么状态？可以有超时吗？

无参 `join()` 会让当前线程进 **WAITING**；带超时的 `join(millis)` 进 **TIMED_WAITING**。超时到了就自动返回继续往下走，不管目标线程是否真的结束。所以生产代码想控制"最长等 5 秒"就用 `t.join(5000)`。

## 面试场景 10：interrupt / interrupted / isInterrupted ★经典陷阱

🎤 面试官

`Thread` 里三个跟"中断"相关的方法，分别是干什么的？

🧑‍💻 你

三个名字长得像的方法，语义完全不同：

方法类型作用是否清除标志

`t.interrupt()`实例方法把线程 `t` 的*中断标志位*设为 `true`；如果 `t` 正在 `sleep/wait/join`，还会抛 `InterruptedException` 唤醒它否（只是设标志）
`t.isInterrupted()`实例方法查线程 `t` 的中断标志位**不清除**
`Thread.interrupted()`静态方法查*当前线程*的中断标志位，然后**清除它**清除（读后清零）

另一个关键点：**抛出 `InterruptedException` 时，标志位会被自动清除**。所以以下代码是错的：

```
try {
Thread.sleep(1000);
} catch (InterruptedException e) {
// 什么都不做 ← 大坑！中断标志已被清，上层完全感知不到发生过中断
}
```

正确写法是**重置中断标志**：

```
try {
Thread.sleep(1000);
} catch (InterruptedException e) {
Thread.currentThread().interrupt();  // 补回标志，让上层能响应
}
```

追问 怎么优雅地停止一个线程？为什么 `Thread.stop()` 被弃用？

优雅的做法是**协作式中断**：调 `t.interrupt()`，然后让 `t` 内部循环里 `while (!Thread.currentThread().isInterrupted()) {...}` 主动检查退出，或在 catch `InterruptedException` 时退出。

`Thread.stop()` 弃用的原因是它**会立即抛 `ThreadDeath` 强行终止线程**—— 线程持有的 `synchronized` 锁会被*直接释放*，但受锁保护的共享数据可能只更新到一半，导致其它线程看到**不一致状态**。而且异常抛出点不可预测，可能刚 `new` 完对象没赋值就死了，资源泄漏 + 数据损坏。同样被弃的还有 `suspend()`（挂起但不释放锁，容易死锁）、`resume()`。

追问 怎么实现一个响应中断的阻塞操作？

三条路：**(1)** 循环里主动检查 `Thread.interrupted()`，退出前处理清理；**(2)** 调用*可中断的阻塞方法*—— `Thread.sleep`、`Object.wait`、`BlockingQueue.take`、`Lock.lockInterruptibly`、`InterruptibleChannel` 的 I/O 方法都会抛 `InterruptedException`；**(3)** 用 `LockSupport.park()` 挂起当前线程—— 它会响应 `interrupt()`，被唤醒后*不抛异常*，但 `Thread.interrupted()` 会返回 true。*注意：普通的 `InputStream.read()`、`Socket.read()` 不响应中断*，要中断必须关掉底层 socket。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：start() vs run() 的线程差异

```
public class StartVsRun {
public static void main(String[] args) {
Runnable r = () -> System.out.println("running in: "
+ Thread.currentThread().getName());

Thread t = new Thread(r, "worker");
t.run();     // 在 main 线程直接执行 → running in: main
t.start();   // JVM 起新线程 → running in: worker
}
}
```

再试一次 `t.start()` 两次会怎样？答案：第二次抛 `IllegalThreadStateException`—— 因为线程已不在 NEW 状态。

### 验证 2：6 种状态各来一次

```
import static java.lang.Thread.State.*;

public class ThreadStates {
public static void main(String[] args) throws Exception {
Object lock = new Object();

Thread t = new Thread(() -> {
synchronized (lock) {
try {
lock.wait(500);  // TIMED_WAITING
} catch (InterruptedException e) {
Thread.currentThread().interrupt();
}
}
}, "demo");

System.out.println(t.getState());  // NEW
t.start();
Thread.sleep(50);
System.out.println(t.getState());  // TIMED_WAITING（正在 wait(500)）

t.join();
System.out.println(t.getState());  // TERMINATED
}
}
```

### 验证 3：sleep 不释放锁，wait 释放锁

```
public class SleepVsWait {
private static final Object LOCK = new Object();

public static void main(String[] args) throws Exception {
Thread holder = new Thread(() -> {
synchronized (LOCK) {
System.out.println("holder got lock, sleeping...");
try { Thread.sleep(2000); }             // 抱着锁睡
catch (InterruptedException e) { Thread.currentThread().interrupt(); }
System.out.println("holder wake up");
}
}, "holder");

Thread waiter = new Thread(() -> {
System.out.println("waiter trying to enter...");
synchronized (LOCK) {                        // 会 BLOCKED 2s
System.out.println("waiter got lock");
}
}, "waiter");

holder.start();
Thread.sleep(100);
waiter.start();

// 把 Thread.sleep(2000) 换成 LOCK.wait(2000) 再跑一次
// waiter 会立刻拿到锁 —— 因为 wait 释放锁了
}
}
```

### 验证 4：interrupt 唤醒 sleep，并保留标志

```
public class InterruptDemo {
public static void main(String[] args) throws Exception {
Thread worker = new Thread(() -> {
try {
Thread.sleep(10_000);
} catch (InterruptedException e) {
System.out.println("interrupted flag inside catch: "
+ Thread.currentThread().isInterrupted());
// false ← 抛异常时标志被清了
Thread.currentThread().interrupt();  // 补回来
System.out.println("after re-interrupt: "
+ Thread.currentThread().isInterrupted());  // true
}
}, "worker");

worker.start();
Thread.sleep(200);
worker.interrupt();  // 唤醒 sleep 抛 InterruptedException
worker.join();
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 Java 线程的 6 种状态是什么？哪一个是等 `synchronized` 锁失败时的状态？</summary>

6 种：`NEW` / `RUNNABLE` / `BLOCKED` / `WAITING` / `TIMED_WAITING` / `TERMINATED`。等 `synchronized` monitor 失败时是 **BLOCKED**。注意等 `ReentrantLock` 是 WAITING，因为底层用 `LockSupport.park()`。

</details>

<details>

<summary>Q2 `sleep()` 和 `wait()` 三大区别是什么？</summary>

(1) 定义位置：`sleep` 属 `Thread` 静态方法，`wait` 属 `Object` 实例方法；(2) 锁：`sleep` 不释放锁，`wait` 释放当前对象的 monitor；(3) 调用限制：`wait` 必须在 `synchronized(obj)` 里，否则 IllegalMonitorStateException；`sleep` 任何地方能调。唤醒方式也不同：`sleep` 靠时间到 / interrupt；`wait` 靠 notify/notifyAll/时间到/interrupt。

</details>

<details>

<summary>Q3 直接调 `thread.run()` 会怎样？和 `thread.start()` 有本质区别吗？</summary>

`run()` 就是普通方法调用，在*当前线程*同步执行，压根没起新线程。`start()` 才会通过 native `start0()` 让 OS 创建内核线程并异步执行 `run()`。同一个 Thread 对象 `start()` 只能调一次，第二次抛 `IllegalThreadStateException`。

</details>

<details>

<summary>Q4 为什么 `Thread.stop()` 被弃用？怎么优雅地停止线程？</summary>

`stop()` 强杀线程会立即释放持有的锁但受锁保护的数据可能只更新到一半，导致其他线程看到不一致状态；异常点不可预测，还容易资源泄漏。优雅做法是**协作式中断**：`t.interrupt()` 设标志 + 线程内部循环里 `while(!Thread.interrupted())` 主动检查退出，或在 `catch InterruptedException` 后清理并退出。

</details>

<details>

<summary>Q5 `Thread.interrupted()` 和 `t.isInterrupted()` 差别在哪？抛 `InterruptedException` 时标志位怎么变？</summary>

`Thread.interrupted()` 是静态方法，查*当前线程*的中断标志并**清除**（读后清零）；`t.isInterrupted()` 是实例方法，查指定线程的标志**不清除**。`sleep/wait/join` 被中断而抛 `InterruptedException` 时，JVM 会**自动清除中断标志**—— 所以规范做法是在 catch 里 `Thread.currentThread().interrupt()` 把标志补回来，让上层能感知。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.lang.Thread` API —— `start` / `run` / `interrupt` 官方文档

- JDK 21 · `Thread.State` 枚举 —— 6 种状态的规范定义

- JDK 21 · `Object.wait` 规范 —— 为什么必须在 synchronized 里

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0019：**synchronized 关键字详解 · 对象头 · Monitor · 锁升级** —— 并发面试的第二座大山，从"线程"进阶到"锁"。

💬 有任何疑问 ——「BLOCKED 和 WAITING 我还是分不清」「虚拟线程怎么落地」「面试真被问过 XX 变体怎么答」—— 直接问我。这一阶段我陪你把并发的坑全趟一遍。


