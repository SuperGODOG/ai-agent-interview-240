> Lesson 0024 · 阶段三 · 并发编程 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0024 · ReentrantLock &amp; Condition &amp; 公平/非公平锁

这一课是  的直接下游。上一课我们拆了 AQS 的底盘 —— state + FIFO 队列 + 模板方法；这一课我们看 **AQS 最经典的应用 —— `ReentrantLock`**：它是怎么把 AQS 的独占模式包装成一把「可重入 + 可选公平 + 支持多条件」的显式锁的。

面试里 ReentrantLock 的问法很密集：**「和 synchronized 有什么区别？」「公平锁怎么实现的？」「Condition 和 wait/notify 区别？」** —— 答不出这三连就基本挂了并发这一轮。对应  的 。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `new ReentrantLock()` 默认是公平锁还是非公平锁？</summary>

**非公平锁**。无参构造直接调 `this(false)`，追求吞吐。要公平锁得手写 `new ReentrantLock(true)`。第 5 题详细讲为什么默认非公平。

</details>

<details>

<summary>Q0.2 一个 `ReentrantLock` 最多能派生几个 `Condition`？</summary>

**任意多个**。这是 ReentrantLock 相对 `synchronized` 最关键的一个能力 —— `synchronized` 只有一条隐式 waitset（`notifyAll` 会把所有等待线程一起唤醒）；ReentrantLock 每次 `lock.newCondition()` 就多一条独立的 waitQueue，可以精细唤醒某一类等待者。ArrayBlockingQueue 就是靠 `notEmpty` + `notFull` 两个 Condition 分离生产者和消费者的。第 7、9 题会展开。

</details>

## 面试场景 1：ReentrantLock 是什么？和 synchronized 的核心区别

🎤 面试官

ReentrantLock 是什么？为什么有了 synchronized 还要有它？

🧑‍💻 你

`ReentrantLock` 是 JDK 5 引入的**显式锁**（`java.util.concurrent.locks.Lock` 的实现类），基于 **AQS 的独占模式**（`exclusive`）实现，语义等价于 `synchronized`（都是互斥 + 可重入），但 API 层面灵活得多。

- **显式**：手动 `lock()` / `unlock()`，必须写 `try/finally`，加解锁范围可跨方法。

- **可中断**：`lockInterruptibly()` 等锁时能被 `Thread.interrupt()` 打断。

- **可超时**：`tryLock(3, TimeUnit.SECONDS)`，等不到就放弃 —— 天然避免死锁。

- **可选公平**：构造器传 `true` 就是公平锁，按 FIFO 严格排队。

- **多 Condition**：一把锁能派生任意多个 `Condition`，实现精细唤醒。

`synchronized` 是 JVM 层面的 **关键字**，靠对象头 Mark Word + Monitor 实现，语法简单但没上面这些能力；ReentrantLock 是 JUC 层面的 **类库**，灵活但要小心手动释放。

追问 ReentrantLock 一定要在 finally 里释放吗？为什么？

**必须**。ReentrantLock 是*显式锁*，JVM 不会像 `synchronized` 那样在方法/代码块退出（含异常抛出）时自动释放。如果在临界区代码抛异常没走到 `unlock()`，锁就永远不会释放 —— 其他线程 `lock()` 会永久阻塞，进程级死锁。所以模板永远是：`lock.lock(); try { ... } finally { lock.unlock(); }`，**`lock()` 一定要写在 `try` 外面**（否则加锁失败直接进 `finally` 会误释放没持有的锁）。

## 面试场景 2：ReentrantLock 的三种加锁方式

🎤 面试官

ReentrantLock 的 `lock()`、`tryLock()`、`lockInterruptibly()` 有什么区别？分别用在什么场景？

🧑‍💻 你

三种加锁方式对应三种「等不到锁时怎么办」的策略：

方法抢不到锁时行为响应中断典型场景

`lock()`
阻塞等待，直到拿到锁
❌ 不响应（中断只是记录）
短临界区、必须拿到锁才能继续

`tryLock()`
立即返回 `false`
—
「拿不到就走别的路」，避免死锁

`tryLock(timeout, unit)`
最多等 timeout，超时返回 `false`
✅ 抛 `InterruptedException`
接口有 SLA 上限，超时降级

