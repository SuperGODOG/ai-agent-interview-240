> Lesson 0043 · 阶段六 · MySQL · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑 SQL · 5 道自测 · 8 个追问

# 0043 · MySQL 索引详解：B+ 树 & 聚簇/非聚簇 & 回表 & 覆盖索引 & 最左前缀

MySQL 面试三大硬骨头：**索引、事务、锁**。索引排在第一，因为它是数据库能跑到毫秒级的物理基础，也是 SQL 优化的第一战场。能*手画 B+ 树结构*、*说清聚簇/非聚簇/回表/覆盖索引*、*回答最左前缀原则的边界情况* —— 这四件事讲明白，索引这块基本过关。

本课覆盖  的全部核心考点。索引*失效*场景和 `EXPLAIN` 各字段的深度解读留给下节  和 。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 为什么 InnoDB 用 B+ 树而不用 B 树？也不用红黑树？</summary>

核心是**降低磁盘 IO 次数**。B+ 树把 data 全部下沉到叶子节点，非叶节点只放 key + 指针 —— 一页 16 KB 可以塞下上千个索引项，树高只需 3-4 层就能撑起 20 亿行数据。B 树非叶节点也存 data，一页装的 key 少，树就高；红黑树/AVL 每个节点只有一个 key，磁盘 IO 更是灾难（数据一多树高十几层）。而且 B+ 树叶子节点用**双向链表**相连，范围查询直接顺着叶子扫，B 树做不到。第 2 题细讲。

</details>

<details>

<summary>Q0.2 主键索引和普通索引，查询过程有什么区别？</summary>

InnoDB 里主键索引是**聚簇索引**：叶子节点直接存整行数据，找到主键就拿到全部字段。普通（辅助/二级）索引是**非聚簇索引**：叶子节点只存主键值 —— 想拿完整数据必须再走一次主键索引，这个过程叫**回表**。如果 `SELECT` 的字段正好都在辅助索引里（比如 `SELECT id, name` 而索引就是 `(name)`），就不用回表，这叫**覆盖索引**，`EXPLAIN` 的 `Extra` 会显示 `Using index`。第 4、5 题细讲。

</details>

## 面试场景 1：索引是什么？为什么要用？

🎤 面试官

你能用一分钟解释一下什么是索引？为什么要建索引？

🧑‍💻 你

**索引（Index）**是存储引擎用来*快速找到数据*的一种**排序好的数据结构**。类比就是新华字典的目录：不建索引，全表扫描相当于把字典从第一页翻到最后一页；建了索引，先翻目录定位到「M-开头」再跳到对应页，几次翻页搞定。

本质是**空间换时间** —— 索引文件本身要占磁盘，写入/更新时也要维护 B+ 树结构（有额外开销），但换来查询从 O(n) 全表扫降到 O(log n) 的树查找。

- **优点**：查询快；唯一索引能保证数据唯一；`ORDER BY`/`GROUP BY` 可以直接利用索引有序，省掉 `filesort`。

- **缺点**：占磁盘空间；`INSERT`/`UPDATE`/`DELETE` 变慢（要维护 B+ 树）；索引设计不当会失效或被优化器嫌弃。

追问 索引一定能让查询变快吗？有没有反例？

不一定。两个反例：**(1) 数据量太小**（几百行），全表扫描比走索引 + 回表还快，优化器会直接放弃索引；**(2) 查询结果集占比过大**（超过 20%-30%），走非聚簇索引意味着大量随机 IO 回表，还不如一次顺序扫描全表。优化器基于*成本估算*（Cost-Based Optimizer, CBO）来决定用不用索引，成本高的话它会自己弃用你辛苦建的索引。

## 面试场景 2：为什么 InnoDB 用 B+ 树，不用 B 树 / 红黑树 / Hash？（★经典）

🎤 面试官

MySQL InnoDB 的索引底层是 B+ 树。为什么选 B+ 树？B 树、红黑树、Hash 表都不行吗？

🧑‍💻 你

