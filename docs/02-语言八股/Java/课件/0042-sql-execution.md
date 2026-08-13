> Lesson 0042 · 阶段六 · MySQL · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑 SQL · 5 道自测

# 0042 · SQL 执行过程 & Server 层 vs 引擎层

这一课覆盖 的全部考点。「一条 SQL 从客户端敲下回车到磁盘落盘，MySQL 内部到底走了几层？」—— 这是面试官摸你 MySQL 深度的第一枪。**没搞懂这条链路，索引、事务、redo/binlog、主从复制统统只能背概念。**今天把这根主动脉打通，后面几课的 *索引 / 事务 / 日志 / 主从* 都会顺理成章。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 一条 SQL 从客户端到磁盘，会经过 MySQL 内部哪几个主要模块？按顺序说。</summary>

Server 层：`连接器 → (查询缓存) → 分析器 → 优化器 → 执行器`；引擎层：`InnoDB (buffer pool / undo log / redo log / 磁盘)`。查询缓存 8.0 已移除。第 3 场景完整展开。

</details>

<details>

<summary>Q0.2 查询缓存 8.0 被移除的最根本理由是什么？</summary>

**命中率极低**：只要底层表数据一变，与该表相关的所有缓存 *全部失效*。写多读多的业务里几乎不可能反复命中同一条完整 SQL 结果。维护缓存的开销远大于收益，所以 8.0 直接砍掉。第 5 场景展开。

</details>

## 面试场景 1：MySQL 整体架构 —— Server 层 + 存储引擎层 ⭐核心

🎤 面试官

你能画一下 MySQL 的整体架构吗？为什么要分成两层？

🧑‍💻 你

MySQL 从上到下是**两大层 + 一个连接入口**：

```
┌──────────────── 客户端 ────────────────┐
│  mysql CLI / JDBC / MyBatis / ...      │
└─────────────────┬──────────────────────┘
│ MySQL 协议 (TCP)
▼
┌────────────── Server 层 ───────────────┐
│  连接器     Connector                    │
│  查询缓存   Query Cache（8.0 已移除）    │
│  分析器     Parser（词法 + 语法）        │
│  优化器     Optimizer（选执行计划）      │
│  执行器     Executor（调引擎 API）       │
│  ── binlog 归档日志 ──                   │
└─────────────────┬──────────────────────┘
│ handler API (ha_*)
▼
┌────────── 存储引擎层（插件化）──────────┐
│  InnoDB   MyISAM   Memory   Archive     │
│  ├─ Buffer Pool                          │
│  ├─ undo log / redo log                  │
│  └─ 数据文件 (.ibd)                      │
└─────────────────┬──────────────────────┘
▼
磁盘 / 文件系统
```

分两层的目的：

- **Server 层**：所有*跨引擎*的通用功能都放这里 —— 连接管理、SQL 解析、执行计划生成、内置函数（date、md5、count 等）、视图、存储过程、触发器、binlog。

- **存储引擎层**：插件式架构，负责*数据的存与取*。InnoDB 是 5.5 之后的默认引擎，也是唯一支持事务的主流引擎。

好处：**换引擎不用换 SQL**。同一条 `SELECT * FROM t` 走 InnoDB 还是 MyISAM，Server 层完全不需要改。

追问 InnoDB 和 MyISAM 最本质的区别是什么？

三条底线区别：**(1) 事务** —— InnoDB 支持 ACID，MyISAM 不支持；**(2) 行锁** —— InnoDB 行级锁，MyISAM 只有表锁；**(3) 外键 & 崩溃恢复** —— InnoDB 支持外键、有 redo log 崩溃恢复能力，MyISAM 都没有。所以生产环境 *基本只用 InnoDB*，MyISAM 只在只读、纯统计的场景才可能选用。

## 面试场景 2：Server 层的五大模块分别干什么？

模块职责关键动作

