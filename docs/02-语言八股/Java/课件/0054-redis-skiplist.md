> Lesson 0054 · 阶段七 · Redis · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0054 · Redis 跳表 & ziplist & listpack

0052 课把 5 种基本类型（String / List / Hash / Set / ZSet）的*外壳*过了一遍，反复提到「ZSet 底层是**跳表**、小 Hash / 小 List 用 **ziplist**、Redis 7.0 后 ziplist 被 **listpack** 取代」—— 但没展开原理。这一课就把这三种紧凑数据结构掰开揉碎：**跳表凭什么打败红黑树坐稳 ZSet 的头把交椅？ziplist 的「级联更新」为什么被 Redis 团队痛下决心废弃？listpack 到底改了什么？**面试问 Redis 底层结构，八成绕不开这三个词。

本课主源 ，并补充 Redis 源码里的 `t_zset.c`、`ziplist.c`、`listpack.c` 的关键设计。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 ZSet 为什么用跳表而不用红黑树？只答一句「简单」够吗？</summary>

远远不够。**四个理由**：实现简单、*范围查询天然快*（底层就是有序链表）、内存开销更低（平均指针 3-4 个 < 红黑树的 3 指针 + 颜色）、并发无锁更好实现。*范围查询*是压死红黑树的最重稻草 —— `ZRANGE`/`ZRANGEBYSCORE` 是 ZSet 最常见操作。第 3 题详细拆。

</details>

<details>

<summary>Q0.2 ziplist 的「级联更新」是什么？为什么值得 Redis 团队重新设计一个 listpack 替换它？</summary>

ziplist 每个节点用 `prevlen` 字段记录前驱长度，<254 字节用 1 字节存，≥254 用 5 字节。如果你在 253 字节和 254 字节之间反复横跳（比如插入一个 300 字节的节点），后一个节点的 `prevlen` 从 1 变 5，导致*它自己*的长度也变了，再触发后一个节点的 `prevlen` 扩容...最坏 **O(n²)**。listpack 让*每个节点自己存自己的长度*，彻底切断这种依赖链。第 7、8 题细讲。

</details>

## 面试场景 1：跳表是什么？（★核心）

🎤 面试官

跳表你能用一分钟讲清楚吗？

🧑‍💻 你

**跳表（skiplist）**是一种基于*多层有序链表*的概率数据结构，1990 年由 William Pugh 提出。核心思想：给有序链表建**多级索引**，查找时从最高层「快速道」跳着走，接近目标再下降。

三大性质：

- **底层是完整的有序链表**，包含所有元素。

- **上层是「稀疏索引」**，每层元素数期望是下层的 1/p（p 通常 1/2 或 1/4）。

- **节点层高随机决定**，不需要旋转/染色维护平衡。

时间复杂度：查找 / 插入 / 删除都是**期望 O(log n)**；空间 O(n)。

追问 跳表最坏时间复杂度是多少？为什么 Redis 敢用一个「随机」数据结构？

理论最坏 **O(n)**（所有节点随机到层高 1 时退化成普通链表）。但概率极低：*1000 个节点全退化到 1 层*的概率约 `(3/4)^1000 ≈ 10^-125`。工程上完全可以忽略。Redis 敢用是因为：随机性只影响性能不影响正确性，且实测在百万级 ZSet 上表现稳定。

## 面试场景 2：跳表的结构与原理

🧑‍💻 你

画一个高度为 3 的跳表来说明：

```
Level 3:  HEAD ─────────────────────────► 30 ────────────► NIL
Level 2:  HEAD ────────► 10 ────────────► 30 ────► 50 ──► NIL
Level 1:  HEAD ────────► 10 ────► 20 ──► 30 ────► 50 ──► NIL
Level 0:  HEAD ► 5 ───► 10 ► 15 ► 20 ──► 30 ► 40 ► 50 ──► NIL
↑ 每层都是有序链表，同一节点通过 forward[] 数组挂在多层
```

**查找 40 的路径**：从 Level 3 的 HEAD 出发 →

1. Level 3：HEAD.forward[3] = 30，30 < 40，前进到 30。30.forward[3] = NIL，下降到 Level 2。

