> Lesson 0049 · 阶段六 · MySQL · ⭐⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0049 · MySQL 三大日志详解

覆盖 。三大日志是 **ACID 的 D（持久性） + 主从复制 + 备份恢复**的地基。面试三连击：三大日志各自做什么？为什么要两阶段提交？双 1 配置是啥？

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 三大日志分别属于 Server 层还是引擎层？</summary>

**redo/undo log** 是 InnoDB *引擎层*独有（其他引擎没有）；**binlog** 是 MySQL *Server 层*通用（所有引擎都有）。第 1 题细讲。

</details>

<details>

<summary>Q0.2 redo log 和 binlog 都记「写」，为什么不冗余？</summary>

用途完全不同：redo log 是*物理日志*用于崩溃恢复（每页的物理修改）；binlog 是*逻辑日志*用于主从复制和备份恢复（每条 SQL 或每行的变更）。层级也不同，是两个各司其职的组件。第 3 题细讲。

</details>

## 面试场景 1：三大日志速览（★核心）

日志所属层类型核心作用写入方式

**redo log**InnoDB 引擎层物理日志崩溃恢复（ACID 的 D）循环写
**undo log**InnoDB 引擎层逻辑日志回滚（A）+ MVCC 版本链随事务生成
**binlog**MySQL Server 层逻辑日志主从复制 + 备份恢复追加写

## 面试场景 2：redo log 详解（★核心）

🧑‍💻 你

**redo log 是物理日志**：记录「表空间号 + 数据页号 + 偏移量 + 修改后的值」这种物理修改。

关键特性：

- **顺序写**：追加到 redo log buffer → 刷到 redo log file（`ib_logfile0/1`）—— *顺序 IO 极快*

- **循环写 + 固定大小**：`innodb_log_file_size` 默认 48MB；write_pos 推进写入位置，checkpoint 推进清理位置；追上就要等 checkpoint 前移

- **WAL（Write-Ahead Logging）**：*先写 redo log，再刷数据页*；即使宕机，重启时用 redo log 恢复未刷盘的修改

为什么 redo log 能保证持久性？—— 事务提交前 redo log 已经 fsync 到磁盘，即使断电，重启后 InnoDB 重放 redo log 即可恢复。

## 面试场景 3：redo log 的刷盘策略（★核心）

🧑‍💻 你

参数 `innodb_flush_log_at_trx_commit`：

值行为崩溃丢失性能

**0**事务提交时不刷；后台每 1s 刷最多丢 1 秒数据最快
**1**（默认，推荐）每次事务提交都 fsync 到磁盘不丢最慢
**2**写到 OS page cache，每 1s fsyncMySQL 崩溃不丢；OS 崩溃丢 1s折中

陷阱 `innodb_flush_log_at_trx_commit=1` 才能真正保证 D（持久性），但每次事务都 fsync 性能会掉。金融/订单必须 =1；日志/统计可以 =2 换性能。

## 面试场景 4：undo log 详解

🧑‍💻 你

**undo log 是逻辑日志**：记录反向操作。

- INSERT → undo 里存 DELETE

- DELETE → undo 里存 INSERT（含原行数据）

- UPDATE → undo 里存原字段值

两大用途：

1. **事务回滚**：ROLLBACK 时按 undo log 反向执行 —— 保证原子性 A

2. **MVCC 版本链**：每行的 `DB_ROLL_PTR` 指向 undo log 里的旧版本，形成版本链供快照读回溯（回顾 ）

**undo log 的回收**：事务提交后 undo log 通过 *purge 线程*回收。但如果有**长事务**持有旧 ReadView，那么该事务开始时之后的所有 undo log 都不能 purge —— *撑爆 ibdata1 是生产事故常客*。

## 面试场景 5：binlog 详解

🧑‍💻 你

**binlog 是 Server 层的逻辑日志**，追加写不覆盖。用途：

- **主从复制**：主库把 binlog 传给从库回放

- **备份恢复**：结合全量备份 + binlog 增量，可恢复到*任意时间点*（Point-In-Time Recovery, PITR）

