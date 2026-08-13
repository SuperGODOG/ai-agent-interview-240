> Lesson 0013 · 阶段二 · Java 集合 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个高频追问

# 0013 · HashMap 源码深挖：数据结构 & hash 扰动 & 扩容 & 树化 & 线程不安全

这是 Java 集合面试**几乎必问的一课**。参考 ，面试官从这里能连问 20 分钟：数据结构、hash 扰动、扩容 rehash、树化阈值、线程不安全、和 `ConcurrentHashMap` 的对比…… 只要你能把 HashMap 说明白，**集合面试就过关一半**。这一课把 JDK 8 源码里所有面试点一次拆完。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `new HashMap<>()` 建出来的 map 内部数组长度是 16 吗？</summary>

**不是**。构造函数只把 `loadFactor` 设为 0.75f，`table` 数组是 `null`，只有第一次 `put` 才会 resize 出长度 16 的数组。这是最经典的陷阱题，第 2 题会展开。

</details>

<details>

<summary>Q0.2 HashMap 什么时候会树化，什么时候退化回链表？</summary>

树化条件是**两个同时满足**：单桶链表长度 ≥ 8 *且* `table` 长度 ≥ 64（否则先扩容而不是树化）；退化条件是扩容 split 后**树节点 ≤ 6**。阈值差 2 是为了防止在 7-8 之间反复震荡。第 7、8 题细讲。

</details>

## 面试场景 1：HashMap 底层数据结构 ⭐核心

🎤 面试官

说说 HashMap 的底层数据结构。JDK 8 前后有什么变化？

🧑‍💻 你

**JDK 8 之前**：`数组 + 链表`（拉链法）。哈希冲突就在同一个桶挂一条单链表。

**JDK 8 之后**：`数组 + 链表 + 红黑树`。当单桶链表长度达到 8 且数组长度 ≥ 64 时，把链表转成红黑树，把最坏查询从 `O(n)` 降到 `O(log n)`；反过来节点数退到 6 又转回链表。

三个核心类型：

- `Node<K,V>[] table`：桶数组，长度永远是 2 的幂。

- `Node<K,V>`：普通链表节点，字段 `hash`、`key`、`value`、`next`。

- `TreeNode<K,V>`：红黑树节点，继承自 `LinkedHashMap.Entry`，额外有 `parent`、`left`、`right`、`prev`、`red`。

```
table
┌─┐   ┌───────┐   ┌───────┐
│0├──►│ Node  ├──►│ Node  │
├─┤   └───────┘   └───────┘
│1│  null
├─┤   ┌────────────┐
│2├──►│  TreeNode  │  ← 长链表已经树化
├─┤   │  (root)    │
│…│   └────────────┘
```

追问 HashMap 允许 key 为 null 吗？value 呢？允许几个？

**都允许。** key 允许*一个* null（`hash(null)` 直接返回 0，所以 null key 永远落在 `table[0]`），value 无限制。反例：`Hashtable` 和 `ConcurrentHashMap` 都*不允许* null key / null value —— `ConcurrentHashMap` 是因为并发场景下无法区分「key 不存在」和「key 存在但值为 null」（会引发歧义）。

## 面试场景 2：`new HashMap<>()` 初始容量是 16 吗？⭐经典陷阱

🎤 面试官

`new HashMap<>()` 之后，内部数组长度是 16 吗？

🧑‍💻 你

**不是。** 无参构造函数*只做一件事* —— 把 `loadFactor` 设为默认的 0.75f，`table` 依然是 `null`：

```
public HashMap() {
this.loadFactor = DEFAULT_LOAD_FACTOR;  // 只有这一行
// table = null
// threshold = 0
}
```

数组的真正分配**延迟到第一次 `put`**。`put` 内部走 `putVal` → 判断 `table == null` → 调 `resize()`，在 `resize()` 里根据 `DEFAULT_INITIAL_CAPACITY = 16` 分配数组。

指定容量的构造函数更绕，它把参数用 `tableSizeFor` 向上取整成 2 的幂，**存到 `threshold` 字段**而不是当容量用：

```
public HashMap(int initialCapacity, float loadFactor) {
this.loadFactor = loadFactor;
this.threshold = tableSizeFor(initialCapacity);  // 借 threshold 暂存
}
```

第一次 put 时 `resize()` 检测到 `threshold > 0`，就把它当成初始容量分配数组，然后重新算出真正的 threshold（`capacity * loadFactor`）。

