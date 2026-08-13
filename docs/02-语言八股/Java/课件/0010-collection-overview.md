> Lesson 0010 · 阶段二 · 集合 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0010 · 集合框架概览 & 使用注意事项

欢迎进入 **阶段二 · 集合**。这一节是全阶段的开篇课 ——「宽而不深」，先把整张地图铺开：`Collection` / `Map` 的顶层结构、各主流实现的对比、以及日常写业务代码最容易踩的几个坑（`Arrays.asList`、`subList`、`toArray`）。从 0011 开始，我们会一个一个类做源码深挖：`ArrayList`、`LinkedList`、`HashMap`、`ConcurrentHashMap`、红黑树 …… 现在你只需要建立起「集合家族全景图」的直觉。

本课覆盖  三篇：、、。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `ArrayList` 底层为什么用数组，而不是链表？</summary>

因为 `ArrayList` 的核心诉求是**随机访问**（`get(i)` O(1)）。数组天然按下标寻址，链表要遍历。至于「插入删除慢」的代价，大多数业务场景其实是「尾部追加 + 顺序遍历」，扩容+尾插仍然接近 O(1) 均摊。第 2 题会展开。

</details>

<details>

<summary>Q0.2 `HashMap` 为什么是线程不安全的？</summary>

多线程同时 `put` 可能同时触发扩容 `resize()`，JDK 7 的头插法在并发下会形成**循环链表**导致 `get` 死循环；JDK 8 改成尾插虽然消除了循环链，但仍会有**数据丢失**（后写覆盖前写、size 计数错乱）。要线程安全用 `ConcurrentHashMap`。第 3、5 题展开。

</details>

## 面试场景 1：Java 集合框架有哪几大类？（类图）

🎤 面试官

你能画一下 Java 集合框架的顶层类图吗？

🧑‍💻 你

Java 集合分成**两大体系**：`Collection`（单元素）和 `Map`（键值对），二者互不继承。

```
Iterable
│
Collection ────────────────┐
/    │    \                │
List   Set   Queue          Map (独立体系)
│      │      │             │
┌───────┼──────┼──────┼─────┐   ┌───┼──────────────┐
│       │      │      │     │   │   │              │
ArrayList  │  HashSet  ArrayDeque│ HashMap  LinkedHashMap
LinkedList │  LinkedHashSet     Deque│  Hashtable    TreeMap
Vector     │  TreeSet(SortedSet)     │  ConcurrentHashMap
CopyOnWrite│                          │  WeakHashMap
ArrayList  │                          │  IdentityHashMap
│                          │
LinkedList 同时实现 List + Deque
```

- **List**：*有序、可重复*，按插入顺序遍历。代表：`ArrayList`、`LinkedList`、`Vector`、`CopyOnWriteArrayList`。

- **Set**：*无序、不可重复*（`LinkedHashSet` 保插入序，`TreeSet` 保自然序）。代表：`HashSet`、`LinkedHashSet`、`TreeSet`。

- **Queue** / **Deque**：*按队列/双端队列语义*。代表：`ArrayDeque`、`LinkedList`、`PriorityQueue`、`BlockingQueue` 家族。

- **Map**：*键值对，key 不可重复*。代表：`HashMap`、`LinkedHashMap`、`TreeMap`、`Hashtable`、`ConcurrentHashMap`。

追问 为什么 `Map` 不继承 `Collection`？

因为语义不同。`Collection` 的抽象是「一堆元素」（add 一个元素、iterator 遍历元素）；`Map` 的抽象是「一堆键值对」（put 需要两个参数、遍历需要 `Entry`）。如果强行让 `Map` 继承 `Collection`，`add(E)` 就没法自然映射。所以 JDK 让二者平级，`Map` 提供 `keySet()` / `values()` / `entrySet()` 三个视图返回 `Collection`。

## 面试场景 2：ArrayList vs LinkedList vs Vector

🎤 面试官

`ArrayList`、`LinkedList`、`Vector` 三者的区别？什么场景该用哪个？

维度ArrayListLinkedListVector