- **数据订阅**：Canal / Debezium 伪装成从库解析 binlog，供 ES/Redis 同步

## 面试场景 6：binlog 三种格式（★经典）

格式记录内容体积一致性典型问题

**STATEMENT**SQL 语句原文小可能不一致`NOW()` / `UUID()` 在主从执行结果不同
**ROW**（默认 5.7+）每行变更前后的完整值大绝对一致批量 UPDATE 影响 100 万行 → binlog 也 100 万条
**MIXED**自动选：确定的用 STATEMENT，不确定用 ROW中一致复杂度高，不推荐

MySQL 5.7 起 **ROW 是默认**，主从一致性优先。

## 面试场景 7：两阶段提交（★核心）

🎤 面试官

redo log 和 binlog 为什么要用两阶段提交？

🧑‍💻 你

为了保证**redo log 和 binlog 逻辑一致**—— 如果只有一个日志或不用两阶段，崩溃时可能出现「主库有从库无」或「主库无从库有」的数据不一致。

完整流程：

```
1. 事务开始，修改数据
2. redo log 写入 (prepare 状态)          ← ①
3. binlog 写入并 fsync                    ← ②
4. redo log 状态改为 commit               ← ③
5. 事务提交完成
```

**崩溃恢复逻辑**：重启时扫 redo log，对每条 prepare 状态的：

- 找对应 binlog（用 XID 关联）：*找到且完整* → 提交（补 commit 状态）

- 找不到 binlog 或不完整 → *回滚*该事务

这样保证 **redo log 已提交的事务 ⇔ binlog 已记录**，主从永远对齐。

追问 如果只有 redo log 没 binlog 会怎样？

崩溃恢复只能恢复到自己的数据；*从库根本不知道有过这些变更* → 主从从此不一致。加上 binlog 用于外部感知（复制、数据订阅），必须协调。

## 面试场景 8：双 1 配置（★核心）

🧑‍💻 你

「双 1 保证」是生产最严格的持久化配置：

- `innodb_flush_log_at_trx_commit = 1`：每事务 redo log fsync

- `sync_binlog = 1`：每事务 binlog fsync

`sync_binlog` 参数含义：

值行为

**0**write 到 OS cache，由 OS 决定何时 fsync（性能高，宕机丢）
**1**（推荐）每次事务提交都 fsync 到磁盘
**N**每 N 次事务批量 fsync（性能与安全折中）

双 1 会带来性能开销（每事务两次 fsync），高并发写场景可能瓶颈；但金融/订单/账户类*不能不用双 1*。日志/统计可以 `=2/N` 换性能。

## 面试场景 9：主从复制流程

🧑‍💻 你

```
┌────────┐          ┌────────────┐            ┌─────────┐
│   主库  │  binlog  │  从库 IO Thread │  relay log │ SQL Thread│
│ 写binlog│─────────▶│    拉取       │────────────▶│  回放    │
└────────┘          └────────────┘            └─────────┘
```

三大线程：

1. 主库 **Dump Thread**：推送 binlog 给从库

2. 从库 **IO Thread**：接收 binlog，写入本地 relay log（中继日志）

3. 从库 **SQL Thread**：读 relay log，回放 SQL / 应用 row 变更

复制模式：

- **异步（默认）**：主库写完 binlog 立即返回，不等从库；可能主库挂了从库还没同步 → 数据丢

- **半同步**（`rpl_semi_sync`）：至少一个从库 ACK 才响应客户端；折中安全

- **全同步**：所有从库 ACK 才响应；性能差几乎不用

## 面试场景 10：主从延迟排查

🧑‍💻 你

常见原因：

1. **SQL Thread 单线程回放跟不上主库并发** —— MySQL 5.7+ 支持并行复制 MTS（`slave_parallel_workers`）

2. **主库大事务**（一次 UPDATE 百万行）—— 从库要等整个事务 binlog 传完才能回放

3. **从库有慢 SQL 或 DDL 阻塞**

4. **网络抖动**影响 IO Thread 拉取

5. **从库负载高**（读写分离下从库 QPS 也大）

排查命令：