`lockInterruptibly()`
阻塞等待，可被打断
✅ 抛 `InterruptedException`
等待可能很久，用户端可能取消

```
// 通用模板
Lock lock = new ReentrantLock();
lock.lock();                       // ← 必须在 try 外
try {
// 临界区
} finally {
lock.unlock();                 // ← 必须在 finally
}

// tryLock 模板
if (lock.tryLock(3, TimeUnit.SECONDS)) {
try { /* ... */ } finally { lock.unlock(); }
} else {
// 超时降级，比如返回缓存 / 走异步
}
```

追问 `lockInterruptibly()` 和 `lock()` 到底差在哪一步？

底层都是走 AQS 的独占获取。区别在于：`lock()` 走的是 `acquire(1)`，等锁过程中检测到线程被中断，只是把中断标志*记下来*（`selfInterrupt()`），继续死等；`lockInterruptibly()` 走的是 `acquireInterruptibly(1)`，一进方法就检查 `Thread.interrupted()`，等锁循环里也检查，一旦中断立刻抛 `InterruptedException`。所以想让「取消操作」能真正打断阻塞的线程，一定得用 `lockInterruptibly`。

## 面试场景 3：ReentrantLock 的可重入怎么实现？★核心

🎤 面试官

「可重入」是什么意思？ReentrantLock 是怎么用 AQS 的 state 实现可重入的？

🧑‍💻 你

**可重入**指同一个线程可以多次拿同一把锁而不死锁 —— 比如递归方法、同一对象的两个 `synchronized` 方法互相调用。ReentrantLock 用 AQS 的 `state` 字段做「重入计数器」：

- **state == 0**：锁空闲，CAS 抢到就是自己的，同时把 `exclusiveOwnerThread` 设为当前线程。

- **state > 0 且 owner == 当前线程**：说明是同一线程重入，`state++` 直接返回成功，不用排队。

- **state > 0 且 owner != 当前线程**：其他线程持有中，进 CLH 队列排队。

释放对称：每次 `unlock()` 让 `state--`，直到 `state == 0` 才把 `owner` 置空、才真正释放锁、才唤醒队首。

```
// ReentrantLock.Sync（非公平版）核心源码
final boolean nonfairTryAcquire(int acquires) {
final Thread current = Thread.currentThread();
int c = getState();
if (c == 0) {                              // 锁空闲
if (compareAndSetState(0, acquires)) { // CAS 抢锁
setExclusiveOwnerThread(current);
return true;
}
}
else if (current == getExclusiveOwnerThread()) {  // ★重入
int nextc = c + acquires;
if (nextc < 0) throw new Error("Maximum lock count exceeded");
setState(nextc);                       // state++（不需要 CAS，因为已经独占）
return true;
}
return false;
}

protected final boolean tryRelease(int releases) {
int c = getState() - releases;
if (Thread.currentThread() != getExclusiveOwnerThread())
throw new IllegalMonitorStateException();
boolean free = false;
if (c == 0) {                              // ★重入次数归零才真正释放
free = true;
setExclusiveOwnerThread(null);
}
setState(c);
return free;
}
```

陷阱 **加了几次锁，就必须解几次**。`lock.lock(); lock.lock(); ...; lock.unlock();` 只解了一次 —— `state` 还剩 1，锁没有真正释放，其他线程永远等不到。写递归临界区时数错次数是经典 bug。

追问 ReentrantLock 是可重入的，那 synchronized 是不是也可重入？

**是的，两者都可重入**。`synchronized` 的可重入靠 Monitor 内部的 *owner* + *count* 字段（HotSpot 里叫 `_owner` 和 `_recursions`），机制和 ReentrantLock 一模一样 —— 同一线程再次进入就 count++，退出就 count--，归零才真正释放 monitor。所以说「Reentrant」这个名字只是把「可重入」这个特性挂在锁名里显式声明了，功能上并不是 ReentrantLock 独有的。

## 面试场景 4：公平锁 vs 非公平锁在源码的实现差异

🎤 面试官

ReentrantLock 的公平锁和非公平锁在源码上就差了一行，能说出是哪一行吗？

🧑‍💻 你

ReentrantLock 内部有个抽象类 `Sync extends AbstractQueuedSynchronizer`，下面挂两个子类：`FairSync`（公平）和 `NonfairSync`（非公平），核心差异就在 `tryAcquire` 里对「锁空闲」分支的处理 —— 公平版**多了一句 `!hasQueuedPredecessors()`**：

