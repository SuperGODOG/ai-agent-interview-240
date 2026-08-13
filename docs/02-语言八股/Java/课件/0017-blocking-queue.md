> Lesson 0017 · 阶段二 · 集合（收尾） · ⭐⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0017 · 阻塞队列 ArrayBlockingQueue & DelayQueue

阻塞队列是**线程池、生产者-消费者、延时任务**的地基。这一课把最经典的两个源码吃透：****（Lock + Condition 的教科书实现）与 ****（延时调度的巧妙 leader 机制）。学完这一课，阶段二 · 集合就正式收工，下一课起我们进入并发编程。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 ArrayBlockingQueue 为什么用 ReentrantLock 而不是 `synchronized`？</summary>

因为要用 `Condition` 精准区分「队满等待」和「队空等待」两个条件 —— `synchronized` 只有一个 `wait/notify`，唤醒时可能唤到不对的一方。第 7 题细讲。

</details>

<details>

<summary>Q0.2 DelayQueue 的元素排序靠什么？</summary>

元素必须实现 `Delayed` 接口的 `getDelay` 和 `compareTo`，底层 `PriorityQueue` 按 `compareTo` 结果建小顶堆，堆顶是*最早到期*的元素。第 8 题细讲。

</details>

## 面试场景 1：BlockingQueue 接口的四组 API

🎤 面试官

你说说 `BlockingQueue` 有几种 API？满或空的时候各自什么反应？

🧑‍💻 你

四组，按「异常/返回值/阻塞/超时」分：

行为入队出队查看队头

**抛异常**`add(e)``remove()``element()`
**返回特殊值**（false / null）`offer(e)``poll()``peek()`
**无限阻塞**`put(e)``take()`—
**超时阻塞**`offer(e, t, u)``poll(t, u)`—

追问 你实际项目里选哪一组比较多？

大多数场景用**超时阻塞**组（`offer(e, t, u)` / `poll(t, u)`）——既不会像 `put`/`take` 那样卡死无法回收线程，也比 `add`/`offer` 立即返回更能吸收峰值。线程池的默认 API 内部就是 `offer(e)` 非阻塞版本，被拒绝了走 `RejectedExecutionHandler`。

## 面试场景 2：JDK 常见阻塞队列全览

队列底层有界公平典型场景

`ArrayBlockingQueue`数组 + 一把锁 + 双 Condition✅（构造必传）可选线程池经典搭档；有界防 OOM
`LinkedBlockingQueue`单向链表 + 两把锁（读写分离）❌ 默认 Integer.MAX_VALUE否高吞吐读写场景；*但默认无界，慎用*
`PriorityBlockingQueue`二叉小顶堆 + 一把锁❌ 无界（自动扩容）否按优先级出队
`DelayQueue`PriorityQueue + leader 线程❌ 无界否延时任务；元素必须 `Delayed`
`SynchronousQueue`不存元素，直接手递手容量 0可选`Executors.newCachedThreadPool` 内部；直接派发
`LinkedTransferQueue`无界链表 + `transfer`❌否生产者可等消费者接手
`LinkedBlockingDeque`双向链表 + 一把锁可选否工作窃取 Deque

## 面试场景 3：线程池默认阻塞队列的陷阱

🎤 面试官

`Executors.newFixedThreadPool(10)` 用的是哪种阻塞队列？有什么问题？

🧑‍💻 你

底层是 `new LinkedBlockingQueue<Runnable>()`，容量默认 `Integer.MAX_VALUE`。**无界队列**意味着任务只要提交就永远不会被拒绝、也永远撑不满触发扩容 —— 于是任务持续堆积，最终 **OOM**。

类似的陷阱：`newCachedThreadPool` 用 `SynchronousQueue`，配 `maxPoolSize = Integer.MAX_VALUE` —— 任务只要来，就直接扩线程，可能爆炸创出几万个线程。

正确做法：**自己 `new ThreadPoolExecutor`，显式传 `ArrayBlockingQueue` 有界队列 + 明确的拒绝策略**（这也是《阿里 Java 开发手册》的强制规约）。

陷阱 `Executors` 的四个「便捷」工厂方法在生产环境几乎**都不能直接用**：`newFixedThreadPool` / `newSingleThreadExecutor` 用无界队列易 OOM；`newCachedThreadPool` 无界线程数易爆栈；`newScheduledThreadPool` 底层 `DelayedWorkQueue` 也是无界。线程池细节留到 0026 深挖。

## 面试场景 4：ArrayBlockingQueue 的字段结构（★核心）

🧑‍💻 你

核心字段就 6 个：