**连接器**建立/管理连接，做身份认证 & 权限校验三次握手 → 校验账号密码 → 拉一次权限表缓存到连接里
**查询缓存**SQL 文本→结果集的 KV 缓存（8.0 移除）整条 SQL 作为 key 精确 hash 匹配；表一变全清空
**分析器**把 SQL 文本变成结构化 AST词法分析 → 语法分析 → 生成语法树
**优化器**决定「怎么执行」选索引、决定多表 JOIN 顺序、判断是否覆盖索引、成本估算
**执行器**真正调用引擎接口取数据执行前二次权限校验 → 循环调 `ha_read_first_row` / `ha_next_row`

易错点 权限校验其实做了**两次**：连接器建连时校验一次（拿到该账号能访问哪些库/表的*缓存快照*），执行器执行前再校验一次（针对具体要碰的表 / 列 / 视图）。所以中途 `REVOKE` 权限，已经建好的连接*还是能查的*，要等它重连才生效。

追问 分析器和优化器的分工是怎么划的？

**分析器只管「合不合法」**：SQL 关键字对不对、字段名有没有拼错、语法结构完不完整，产出一棵语法树。**优化器只管「怎么跑最省」**：一棵合法的树可能有 N 种执行方式（走 A 索引还是 B 索引？先 JOIN t1 还是先 JOIN t2？），优化器基于统计信息估算成本，挑一个最低成本的执行计划出来。

## 面试场景 3：一条 SELECT 的完整执行流程 ⭐背下来

🎤 面试官

拿 `SELECT * FROM users WHERE id = 1` 举例，从我在客户端按下回车开始，MySQL 内部完整走了什么？

🧑‍💻 你

```
[客户端] mysql> SELECT * FROM users WHERE id = 1;
│
│  ① TCP 连接 + 用户名/密码认证
▼
[连接器] 校验通过，把该账号的权限拉一份到连接里
│
│  ② 8.0 之前：先查 Query Cache
│  hash(SQL) 命中 → 直接返回结果，跳过后续所有步骤
│  未命中 / 8.0+ → 继续
▼
[查询缓存] miss，继续走
│
│  ③ 词法 + 语法分析，产出语法树 AST
▼
[分析器] 识别关键字 SELECT / FROM / WHERE
校验表 users 存在、字段 id 存在
│
│  ④ 基于成本估算选执行计划
▼
[优化器] 决定：走主键索引 PRIMARY(id)，type = const
产出 execution plan
│
│  ⑤ 二次权限校验（对 users 表的 SELECT 权限）
▼
[执行器] 调 InnoDB 的 handler API
│
│  ha_index_read_map(PRIMARY, id=1)
▼
[InnoDB] 先查 Buffer Pool
命中 → 直接返回行
未命中 → 从 .ibd 磁盘文件读 16KB 数据页到 Buffer Pool
│
▼
[执行器] 拿到行，做最终过滤/投影，把结果集回传给客户端
```

面试答的时候至少说清楚 **连接器 → 分析器 → 优化器 → 执行器 → 引擎** 这 5 步，加上「查询缓存 8.0 已移除」这个细节，基本满分。

追问 「MySQL 的 order of execution」是什么？是不是就是上面这条链路？

不是！SQL *关键字的执行顺序* 和 *模块调用顺序* 是两回事。SQL 逻辑上的执行顺序（也就是优化器给出的执行计划语义）是：

`FROM → ON → JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`

这也解释了为什么 `SELECT` 里定义的别名不能在 `WHERE` 里用（因为 SELECT 后于 WHERE）—— 但可以在 `ORDER BY` 里用（因为 ORDER BY 后于 SELECT）。

追问 `LIMIT 1` 能不能让全表扫描提前终止？

要看能不能走索引。**能走索引定位**（例如 `WHERE id = 1 LIMIT 1`）：引擎读到第一行满足条件就交给执行器，执行器判断已经够 1 行了，立刻停止调 `ha_next_row` —— 是真的能提前退出。**如果本身就是全表扫**（例如 `SELECT * FROM t LIMIT 1` 无 WHERE）：确实也只读一行就返回，但如果带了 `ORDER BY 非索引列 LIMIT 1`，就得先全表扫排序再取第一条，*LIMIT 1 拦不住*。