```
// NonfairSync：谁抢到算谁的
final boolean nonfairTryAcquire(int acquires) {
...
if (c == 0) {
if (compareAndSetState(0, acquires)) {   // ← 直接 CAS 抢
setExclusiveOwnerThread(current);
return true;
}
}
...
}

// FairSync：先看看队列里有没有前辈在排队
protected final boolean tryAcquire(int acquires) {
...
if (c == 0) {
if (!hasQueuedPredecessors() &&          // ★ 唯一区别
compareAndSetState(0, acquires)) {
setExclusiveOwnerThread(current);
return true;
}
}
...
}
```

`hasQueuedPredecessors()` 检查 AQS 的 CLH 队列里是不是有别的线程在排队等这把锁；**公平锁**发现有前辈就*老老实实排队*，绝不插队；**非公平锁**不看队列，直接 CAS 抢一把，抢到就走，抢不到再去排队。

另外一处小差别：`NonfairSync.lock()` 一进方法先来一个 `compareAndSetState(0, 1)`「快速抢占」，抢到就直接绑 owner 返回，不走 `acquire`；`FairSync.lock()` 老实调 `acquire(1)`。

## 面试场景 5：为什么 ReentrantLock 默认非公平？

🎤 面试官

公平锁听起来更"公平"，为什么 JDK 反而把非公平设为默认？

🧑‍💻 你

核心原因是**吞吐量**。非公平锁允许"插队"，减少的是**线程切换开销**：

1. 假设线程 A 刚释放锁，队首是 B，B 还在 `park` 状态未被唤醒。这时线程 C 刚好调 `lock()` —— 如果是公平锁，C 必须去队尾排队等 B 醒；如果是非公平锁，C 直接 CAS 拿到锁跑了。**C 免掉了一次 park/unpark**，B 也没损失（反正它本来也要被唤醒去争锁）。

2. park/unpark 是**系统调用**（Linux 上是 futex），涉及内核态切换，代价远高于一次 CAS。非公平锁把这次切换省掉了。

3. 虽然理论上非公平可能出现"某个线程被反复插队"的**饥饿**，但实践中：*只要线程已经进队列 park 了，后来的插队者也不会去唤醒它，它照样会被队首的 unpark 醒过来重试*。饥饿只是概率问题，不是必然。

Doug Lea 的结论：默认非公平 → 吞吐显著更高，只有对**响应时间方差**敏感的场景（比如实时系统、严格 SLA）才用公平锁。

陷阱 「非公平」不等于「饿死」。非公平锁的插队只发生在**其他线程刚释放、队首还没被唤醒的那一小段窗口期**；一旦队首线程被 unpark 醒过来，它会重新 `tryAcquire` 争锁，并不会被后来的插队者永久压制。真要出现饥饿需要极端持续的高并发插队。

## 面试场景 6：ReentrantLock vs synchronized 完整对比

维度`ReentrantLock``synchronized`

层级JDK 类库（`java.util.concurrent.locks`）JVM 关键字
加解锁显式 `lock()` / `unlock()`，必须 `try/finally`隐式，进/出代码块自动
异常释放手动写 `finally`，忘了就死锁JVM 自动释放，永远安全
可重入✅（state 计数）✅（Monitor owner + recursions）
可中断等待✅ `lockInterruptibly()`❌
可超时✅ `tryLock(t, u)`❌
非阻塞尝试✅ `tryLock()`❌
公平性可选公平或非公平非公平（且不可配置）
条件变量任意多个 `Condition`，精细唤醒一条隐式 waitset，只能 `notify`/`notifyAll`
性能JDK 5 时明显优于 synchronizedJDK 6 之后引入偏向锁/轻量级锁/自旋，差距基本消失
底层AQS 独占模式对象头 Mark Word + Monitor（`ObjectMonitor`）
可读性需要看 `lock/unlock` 才知道临界区范围代码块清晰

追问 那到底什么时候该用哪个？

默认**优先 `synchronized`**：语法简单、JVM 自动释放、JDK 6 后性能已经够用、字节码可读性好。**需要下面这些能力时才换 ReentrantLock**：① 需要 `tryLock` 探测式加锁避免死锁；② 需要响应中断/超时；③ 需要多个 Condition 精细唤醒（如实现自己的 BlockingQueue）；④ 需要严格公平锁；⑤ 需要跨方法/跨对象的复杂锁模式。业务代码 90% 用 synchronized 就够了。

