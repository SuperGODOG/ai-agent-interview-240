> Lesson 0048 · 阶段六 · MySQL · ⭐⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0048 · MySQL 锁全景

接 和 ，这一课看事务并发控制的另一半 —— 锁。**MVCC 让「读」不阻塞「读/写」；锁保证「写」的正确性 + 「当前读」的隔离**。面试常问：间隙锁怎么防幻读？死锁怎么排查？

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 InnoDB 的行锁加在什么上？没走索引会怎样？</summary>

加在**索引**上（不是数据行）。没走索引 → 全表所有索引都要锁 → 相当于表锁。第 5 题细讲。

</details>

<details>

<summary>Q0.2 间隙锁是 RR 才有的吗？</summary>

是的。**只在 REPEATABLE READ** 隔离级别下生效；`READ COMMITTED` 下 InnoDB 会禁用间隙锁，只留行锁。第 7 题细讲。

</details>

## 面试场景 1：MySQL 锁的分类维度

🧑‍💻 你

按四个维度分：

- **粒度**：全局锁（整库）→ 表级锁 → 行级锁

- **模式**：共享锁 S / 排他锁 X / 意向锁 IS / IX

- **算法**（行锁的三种形式）：记录锁 Record / 间隙锁 Gap / Next-Key Lock

- **思想**：悲观锁（`SELECT FOR UPDATE` 直接加锁）vs 乐观锁（version 字段 + UPDATE 校验）

## 面试场景 2：全局锁 FTWRL

🧑‍💻 你

`FLUSH TABLES WITH READ LOCK`（FTWRL）—— 让整个 MySQL 实例进入*只读*状态。所有 DDL/DML 都会阻塞。

典型用途：**全库逻辑备份**（`mysqldump`）。但生产上更推荐 `mysqldump --single-transaction`：InnoDB 用 MVCC 快照做备份，不用 FTWRL 也能得到一致性，且不阻塞业务。

## 面试场景 3：表级锁 & 元数据锁 MDL

🧑‍💻 你

- **MyISAM**：*只有*表锁，粒度粗；早已被 InnoDB 淘汰。

- **InnoDB**：主推行锁，但也有表锁；显式 `LOCK TABLES ... READ/WRITE` 一般不用。

- **元数据锁 MDL**（Metadata Lock）：自动加，无需显式；*DML 加 MDL 读锁*（互相兼容），*DDL 加 MDL 写锁*（和读、写都互斥）。这就是「线上 ALTER TABLE 会卡死所有查询」的原因。

- **解决方案**：pt-online-schema-change / gh-ost 等在线 DDL 工具，本质是「创建影子表 → 双写 → 切换」避开 MDL 长时间锁。

## 面试场景 4：意向锁 IS/IX（★核心）

🎤 面试官

什么是意向锁？为什么要设计意向锁？

🧑‍💻 你

**意向锁**是表级的*意图*标记：

- **IS**（Intention Shared）：事务要在某行加 S 锁前，先在表上加 IS

- **IX**（Intention Exclusive）：事务要在某行加 X 锁前，先在表上加 IX

作用：*加速判断「表上有没有行锁」*。如果要加表级 X 锁，只需看表上有没有 IS/IX 就知道；**不用扫全表逐行检查**。

兼容性：意向锁之间*互相兼容*（IS/IX 都是意图，不冲突）；意向锁只和*表级* S/X 冲突。

XIXSIS

**X**✗✗✗✗
**IX**✗✓✗✓
**S**✗✗✓✓
**IS**✗✓✓✓

## 面试场景 5：InnoDB 行锁（★核心）

🎤 面试官

InnoDB 的行锁加在哪？如果 WHERE 条件没走索引会怎样？

🧑‍💻 你

**行锁加在索引记录上**，不是加在数据行上。这个理解非常关键：

- `WHERE id = 1`（主键索引）：只锁 id=1 这一条索引记录

- `WHERE name = 'Alice'`（有 name 索引）：锁 name 索引上的对应记录 + 通过主键回表锁数据行

- `WHERE age = 30`（*没有 age 索引*）：InnoDB 无法定位具体行，只能**扫全表锁所有行** —— 相当于表锁！生产事故常客。

陷阱 UPDATE / DELETE 的 WHERE 条件**务必走索引**，否则整个表被锁住，其他事务全部挂起。上线前用 explain 确认 type ≠ ALL。

## 面试场景 6：共享锁 S 和排他锁 X

🧑‍💻 你