陷阱 面试官经常问「`new HashMap<>(11)` 内部容量是多少？」答案是 **16**（`tableSizeFor(11)` 向上取整成最近的 2 的幂）。`new HashMap<>(17)` 就是 32。想按预期数量精确分配，公式：`initialCapacity = (int) (expected / 0.75f) + 1`，避免刚放完就扩容。

追问 为什么要延迟初始化 table？

为了**节省内存**。很多 HashMap 声明了从来不用（比如某个 if 分支才会 put），提前分配 16 长度数组浪费。延迟到第一次 put 是 JDK 8 的优化 —— JDK 7 是构造时就分配。

## 面试场景 3：HashMap 容量为什么必须是 2 的幂？⭐核心

🎤 面试官

为什么 HashMap 的容量一定要是 2 的幂？`tableSizeFor` 为什么要把用户传的容量向上取整？

🧑‍💻 你

两个理由，都是为了性能。

**理由 1：定位桶用位与代替取模**。计算下标本质是 `hash % n`，但 *取模是很慢的 CPU 指令*。当 n 是 2 的幂时，`hash % n` 等价于 `hash & (n - 1)`：

```
n = 16, n - 1 = 15 (二进制 00001111)
hash = 0b11001011010010111010
hash & 15:
0b11001011010010111010
& 0b00000000000000001111
= 0b00000000000000001010  = 10  ← 就是 hash % 16 的结果
```

位与在 CPU 上是单条指令，比整数除法快一个数量级。这也是 `n - 1` 必须全 1 的原因 —— 只有 2 的幂减 1 才是「低位全 1」，才能保留 hash 的全部低位；如果 `n = 15`，`n - 1 = 14 = 0b1110`，最低位永远是 0，一半的桶永远不会被落到，退化成灾难。

**理由 2：扩容 rehash 极其巧妙**。容量翻倍（新 n = 旧 n * 2）时，一个元素在新数组里要么*留在原位置*，要么*移到「原位置 + oldCap」*，只用判断 `e.hash & oldCap == 0` 即可。这是场景 6 的核心，先记住结论。

追问 `tableSizeFor` 内部是怎么把任意整数向上取整成 2 的幂的？

用**连续位移或**把最高位以下全填 1，最后 +1。核心几行：`n |= n >>> 1; n |= n >>> 2; n |= n >>> 4; n |= n >>> 8; n |= n >>> 16;` 之后 `n + 1` 就是大于等于原值的最小 2 的幂。开头还有个 `n = cap - 1`，是为了处理输入本身就是 2 的幂的情况（不然 8 会被取到 16）。

## 面试场景 4：hash 扰动函数 ⭐核心

🎤 面试官

HashMap 是直接用 `key.hashCode()` 定位桶吗？

🧑‍💻 你

不是，中间还有一步「扰动函数」：

```
static final int hash(Object key) {
int h;
return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

做的事情是：把 `hashCode` 的**高 16 位无符号右移，再和自己异或**，让高位也参与到低位。

**为什么要扰动？** 定位桶用 `hash & (n - 1)`，当 `n` 很小（比如默认 16）时，`n - 1 = 15`，*只有最低 4 位起作用*，高位全被丢掉。如果两个 key 的 hashCode 只有高位不同（比如 `0x1234ABCD` 和 `0x5678ABCD`），低位一样 → 定位到同一个桶 → 碰撞。

扰动后：

```
hashCode = 0x1234ABCD  (二进制 0001 0010 0011 0100 1010 1011 1100 1101)
hash     = 0x1234ABCD ^ (0x1234ABCD >>> 16)
= 0x1234ABCD ^ 0x00001234
= 0x1234B9F9   ← 高低位混合，低 4 位从 0xD 变成 0x9
```

一次异或 + 一次移位，成本几乎为 0，但显著降低了「低容量 + 高位差异」场景下的碰撞率。JDK 7 扰动了 4 次，JDK 8 权衡后简化成一次异或就够用。

追问 为什么 HashMap 的 key 推荐用 String / Integer 这种不可变对象？

**防止 hashCode 中途变化找不到元素。** HashMap 定位桶靠 `hash(key)`，如果 key 是可变对象，*put 之后修改字段导致 hashCode 变了*，下次 `get` 时算出的桶位置就变了，找不到原来那条数据。`String`、`Integer`、`Long` 都是 final class + final 字段，构造后 hashCode 永远不变。用可变对象（比如自定义的 `User`）当 key 是常见事故源。

追问 自定义 key 需要重写什么？

**必须同时重写 `equals` 和 `hashCode`**。HashMap 用 hashCode 定位桶，用 equals 在桶内比较。只重写 equals 会导致相等对象散到不同桶；只重写 hashCode 会导致相同桶里找不到「相等」的元素。这就是 equals/hashCode 契约（详见 ）。

## 面试场景 5：put 完整流程 ⭐背下来

🎤 面试官

讲一下 `HashMap.put` 从头到尾的完整流程。

🧑‍💻 你

八步走：

1. **算 hash**：`hash(key)`，扰动一次。

2. **懒初始化**：`table == null` 就 `resize()` 分配长度 16 的数组。

3. **定位桶**：`i = (n - 1) & hash`；**桶空**：直接 `new Node` 放进去。

4. **首节点 key 相同**（hash 相等 *且* equals 返回 true）：记录 `oldValue`，直接覆盖。

5. **首节点是 TreeNode**：走 `putTreeVal` 红黑树插入。

6. **链表遍历**：找到 key 相等的节点覆盖；找不到就 **尾插** 一个新 Node。

7. **链表长度 ≥ 8** 时调 `treeifyBin`：*先看 table 长度* ——< 64 只 resize，≥ 64 才真的树化。

8. **size++，检查 threshold**：`size > threshold` 触发 `resize()` 扩容。

```
public V put(K key, V value) {
return putVal(hash(key), key, value, false, true);
}