## 面试场景 4：一条 UPDATE 的完整执行流程 ⭐核心，涉及日志

🎤 面试官

`UPDATE users SET name = 'Tom' WHERE id = 1` 完整执行过程是什么？和 SELECT 的最大区别在哪？

🧑‍💻 你

UPDATE 前半段和 SELECT 一样走 Server 层，**关键区别在于要写三份日志 + 两阶段提交**：

```
[Server 层] 连接器 → 分析器 → 优化器 → 执行器
│
│  ① 先 SELECT 定位 id=1 的行
▼
[InnoDB]  从 Buffer Pool / 磁盘拿到旧行 (name='Jerry')
│
│  ② 把「旧值」写入 undo log（用于回滚 & MVCC）
▼
undo log: name Jerry→
│
│  ③ 在 Buffer Pool 里把 name 改成 'Tom'
│     （这时磁盘还是旧值，页变成「脏页」）
▼
dirty page in Buffer Pool
│
│  ④ 写 redo log，状态 = prepare
▼
redo log: [PREPARE] update users id=1
│
│  ⑤ Server 层写 binlog（归档日志）
▼
[Server 层]                            binlog: UPDATE users SET name='Tom'...
│
│  ⑥ 引擎把 redo log 改成 commit 状态
▼
[InnoDB]                               redo log: [COMMIT]
│
▼
UPDATE 返回成功
```

三份日志各司其职：

- **undo log**（引擎层，InnoDB）：记录「反向操作」，用于事务回滚 + MVCC 读旧版本。

- **redo log**（引擎层，InnoDB）：物理日志，记录「哪个数据页做了什么改」，用于崩溃恢复（宕机后重放脏页丢失的修改）。

- **binlog**（Server 层，所有引擎共享）：逻辑日志，记录「这条 SQL 干了什么」，用于主从复制 + 数据恢复。

redo log 分 **prepare / commit 两个状态**，中间夹着 binlog 的写入 —— 这就是 *两阶段提交（2PC）*，用来保证 redo 和 binlog 一致，见场景 10。

易错点 「更新数据是先写日志还是先改磁盘？」这是 **WAL（Write-Ahead Logging）**：*先写日志，再改磁盘*。改内存页 → 写 redo log 是很快的顺序 IO；脏页刷回磁盘是随机 IO，可以异步慢慢做。就算刷盘之前宕机，重启后拿 redo log 重放就能恢复。这就是「内存改完 + 日志落盘 = 就算成功」的底气。

## 面试场景 5：为什么 MySQL 8.0 移除了查询缓存？

🧑‍💻 你

三条硬伤，加起来收益不抵成本：

1. **失效粒度太粗**：查询缓存以「表」为单位失效。只要某张表发生 `INSERT / UPDATE / DELETE`，*与该表相关的所有缓存全部清空*。写多的表基本没意义。

2. **命中要求极苛刻**：SQL 文本必须*完全字节级一致*才能命中。多一个空格、大小写不同、注释不同、参数变了都算 miss。加上 `NOW()`、`CURRENT_USER()` 这类不确定函数根本不进缓存。

3. **维护成本高**：每次读要查 hash，每次写要清缓存，全局大锁 `Qcache_lock` 竞争激烈，反而拖慢并发。

实测下来大部分场景命中率 <10%，而维护开销一直在扣分。所以 8.0 直接删掉。**需要缓存请上应用层**（Redis / Caffeine），粒度可控、命中率可控、失效策略可控。

追问 5.7 上怎么关掉查询缓存？

两种：**(1) 会话级** —— SQL 前加 `SQL_NO_CACHE` 提示；**(2) 全局关闭** —— `my.cnf` 里 `query_cache_type = 0` 且 `query_cache_size = 0`。生产环境几乎一定关掉。

## 面试场景 6：连接器 —— 长连接 vs 短连接怎么选？

🧑‍💻 你

先看区别：

- **短连接**：每次执行 SQL 都新建连接，用完关闭。省内存、连接数少，但每次都有 *TCP 三次握手 + MySQL 认证* 开销（认证要查权限表，几毫秒起步）。