核心原则：**数据库索引的第一优化目标是「最大程度减少磁盘 IO」**。磁盘随机 IO 一次约 10 ms，内存访问 100 ns —— 差 5 个数量级。所以数据结构选型要看两点：*树高低不低*、*顺序访问友好不友好*。

候选查找复杂度缺点是否被选

Hash 表
O(1)
**不支持范围查询**（哈希后完全打散，无有序性），不支持 `ORDER BY`，不支持模糊匹配，有哈希冲突
❌

二叉搜索树 / AVL
O(log n)
每个节点只有一个 key —— 100 万数据树高约 20 层，等于 20 次磁盘 IO；AVL 严格平衡插入还要频繁旋转
❌

红黑树
O(log n)
同上：一个节点一个 key，磁盘 IO 太多。红黑树是*内存*结构（HashMap、TreeMap 用它），不适合磁盘
❌

B 树
O(log n)
非叶节点也存 data，一页 16 KB 装的 key 就少了，树高比 B+ 树高；叶子之间没有链表，范围查询要回溯
❌

**B+ 树**
O(log n) 稳定
—
✅

B+ 树的三大杀手锏：**(1) 非叶节点只存 key + 指针**，一页能塞下上千个索引项，度数（fan-out）极大，树高极低（3-4 层撑 20 亿）；**(2) 数据全部存在叶子节点**，每次查询都走到叶子，查询路径长度稳定；**(3) 叶子节点用双向链表连接**，范围查询（`BETWEEN`、`>`、`ORDER BY`）沿着链表扫就完事。

追问 InnoDB 一页大小默认多少？为什么是 16 KB？

默认 **16 KB**（可用 `innodb_page_size` 参数改，一般不动）。为什么是 16 KB：操作系统的一页是 4 KB，16 KB 正好是 **4 KB 的整数倍**（一次 IO 读一个页正好对齐 OS 的 4 个页，不浪费）；同时 16 KB 又能塞下足够多的索引项 —— 假设一条索引项占 16 字节（key 8B + 指针 8B），一页可存 **16384 / 16 ≈ 1000** 个（更精确的估算是 1170 个）索引项。这样 **3 层 B+ 树可存 1170 × 1170 × 16（叶子节点每页存的数据行）≈ 2000 万行，更常见的说法是「3 层撑 20 亿」（假设叶子每页装的数据行更少或索引层数更多）**。也就是说，一张几千万行的表，任何一次主键查询最多 3 次磁盘 IO。

追问 Hash 索引为什么不能范围查询？

因为哈希函数会把原本有序的 key 完全**打散到不同的桶**。原来 `score = 1, 2, 3, 4` 是相邻的，哈希后可能落到桶 3、桶 7、桶 1、桶 5 —— 完全失去了有序性。范围查询 `WHERE score BETWEEN 1 AND 100` 只能扫全部桶挨个比较，比全表扫描还慢。所以 Hash 索引只适合等值查询（`WHERE key = ?`），MySQL 里只有 Memory 引擎默认用 Hash，InnoDB 有个「自适应哈希索引」也只是内部对热点 key 加速等值查询。

## 面试场景 3：B+ 树 vs B 树的关键区别

🧑‍💻 你

三条最本质的区别：

```
┌────────────── B 树 ──────────────┐
│      [30 | 60]                   │
│     /    |    \                  │  非叶节点也存 data
│  [10,20] [40,50] [70,80]         │  叶子之间无链表连接
│  ↑ 每个节点都存完整数据行         │
└──────────────────────────────────┘

┌────────────── B+ 树 ─────────────┐
│      [30 | 60]                   │  非叶节点只存 key + 指针
│     /    |    \                  │
│  [10,20] [40,50] [70,80]         │
│    ⇄        ⇄        ⇄            │  ← 叶子双向链表
│  完整 data 只在叶子              │
└──────────────────────────────────┘
```

1. **数据只在叶子节点**：B 树每个节点都存 data，B+ 树只有叶子存 data，非叶节点全是 key + 指针 —— 一页能塞下的 key 更多，树高更低，磁盘 IO 更少。

