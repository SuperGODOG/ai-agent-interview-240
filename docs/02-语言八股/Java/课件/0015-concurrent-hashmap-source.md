> Lesson 0015 · 阶段二 · 集合与并发容器 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0015 · ConcurrentHashMap 源码深挖

这一课覆盖的最高频考点。**ConcurrentHashMap（简称 CHM）是 `java.util.concurrent` 里最具代表性的容器**，也是和 HashMap 齐名的两大硬骨头之一。1.7 → 1.8 的演进堪称「并发调优活教材」——从*分段锁 + ReentrantLock* 演进到 *桶级 synchronized + CAS + 红黑树*，几乎能把并发编程的核心思想（细粒度锁、CAS、无锁读、分片计数、协作扩容）全串起来。面试频次极高，几乎必问。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 CHM 1.7 和 1.8 的锁粒度分别是什么？分别支持多少个线程并发写？</summary>

1.7 锁粒度是 **Segment**（一段桶），默认 16 个 Segment → 最多 16 线程并发写；1.8 锁粒度细化到 **单个桶头节点**（synchronized），并发度 ≈ 桶数（默认初始 16，可动态扩容到几万几十万）。第 2、4、6 题会详细展开。

</details>

<details>

<summary>Q0.2 `chm.size()` 返回的是精确值吗？为什么？</summary>

**不是精确值，只是近似值**。CHM 用 `baseCount + CounterCell[]` 分片计数（类似 `LongAdder`），`size()` 时把它们求和，但求和过程中如果有其他线程 `put/remove`，结果就会漂。设计上就不希望你依赖精确 size，需要精确统计请业务自己加锁。第 8 题展开。

</details>

## 面试场景 1：为什么需要 ConcurrentHashMap？`Hashtable` 和 `Collections.synchronizedMap` 不行吗？

🎤 面试官

JDK 已经有 `Hashtable` 和 `Collections.synchronizedMap` 了，为什么还要单独造一个 `ConcurrentHashMap`？

🧑‍💻 你

核心原因是**性能**——前两者都是*全表串行*，CHM 是*桶级并发*：

- `Hashtable`：每个方法上都是 `synchronized`，锁的是**整个 Hashtable 实例**。任何两个线程操作它——哪怕一个 read 一个 write、哪怕操作的是完全不同的 key——都要串行等待。在高并发场景下就是性能地狱。

- `Collections.synchronizedMap(new HashMap<>())`：内部包一个 `mutex` 对象，所有方法都 `synchronized(mutex)`——本质和 Hashtable 一样，还是**全表锁**。

- `ConcurrentHashMap`：把锁细化到*桶级别*（1.8）或*分段级别*（1.7），不同桶/段上的操作可以并发；**get 甚至完全无锁**（volatile 读）。所以在多线程场景下吞吐量能比 Hashtable 高一个数量级。

追问 为什么 `Hashtable` 现在被认为「事实上已废弃」？

Java 集合规范演进的锅：`Hashtable` 是 JDK 1.0 就有的老类，继承自 `Dictionary`（这个抽象类本身已废弃），API 命名和设计都不符合后来的 `Map` 规范；性能又被 CHM 全面碾压。所以官方文档明确推荐「新代码用 `ConcurrentHashMap` 或 `HashMap`，不要用 `Hashtable`」，但为了兼容性没有加 `@Deprecated`。

## 面试场景 2：JDK 1.7 CHM 的结构是什么样的？（★核心）

🎤 面试官

说说 JDK 1.7 里 `ConcurrentHashMap` 的内部结构，以及它为什么能支持并发。

🧑‍💻 你

JDK 1.7 用的是**分段锁（Segment Locking）**设计——把大 Map 切成 N 个小 Map，每个小 Map 一把锁。结构是*两层数组*：

```
ConcurrentHashMap
└── Segment[] segments;           // 第一层：默认 16 个 Segment
├── Segment[0]  extends ReentrantLock
│     └── HashEntry[] table;   // 第二层：每段一个数组
│           ├── HashEntry -> HashEntry -> ...  // 链表
│           └── ...
├── Segment[1]  extends ReentrantLock
│     └── HashEntry[] table;
├── ...
└── Segment[15] extends ReentrantLock
└── HashEntry[] table;
```

关键点：

- `Segment` 本身**继承 `ReentrantLock`**——它既是一个「小 Map」又是一把锁。

