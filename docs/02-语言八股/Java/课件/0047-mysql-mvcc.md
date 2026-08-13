> Lesson 0047 · 阶段六 · MySQL · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 8 个追问

# 0047 · InnoDB MVCC 详解

上一课  讲了 MySQL 事务的四个隔离级别，那是*现象层*：脏读、不可重复读、幻读到底会不会出现。这一课直接扎到底层 —— **RC 和 RR 究竟是怎么实现的？为什么普通 SELECT 能不加锁、还能保证一致性？**答案就是三个字母：**MVCC**（Multi-Version Concurrency Control，多版本并发控制）。

MVCC 是面试 MySQL 第三块硬骨头（前两块是索引和事务隔离级别）。追问链条通常是：*MVCC 是什么 → 三大组件（隐藏字段/undo log/ReadView）→ 可见性算法 → RC 和 RR 生成 ReadView 有什么不同 → 幻读到底解决没*。掌握本课，这条链就能一口气讲下来。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 RR 和 RC 下，ReadView 的生成时机有什么区别？</summary>

**RC** 每次快照读都新建一个 ReadView；**RR** 只在事务第一次快照读时创建，之后整个事务复用同一个。这是「可重复读」的实现关键，第 7 题细讲。

</details>

<details>

<summary>Q0.2 快照读和当前读，哪种用 MVCC？</summary>

只有**快照读**（普通 SELECT）走 MVCC 读历史版本；**当前读**（`SELECT ... FOR UPDATE`、`UPDATE`、`DELETE`、`INSERT`）绕过 MVCC，走锁读最新版本。第 8 题细讲。

</details>

## 面试场景 1：MVCC 是什么？为什么要有它？

🎤 面试官

说一下 MVCC 是什么，MySQL 为什么要引入 MVCC？

🧑‍💻 你

**MVCC（Multi-Version Concurrency Control，多版本并发控制）**是一种通过*为数据保留多个历史版本*来实现「读写不阻塞」的并发控制机制。

核心思想：

- **读走历史快照**：普通 SELECT 不加锁，去读一个「过去的、稳定的」版本。

- **写走当前版本**：UPDATE/DELETE 加行锁修改最新数据，同时把旧版本保存到 undo log。

- **读写互不阻塞**：读操作不会被写操作卡住，写操作也不会被读操作卡住 —— 大幅提高并发度。

没有 MVCC 之前，读写必须通过加锁串行化：读的时候写要等、写的时候读要等，并发性能极差。有了 MVCC，只有*写和写*之间才需要互斥，读永远畅通无阻。

InnoDB、Oracle、PostgreSQL 都实现了 MVCC，只是版本管理方式不同（InnoDB 用 undo log 就地更新 + 回滚指针；PG 是新旧版本都放在主表，靠 vacuum 清理旧版本）。

追问 MVCC 和乐观锁是同一回事吗？

不是。**MVCC 是存储引擎级**的多版本视图机制，用户无感知，SELECT 自动就走了；**乐观锁是应用层**的手动版本号 / CAS 校验（如加一列 `version`，UPDATE 时 WHERE version=?）。相似之处：都是*无锁读、写时校验*；不同之处：MVCC 让读永远看到一致的历史快照，乐观锁只在写入冲突时才有意义。

## 面试场景 2：MVCC 的三大核心组件 ⭐核心

🎤 面试官

InnoDB 是怎么实现 MVCC 的？说一下核心组件。

🧑‍💻 你

InnoDB 的 MVCC 由三个组件配合完成：

1. **行的隐藏字段** —— 每行记录额外藏了 3 个字段：`DB_TRX_ID`（最后修改者的事务 ID）、`DB_ROLL_PTR`（指向 undo log 上一版本的指针）、`DB_ROW_ID`（无主键时的隐藏主键）。

2. **undo log 版本链** —— 每次 UPDATE 都把旧值存进 undo log，通过 `DB_ROLL_PTR` 把新旧版本串成一条链。任意历史版本都能沿链回溯。

