> Lesson 0046 · 阶段六 · MySQL · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 处追问

# 0046 · 事务 ACID & 四大隔离级别

这是 MySQL 面试的**第二硬骨头**（第一硬骨头是索引，见 0043）。面试官的经典四连击是：**「ACID 每个字母怎么保证？」「四个隔离级别分别对应哪些异象？」「MySQL 默认是哪个？为什么和 SQL 标准不一样？」「InnoDB 在 RR 下真的没有幻读吗？」**—— 这条链路把「锁 / MVCC / undo log / redo log」全部串起来。本课先把 ACID + 隔离级别 + 读现象讲透，*MVCC 版本链的深挖留给下一课 0047，锁的细节留给 0048*。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 ACID 里的 I（Isolation 隔离性）是靠什么机制保证的？</summary>

**锁 + MVCC**。写-写冲突靠行锁 / Next-Key Lock 串行化；读-写并发用 MVCC 版本链实现快照读，避免读者阻塞写者。见场景 2。

</details>

<details>

<summary>Q0.2 MySQL InnoDB 的默认隔离级别是什么？为什么和 SQL 标准 / Oracle / PG 都不一样？</summary>

**REPEATABLE READ**。Oracle / PostgreSQL 默认是 READ COMMITTED。MySQL 选 RR 是历史原因 —— 早期 `binlog` 用 **statement 格式**，在 RC 下主从复制会出现顺序不一致（主库的 UPDATE 依赖当前读到的行，从库回放时看到的数据可能不同），必须用 RR 的间隙锁强行串行化 INSERT 才安全。见场景 5。

</details>

## 面试场景 1：什么是事务？为什么需要事务？

🎤 面试官

你能用一句话解释一下「事务」吗？MySQL 哪些存储引擎支持事务？

🧑‍💻 你

**事务（Transaction）**是一组数据库操作组成的*不可分割的逻辑单元*：要么全部成功、要么全部失败回滚。经典例子是银行转账 —— A 账户 `-100` 和 B 账户 `+100` 必须原子执行，否则中间断电就会凭空少 100。

MySQL 里：

- **InnoDB**：支持事务（也是 MySQL 5.5 以后的默认引擎）。

- **MyISAM**：*不支持事务*，也不支持行锁和外键 —— 所以现代业务表几乎全用 InnoDB。

- **Memory**：也不支持事务。

追问 事务的*边界*是什么？一段业务代码里默认是不是一个事务？

MySQL 默认 **autocommit=1**，即每条 SQL 自动就是一个独立事务，执行完立刻 COMMIT。想把多条 SQL 组成一个事务，要么显式 `BEGIN ... COMMIT`，要么先 `SET autocommit=0` 手动控制。Spring 应用里 `@Transactional` 会通过 AOP 自动打开事务并在方法退出时 COMMIT / ROLLBACK。

## 面试场景 2：ACID 四大特性 & 各自靠什么机制保证？⭐ 必背

🎤 面试官

ACID 四个特性分别是什么？MySQL 里各自靠什么机制保证？

🧑‍💻 你

字母含义InnoDB 里靠什么保证

**A**tomicity原子性：事务内操作要么全成功、要么全回滚**undo log**（回滚日志）：执行 DML 前先把「反向操作」写到 undo；ROLLBACK 时按 undo 反向执行
**C**onsistency一致性：数据从一个合法状态到另一个合法状态（不违反业务约束、外键、唯一索引等）由 *A + I + D 共同保证* + 应用层业务约束（是 ACID 的**最终目标**而非独立机制）
**I**solation隔离性：并发事务互不干扰，看起来像串行**锁 + MVCC**：写-写靠行锁 / Next-Key Lock；读-写靠 MVCC 版本链（Read View）
**D**urability持久性：一旦 COMMIT，数据永久保存，即使宕机也不丢**redo log**（重做日志，WAL）：COMMIT 前先把「物理页修改」顺序刷盘；崩溃恢复时按 redo 前滚

助记口诀：**A 靠 undo 回滚、I 靠锁 + MVCC、D 靠 redo 前滚，C 是三者叠加后的结果**。