- **长连接**：一次建连后长期复用（配合连接池，如 HikariCP、Druid）。省掉重复认证开销，QPS 高的应用*基本都用长连接*。

但长连接有个隐藏坑：**连接内存不释放**。MySQL 里执行 SQL 用到的临时内存（排序缓冲、临时表、prepared statement 缓存）都挂在*连接对象*上，只有连接断开才回收。跑得久了单个连接可能吃到几十 MB 甚至几百 MB，最终触发 OOM Killer 把 `mysqld` 干掉。

追问 长连接积累的内存怎么解决？

三条常用手段：**(1)** *定期断开重连*：连接池设置 `maxLifetime`（HikariCP 默认 30 分钟），到期强制换新连接；**(2)** *执行 `mysql_reset_connection`*：MySQL 5.7+ 提供的 API，在不断开连接的情况下把连接资源重置回刚建连时的状态，权限不用重认；**(3)** *限制单连接内存*：`tmp_table_size`、`sort_buffer_size` 别调过大 —— 这些是*每连接分配*的。

陷阱 `wait_timeout`（服务端主动断开空闲连接的时长，默认 8 小时）和连接池的 `maxLifetime` 要配合好。如果 `maxLifetime > wait_timeout`，会经典报错 `Communications link failure / The last packet successfully received from the server was N ms ago` —— 应用池里持有的连接已经被服务端悄悄断了。规矩：*maxLifetime 至少比 wait_timeout 小 30 秒*。

## 面试场景 7：分析器 —— 词法分析 vs 语法分析

🧑‍💻 你

分析器做两件事：

1. **词法分析（Lexical Analysis）**：把 SQL 字符串切成一个个 *Token*。识别关键字（`SELECT`、`FROM`）、标识符（`users`、`id`）、字面量（`1`、`'Tom'`）、操作符（`=`、`>`）。

2. **语法分析（Syntactic Analysis）**：把 Token 序列按 SQL 语法规则组装成*语法树 AST*。检查 `SELECT ... FROM ... WHERE ...` 的结构是否正确。语法错误在这里报 `You have an error in your SQL syntax`。

常见误区：「字段/表存不存在也在分析器阶段判断」—— 严格说这一步归到 Server 层「预处理器（Preprocessor）」，在分析器之后、优化器之前。但面试口径上把它算进「分析器」也算过关。

追问 `select * from t where id = 1` 把表名写错成 `tt` 会在哪一步报错？

词法/语法分析都能过（`tt` 是合法标识符），但**预处理阶段**会去校验元数据，发现表不存在，报 `Table 'test.tt' doesn't exist`。所以这个错并不是「语法错误」而是「语义错误」，报错栈也不同。

## 面试场景 8：优化器怎么选索引？

🧑‍💻 你

MySQL 的优化器是 **CBO（Cost-Based Optimizer，基于成本的优化器）**，不是硬编码规则，而是*算成本*。核心公式：

`Cost = IO_cost + CPU_cost`

估算时会看：

- **索引选择性**：`Cardinality / Total_rows` 越接近 1，选择性越高（越接近唯一）。选择性高的索引更值得走。

- **预估回表次数**：走二级索引后如果要回表拿 `SELECT *` 的字段，回表次数越多成本越高。

- **是否覆盖索引**：要查的字段全在索引里（不用回表），成本骤降。

- **JOIN 顺序**：多表 JOIN 时，小表驱动大表通常更省。

统计信息不是实时的，是 *采样估算*（InnoDB 默认采样 20 页）。所以偶尔会选错索引 —— 这时候可以用 `FORCE INDEX(...)` 强制指定，或者 `ANALYZE TABLE t` 让它重新统计。

追问 优化器选错索引了怎么办？

四板斧从轻到重：**(1)** `ANALYZE TABLE` 重算统计信息（80% 的选错都是统计信息陈旧）；**(2)** 改 SQL 让优化器更容易看懂（比如把 `OR` 改成 `UNION`，把隐式类型转换消掉）；**(3)** `FORCE INDEX(idx_name)` 硬指定；**(4)** 最后手段：`optimizer_switch` 关掉特定优化，或者用 optimizer hints（`/*+ INDEX(t idx) */`）。