```
public class ArrayBlockingQueue<E> extends AbstractQueue<E>
implements BlockingQueue<E> {
final Object[] items;           // 存元素的定长数组
int takeIndex;                  // 下次 take 的位置
int putIndex;                   // 下次 put 的位置
int count;                      // 当前元素个数
final ReentrantLock lock;       // 一把锁
private final Condition notEmpty;   // 队非空条件（唤醒 take 者）
private final Condition notFull;    // 队非满条件（唤醒 put 者）
...
}
```

构造函数**必须传容量**（有界），可选公平/非公平锁（默认非公平，性能高但可能饥饿）：

```
new ArrayBlockingQueue<>(1024);            // 非公平
new ArrayBlockingQueue<>(1024, true);      // 公平
```

追问 ABQ 为什么用**环形数组**而不是普通队列？

为了**空间复用不搬迁**。`putIndex` / `takeIndex` 各自到达数组末尾时归零重头走，就像一圈跑道。而不是像普通队列那样 dequeue 后所有元素往前移动 —— 那是 O(n) 灾难。环形数组的 enqueue/dequeue 都是 O(1)。

## 面试场景 5：ABQ 的 put 完整流程（★背下来）

🧑‍💻 你

```
public void put(E e) throws InterruptedException {
Objects.requireNonNull(e);
final ReentrantLock lock = this.lock;
lock.lockInterruptibly();                   // ① 可中断加锁
try {
while (count == items.length)           // ② while 循环防虚假唤醒
notFull.await();                    //    队满则挂到 notFull
enqueue(e);                             // ③ 环形数组入队
} finally {
lock.unlock();                          // ⑤ 释放锁
}
}

private void enqueue(E e) {
final Object[] items = this.items;
items[putIndex] = e;
if (++putIndex == items.length) putIndex = 0;   // 环形归零
count++;
notEmpty.signal();                          // ④ 唤醒一个 take 等待者
}
```

关键点：**用 `while` 而不是 `if`** 判断队满 —— 防止「虚假唤醒」（`Condition.await` 规范允许无信号也返回）；signal 时机在*已入队后*，唤醒的 take 者能立刻拿到元素。

## 面试场景 6：ABQ 的 take 完整流程

🧑‍💻 你

```
public E take() throws InterruptedException {
final ReentrantLock lock = this.lock;
lock.lockInterruptibly();
try {
while (count == 0)
notEmpty.await();                   // 队空则挂到 notEmpty
return dequeue();
} finally {
lock.unlock();
}
}

private E dequeue() {
final Object[] items = this.items;
E e = (E) items[takeIndex];
items[takeIndex] = null;                    // 帮 GC
if (++takeIndex == items.length) takeIndex = 0;
count--;
notFull.signal();                           // 唤醒一个 put 等待者
return e;
}
```

put 和 take 完全对称，一个是「满 → 等 notFull → 入队 → 通知 notEmpty」，另一个是「空 → 等 notEmpty → 出队 → 通知 notFull」。

## 面试场景 7：ABQ 为什么一把锁，而 LinkedBlockingQueue 是两把锁？

🧑‍💻 你

核心差别在**数据结构本身能不能做到读写解耦**：

- `ArrayBlockingQueue`：数组 + putIndex / takeIndex 共享 `count`。put 时要动 `putIndex + count`，take 时要动 `takeIndex + count` —— `count` 是共享写入点，硬要拆两把锁反而要为 `count` 引入 CAS 或另一层锁，得不偿失。所以一把锁最简单。

- `LinkedBlockingQueue`：单向链表 `head` / `tail` 两端天然分离，头出队只动 `head`，尾入队只动 `tail`，中间用 `AtomicInteger count`。所以拆成 `takeLock` + `putLock` 让读写完全并行。

结论：**ABQ 单锁不是缺陷，是结构决定的最优解**；LBQ 双锁不是「更先进」，是链表结构才有条件这么做。

追问 那 ABQ 和 LBQ 该怎么选？

看**吞吐 vs 稳定性**：LBQ 吞吐高（读写并行）但节点分配 + 无界默认易 OOM；ABQ 单锁竞争大但预分配数组无 GC 压力且必须有界。**生产线程池首选 ABQ**，因为可控性是压倒性的。

## 面试场景 8：DelayQueue 的结构 & Delayed 接口（★核心）

🧑‍💻 你

```
public class DelayQueue<E extends Delayed> extends AbstractQueue<E>
implements BlockingQueue<E> {
private final transient ReentrantLock lock = new ReentrantLock();
private final PriorityQueue<E> q = new PriorityQueue<E>();   // 小顶堆
private Thread leader = null;                                  // ★ leader 线程
private final Condition available = lock.newCondition();       // 唯一条件
}

// 元素约束
public interface Delayed extends Comparable<Delayed> {
long getDelay(TimeUnit unit);   // 剩余延时
// 继承 Comparable，一般按到期时间排序
}
```