追问 「C 是靠 AID 保证的」这个说法对吗？为什么 C 单独拎出来？

严格来说 C 有两层含义：**数据库层面**（外键约束、唯一约束、CHECK 约束 —— 数据库自己会拒绝违反约束的写入）+ **业务层面**（比如「转账两侧金额必须相等」这种业务不变量，是应用代码要保证的）。数据库层的 A/I/D 只能保证「不出现残缺或中间态」，业务不变量还得靠开发者写对 SQL。所以 C 是*目标*，A/I/D 是*手段*，两者不在同一层。

追问 undo log 和 redo log 有什么区别？为什么要有两份？

**undo log** 是*逻辑日志*，记录「如何反向撤销」（比如 INSERT 记录了对应的 DELETE），用于 **ROLLBACK 和 MVCC 版本链**。**redo log** 是*物理日志*，记录「某个数据页哪个位置改成了什么」，用于 **崩溃恢复**（因为 COMMIT 时脏页可能还没刷到磁盘）。两份日志解决两个不同问题：一份让你能「后悔」，一份让你「不怕断电」。细节见 0049。

## 面试场景 3：并发事务的三大读现象 ⭐ 经典必背

🎤 面试官

并发事务下会出现哪些读一致性问题？分别举个例子。

🧑‍💻 你

1.
**脏读（Dirty Read）**：读到了*另一个事务未提交*的数据。

场景：事务 A 把余额从 100 改成 200 但未 COMMIT；事务 B 此时读到 200；接着 A 回滚，B 读到的 200 是「幽灵数据」。

2.
**不可重复读（Non-Repeatable Read）**：同一事务内两次读*同一行*，结果不同 —— 因为期间别人 **UPDATE 并 COMMIT** 了。

场景：事务 A 第一次读余额是 100；事务 B UPDATE 成 200 并 COMMIT；事务 A 再读变成 200。*关注点是「同一行的值变了」*。

3.
**幻读（Phantom Read）**：同一事务内两次*范围查询*，结果集*行数不同* —— 因为期间别人 **INSERT / DELETE 并 COMMIT** 了。

场景：事务 A 第一次 `SELECT COUNT(*) WHERE age > 18` 得到 10；事务 B INSERT 一行成年人并 COMMIT；事务 A 再查得到 11。*关注点是「多出/少了一行」*。

陷阱 「幻读」和「不可重复读」的**本质区别**：

- 不可重复读的问题在于「**行的内容变了**」，对应操作是 UPDATE，解决办法是*对读到的行加行锁*就够了。

- 幻读的问题在于「**行的数量变了**」，对应操作是 INSERT / DELETE，行锁锁不住「还不存在的行」—— 必须用**间隙锁 Gap Lock**把索引间的「空档」也锁住，才能防止新行插入。

## 面试场景 4：SQL 标准的 4 大隔离级别 ⭐ 核心表格

🎤 面试官

SQL 标准定义了哪 4 个隔离级别？分别解决哪些读现象？

🧑‍💻 你

由低到高排列（隔离越强、并发越差）：

隔离级别
脏读
不可重复读
幻读
说明

**READ UNCOMMITTED**（读未提交）
✗ 可能
✗ 可能
✗ 可能
没有任何保证，几乎不用

**READ COMMITTED**（读已提交）
✓ 避免
✗ 可能
✗ 可能
Oracle / PostgreSQL / SQL Server 默认

**REPEATABLE READ**（可重复读）
✓ 避免
✓ 避免
标准下 ✗ / *InnoDB 下 ≈ ✓*
**MySQL InnoDB 默认**

**SERIALIZABLE**（串行化）
✓ 避免
✓ 避免
✓ 避免
所有事务串行执行，性能极差，几乎不用

规律：**级别越高，解决的异象越多，但并发性能越差**。

追问 隔离级别越高性能一定越差吗？