2. Level 2：30.forward[2] = 50，50 > 40，下降到 Level 1。

3. Level 1：30.forward[1] = 50，50 > 40，下降到 Level 0。

4. Level 0：30.forward[0] = 40，命中！

只走了 4 步就找到了。这就是「**每层前进直到 > 目标就下降**」的核心思路。插入和删除也遵循同样路径找位置，只是多做几步链表指针操作。

追问 跳表查找的时间复杂度证明？

关键在*每层期望前进步数*。设升级概率 p，则每层前进 1 步「不下降」的概率是 p，「下降」的概率是 1-p。**期望在每层前进 1/(1-p) 步就下降**（几何分布）。总层数期望 `log_(1/p)(n)`。所以总步数 = 层数 × 每层步数 = O(log_(1/p) n) × O(1/(1-p)) = **O(log n)**。Redis 取 p=1/4，是内存和速度的折中。

## 面试场景 3：为什么 ZSet 用跳表而不是红黑树？（★经典）

🎤 面试官

ZSet 底层为什么用跳表？红黑树、B+ 树难道不行吗？

🧑‍💻 你

Redis 作者 antirez 在源码注释里给了**四个理由**（可以对着背）：

维度跳表红黑树

**实现复杂度**几十行核心代码，只有 forward 指针 + 层高需要旋转（左旋/右旋/双旋）、染色、修复平衡，几百行
**范围查询**底层就是有序链表，找到起点后*顺序遍历一次*需要中序遍历 + 栈或 Morris 遍历，每步跳兄弟节点，缓存不友好
**内存开销**平均每节点 `1 / (1-p) = 4/3` 层，即 ~1.33 个 forward 指针（p=1/4）每节点 3 指针（left/right/parent）+ 1 颜色位
**并发实现**无锁跳表相对好写（每层局部 CAS）无锁红黑树近乎不可能，锁粒度大

其中**范围查询**是决定性因素 —— `ZRANGE key 5 10`、`ZRANGEBYSCORE key 100 200` 是 ZSet 最常见操作。跳表底层链表天然按 score 有序，找到起点 O(log n) 后直接 `forward[0]` 一路走，全在缓存里；红黑树中序遍历要跨越父子祖孙节点，指针跳跃严重。

追问 跳表和 B+ 树有什么区别？为什么 MySQL 用 B+ 树、Redis 用跳表？

**本质区别是介质**：B+ 树为*磁盘*设计，每个节点大（一页 4KB-16KB），装几百个 key，目的是减少磁盘 IO 次数（树高压到 3-4 层就能装亿级数据）。跳表为*内存*设计，每个节点小、指针少，追求 CPU 缓存友好和实现简单。**磁盘 IO 是 ms 级、内存访问是 ns 级**，优化目标完全不同。

追问 Java 里 `ConcurrentSkipListMap` 也是跳表，它和 Redis 跳表有什么共同点/差异？

共同点：都是多层索引 + 期望 O(log n)。差异：**ConcurrentSkipListMap 用 CAS 实现无锁并发**（Doug Lea 手笔），支持高并发；Redis 是单线程模型不需要并发保护，实现更纯粹。另外 Redis 节点带 `backward` 指针支持反向遍历（`ZREVRANGE`），JDK 版没有反向指针。

## 面试场景 4：Redis 跳表的具体实现

🧑‍💻 你

看一下 Redis 源码 `server.h` 里的定义：

```
// 跳表容器
typedef struct zskiplist {
struct zskiplistNode *header, *tail;  // 头尾节点
unsigned long length;                  // 节点数（不含 header）
int level;                             // 当前最大层高
} zskiplist;

// 跳表节点
typedef struct zskiplistNode {
sds ele;                               // 成员对象（如用户名）
double score;                          // 分数（排序依据）
struct zskiplistNode *backward;        // 后退指针，反向遍历用
struct zskiplistLevel {
struct zskiplistNode *forward;     // 前进指针
unsigned long span;                // 到 forward 之间的节点数（跨度）
} level[];                             // 层数组（柔性数组）
} zskiplistNode;
```

三个关键字段值得强调：