3. **ReadView 一致性视图** —— 事务读的时候生成一个「快照描述」，记录当时哪些事务是活跃的、事务 ID 高水位在哪，用它去判断版本链上哪个版本对我可见。

可以简单记成：*隐藏字段标记版本、undo log 保存版本、ReadView 挑选版本*。

## 面试场景 3：隐藏字段 DB_TRX_ID / DB_ROLL_PTR / DB_ROW_ID ⭐核心

🧑‍💻 你

每一行 InnoDB 记录，除了用户定义的列，还偷偷藏了 3 个字段：

字段大小含义

`DB_TRX_ID`6 字节最近一次*修改*本行的事务 ID（INSERT/UPDATE/DELETE 都会更新它）
`DB_ROLL_PTR`7 字节回滚指针，指向 undo log 里该行的*上一个版本*；没有就置空
`DB_ROW_ID`6 字节只在*表无主键、也无非空唯一索引*时才生成的隐藏聚簇主键

其中 `DB_TRX_ID` 和 `DB_ROLL_PTR` 才是 MVCC 的主角：前者告诉 ReadView「这行是谁改的」，后者告诉 ReadView「上一个版本在哪里」。`DB_ROW_ID` 只是聚簇索引的兜底方案，跟 MVCC 关系不大。

追问 MVCC 里的「版本」是什么粒度？

**行级**。每一行独立维护自己的 `DB_ROLL_PTR` 版本链，各行的历史互不干扰。这也意味着一张表的 undo log 是「按行分散」的，不是全表的时间轴快照。

## 面试场景 4：undo log 版本链 ⭐核心

🧑‍💻 你

每次 `UPDATE`，InnoDB 会：

1. **原地更新**该行为新值，把新事务 ID 写进 `DB_TRX_ID`。

2. 把*旧值*和*旧的 DB_TRX_ID*拷进一条 undo log 记录。

3. 让当前行的 `DB_ROLL_PTR` 指向这条新写的 undo log，而新写的 undo log 又指向*更早的 undo log*。

结果就是：一条数据行 + 若干条 undo log 组成一条**由新到旧的单向链表**。可以类比 *git commit 链*：每次 commit 都保留前一个 commit 的哈希，可以一路回溯到项目创世。

```
当前行 (最新版本)                undo log 链
┌────────────────┐          ┌────────────────┐          ┌────────────────┐
│ id = 1         │          │ id = 1         │          │ id = 1         │
│ name = "赵六"  │  ROLL    │ name = "王五"  │  ROLL    │ name = "张三"  │
│ DB_TRX_ID = 30 │─────────>│ DB_TRX_ID = 20 │─────────>│ DB_TRX_ID = 10 │
│ DB_ROLL_PTR ●──┤   PTR    │ DB_ROLL_PTR ●──┤   PTR    │ DB_ROLL_PTR = ∅│
└────────────────┘          └────────────────┘          └────────────────┘
(heap 里的行)              (undo log 记录)             (undo log 记录)
```

快照读要读的「历史版本」，就是沿着这条链找出*对我可见的那一条*。

陷阱 undo log 有两种：**insert undo log** 只对当前事务的回滚有意义，事务提交后立刻可删；**update undo log** 因为要支撑其他事务的 MVCC 读，必须等到*没有任何 ReadView 需要它*才能被 purge 线程回收。长事务会让 update undo 长时间无法清理 —— 这是生产事故常见诱因，下面第 10 题会展开。

## 面试场景 5：ReadView 是什么？包含哪些字段？⭐核心

🧑‍💻 你

**ReadView** 是「快照读时刻的事务状态快照」。它不复制数据，只记录*当时哪些事务在跑*，用来判断版本链上每个版本对「此刻的我」可不可见。

关键字段有 4 个：

字段含义