是的。RU 完全不加读锁，最快；RC 每次 SELECT 都要读取最新已提交版本（快照小、频繁重建 Read View），锁范围小；RR 事务内共享一个快照 + 使用 Gap Lock，锁范围大；SERIALIZABLE 直接把所有 SELECT 变成加共享锁的当前读，读写完全串行，性能最差。所以业界主流选择是 RC 或 RR，两端很少用。

## 面试场景 5：为什么 MySQL 默认是 RR 而不是 RC？⭐ 历史题

🎤 面试官

Oracle、PostgreSQL、SQL Server 都是默认 READ COMMITTED，为什么 MySQL InnoDB 偏偏默认 REPEATABLE READ？

🧑‍💻 你

历史原因 —— 跟 **binlog 的复制机制**有关。

MySQL 5.0 及以前，`binlog` 只支持 **statement 格式**（记录原始 SQL 文本）。在 RC 隔离级别下会出现*主从数据不一致*：

1. 主库上事务 A 先执行 `DELETE ... WHERE id > 5`（未 COMMIT）。

2. 事务 B 执行 `INSERT id=10` 并 COMMIT。

3. 事务 A 后 COMMIT。

4. 主库：id=10 被 A 的 DELETE 删掉了（因为 RC 下 A 的 DELETE 使用「当前读」）。

5. 但 binlog 按 COMMIT 顺序记录变成「B 先 INSERT、A 后 DELETE」—— 从库回放时 id=10 也被删掉，看似一致。

6. 但更复杂的组合（如 *INSERT SELECT + DELETE 混用*）会出现主从行数不同的严重问题。

MySQL 的解决方案是**用 RR 的间隙锁强行把 INSERT 阻塞**，让并发事务的执行顺序和 COMMIT 顺序一致，statement binlog 才安全。

后来 MySQL 5.1 引入 **row 格式 binlog**（记录每行的前后镜像），RC 下再用 row 格式就没这个问题了 —— 但 MySQL 为了兼容性，默认级别一直保留 RR。*很多公司业务上会手动改成 RC，因为性能更好、锁范围更小*。

追问 那生产上是选 RR 还是 RC？

看业务。**互联网大厂多数选 RC**（阿里、字节部分业务规范强制 RC）—— 原因是 RC 没有间隙锁、锁范围小、死锁概率低、并发高。**金融、账务、对一致性要求极高的场景选 RR**—— 因为需要事务内多次读取的一致性快照。切换隔离级别一定要评估是否有依赖「同一事务内快照一致」的业务代码。见场景 9。

## 面试场景 6：InnoDB 在 RR 下如何避免幻读？⭐ 高频深挖

🎤 面试官

SQL 标准说 RR 不能解决幻读，但你说 InnoDB 的 RR「几乎」解决了幻读，靠什么？

🧑‍💻 你

InnoDB 用*两套机制*分别覆盖两种读：

1.
**快照读（Snapshot Read）**—— 也叫一致性非锁定读：普通 `SELECT` 语句走 **MVCC 版本链**。

- RR 下事务*第一次 SELECT 时创建 Read View*，之后整个事务都用这个快照。

- 别人 INSERT 的新行事务 ID 大于快照的 up_limit_id，直接被判定为「快照之后的版本」，看不见 —— 自然没有幻读。

- MVCC 的完整原理见 **0047**。

2.
**当前读（Current Read）**—— 也叫一致性锁定读：`SELECT ... FOR UPDATE`、`SELECT ... LOCK IN SHARE MODE`、UPDATE、DELETE、INSERT 都是当前读。

- 当前读必须读*最新已提交版本*，不能用快照。

- InnoDB 用 **Next-Key Lock = Record Lock 行锁 + Gap Lock 间隙锁**，锁住命中行 + 索引间的「空档」，别人想 INSERT 落到间隙里会被阻塞 —— 也防住幻读。

所以结论是：**InnoDB RR 在大部分场景下没有幻读**。

陷阱 InnoDB RR 也*不是完全没幻读*。反例：**先快照读、再当前读**，就可能读到「幻行」。