- 默认 `concurrencyLevel = 16`，即 16 个 Segment，理论上支持**16 个线程同时写**不同段。

- `HashEntry` 里的 `value` 和 `next` 都是 `volatile`，保证读的可见性 → get 不用加锁。

- 定位过程**两次 hash**：先根据 hash 高位定位到哪个 Segment，再根据 hash 低位定位到 Segment 内的哪个桶。

追问 JDK 1.7 CHM 的默认并发度 `concurrencyLevel` 是多少？如果我传 100 进去会怎样？

默认 **16**。构造器传入的 `concurrencyLevel` 会被**向上取整到 2 的幂**（为了让 hash 定位可以用位运算），传 100 会变成 **128**。这个值一旦初始化就**不能修改**——所以 1.7 的并发度是硬上限，这也是 1.8 要重做的原因之一。

## 面试场景 3：JDK 1.7 CHM 的 put/get 流程是怎么走的？

🧑‍💻 你

**put(k, v)** 流程：

1. 计算 `hash(k)`，用*高位*定位到 `Segment[i]`。

2. 如果 `Segment[i]` 还没初始化，用 CAS 懒加载（1.7 只在构造时初始化 `segments[0]`，其他段用到才初始化）。

3. 调用 `Segment.put()`：**`tryLock()` 尝试获取当前 Segment 的锁**，失败则自旋一定次数（`MAX_SCAN_RETRIES`）再阻塞。

4. 获得锁后：用 hash *低位*定位到 Segment 内的桶下标，遍历链表，找到 key 则覆盖 value，找不到则**头插法**插入新 `HashEntry`。

5. 如果 Segment 内元素数量超过阈值，触发 **Segment 内部 rehash 扩容**（不影响其他 Segment）。

6. 释放锁。

**get(k)** 流程：

1. hash 高位定位 Segment，低位定位桶。

2. 沿链表遍历（`value` 和 `next` 是 `volatile`，保证可见性）。

3. **全程不加锁**——这是 CHM 高性能的关键：读远比写多，读无锁能让整体吞吐上一个数量级。

追问 1.7 里 `tryLock` 自旋 `MAX_SCAN_RETRIES` 次的意义是什么？

避免**无必要的线程阻塞/唤醒开销**。锁竞争如果只是短暂的（比如另一个线程刚 put 完马上就要释放），自旋几次就能拿到——比 park/unpark 系统调用便宜得多。单核 CPU 上自旋 1 次，多核 CPU 上自旋 64 次（`Runtime.availableProcessors() > 1 ? 64 : 1`），超过还没拿到就走 `lock()` 进 AQS 队列阻塞。这个思路后来演化成 JDK 6+ synchronized 的「自适应自旋」。

## 面试场景 4：JDK 1.8 CHM 的结构是什么样的？（★核心）

🎤 面试官

JDK 1.8 的 `ConcurrentHashMap` 做了大改，说说它的结构和之前有什么不同。

🧑‍💻 你

1.8 彻底**抛弃了 Segment 分段锁**，向 `HashMap` 的结构对齐：

```
ConcurrentHashMap
└── Node<K,V>[] table;      // 单层数组，和 HashMap 一样
├── Node -> Node -> ...   // 桶为链表（长度 < 8）
├── TreeBin -> RBTree     // 桶为红黑树（长度 >= 8 且 table 长度 >= 64）
├── ForwardingNode        // 桶正在扩容，hash = MOVED (-1)
└── ...
```

关键变化：

- **结构和 HashMap 完全一致**：`Node[]` + 链表 / 红黑树。链表长度 ≥ 8 且 table 长度 ≥ 64 时树化，红黑树节点降到 6 时退化回链表。

- **锁粒度细化到桶头节点**：`synchronized(table[i])`——不同桶之间完全并发，理论并发度 ≈ 桶数。

- **大量使用 CAS**：桶为空时直接 CAS 写入（无锁）、`initTable` 用 CAS 争抢初始化权、`size` 计数用 `CounterCell` 分片 CAS。

- 引入几个特殊节点：`TreeBin`（红黑树的桶头，hash = -2）、`ForwardingNode`（扩容中的桶头，hash = -1 = MOVED），用*负 hash* 区分特殊节点。