2. **叶子节点双向链表相连**：B+ 树范围查询极快，找到起点后沿着链表往后扫；B 树范围查询要中序遍历，需要回溯到父节点。

3. **查询效率稳定**：B+ 树任何查询都要走到叶子，路径长度一致 = O(log n) 稳定；B 树可能在非叶节点就命中，看似有时更快，但整体不如 B+ 树可预测（对数据库来说，可预测比偶尔快更重要）。

追问 为什么 B+ 树的叶子节点是双向链表而不是单向？

为了支持**倒序范围查询**。`ORDER BY id DESC LIMIT 100` 直接从最右叶子往前扫；`WHERE id BETWEEN 100 AND 200` 可以从两端往中间扫。单向链表只能从头往尾走一条路，倒序就要全扫再反转，代价大。MySQL 8.x 还进一步支持了「降序索引」（真的按倒序存），把倒序查询做得更彻底。

## 面试场景 4：聚簇索引 vs 非聚簇索引（★核心）

🎤 面试官

解释一下聚簇索引和非聚簇索引的区别。InnoDB 的主键索引属于哪种？MyISAM 呢？

🧑‍💻 你

关键差异在**叶子节点存的是什么**：

类型别名叶子存什么一张表能有几个典型例子

**聚簇索引** Clustered Index
主键索引
*整行数据*
只能 1 个（数据物理上按它排序）
InnoDB 的主键（`PRIMARY KEY`）

**非聚簇索引** Secondary Index
二级索引、辅助索引
*主键值*（InnoDB）或*数据行地址*（MyISAM）
可以多个
InnoDB 的普通索引、唯一索引、联合索引

用一张图直观感受：

```
InnoDB 聚簇索引（主键 id）：
[B+ 树根]
│
...(中间节点)
│
[叶子节点]  ← 直接存 (id=1, name='Tom', age=20, city='SZ') 完整一行

InnoDB 非聚簇索引（比如给 name 建的索引）：
[B+ 树根]
│
...(中间节点)
│
[叶子节点]  ← 只存 (name='Tom', id=1)   —— 拿到 id=1 后要「回表」

MyISAM 索引（无聚簇）：
[B+ 树根]
│
[叶子节点]  ← 存 (id=1, 数据文件地址 0x2A8F)
数据行存在独立的 .MYD 文件里
主键和二级索引结构一样，都需要按地址去数据文件读
```

**InnoDB 主键就是聚簇索引**（`.ibd` 文件里索引和数据是一体的，B+ 树叶子=数据行）；**InnoDB 二级索引都是非聚簇**，叶子存主键值。**MyISAM 全部索引都是非聚簇**，主键和普通索引结构完全对称，叶子都存数据文件里的物理地址。

追问 MyISAM 是聚簇还是非聚簇？

**MyISAM 全部索引都是非聚簇**。MyISAM 的数据文件（`.MYD`）和索引文件（`.MYI`）是分开的两个文件，所有索引（包括主键索引）的叶子节点存的都是*数据行在 .MYD 文件里的物理地址*。所以 MyISAM 的主键索引和二级索引结构完全对称 —— 主键并没有特殊地位，任何一次查询都要通过地址去 .MYD 文件二次读取，相当于「所有索引都要回表」。

追问 一张 InnoDB 表如果没建主键会怎样？

InnoDB 必须有聚簇索引。如果你没定义 `PRIMARY KEY`，它会按以下顺序找：**(1) 找第一个非空唯一索引 `NOT NULL UNIQUE`** 顶替；**(2) 都没有的话**，InnoDB 会*偷偷生成一个 6 字节的隐藏主键 `_rowid`* 作为聚簇索引。这就是为什么面试常说「InnoDB 表一定要显式建主键」——用自增 `BIGINT` 主键最省事，避免 InnoDB 用长字符串或隐藏 `_rowid`（不受你控制）。

## 面试场景 5：回表 & 覆盖索引（★核心）

🎤 面试官

什么叫回表？什么叫覆盖索引？`EXPLAIN` 里怎么看出来是覆盖索引？