比如事务 A 先 `SELECT * FROM t WHERE age > 18`（快照读，10 行）；此时事务 B INSERT 一行 `age=20` 并 COMMIT；事务 A 再 `SELECT * FROM t WHERE age > 18 FOR UPDATE`（当前读，11 行）—— 多出来的那一行就是幻行。这是 InnoDB RR 唯一还能出幻读的场景，面试官很爱问。

追问 间隙锁 Gap Lock 是什么？为什么 RC 下没有？

Gap Lock 锁的是*索引记录之间的「空档」*，不锁具体行，目的就是防止别人在空档里 INSERT 新行。比如索引里有 `id=5, id=10, id=15`，`SELECT ... WHERE id > 5 AND id < 15 FOR UPDATE` 会给 `(5, 10)` 和 `(10, 15)` 两个间隙加 Gap Lock。**Gap Lock 只在 RR 下才有**，RC 下只有 Record Lock（行锁），所以 RC 下必然有幻读 —— 但代价是并发高、死锁少，很多互联网业务愿意接受。

## 面试场景 7：快照读 vs 当前读 ⭐ 核心

🎤 面试官

快照读和当前读分别对应哪些 SQL？为什么要区分这两种读？

🧑‍💻 你

维度快照读（Snapshot Read）当前读（Current Read）

触发 SQL普通 `SELECT ...``SELECT ... FOR UPDATE`、`SELECT ... LOCK IN SHARE MODE`、`UPDATE`、`DELETE`、`INSERT`
读到的版本事务快照对应的*历史*版本最新*已提交*版本
加锁不加锁（MVCC 无阻塞）加行锁 + 间隙锁（Next-Key Lock）
性能高（读者不阻塞写者）低（可能阻塞并发写）
幻读MVCC 天然避免Gap Lock 避免
典型用途展示、报表、只读查询需要「先读后写」的强一致场景（扣库存、抢红包）

为什么要区分：*读多写少的场景走快照读性能高*，*需要独占资源的场景走当前读避免并发覆盖*。

追问 `UPDATE t SET stock = stock - 1 WHERE id = 1` 内部先读还是先写？读的是快照还是当前？

UPDATE 内部包含一次「当前读」+ 一次写。它必须读到**最新已提交**的 stock 值（不能读快照，否则算出来的 `stock - 1` 早就过时了），然后基于最新值写回。所以 UPDATE / DELETE / INSERT ... SELECT 全都是*当前读*，会给相关行加 Next-Key Lock。*这也是为什么高并发扣库存不能用 `SELECT + UPDATE` 两步，而必须一条 UPDATE 走原子当前读*。

## 面试场景 8：事务的控制语句 & 隔离级别设置

🧑‍💻 你

事务控制常用 SQL：

- `BEGIN` / `START TRANSACTION`：开启事务

- `COMMIT`：提交事务

- `ROLLBACK`：回滚事务

- `SAVEPOINT sp1` / `ROLLBACK TO sp1`：设置保存点、部分回滚（不常用）

- `SET AUTOCOMMIT = 0`：关闭自动提交，之后每条 SQL 需手动 COMMIT

查看和设置隔离级别：

```
-- 查看（MySQL 8.0+）
SELECT @@transaction_isolation;    -- 会话级
SELECT @@global.transaction_isolation;  -- 全局级

-- 设置（对当前会话）
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 设置（对全局，需重连生效）
SET GLOBAL TRANSACTION ISOLATION LEVEL REPEATABLE READ;
```

追问 `BEGIN` 和 `START TRANSACTION` 有区别吗？

基本等价。`START TRANSACTION` 是 SQL 标准写法，还支持 `WITH CONSISTENT SNAPSHOT` 选项（在 RR 下*立刻*创建 Read View，而不是等到第一次 SELECT 时才创建 —— 面试官问细节时可以提这个）。`BEGIN` 是 MySQL 简写别名。

## 面试场景 9：实际项目里的隔离级别怎么选？

🎤 面试官

你们生产环境用的哪个隔离级别？为什么？

🧑‍💻 你

