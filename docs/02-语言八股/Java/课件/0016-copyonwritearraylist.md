> Lesson 0016 · 阶段二 · 集合与并发 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 处追问

# 0016 · CopyOnWriteArrayList & 写时复制

这一课覆盖 的核心考点。`CopyOnWriteArrayList`（下文简称 **CoW**）是 *读多写少* 场景下的并发神器 —— 它的思想极简（**写的时候复制一份，改副本；读的时候永远读旧的**），却踩坑无数：*内存翻倍、弱一致性、大集合写入雪崩* 都会被面试官追着问。串起来这一课，也是理解「不可变数据 + 引用替换」这条并发思路的一个绝佳入口。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `CopyOnWriteArrayList` 的 `get()` 需要加锁吗？</summary>

不需要。读始终读 `volatile Object[] array` 这个引用指向的数组，无锁。写操作把 `array` 换成新数组，读者要么读到旧的、要么读到新的，都是完整数组，不会读到「一半新一半旧」。第 4 题细讲。

</details>

<details>

<summary>Q0.2 `CopyOnWriteArrayList` 是不是所有并发场景都比 `Collections.synchronizedList()` 好？</summary>

远远不是。CoW 每次写都要 `Arrays.copyOf` 整个数组，写多、集合大就是灾难。它只适合**读极多、写极少**（如监听器列表、配置项、白名单）。写频繁场景老老实实用 `synchronizedList` 或 `ConcurrentHashMap`。第 5、6 题细讲。

</details>

## 面试场景 1：什么是写时复制（Copy-On-Write, COW）？⭐核心

🎤 面试官

先解释一下什么叫「写时复制」？它到底解决了什么问题？

🧑‍💻 你

**写时复制**是一种「以空间换并发」的思路。核心一句话：*多个调用者共享同一份底层资源，直到有人要改，就单独复制一份、在副本上改、改完把「共享引用」指向副本*。所有旧读者手上拿到的还是旧引用，读不受任何影响。

用到 `CopyOnWriteArrayList` 里就是：

1. 底层是一个 `Object[] array`，所有读者都读这个引用。

2. 写线程进来时，先 `Arrays.copyOf` 拷一份新数组。

3. 在新数组上完成 `add` / `set` / `remove`。

4. 最后一步：`setArray(newArray)`，把 `array` 字段指向新数组。

解决的问题：**读多写少场景下，读者不用被锁挡住**。传统 `synchronized List` 的读也要抢锁，读多线程之间会互相排队；CoW 则让读操作完全无锁。

追问 COW 思想在操作系统里还有哪些经典应用？

非常多：**Linux 的 `fork()`** 就是典型的 COW —— 父子进程 fork 出来时共享物理页，任一方要写才真正复制该页；**Redis 的 `bgsave`** 也是靠 fork 的 COW 实现「持久化不阻塞写」；**文件系统快照（Btrfs、ZFS）**、**Docker 的 UnionFS 分层镜像**、**JVM 的 `String.substring()`（JDK 6 时代）** 都是同一思想。面试时能顺手举一两个，加分。

## 面试场景 2：CopyOnWriteArrayList 的核心字段有哪些？

🧑‍💻 你

翻开源码，就两个字段撑起整个类：

```
public class CopyOnWriteArrayList<E>
implements List<E>, RandomAccess, Cloneable, java.io.Serializable {

/** 保护所有变更操作的可重入锁 */
final transient ReentrantLock lock = new ReentrantLock();

/** 底层数组，volatile 保证引用可见性；只能通过 getArray/setArray 访问 */
private transient volatile Object[] array;

final Object[] getArray()          { return array; }
final void setArray(Object[] a)    { array = a; }
}
```

两个关键修饰符要吃透：

- **`volatile Object[] array`**：volatile 修饰的是*数组引用*，不是数组元素。作用是保证「写线程 `setArray` 换引用」这个动作对所有读线程立即可见 —— 读者下次读 `array` 一定拿到最新引用，不会读到旧的。