final V putVal(int hash, K key, V value, boolean onlyIfAbsent, boolean evict) {
Node<K,V>[] tab; Node<K,V> p; int n, i;
if ((tab = table) == null || (n = tab.length) == 0)
n = (tab = resize()).length;                    // 步骤 2
if ((p = tab[i = (n - 1) & hash]) == null)
tab[i] = newNode(hash, key, value, null);       // 步骤 3
else {
Node<K,V> e; K k;
if (p.hash == hash &&
((k = p.key) == key || (key != null && key.equals(k))))
e = p;                                      // 步骤 4：首节点命中
else if (p instanceof TreeNode)
e = ((TreeNode<K,V>)p).putTreeVal(...);    // 步骤 5：走树
else {
for (int binCount = 0; ; ++binCount) {
if ((e = p.next) == null) {
p.next = newNode(hash, key, value, null); // 步骤 6：尾插
if (binCount >= TREEIFY_THRESHOLD - 1)
treeifyBin(tab, hash);          // 步骤 7
break;
}
if (e.hash == hash &&
((k = e.key) == key || (key != null && key.equals(k))))
break;                              // 覆盖
p = e;
}
}
if (e != null) {
V oldValue = e.value;
if (!onlyIfAbsent || oldValue == null) e.value = value;
return oldValue;                            // 返回旧值
}
}
++modCount;
if (++size > threshold) resize();                   // 步骤 8
return null;
}
```

## 面试场景 6：扩容 resize ⭐核心

🎤 面试官

HashMap 扩容时怎么把老数据搬到新数组？需要重新算 hash 吗？

🧑‍💻 你

**不需要重新算 hash**，这是 JDK 8 相对 JDK 7 最漂亮的优化。

扩容规则：容量 `oldCap → newCap = oldCap * 2`，threshold 也翻倍。老数组每个节点，在新数组里**只有两种可能**：留在原位置 `j`，或移到 `j + oldCap`。

为什么？举个例子。假设 `oldCap = 16`，`oldCap - 1 = 0b01111`；`newCap = 32`，`newCap - 1 = 0b11111`。*新旧下标只差第 5 位*（也就是 `oldCap` 那位）。

```
hash = ...X abcd   (X 是第 5 位，abcd 是低 4 位)

老下标 = hash & 0b01111 = 0abcd
新下标 = hash & 0b11111 = Xabcd

若 X = 0：新下标 == 老下标（留原位）
若 X = 1：新下标 == 老下标 + 16（移到 j + oldCap）

判断 X 就用：(hash & oldCap) == 0
(即 hash & 0b10000)
```

所以每个链表可以被**拆成两条子链**（低位链 loHead 和高位链 hiHead），一次遍历搞定，不用重新算 hash，也不用重新定位每个元素：

```
Node<K,V> loHead = null, loTail = null;
Node<K,V> hiHead = null, hiTail = null;
Node<K,V> next;
do {
next = e.next;
if ((e.hash & oldCap) == 0) {           // 留原位
if (loTail == null) loHead = e;
else loTail.next = e;
loTail = e;
} else {                                 // 移到 j + oldCap
if (hiTail == null) hiHead = e;
else hiTail.next = e;
hiTail = e;
}
} while ((e = next) != null);