底层结构动态数组 `Object[]`双向链表 `Node`动态数组 `Object[]`
线程安全否否是（方法级 `synchronized`）
随机访问 `get(i)`O(1) ✅（实现 `RandomAccess`）O(n) ❌O(1) ✅
尾部追加 `add(e)`均摊 O(1)O(1)均摊 O(1)
头部/中间插入删除O(n)（要搬移）O(1) 若已有 Node 引用；否则 O(n) 定位O(n)
扩容策略1.5 倍（`oldCap + oldCap>>1`）无需扩容2 倍（也可指定增量）
内存占用小（连续内存 + 少量空闲）大（每个节点带 prev/next 两个指针）小
典型场景99% 的日常场景频繁头尾操作、当 `Deque` 用基本已弃用

追问 `LinkedList` 是不是双向链表？为什么随机访问慢？

是双向链表，每个 `Node` 有 `prev`、`next`、`item` 三个字段。`get(i)` 慢的原因是链表没有下标寻址，只能从 `first` 或 `last` 出发一步步走。JDK 做了一点小优化：`node(i)` 会先判断 `i` 更接近头还是尾，选就近方向遍历 —— 但最坏还是 O(n/2) = O(n)。

追问 `Vector` 现在还有使用场景吗？

基本没有。它的方法级 `synchronized` 锁粒度极粗（每次 `get`/`add`/`size` 都锁整个对象），并发下性能远不如 `CopyOnWriteArrayList`（读无锁）或 `Collections.synchronizedList`（可显式复合操作加锁）。`Stack`（继承自 `Vector`）同样已过时，推荐用 `ArrayDeque`。

陷阱 `ArrayList` 允许存 `null`，但业务代码里塞 `null` 会让「集合是否为空」「元素是否存在」这两件事变得暧昧（`list.contains(null)` 返回 `true`），维护同事会想打人。除非你真的用 `null` 表达「占位」，否则一律禁用。

## 面试场景 3：HashMap vs Hashtable vs LinkedHashMap vs TreeMap vs ConcurrentHashMap

🎤 面试官

常见的几种 `Map` 实现类你都熟吗？逐一对比一下。

类底层结构线程安全有序性null 支持典型场景

`HashMap`
数组 + 链表 + 红黑树（JDK 8）
❌
无序
key/value 都可 `null`（key 仅一个）
单线程绝对首选

`Hashtable`
数组 + 链表
✅ 方法级 `synchronized`
无序
都不允许 `null`
已过时，被 `ConcurrentHashMap` 取代

`LinkedHashMap`
`HashMap` + 双向链表
❌
保插入顺序（可切访问顺序）
与 `HashMap` 同
要保序、实现 LRU 缓存

`TreeMap`
红黑树
❌
按 key 自然序或 `Comparator`
key 不可 `null`（要比较）；value 可
需要按 key 有序遍历、区间查询

`ConcurrentHashMap`
数组 + 链表 + 红黑树（JDK 8 起）
✅ CAS + `synchronized`（锁桶头）
无序
都不允许 `null`
并发场景默认选择

追问 为什么 `ConcurrentHashMap` 不允许 `null`？

因为并发场景下有**二义性**：`map.get(k) == null` 到底是「key 不存在」还是「key 对应的 value 就是 null」？单线程可以用 `containsKey()` 消歧，但多线程中间可能被别的线程改动，无法可靠区分。作者 Doug Lea 直接禁掉了。

追问 `HashMap` 的 key 用什么对象比较好？

**不可变对象**，如 `String`、`Integer`、`Long`、`UUID`、`enum`。原因：一是 `hashCode()` 结果稳定，key 不会「跑丢」；二是可缓存 hash（`String` 就缓存了 hash）。**禁忌**：可变的自定义对象，若字段变了 `hashCode` 也变，会导致 `get` 找不到自己塞进去的东西。

## 面试场景 4：HashSet 是怎么保证元素唯一的？

🎤 面试官

`HashSet.add(e)` 是怎么判断重复的？

🧑‍💻 你

`HashSet` 本质上就是「披着 Set 皮的 `HashMap`」。它内部持有一个 `HashMap`，把你 `add(e)` 的元素作为 *key* 塞进去，value 是一个静态占位对象 `PRESENT`：

```
public class HashSet<E> {
private transient HashMap<E, Object> map;
private static final Object PRESENT = new Object();

public boolean add(E e) {
return map.put(e, PRESENT) == null;   // 复用 HashMap 的去重
}
}
```