- **`final ReentrantLock lock`**：所有写操作（`add`/`set`/`remove`/`addIfAbsent`）都必须持有此锁，保证多写者互斥。*JDK 11 之前*是 `ReentrantLock`，*JDK 11 之后*改为 `synchronized (lock)`（`lock` 变成一个普通 Object），效果一样，但为 Loom 虚拟线程铺路（`synchronized` 后续会与 VT 更好配合）。

追问 为什么 `array` 要用 `transient` 修饰？

因为 `CopyOnWriteArrayList` 自己实现了 `writeObject` / `readObject`，序列化时只把元素一个个写出，读回来时再重建数组 —— 不依赖默认字段序列化。`transient` 只是告诉 *默认序列化机制*「别处理这个字段」，把控制权交给自定义方法。这是 JDK 集合类的通用套路，`ArrayList`、`HashMap` 的核心数组都是 `transient`。

## 面试场景 3：写操作 add / set / remove 是怎么工作的？

🎤 面试官

把 `add(E)` 的源码过一遍，讲清每一步在做什么。

🧑‍💻 你

```
public boolean add(E e) {
final ReentrantLock lock = this.lock;
lock.lock();                                 // ① 拿写锁：保证多写互斥
try {
Object[] elements = getArray();          // ② 读旧数组引用
int len = elements.length;
Object[] newElements = Arrays.copyOf(    // ③ 拷贝一份长度 len+1 的新数组
elements, len + 1);
newElements[len] = e;                    // ④ 在新数组末尾放新元素
setArray(newElements);                   // ⑤ volatile 写：切换引用
return true;
} finally {
lock.unlock();                           // ⑥ 释放锁
}
}
```

五步核心动作：**加锁 → 拷贝 → 改副本 → 换引用 → 解锁**。`set(int, E)` 和 `remove(int)` 完全同一套路，唯一区别是：

- `set`：如果新旧值不同才拷贝并 `setArray`；相同则复用旧数组，但仍走一次 `setArray(elements)` 保证 happens-before 语义。

- `remove`：新数组长度为 `len - 1`，用两次 `System.arraycopy` 跳过被删元素。

关键点：**写操作对读者永远不可见「中间状态」**。读者要么看到「旧数组」（完整的旧状态），要么看到「新数组」（完整的新状态），不可能看到半新半旧。这是 CoW 一致性保证的根本。

追问 多个线程同时 `add` 会不会出问题？会发生什么？

不会出并发安全问题，`ReentrantLock` 保证互斥 —— 一个线程在拷贝时，其他写线程排队等待。但**性能会雪崩**：假设集合有 10 万元素，10 个线程并发 add，每个线程都要拷贝一次 10 万长度的数组 —— 相当于 100 万次数组拷贝 + 10 次 GC 压力。所以 CoW **不适合写并发场景**。

陷阱 千万别在循环里 `list.add(...)`！如果集合本就大，循环 N 次就是 N 次全数组拷贝，时间复杂度 O(N²)。批量插入务必用 `addAll`（内部一次拷贝到位）。

## 面试场景 4：读操作 get / iterator 为什么可以不加锁？

🧑‍💻 你

```
public E get(int index) {
return elementAt(getArray(), index);
}
static <E> E elementAt(Object[] a, int index) {
return (E) a[index];
}
```

就这么两行，一个锁都没有。安全性靠三个保证叠加：

1. **`volatile` 读**：`getArray()` 读的是 `volatile` 字段，一定看到最新引用。

2. **数组一旦发布就不会被修改**：写者拿到的是*拷贝*，永远不动原数组的内容。所以读者手上的数组内容永远稳定。

3. **引用切换是原子的**：`setArray` 只是一次引用赋值，JVM 保证 32/64 位引用写入的原子性（配合 volatile 保证可见性）。

迭代器同理：