if (loTail != null) { loTail.next = null; newTab[j] = loHead; }
if (hiTail != null) { hiTail.next = null; newTab[j + oldCap] = hiHead; }
```

红黑树的迁移逻辑一样，只是 split 之后如果一条子链的节点数 ≤ `UNTREEIFY_THRESHOLD = 6`，就退化回链表。

追问 扩容是不是很慢？高频写入怎么规避？

**会慢**。resize 需要遍历所有节点重新链接，是 `O(n)` 的一次性开销。规避办法：**初始化时预估容量**，用 `new HashMap<>((int)(expected / 0.75f) + 1)`。比如已知会放 100 个元素，构造时传 `134`（会被 `tableSizeFor` 向上取整为 256），全程无需扩容。反例：`new HashMap<>(100)` 得到容量 128，threshold 是 96，放到第 97 个就触发扩容。

## 面试场景 7：树化条件 & 退化条件 ⭐经典追问

🎤 面试官

HashMap 什么时候树化？什么时候又退化回链表？

🧑‍💻 你

三个常量卡住这件事：

- `TREEIFY_THRESHOLD = 8`：单桶链表长度达到 8 时*考虑*树化。

- `MIN_TREEIFY_CAPACITY = 64`：真正树化的前提是 `table.length ≥ 64`。如果不够，`treeifyBin` 只 resize 而不树化。

- `UNTREEIFY_THRESHOLD = 6`：扩容 split 后，红黑树节点数 ≤ 6 就退化回链表。

为什么小容量优先扩容而不是树化？*因为链表长是「容量太小 → 碰撞太多」的信号，扩容能同时缓解所有桶*，比只树化一个桶更划算。`treeifyBin` 源码里第一行就是：

```
final void treeifyBin(Node<K,V>[] tab, int hash) {
int n, index; Node<K,V> e;
if (tab == null || (n = tab.length) < MIN_TREEIFY_CAPACITY)
resize();                     // 容量不够 64 → 只扩容
else if ((e = tab[index = (n - 1) & hash]) != null) {
// ...真正树化的逻辑
}
}
```

**退化时机**：只在 `resize` 拆链和 `remove` 里检查。普通 put 不会主动退化。

## 面试场景 8：为什么树化阈值是 8，退化是 6？

🎤 面试官

为什么树化阈值是 8？为什么退化是 6，不是 7？

🧑‍💻 你

**关于 8 —— 来自泊松分布**。JDK 源码注释里写死了：在负载因子 0.75 下，桶内节点数服从参数 λ ≈ 0.5 的泊松分布，各长度出现的概率是：

```
0: 0.60653066
1: 0.30326533
2: 0.07581633
3: 0.01263606
4: 0.00157952
5: 0.00015795
6: 0.00001316
7: 0.00000094
8: 0.00000006   ← 千万分之六，几乎不可能
```

换句话说，正常使用中链表*几乎不会长到 8*。真的长到 8 说明碰撞已经异常（可能是攻击性 hash 冲突），这时候树化才划算。设成 8 就是让树化**成为异常兜底**，而不是常规操作 —— 因为红黑树维护成本远高于链表（每个 TreeNode 是 Node 的两倍大小）。

**关于 6 —— 阈值差 2 避免震荡**。如果树化和退化都用同一个阈值（比如都是 7），那么单桶节点数在 7 附近反复 put/remove 时会不断树化 → 退化 → 树化，消耗巨大。差 2 留出**迟滞区间**：7 时既不树化也不退化，稳定。

追问 HashMap 的负载因子 0.75 是怎么算出来的？

**时间空间平衡的经验值**。数学层面：负载因子越大 → 数组越密 → 碰撞越多 → 链表变长 → 查询慢；负载因子越小 → 数组越稀 → 扩容更频繁 → 内存浪费。0.75 是「查询 O(1) 概率高 + 空间利用率还行」的甜点。JDK 源码注释还给了另一个理由：*0.75 让 `capacity * loadFactor` 是整数*（因为 capacity 都是 2 的幂，乘 0.75 = 乘 3/4 = 位移相加，结果是整数），threshold 计算干净。

## 面试场景 9：JDK 7 头插 vs JDK 8 尾插 ⭐经典追问

🎤 面试官

听说 JDK 7 的 HashMap 多线程会死循环？JDK 8 修了？

🧑‍💻 你

**问题根源在 JDK 7 用「头插法」rehash**。JDK 7 扩容时遍历老链表，逐个把节点*头插*到新桶 —— 这会**倒转链表顺序**。单线程无所谓，多线程并发扩容时会出事：

假设老链表是 `A → B → null`，两个线程 T1 和 T2 同时触发 resize。T1 刚拿到 A、还没链完就被切走，T2 完整跑完 rehash 得到 `B → A → null`。T1 恢复后继续用*老的引用*：以为还是 `A → B`，把 A 头插到新桶，再把 B 头插到 A 前面，结果 **`A.next = B` 且 `B.next = A`** —— 环链形成。之后任何 `get` 命中这个桶都是死循环，CPU 100%。

**JDK 8 改为尾插**：rehash 时用 loHead/loTail、hiHead/hiTail 拆链，*保持原顺序*，不会倒转 —— 从根本上杜绝了环链。但……

追问 JDK 8 尾插解决了死循环，但为什么还是不能多线程用？

因为**其他并发问题依然存在**：

1. **数据覆盖**：两个线程同时 put 到同一个空桶，都判断 `tab[i] == null` 通过，然后*后写的覆盖先写的*，先写的数据凭空消失。

2. **size 竞争**：`++size` 不是原子操作，多线程并发时 size 会被少加，导致 `size > threshold` 判断失灵，容量迟迟不扩，链表越来越长。

3. **扩容期间的读写**：resize 过程中另一个线程读到旧 `table` 或半迁移状态，get 返回 null。

4. **迭代 fail-fast**：一个线程遍历时另一个改 `modCount`，`ConcurrentModificationException`。

并发场景一律用 `ConcurrentHashMap`（详见 ）。

## 面试场景 10：HashMap 为什么线程不安全？怎么解决？

🎤 面试官

HashMap 线程不安全的具体表现有哪些？生产环境怎么替换？

🧑‍💻 你

不安全的表现整合成一张表：

问题根因后果

数据丢失并发 put 到同一空桶后写覆盖先写
size 不准`++size` 非原子threshold 判断失灵，扩容延迟
死循环（JDK 7）头插法 rehash 倒转链表CPU 100%
get nullresize 中读到半迁移 table明明 put 过却读不到
迭代异常fail-fast 机制`ConcurrentModificationException`

🧑‍💻 你

解决方案三选一：

- **`Hashtable`**：老古董，方法级 `synchronized`，*全表锁*，并发性能差。key/value 不允许 null。除了遗留代码不要用。

- **`Collections.synchronizedMap(new HashMap<>())`**：包一层 `SynchronizedMap`，所有方法加同一把互斥锁，本质和 Hashtable 一样烂。

- **`ConcurrentHashMap`**：*正确答案*。JDK 8 用 CAS + `synchronized(桶头节点)`，只锁单个桶，get 完全无锁。第 0015 课深挖。

追问 HashMap 遍历顺序是什么？依赖顺序会踩什么坑？

**无序**。迭代顺序由 *hash 值 + 桶数组顺序* 决定，不是插入顺序。而且 **扩容后顺序会变**（元素被拆到不同桶，链表内部顺序也可能改）。业务代码里一旦依赖遍历顺序（比如返回给前端要按插入顺序展示），扩容后就会出诡异 bug。要保序用 `LinkedHashMap`（详见 ），要按 key 排序用 `TreeMap`。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：`new HashMap<>()` 之后 table 是 null

```
import java.lang.reflect.Field;
import java.util.HashMap;

