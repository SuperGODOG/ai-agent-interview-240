> Lesson 0014 · 阶段二 · Java 集合 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0014 · LinkedHashMap 源码 & 手撕 LRU 实现

这一课覆盖的所有考点。`LinkedHashMap` 是 `HashMap` 的亲兄弟 —— **底层就是 HashMap，只是在每个 Entry 上加了 `before`/`after` 两个指针，串成一条独立于桶数组的双向链表**。

面试官为什么爱考它？因为它是**「手撕 LRU 缓存」**这道经典题最优雅的答案 —— *不用手写双向链表，不用手动维护指针，5 行代码搞定*。搞懂它，你既能过面试题，又能理解 Redis / Caffeine / Guava Cache 背后的驱逐策略。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `LinkedHashMap` 相比 `HashMap` 多了什么？</summary>

多了两样东西：**Entry 节点上的 `before`/`after` 指针**（把所有节点串成一条独立于桶数组的双向链表）+ **`head`/`tail` 头尾指针**（用于 O(1) 追加、迭代）。仅此而已，其他所有逻辑（hash、扩容、树化）都复用 HashMap 父类。

</details>

<details>

<summary>Q0.2 用 `LinkedHashMap` 实现 LRU 需要传什么参数？重写什么方法？</summary>

构造器传 `accessOrder=true`（三参构造：`super(cap, 0.75f, true)`），并重写 `removeEldestEntry(Map.Entry)` 让它在 `size() > 容量` 时返回 `true`。就这两步。第 5 题会展开完整代码。

</details>

## 面试场景 1：LinkedHashMap 和 HashMap 是什么关系？

🎤 面试官

你了解 `LinkedHashMap` 吗？它和 `HashMap` 有什么关系？

🧑‍💻 你

`LinkedHashMap` **直接继承 `HashMap`**，几乎所有能力（put、get、扩容、树化）都直接复用父类，唯一的加法是：**在每个 Entry 上多挂两个指针 `before`/`after`，把所有节点串成一条独立于桶数组的双向链表**。

它的 Entry 定义就是这么简单：

```
static class Entry<K,V> extends HashMap.Node<K,V> {
Entry<K,V> before, after;  // 双向链表指针
Entry(int hash, K key, V value, Node<K,V> next) {
super(hash, key, value, next);   // next 是 HashMap 桶内单链表指针
}
}
```

关键区别是：**HashMap 内的 `next` 是桶内冲突链的指针，而 `before`/`after` 是横跨所有桶的全局顺序链**。同一个节点同时挂在两条链上。

追问 迭代 `LinkedHashMap` 和 `HashMap` 有什么效率差异？

差别在于「遍历路径」。`HashMap` 迭代要扫整个桶数组找非空槽，效率跟 **容量（capacity）** 成正比 —— 即使只放了 10 个元素，容量 1024 时也要扫 1024 个槽。`LinkedHashMap` 直接沿 `head → tail` 走双向链表，效率跟 **元素个数（size）** 成正比。所以稀疏 Map 场景下 `LinkedHashMap` 迭代反而更快。

追问 为什么 `HashMap` 里的 `TreeNode` 继承的是 `LinkedHashMap.Entry` 而不是 `Node`？

这是 JDK 源码里的一个巧妙设计。`TreeNode extends LinkedHashMap.Entry extends HashMap.Node`。原因是：一旦 `HashMap` 里插入的是 `LinkedHashMap`，桶内冲突链树化后的 `TreeNode` 也必须能挂进那条双向链表，所以必须带 `before`/`after` 字段。作者取舍：普通 HashMap 场景树化概率不高，多这两个字段的开销可以接受，换来的是继承关系统一。

## 面试场景 2：LinkedHashMap 的两种顺序模式（★核心）

🎤 面试官

`LinkedHashMap` 有几种迭代顺序？分别怎么触发？

🧑‍💻 你