- `sizeCtl` 一个字段身兼多职：`-1` = 初始化中；`-N` = N-1 个线程正在扩容；`0` = 未初始化；正数 = 下次扩容阈值。

## 面试场景 5：JDK 1.8 CHM 的 put 流程详细说说

🧑‍💻 你

1.8 的 `putVal` 是一个 **for (;;) 自旋循环**，每次循环里判断桶的四种状态：

```
final V putVal(K key, V value, boolean onlyIfAbsent) {
if (key == null || value == null) throw new NullPointerException();
int hash = spread(key.hashCode());
int binCount = 0;
for (Node<K,V>[] tab = table;;) {
Node<K,V> f; int n, i, fh;
// ① table 为空 → 初始化
if (tab == null || (n = tab.length) == 0)
tab = initTable();
// ② 桶为空 → CAS 直接放入（无锁！）
else if ((f = tabAt(tab, i = (n - 1) & hash)) == null) {
if (casTabAt(tab, i, null, new Node<>(hash, key, value, null)))
break;
}
// ③ 桶头 hash == MOVED(-1) → 帮助扩容
else if ((fh = f.hash) == MOVED)
tab = helpTransfer(tab, f);
// ④ 桶非空 → synchronized 锁桶头
else {
V oldVal = null;
synchronized (f) {
if (tabAt(tab, i) == f) {   // 双重检查
if (fh >= 0) {          // 链表
// ... 遍历链表，找到覆盖，找不到尾插
} else if (f instanceof TreeBin) {   // 红黑树
// ... putTreeVal
}
}
}
if (binCount >= TREEIFY_THRESHOLD)
treeifyBin(tab, i);
break;
}
}
addCount(1L, binCount);   // 计数（分片 CAS）
return null;
}
```

四种情况的核心思想：

- **桶为空 → CAS 无锁**，成功就走人；失败说明有别的线程刚放了值，自旋重来。

- **正在扩容 → 帮忙搬**（`helpTransfer`），扩容不是「阻塞其他线程」而是「拉大家一起干」。

- **桶非空 → synchronized 锁桶头**，只锁这一个桶，其他桶不受影响。

- **链表 ≥ 8 → 树化**（前提 table 长度 ≥ 64，否则先扩容）。

追问 CHM 1.8 帮助扩容（helpTransfer）的机制是什么？

**多线程分段迁移**。触发扩容的线程（通常是超过阈值的 `putVal`）会调 `transfer()`，其他线程 `put` 时如果发现桶头是 `ForwardingNode`（hash = MOVED = -1），就调 `helpTransfer` 加入扩容大军。`sizeCtl` 用高 16 位记录扩容戳（防止不同代的扩容混淆）、低 16 位记录参与线程数（每来一个线程 +1，完事 -1）。每个线程分到一个 `stride` 大小的桶区间去搬数据。这就是「你要写数据？先帮我把数据搬完再说」——把扩容变成协作而不是阻塞。

## 面试场景 6：JDK 1.7 vs 1.8 CHM 全对比（★核心）

维度JDK 1.7JDK 1.8

数据结构Segment[] + HashEntry[] + 链表（两层数组）Node[] + 链表/红黑树（单层数组）
锁粒度**Segment 级**（一段桶一把锁）**桶头节点级**（一个桶一把锁）
锁类型ReentrantLock（Segment 直接继承）synchronized + CAS
并发度固定 = Segment 数（默认 16，构造后不可变）动态 ≈ 桶数（可随扩容增长）
hash 冲突只有链表（头插法）链表 + 红黑树（尾插法，长度 ≥ 8 树化）
get 是否加锁不加锁（volatile 读）不加锁（volatile 读 + CAS）
扩容单 Segment 独立扩容，触发线程独扛整表扩容，多线程协作 `helpTransfer`
size 统计两次不加锁求和，不一致就整表加锁重算baseCount + CounterCell[] 分片计数（类 LongAdder）
初始化构造时初始化 `segments[0]`（提供模板）完全懒加载，首次 put 时 CAS 争抢
定位两次 hash：先段后桶一次 hash：直接定位桶

一句话总结演进思路：**从「粗粒度锁 + 固定并发度」演进到「细粒度锁 + 动态并发度 + 多线程协作」**，性能和内存效率都显著提升。

## 面试场景 7：CHM 1.8 为什么用 `synchronized` 而不是继续用 `ReentrantLock`？