```
-- 显式加 S 锁（读锁）
SELECT * FROM t WHERE id = 1 LOCK IN SHARE MODE;
-- MySQL 8+ 新语法：
SELECT * FROM t WHERE id = 1 FOR SHARE;

-- 显式加 X 锁（写锁）
SELECT * FROM t WHERE id = 1 FOR UPDATE;

-- 隐式加 X 锁
UPDATE t SET name = 'Bob' WHERE id = 1;
DELETE FROM t WHERE id = 1;
INSERT INTO t VALUES (...);
```

兼容规则：S ↔ S 兼容；X 与所有互斥。所以两个事务可以同时 `FOR SHARE`；但一个 `FOR UPDATE` 会阻塞其他所有事务的锁请求。

## 面试场景 7：Record / Gap / Next-Key Lock（★核心）

🧑‍💻 你

InnoDB 行锁其实是三种算法：

- **Record Lock**（记录锁）：锁一条*存在*的索引记录。例如 `WHERE id=5 FOR UPDATE` 且 id=5 存在。

- **Gap Lock**（间隙锁）：锁两条记录之间的*间隙*（左开右开）。目的：**阻止其他事务在这个间隙内 INSERT**。

- **Next-Key Lock**：Record + Gap 的组合，锁「一条记录 + 前面的间隙」（左开右闭）。*RR 下 InnoDB 默认加 Next-Key Lock*。

示例：表里有 id=1, 5, 10 三条记录。`SELECT * FROM t WHERE id BETWEEN 3 AND 8 FOR UPDATE`（RR 下）：

- 锁 id=5 的记录（Record Lock）

- 锁 (1, 5] 和 (5, 10] 两段 Next-Key Lock —— 其他事务不能在 [2,4]、[6,9] 中间 INSERT

追问 唯一索引等值查询会退化吗？

会。唯一索引 + 等值 + 记录存在 → **退化为 Record Lock**（不需要 Gap 因为唯一了不会有幻读）；记录不存在 → 退化为 Gap Lock。

## 面试场景 8：间隙锁怎么防幻读（★经典）

🧑‍💻 你

回顾 0046：*幻读* = 同一事务两次范围查询结果集不同。InnoDB RR 的解法：

1. **快照读**（普通 SELECT）：走 MVCC，用同一 ReadView，天然看不到新 INSERT

2. **当前读**（`FOR UPDATE`、UPDATE、DELETE）：加 **Next-Key Lock**，锁住范围内的*间隙* → 其他事务无法 INSERT → 避免幻读

所以 InnoDB RR*大部分场景*没有幻读。少数场景（先快照读、再当前读）仍可能看到「快照没有的新行」，理论上仍属幻读。

## 面试场景 9：死锁场景与排查（★经典）

🎤 面试官

线上出现死锁，你怎么排查？

🧑‍💻 你

经典死锁场景：事务 A 持有行 1 的 X 锁要申请行 2 的 X 锁；事务 B 持有行 2 的 X 锁要申请行 1 的 X 锁 —— *循环等待*。

排查三步走：

1. `SHOW ENGINE INNODB STATUS\G`，看 **LATEST DETECTED DEADLOCK** 段：涉及的表、SQL、锁类型、等待关系

2. 结合业务日志（应用侧的堆栈 + 事务 ID）定位是哪两个业务操作冲突

3. 看是否有加锁顺序不一致的问题

**InnoDB 有自动死锁检测**（`innodb_deadlock_detect=on`）：形成环时回滚*影响行数少*的事务；应用需要捕获 `SQLState=40001` 或错误码 1213 并重试。

**避免策略**：固定加锁顺序（如全项目都按 id 升序锁）、减小事务粒度、加索引减少锁范围、大事务拆小事务。

追问 死锁检测算法开销大吗？

大。每加新锁都要遍历*等待图*找环。高并发下 CPU 消耗明显。极致性能场景可关：`innodb_deadlock_detect=off` + `innodb_lock_wait_timeout` 设小值（1-2s）快速超时；但要保证业务能重试。

## 面试场景 10：乐观锁 vs 悲观锁在 MySQL 里的应用

🧑‍💻 你

**悲观锁**：`SELECT ... FOR UPDATE` 直接锁行 —— 适合冲突多的场景（订单库存扣减、幂等控制）

**乐观锁**（应用层）：给表加 `version` 字段，UPDATE 时校验：

```
UPDATE account SET balance = balance - 100, version = version + 1
WHERE id = 1 AND version = @old_version;
-- 若 affected rows = 0，说明有并发修改，业务层重试或报错
```