`m_ids`创建 ReadView 时，*活跃*（已启动但未提交）的事务 ID 集合
`min_trx_id``m_ids` 里最小的事务 ID —— 活跃事务里最老的那个
`max_trx_id`系统*下一个要分配*的事务 ID —— 相当于「高水位」，任何 >= 它的事务都是「未来的」
`creator_trx_id`创建这个 ReadView 的*本事务自身*的 ID

直觉上可以这样理解：`min_trx_id` 和 `max_trx_id` 定义了一段「灰色区间」，落在这段区间里的事务需要看 `m_ids` 才知道是不是已提交；区间外要么早就提交（可见），要么根本还没启动（不可见）。

## 面试场景 6：ReadView 的可见性算法 ⭐核心

🎤 面试官

给一条行记录，怎么用 ReadView 判断它对当前事务可不可见？

🧑‍💻 你

取行的 `DB_TRX_ID`（记为 `trx_id`），按下面 4 条规则依次判：

条件结论直觉解释

`trx_id == creator_trx_id`可见自己改的自己当然看得见
`trx_id < min_trx_id`可见生成 ReadView 之前就已经提交的老事务
`trx_id >= max_trx_id`不可见ReadView 生成之后才启动的「未来事务」
`min_trx_id <= trx_id < max_trx_id`在 `m_ids` 中 → 不可见；不在 → 可见灰色区间：活跃列表里说明当时还没提交

如果当前版本*不可见*，就沿 `DB_ROLL_PTR` 跳到 undo log 中的上一版本继续判 —— 一直找到可见的版本或者链尾（找到链尾还没有可见的，说明这行对当前事务不存在，可能是被后面的事务 INSERT 的）。

追问 如果版本链走到尽头都不可见，怎么办？

说明这行对当前事务而言*不存在*。典型情况：该行是 ReadView 创建之后被别的事务 INSERT 进来的（所有版本的 `DB_TRX_ID` 都 >= `max_trx_id`），当前事务的快照读根本看不到它。这也是 RR 快照读能天然屏蔽新插入的行、部分解决幻读的底层原因。

## 面试场景 7：RC vs RR 的 ReadView 生成时机 ⭐核心

🎤 面试官

同样的 MVCC 机制，为什么 RC 是「不可重复读」，RR 就能「可重复读」？

🧑‍💻 你

秘密全在 **ReadView 的创建时机**：

隔离级别ReadView 何时创建结果

**RC (Read Committed)**每次快照读都*新建*一个 ReadView能看到别人最新提交的修改 → *不可重复读*
**RR (Repeatable Read)**只在事务的*第一次快照读*时创建，之后整个事务复用整个事务用同一个「时间切片」 → *可重复读*

换句话说，RR 一整个事务只有*一个*ReadView，RC 一个事务可能有*多个*ReadView。两个 SELECT 之间别人提交了新版本，RC 会看到（因为新 ReadView），RR 看不到（还在用老 ReadView，新事务 ID 落在 `max_trx_id` 之外）。

追问 RR 事务如果*始终不做快照读*，会创建 ReadView 吗？

不会。ReadView 是懒创建的 —— 只有第一次快照读时才生成。所以一个 RR 事务如果只执行 `UPDATE`、`SELECT ... FOR UPDATE`（都是当前读），从头到尾都不会有 ReadView。这也是为什么*只做当前读的 RR 事务不能防幻读*。

## 面试场景 8：MVCC 只对「快照读」生效

🧑‍💻 你

不是所有读都走 MVCC。要区分两类：

类型SQL读的是什么走 MVCC 吗

快照读普通 `SELECT`（不带 FOR UPDATE / LOCK IN SHARE MODE）ReadView 判定出的历史版本✅ 走
当前读`SELECT ... FOR UPDATE`、`SELECT ... LOCK IN SHARE MODE`、`UPDATE`、`DELETE`、`INSERT`最新已提交版本❌ 不走，直接读最新 + 加锁