- **READ COMMITTED**（互联网业务首选）：Oracle / PG 默认；无间隙锁 → 锁范围小、死锁少、并发高；容忍不可重复读和幻读（业务代码避免依赖同事务内快照一致）。*阿里、字节的 MySQL 规范多数强制 RC*。

- **REPEATABLE READ**（MySQL 默认，一致性优先场景）：金融、账务、报表统计等需要事务内快照一致的场景。*要小心 Gap Lock 引发的死锁*。

- **READ UNCOMMITTED**：几乎不用，脏读风险大。

- **SERIALIZABLE**：几乎不用，全部读加锁 → 性能极差。特殊分析场景可能临时用。

陷阱 从 RR 切到 RC **不是无风险操作**！业务代码里如果依赖了「事务内多次读同一行结果一致」的假设（比如「先 SELECT 校验金额，再 UPDATE 扣款」），切到 RC 后可能读到中间被改过的数据，出现覆盖问题。安全做法：*要么全用当前读（SELECT FOR UPDATE），要么改造成单条 UPDATE 原子操作*。

## 面试场景 10：Spring @Transactional 的传播行为（预告 0063）

🎤 面试官

Spring 里 `@Transactional` 的传播行为有哪些？（本课只做速览，细节留给 Spring 事务专题）

🧑‍💻 你

Spring 定义了 **7 种传播行为**（`Propagation` 枚举），控制「一个已在事务中的方法调用另一个 @Transactional 方法时」的行为：

- **REQUIRED（默认）**：有事务则加入，没事务就新建。90% 场景够用。

- **REQUIRES_NEW**：*无论外层有没有事务，都新建一个独立事务*，外层挂起。用于「日志/审计必须独立提交」的场景。

- **SUPPORTS**：有事务就加入，没有就以非事务方式运行。

- **NOT_SUPPORTED**：以非事务方式运行；如果外层有事务就挂起。

- **MANDATORY**：必须在外层事务中运行；没有就抛异常。

- **NEVER**：反过来，必须*不在*事务中；有就抛异常。

- **NESTED**：如果外层有事务，就用 SAVEPOINT 创建嵌套子事务（子回滚不影响外层，外层回滚会带上子）。

面试重点是「REQUIRED vs REQUIRES_NEW vs NESTED」三者的区别，以及为什么*同类内部方法调用 @Transactional 不生效*（AOP 代理问题）。**细节 & 陷阱留到 0063 Spring 事务课**。

## 💻 代码验证（打开 mysql 客户端跑一遍）

### 验证 1：脏读（RU 才能复现）

开两个 MySQL 客户端会话，都执行 `SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;`。

```
-- 准备：CREATE TABLE account(id INT PRIMARY KEY, balance INT);
--       INSERT INTO account VALUES (1, 100);

-- 会话 A                          -- 会话 B
BEGIN;
UPDATE account SET balance = 200
WHERE id = 1;
BEGIN;
SELECT balance FROM account
WHERE id = 1;
-- 返回 200 ← 脏读！A 还没 COMMIT
ROLLBACK;
-- B 手里的 200 是幽灵数据
```

### 验证 2：不可重复读（RC 会复现，RR 不会）

```
-- 两个会话都：SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 会话 A                          -- 会话 B
BEGIN;
SELECT balance FROM account
WHERE id = 1;     -- 返回 100
BEGIN;
UPDATE account SET balance = 200
WHERE id = 1;
COMMIT;
SELECT balance FROM account
WHERE id = 1;     -- 返回 200 ← 不可重复读！
COMMIT;

-- 把会话都切成 REPEATABLE READ 再试一次，A 两次读都是 100（快照一致）
```

### 验证 3：InnoDB RR 用 MVCC 避免幻读（快照读部分）

```
-- 两个会话都：SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- 会话 A                          -- 会话 B
BEGIN;
SELECT COUNT(*) FROM account;
-- 假设返回 1（快照建立）
BEGIN;
INSERT INTO account
VALUES (2, 500);
COMMIT;
SELECT COUNT(*) FROM account;
-- 仍然返回 1 ← MVCC 快照读，看不见 B 的新行
COMMIT;
SELECT COUNT(*) FROM account;
-- 事务外看到 2
```