乐观锁本质是 *CAS 思想*（回顾 ）。**高并发 + 冲突低**时乐观锁完胜（无锁不阻塞）；*冲突频繁*时乐观锁重试太多反而不如悲观锁。

## 💻 代码验证

### 验证 1：观察间隙锁（RR 下）

```
-- 准备
CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(20));
INSERT INTO t VALUES (1, 'a'), (5, 'b'), (10, 'c');

-- 事务 A（终端 1）
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN;
SELECT * FROM t WHERE id BETWEEN 3 AND 8 FOR UPDATE;
-- 此时锁住 id=5 记录 + (1,5) (5,10) 间隙

-- 事务 B（终端 2）
BEGIN;
INSERT INTO t VALUES (2, 'x');   -- 阻塞！间隙锁挡住
INSERT INTO t VALUES (11, 'y');  -- 成功，11 在锁范围外
```

### 验证 2：无索引触发全表锁

```
CREATE TABLE t2 (id INT PRIMARY KEY, name VARCHAR(20), age INT);
-- age 列没有索引

-- 事务 A
BEGIN;
UPDATE t2 SET name = 'x' WHERE age = 30;
-- 由于 age 无索引，锁住所有行

-- 事务 B
UPDATE t2 SET name = 'y' WHERE id = 1;  -- 阻塞！
```

### 验证 3：死锁自动检测

```
-- 事务 A
BEGIN;
UPDATE t SET name='A1' WHERE id = 1;   -- 锁行 1
-- 停一下让 B 拿到行 2

-- 事务 B
BEGIN;
UPDATE t SET name='B2' WHERE id = 2;   -- 锁行 2
UPDATE t SET name='B1' WHERE id = 1;   -- 等 A 释放行 1

-- 事务 A
UPDATE t SET name='A2' WHERE id = 2;   -- 等 B 释放行 2 → 死锁！
-- InnoDB 检测到，回滚其中一个：
-- ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction

-- 查看死锁详情
SHOW ENGINE INNODB STATUS\G
```

### 验证 4：乐观锁 version 字段

```
CREATE TABLE account (
id INT PRIMARY KEY,
balance DECIMAL(10,2),
version INT DEFAULT 0
);

-- 应用层扣款流程
-- 1. 读
SELECT balance, version FROM account WHERE id = 1;
-- 假设 balance=1000, version=3

-- 2. 业务计算
-- new_balance = 1000 - 100 = 900

-- 3. CAS 写
UPDATE account
SET balance = 900, version = version + 1
WHERE id = 1 AND version = 3;
-- affected rows = 1 → 成功
-- affected rows = 0 → 有并发修改，业务重试
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 InnoDB 行锁加在哪？如果没走索引会发生什么？</summary>

加在**索引记录**上。没走索引 → 全表所有索引都要锁 → 相当于表锁，其他事务全部挂起。UPDATE/DELETE 前用 explain 确认 type ≠ ALL。

</details>

<details>

<summary>Q2 意向锁 IS/IX 为什么存在？</summary>

加速判断「表上有没有行锁」。加行锁前先加对应意向表锁；后来者要加表锁只需看表上有没有 IS/IX，不用扫全表逐行看。意向锁之间兼容，只和表级 S/X 冲突。

</details>

<details>

<summary>Q3 Record Lock / Gap Lock / Next-Key Lock 分别锁什么？</summary>

Record 锁一条存在的索引记录；Gap 锁两条记录之间的间隙（防 INSERT）；Next-Key = Record + Gap（左开右闭），InnoDB RR 下默认加这个。

</details>

<details>

<summary>Q4 间隙锁怎么防幻读？</summary>

锁住范围内的所有间隙 → 其他事务无法 INSERT 新行 → 同一事务两次范围查询结果集一致（当前读场景）。快照读场景则靠 MVCC 用同一 ReadView。

</details>

<details>

<summary>Q5 死锁怎么排查？</summary>

`SHOW ENGINE INNODB STATUS\G` 看 LATEST DETECTED DEADLOCK；InnoDB 自动检测环并回滚受影响行数少的事务；应用捕获 ERROR 1213 重试。避免：固定加锁顺序、减小事务、加索引减少锁范围。

</details>

#### 📖 原文

-

- MySQL Reference · InnoDB Locking（一手规范）

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0049：**MySQL 三大日志详解** —— redo log / undo log / binlog 分别做什么，两阶段提交为什么必需。

💬 想问「MDL 具体在什么时候升级？」「pt-osc 到底怎么绕过 MDL？」「乐观锁高并发下的重试放大问题？」—— 直接问我。