当前读*必须*读到最新数据，否则会覆盖别人的修改。所以它绕过 ReadView，直接读 heap 上的最新行，并加 X 锁或 S 锁保证独占性。

追问 `SELECT ... FOR UPDATE` 到底走什么锁？会看到未提交数据吗？

走*行级 X 锁*（`UPDATE/DELETE` 也一样），RR 下还加*间隙锁 / next-key lock*。它*不会看到未提交数据* —— 因为它*等到别人提交或回滚*再读，不是脏读。所以 FOR UPDATE 是「阻塞的当前读」，不是 MVCC。

## 面试场景 9：MVCC 能解决幻读吗？

🎤 面试官

RR 隔离级别下 MVCC 到底解决了幻读没？

🧑‍💻 你

结论：**MVCC 解决了「快照读」下的幻读，但没解决「当前读」下的幻读**。

- **快照读没幻读**：RR 全程复用第一次生成的 ReadView。别人 INSERT 的新行 `DB_TRX_ID >= max_trx_id`，永远不可见 —— 天然屏蔽。

- **当前读会幻读**：`SELECT ... FOR UPDATE` 读的是最新版本，会看到别人刚 INSERT 的新行 —— 幻读复现。

InnoDB 补的这条补丁叫 **Next-Key Lock（间隙锁 + 行锁）**：在 RR 下对*当前读*加上间隙锁，锁住「查询范围内所有间隙」，阻止别人 INSERT。这样快照读靠 MVCC 防幻读、当前读靠间隙锁防幻读，双管齐下。所以标准答案是：**RR 下 MVCC + 间隙锁一起把幻读解决了**。

追问 RR 下的「幻读没解决完」具体指什么？举个例子。

典型场景：*先快照读，再当前读，两次结果不一致*。事务 A 先 `SELECT * FROM t WHERE age > 20` 拿到 3 行；事务 B `INSERT` 一行 age=25 并提交；事务 A 再执行 `SELECT * FROM t WHERE age > 20 FOR UPDATE` —— 因为 FOR UPDATE 是当前读，A 会看到 4 行。前后两次结果不一致，这就是 RR 下 MVCC 无法覆盖的幻读边缘。

## 面试场景 10：MVCC 的代价

🧑‍💻 你

MVCC 不是免费的，主要代价有三：

1. **undo log 空间**：所有 UPDATE 的旧版本都要保留在 undo log 里，只要还有事务的 ReadView 可能引用到它，就不能被 purge 线程清理。

2. **版本链变长影响查询**：热点行如果被反复更新、且有长事务持有 ReadView，版本链会拉得很长。每次快照读都要沿链回溯很多步，性能下降。

3. **大事务 / 长事务是杀手**：一个持续几分钟甚至几小时的事务，会一直持有 ReadView。它*之后*提交的所有事务产生的 update undo 都无法被 purge —— `ibdata1` 或独立 undo 表空间会疯狂膨胀，还可能拖垮从库同步。

面试常见追问：*「你们生产遇到过慢查询突然变慢吗？」*—— 排查思路里一定要提到长事务 + 版本链，能立刻加分。

追问 长事务为什么危害这么大？完整链路讲一下。

链路：*长事务持有 ReadView 不释放 → purge 线程发现「还有 ReadView 可能引用这些老版本」→ update undo log 无法回收 → undo 表空间持续增大（`innodb_undo_tablespaces` 撑爆）→ 同时其他事务的更新会在版本链上不断堆积 → 热点行版本链拉到几百上千条 → 快照读要遍历长链、CPU 飙升、查询变慢。*更糟的是主库如果炸了，从库还得复现整个事务，主从延迟也会跟着爆。生产上通常用 `information_schema.INNODB_TRX` 结合 `trx_started` 找出运行超过几分钟的长事务，直接 `KILL`。

追问 如果一个事务修改了很多行，undo log 会多大？