## 面试场景 7：Condition 是什么？为什么要有它？★核心

🎤 面试官

`Condition` 是什么？和 `Object.wait/notify` 相比多了什么能力？

🧑‍💻 你

`Condition` 是 `Lock` 的**条件变量**，通过 `lock.newCondition()` 创建。它的具体实现是 AQS 里的一个内部类 `ConditionObject`，每个 Condition 都维护**一条独立的单向链表 waitQueue**，作用相当于 `synchronized` 里 `Object.wait/notify` 的等待集，但功能强大得多：

- **一把锁可以有任意多个 Condition**：每个 Condition 对应一类等待原因，`signal` 只唤醒*这一类*的等待者，而不是全部 —— 精细唤醒。

- **可以响应中断**：`await()` 被 `interrupt` 会抛 `InterruptedException`；`awaitUninterruptibly()` 则忽略中断。

- **可以带超时**：`awaitNanos(long)`、`await(t, u)`、`awaitUntil(Date)`。

- **可以是公平的**：如果锁是公平锁，Condition 的 signal 也按 FIFO 从队首挑。

典型例子：`ArrayBlockingQueue` 一把 `ReentrantLock` + 两个 Condition `notEmpty`（消费者等这里）和 `notFull`（生产者等这里）。生产者放完东西只 `notEmpty.signal()` 消费者，不会去骚扰"队列不满"这条队里的其他生产者。如果用 `synchronized` + `wait/notifyAll`，一次 `notifyAll` 会把生产者消费者全叫起来一起争锁，绝大多数被唤醒的线程发现条件还是不满足又睡回去，浪费一堆 park/unpark。

追问 Condition 的 `signal` 会立刻唤醒线程吗？

**不会**。`signal()` 做的只是"把 Condition 队列的队首节点*转移*到 AQS 的 CLH 同步队列尾部"，节点上的线程并没有被 unpark。真正唤醒发生在*之前持有锁的线程 `unlock()` 时* —— `unlock` 会把 CLH 队列队首线程 unpark 起来重试拿锁。所以 signal 后的等待线程要经历"入 CLH 队 → 等前面的锁释放 → 被 unpark → 抢锁 → 抢到才从 await 返回"整条链路。这也是为什么** `signal()` 必须在持有锁的时候调**：否则 IllegalMonitorStateException。

## 面试场景 8：Condition 的 await/signal 机制

🎤 面试官

说一下 `Condition.await()` 和 `signal()` 的完整流程。

🧑‍💻 你

Condition 涉及两条队列：**AQS 的 CLH 同步队列**（争锁排队）和 **Condition 自己的 waitQueue**（等条件排队）。两条队列的节点是同一种 `Node`，节点会在两条队列间转移。

```
┌─────────── CLH 同步队列 ───────────┐   ┌── Condition.waitQueue ──┐
│  head → nodeA → nodeB → nodeC → …   │   │  firstWaiter → w1 → w2  │
└─────────────────────────────────────┘   └─────────────────────────┘
↑                                          │
│  signal():  w1 从 Condition 队列出队      │
│             转移到 CLH 队列尾部           │
└──────────────────────────────────────────┘
```

**await() 完整流程**：

1. 检查：线程必须已经持有锁，否则抛 IllegalMonitorStateException。

2. `addConditionWaiter()`：new 一个 `Node(mode=CONDITION)`，加到 Condition 的 waitQueue 尾部。

3. `fullyRelease(savedState)`：**一次性把 state 清零、完全释放锁**（哪怕重入了 3 次也一次性全释放；savedState 存起来待会恢复），并唤醒 CLH 队首。

4. 循环 `while (!isOnSyncQueue(node)) LockSupport.park(this);`：*只要节点还在 Condition 队列*就一直 park。

5. 被 signal 转移到 CLH 队列后循环退出，走 `acquireQueued(node, savedState)` 重新排队争锁。

6. 抢到锁后：**把 savedState 恢复回 state**（保持重入次数）→ 从 await 返回。

**signal() 完整流程**：

1. 检查：调用者必须持有锁。

2. 取 `firstWaiter`（Condition 队列的队首节点）。