public class TableInitTest {
public static void main(String[] args) throws Exception {
HashMap<String, String> map = new HashMap<>();
Field tableField = HashMap.class.getDeclaredField("table");
tableField.setAccessible(true);
System.out.println("刚构造 table = " + tableField.get(map));      // null
map.put("k", "v");
Object[] table = (Object[]) tableField.get(map);
System.out.println("put 后 table.length = " + table.length);      // 16
}
}
```

### 验证 2：hash 扰动的效果

```
public class HashPerturbation {
static int hash(Object key) {
int h;
return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}

public static void main(String[] args) {
// 两个 hashCode 只在高位不同的 key
int hc1 = 0x1234ABCD;
int hc2 = 0x5678ABCD;
int n = 16;   // 假设容量 16

// 不扰动：低 4 位一样 → 冲突
System.out.printf("不扰动: %d, %d%n", hc1 & (n-1), hc2 & (n-1));
// 扰动后：高低位混合 → 分散
int h1 = hc1 ^ (hc1 >>> 16);
int h2 = hc2 ^ (hc2 >>> 16);
System.out.printf("扰动后: %d, %d%n", h1 & (n-1), h2 & (n-1));
}
}
// 不扰动: 13, 13   ← 撞桶
// 扰动后: 9, 5     ← 分散
```

### 验证 3：可变 key 找不到元素

```
import java.util.HashMap;
import java.util.Objects;