## 面试场景 9：执行器怎么与引擎交互？

🧑‍💻 你

执行器**不直接读磁盘**，只通过 *handler API（也叫 storage engine API）*调用引擎接口，逐行取。伪代码：

```
// 执行器视角（简化伪代码）
handler.ha_index_init(idx);              // 打开索引
row = handler.ha_index_read_map(key);    // 取第一行
while (row != NULL) {
if (row 满足剩余 WHERE) {              // Server 层过滤
emit(row);                        // 交给客户端
}
row = handler.ha_index_next();       // 取下一行
}
handler.ha_index_end();
```

这里有个关键优化 —— **索引条件下推 ICP（Index Condition Pushdown，MySQL 5.6+）**：原本 *只有* 索引前缀条件能在引擎层过滤，其余 WHERE 拉回 Server 层再判断。ICP 把「能用索引列判断」的条件也推到引擎层，*在读索引时就过滤掉不满足的行*，减少回表次数。

追问 ICP 的具体例子？

假设联合索引 `(name, age)`，SQL 是 `WHERE name LIKE '张%' AND age = 20`。**没有 ICP**：引擎只能用 `name LIKE '张%'` 走索引拿到所有姓张的记录（可能上万条），全部回表拿 age 再判断 —— 大量无效回表。**有 ICP**：引擎读索引记录时顺手判断 `age = 20`，不满足的直接跳过，*只回表真正满足的行*。`EXPLAIN` 的 `Extra` 列会显示 `Using index condition`。

追问 慢查询里看到 `Rows_examined` 很大是什么意思？

`Rows_examined` = *执行器让引擎扫过的行数*。如果比 `Rows_sent`（真正返回的行数）大很多，说明*大量扫过的行被过滤掉了*，索引很可能不合适。理想是两者接近。

## 面试场景 10：两阶段提交 —— redo log 和 binlog 怎么保证一致？⭐核心

🎤 面试官

为什么 UPDATE 要搞两阶段提交这么复杂？直接顺序写 redo log 和 binlog 不行吗？

🧑‍💻 你

核心目的：**保证 redo log（用于崩溃恢复本机）和 binlog（用于主从复制到从库）内容一致**。如果两个日志不一致，主从数据就会分叉。

假设没有两阶段提交，会怎么样？两种顺序都不行：

1. **先写 redo，再写 binlog**：写完 redo 就崩了，主库重启后重放 redo 生效了这条修改；但 binlog 没写，从库*不知道这个修改* —— 主从数据不一致。

2. **先写 binlog，再写 redo**：写完 binlog 就崩了，binlog 已经带过去从库了；但 redo 没写，主库重启后*看不到这个修改* —— 又不一致。

两阶段提交怎么解决？*把 redo log 的写入拆成 prepare 和 commit 两步，中间夹着 binlog*：

```
① redo log 写 PREPARE  ─┐
│
② binlog 写入          │  ← 崩溃发生在这三个点，都能一致地恢复
│
③ redo log 写 COMMIT  ─┘
```

崩溃恢复时的仲裁规则：

- 如果 redo 是 `commit`：直接提交。

- 如果 redo 是 `prepare`：*去看 binlog 是否完整*（每条 binlog 有 XID 和结束标志）—— binlog 完整就把 redo 提交（因为 binlog 已经/会被从库消费），binlog 不完整就*回滚*这条事务。

这样无论崩在哪一步，主库最终状态和 binlog 传给从库的状态都一致。

追问 具体来说，「binlog 写了但 redo 还没 commit 就崩了」会怎么恢复？

重启后 InnoDB 扫描 redo log，找到处于 `prepare` 状态的事务，拿它的 **XID** 去 binlog 里找 —— 如果 binlog 里有完整的这条事务（含结束标记 `Xid_log_event`），就把 redo *补一个 commit*，事务生效；如果 binlog 没写完（连结束标记都没有），说明这条事务客户端根本没收到成功响应，直接*回滚*。这样即使 binlog 已经传到从库，主库也会跟上；如果 binlog 传输失败，主库回滚，从库那边也不会应用（因为 binlog 不完整不会被复制）。