两种，由构造器的 `accessOrder` 布尔字段决定：

- **`accessOrder = false`（默认，插入顺序）**：只在 *put 新节点* 时把节点挂到 `tail`，之后不动。迭代顺序 = 插入顺序。

- **`accessOrder = true`（访问顺序）**：每次 `get` 或 `put`（更新旧值）都会触发 `afterNodeAccess`，把该节点**从链表中断开并挂到 `tail`**。结果就是：*最少访问的节点自然沉到 `head`，最近访问的在 `tail`* —— 这就是 LRU 需要的顺序。

只有三参构造器能开启访问顺序模式：

```
public LinkedHashMap(int initialCapacity, float loadFactor, boolean accessOrder) {
super(initialCapacity, loadFactor);
this.accessOrder = accessOrder;
}
```

陷阱 无参构造 `new LinkedHashMap<>()` 默认是 **插入顺序（`accessOrder=false`）**，不是访问顺序。想做 LRU 必须显式传 `true`。这是笔试题里最容易踩的坑之一。

追问 `accessOrder=true` 时，`put` 一个已存在的 key 会不会挪到链尾？

会。`HashMap.putVal` 更新旧值后会调用 `afterNodeAccess`（HashMap 里的实现是空的，LinkedHashMap 重写了），把节点挪到 `tail`。所以「更新即访问」，这也符合 LRU 语义 —— *写入相当于最近使用*。

追问 `accessOrder=true` 时，`for-each` 遍历过程中调 `get` 会不会抛 `ConcurrentModificationException`？

不会。`get` 触发的 `afterNodeAccess` 只调整了链表的 `before`/`after` 指针 —— **没有改动 `modCount`**。而 CME 的判定条件是 `modCount != expectedModCount`。所以 get 期间的链表挪动是「静默」的，不影响迭代器的 fail-fast 检测。但要注意：*迭代顺序会跟着变*，可能出现你没想到的顺序（比如刚刚 get 过的元素跑到最后）。

## 面试场景 3：LinkedHashMap 如何做到「插入顺序遍历」？

🧑‍💻 你

核心是**重写 `newNode` 钩子**。HashMap 的 `putVal` 在需要新建节点时会调 `newNode(hash, key, value, next)`，父类的实现只是 `return new Node(...)`。LinkedHashMap 重写为：

```
Node<K,V> newNode(int hash, K key, V value, Node<K,V> e) {
LinkedHashMap.Entry<K,V> p =
new LinkedHashMap.Entry<>(hash, key, value, e);
linkNodeLast(p);   // ★ 关键：立刻挂到双向链表尾部
return p;
}

private void linkNodeLast(LinkedHashMap.Entry<K,V> p) {
LinkedHashMap.Entry<K,V> last = tail;
tail = p;
if (last == null)
head = p;              // 空链表：head/tail 都指向新节点
else {
p.before = last;       // 非空链表：串到原 tail 后面
last.after = p;
}
}
```

新节点一诞生就被追加到 `tail`，插入顺序被链表天然记录下来。

迭代时也不走桶数组，直接沿链表走：

```
// LinkedHashIterator.nextNode() 简化版
final LinkedHashMap.Entry<K, V> nextNode() {
LinkedHashMap.Entry<K, V> e = next;
if (modCount != expectedModCount)
throw new ConcurrentModificationException();
if (e == null) throw new NoSuchElementException();
current = e;
next = e.after;   // ← 沿 after 指针直接跳到下一个
return e;
}
```

对比 HashMap 要「扫桶数组找下一个非空槽 + 遍历桶内单链表」两层循环，LinkedHashMap 的迭代真的就是**一条链走到底**，简洁高效。

## 面试场景 4：LinkedHashMap 重写了 HashMap 的哪些钩子方法？

🎤 面试官

`LinkedHashMap` 几乎什么都没重写，为什么能维护链表？

🧑‍💻 你