3. `transferForSignal(node)`：把节点的 `waitStatus` 从 `CONDITION(-2)` 改成 `0`，用 `enq(node)` 把它接到 CLH 队列尾部；如果前驱节点已取消或 CAS 设置 SIGNAL 失败，就地 unpark 一下（免得永远醒不来）。

4. 返回 —— 此时节点已经在 CLH 队列排队等锁了，但线程**并未 unpark**。

5. 调用者继续走完临界区，最终 `unlock()` 时按 CLH 队列顺序 unpark 后继节点，被 signal 的线程醒来抢到锁后才从 `await()` 返回。

陷阱 `await()` 一定要放在 `while` 循环里检查条件，不能用 `if`：`while (queue.isEmpty()) notEmpty.await();`。因为 ① 可能被虚假唤醒；② 从 await 醒来到重新抢到锁之间，条件可能已被别的线程改变（比如刚有元素进来又被另一个消费者抢走）。用 `if` 会直接跳过检查去执行动作，产生 NPE 或数据错乱。

## 面试场景 9：手撕生产者消费者（用 Condition 精细唤醒）

🎤 面试官

请用 ReentrantLock + Condition 手写一个有界阻塞队列的生产者消费者。

```
public class BoundedBuffer<E> {
private final Object[] items;
private int putIdx, takeIdx, count;

private final ReentrantLock lock = new ReentrantLock();
private final Condition notFull  = lock.newCondition();  // 生产者等在这
private final Condition notEmpty = lock.newCondition();  // 消费者等在这

public BoundedBuffer(int capacity) {
this.items = new Object[capacity];
}

public void put(E e) throws InterruptedException {
lock.lockInterruptibly();
try {
while (count == items.length) {   // ★ 一定要 while
notFull.await();              // 满了 → 生产者去 notFull 队里睡
}
items[putIdx] = e;
if (++putIdx == items.length) putIdx = 0;
count++;
notEmpty.signal();                // ★ 只叫醒消费者，不打扰生产者
} finally {
lock.unlock();
}
}

@SuppressWarnings("unchecked")
public E take() throws InterruptedException {
lock.lockInterruptibly();
try {
while (count == 0) {
notEmpty.await();             // 空了 → 消费者去 notEmpty 队里睡
}
E e = (E) items[takeIdx];
items[takeIdx] = null;
if (++takeIdx == items.length) takeIdx = 0;
count--;
notFull.signal();                 // ★ 只叫醒生产者
} finally {
lock.unlock();
}
}
}
```

这段代码几乎就是 JDK `ArrayBlockingQueue` 的原型。**精细唤醒**的意义：如果只有一个 waitset（比如 `synchronized` + 一个 `notifyAll`），队列满时消费者拿到东西 `notifyAll` 会把所有生产者*和*其他消费者全叫醒一起争锁，绝大多数消费者醒来发现队列又空了只能睡回去 —— 无效唤醒。Condition 拆成两条队列后，*生产者只叫消费者，消费者只叫生产者*，无效唤醒基本消失。

追问 为什么 put/take 里用 `signal()` 而不是 `signalAll()`？

**精确释放，避免惊群**。每 put 一个元素只让*一个*消费者出来处理正好；`signalAll` 会把所有消费者都叫醒争锁，只有一个抢得到，其他又睡回去，浪费。用 `signal` 的前提是：唤醒任意一个等待者都能推进 —— 生产/消费场景天然满足，所以 `signal` 更优。

## 面试场景 10：ReentrantLock 的实际使用场景

🎤 面试官

项目里什么时候你会主动选 ReentrantLock 而不是 synchronized？

🧑‍💻 你

1. **需要 `tryLock` 避免死锁**：多把锁按顺序取时，用 `tryLock` 拿不到就回滚已持有的锁，避免 A-B / B-A 顺序引起的死锁。

2. **需要可中断响应超时**：接口有 SLA，等锁最多等 100ms 就要降级返回缓存 —— 只能靠 `tryLock(100, MILLIS)`。

3. **读多写少 → `ReentrantReadWriteLock`**：读锁共享、写锁独占，配置中心、缓存元数据这种极端读多写少场景性能吊打互斥锁（JDK 8+ 更推荐 `StampedLock` —— 支持乐观读）。