🧑‍💻 你

**回表（Back to Table）**：走非聚簇索引拿到主键值之后，*再走一次聚簇索引*去取整行数据的过程。「两次 B+ 树查找」。

**覆盖索引（Covering Index）**：`SELECT` 要的字段*全部都在辅助索引里*，不需要回表，只读索引就够了。

```
-- 假设 user 表：id 是主键，name 上建了普通索引 idx_name

-- 场景 A：回表
SELECT * FROM user WHERE name = 'Tom';
-- 1. 走 idx_name 找到 (name='Tom', id=42)
-- 2. 拿到 id=42 后走聚簇索引（主键索引）找到整行 —— 回表

-- 场景 B：覆盖索引
SELECT id, name FROM user WHERE name = 'Tom';
-- idx_name 的叶子已经包含了 (name, id) —— 不用回表
-- EXPLAIN 的 Extra 会显示 Using index

-- 场景 C：联合索引 (name, age) 的覆盖
SELECT name, age FROM user WHERE name = 'Tom';
-- idx_name_age 叶子存 (name, age, id) —— name 和 age 全在，不回表
```

验证方法：`EXPLAIN` 结果里 `Extra` 列出现 **`Using index`**，就是走了覆盖索引；如果显示 `Using where; Using index condition` 那是索引下推（下面第 7 题讲）。

追问 为什么 `SELECT *` 通常要回表，`SELECT id, name`（name 已在辅助索引里）就不用回表？

`SELECT *` 要拿出*所有字段*，除非你的辅助索引覆盖了所有字段（几乎不可能，一般表都有十几列），否则必须回表去聚簇索引拿完整行。而 `SELECT id, name` 只要 id 和 name —— 假如 name 有辅助索引 `idx_name(name)`，因为 InnoDB 的二级索引叶子本来就存了主键 id，所以 (name, id) 两列全在索引里，不用回表。这就是**「查询字段最小化」原则**的核心动机 —— 拒绝无脑 `SELECT *`，让覆盖索引成为可能。

追问 联合索引 `(a, b, c)` 上执行 `SELECT a, b, c FROM t WHERE a = 1` 是不是覆盖索引？

是。联合索引 `(a, b, c)` 的叶子节点里存的是 `(a, b, c, 主键)`，四列全在索引里。查询只要 `a, b, c`，直接从索引读就完事，不用回表。`EXPLAIN` 会显示 `Extra: Using index`。这也是为什么很多面试题问「怎么优化 `SELECT xxx WHERE ...`」时，标准答案就是「加一个联合索引把 SELECT 的字段全覆盖进去」。

## 面试场景 6：最左前缀原则（★核心）

🎤 面试官

什么是最左前缀原则？联合索引 `(a, b, c)` 上，`WHERE b = 1 AND c = 2` 能走索引吗？

🧑‍💻 你

**最左前缀原则**：联合索引 `(a, b, c)` 在 B+ 树里是*先按 a 排，a 相同再按 b 排，b 相同再按 c 排*。它相当于一次性建了三个索引：`(a)`、`(a, b)`、`(a, b, c)`。查询 `WHERE` 必须*从最左字段 a 开始连续使用*，才能走索引。

具体到 `WHERE b = 1 AND c = 2` —— **不能走索引**。原因：整棵树是按 a 分区的，缺了 a 就无从下手，只能全表扫。

完整案例（索引 `(a, b, c)`）：

SQL是否走索引说明

`WHERE a=1 AND b=1 AND c=1`✅ 全走三列全用上
`WHERE a=1 AND b=1`✅ 走 a, b用了最左两列
`WHERE a=1`✅ 只走 a最左单列
`WHERE a=1 AND c=1`⚠️ 只走 ab 缺失，c 无法用索引，只能拿 a=1 的结果再过滤 c
`WHERE b=1 AND c=1`❌ 不走缺最左 a，整个索引失效
`WHERE c=1`❌ 不走同上
`WHERE b=1 AND a=1 AND c=1`✅ 全走优化器会自动重排成 a, b, c，别怕写错顺序
`WHERE a=1 AND b>10 AND c=1`⚠️ 走 a, bb 是范围查询，索引在 b 之后中断，c 无法用