- **`score`**：所有排序都按它。相同 score 时按 `ele` 字典序作为 tiebreaker。

- **`backward`**：单向后退指针（只在 Level 0），支撑 `ZREVRANGE`。

- **`span`**：*这一层*到 `forward` 之间跨了几个 Level 0 节点。用来算 **rank（排名）**—— `ZRANK`/`ZREVRANK` 沿路径累加 span 就能得到。

追问 ZSet 底层其实不是「只有跳表」，还有什么？

ZSet 底层是**跳表 + 哈希表**组合结构（`zset` struct）。跳表按 score 排序，支持范围查询和 rank；哈希表按 ele 索引，让 `ZSCORE key member` 达到 O(1)（否则跳表按 score 找 member 得 O(log n)）。两个结构指向同一份数据，内存换性能的经典设计。

## 面试场景 5：跳表的层高怎么定？

🧑‍💻 你

Redis 用**随机算法**决定新节点的层高，源码 `t_zset.c` 里的 `zslRandomLevel`：

```
#define ZSKIPLIST_MAXLEVEL 32       // 最大层高
#define ZSKIPLIST_P 0.25            // 升层概率

int zslRandomLevel(void) {
int level = 1;
while ((random()&0xFFFF) < (ZSKIPLIST_P * 0xFFFF))
level += 1;
return (level < ZSKIPLIST_MAXLEVEL) ? level : ZSKIPLIST_MAXLEVEL;
}
```

逻辑：**初始层高 1，每次以 25% 概率再升一层，直到失败或到 32**。这样保证：

- 75% 的节点只有 1 层

- 18.75% 的节点有 2 层（0.25 × 0.75）

- 4.69% 的节点有 3 层（0.25² × 0.75）

- ...

数学上：**期望层高 = 1/(1-p) = 1.33**，非常省内存。最大 32 层理论上支持 `(1/p)^32 = 4^32 ≈ 1.8 × 10^19` 个元素，远超 Redis 单 ZSet 容量。

追问 为什么 p 选 1/4 而不是教科书上常见的 1/2？

p=1/2 每层前进步数期望 2，层数期望 log_2(n)；p=1/4 每层前进步数期望 4/3，层数期望 log_4(n) = log_2(n)/2。**总步数期望**：p=1/2 是 2·log_2(n)，p=1/4 是 (4/3)·(log_2(n)/2) ≈ 0.67·log_2(n) —— *p=1/4 更快*！而且 p 越小层数越少，指针数少内存也省。Redis 选 1/4 是速度和空间的最优解。

## 面试场景 6：ziplist 是什么？为什么设计成这样？

🧑‍💻 你

**ziplist（压缩列表）**是 Redis 早期为*小集合*设计的紧凑数据结构，本质是一段连续内存里的*变长编码序列*。整体布局：

```
┌────────┬────────┬──────┬────────┬────────┬─────┬────────┬──────┐
│ zlbytes │ zltail │ zllen │ entry1 │ entry2 │ ... │ entryN │ zlend │
│  4字节  │  4字节  │ 2字节 │  变长  │  变长  │     │  变长  │ 1字节 │
└────────┴────────┴──────┴────────┴────────┴─────┴────────┴──────┘

每个 entry：
┌─────────┬──────────┬─────────┐
│ prevlen │ encoding │ content │
└─────────┴──────────┴─────────┘
```

三大设计目标：

- **连续内存**：CPU 缓存命中率高，遍历极快。

- **变长编码**：小整数用 1 字节，短字符串不预留空间，比 hashtable/quicklist *省内存好几倍*。

- **无指针开销**：不像链表每节点有 `next` 指针（8 字节），ziplist 每 entry 只额外多几字节 header。

典型场景：小 Hash（几十个字段）、小 List（几十个元素）、小 ZSet。**只要元素少且短，ziplist 的内存优势碾压 hashtable**。

追问 ziplist 的 `prevlen` 为什么用变长编码？