每修改一行就生成一条 undo log 记录，批量 `UPDATE t SET ... WHERE cond` 涉及 10 万行就有 10 万条 update undo。所以「一个 SQL 更新超大范围」是大事务的常见坑，DBA 通常要求分批 `LIMIT` 提交 —— 每次几千行、提交后再来一轮，让 purge 有机会回收。

## 💻 代码验证（跟着敲一遍最有效）

### 验证 1：建表 + 查询隐藏字段（间接观察）

InnoDB 的隐藏字段用户 SQL 层查不到（不在 `information_schema.COLUMNS` 里），但可以通过 `SHOW ENGINE INNODB STATUS` 里活跃事务和 undo 状况间接观察。

```
-- 建表
CREATE TABLE account (
id   INT PRIMARY KEY,
name VARCHAR(32),
bal  DECIMAL(10,2)
) ENGINE=InnoDB;

INSERT INTO account VALUES (1, '张三', 100.00);

-- 查看当前所有活跃事务和它们分配的事务 ID
SELECT trx_id, trx_state, trx_started, trx_mysql_thread_id, trx_query
FROM information_schema.INNODB_TRX;

-- 查看当前系统「下一个即将分配」的事务 ID（近似 max_trx_id 的来源）
SHOW ENGINE INNODB STATUS\G
-- 输出里搜「Trx id counter」和「History list length」两行：
--   Trx id counter 12345         <- 下一个事务 ID
--   History list length 87       <- undo log 版本链中未 purge 的记录数（越大越危险）
```

**观察点**：`History list length` 短时间内快速增长，通常意味着有长事务持有 ReadView 阻碍 purge。生产上超过几万就要报警排查。

### 验证 2：RR 下两个事务演示可重复读

```
-- Session A (事务 A，先启动 → 假设分配到 trx_id = 100)
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
SELECT bal FROM account WHERE id = 1;
-- 输出: 100.00
-- 此时 A 生成 ReadView: m_ids=[100], min=100, max=101, creator=100

-- Session B (事务 B，中途启动 → 假设 trx_id = 101)
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
UPDATE account SET bal = 500.00 WHERE id = 1;
COMMIT;
-- 此时 heap 上 id=1 的行:
--   bal=500.00, DB_TRX_ID=101, DB_ROLL_PTR->undo(bal=100.00, DB_TRX_ID=?)

-- Session A 再次读（还没提交，还在用同一个 ReadView）
SELECT bal FROM account WHERE id = 1;
-- 输出仍是: 100.00
-- 原因: 当前行 DB_TRX_ID=101 >= max_trx_id=101，不可见
--       顺 DB_ROLL_PTR 找到 undo 里 bal=100 的老版本，可见 → 返回 100
COMMIT;

-- Session A 再开一个新事务
START TRANSACTION;
SELECT bal FROM account WHERE id = 1;
-- 输出: 500.00 （新 ReadView，B 已提交，可见）
```

### 验证 3：RC 下同一事务两次读结果不同

```
-- Session A
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;
SELECT bal FROM account WHERE id = 1;  -- 输出: 500.00 （新建 ReadView）

-- Session B
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;
UPDATE account SET bal = 999.00 WHERE id = 1;
COMMIT;

-- Session A 同一事务里再读
SELECT bal FROM account WHERE id = 1;  -- 输出: 999.00 （又新建了一个 ReadView）
-- 这就是「不可重复读」：RC 每次快照读都新建 ReadView
COMMIT;
```

### 验证 4：可见性算法的 Java 伪代码