一句话：**从最左开始连续、遇到范围查询（`>` `<` `BETWEEN`）停止**。等值查询（`=` `IN`）不会中断，范围查询之后的列就不走索引了。

追问 联合索引 `(a, b, c)` 中 `WHERE a = 1 AND c = 2` 到底能走多少？为什么？

能走 **a 那一段**，但*不能走 c*。因为整棵 B+ 树是「按 a 排序，a 相同再按 b 排序，b 相同再按 c 排序」—— 缺了 b，c 在树里就是完全无序的。走完 a=1 拿到一堆候选记录后，c=2 的判断只能*逐行过滤*（Server 层的 Using where，MySQL 5.6+ 有 ICP 也可以在存储引擎层过滤，见第 7 题）。`EXPLAIN` 会显示 `key = idx_abc` 但 `key_len` 只等于 a 那一列的长度，说明索引只用到了第一列。

追问 那 `WHERE b = 1 AND c = 2` 呢？完全不能走索引？

正常情况下不能。B+ 树按 a 分区，跳过 a 就没有入口。**但有个例外**：MySQL 8.0.13+ 引入了 **Index Skip Scan（索引跳跃扫描）**，优化器会自动把它拆成 `WHERE a IN (所有 a 的可能值) AND b = 1 AND c = 2` 来尝试走索引 —— 但仅当 a 列的*基数很低*（比如 a 是性别只有 2 种）时才有用，大部分场景还是老实按最左前缀来。所以面试官问这题，标准答案还是「不走」，除非他特意问 8.0 新特性。

## 面试场景 7：索引下推 ICP（Index Condition Pushdown）

🎤 面试官

你知道索引下推吗？它解决什么问题？

🧑‍💻 你

**索引下推（Index Condition Pushdown, ICP）** 是 MySQL 5.6 引入的优化：把原本要在 *Server 层*做的 `WHERE` 过滤，「下推」到*存储引擎层*，让引擎在读索引时就直接过滤掉不满足条件的记录，**减少回表次数**。

举个例子。联合索引 `(zipcode, birthdate)`，查询：

```
SELECT * FROM user
WHERE zipcode = '431200' AND MONTH(birthdate) = 3;
```

因为 `MONTH(birthdate)` 是对 birthdate 加了函数（破坏了索引有序性），联合索引 `(zipcode, birthdate)` 只有 zipcode 这一列能真正走索引。

```
【没有 ICP 时】（MySQL 5.5 及以前）
引擎层：扫索引，拿到所有 zipcode='431200' 的主键（假设 1000 条）
↓
引擎层：拿主键回表 1000 次，取完整行数据
↓
Server 层：再判断 MONTH(birthdate)=3 —— 假设只有 100 条满足
➜ 白白回表了 900 次

【开启 ICP 后】（MySQL 5.6+，默认开）
引擎层：扫索引，拿到 zipcode='431200' 的记录
↓
引擎层：在索引里直接判断 MONTH(birthdate)=3 —— 满足才继续
↓
引擎层：只对 100 条满足条件的回表
➜ 回表次数从 1000 降到 100
```

验证：`EXPLAIN` 的 `Extra` 出现 **`Using index condition`** 就是启用了 ICP。可以用 `SET optimizer_switch = 'index_condition_pushdown=off';` 关掉对比效果。

追问 ICP 只对二级索引有效吗？为什么？

InnoDB 里 ICP **只对二级索引生效**。原因很直观：聚簇索引的叶子本来就是数据行，没有「回表」这回事 —— ICP 的价值就是「少回表」，聚簇索引根本不回表，没什么可优化的。所以 ICP 只在 `type = range / ref / eq_ref / ref_or_null` 且使用*二级索引*的执行计划里出现。

## 面试场景 8：索引的分类

🧑‍💻 你

按**应用维度**分（面试常考）：

类型特点能否 NULL一张表几个