为了*反向遍历*。ziplist 需要支持从尾往头遍历（比如 `LRANGE key -1 -5`），所以每个 entry 要能算出前一个 entry 的起始地址。`prevlen` 存的就是前驱字节数：**前驱 < 254 字节时 `prevlen` 只用 1 字节；≥ 254 字节时用 5 字节**（1 字节标志位 0xFE + 4 字节长度）。这个变长编码省了绝大多数情况下的 4 字节，代价就是引出了「级联更新」这个大坑。

## 面试场景 7：ziplist 的致命问题 —— 级联更新（★经典）

🎤 面试官

ziplist 有个著名的性能问题叫「级联更新」，你能讲讲吗？

🧑‍💻 你

问题根源就在上一题说的 `prevlen` 变长编码。**假设一个 ziplist 里所有 entry 长度都是 253 字节**（`prevlen` 都用 1 字节）：

```
[entry1: 253B, prevlen=1B]
[entry2: 253B, prevlen=1B]  ← prevlen=1B 因为 entry1=253<254
[entry3: 253B, prevlen=1B]
...
```

现在我在中间插入一个 **300 字节**的新 entry：

1. 新 entry 长 300 > 254，所以*紧邻的下一个 entry*需要把 `prevlen` 从 1 字节扩到 5 字节。

2. 下一个 entry 的总长度从 253 变成 **257**（253 + 4）—— 也 > 254 了。

3. 于是*它的下一个 entry* 的 `prevlen` 也得从 1 变 5，长度也变成 257...

4. 连锁反应，可能**整个 ziplist 从插入点到末尾全部要扩容**，每次都 `memmove`。

最坏时间复杂度：**O(n²)**（每次扩容触发下一个 O(n) 的 memmove）。删除操作同理 —— 一个大 entry 删掉后，后续 entry 缩短，也可能反向级联。

虽然实际触发概率不高（要求节点长度密集在 250-254 的窄带里），但这是*理论上无法排除*的性能悬崖，让 ziplist 在大规模场景下不敢用。

陷阱 面试常问「级联更新真的是致命问题吗」—— 答案是「**概率低但确实存在**」。Redis 5 及以前团队做过很多补救（比如 `ziplistCascadeUpdate` 单独函数、限制 ziplist 元素数），但最终 7.0 干脆重新设计 listpack 换掉。这告诉我们：*「变长依赖链」是紧凑结构的原罪*。

## 面试场景 8：listpack 如何解决级联更新（Redis 7.0）

🧑‍💻 你

Redis 7.0 引入 **listpack** 全面替换 ziplist。核心改动：*每个节点在末尾多存一个「自身长度」字段*，不再依赖前驱。

```
ziplist entry:
┌─────────┬──────────┬─────────┐
│ prevlen │ encoding │ content │       ← prevlen 依赖前驱长度 → 级联更新
└─────────┴──────────┴─────────┘

listpack entry:
┌──────────┬─────────┬────────────┐
│ encoding │ content │ backlen    │       ← backlen 是「自己」的总长度
└──────────┴─────────┴────────────┘       ← 独立编码，与前后节点无关
```

为什么这么改就能解决级联？

- **反向遍历**：需要「从当前 entry 起始地址往前找到上一个 entry」。ziplist 靠*当前 entry 头部的 prevlen*；listpack 靠*上一个 entry 尾部的 backlen*（往前读几字节就知道上一个 entry 长度）。

- **插入/修改某节点**：只影响这个节点自己的 `backlen`，*不影响任何其他节点的编码*。级联更新彻底消失。

- **backlen 本身也是变长**：1-5 字节，但只反映自己长度，不引入依赖。

代价：**listpack 每个节点多花几字节存 backlen**，内存略增，但换来了操作可预测的 O(1) / O(n)，值得。

追问 listpack 相比 ziplist 每个节点具体多存了什么？

ziplist entry 是 `[prevlen][encoding][content]`，其中 prevlen 存*前驱*长度；listpack entry 是 `[encoding][content][backlen]`，backlen 存*自身*长度。反向遍历时 ziplist 从当前 entry 头部读 prevlen 就能跳到前一个；listpack 从当前 entry 起始地址往前 1 字节开始读，用 *变长解码*反向解析上一个 entry 的 backlen，就能得到上一个 entry 起始地址。**核心差别：ziplist 的元数据描述「前驱」，listpack 的元数据描述「自己」**。