4. **手写 BlockingQueue / 生产者消费者**：`ArrayBlockingQueue`、`LinkedBlockingQueue`、`DelayQueue`、`SynchronousQueue` 内部都是 ReentrantLock + 一到两个 Condition。

5. **业务级"锁的持有者"检查**：`lock.isHeldByCurrentThread()`、`lock.getHoldCount()`、`lock.getQueueLength()` 这些运维/监控能力 synchronized 完全没有。

追问 ReadWriteLock 的写锁降级是什么？

**写锁降级**指：线程*先持有写锁*，然后在*不释放写锁的前提下*再申请读锁，成功后再释放写锁 —— 于是从"写锁独占"平滑降为"读锁共享"，中间不会被其他写线程插入。**反过来的锁升级（先持读锁再升级为写锁）不允许** —— 因为多个读线程同时尝试升级会互相死锁。典型用法：`写锁下修改数据 → 获取读锁 → 释放写锁 → 用读锁继续读修改后的数据，同时允许其他读线程进入`，比先释放写锁再拿读锁多了个「保证中间没人偷改数据」的原子性。

追问 项目里有没有 ReentrantLock 用错的例子？

常见有三个：① **忘写 `finally`**，或者 `lock()` 写在 `try` 里（加锁失败进 finally 又 unlock 抛 IllegalMonitorStateException 掩盖真实异常）；② **把 ReentrantLock 声明为局部变量**，每次进方法 new 一把新锁，等于没加锁；③ **用 `Object.wait/notify` 在 ReentrantLock 里**，编译能过但抛 IllegalMonitorStateException —— Condition 才是 ReentrantLock 的配套等待唤醒机制。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：可重入 —— state 计数

```
import java.util.concurrent.locks.ReentrantLock;

public class ReentrantDemo {
private static final ReentrantLock lock = new ReentrantLock();

static void outer() {
lock.lock();
try {
System.out.println("outer  holdCount = " + lock.getHoldCount()); // 1
inner();
System.out.println("after inner, holdCount = " + lock.getHoldCount()); // 1
} finally {
lock.unlock();
}
}

static void inner() {
lock.lock();       // 同一线程重入
try {
System.out.println("inner  holdCount = " + lock.getHoldCount()); // 2
} finally {
lock.unlock(); // 必须配对，state 从 2 降回 1
}
}

public static void main(String[] args) { outer(); }
}
```

观察点：`getHoldCount()` 直接读的就是 AQS 的 `state`。加两次锁 state = 2，解一次才降回 1，全部退出才归 0。

### 验证 2：公平锁 vs 非公平锁

```
import java.util.concurrent.locks.ReentrantLock;

public class FairnessDemo {
public static void main(String[] args) throws InterruptedException {
test("非公平", new ReentrantLock(false));
Thread.sleep(500);
test("公平", new ReentrantLock(true));
}

static void test(String name, ReentrantLock lock) throws InterruptedException {
System.out.println("---- " + name + " ----");
for (int i = 0; i < 5; i++) {
final int id = i;
new Thread(() -> {
for (int j = 0; j < 2; j++) {
lock.lock();
try {
System.out.println("thread-" + id + " got lock");
} finally {
lock.unlock();
}
}
}, "T-" + i).start();
}
Thread.sleep(300);
}
}
// 非公平：某些线程连续输出两次（插队命中）
// 公平：严格 T-0 T-1 T-2 T-3 T-4 T-0 T-1 …… 轮转
```

### 验证 3：tryLock 避免死锁

```
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.TimeUnit;

public class TryLockDemo {
static final ReentrantLock A = new ReentrantLock();
static final ReentrantLock B = new ReentrantLock();

static void doWork(ReentrantLock first, ReentrantLock second, String name) {
while (true) {
if (first.tryLock()) {
try {
if (second.tryLock()) {
try {
System.out.println(name + " got both, working…");
return;
} finally { second.unlock(); }
}
} finally { first.unlock(); }
}
try { TimeUnit.MILLISECONDS.sleep(10); } catch (InterruptedException e) { return; }
}
}

public static void main(String[] args) {
new Thread(() -> doWork(A, B, "T1")).start();
new Thread(() -> doWork(B, A, "T2")).start();  // 反顺序也不会死锁
}
}
```