**主键索引** `PRIMARY KEY`加速 + 唯一约束，InnoDB 里是聚簇索引❌ 不允许 NULL1 个
**唯一索引** `UNIQUE KEY`加速 + 唯一约束✅ 允许 NULL（且多个 NULL 不冲突）多个
**普通索引** `KEY` / `INDEX`只加速查询✅多个
**联合索引** `KEY(a, b, c)`多列组合，遵循最左前缀✅多个
**全文索引** `FULLTEXT`对文本分词后索引，用 `MATCH ... AGAINST` 查—多个
**空间索引** `SPATIAL`对 `GEOMETRY` 类型的地理数据建 R-Tree❌多个
**前缀索引** `KEY(name(10))`只索引字符串前 N 个字符，省空间✅多个

按**存储方式**分：**聚簇索引**（InnoDB 主键）vs **非聚簇索引**（其他所有）。按**数据结构**分：B+ Tree（默认）、Hash（Memory 引擎）、R-Tree（空间索引）、Full-Text（倒排索引）。

追问 全文索引为什么生产上很少用？

三个原因：**(1) 中文分词能力弱**，早期 MySQL FULLTEXT 只支持英文空格分词，中文得靠 ngram 插件（5.7+），效果远不如专业分词器；**(2) 性能和相关度打分不如专业搜索引擎**，Elasticsearch / Solr 有 TF-IDF、BM25、向量检索等成熟能力；**(3) 更新代价大**，全文索引维护成本高，写多的场景不合适。生产上标准做法是*MySQL 存原始数据 + Elasticsearch 建全文索引*，用 canal / debezium 同步。

## 面试场景 9：哪些字段适合建索引？

🧑‍💻 你

- **WHERE 里频繁作为过滤条件的字段**：这是索引最直接的价值。

- **ORDER BY / GROUP BY 用到的字段**：索引本身有序，能省掉 `Using filesort` 和临时表。

- **JOIN ON 的字段**：驱动表和被驱动表关联字段建索引能把嵌套循环 JOIN 的复杂度大幅降低。

- **区分度高（cardinality 高）的字段**：例如身份证号、手机号、UUID —— 每条数据几乎唯一，索引筛选效果好。区分度用 `COUNT(DISTINCT col) / COUNT(*)` 衡量，越接近 1 越好。反例是「性别」只有 M/F 两个值，区分度约 0.5，建索引后过滤一半数据还是很多，优化器可能直接放弃。

- **字符串很长的字段用前缀索引**：比如 `email` 长度动辄 50+ 字符，建 `KEY idx_email(email(10))` 只索引前 10 个字符，省空间又够用。

- **优先建联合索引，少建单列索引**：一个联合索引 `(a, b, c)` 顶三个单列索引，还能玩覆盖索引；单表索引数量控制在 5 个以内，太多会拖慢写入。

## 面试场景 10：哪些情况不该建索引？

🧑‍💻 你

- **区分度极低的字段**：性别、状态位（0/1）、is_deleted —— 只有 2-3 个值，索引筛选后还剩一大半数据，优化器不会用。

- **频繁 UPDATE 的字段**：每次更新都要维护 B+ 树（可能触发页分裂），写入代价大幅上升。典型：`view_count` 这种每次访问都 +1 的字段，绝对别建索引。

- **很少作为查询条件的字段**：索引本身占空间，从不查询就是纯浪费。

- **表数据量小**（几百行以内）：全表扫描比走索引还快，MySQL 优化器直接忽略索引。

- **NULL 值极多的字段**：索引对 NULL 的处理比较特殊，很多情况下 `WHERE col IS NULL` 优化器不会走索引。设计表时能设 `NOT NULL DEFAULT ''` / `DEFAULT 0` 就别用 NULL。

**反面案例**：某系统建了 15 个索引结果每次 `INSERT` 都要维护 15 棵 B+ 树，写入 TPS 从 5000 掉到 500 —— 索引不是越多越好，是*好钢用在刀刃上*。