去重逻辑完全交给 `HashMap`：先算 `hashCode()` 定位桶，再对桶内元素用 `equals()` 挨个比较。所以放进 `HashSet` 的元素**必须同时正确重写 `hashCode()` 和 `equals()`**，两者必须自洽（*equals 相等 → hashCode 必须相等*）。

陷阱 只重写 `equals()` 不重写 `hashCode()`，两个「业务相等」的对象会落到不同桶里，`HashSet` 认为它们不重复 —— 集合里出现两份「相同」的用户，业务逻辑崩溃。IDE 生成 `equals` 时永远勾上「同时生成 hashCode」。

## 面试场景 5：fail-fast vs fail-safe（★核心）

🎤 面试官

什么是 fail-fast、什么是 fail-safe？`ArrayList` 和 `CopyOnWriteArrayList` 分别是哪种？

🧑‍💻 你

**fail-fast（快速失败）**：迭代过程中一旦检测到集合被结构性修改（`add`/`remove`/`clear`），立即抛 `ConcurrentModificationException`。目的是*尽早暴露并发 bug*，不让程序在不一致状态下继续跑。**代表**：`ArrayList`、`HashMap`、`HashSet`、`LinkedList` 等 `java.util` 下几乎所有非线程安全集合。

**fail-safe（安全失败）**：迭代基于集合快照或写时复制，即使原集合被修改也不抛异常，但迭代到的可能是旧数据。**代表**：`CopyOnWriteArrayList`、`ConcurrentHashMap` 等 `java.util.concurrent` 下的并发集合。

**实现机制**：fail-fast 依赖 `modCount` 计数器。集合内部维护一个 `modCount`，每次 `add`/`remove` 加 1。迭代器创建时把当前值记为 `expectedModCount`，每次 `next()` 校验二者是否相等，不等就抛 CME：

```
// ArrayList$Itr#checkForComodification
final void checkForComodification() {
if (modCount != expectedModCount)
throw new ConcurrentModificationException();
}
```

追问 为什么 `Iterator.remove()` 不会触发 fail-fast？

因为 `Iterator.remove()` 在删除元素后**同步更新了 `expectedModCount = modCount`**，所以下一次 `checkForComodification` 仍然相等。这是唯一一种「在遍历中安全删除」的方法。你在 for-each 里直接 `list.remove(e)` 会 CME，因为改的是 list 的 `modCount`，迭代器不知情。

追问 fail-fast 是并发安全保证吗？

**不是**。JDK 文档写得很清楚：「fail-fast 行为是 best-effort，无法保证一定抛出 CME」。它只是一种 *bug 探测机制*，不能替代真正的并发控制。在多线程场景要么用 `ConcurrentHashMap` 这类并发集合，要么在业务层加锁。

## 面试场景 6：如何遍历 Map 才是最优雅的？

🧑‍💻 你

四种主流姿势，按推荐度排序：

1. **JDK 8 `forEach` + Lambda**（首选，代码最短）：

```
map.forEach((k, v) -> System.out.println(k + "=" + v));
```

2. **`entrySet()` + 增强 for**（老代码里最常见，效率最高，只查一次桶）：

```
for (Map.Entry<String, Integer> e : map.entrySet()) {
String k = e.getKey();
Integer v = e.getValue();
}
```

3. **Stream**（要过滤/转换时用）：

```
map.entrySet().stream()
.filter(e -> e.getValue() > 100)
.forEach(System.out::println);
```

4. **`keySet()` + `get()`**（*不推荐*，每次 `get(k)` 又要算一次 hash + 走桶）：

```
for (String k : map.keySet()) {
Integer v = map.get(k);   // 多算一次哈希
}
```

结论：**只要 value 一定要用，就走 `entrySet()` 或 `forEach`，别用 `keySet()`。**

## 面试场景 7：Collections.synchronizedXxx 和 CopyOnWriteArrayList 有什么区别？

维度`Collections.synchronizedList``CopyOnWriteArrayList`