```
public Iterator<E> iterator() {
return new COWIterator<E>(getArray(), 0);  // 创建时快照当前数组
}

static final class COWIterator<E> implements ListIterator<E> {
private final Object[] snapshot;     // final，指向创建那一刻的数组
private int cursor;
// 不实现 remove/add/set，全部抛 UnsupportedOperationException
}
```

迭代器一旦创建，就把当时的 `array` 引用「拍照」保存到 `snapshot` 字段。之后无论其他线程怎么 `add`/`remove`，都是在换 `CopyOnWriteArrayList.array` 字段，*迭代器的 `snapshot` 不受任何影响*。所以遍历过程绝对不会抛 `ConcurrentModificationException`。

追问 volatile 具体保护的是什么？如果去掉 volatile 会怎样？

volatile 保护 **array 引用的可见性**（不是数组元素的可见性）。如果去掉：写线程 `setArray(newArray)` 把引用换成新数组后，其他 CPU 核心的读线程可能在*相当长的时间内*仍从自己的缓存里读到旧引用 —— 这些读者永远看不到新数据。加了 volatile，写入会立即刷新到主存，读取会强制从主存拉取，可见性得到保证。**volatile 在这里的作用比互斥锁小得多，只做「换引用」的可见性 —— 恰恰是 CoW 只用它就够的核心原因**。

## 面试场景 5：和 SynchronizedList / Vector 有什么区别？⭐对比表

维度
`CopyOnWriteArrayList`
`Collections.synchronizedList` / `Vector`

锁粒度
写有锁（ReentrantLock），**读完全无锁**
读写都加同一把 `synchronized` 锁

读并发
无限并发（读读、读写都不互斥）
串行（读读也要抢锁）

写并发
互斥（多写排队），每次全数组拷贝
互斥（多写排队），原地修改

写代价
**O(n) 拷贝 + GC**，代价高
O(1) 或 O(n)（取决于操作），代价低

一致性
**弱一致性**（读可能读到旧数组）
**强一致性**（读必读最新）

迭代行为
**fail-safe**（快照，遍历不抛 CME，但看不到新写入）
**fail-fast**（外部迭代时其他线程改会抛 CME，需自己 `synchronized(list)` 包一层）

内存开销
**写时翻倍**（新旧数组并存）
常驻内存低

典型场景
监听器列表、白名单、配置
写不算多但要求强一致

追问 CoW 相比 `ConcurrentHashMap` 有什么本质不同？各自适合什么场景？

本质不同：**CoW 是「整体复制」思路，CHM 是「分桶锁 + CAS」思路**。CoW 适合*读极多、写极少、数据集小*（监听器、配置）；CHM 适合*读写都很多、数据集可能很大*（缓存、计数器、会话表）。写多的场景用 CoW 相当于放火烧仓库，CHM 才是正解。

## 面试场景 6：CopyOnWriteArrayList 适合什么场景？⭐核心

🧑‍💻 你

只有一句话：**读极多、写极少、集合本身不大**。三个条件缺一不可。举几个真实项目里的场景：

- **观察者/监听器列表**：Spring 的 `ApplicationListener` 注册列表、Servlet 3 的 `AsyncListener`、自定义事件总线的 subscriber 列表 —— 注册是启动时一次性的，运行时全是「遍历广播」。

- **不常变的白名单 / 黑名单 / IP 名单**：管理员偶尔改一次，请求路径上每次都要判断。

- **热更新的配置**：Nacos / Apollo 推下来的路由规则、限流规则，通常几秒到几分钟才变一次，业务代码上百 QPS 在读。

- **菜单 / 权限缓存**：改一次维护更新一次，用户高频访问。

**不适合**的场景：

- 写频繁：每次全数组拷贝，性能雪崩。

- 集合很大（几万以上）：单次拷贝就要几毫秒，且新旧数组内存双份。

- 需要强一致读：读可能读到旧数据，别用它做实时账本。

追问 Spring 的事件监听器为什么用 CoW？