因为 HashMap 在关键路径上**预留了几个「空实现」的钩子方法**（Template Method 模式），LinkedHashMap 只需要重写这几个钩子，就能透明地扩展行为。核心四个：

钩子方法HashMap 何时调用LinkedHashMap 做什么

`newNode``putVal` 里创建新节点创建 `Entry` 后调 `linkNodeLast` 挂到链尾
`afterNodeAccess(e)``get` 命中、`putVal` 更新旧值若 `accessOrder=true`，把 e 移到链尾
`afterNodeInsertion(evict)``putVal` 结束时检查 `removeEldestEntry(head)`，为 true 就删 head
`afterNodeRemoval(e)``removeNode` 删除节点后从双向链表上摘掉 e（前驱指向后继，后继指向前驱）

父类的这四个方法在 HashMap 里都是*空方法体*，专门留给 LinkedHashMap 覆盖。这是一次教科书级的**模板方法模式**应用 —— HashMap 定义骨架，子类通过钩子插入行为。

追问 `afterNodeAccess` 里怎么把节点挪到链尾？说说指针操作。

三步：**①** 让节点的前驱指向节点的后继（`p.before.after = p.after`）；**②** 让节点的后继指向节点的前驱（`p.after.before = p.before`）—— 这两步把节点从链中「摘」出来；**③** 让节点变成新 `tail`（`p.before = 原tail; 原tail.after = p; tail = p`）。所有操作都是 O(1) 的指针改写，不涉及元素移动。

## 面试场景 5：手撕 LRU 缓存 ★经典必考题

🎤 面试官

手写一个 LRU 缓存，容量满时自动淘汰最久未使用的元素。

🧑‍💻 你

用 `LinkedHashMap`，5 行核心代码：

```
public class LRUCache<K, V> extends LinkedHashMap<K, V> {
private final int capacity;

public LRUCache(int capacity) {
super(capacity, 0.75f, true);   // ★ accessOrder=true 开启访问顺序
this.capacity = capacity;
}

@Override
protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
return size() > capacity;       // ★ 超容量就淘汰 head
}
}
```

三个关键点：

1. 继承 `LinkedHashMap`，白嫖父类的双向链表能力。

2. 构造器传 `accessOrder=true`，让 `get`/`put` 自动把节点挪到链尾。

3. 重写 `removeEldestEntry`，返回 `true` 时会自动删链头（也就是最久未访问的元素）—— 这个方法在 `afterNodeInsertion` 里被调用。

然后就可以像普通 Map 一样用：

```
LRUCache<Integer, String> cache = new LRUCache<>(3);
cache.put(1, "A");
cache.put(2, "B");
cache.put(3, "C");
cache.get(1);              // 1 变最新
cache.put(4, "D");         // 容量满，淘汰 head（也就是 2）
System.out.println(cache); // {3=C, 1=A, 4=D}
```

追问 面试官说「不允许继承 LinkedHashMap，用最原始的数据结构手写」，怎么写？

标配答案是 **`HashMap` + 手写双向链表**。HashMap 保 O(1) 查找，双向链表保 O(1) 插入删除。核心操作：get 时若命中，把节点从链中断开重新挂到链尾；put 时若已存在则更新并挪尾，若不存在则新建挂尾；容量超限则删链头。所有操作 O(1)。LeetCode 146 就是这道题。

追问 面试让手写一个**线程安全**的 LRU，怎么做？

三条路：**①** 最简单：`Collections.synchronizedMap(new LRUCache<>(cap))`，全局锁性能一般。**②** 用 `ReentrantReadWriteLock`，读写分离一点，但 accessOrder 场景下 `get` 也会改链表，所以本质上还是写锁。**③** 生产级：`ConcurrentHashMap` + 手写 CAS 链表，或者直接上 **Caffeine**（分段锁 + 异步驱逐 + W-TinyLFU 算法）。

## 面试场景 6：LinkedHashMap 的 get 为什么仍然是 O(1)？