🎤 面试官

ReentrantLock 明明功能更丰富（可中断、公平锁、多条件变量），1.8 为什么反而退回 synchronized？

🧑‍💻 你

这是 Doug Lea 深思熟虑后的选择，主要四个原因：

1. **JDK 6+ synchronized 性能已经追平甚至反超 ReentrantLock**。JVM 引入了*偏向锁 → 轻量级锁 → 重量级锁* 的锁升级机制，以及*自适应自旋*——在竞争不激烈时几乎零开销。CHM 1.8 锁的是桶头，竞争本来就分散，绝大多数时候都在偏向/轻量级阶段，synchronized 完胜。

2. **synchronized 是 JVM 内建的，更省内存**。ReentrantLock 需要在每个 Segment 里挂一个 AQS 队列 + 状态字段（Segment 直接继承 ReentrantLock，每个段都自带一整套 AQS 开销）。1.8 桶数动辄成千上万，如果每个桶都挂一个 Lock 对象，光锁对象就要吃几十 MB。用 synchronized 直接锁桶头节点，*零额外对象*。

3. **减少一次继承层次**。1.7 里 `Segment extends ReentrantLock`，1.8 完全不需要这层继承——Node 就是纯数据节点，锁直接是 `synchronized(node)`。Doug Lea 自己在 comment 里说这是「减少内存和继承开销」。

4. **GC 友好、异常安全**。synchronized 的锁释放由 JVM 保证（就算方法抛异常也会自动释放），ReentrantLock 必须手动 `try-finally`——CHM 内部代码复杂，用 synchronized 更不容易漏 unlock。

追问 那 ReentrantLock 是不是就没用了？

不是。ReentrantLock 有 synchronized 做不到的能力：**可中断加锁**（`lockInterruptibly()`）、**可超时**（`tryLock(timeout)`）、**公平锁**、**绑定多个 Condition**（`newCondition()`）——这些在 `BlockingQueue`、线程池、限流器等复杂场景里必不可少。*选锁的原则：能用 synchronized 就用 synchronized，需要高级特性再上 ReentrantLock*。

## 面试场景 8：CHM 的 `size()` 是精确值吗？（★核心）

🎤 面试官

并发场景下 `chm.size()` 返回的数字准吗？如果我要精确统计怎么办？

🧑‍💻 你

**不精确，只是一个「弱一致的近似值」**。1.8 用 **baseCount + CounterCell[]** 分片计数——这个思想和 `LongAdder` 一模一样：

- 无竞争时，直接 CAS 更新 `baseCount`（一个 volatile long）。

- CAS 竞争失败时，说明有热点，就把计数分散到 `CounterCell[]` 数组的不同槽位——每个线程按自己的 `ThreadLocalRandom.probe` 映射到一个 Cell，不同线程操作不同 Cell，几乎无竞争。

- `size()` = `baseCount + Σ counterCells[i].value`。

但求和是**无锁遍历**——第 0 个 Cell 求和完到第 5 个 Cell 时，可能又有线程写第 0 个 Cell，那次写就没被算进去。所以是*近似值*。

如果业务真的需要精确统计，只能：

1. 业务上避免精确 size 需求（99% 的场景只需近似值：判断「大概多少」「有没有超过某阈值」）。

2. 非要精确就在业务层加读写锁——但这就把 CHM 的并发优势全废了，不如换回 `Collections.synchronizedMap`。

3. 用 `mappingCount()`（返回 `long`，避免超过 `Integer.MAX_VALUE` 溢出），但仍然是近似值。

追问 `LongAdder` 为什么比 `AtomicLong` 快？CHM 的 `CounterCell` 是不是同一思想？

完全同一思想。`AtomicLong` 是*单点计数*——所有线程都 CAS 同一个 `value`，高并发下 CAS 失败率飙升，大量线程在自旋，甚至比锁还慢。`LongAdder` 是*分片计数*——把总数拆到 `base + Cell[]`，每个线程去写自己对应的 Cell，冲突概率大幅降低；读的时候把所有 Cell 求和。用「空间（多个 Cell）换时间（无 CAS 竞争）」。CHM 的 `CounterCell` 就是 LongAdder 的*私有翻版*（Doug Lea 是同一个作者，思路直接复用），甚至 `@sun.misc.Contended`（避免伪共享）都一样用了。