典型的**「一次注册、多次广播」**模式。`ApplicationContext` 启动时把所有 `ApplicationListener` 注册到内部一个 `CopyOnWriteArraySet` 里；之后每次 `publishEvent` 都要遍历这个集合调回调。写操作只在启动/热部署时发生，读操作每次事件发布都会走 —— 读写比可能是 *百万比一*。用 CoW 让事件发布路径完全无锁，是极合适的选择。

## 面试场景 7：写时复制的缺点有哪些？⭐经典追问

🧑‍💻 你

四个大坑，面试官会挨个问：

1. **内存翻倍**：写入瞬间新旧数组并存，如果原数组占 100MB，写入过程要吃到 200MB。老年代 GC 会被频繁触发，甚至 OOM。

2. **GC 压力**：每次写都产生一个「刚用完就废弃」的旧数组，非常典型的*大对象直接进老年代*场景，容易触发 Full GC。

3. **弱一致性**：读者手上可能是旧数组，读到的元素是「写入前」的状态。如果业务不能容忍旧数据（如「读到自己刚写入的值」），CoW 不合适。

4. **大集合写入极慢**：写复杂度 O(n)，n 大时单次写入毫秒级；如果并发写更是排队 + 每人 O(n)。

综合起来：**CoW 是用「写的时空成本」换「读的无锁并发」**。写代价不是「有一点」，而是「非常大」。

陷阱 弱一致性还有一层：*读到的旧数组元素本身可能被后续写者「原地改」了吗？* 不会。CoW 严格遵守「只在副本上改」原则，旧数组一经发布，其数组内容永不被修改 —— 只是被 *废弃引用* 掉。所以旧读者读到的元素状态是「快照那一刻的确定值」，只是不新罢了。

## 面试场景 8：CoW 的迭代器为什么是 fail-safe？和 fail-fast 有什么区别？

🧑‍💻 你

先说定义：

- **fail-fast**：遍历过程中检测到集合被修改，立刻抛 `ConcurrentModificationException`（简称 CME）。`ArrayList` / `HashMap` 用 `modCount` 字段实现 —— 迭代器创建时记下 `modCount`，每次 `next()` 前对比，不一致就抛。

- **fail-safe**：遍历过程中集合被修改*不抛异常*，但可能看不到修改。CoW、`ConcurrentHashMap` 的迭代器都是这个语义。

CoW 的 fail-safe 是这样保证的：

```
Iterator<E> it = list.iterator();   // 拍照：snapshot 指向当前 array
list.add("X");                        // 换的是 list.array 字段
it.hasNext();                         // 读的是 it.snapshot，与 list.array 无关
it.next();                            // 永远遍历「拍照那一刻」的元素
```

好处：**遍历绝不抛 CME，多线程读极其安全**。副作用：*看不到遍历开始后新写入的元素，也看不到删除*；且迭代器**不支持 `remove/set/add`**（会抛 `UnsupportedOperationException`）—— 因为快照是 final 的，改也没意义。

追问 `ArrayList` 在多线程遍历时抛 CME 一定是「另一个线程改了」吗？

不一定，**单线程也能触发**。经典案例：`for (String s : list) { if (...) list.remove(s); }` —— 增强 for 循环内部就是迭代器，直接调 `list.remove` 而非 `iterator.remove`，一定抛 CME。正确写法是显式用迭代器：`Iterator<String> it = list.iterator(); while (it.hasNext()) { if (...) it.remove(); }`。

## 面试场景 9：CopyOnWriteArraySet 是怎么实现的？

🧑‍💻 你

它就是**装饰在 `CopyOnWriteArrayList` 外面的一层薄壳**：

```
public class CopyOnWriteArraySet<E> extends AbstractSet<E> {
private final CopyOnWriteArrayList<E> al;

public CopyOnWriteArraySet() {
al = new CopyOnWriteArrayList<E>();
}

public boolean add(E e) {
return al.addIfAbsent(e);        // ← 核心：不存在才加
}
public boolean contains(Object o)    { return al.contains(o); }
public Iterator<E> iterator()        { return al.iterator(); }
}
```