追问 Redis 7.0 换 listpack 影响我们业务代码吗？

不影响。listpack 是*内部编码*，对外 API 完全一致。你的 `HGET`、`LPUSH`、`ZADD` 都不用改。只有一个可观察的变化：`OBJECT ENCODING key` 返回值从 `ziplist`/`quicklist`（内层）变成 `listpack`。相关配置项也换名：`hash-max-ziplist-entries` → `hash-max-listpack-entries`（旧名保留兼容）。

## 面试场景 9：quicklist —— List 的中间形态

🧑‍💻 你

Redis 3.2 之前，List 大就用**双向链表 linkedlist**、小就用 ziplist；3.2 后合并成 **quicklist**：

```
quicklist:  [head] ⇄ [node1] ⇄ [node2] ⇄ [node3] ⇄ [tail]
↓          ↓          ↓
ziplist    ziplist    ziplist
(若干     (若干     (若干
元素)     元素)     元素)
```

quicklist = **双向链表 + 每个节点挂一个 ziplist**。设计动机是平衡两个极端：

方案优点缺点

纯 linkedlist无级联更新，操作可预测每节点 3 指针（prev/next/value）+ SDS，指针占空间
纯 ziplist紧凑省内存元素多时级联更新爆炸，插入 O(n)
**quicklist**ziplist 分片限制大小 → 级联更新可控；链表指针分摊到多元素上 → 指针开销小实现复杂度上升

Redis 7.0 后 quicklist 里的 ziplist **换成 listpack**，彻底摆脱级联更新。

追问 quicklist 每个 ziplist / listpack 节点多大合适？

由 `list-max-listpack-size`（旧名 `list-max-ziplist-size`）控制。正数表示*元素个数*上限（如 128 就是每 listpack 装 128 个元素）；负数表示*字节数*上限：-1=4KB、-2=8KB、-3=16KB、-4=32KB、-5=64KB。**默认 -2（8KB）**，正好一个内存页附近，兼顾 CPU 缓存和空间。

## 面试场景 10：紧凑结构的编码转换阈值

🎤 面试官

Redis 的 Hash/List/ZSet 什么时候用 listpack、什么时候转成 hashtable/skiplist？

🧑‍💻 你

每种类型都有两个阈值 —— *元素数*和*单元素长度*，任一超过就升级。Redis 7.x 配置：

类型小编码大编码元素数阈值元素长度阈值

Hashlistpackhashtable`hash-max-listpack-entries=128``hash-max-listpack-value=64`
Listlistpack (内嵌 quicklist)quicklist`list-max-listpack-size=-2`（8KB/节点）
ZSetlistpackskiplist`zset-max-listpack-entries=128``zset-max-listpack-value=64`
Set (整数)intsethashtable / listpack`set-max-intset-entries=512`-
Set (混合)listpackhashtable`set-max-listpack-entries=128``set-max-listpack-value=64`

三个关键点：

1. **转换单向不可逆**：即使后来元素数降回阈值下，也*不会退回 listpack*。因为频繁转换代价太大。

2. **阈值可调**：`CONFIG SET hash-max-listpack-entries 256` 立即生效。但不建议调太大，listpack 的 O(n) 操作在几百元素后就明显慢于 hashtable 的 O(1)。

3. **阈值判断在每次写入时**：`HSET`/`ZADD` 后检查，超过就调用 `hashTypeConvert`/`zsetConvert` 转结构。

追问 为什么 Set 元素全是整数用 intset 而不是 listpack？

**intset 更紧凑**：它是一段连续内存的*有序整数数组*，只存整数值，不需要类型标记（listpack 每个 entry 都要 encoding 字节说明是整数还是字符串）。而且有序数组支持*二分查找 O(log n)*，比 listpack 线性扫描 O(n) 快。intset 还会动态选择 int16/int32/int64 编码（`encoding` 字段），进一步省空间。只有加入非整数元素时才被迫转成 hashtable / listpack。

追问 为什么阈值转换是「不可逆」的？