### 验证 4：InnoDB RR 「先快照后当前」还会出幻读

```
-- 两个会话都保持 RR

-- 会话 A                          -- 会话 B
BEGIN;
SELECT * FROM account
WHERE balance > 50;
-- 假设看到 1 行（快照建立）
BEGIN;
INSERT INTO account
VALUES (3, 999);
COMMIT;
SELECT * FROM account
WHERE balance > 50
FOR UPDATE;
-- 看到 2 行 ← 幻行！
-- 当前读读的是最新已提交版本，
-- 不受快照约束
COMMIT;
```

观察点：**纯快照读事务下 InnoDB RR 没幻读；一旦掺进当前读，幻读就出现了**。这就是面试官深挖 InnoDB RR 时最爱问的边界。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话说清 ACID 每个字母的含义 + InnoDB 用什么机制保证它。</summary>

A 原子性靠 **undo log 回滚**；C 一致性是 A/I/D 共同作用 + 业务约束的*目标*；I 隔离性靠 **锁 + MVCC**；D 持久性靠 **redo log** 前滚。

</details>

<details>

<summary>Q2 不可重复读和幻读的本质区别是什么？分别靠什么机制解决？</summary>

不可重复读是**同一行的值变了**（UPDATE），加行锁就能解决；幻读是**行的数量变了**（INSERT/DELETE），行锁锁不住不存在的行，必须加 **Gap Lock 间隙锁**。

</details>

<details>

<summary>Q3 MySQL InnoDB 默认隔离级别是什么？为什么选它而不是像 Oracle/PG 那样选 RC？</summary>

默认 **REPEATABLE READ**。历史原因：早期只有 statement 格式 binlog，在 RC 下主从复制会出现顺序不一致（INSERT/DELETE 组合），必须用 RR 的 Gap Lock 强行串行化 INSERT 才安全。后来有了 row 格式 binlog，RC 也没这个问题，但 MySQL 出于兼容一直保留 RR 为默认。

</details>

<details>

<summary>Q4 InnoDB 在 RR 下真的完全没有幻读吗？举一个反例。</summary>

不是完全没有。**先快照读、再当前读**会出幻读 —— 快照读走 MVCC 看不到新行，但紧跟一个 `SELECT ... FOR UPDATE`（当前读）会读到最新已提交版本，多出来的行就是幻行。纯快照读或纯当前读场景下 RR 都没幻读。

</details>

<details>

<summary>Q5 `SELECT ... FOR UPDATE` 和普通 `SELECT` 有什么区别？高并发扣库存该用哪个？</summary>

普通 SELECT 是**快照读**，走 MVCC 版本链，不加锁；`SELECT ... FOR UPDATE` 是**当前读**，读最新已提交版本 + 加行锁 / Next-Key Lock。高并发扣库存*不该用「SELECT 校验 + UPDATE 扣减」两步*（会有并发覆盖问题），最优做法是一条 `UPDATE stock SET n = n - 1 WHERE id = X AND n > 0`（内部就是原子当前读 + 写），根据影响行数判断是否成功。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- MySQL 8.0 Reference · InnoDB Transaction Isolation Levels —— 官方文档

- MySQL 8.0 Reference · Next-Key Locking —— Gap Lock 官方定义

#### 🔗 关联课件

- （上一课）

- （下一课 ★ 本课的直接后续）

-

-

#### 🧭 下一课预告

Lesson 0047：**MVCC 版本链 & Read View 深挖** —— 本课埋了「快照读怎么读到历史版本」「RR 的 Read View 何时创建」「事务 ID 和 up_limit_id / low_limit_id 判定规则」等钩子，下一课全部拆开讲。是 MySQL 面试的*最深洞*。

💬 有任何疑问 —— 「A/B/C 到底谁是目标谁是手段？」「Gap Lock 到底怎么锁的？」「RR 切 RC 我们业务代码要改什么？」「Spring @Transactional 内部方法调用为什么失效？」—— 直接问我。我是你的老师，也是你的追问陪练。