线程安全实现方法级 `synchronized(mutex)` 包装写时复制：写操作复制底层数组，读无锁
读性能读也要抢锁，并发读会串行读完全无锁，性能极高
写性能直接改，快每次写都复制整个数组，慢 + 吃内存
迭代一致性迭代必须*手动*加锁（`synchronized(list) {…}`）；否则可能 CME迭代基于创建时的数组快照，天然安全
fail 类型fail-fastfail-safe
数据实时性迭代能读到最新迭代读的是快照，可能过时
典型场景写多读多、要求强一致**读多写少**（配置、监听器列表、白名单）

追问 为什么 `CopyOnWriteArrayList` 不适合写多场景？

每次 `add` 都会 `Arrays.copyOf(oldArr, oldArr.length + 1)` 复制整个底层数组。10 万元素的 list 每次写要复制 10 万个引用 —— 频繁写会 CPU 飙升、GC 压力巨大。写多场景应该考虑 `ConcurrentLinkedQueue` 或分段/分片方案。

## 面试场景 8：Arrays.asList 有什么陷阱？（★经典）

🎤 面试官

看这段代码，会输出什么？

```
List<Integer> list = Arrays.asList(1, 2, 3);
list.add(4);
System.out.println(list);
```

🧑‍💻 你

会抛 `UnsupportedOperationException`。因为 `Arrays.asList` 返回的**不是 `java.util.ArrayList`**，而是 `java.util.Arrays` 的静态内部类 `Arrays$ArrayList`。它只重写了 `get`/`set`/`size` 等方法，`add`/`remove`/`clear` 全都继承自 `AbstractList` —— 而 `AbstractList` 里这几个方法的默认实现就是抛 `UnsupportedOperationException`。

这个返回值本质上是**原数组的一层视图**：`set(i, x)` 会直接改到原数组，不能改变长度。

陷阱 · 三连坑

1. **不能 add/remove**：抛 UnsupportedOperationException。

2. **基本类型数组会被整体包成单元素**：`Arrays.asList(new int[]{1,2,3})` 得到的是 `List<int[]>`，size = 1，而不是 `List<Integer>` size = 3。要传 `Integer[]` 才行。

3. **改原数组会影响 list**：因为是视图，原数组 `arr[0] = 99`，list.get(0) 也变 99。

**正确姿势**：需要可变 list 时用 `new ArrayList<>(Arrays.asList(...))`；JDK 9+ 用 `List.of(...)`（返回真正的不可变 list，语义更清晰）。

## 面试场景 9：subList 有什么陷阱？（★经典）

🎤 面试官

看这段代码：

```
List<Integer> list = new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5));
List<Integer> sub = list.subList(1, 4);   // [2, 3, 4]
list.add(6);                                // ← 修改原 list
System.out.println(sub);                    // ?
```

🧑‍💻 你

访问 `sub` 的任何方法都会抛 `ConcurrentModificationException`。因为 `subList` 返回的**不是新集合，而是原 list 的视图**（`ArrayList$SubList`）。SubList 内部保存了创建时的 `expectedModCount`，一旦原 list 发生结构性修改（`add`/`remove`），modCount 变了，SubList 再操作时校验失败就 CME。

反过来也一样：改 `sub`（`sub.add(x)`）会直接改到原 `list`！它们共用同一份底层数组。

陷阱 · 双向牵连

- **改原 list → sub 抛 CME**（fail-fast 校验失败）。

- **改 sub → 原 list 跟着变**（同一份数组的窗口）。

- 序列化陷阱：`SubList` 不实现 `Serializable`，直接序列化会抛异常。

**正确姿势**：要独立的子集，一律 `new ArrayList<>(list.subList(1, 4))`，拷一份出来彻底解耦。

追问 那 `subList` 存在的意义是什么？

批量删除子区间：`list.subList(1, 4).clear()` 可以一次删掉 `[1, 4)` 三个元素，比循环 `remove` 高效得多（`ArrayList` 内部只做一次 `System.arraycopy`）。这是 `subList` 视图设计的最大用途。

## 面试场景 10：集合转数组 `list.toArray()` 有什么陷阱？

🎤 面试官

下面两种写法，哪种正确、哪种更好？

```
List<String> list = List.of("a", "b", "c");
Object[] a = list.toArray();                          // 写法 A
String[] b = list.toArray(new String[list.size()]);   // 写法 B
String[] c = list.toArray(new String[0]);             // 写法 C
```