如果可逆，会出现*抖动场景*：假设 hash 元素在 128 上下反复增删，每次触发结构转换，都是全量 `rehash`（listpack ↔ hashtable 都是 O(n)）。工程上这个代价不可接受。所以**只升不降**是刻意的权衡 —— 用户偶尔碰阈值只付一次转换成本。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：Java 手写一个简单跳表

```
import java.util.Random;

public class MySkipList {
private static final int MAX_LEVEL = 16;
private static final double P = 0.25;
private final Random rnd = new Random();

static class Node {
int val;
Node[] forward;
Node(int val, int level) {
this.val = val;
this.forward = new Node[level + 1];
}
}

private final Node head = new Node(Integer.MIN_VALUE, MAX_LEVEL);
private int level = 0;

private int randomLevel() {
int lv = 0;
while (rnd.nextDouble() < P && lv < MAX_LEVEL - 1) lv++;
return lv;
}

public boolean search(int target) {
Node cur = head;
for (int i = level; i >= 0; i--) {
while (cur.forward[i] != null && cur.forward[i].val < target) {
cur = cur.forward[i];  // 当前层前进
}
}
cur = cur.forward[0];
return cur != null && cur.val == target;
}

public void insert(int val) {
Node[] update = new Node[MAX_LEVEL];
Node cur = head;
for (int i = level; i >= 0; i--) {
while (cur.forward[i] != null && cur.forward[i].val < val) {
cur = cur.forward[i];
}
update[i] = cur;  // 记录每层的插入位置
}
int newLevel = randomLevel();
if (newLevel > level) {
for (int i = level + 1; i <= newLevel; i++) update[i] = head;
level = newLevel;
}
Node node = new Node(val, newLevel);
for (int i = 0; i <= newLevel; i++) {
node.forward[i] = update[i].forward[i];
update[i].forward[i] = node;
}
}

public static void main(String[] args) {
MySkipList sl = new MySkipList();
for (int i : new int[]{5, 10, 15, 20, 30, 40, 50}) sl.insert(i);
System.out.println(sl.search(30));  // true
System.out.println(sl.search(35));  // false
}
}
```

观察点：`search` 和 `insert` 都是「**逐层前进直到大于目标就下降**」的同一模式。整个跳表核心不到 50 行。

### 验证 2：用 `OBJECT ENCODING` 观察编码转换

```
# 小 Hash → listpack
127.0.0.1:6379> HSET user:1 name alice age 20
(integer) 2
127.0.0.1:6379> OBJECT ENCODING user:1
"listpack"

# 加入超过 64 字节的值 → 立刻转 hashtable
127.0.0.1:6379> HSET user:1 bio "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
(integer) 1
127.0.0.1:6379> OBJECT ENCODING user:1
"hashtable"

# 即使把大值删掉，编码也不会退回 listpack
127.0.0.1:6379> HDEL user:1 bio
(integer) 1
127.0.0.1:6379> OBJECT ENCODING user:1
"hashtable"       ← 转换不可逆！
```

### 验证 3：观察 ZSet 编码切换

```
# 小 ZSet 用 listpack
127.0.0.1:6379> ZADD leaderboard 100 alice 200 bob 300 carol
(integer) 3
127.0.0.1:6379> OBJECT ENCODING leaderboard
"listpack"

# 加超过 128 个元素 → 转 skiplist
127.0.0.1:6379> EVAL "for i=1,200 do redis.call('ZADD', KEYS[1], i, 'm'..i) end return 1" 1 leaderboard
(integer) 1
127.0.0.1:6379> OBJECT ENCODING leaderboard
"skiplist"

# 手动调阈值让转换晚点发生
127.0.0.1:6379> CONFIG SET zset-max-listpack-entries 500
OK
```

### 验证 4：模拟级联更新（伪代码演示原理）