```
SHOW SLAVE STATUS\G
-- 关注：
--   Seconds_Behind_Master  ← 延迟秒数
--   Slave_IO_Running / Slave_SQL_Running  ← 两个线程是否正常
--   Last_IO_Error / Last_SQL_Error  ← 错误信息
```

业务侧：读写分离时可能读到旧数据 —— 强制走主 / 中间件路由（ShardingSphere）/ 关键读加 hint。

## 💻 代码验证

### 验证 1：查看当前 binlog 格式和位置

```
SHOW VARIABLES LIKE 'binlog_format';
-- +---------------+-------+
-- | Variable_name | Value |
-- +---------------+-------+
-- | binlog_format | ROW   |
-- +---------------+-------+

SHOW MASTER STATUS;
-- 显示当前 binlog 文件名 + Position

SHOW BINARY LOGS;
-- 列出所有 binlog 文件
```

### 验证 2：解析 binlog 内容

```
# mysqlbinlog 工具解析 binlog
mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000001

# ROW 格式下能看到每行变更前后镜像：
### UPDATE `test`.`account`
### WHERE
###   @1=1                    /* id */
###   @2=1000.00              /* balance BEFORE */
### SET
###   @1=1
###   @2=900.00               /* balance AFTER */
```

### 验证 3：检查双 1 配置

```
SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit';
-- 1 = 每事务刷（安全）
SHOW VARIABLES LIKE 'sync_binlog';
-- 1 = 每事务 fsync binlog

-- 临时修改（重启失效）
SET GLOBAL innodb_flush_log_at_trx_commit = 1;
SET GLOBAL sync_binlog = 1;
-- 永久修改要写 my.cnf
```

### 验证 4：主从复制状态检查

```
-- 在从库执行
SHOW SLAVE STATUS\G

-- 关键字段：
Slave_IO_Running: Yes         ← IO Thread 正常
Slave_SQL_Running: Yes        ← SQL Thread 正常
Seconds_Behind_Master: 0      ← 无延迟
Master_Log_File: mysql-bin.000010     ← 已读到的主库 binlog 文件
Read_Master_Log_Pos: 12345678         ← 位置
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 三大日志各自的用途？</summary>

redo log 崩溃恢复（保证 D）；undo log 回滚 + MVCC 版本链（保证 A）；binlog 主从复制 + 备份恢复。前两个在 InnoDB 引擎层，binlog 在 Server 层。

</details>

<details>

<summary>Q2 为什么要两阶段提交？崩溃恢复怎么用它？</summary>

保证 redo log 和 binlog 逻辑一致，避免主从数据分离。恢复时对 prepare 状态的 redo log：能找到对应完整 binlog → 提交；否则回滚。

</details>

<details>

<summary>Q3 双 1 配置具体是哪两个参数？作用？</summary>

`innodb_flush_log_at_trx_commit=1`（redo log 每事务 fsync）+ `sync_binlog=1`（binlog 每事务 fsync）。金融/订单场景必须双 1。

</details>

<details>

<summary>Q4 binlog 三种格式选哪个？</summary>

生产推荐 ROW（MySQL 5.7+ 默认）—— 绝对一致，代价是体积大。避免 STATEMENT（NOW/UUID 主从不一致）。MIXED 不推荐（复杂度高）。

</details>

<details>

<summary>Q5 主从延迟怎么排查？</summary>

`SHOW SLAVE STATUS` 看 `Seconds_Behind_Master` + 两个 Running 状态；常见原因：大事务、SQL Thread 单线程、DDL 阻塞、从库慢 SQL、网络。解法：并行复制 MTS、拆分大事务、从库避免读写。

</details>

#### 📖 原文

-

- MySQL Reference · The Binary Log（一手规范）

- MySQL Reference · InnoDB Redo Log

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0050：**MySQL 优化规范 & 备份恢复 & 自增主键** —— 阶段六收尾课，实战杂项打包。

💬 想问「redo log 循环写到底和 checkpoint 怎么协作？」「Canal 是怎么伪装从库的？」「半同步复制怎么开？」—— 直接问我。