🧑‍💻 你

- **写法 A 无参 `toArray()`：返回 `Object[]`**，强转成 `String[]` 会 `ClassCastException`（因为运行时数组类型就是 Object[]，无法强转为 String[]）。日常业务里想拿到具体类型数组就不能用它。

- **写法 B `toArray(new String[list.size()])`：能工作但不推荐。** 传入的数组会被直接填充。

- **写法 C `toArray(new String[0])`：JDK 官方 & 阿里规约推荐。** 空数组只是*类型模板*，JDK 内部会自己 `Arrays.copyOf` 分配一个刚好合适大小的新数组。

追问 为什么 `toArray(new T[0])` 反而比 `toArray(new T[list.size()])` 更快？

反直觉但 benchmark 证实：

1. JIT 对 `new T[0]` 这种零长度数组分配做了特化，几乎零成本。

2. `toArray(new T[size])` 传入的数组需要先*清零初始化*（JVM 规范要求），再被覆盖填充 —— 相当于做了两次写。

3. 而 `toArray(new T[0])` 走 JDK 内部 `Arrays.copyOf`，底层是 `System.arraycopy` 原生批量拷贝，中间没有清零步骤。

4. 并发场景下 `list.size()` 可能已经过期，传预分配的数组还有 size 竞态风险。

详见 Aleksey Shipilev 的经典博文《Arrays of Wisdom of the Ancients》。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：fail-fast 触发 CME

```
import java.util.*;

public class FailFastDemo {
public static void main(String[] args) {
List<String> list = new ArrayList<>(List.of("a", "b", "c", "d"));

// ❌ 反例：for-each 里直接 list.remove
try {
for (String s : list) {
if ("b".equals(s)) list.remove(s);   // 改了 modCount
}
} catch (ConcurrentModificationException e) {
System.out.println("CME! for-each 里 list.remove 触发");
}

// ✅ 正例：Iterator.remove
Iterator<String> it = list.iterator();
while (it.hasNext()) {
if ("c".equals(it.next())) it.remove();  // 同步更新 expectedModCount
}
System.out.println(list);   // [a, b, d]

// ✅ JDK 8+ 更简洁
list.removeIf(s -> s.equals("d"));
System.out.println(list);   // [a, b]
}
}
```

### 验证 2：Arrays.asList 三连坑

```
import java.util.*;

public class AsListTrap {
public static void main(String[] args) {
// 坑 1：不能 add
List<Integer> l1 = Arrays.asList(1, 2, 3);
try {
l1.add(4);
} catch (UnsupportedOperationException e) {
System.out.println("坑1: add 抛 UnsupportedOperationException");
}

// 坑 2：基本类型数组被整体当成单元素
int[] arr = {1, 2, 3};
List<int[]> l2 = Arrays.asList(arr);
System.out.println("坑2: size = " + l2.size());   // 1，不是 3！

Integer[] boxed = {1, 2, 3};
List<Integer> l3 = Arrays.asList(boxed);
System.out.println("对比: size = " + l3.size());  // 3

// 坑 3：改原数组会影响 list（视图）
boxed[0] = 99;
System.out.println("坑3: " + l3);   // [99, 2, 3]

// ✅ 正确姿势
List<Integer> safe = new ArrayList<>(Arrays.asList(1, 2, 3));
safe.add(4);   // OK
System.out.println("safe: " + safe);
}
}
```

### 验证 3：subList 双向牵连

```
import java.util.*;

public class SubListTrap {
public static void main(String[] args) {
List<Integer> list = new ArrayList<>(List.of(1, 2, 3, 4, 5));
List<Integer> sub = list.subList(1, 4);   // [2, 3, 4]

// 坑 A：改 sub 会同步改到 list（同一份底层数组）
sub.set(0, 20);
System.out.println("list = " + list);   // [1, 20, 3, 4, 5]

// 坑 B：改 list 会导致 sub 抛 CME
list.add(6);
try {
System.out.println(sub.get(0));
} catch (ConcurrentModificationException e) {
System.out.println("坑B: 原 list 结构变化 → sub 抛 CME");
}

// ✅ 正确姿势：拷贝一份彻底解耦
List<Integer> independent = new ArrayList<>(list.subList(1, 4));
list.add(7);
System.out.println("independent 不受影响: " + independent);
}
}
```