```
// 模拟 ziplist 中「插入长节点触发级联更新」的最坏路径
// 真实 ziplist 是 C 里的 memmove，这里用数组示意

int[] entryLens = {253, 253, 253, 253, 253};  // 每个 entry 都是 253 字节（临界值）
int[] prevlenBytes = {1, 1, 1, 1, 1};         // prevlen 都用 1 字节

// 在开头插入一个 300 字节的新节点
int newLen = 300;

// 从头开始检查每个后续 entry 是否需要扩容 prevlen
int prevActualLen = newLen;
for (int i = 0; i < entryLens.length; i++) {
boolean needExpand = (prevActualLen >= 254) && (prevlenBytes[i] == 1);
if (needExpand) {
prevlenBytes[i] = 5;      // 扩到 5 字节
entryLens[i] += 4;         // 当前 entry 也变长 4 字节
System.out.println("Entry " + i + " 触发 prevlen 扩容，新长度 = " + entryLens[i]);
prevActualLen = entryLens[i];  // 继续影响下一个
} else {
break;  // 没触发就停止
}
}
// 输出：所有 5 个 entry 全部触发扩容 —— 就是级联更新
// 真实场景下每次扩容都要 memmove 后续所有字节，最坏 O(n²)
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 跳表查找/插入/删除的时间复杂度是多少？为什么？</summary>

期望 **O(log n)**。核心推导：升层概率 p，每层期望前进 `1/(1-p)` 步，总层数期望 `log_{1/p}(n)`，相乘得 O(log n)。最坏 O(n)（所有节点层高 1），但概率极小。

</details>

<details>

<summary>Q2 ZSet 底层完整结构是什么？只有跳表吗？</summary>

**跳表 + 哈希表**。跳表按 score 排序支持 `ZRANGE`/`ZRANK`；哈希表按 member 索引让 `ZSCORE` 达到 O(1)。两者指向同一份数据，是内存换性能的组合。（小 ZSet 用 listpack，超阈值才转成这种组合。）

</details>

<details>

<summary>Q3 ziplist 的级联更新最坏时间复杂度是多少？触发条件是什么？</summary>

最坏 **O(n²)**。触发条件：连续多个 entry 长度密集在 250-254 字节的窄带里（`prevlen` 都是 1 字节），此时插入/修改/删除一个跨过 254 边界的 entry，会导致后续 entry 的 `prevlen` 从 1 字节扩到 5 字节，自身长度也变，级联触发下一个 entry 扩容。

</details>

<details>

<summary>Q4 listpack 和 ziplist 的核心结构差别是什么？为什么这个差别能解决级联更新？</summary>

ziplist entry 结构 `[prevlen][encoding][content]`，`prevlen` 描述*前驱*长度；listpack entry 结构 `[encoding][content][backlen]`，`backlen` 描述*自身*长度。因为每个节点的元数据只反映自己，任何节点的插入/修改都不会影响其他节点编码，级联依赖链被彻底切断。

</details>

<details>

<summary>Q5 Redis 7.x 里 Hash 从 listpack 转 hashtable 的两个阈值是什么？转换后能退回吗？</summary>

两个阈值：`hash-max-listpack-entries=128`（字段数）和 `hash-max-listpack-value=64`（单字段字节数），任一超过就转 hashtable。**转换不可逆** —— 即使后来元素数降回阈值下，也不会自动回退，避免抖动场景下反复重构。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Redis 源码 · `t_zset.c` —— `zslRandomLevel`、`zslInsert` 的官方实现

- Redis 源码 · `listpack.c` —— listpack 的紧凑实现

- William Pugh 1990 · Skip Lists: A Probabilistic Alternative to Balanced Trees —— 跳表原始论文

#### 🔗 关联课件

-  —— 本课的上游，讲了 5 种类型如何选择底层编码

-  —— 上一课

-  —— 下一课，从内存结构走向磁盘

#### 🧭 下一课预告

Lesson 0055：**Redis 持久化 RDB & AOF & 混合模式** —— 面试中*频次和难度双高*的一课：什么时候会 fork？AOF rewrite 时 buffer 怎么处理？重启用 RDB 还是 AOF？混合持久化到底是什么？我们下节课把持久化的每个细节都捞出来。

💬 有任何疑问 —— 「跳表的 span 字段怎么算 rank？」「listpack 反向遍历的 backlen 变长解码具体怎么写？」「面试真被问过为什么 Set 不用跳表？」—— 直接问我。我是你的老师，也是你的追问陪练。