追问 CHM 的 `size()` 不精确，怎么办？

设计上就**不要依赖精确 size**。`mappingCount()` 也是近似值，从 API 命名上 Doug Lea 就在提示你「这是映射数量（估算）」而不是「元素数量（精确）」。如果业务逻辑真的依赖精确计数（比如限流器判断「是否达到 1000 个 key」），要么在业务层用 `AtomicLong` 单独维护计数（写入时加）、要么改用带精确 size 的其他并发结构（如 `ConcurrentSkipListMap`——但性能差得多）。*更好的做法是重新设计业务逻辑：不要在并发容器上做「精确阈值判断」*。

## 面试场景 9：CHM 允许 null key/value 吗？（★经典陷阱）

🎤 面试官

`HashMap` 允许 null key 和 null value，那 `ConcurrentHashMap` 呢？

🧑‍💻 你

**都不允许**！`chm.put(null, x)` 或 `chm.put(k, null)` 都会直接抛 `NullPointerException`：

```
final V putVal(K key, V value, boolean onlyIfAbsent) {
if (key == null || value == null) throw new NullPointerException();   // ← 第一行
...
}
```

这不是「忘了实现」，而是**有意为之**——因为并发场景下 null 会带来*无法弥补的二义性*：

- 假设 CHM 允许 null value，`chm.get(k)` 返回 null 时，你无法判断是「key 不存在」还是「key 存在但 value 是 null」。

- 单线程 HashMap 里你可以再调 `containsKey(k)` 补一刀区分——但并发场景下**两次调用之间可能有其他线程 `put/remove`**，第一次 get 是 null（key 不存在），第二次 containsKey 是 true（因为中间有线程 put 了），你还是无法判断真实情况。

- 要保证「get + containsKey」原子性，只能加锁——那 CHM 的无锁 get 优势就毁了。

Doug Lea 邮件里的原话：*「Maps and sets allowing null triggers all kinds of problems... they invite errors that can be very difficult to trace.」* 干脆从设计上禁止，把问题在 API 层就摁死。

追问 举一个「并发下 get null 二义性」的具体例子。

假设 CHM 允许 null，线程 A 调 `chm.get("uid_10086")` 返回 null，A 想判断到底是「用户不存在」还是「用户存在但值是 null」，于是准备调 `chm.containsKey("uid_10086")`。但在这两次调用**中间的纳秒级窗口**里，线程 B 调了 `chm.put("uid_10086", null)`——现在 A 的 containsKey 返回 true，A 就以为「原本就存在只是值为 null」，但实际是先前根本没有、被 B 刚放进去的。*不加锁的话，get 的时刻和 containsKey 的时刻是两个独立事件*，中间状态对调用方不可见。反过来 put(k, null) → 另一线程 get → 又 put(k, v) 也一样有二义性。禁掉 null 是最简单最正确的解法。

陷阱 从 `HashMap` 迁移到 `ConcurrentHashMap` 时，如果之前代码里存过 null value（比如缓存「查询过但结果为空」的标记），一切换直接 NPE 崩溃。*迁移前先全局搜 `.put(` 和 `.get(`，把可能存 null 的地方改成显式哨兵值*（如 `Optional.empty()`、或自定义 `NULL_MARKER` 常量）。

## 面试场景 10：CHM 的迭代器是 fail-fast 还是 fail-safe？

🧑‍💻 你

**fail-safe（弱一致性迭代器）**。和 `HashMap`/`ArrayList` 的 fail-fast 完全相反：

- 遍历 CHM 时，其他线程 `put`/`remove` **不会抛 `ConcurrentModificationException`**。

- 但迭代器反映的是**弱一致视图**：迭代器创建时会「记住」当时的 table 引用，遍历过程中的修改可能被看到、也可能看不到（例如遍历到桶 5 时，桶 3 被 put 的新元素就看不到；桶 8 被 put 的新元素可能看到）。

- 不保证遍历*顺序*、不保证元素*数量*、不保证包含遍历*过程中的所有修改*。

设计上：**并发容器不可能既高性能又保证 fail-fast**——fail-fast 需要维护 `modCount` 并在每次 next() 时比对，这本身就是并发写点。CHM 选择放弃 fail-fast，换取更高的并发吞吐；调用方需要自己接受「遍历结果只是一个快照近似」。

追问 fail-fast 和 fail-safe 的本质区别是什么？