追问 两阶段提交是不是每次都要 `fsync` 刷盘？性能怎么样？

是的，为了「不丢数据」，理论上 redo log 的 prepare、binlog、redo log 的 commit 三步都要落盘。控制参数是 `innodb_flush_log_at_trx_commit`（redo）和 `sync_binlog`（binlog），生产环境双 1 配置（都设为 1）最安全但最慢。MySQL 用 **组提交（group commit）**把多个并发事务的日志合并一次 `fsync`，摊薄开销。追高吞吐时可以调成 `innodb_flush_log_at_trx_commit=2`（每秒刷）+ `sync_binlog=100`（每 100 事务刷），代价是宕机可能丢最后一秒的数据。

## 💻 代码验证（打开 MySQL 跑一遍）

### 验证 1：看 MySQL 版本和是否还有查询缓存

```
-- 看版本
SELECT VERSION();
-- 5.7.x：还有查询缓存
-- 8.0.x：查询缓存已被彻底删除

-- 5.7 才有的变量，8.0 直接不存在
SHOW VARIABLES LIKE 'query_cache%';
-- 5.7 输出：
-- query_cache_type    OFF/ON/DEMAND
-- query_cache_size    1048576
-- 8.0 输出：Empty set  ← 变量都没了
```

### 验证 2：EXPLAIN 看优化器选的执行计划

```
CREATE TABLE users (
id      BIGINT PRIMARY KEY,
name    VARCHAR(64),
age     INT,
email   VARCHAR(128),
KEY idx_name_age (name, age)
);

-- 主键等值查询：type=const，成本最低
EXPLAIN SELECT * FROM users WHERE id = 1;
-- +----+-------------+-------+-------+---------------+---------+---------+
-- | id | select_type | table | type  | key           | key_len | rows    |
-- +----+-------------+-------+-------+---------------+---------+---------+
-- |  1 | SIMPLE      | users | const | PRIMARY       | 8       |    1    |
-- +----+-------------+-------+-------+---------------+---------+---------+

-- 走联合索引前缀 + ICP
EXPLAIN SELECT * FROM users WHERE name LIKE '张%' AND age = 20;
-- Extra: Using index condition  ← ICP 生效

-- 覆盖索引（不回表）
EXPLAIN SELECT name, age FROM users WHERE name = '张三';
-- Extra: Using index  ← 只读索引就够了
```

### 验证 3：观察分析器 vs 预处理的错误信息差异

```
-- 语法错误（分析器报）
SELCT * FROM users;
-- ERROR 1064 (42000): You have an error in your SQL syntax;
-- check the manual that corresponds to your MySQL server version...

-- 语义错误（预处理器报，语法没问题但表不存在）
SELECT * FROM users_typo;
-- ERROR 1146 (42S02): Table 'test.users_typo' doesn't exist

-- 字段错误
SELECT nam FROM users;  -- name 拼错
-- ERROR 1054 (42S22): Unknown column 'nam' in 'field list'
```

### 验证 4：用 `SHOW PROFILE` 观察一条 SQL 内部的耗时分布（5.7）