🎤 面试官

`accessOrder=true` 时每次 `get` 都要挪链表，还是 O(1) 吗？

🧑‍💻 你

还是 O(1)。原因是 `get` 只做两件事：

1. **桶定位**：走 HashMap 父类的 `getNode`，靠 hash 直接定位到桶。理想情况下（无冲突）O(1)；有冲突时链表/红黑树内 O(k) 或 O(log k)，k 是桶内元素数，通常 < 8，可视为常数。

2. **afterNodeAccess**：拿到节点后调这个钩子。它只做**指针改写** —— 断开、重挂 `tail`，全部是 O(1) 的引用赋值，不涉及节点复制或数据搬迁。

两步都是 O(1)，所以 get 整体 O(1)。**这也是为什么用 LinkedHashMap 做 LRU 是最优雅的方案 —— 时间复杂度和纯 HashMap 一样。**

追问 手写「HashMap + 双向链表」的 LRU，get 是 O(1) 的原因也一样吗？

是的。HashMap 提供 O(1) 键值查找，双向链表提供 O(1) 断链和重挂尾。*关键在于「双向」*：单向链表删除中间节点需要 O(n) 找前驱，双向链表直接通过 `node.prev` 拿到前驱，O(1) 摘除。这就是为什么 LRU 必须是双向链表，不能是单向。

## 面试场景 7：LinkedHashMap vs TreeMap 顺序保证的区别

维度`LinkedHashMap``TreeMap`

底层结构HashMap + 双向链表红黑树
顺序含义插入顺序 / 访问顺序Key 的自然序 或 `Comparator`
put/get/removeO(1)O(log n)
迭代顺序沿双向链表红黑树中序遍历
Key 要求需实现 `equals` + `hashCode`需实现 `Comparable` 或传 `Comparator`
能否范围查询不能（不知道 key 大小关系）能（`subMap`、`headMap`、`tailMap`）
典型场景LRU 缓存、按插入顺序输出、Excel 表头字典序索引、范围统计、有序集合

追问 想让 Map 按**插入顺序**输出 JSON，用哪个？

`LinkedHashMap`。Jackson 序列化 `Map` 时会按迭代顺序输出字段，用 `LinkedHashMap` 能保证 JSON 字段顺序和你 put 的顺序一致。`HashMap` 顺序不定，`TreeMap` 会按 key 字典序排（比如 `{"age":..., "name":...}` 会输出成 `age` 在前）。

追问 想让 Map 按 **value 大小**排序（比如按分数倒排学生名单），用哪个？

三种做法：**①** 用 `TreeMap` 时把 key 和 value 交换过来（key = 分数），但要处理相同分数；**②** 把 `entrySet()` 拷到 `List` 里 `sort(Comparator.comparing(Map.Entry::getValue))`，再灌进 `LinkedHashMap`；**③** 用 Guava 的 `ImmutableSortedMap.copyOf(map, Ordering.natural().onResultOf(map::get))`。生产里 **②** 最常用。

## 面试场景 8：LRU 缓存击穿场景 & 生产替代方案

🎤 面试官

你说用 `LinkedHashMap` 实现 LRU 很优雅，那生产环境为什么不用它？

🧑‍💻 你

能用，但只适合**单机小容量、非高并发**的场景（比如 SQL 语句缓存、配置缓存）。生产上更主流的选择：

方案算法优点适用

`LinkedHashMap`朴素 LRU零依赖，代码 5 行小容量、单线程/低并发
Guava CacheLRU + 分段锁老牌稳定，API 好用Spring 老项目、简单缓存
**Caffeine**W-TinyLFU命中率高、异步驱逐、分段锁★现代 JVM 缓存首选
EhcacheLRU/LFU + 持久化支持磁盘、集群需要持久化或二级缓存
RedisLRU/LFU 近似分布式、持久化、多种驱逐策略★分布式缓存标配