**fail-fast**（如 HashMap、ArrayList 的 Iterator）：迭代过程中检测到结构性修改就*立刻抛 CME*，让你早发现 bug。实现方式是 `modCount` 计数器 + `expectedModCount` 快照，每次 next() 比对不一致就抛。**fail-safe**（如 CHM、CopyOnWriteArrayList 的 Iterator）：迭代过程中*不抛异常*，通过遍历数组快照 / 特殊数据结构容忍并发修改。两者取舍不同：fail-fast 优先*正确性提示*（帮你发现并发误用），fail-safe 优先*可用性*（并发容器就是要允许并发修改）。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：CHM vs Hashtable vs HashMap 并发写性能对比

```
import java.util.*;
import java.util.concurrent.*;

public class MapConcurrentBench {
static final int THREADS = 16;
static final int PUTS_PER_THREAD = 100_000;

public static void main(String[] args) throws Exception {
bench("ConcurrentHashMap", new ConcurrentHashMap<>());
bench("Hashtable",         new Hashtable<>());
bench("SynchronizedMap",   Collections.synchronizedMap(new HashMap<>()));
// HashMap 不加锁并发写 → 数据丢失甚至死循环，别在生产验证
}

static void bench(String name, Map<Integer, Integer> map) throws Exception {
ExecutorService pool = Executors.newFixedThreadPool(THREADS);
long t0 = System.nanoTime();
CountDownLatch done = new CountDownLatch(THREADS);
for (int t = 0; t < THREADS; t++) {
final int tid = t;
pool.submit(() -> {
for (int i = 0; i < PUTS_PER_THREAD; i++) {
map.put(tid * PUTS_PER_THREAD + i, i);
}
done.countDown();
});
}
done.await();
long ms = (System.nanoTime() - t0) / 1_000_000;
pool.shutdown();
System.out.printf("%-22s  %,d ms  size=%d%n", name, ms, map.size());
}
}
// 典型输出（16 线程 * 10 万次 put）：
// ConcurrentHashMap       ~ 180 ms
// Hashtable               ~ 900 ms   ← 全表锁，串行
// SynchronizedMap         ~ 950 ms   ← 同上
```

### 验证 2：CHM 不允许 null key/value

```
import java.util.concurrent.ConcurrentHashMap;

public class ChmNullTest {
public static void main(String[] args) {
ConcurrentHashMap<String, String> chm = new ConcurrentHashMap<>();
try {
chm.put("k", null);         // ← NPE
} catch (NullPointerException e) {
System.out.println("put null value → NPE");
}
try {
chm.put(null, "v");         // ← NPE
} catch (NullPointerException e) {
System.out.println("put null key   → NPE");
}

// 对比：HashMap 都允许
java.util.HashMap<String, String> hm = new java.util.HashMap<>();
hm.put(null, null);
System.out.println("HashMap 允许 null: " + hm.get(null));   // null
}
}
```

### 验证 3：CHM 迭代器 fail-safe（不抛 CME）

```
import java.util.*;
import java.util.concurrent.*;

public class ChmIteratorSafe {
public static void main(String[] args) throws Exception {
// 1) CHM：并发修改不抛异常
ConcurrentHashMap<Integer, Integer> chm = new ConcurrentHashMap<>();
for (int i = 0; i < 10; i++) chm.put(i, i);
new Thread(() -> {
for (int i = 100; i < 200; i++) chm.put(i, i);
}).start();
int count = 0;
for (Map.Entry<Integer, Integer> e : chm.entrySet()) {
count++;   // 不会抛 CME
Thread.sleep(1);
}
System.out.println("CHM  遍历数量 = " + count + "（近似值，不保证等于总元素数）");

// 2) HashMap：同样场景抛 CME
HashMap<Integer, Integer> hm = new HashMap<>();
for (int i = 0; i < 10; i++) hm.put(i, i);
new Thread(() -> {
try { Thread.sleep(1); } catch (InterruptedException ignore) {}
hm.put(999, 999);   // 结构性修改
}).start();
try {
for (Map.Entry<Integer, Integer> e : hm.entrySet()) {
Thread.sleep(10);   // 给上面那个线程留时间
}
} catch (ConcurrentModificationException e) {
System.out.println("HashMap 抛 ConcurrentModificationException（fail-fast）");
}
}
}
```