class MutableKey {
int id;
MutableKey(int id) { this.id = id; }
@Override public boolean equals(Object o) {
return o instanceof MutableKey && ((MutableKey) o).id == id;
}
@Override public int hashCode() { return Objects.hash(id); }
}

public class MutableKeyTest {
public static void main(String[] args) {
HashMap<MutableKey, String> map = new HashMap<>();
MutableKey k = new MutableKey(1);
map.put(k, "hello");

k.id = 999;                          // ← 改了字段
System.out.println(map.get(k));      // null！找不到自己
System.out.println(map.size());      // 1，数据还在，只是永远读不到
}
}
```

### 验证 4：多线程 put 数据丢失（JDK 8 也丢）

```
import java.util.HashMap;
import java.util.concurrent.CountDownLatch;

public class ConcurrentPutLoss {
public static void main(String[] args) throws Exception {
HashMap<Integer, Integer> map = new HashMap<>();
int threads = 10, perThread = 10000;
CountDownLatch latch = new CountDownLatch(threads);

for (int t = 0; t < threads; t++) {
final int base = t * perThread;
new Thread(() -> {
for (int i = 0; i < perThread; i++) map.put(base + i, i);
latch.countDown();
}).start();
}
latch.await();
System.out.println("期望 size = " + (threads * perThread));
System.out.println("实际 size = " + map.size());  // 通常小于期望，甚至可能死循环 / OOM
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `new HashMap<>(20)` 之后 `table.length` 是多少？threshold 呢？</summary>

`table.length` 在第一次 put 前是 0（table 是 null）；第一次 put 后是 **32**（`tableSizeFor(20)` 向上取整到最近 2 的幂）。threshold 在构造后先临时存 32，第一次 put 后重新算成 `32 * 0.75 = 24`。

</details>

<details>

<summary>Q2 hash 扰动函数 `(h = key.hashCode()) ^ (h >>> 16)` 解决什么问题？</summary>

让 hashCode 的**高 16 位参与低位运算**。定位桶用 `hash & (n-1)`，容量小时只有低位起作用，两个高位差异的 key 容易碰撞。扰动一次异或几乎无性能损失，却显著降低碰撞率。

</details>

<details>

<summary>Q3 扩容时 `(e.hash & oldCap) == 0` 判断的是什么？</summary>

判断新数组里该元素**留原位还是移到「原位置 + oldCap」**。因为新容量是老容量的 2 倍，新旧下标只差 `oldCap` 那一位（也就是新的最高位）。这样不用重新算 hash，一次遍历拆成两条子链，性能极好。

</details>

<details>

<summary>Q4 链表长度到 8 一定会树化吗？</summary>

**不一定**。`treeifyBin` 先检查 `table.length`：小于 `MIN_TREEIFY_CAPACITY = 64` 时只 resize 不树化。因为链表长常常是「容量太小」的信号，扩容能缓解所有桶，比只树化一个更划算。

</details>

<details>

<summary>Q5 JDK 8 已经改成尾插，为什么还是不能多线程？</summary>

尾插只解决了 rehash 环链导致的死循环。其他并发问题依旧：**并发 put 数据覆盖、`++size` 非原子导致 size 不准、resize 中读到半迁移 table 返回 null、迭代 fail-fast 抛 `ConcurrentModificationException`**。并发场景一律用 `ConcurrentHashMap`。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.util.HashMap` API —— 官方 Javadoc

- OpenJDK 源码：`src/java.base/share/classes/java/util/HashMap.java`

#### 🔗 关联课件

- （上一课）

- （下一课 —— 有序的 HashMap）

- （HashMap 的并发版）

- （自定义 key 必读）

#### 🧭 下一课预告

Lesson 0014：**LinkedHashMap & LRU 缓存实现** —— HashMap 加一条双向链表，就能同时具备哈希查找和插入/访问顺序，是手写 LRU 面试题的标准答案。

💬 有任何疑问 ——「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