陷阱 前面追问已经出现过一部分「索引失效」场景，但完整的 **索引失效 10 种情况**（对索引列加函数、隐式类型转换、前置 `%` 模糊查询、`OR` 条件、`!=`/`NOT IN`、字符集不一致等）留到  那节专门讲，是独立高频考点。

## 💻 代码验证（打开 MySQL 跑一遍）

### 验证 1：建表 + 联合索引 + EXPLAIN 观察最左前缀

```
-- 建学生表
CREATE TABLE student (
id INT PRIMARY KEY AUTO_INCREMENT,
name VARCHAR(50) NOT NULL,
class VARCHAR(50) NOT NULL,
score INT NOT NULL,
KEY idx_name_class (name, class)          -- 联合索引 (name, class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO student(name, class, score) VALUES
('Alice', 'Class1', 88), ('Bob', 'Class2', 76),
('Cindy', 'Class1', 92), ('David', 'Class3', 65);

-- ✅ 走索引（用了最左字段 name）
EXPLAIN SELECT * FROM student WHERE name = 'Alice' AND class = 'Class1';
-- 期望：key = idx_name_class, key_len 包含 name + class 两列长度

-- ✅ 走索引，但只用到 name
EXPLAIN SELECT * FROM student WHERE name = 'Alice';
-- 期望：key = idx_name_class, key_len 只等于 name 一列长度

-- ❌ 不走索引（缺最左 name）
EXPLAIN SELECT * FROM student WHERE class = 'Class1';
-- 期望：key = NULL, type = ALL（全表扫描）
```

### 验证 2：覆盖索引 vs 回表

```
-- 假设已有 student 表 + 索引 idx_name_class (name, class)

-- 场景 A：覆盖索引（只 SELECT 索引里已有的列）
EXPLAIN SELECT name, class FROM student WHERE name = 'Alice';
-- 期望：Extra = Using index   ← 覆盖索引，不回表

-- 场景 B：需要回表（SELECT * 要拿 score，score 不在索引里）
EXPLAIN SELECT * FROM student WHERE name = 'Alice';
-- 期望：Extra 里没有 Using index，需要回表拿 score

-- 场景 C：SELECT id 也是覆盖索引（因为 InnoDB 二级索引叶子存了主键 id）
EXPLAIN SELECT id, name FROM student WHERE name = 'Alice';
-- 期望：Extra = Using index
```

### 验证 3：索引下推 ICP 观察

```
CREATE TABLE user_icp (
id INT PRIMARY KEY AUTO_INCREMENT,
zipcode VARCHAR(10) NOT NULL,
birthdate DATE NOT NULL,
username VARCHAR(50),
KEY idx_zip_birth (zipcode, birthdate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO user_icp(zipcode, birthdate, username) VALUES
('431200', '1990-03-15', 'A'), ('431200', '1988-07-22', 'B'),
('431200', '1995-03-08', 'C'), ('518000', '1990-03-01', 'D');

-- ICP 生效场景：MONTH(birthdate) 破坏了 birthdate 的索引有序性
-- 但 zipcode 精确匹配 + birthdate 的月份过滤可以下推到引擎层
EXPLAIN SELECT * FROM user_icp
WHERE zipcode = '431200' AND MONTH(birthdate) = 3;
-- 期望：Extra = Using index condition   ← ICP 生效

-- 对比：关掉 ICP 后
SET optimizer_switch = 'index_condition_pushdown=off';
EXPLAIN SELECT * FROM user_icp
WHERE zipcode = '431200' AND MONTH(birthdate) = 3;
-- 期望：Extra = Using where（Server 层过滤）—— 回表次数变多

SET optimizer_switch = 'index_condition_pushdown=on';   -- 记得开回来
```

### 验证 4：前缀索引 & 区分度计算