特点：

- **无界**：底层 `PriorityQueue` 会自动扩容。

- **元素必须实现 `Delayed`**：`getDelay` 返回剩余延时，`compareTo` 决定堆序（最早到期在堆顶）。

- **只有到期元素能出队**：`poll` 未到期返回 `null`；`take` 会阻塞到最早元素到期。

## 面试场景 9：DelayQueue 的 take + leader 机制（★经典）

🎤 面试官

假设 DelayQueue 有 10 个消费者，队头元素还有 5 秒到期，你觉得会发生什么？

🧑‍💻 你

如果没有 leader 机制，10 个消费者都会 `awaitNanos(5秒)`，等待期间都在时钟队列里，5 秒后**全部被唤醒**，抢一个元素 —— 一次*惊群效应*，浪费 9 次调度。

DelayQueue 的解法：**只让第一个消费者当 leader**，负责真正的 `awaitNanos(delay)` 定时；后来的消费者全部 `available.await()` 无限等待。leader 到期拿走元素后 `signal()` 传接力棒。

```
public E take() throws InterruptedException {
final ReentrantLock lock = this.lock;
lock.lockInterruptibly();
try {
for (;;) {
E first = q.peek();
if (first == null) {
available.await();                  // ① 队空 → 无限等
} else {
long delay = first.getDelay(NANOSECONDS);
if (delay <= 0L)
return q.poll();                // ② 到期直接取走

first = null;                       // 别持引用避免影响 GC
if (leader != null) {
available.await();              // ③ 已有 leader → 无限等
} else {
Thread thisThread = Thread.currentThread();
leader = thisThread;            // ④ 我来当 leader
try {
available.awaitNanos(delay);// ⑤ 只有 leader 定时
} finally {
if (leader == thisThread)
leader = null;
}
}
}
}
} finally {
if (leader == null && q.peek() != null)
available.signal();                     // ⑥ 交接力棒
lock.unlock();
}
}
```

追问 leader 机制的本质是什么？

把「多消费者定时」**合并成一次定时唤醒**，避免惊群。这是并发场景里非常常见的优化模式，Doug Lea 也用在 `ScheduledThreadPoolExecutor.DelayedWorkQueue` 里。

## 面试场景 10：DelayQueue 的实战应用

🧑‍💻 你

1. **定时调度**：`ScheduledThreadPoolExecutor` 内部就用 `DelayedWorkQueue`（一个特化的 DelayQueue）。

2. **订单超时取消**：下单时把订单包一层 `Delayed`（延时 = 30 分钟）放入 DelayQueue；消费者 `take` 到期订单，检查未付款则取消。

3. **缓存过期**：把 `(key, expireTime)` 塞 DelayQueue，后台线程 `take` 出到期 key 删缓存。

4. **消息重试**：失败消息按指数退避时间入 DelayQueue，到时重试。

5. **限流令牌桶**：按定时间隔发令牌到 DelayQueue，请求方 `poll` 得到令牌才可通行。

陷阱 DelayQueue 是**单机**方案，进程挂了任务全丢。生产环境的延时任务通常用 **Redis ZSet**、**RocketMQ 定时消息**、**Quartz + DB** 或 **时间轮**（Netty HashedWheelTimer / Kafka Purgatory）来做，保证可靠性。DelayQueue 只适合*单机内部小规模、允许丢失*的场景。

## 💻 代码验证

### 验证 1：BlockingQueue 四组 API 对比

```
import java.util.concurrent.*;

BlockingQueue<String> q = new ArrayBlockingQueue<>(2);
q.put("a"); q.put("b");

// 抛异常组
try { q.add("c"); } catch (IllegalStateException e) { System.out.println("add 满 → 抛异常"); }

// 返回特殊值组
System.out.println(q.offer("c"));   // false，不抛不阻塞

// 无限阻塞组（另起线程演示）
// q.put("c");   ← 会一直卡住直到有 take

// 超时阻塞组
boolean ok = q.offer("c", 500, TimeUnit.MILLISECONDS);
System.out.println("offer 超时 500ms → " + ok);
```

### 验证 2：ABQ 生产者-消费者模板

```
import java.util.concurrent.*;

public class ProducerConsumer {
public static void main(String[] args) {
BlockingQueue<Integer> q = new ArrayBlockingQueue<>(10);

// 生产者
new Thread(() -> {
for (int i = 0; i < 100; i++) {
try { q.put(i); System.out.println("put " + i); }
catch (InterruptedException e) { Thread.currentThread().interrupt(); break; }
}
}, "Producer").start();

// 消费者
new Thread(() -> {
while (true) {
try {
Integer v = q.take();
System.out.println("  take " + v);
Thread.sleep(50);              // 模拟消费慢
} catch (InterruptedException e) { Thread.currentThread().interrupt(); break; }
}
}, "Consumer").start();
}
}
```

