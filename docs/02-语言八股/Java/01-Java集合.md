# 01 · Java 集合

## 一、HashMap（最高频，必考）

### 底层结构
- JDK 1.8：数组 + 链表 + 红黑树。数组叫 table，每个槽位（Node）是链表的头。
- 链表长度 >= 8 且数组长度 >= 64 时转红黑树；树退化回链表：扩容拆分后节点数 <= 6，或 remove 后根为 null/小节点。
  - 为什么是 8？泊松分布：负载因子 0.75 下，链表长度到 8 的概率极低（约千万分之六），8 是空间与时间权衡的经验值。
  - 为什么树化还留 6？留缓冲，避免在 7/8 之间频繁转换（抖动）。

### put 流程
1. 对 key 的 hashCode 做扰动：`hash = key.hashCode() ^ (hashCode >>> 16)`（高 16 位参与运算，降低碰撞）。
2. `(n - 1) & hash` 定位数组下标（等价取模，前提 n 是 2 的幂）。
3. 槽为空 → 直接放新节点。
4. 槽非空：比较 hash 和 equals，相同则覆盖；否则尾插法追加链表（1.7 是头插，并发扩容会成环）；到达树化阈值则转红黑树。
5. 容量超过阈值 `size > capacity * loadFactor`（默认 0.75）→ 扩容。

### 扩容机制
- 默认容量 16，负载因子 0.75，扩容翻倍（resize）。
- 为什么容量必须是 2 的幂：`(n-1) & hash` 才能均匀散列；扩容后元素要么在原位，要么在原位 + 旧容量（高位为 1 则挪），1.8 用高低位拆分，无需 rehash，效率高。
- 指定初始容量会向上取 2 的幂：`tableSizeFor`。

### 为什么线程不安全
- 1.7：并发扩容头插法形成循环链表 → 死循环。
- 1.8：put 覆盖（两个线程同时 put 到同一槽，后写覆盖）、size 不准确、可能丢数据。

### 1.7 vs 1.8 差异（追问常考）
| 项 | 1.7 | 1.8 |
| --- | --- | --- |
| 结构 | 数组+链表 | 数组+链表+红黑树 |
| 插入 | 头插 | 尾插 |
| 扩容 | 全部 rehash | 高低位拆分 |
| hash | 4 次扰动 | 1 次扰动 |

### get 流程
- 算 hash → 定位槽 → 链表/树中按 hash+equals 查找。

### 其他考点
- 允许 null key（放到 table[0]）、null value；无序；非线程安全。
- 为什么重写 equals 必须重写 hashCode：hashCode 相同不一定相等，但相等必须 hashCode 相同，否则 HashMap 里查不到。
- size 是插入数，非桶数。

## 二、ConcurrentHashMap（必考）

### 1.7：Segment 分段锁
- 继承 ReentrantLock 的 Segment 数组，默认 16 段，每段一把锁；put 锁段，get 不加锁（volatile 读）。锁粒度大，已废弃。

### 1.8：CAS + synchronized
- 取消分段，直接用 Node 数组。
- put：槽为空用 CAS 写入；槽非空 synchronized 锁住链表头/树根（只锁一个槽，粒度最小）；数组扩容用 `sizeCtl` + CAS 控制。
- get 全程无锁：Node 的 val/next 用 volatile 修饰。
- 为什么 1.8 用 synchronized 而不是 ReentrantLock：锁的是单个 Node，粒度更细，且 synchronized 在 JDK 后期有锁升级优化，性能不差、代码更简单。

### 计数
- 用 baseCount + CounterCell 数组分散计数，并发高时 CAS 失败落到 Cell 上，size() 做累加（近似值）。

### 与 Hashtable / Collections.synchronizedMap 区别
- Hashtable 整表一把锁（锁 this），并发极差；ConcurrentHashMap 锁粒度细，读多写少性能最好。

## 三、List

### ArrayList
- 底层 Object[]，默认初始容量 10（懒加载，第一次 add 才建）。
- 扩容：1.5 倍（`old + (old >> 1)`），Arrays.copyOf 拷新数组，O(n)。
- 随机访问 O(1)；中间插入/删除 O(n)（System.arraycopy 移动元素）。
- 适合：读多写少、尾部操作。
- 线程不安全；subList 是视图，改动会影响原列表；`Arrays.asList` 返回定长列表，不能 add/remove。

### LinkedList
- 双向链表 Node（prev/item/next），增删头尾 O(1)，随机访问 O(n)（二分折半找）。
- 实现了 Deque，可当队列/栈用。
- 适合：频繁头尾插入删除。

### 怎么选
- 大多数场景 ArrayList；明确要频繁头尾增删才用 LinkedList。

## 四、HashSet / TreeMap

- HashSet 底层就是 HashMap（value 是固定 Object），add 即 map.put；元素不能重复且无序。
- TreeMap：红黑树实现，key 有序（自然序或 Comparator）；put/get O(log n)。
- LinkedHashMap：HashMap + 双向链表，保插入序或访问序（LRU 可用 accessOrder=true 实现）。

## 五、fail-fast / fail-safe

- fail-fast：迭代时结构被修改（modCount 变化）抛 ConcurrentModificationException，如 ArrayList/HashMap。
- fail-safe：迭代拷贝副本，不抛异常但可能读不到最新，如 CopyOnWriteArrayList。

## 六、常问追问

1. HashMap 为什么不直接用 hashCode 做下标？→ 容量小，高 16 位不参与会导致碰撞多。
2. 为什么树化阈值 8、退化 6？→ 概率 + 缓冲。
3. 为什么重写 equals 要重写 hashCode？→ 哈希容器查找一致性。
4. 1.8 HashMap 扩容为什么不用 rehash？→ 高低位拆分，新下标 = 原下标 或 原下标+旧容量。
5. 用 HashMap 存 1 万条数据，初始容量设多少？→ 预估 size/0.75 向上取 2 的幂，避免频繁扩容。
6. ConcurrentHashMap 的 size() 准确吗？→ 近似值。
7. 让你设计一个并发安全的 LRU？→ LinkedHashMap accessOrder + 读写锁，或 ConcurrentHashMap + 双向链表。