```
-- 建带 email 字段的表
CREATE TABLE user_email (
id INT PRIMARY KEY AUTO_INCREMENT,
email VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 灌一批数据后，先算不同前缀长度的区分度（越接近 1 越好）
SELECT
COUNT(DISTINCT LEFT(email, 5))  / COUNT(*) AS rate5,
COUNT(DISTINCT LEFT(email, 8))  / COUNT(*) AS rate8,
COUNT(DISTINCT LEFT(email, 12)) / COUNT(*) AS rate12,
COUNT(DISTINCT email)           / COUNT(*) AS rate_full
FROM user_email;
-- 一般选达到 rate_full 95% 以上的最小长度，比如 rate8 = 0.98 就取 8

-- 建前缀索引
ALTER TABLE user_email ADD KEY idx_email_pfx (email(8));

-- 查询时正常写，MySQL 会自动利用前缀索引
EXPLAIN SELECT * FROM user_email WHERE email = 'user@example.com';
```

### 验证 5：聚簇 vs 非聚簇的回表次数直观感受

```
-- 造 100 万数据观察查询代价
CREATE TABLE cus_order (
id INT PRIMARY KEY AUTO_INCREMENT,
score INT NOT NULL,
name VARCHAR(20) NOT NULL,
KEY idx_score (score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用存储过程灌 100 万数据（略，用 loop insert 即可）
-- ...

-- ① 主键查询（聚簇索引，一次树查找拿到整行）
EXPLAIN SELECT * FROM cus_order WHERE id = 500000;
-- 期望：type = const, rows = 1，最快

-- ② 走辅助索引 + 回表
EXPLAIN SELECT * FROM cus_order WHERE score = 500;
-- 期望：type = ref，Extra 无 Using index，需要回表

-- ③ 覆盖索引（不回表）
EXPLAIN SELECT id, score FROM cus_order WHERE score = 500;
-- 期望：Extra = Using index，速度接近 ①

-- 观察查询时间：可以 SET profiling = 1 后跑 SHOW PROFILES 对比
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 一句话说清「为什么 InnoDB 用 B+ 树，不用 B 树 / 红黑树 / Hash」。</summary>

B+ 树非叶节点只存 key、度数大 → 树高低 → 磁盘 IO 少；叶子双向链表 → 范围查询快。B 树非叶存 data 度数小、红黑树一节点一 key 树高太高，都不适合磁盘存储；Hash 不支持范围查询。

</details>

<details>

<summary>Q2 InnoDB 主键索引和普通（二级）索引的叶子节点分别存什么？MyISAM 呢？</summary>

InnoDB 主键索引叶子存**整行数据**（聚簇索引）；InnoDB 二级索引叶子存**主键值**（需回表）。MyISAM 所有索引（主键 + 二级）叶子都存**数据行的物理地址**，都是非聚簇。

</details>

<details>

<summary>Q3 什么是覆盖索引？`EXPLAIN` 里怎么判断？</summary>

`SELECT` 的字段全部包含在辅助索引里，不需要回表就能拿到全部结果。`EXPLAIN` 的 `Extra` 列出现 `Using index` 就是覆盖索引。

</details>

<details>

<summary>Q4 联合索引 `(a, b, c)`，下面哪些能走索引：`WHERE a=1 AND b=1` / `WHERE a=1 AND c=1` / `WHERE b=1 AND c=1`？</summary>

第 1 个：✅ 走 a、b 两列；第 2 个：⚠️ 只走 a 列（b 缺失导致 c 无法用索引）；第 3 个：❌ 完全不走（缺最左的 a，整个索引失效）。

</details>

<details>

<summary>Q5 索引下推 ICP 是什么？它解决了什么问题？</summary>

MySQL 5.6+ 的优化：把原本要在 Server 层做的 `WHERE` 过滤下推到存储引擎层，在扫描索引时就直接过滤掉不满足条件的记录，**减少回表次数**。`EXPLAIN` 的 `Extra` 显示 `Using index condition` 就是启用了 ICP。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- MySQL 8.0 Reference · Comparison of B-Tree and Hash Indexes

- MySQL 8.0 Reference · Index Condition Pushdown Optimization

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0044：**索引失效的 10 种场景** —— 建了索引却没走索引？函数、隐式类型转换、前置 `%`、`OR` 条件、字符集不一致 —— 一次讲透面试官最爱的「找茬 SQL」。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