`addIfAbsent` 内部先*遍历数组*用 `equals` 判重，找到就不加，找不到才走 `add` 拷贝流程。所以：

- **add 复杂度 O(n)**（判重 O(n) + 拷贝 O(n)）—— 集合大时非常慢。

- **contains 复杂度 O(n)**（线性扫描）—— 因为底层是数组，没有 hash 结构。

所以 `CopyOnWriteArraySet` 只适合**元素数量极少（几十以内）**的场景。想要「Set 语义 + 高并发」，元素数量大就得用 `ConcurrentHashMap.newKeySet()`。

追问 那为啥 Spring 的监听器还用 `CopyOnWriteArraySet`？

因为监听器数量本来就少（一般几十个撑死），且启动时一次性注册完，运行时基本不动。*「读极多写极少 + 元素极少」* 完美命中 CoW 场景。数量再多，Spring 早就换 CHM 了。

## 面试场景 10：实际生产中你会用它吗？说个例子。

🧑‍💻 你

会用，但用得**谨慎且窄**。典型例子有三类：

1. **热更新的路由/限流规则表**：Nacos 推下来的规则集合，业务代码高频读。规则条数一般几十上百，配置更新每几分钟一次 —— 用 CoW 让业务路径 0 锁。

2. **事件订阅者列表**：自研事件总线的 `subscribers`，注册时机固定（启动或 SPI 加载），事件派发高频 —— CoW 是标配。

3. **动态开关列表**：feature toggle、灰度名单、AB 测试白名单，运营改一次，请求全在读 —— 完美命中。

不会用它做的事：

- 普通的业务集合，比如「订单列表」「用户购物车」—— 写太频繁。

- 需要 O(1) 判重的 Set —— 用 CHM.newKeySet。

- 大集合（万级以上）—— 内存和 GC 扛不住。

追问 你在项目里用 CoW 时踩过什么坑吗？

最常见两个：**①** 上线时才发现某个「配置列表」被业务代码高频写入（不小心把用户行为写进去了），瞬间 Full GC 飙升 —— 后来加了监控和 code review 规则。**②** 用 `list.iterator()` 遍历后*期望能看到并发写入*，结果 debug 半天发现是 fail-safe 快照，只能改成每次遍历前重新调 `list.iterator()`。—— 面试时把这类真实踩坑讲出来，比背 API 加分十倍。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：并发读写下 CoW 不抛 CME

```
import java.util.*;
import java.util.concurrent.*;

public class CowSafeDemo {
public static void main(String[] args) throws Exception {
List<Integer> list = new CopyOnWriteArrayList<>();
for (int i = 0; i < 100; i++) list.add(i);

// 一个线程遍历，一个线程持续 add
Thread reader = new Thread(() -> {
for (int i = 0; i < 10; i++) {
for (Integer x : list) {   // 增强 for = iterator()
// 不会抛 CME
}
}
System.out.println("reader done, size=" + list.size());
});
Thread writer = new Thread(() -> {
for (int i = 100; i < 200; i++) list.add(i);
});
reader.start(); writer.start();
reader.join(); writer.join();
}
}
// 换成 new ArrayList<>() 试试 —— 大概率抛 ConcurrentModificationException
```

### 验证 2：迭代器的快照语义

```
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;

public class CowIteratorSnapshot {
public static void main(String[] args) {
List<String> list = new CopyOnWriteArrayList<>(
Arrays.asList("A", "B", "C"));

Iterator<String> it = list.iterator();  // 快照：[A, B, C]

list.add("D");                          // 换掉 list.array
list.remove("A");                       // 又换一次
System.out.println("当前 list: " + list);        // [B, C, D]

while (it.hasNext()) {
System.out.print(it.next() + " ");  // 输出：A B C
}
// 迭代器手上的 snapshot 仍是最初的 [A, B, C]，没变
}
}
```