### 验证 4：toArray 的三种写法对比

```
import java.util.*;

public class ToArrayDemo {
public static void main(String[] args) {
List<String> list = List.of("a", "b", "c");

// 写法 A：无参，返回 Object[]
Object[] a = list.toArray();
try {
String[] cast = (String[]) a;   // ← 运行时 ClassCastException
} catch (ClassCastException e) {
System.out.println("Object[] 无法强转 String[]");
}

// 写法 B：预分配 size（能用但不推荐）
String[] b = list.toArray(new String[list.size()]);
System.out.println("B: " + Arrays.toString(b));

// 写法 C：官方推荐，传空数组做类型模板
String[] c = list.toArray(new String[0]);
System.out.println("C: " + Arrays.toString(c));
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `ArrayList`、`LinkedList`、`Vector` 三者的核心区别？分别在什么场景用？</summary>

`ArrayList`：动态数组，非线程安全，随机访问 O(1)，日常首选。`LinkedList`：双向链表，非线程安全，头尾操作 O(1)，可当 `Deque` 用。`Vector`：动态数组，方法级 `synchronized` 线程安全，性能差，已基本被 `CopyOnWriteArrayList` / `Collections.synchronizedList` 取代。

</details>

<details>

<summary>Q2 `HashMap` 和 `ConcurrentHashMap` 在线程安全、null 支持、底层结构上各有什么差异？</summary>

`HashMap`：非线程安全，key/value 均可 null，数组+链表+红黑树。`ConcurrentHashMap`：线程安全（CAS + 桶头 `synchronized`），不允许 null（并发下 null 有二义性），数据结构类似但节点是 `Node` 且带 `volatile`。

</details>

<details>

<summary>Q3 什么是 fail-fast？它是如何实现的？`Iterator.remove()` 为什么不触发？</summary>

fail-fast 指集合被并发/结构性修改时快速抛 `ConcurrentModificationException`，属 bug 探测机制。实现靠 `modCount` 计数器：每次 `add`/`remove` 递增，迭代器创建时快照为 `expectedModCount`，`next()` 时校验。`Iterator.remove()` 会在删除后把 `expectedModCount` 同步回新的 `modCount`，所以不会误报。

</details>

<details>

<summary>Q4 `Arrays.asList(1,2,3).add(4)` 会发生什么？为什么？正确做法？</summary>

抛 `UnsupportedOperationException`。因为返回的是 `Arrays` 的内部类 `Arrays$ArrayList`（非 `java.util.ArrayList`），底层就是原数组视图，长度不可变，`add`/`remove` 走 `AbstractList` 默认实现（抛 UOE）。正确做法：`new ArrayList<>(Arrays.asList(...))` 或 JDK 9+ 的 `List.of(...)`（不可变但语义清晰）。

</details>

<details>

<summary>Q5 `list.toArray(new String[list.size()])` 和 `list.toArray(new String[0])` 哪个更好？为什么？</summary>

后者更好。JIT 对零长度数组分配做了特化，几乎零成本；预分配 size 的数组需要先清零初始化再被覆盖，做了两次写；而 `toArray(new T[0])` 走 `System.arraycopy`，跳过清零。并发场景 `list.size()` 还有过期风险。阿里规约、Effective Java、Shipilev benchmark 一致推荐第二种。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

-  —— 本课主源 C

- Aleksey Shipilev · Arrays of Wisdom of the Ancients —— `toArray(new T[0])` 性能考据

- JDK 21 · `java.util` 包 API

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0011：**`ArrayList` 源码深挖** —— 扩容 1.5 倍怎么算、`elementData` 为什么是 `Object[]`、`trimToSize` 什么时候用、`ensureCapacity` 的性能价值、`SubList` 源码里 `modCount` 到底怎么校验。这一课我们停留在「全景 + 陷阱」层面，下一课起真正进源码。

💬 有任何疑问 —— 「fail-fast 的 modCount 具体在哪一行加？」「TreeMap 的红黑树能扒一下源码吗？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