**LinkedHashMap 版 LRU 的局限**：非线程安全、命中率一般（纯 LRU 会被扫描类流量污染）、无 TTL 过期、无 refresh、无监听 evict 事件。

追问 Caffeine 的 W-TinyLFU 相比朴素 LRU 好在哪？

朴素 LRU 有个致命弱点：**扫描污染**。假设缓存里存的是「近期热门商品」，突然来了一次全量扫描（如爬虫或定时任务），扫过一遍就把所有热点冲走了，命中率断崖式下跌。W-TinyLFU 引入了**频率维度**：用 Count-Min Sketch 记录每个 key 的访问频次，新元素想进主缓存必须*击败*要被淘汰的元素（比拼历史访问频率）。这样一次性访问的扫描流量根本进不了主区，热点得以保留。加上「W-」的 Window TinyLFU 还处理了突发流量（burst）问题。

追问 Redis 的 LRU 是「精确 LRU」吗？

不是，是**近似 LRU（approximated LRU）**。真 LRU 要维护一条全局双向链表，Redis 因内存开销和锁竞争放弃了这条路，改为**随机采样**：每次驱逐时随机取 `maxmemory-samples`（默认 5）个 key，淘汰其中最久未访问的。样本越大越接近真 LRU，但 CPU 开销也越大。Redis 4.0 起还加了 LFU 模式（`allkeys-lfu`），思想类似 W-TinyLFU。

## 面试场景 9：LinkedHashMap 是线程安全的吗？

🧑‍💻 你

不是。父类 `HashMap` 就不线程安全，`LinkedHashMap` 又多了一条双向链表要维护，多线程下更容易出问题 —— 除了 `HashMap` 那些死循环 / 数据丢失的老问题，还可能出现**双向链表指针错乱**（一个线程正在 `afterNodeAccess` 挪节点，另一个线程正在删除）。

并发场景的选择：

- **低并发**：`Collections.synchronizedMap(new LinkedHashMap<>())`，全局锁。

- **高并发**：直接换 `ConcurrentHashMap`（放弃顺序保证）或 **Caffeine**（内部用分段锁 + `ConcurrentHashMap` 存节点，异步维护 LRU 队列）。

- **历史方案**：`ConcurrentLinkedHashMap`（Google 开源库，Caffeine 前身），现在基本被 Caffeine 取代。

追问 JDK 有没有官方的「线程安全 + 保持顺序」的 Map？

没有直接对应的。`ConcurrentHashMap` 无顺序，`ConcurrentSkipListMap` 按 key 有序（skip list），但没有「插入顺序」的官方并发实现。要「线程安全的 LinkedHashMap」只能自己 `synchronizedMap` 包装，或者引 Caffeine 这样的第三方库。

## 面试场景 10：removeEldestEntry 什么时候被调用？

🎤 面试官

`removeEldestEntry` 是每次 `get` 都会调吗？

🧑‍💻 你

不是。它只在 **put / putAll 之后** 被调用，且只调一次。调用链路是：

```
HashMap.put(k, v)
└─ HashMap.putVal(...)
├─ 新建节点 → newNode  (LinkedHashMap 重写：挂到 tail)
└─ 结束前调用 afterNodeInsertion(evict=true)
└─ LinkedHashMap 重写：
if (evict && head != null && removeEldestEntry(head))
removeNode(hash(head.key), head.key, ...);
```

翻译一下：每次 put 结束，LinkedHashMap 都会拿 `head`（最老元素）问一下 `removeEldestEntry`「要不要删」，你返回 `true` 它就 `removeNode` 掉链头。默认实现永远返回 `false`，所以普通 `LinkedHashMap` 不会自动删元素；LRU 缓存重写为 `size() > capacity`，就实现了容量自动淘汰。

追问 `removeEldestEntry` 每次 put 只删一个 head，那如果我 `putAll` 一次灌了 100 个进来，容量只有 10，会怎样？