```
-- 打开 profile
SET profiling = 1;

-- 跑一条 SQL
SELECT * FROM users WHERE id = 1;

-- 看内部各阶段耗时
SHOW PROFILES;
-- +----------+------------+----------------------------------+
-- | Query_ID | Duration   | Query                            |
-- +----------+------------+----------------------------------+
-- |        1 | 0.00023450 | SELECT * FROM users WHERE id = 1 |
-- +----------+------------+----------------------------------+

SHOW PROFILE FOR QUERY 1;
-- +----------------------+----------+
-- | Status               | Duration |
-- +----------------------+----------+
-- | starting             | 0.000053 |
-- | Waiting for lock     | 0.000004 |
-- | checking permissions | 0.000005 |  ← 连接器/执行器权限校验
-- | Opening tables       | 0.000019 |
-- | init                 | 0.000007 |
-- | System lock          | 0.000005 |
-- | optimizing           | 0.000006 |  ← 优化器
-- | statistics           | 0.000019 |
-- | preparing            | 0.000010 |  ← 预处理
-- | executing            | 0.000002 |  ← 执行器
-- | Sending data         | 0.000025 |  ← 引擎取数据
-- | end                  | 0.000004 |
-- | query end            | 0.000003 |
-- | closing tables       | 0.000006 |
-- | freeing items        | 0.000038 |
-- | cleaning up          | 0.000012 |
-- +----------------------+----------+
-- 一条 SQL 的所有内部阶段一目了然
-- 注：MySQL 8.0 已弃用 SHOW PROFILE，改用 performance_schema
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 完整说出一条 SELECT 从客户端到磁盘的执行链路，包含每一步做什么。</summary>

客户端 → **连接器**（TCP 建连 + 认证）→ **查询缓存**（8.0 已移除，5.7 命中直接返回）→ **分析器**（词法 + 语法 → AST）→ **优化器**（成本估算选执行计划）→ **执行器**（二次权限校验 → 调 handler API）→ **存储引擎**（Buffer Pool → 磁盘取数据）→ 结果集回传客户端。

</details>

<details>

<summary>Q2 一条 UPDATE 相比 SELECT 多做了哪些事？为什么要两阶段提交？</summary>

UPDATE 走完 Server 层后，引擎层要额外做：*写 undo log（旧值）→ 改 Buffer Pool 中数据页 → 写 redo log(prepare) → Server 层写 binlog → 写 redo log(commit)*。两阶段提交是把 redo 拆成 prepare/commit 夹住 binlog，保证 **redo 和 binlog 的一致性**：无论崩溃在哪一步，重启后通过 XID 匹配 binlog 完整性来决定提交或回滚，避免主从数据分叉。

</details>

<details>

<summary>Q3 MySQL 8.0 为什么删除查询缓存？</summary>

三条硬伤：**(1)** 失效粒度是「表」，任何写都清空该表所有缓存；**(2)** SQL 文本必须字节级一致才命中，命中率极低；**(3)** 维护成本高，全局锁竞争严重。收益不抵成本，缓存应该由应用层（Redis）以业务粒度控制。

</details>

<details>

<summary>Q4 Server 层和存储引擎层分别负责什么？为什么这么分？</summary>

Server 层负责*所有跨引擎的通用功能*：连接、SQL 解析、优化、执行、内置函数、视图、存储过程、binlog。存储引擎层负责*数据的实际存储和提取*，插件化设计，InnoDB 是默认。分层的好处是**换引擎不用改 SQL**，同一条 SQL 走 InnoDB 或 MyISAM 语义一致；SQL 层可以复用大量通用逻辑。

</details>

<details>

<summary>Q5 长连接积累内存的问题怎么解决？</summary>

三种手段：**(1) 定期断开重连**（连接池设 `maxLifetime`）；**(2) 执行 `mysql_reset_connection`**（5.7+，重置连接内部状态但不断连、不用重新认证）；**(3) 限制单连接内存参数**（`sort_buffer_size`、`tmp_table_size` 别设太大 —— 这些是每连接分配的）。另外注意 `maxLifetime` 要小于服务端的 `wait_timeout`，否则会拿到已被服务端断开的死连接。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- MySQL 8.0 Reference · Pluggable Storage Engine Architecture —— 存储引擎插件化官方说明

- MySQL 8.0 Reference · The Binary Log —— binlog 详解

#### 🔗 关联课件

- （上一课，架构总览）

- （下一课，优化器为什么选那个索引？）

- （本课两阶段提交的完整背景）

#### 🧭 下一课预告

Lesson 0043：**MySQL 索引 —— B+ 树、聚簇/二级、覆盖索引、最左前缀** —— 面试最高频的一课，直接决定你懂不懂优化器为什么选那个索引。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