### 验证 4：CHM 1.8 桶级 synchronized 并发写观察

```
import java.util.concurrent.*;
import java.util.concurrent.atomic.LongAdder;

public class ChmBucketLockDemo {
public static void main(String[] args) throws Exception {
// 用固定容量避免扩容干扰；构造器建议传入 initialCapacity 减少 resize
ConcurrentHashMap<String, LongAdder> counter = new ConcurrentHashMap<>(64);
String[] hotKeys = {"apple", "banana", "cherry", "durian"};

ExecutorService pool = Executors.newFixedThreadPool(8);
CountDownLatch done = new CountDownLatch(8);
for (int t = 0; t < 8; t++) {
pool.submit(() -> {
for (int i = 0; i < 100_000; i++) {
// computeIfAbsent 是原子的：内部对桶头 synchronized
counter.computeIfAbsent(hotKeys[i % 4], k -> new LongAdder())
.increment();
}
done.countDown();
});
}
done.await();
pool.shutdown();
counter.forEach((k, v) -> System.out.println(k + " = " + v.sum()));
// 每个 key 都是 200_000（8 线程 * 10 万次 / 4 个 key）
// 说明 computeIfAbsent + LongAdder 组合可以做「并发安全的分组计数」
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 一句话说清 CHM 1.7 和 1.8 锁粒度的差别，以及带来的并发度变化。</summary>

1.7 锁 **Segment**（一段桶用一把 `ReentrantLock`），并发度 = Segment 数（默认 16，构造后不可变）；1.8 锁 **桶头节点**（`synchronized(table[i])`），并发度 ≈ 桶数（可随扩容增长）。1.8 的锁粒度更细，并发度更高。

</details>

<details>

<summary>Q2 CHM 1.8 的 putVal 遇到桶为空 vs 桶非空 vs 桶正在扩容，分别怎么处理？</summary>

桶为空 → **CAS 直接放入**（无锁）；桶非空 → **`synchronized(桶头)`** 加锁再插入/覆盖；桶头 hash == MOVED → **`helpTransfer`** 帮助扩容。table 为空时先 `initTable`（CAS 争抢初始化权）。

</details>

<details>

<summary>Q3 为什么 CHM 1.8 抛弃 ReentrantLock 改用 synchronized？</summary>

四个原因：① JDK 6+ synchronized 有锁升级和自适应自旋，性能追平；② 省内存——不需要每个 Segment 挂 AQS 队列；③ 减少继承层次（Node 不需要 extends Lock）；④ JVM 自动释放锁，异常安全。桶级竞争分散，synchronized 大部分时间在偏向/轻量级阶段。

</details>

<details>

<summary>Q4 CHM 的 size() 为什么不精确？内部实现是什么？</summary>

用 **baseCount + CounterCell[]** 分片计数（思想同 `LongAdder`）。无竞争时 CAS 更新 baseCount，有竞争则分散到 CounterCell 数组，每个线程写自己的 Cell。`size()` = baseCount + Σ counterCells——求和过程中如果有并发写，最新的写就没被算进去，所以是近似值。设计上就不希望依赖精确 size，`mappingCount()` 也一样近似。

</details>

<details>

<summary>Q5 为什么 CHM 不允许 null key/value？举个二义性的例子。</summary>

因为并发下 null 会产生**无法弥补的二义性**：`get(k)` 返回 null 时无法区分「key 不存在」还是「value 是 null」。单线程 HashMap 里可以再调 `containsKey(k)` 补一刀，但并发下两次调用之间可能有别的线程 put/remove，判断依然不可靠。要保证原子性只能加锁，那就毁了 CHM 无锁 get 的优势。Doug Lea 决定从 API 层禁止 null，让问题在编译/运行早期就暴露。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `ConcurrentHashMap` API

- Doug Lea's Concurrency Interest —— Doug Lea 官方主页，CHM 的作者

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0016：**CopyOnWriteArrayList & 读写分离 & 迭代器快照** —— 另一个 `java.util.concurrent` 里必考的读多写少并发容器，和 CHM 一起构成「并发集合两件套」。

💬 有任何疑问 —— 「CHM 1.7 的 tryLock 自旋次数怎么定的？」「helpTransfer 的 sizeCtl 高 16 位到底怎么编码？」「面试真被问过 CHM + 缓存穿透，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