会正常淘汰到 10 个。`putAll` 内部是循环调 `putVal`，每次 put 都会触发一次 `afterNodeInsertion → removeEldestEntry` 检查。所以是「每插一个，检查一次，超容就删一个 head」，最终 size 稳定在 capacity。*但注意：中间过程会短暂到达 size = capacity + 1*。

追问 我在 `removeEldestEntry` 里除了返回 true，能不能顺便做点别的（比如写日志、发通知）？

可以，但要小心。`removeEldestEntry(Map.Entry eldest)` 会把即将被淘汰的 entry 传给你，你可以打日志、发 metrics。**不要在这里做重操作**（比如同步 IO、RPC），因为它在 put 的关键路径上，会拖慢所有写入。想做异步通知，考虑用 **Caffeine 的 `RemovalListener`**，它支持异步驱逐回调。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：插入顺序 vs 访问顺序

```
import java.util.LinkedHashMap;

public class OrderDemo {
public static void main(String[] args) {
// 插入顺序（默认）
LinkedHashMap<Integer, String> insertOrder = new LinkedHashMap<>();
insertOrder.put(1, "A");
insertOrder.put(2, "B");
insertOrder.put(3, "C");
insertOrder.get(1);                 // 访问 1，不影响顺序
System.out.println(insertOrder);    // {1=A, 2=B, 3=C}

// 访问顺序（accessOrder=true）
LinkedHashMap<Integer, String> accessOrder =
new LinkedHashMap<>(16, 0.75f, true);
accessOrder.put(1, "A");
accessOrder.put(2, "B");
accessOrder.put(3, "C");
accessOrder.get(1);                 // 访问 1，1 移到 tail
System.out.println(accessOrder);    // {2=B, 3=C, 1=A}
}
}
```

### 验证 2：手撕 LRU 缓存（完整可跑）

```
import java.util.LinkedHashMap;
import java.util.Map;

public class LRUCache<K, V> extends LinkedHashMap<K, V> {
private final int capacity;

public LRUCache(int capacity) {
super(capacity, 0.75f, true);   // accessOrder=true
this.capacity = capacity;
}

@Override
protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
return size() > capacity;
}

public static void main(String[] args) {
LRUCache<Integer, String> cache = new LRUCache<>(3);
cache.put(1, "A");
cache.put(2, "B");
cache.put(3, "C");
System.out.println(cache);    // {1=A, 2=B, 3=C}

cache.get(1);                 // 访问 1，1 变最新
System.out.println(cache);    // {2=B, 3=C, 1=A}

cache.put(4, "D");            // 容量满，淘汰 head（2）
System.out.println(cache);    // {3=C, 1=A, 4=D}

cache.put(3, "C-new");        // 更新已存在的 key，3 也算最近访问
System.out.println(cache);    // {1=A, 4=D, 3=C-new}
}
}
```

### 验证 3：不用继承，手写「HashMap + 双向链表」LRU（LeetCode 146）

```
import java.util.HashMap;

public class LRU146 {
static class Node {
int key, val;
Node prev, next;
Node(int k, int v) { key = k; val = v; }
}

private final int cap;
private final HashMap<Integer, Node> map = new HashMap<>();
private final Node head = new Node(0, 0);   // 哨兵，简化边界处理
private final Node tail = new Node(0, 0);

public LRU146(int capacity) {
this.cap = capacity;
head.next = tail;
tail.prev = head;
}

public int get(int key) {
Node n = map.get(key);
if (n == null) return -1;
moveToHead(n);
return n.val;
}

public void put(int key, int value) {
Node n = map.get(key);
if (n != null) { n.val = value; moveToHead(n); return; }
Node fresh = new Node(key, value);
map.put(key, fresh);
addToHead(fresh);
if (map.size() > cap) {
Node old = tail.prev;
removeNode(old);
map.remove(old.key);
}
}

private void addToHead(Node n) {
n.prev = head; n.next = head.next;
head.next.prev = n; head.next = n;
}
private void removeNode(Node n) {
n.prev.next = n.next; n.next.prev = n.prev;
}
private void moveToHead(Node n) { removeNode(n); addToHead(n); }
}
```