### 验证 3：DelayQueue 实现订单超时取消

```
import java.util.concurrent.*;
import static java.util.concurrent.TimeUnit.*;

class DelayedOrder implements Delayed {
final String orderId;
final long expireAt;                 // 到期毫秒时间戳

DelayedOrder(String id, long delayMs) {
this.orderId = id;
this.expireAt = System.currentTimeMillis() + delayMs;
}
public long getDelay(TimeUnit unit) {
return unit.convert(expireAt - System.currentTimeMillis(), MILLISECONDS);
}
public int compareTo(Delayed o) {
return Long.compare(this.expireAt, ((DelayedOrder) o).expireAt);
}
}

public class OrderTimeoutDemo {
public static void main(String[] args) throws Exception {
DelayQueue<DelayedOrder> queue = new DelayQueue<>();
queue.offer(new DelayedOrder("O-1", 3000));
queue.offer(new DelayedOrder("O-2", 1000));
queue.offer(new DelayedOrder("O-3", 2000));

while (!queue.isEmpty()) {
DelayedOrder o = queue.take();
System.out.printf("%tT 订单超时: %s%n", System.currentTimeMillis(), o.orderId);
}
// 输出顺序：O-2 → O-3 → O-1（按到期时间）
}
}
```

### 验证 4：观察 ABQ 环形数组（反射窥探内部 items）

```
import java.lang.reflect.Field;
import java.util.concurrent.ArrayBlockingQueue;

public class RingArrayInspect {
public static void main(String[] args) throws Exception {
var q = new ArrayBlockingQueue<Integer>(4);
q.put(1); q.put(2); q.put(3);
q.take();                                    // takeIndex 从 0 走到 1
q.take();                                    // takeIndex 走到 2
q.put(4); q.put(5);                          // putIndex 环形归零，覆盖 0 位

Field f = ArrayBlockingQueue.class.getDeclaredField("items");
f.setAccessible(true);
Object[] items = (Object[]) f.get(q);
System.out.println(java.util.Arrays.toString(items));
// 可能看到 [5, null, 3, 4] —— putIndex 已经绕回索引 0
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `put/take`、`offer/poll`、`add/remove` 三组入队出队 API 的区别？</summary>

put/take 无限阻塞；offer/poll 立即返回 boolean/null；add/remove 满或空时直接抛异常。生产场景多用带超时的 `offer(e, t, u)`/`poll(t, u)`。

</details>

<details>

<summary>Q2 为什么 `Executors.newFixedThreadPool` 在生产环境不推荐？</summary>

底层用 `LinkedBlockingQueue` 无界队列 → 任务无限堆积 → OOM。应该自己 `new ThreadPoolExecutor`，显式传 `ArrayBlockingQueue` 有界队列 + 明确的拒绝策略。

</details>

<details>

<summary>Q3 ABQ 的 put 里 `while(count == items.length) notFull.await()` 为什么用 while 不是 if？</summary>

防止**虚假唤醒**（spurious wakeup）。`Condition.await` 规范允许在无 signal 情况下也返回；用 while 会重新检查条件，只有条件真正成立才继续。这是并发编程的通用规范。

</details>

<details>

<summary>Q4 DelayQueue 的 leader 机制解决什么问题？</summary>

避免**惊群效应**：多个消费者同时 `awaitNanos(delay)` 会在到期时全部被唤醒抢一个元素。leader 机制只让一个线程真正定时，其他线程无限等待，元素到期后由 leader 传接力棒 `signal`。

</details>

<details>

<summary>Q5 生产环境的延时任务，DelayQueue 够用吗？</summary>

不够。DelayQueue 是**单机内存**方案，进程挂任务全丢。需要可靠的延时调度请用：Redis ZSet 轮询、RocketMQ 定时消息、Quartz + DB、或 Netty/Kafka 的时间轮（HashedWheelTimer）。

</details>

#### 📖 原文

-

-

- JDK · `BlockingQueue` API

- JDK · `Condition` API（虚假唤醒规范说明）

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0018：**阶段三 · 并发编程** 开篇 —— 线程基础、生命周期、Thread vs Runnable、start vs run、sleep vs wait、interrupt 三兄弟。并发是面试最深的一块，我们从最扎实的基础开始。

💬 想问「时间轮的实现原理？」「Redis ZSet 怎么做延时？」「工作窃取 Deque 是什么？」—— 都可以直接问我。