如果换成 `synchronized(A){ synchronized(B){...} }` 和 `synchronized(B){ synchronized(A){...} }`，两个线程各拿一把互等就死锁了。`tryLock` 拿不到第二把就**主动释放第一把**再重试，天然打破循环等待。

### 验证 4：Condition 精细唤醒 —— 有界缓冲区

```
public class BufferDemo {
public static void main(String[] args) throws Exception {
BoundedBuffer<Integer> buf = new BoundedBuffer<>(3);

Thread producer = new Thread(() -> {
for (int i = 0; i < 8; i++) {
try {
buf.put(i);
System.out.println("put  " + i);
Thread.sleep(80);
} catch (InterruptedException e) { return; }
}
}, "P");

Thread consumer = new Thread(() -> {
for (int i = 0; i < 8; i++) {
try {
Thread.sleep(200);           // 消费慢 → 生产者会在 notFull.await 阻塞
System.out.println("take " + buf.take());
} catch (InterruptedException e) { return; }
}
}, "C");

producer.start(); consumer.start();
producer.join();  consumer.join();
}
}
// 观察：前 3 次 put 秒完，第 4 次 put 阻塞等 C 消费一次后 notFull.signal() 才继续
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话说清 ReentrantLock 相对 synchronized 多了哪些能力。</summary>

显式加解锁（可跨方法）、`tryLock`（非阻塞/带超时）、`lockInterruptibly`（可中断等锁）、可选公平锁、任意多个 Condition 精细唤醒、丰富的监控 API（`getHoldCount`、`getQueueLength`）。

</details>

<details>

<summary>Q2 ReentrantLock 的公平锁和非公平锁源码只差在哪？为什么默认非公平？</summary>

差在公平版 `tryAcquire` 里多了一句 `!hasQueuedPredecessors()` —— 只有队列里没有前辈时才 CAS 抢锁。默认非公平是因为吞吐高：允许"锁刚释放、队首还没醒"的窗口期让新来的线程直接 CAS 抢一把，省掉一次 park/unpark 系统调用；且已在队列 park 的线程也不会因此被永久压制。

</details>

<details>

<summary>Q3 `ReentrantLock` 的可重入是靠什么实现的？加两次锁必须解两次吗？</summary>

靠 AQS 的 `state` 字段做重入计数：同一线程再次 `lock()` 时 state++，`unlock()` 时 state--，只有 state 归 0 才真正释放锁并置空 `exclusiveOwnerThread`。所以**加几次必须解几次**，否则 state 一直大于 0，其他线程永远抢不到。

</details>

<details>

<summary>Q4 `Condition.await()` 被调用时发生了什么？`signal()` 会立刻唤醒等待线程吗？</summary>

`await()`：把当前节点加入 Condition 的独立 waitQueue → 一次性完全释放锁（保存 state）→ park。`signal()` **不会立刻唤醒**，它只是把 Condition 队首节点*转移*到 AQS 的 CLH 同步队列尾部；真正的 unpark 发生在 signal 调用者 `unlock()` 之后，节点走到 CLH 队首、被前驱 unpark 后才抢锁、抢到才从 `await` 返回。

</details>

<details>

<summary>Q5 为什么手写生产者消费者要用 `while` 检查条件而不是 `if`？为什么用两个 Condition 而不是一个 `signalAll`？</summary>

**用 `while`**：防虚假唤醒 + 防条件在"醒来→抢到锁"之间被别的线程改变（比如队首消费者被 signal 后醒来抢锁，结果元素已被并发的另一个消费者取走 → 用 if 直接 poll 就是 NPE/数据错乱）。**两个 Condition**：生产者只等在 `notFull`、消费者只等在 `notEmpty`，signal 时精准唤醒对应一类，避免 `notifyAll` 惊群导致的大量无效 park/unpark，吞吐显著更高。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `ReentrantLock` API

- JDK 21 · `Condition` API —— 官方给的示例就是有界缓冲区

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0025：**ThreadLocal 原理 & 内存泄漏** —— 从 `ThreadLocalMap` 的弱引用 key + 强引用 value 讲起，讲清为什么必须 `remove()`、为什么在线程池里格外危险。

💬 有任何疑问 —— 「Condition 的 signal 转移那段能画个更细的图吗？」「非公平锁真的不会饿死吗？极端情况呢？」「读写锁的具体源码怎么和 AQS 共享模式对应？」—— 直接问我。我是你的老师，也是你的追问陪练。