### 验证 4：观察 removeEldestEntry 的调用时机

```
import java.util.LinkedHashMap;
import java.util.Map;

public class HookDemo {
public static void main(String[] args) {
LinkedHashMap<Integer, String> m = new LinkedHashMap<>(16, 0.75f, true) {
@Override
protected boolean removeEldestEntry(Map.Entry<Integer, String> eldest) {
System.out.println("  removeEldestEntry called, head=" + eldest
+ ", size=" + size());
return size() > 2;
}
};

System.out.println("put 1"); m.put(1, "A");
System.out.println("put 2"); m.put(2, "B");
System.out.println("put 3"); m.put(3, "C");   // 触发驱逐 1
System.out.println("get 2"); m.get(2);         // get 不触发
System.out.println("put 4"); m.put(4, "D");   // 触发驱逐 3
System.out.println("final: " + m);
}
}
/* 输出：
put 1
removeEldestEntry called, head=1=A, size=1
put 2
removeEldestEntry called, head=1=A, size=2
put 3
removeEldestEntry called, head=1=A, size=3    ← 返回 true，删 1
get 2
put 4
removeEldestEntry called, head=3=C, size=3    ← 返回 true，删 3
final: {2=B, 4=D}
*/
```

观察点：**每次 put 都调 removeEldestEntry**（即使 size 还没超），**get 完全不调**。这跟第 10 题的分析一致。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话说明 `LinkedHashMap` 相比 `HashMap` 的核心增强。</summary>

在 Entry 上多了 `before`/`after` 指针，把所有节点串成一条独立于桶数组的双向链表，从而能按**插入顺序**或**访问顺序**迭代。

</details>

<details>

<summary>Q2 手撕 LRU 缓存，写出核心 3 步。</summary>

① `extends LinkedHashMap`；② 构造器传 `accessOrder=true`（`super(cap, 0.75f, true)`）；③ 重写 `removeEldestEntry`，超容返回 `true`。完整代码见验证 2。

</details>

<details>

<summary>Q3 `LinkedHashMap` 的 `get` 是 O(1) 吗？`accessOrder=true` 时呢？</summary>

都是 O(1)。`get` 走 HashMap 桶定位（O(1)），`afterNodeAccess` 只是 O(1) 的链表指针改写。*关键在于双向链表能 O(1) 摘除任意节点。*

</details>

<details>

<summary>Q4 `removeEldestEntry` 在什么时候被调用？`get` 会触发它吗？</summary>

只在 `put` / `putAll` 结束时通过 `afterNodeInsertion` 调用，**`get` 不会触发**。所以 LRU 的容量控制只在写入路径上做，读路径零开销。

</details>

<details>

<summary>Q5 生产环境为什么很少直接用 `LinkedHashMap` 做缓存？替代方案有哪些？</summary>

因为它**非线程安全**、命中率一般（易被扫描污染）、无 TTL / refresh / 异步驱逐监听。替代方案：单机首选 **Caffeine**（W-TinyLFU 算法命中率高、分段锁并发好、异步驱逐），老项目 Guava Cache，需持久化用 Ehcache，分布式用 Redis。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.util.LinkedHashMap` API —— `removeEldestEntry` 官方注释里就有 LRU 示例

- Caffeine · GitHub —— W-TinyLFU 参考实现

- LeetCode 146 · LRU 缓存 —— 手写练习题

#### 🔗 关联课件

- （上一课，理解父类是本课的前置）

- （下一课，线程安全的 Map 长啥样）

#### 🧭 下一课预告

Lesson 0015：**ConcurrentHashMap 源码 & 分段锁 → CAS + synchronized 演进** —— 面试频次同样极高的一课。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