### 验证 3：写操作性能雪崩（大集合并发写）

```
import java.util.*;
import java.util.concurrent.*;

public class CowWriteBenchmark {
public static void main(String[] args) throws Exception {
int size = 100_000;
List<Integer> cow  = new CopyOnWriteArrayList<>();
List<Integer> sync = Collections.synchronizedList(new ArrayList<>());
for (int i = 0; i < size; i++) { cow.add(i); sync.add(i); }

long t1 = System.currentTimeMillis();
for (int i = 0; i < 1000; i++) cow.add(i);
System.out.println("CoW  1000 次 add: " + (System.currentTimeMillis() - t1) + " ms");

long t2 = System.currentTimeMillis();
for (int i = 0; i < 1000; i++) sync.add(i);
System.out.println("Sync 1000 次 add: " + (System.currentTimeMillis() - t2) + " ms");
}
}
// 典型输出：
//   CoW  1000 次 add: 800 ms   ← 每次都拷 10 万元素
//   Sync 1000 次 add: 2 ms     ← 原地追加
// 差距可达 400 倍
```

### 验证 4：迭代器不支持修改

```
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;

public class CowIteratorReadonly {
public static void main(String[] args) {
List<String> list = new CopyOnWriteArrayList<>(
Arrays.asList("A", "B", "C"));
Iterator<String> it = list.iterator();
it.next();
it.remove();  // 抛 UnsupportedOperationException
// 想删除只能用 list.remove("A")，走完整的写时复制流程
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 一句话解释 CopyOnWriteArrayList 的核心思想。</summary>

写操作先复制底层数组、在副本上修改、再用 volatile 写把 `array` 引用指向副本；读操作全程无锁，直接读当前 `array` 引用指向的数组。

</details>

<details>

<summary>Q2 `volatile Object[] array` 里 `volatile` 到底保护了什么？</summary>

保护数组引用的**可见性**（不是数组元素的可见性）。让写者 `setArray` 换的新引用能立即被所有读线程看到，避免读者一直读到 CPU 缓存里的旧引用。

</details>

<details>

<summary>Q3 为什么 CoW 迭代器不会抛 `ConcurrentModificationException`？</summary>

迭代器创建时把当时的 `array` 引用拍照到自己的 `snapshot` final 字段。之后集合的写操作换的是 `list.array`，迭代器的 `snapshot` 完全不受影响 —— 遍历的是「快照那一刻的数组」，所以不会有「集合变了」的检测。副作用是看不到新写入。

</details>

<details>

<summary>Q4 CoW 相比 `synchronizedList`、`ConcurrentHashMap` 各自适合什么场景？</summary>

CoW：读极多、写极少、集合小（监听器、配置、白名单）。synchronizedList：写不算少但要求强一致、集合较小。CHM：读写都多、可能大数据集（缓存、计数、会话表）。

</details>

<details>

<summary>Q5 CoW 的四大缺点是什么？为什么大集合、写频繁场景不能用？</summary>

① 内存翻倍（新旧数组并存）；② GC 压力（旧数组频繁进老年代）；③ 弱一致性（读可能读到旧数据）；④ 大集合写入 O(n) 拷贝，性能雪崩。写频繁场景意味着高频拷贝 + 高频 GC，直接把 JVM 拖垮。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `CopyOnWriteArrayList` API

- JDK 21 · `CopyOnWriteArraySet` API

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0017：**BlockingQueue 全家桶（ArrayBQ / LinkedBQ / SynchronousQ / DelayQ / PriorityBQ）** —— 生产者-消费者模型的核心组件，也是线程池实现原理的关键拼图。

💬 有任何疑问 —— 「CoW 换成 JDK 11 后的 synchronized 是不是性能更差？」「Spring 的 ApplicationListener 源码里 CoW 具体在哪个类？」「弱一致性会不会导致监听器丢事件？」—— 直接问我。我是你的老师，也是你的追问陪练。