```
/**
* ReadView 可见性判断（对照 InnoDB 源码 read0read.cc 里的 changes_visible）
*/
class ReadView {
long creatorTrxId;      // 本事务 ID
long minTrxId;          // 活跃事务里最小的
long maxTrxId;          // 下一个要分配的 trx_id（高水位）
Set<Long> mIds;         // 活跃事务列表

boolean isVisible(long rowTrxId) {
if (rowTrxId == creatorTrxId) return true;   // 自己改的
if (rowTrxId < minTrxId)      return true;   // 早已提交
if (rowTrxId >= maxTrxId)     return false;  // ReadView 之后启动
// 灰色区间: 看当时是否活跃
return !mIds.contains(rowTrxId);
}
}

/**
* 沿版本链找可见版本
*/
Row findVisibleVersion(Row current, ReadView view) {
Row row = current;
while (row != null) {
if (view.isVisible(row.dbTrxId)) return row;
row = undoLog.getPreviousVersion(row.dbRollPtr);  // 沿 ROLL_PTR 回溯
}
return null;  // 版本链走完都不可见 → 该行对当前事务不存在
}
```

### 验证 5：查长事务 & History list length

```
-- 找出运行超过 60 秒的长事务
SELECT
trx_id,
trx_mysql_thread_id AS thread_id,
TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration_sec,
trx_query
FROM information_schema.INNODB_TRX
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60
ORDER BY duration_sec DESC;

-- 观察 undo 堆积
SELECT NAME, COUNT
FROM information_schema.INNODB_METRICS
WHERE NAME IN ('trx_rseg_history_len');

-- 紧急处理: KILL 掉罪魁事务的线程（谨慎! 会导致该事务回滚）
-- KILL <thread_id>;
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 一句话说清 MVCC 的三大组件。</summary>

**隐藏字段**（`DB_TRX_ID` 标最后修改者、`DB_ROLL_PTR` 指上一版本）+ **undo log 版本链**（保存历史值、通过 ROLL_PTR 串联）+ **ReadView**（一致性视图，判断版本链上哪个版本对当前事务可见）。

</details>

<details>

<summary>Q2 ReadView 的 4 个关键字段和它们的作用。</summary>

`m_ids`（活跃事务集合）、`min_trx_id`（活跃事务里最小的）、`max_trx_id`（下一个待分配 ID，高水位）、`creator_trx_id`（自身事务 ID）。可见性判断就是拿行的 `DB_TRX_ID` 和它们比较：小于 min 可见、大于等于 max 不可见、落在中间看是否在 `m_ids` 里。

</details>

<details>

<summary>Q3 RR 和 RC 都用 MVCC，为什么表现不一样？</summary>

因为**ReadView 生成时机不同**：RC 每次快照读都新建 ReadView，能看到最新提交（不可重复读）；RR 只在事务第一次快照读时创建，之后一直复用（可重复读）。

</details>

<details>

<summary>Q4 `SELECT ... FOR UPDATE` 走不走 MVCC？为什么？</summary>

不走。它是*当前读*，必须读到最新已提交版本才能安全加锁修改。它绕过 ReadView 直接读 heap 最新行，并加行级 X 锁（RR 下还会加 next-key lock）。所以 FOR UPDATE 和 MVCC 是两条不同路径。

</details>

<details>

<summary>Q5 RR 下 MVCC 是彻底解决幻读了吗？举反例。</summary>

没有彻底解决。快照读能防（新行 `DB_TRX_ID >= max_trx_id` 不可见），但*当前读会看到别人 INSERT 的新行*。经典反例：事务 A 先普通 SELECT 得 N 行 → 事务 B INSERT 一行并提交 → A 再 `SELECT ... FOR UPDATE` 会看到 N+1 行。InnoDB 用**间隙锁 / next-key lock**补了这个洞，配合 MVCC 才把幻读堵死。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- MySQL 8.0 官方 · InnoDB Multi-Versioning

- MySQL 8.0 官方 · InnoDB Undo Logs

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0048：**MySQL 锁机制** —— 表锁 / 行锁 / 记录锁 / 间隙锁 / next-key lock / 意向锁，配合本课的 MVCC，能完整回答「RR 是怎么解决幻读的」。

💬 有任何疑问 —— 「ReadView 的可见性算法能不能画个例子？」「长事务实际怎么排查？」「MVCC 和 PG 的实现有什么不同？」—— 直接问我。我是你的老师，也是你的追问陪练。


