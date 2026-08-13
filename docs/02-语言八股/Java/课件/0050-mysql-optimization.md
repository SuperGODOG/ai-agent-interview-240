> Lesson 0050 · 阶段六 · MySQL 收尾 · ⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0050 · MySQL 优化规范 & 备份恢复

阶段六收尾课，把散落的工程细节打包成一节：、、、深分页优化。面试常问的实用题都在这里。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 InnoDB 自增主键一定连续吗？</summary>

**不一定**。INSERT 失败（主键冲突/字段校验）、事务回滚、批量 INSERT 分配都可能造成断层。业务不能依赖「自增连续」。第 7 题细讲。

</details>

<details>

<summary>Q0.2 `LIMIT 100000, 20` 慢在哪？怎么优化？</summary>

实际要扫描 100020 行然后丢弃前 100000。优化：① 用 `WHERE id > 上次最大 id LIMIT 20` 递进翻页；② 延迟关联 `JOIN (SELECT id FROM t ORDER BY id LIMIT 100000, 20)`。第 9 题细讲。

</details>

## 面试场景 1：表设计规范

🧑‍💻 你

- **单表数据量控制**：建议 500 万行以内。SSD + 简单结构可扩到几千万；机械盘 + 复杂结构 500 万就要考虑分表。超过阈值考虑分库分表或历史数据归档

- **字段尽量 NOT NULL + 默认值**：NULL 参与比较结果永远是 NULL；索引对 NULL 不友好；`WHERE col = NULL` 永远 false

- **禁用宽表**：字段太多会增加 IO 和 buffer pool 压力；如果业务只用其中一部分字段，考虑垂直拆分

- **主键推荐 BIGINT 自增**：顺序插入避免 B+ 树页分裂；空间利用率高；配合业务外的分布式 ID（雪花算法/Redis）也可

- **反范式冗余高频查询字段**：适度冗余避免多表 JOIN；如订单表冗余用户名/商品名

- **字符集统一 utf8mb4**：支持 emoji 和 4 字节字符；避免主从字符集不一致导致隐式转换

## 面试场景 2：字段类型选择

业务类型推荐字段类型不推荐 & 原因

整数（ID/年龄）`INT UNSIGNED` / `BIGINT UNSIGNED`用字符串存数字 → 索引大、比较慢
金额`DECIMAL(20,4)` 或 `BIGINT` 存分FLOAT/DOUBLE 精度损失（回顾 ）
短字符串（≤ 255）`VARCHAR(N)`CHAR 定长浪费空间（除非确实定长如 MD5/UUID）
长文本另存文件系统/OSS，DB 只存路径TEXT/BLOB 占 buffer pool、影响性能
时间`DATETIME`（无时区）或 `BIGINT` 存毫秒TIMESTAMP 2038 问题；字符串存时间无法排序
布尔`TINYINT(1)`MySQL 没有真正的 BOOLEAN 类型（是 TINYINT 别名）
枚举`TINYINT` 存 code 值 + 应用层映射ENUM 修改困难、跨语言支持差

陷阱 `TIMESTAMP` 存的是从 1970-01-01 UTC 起的秒数（int32），到 **2038-01-19 03:14:07** 就溢出了。新项目直接用 `DATETIME` 或 `BIGINT` 存毫秒时间戳；老系统也要提前规划迁移。

## 面试场景 3：SELECT 规范 —— 禁用 SELECT *

🧑‍💻 你

为什么不能 `SELECT *`？

1. **影响覆盖索引**：覆盖索引要求 SELECT 字段全在辅助索引里；* 一定包含非索引字段 → 必须回表

2. **网络带宽浪费**：宽表返回几十个字段，多数用不上

3. **Server 内存浪费**：查询缓存、临时表都变大

4. **字段变更影响业务**：表加字段业务侧代码可能出错（依赖字段顺序）

正确姿势：明确列出用到的字段，如 `SELECT id, name, status FROM t`。

## 面试场景 4：INSERT/UPDATE 规范

🧑‍💻 你

- **批量 INSERT**：一条语句多个值组，减少往返：`INSERT INTO t VALUES (1,'a'),(2,'b'),(3,'c')`；*百万级批量务必分批（1000-5000/批）*避免大事务

- **ON DUPLICATE KEY UPDATE**：唯一约束冲突时更新已有行，避免先查后写

- **避免大事务**：单事务时间过长导致 undo log 无法 purge、锁范围大、主从延迟

- **WHERE 必走索引**：否则 UPDATE/DELETE 全表锁（回顾 0048）

- **大表结构变更用 pt-osc / gh-ost**：直接 `ALTER TABLE` 会加 MDL 写锁阻塞所有查询

## 面试场景 5：索引规范

🧑‍💻 你

- **单表索引 ≤ 5 个**：索引多会增加 INSERT/UPDATE 成本 + 优化器选择时间

- **联合索引不超过 5 个字段**；把区分度高的放最左

- **避免冗余索引**：`(a, b, c)` 已存在时再建 `(a, b)` 就是冗余

- **区分度低不建索引**：如性别 boolean 建了也不走

- **频繁更新字段不建索引**：每次更新都要维护 B+ 树

- **长字符串用前缀索引**：`INDEX(name(10))`，但注意可能失去覆盖索引能力

## 面试场景 6：日期类型选择

类型字节范围时区推荐场景

`DATETIME`81000-01-01 ~ 9999-12-31不转换（存啥读啥）业务时间（订单创建、日志时间）
`TIMESTAMP`41970-01-01 ~ 2038-01-19写时按会话时区转 UTC，读时按会话时区转回老项目；*2038 问题*要小心
`DATE`31000-01-01 ~ 9999-12-31无时间部分生日、日期字段
`BIGINT`（存毫秒）8无限不涉及跨语言互通、避免时区问题；应用层格式化

## 面试场景 7：自增主键一定连续吗？（★经典）

🎤 面试官

InnoDB 自增主键一定连续吗？

🧑‍💻 你

**不一定**。原因有四个：

1. **INSERT 失败已分配值不回收**：`INSERT` 触发字段校验失败或唯一冲突时，自增计数器已经 +1 → 下次 INSERT 会跳过这个值

2. **事务回滚已分配值不回收**：`BEGIN; INSERT; ROLLBACK;` → 数据没插入但自增值前进了

3. **批量 INSERT 预分配多值**：`INSERT SELECT ...` 场景 InnoDB 会预估行数一次分配多个自增值，多余的不回退

4. **`innodb_autoinc_lock_mode` 参数影响**：

- 0 *traditional*：全语句持锁，最保守，连续

- 1 *consecutive*（8.0 前默认）：批量插入预分配，可能不连续

- 2 *interleaved*（8.0 默认）：更并发，主键更可能不连续

**结论**：业务上*不能依赖自增主键的连续性*。要连续序号请用应用层生成或数据库单独维护序列。

## 面试场景 8：备份策略

🧑‍💻 你

类型工具特点典型场景

**逻辑备份**`mysqldump`输出 SQL 文本；跨版本兼容；*大表慢，恢复更慢*小库、跨版本迁移
**物理备份**Percona `xtrabackup`拷贝 InnoDB 数据文件；快，恢复快；*同版本才能用*大库、生产日常备份
**热备**xtrabackup / mysqldump --single-transaction不停服；InnoDB 用 MVCC 快照读7×24 服务
**冷备**停服后拷贝 datadir停服影响业务已很少用

**PITR（Point-In-Time Recovery，任意时点恢复）**：全量备份 + 增量 binlog；

```
# 1. 恢复全量（假设 2026-07-27 00:00 备份）
xtrabackup --copy-back --target-dir=/backup/full

# 2. 用 binlog 增量恢复到指定时点（如 03:00）
mysqlbinlog --start-datetime="2026-07-27 00:00:01" \
--stop-datetime="2026-07-27 03:00:00" \
/var/lib/mysql/mysql-bin.00000{1,2,3} | mysql -u root -p
```

## 面试场景 9：深分页优化（★经典）

🎤 面试官

`SELECT * FROM t ORDER BY id LIMIT 100000, 20` 慢到爆，怎么优化？

🧑‍💻 你

慢的根源：LIMIT 100000, 20 *实际扫描 100020 行然后丢弃前 100000 行*；即使有 id 索引也要遍历这么多。

**方案 1：id 递进翻页（首选）** —— 用「上一页最大 id」做条件

```
-- ❌ 慢
SELECT * FROM t ORDER BY id LIMIT 100000, 20;

-- ✅ 快（要求前端传上一页最后一条的 id）
SELECT * FROM t WHERE id > 100000 ORDER BY id LIMIT 20;
-- 直接从索引定位到 100000 之后，只扫 20 行
```

**方案 2：延迟关联（不能改前端时用）**

```
SELECT t.*
FROM t
JOIN (SELECT id FROM t ORDER BY id LIMIT 100000, 20) x USING(id);
-- 内层子查询只扫索引（覆盖索引），拿到 20 个 id 后再回表
-- 相比原写法 * 号回表，速度快很多
```

**方案 3：业务层限制** —— 后端强制「最多允许翻到第 N 页」；Google/淘宝也不给你翻到 1000 页

## 面试场景 10：慢查询优化清单

🧑‍💻 你

1. **用 explain 看走没走索引**（回顾 0045）：type 从 ALL/index → range/ref/eq_ref/const 是优化方向

2. **加/改索引**：结合业务 SQL 的 WHERE/JOIN/ORDER BY/GROUP BY

3. **消除 Using filesort**：让 ORDER BY 字段能用有序索引

4. **消除 Using temporary**：调整 GROUP BY 顺序，或用覆盖索引

5. **覆盖索引优化**：SELECT 字段全放到辅助索引里避免回表

6. **拆复杂 SQL**：多表关联拆成应用层多次单表查询

7. **缓存热点数据**：Redis / 本地缓存挡在 DB 前

8. **分库分表**：单表数据量太大时的终极方案（ShardingSphere / MyCat）

9. **SQL 改写**：`NOT IN` → `NOT EXISTS`、子查询 → JOIN、避免函数计算列

10. **参数调优**：buffer pool 大小、innodb_io_capacity、join_buffer_size 等

## 💻 代码验证

### 验证 1：自增主键不连续演示

```
CREATE TABLE t (
id INT PRIMARY KEY AUTO_INCREMENT,
code VARCHAR(10) UNIQUE
);

INSERT INTO t(code) VALUES ('A');   -- id=1
INSERT INTO t(code) VALUES ('A');   -- 唯一冲突失败，但自增 → 2 已被消耗
INSERT INTO t(code) VALUES ('B');   -- id=3（跳过了 2）

SELECT * FROM t;
-- +----+------+
-- | id | code |
-- +----+------+
-- |  1 | A    |
-- |  3 | B    |    ← 断层
-- +----+------+
```

### 验证 2：深分页方案对比

```
-- 表 t 有 100 万行，主键 id
-- 传统：
mysql> EXPLAIN SELECT * FROM t ORDER BY id LIMIT 100000, 20;
-- type: index, rows: 100020, Extra: Using index
-- 耗时约 500ms

-- id 递进：
mysql> EXPLAIN SELECT * FROM t WHERE id > 100000 ORDER BY id LIMIT 20;
-- type: range, rows: 20
-- 耗时约 1ms

-- 延迟关联：
mysql> EXPLAIN SELECT t.* FROM t
JOIN (SELECT id FROM t ORDER BY id LIMIT 100000, 20) x USING(id);
-- 子查询只走索引，主查询按 id 回表 20 次
-- 耗时约 50ms
```

### 验证 3：mysqldump 逻辑备份

```
# 备份整个库（推荐参数）
mysqldump -uroot -p \
--single-transaction \
--routines --triggers --events \
--databases mydb \
> mydb_$(date +%F).sql

# --single-transaction：InnoDB 用 MVCC 一致性快照，不加锁
# --routines/--triggers/--events：包含存储过程/触发器/事件

# 恢复
mysql -uroot -p < mydb_2026-07-27.sql
```

### 验证 4：慢查询日志开启和分析

```
# 开启慢查询日志
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;      -- 超过 1s 记录

# 查看日志位置
SHOW VARIABLES LIKE 'slow_query_log_file';

# 用 mysqldumpslow 统计
mysqldumpslow -s t -t 10 /var/lib/mysql/slow.log
# -s t 按时间排序，-t 10 前 10 条

# 或用 pt-query-digest（更强大）
pt-query-digest /var/lib/mysql/slow.log
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 为什么阿里 Java 手册强制字段 NOT NULL？</summary>

NULL 参与比较结果永远是 NULL 而不是 TRUE；索引对 NULL 处理差；`WHERE col = NULL` 永远 false（必须 `IS NULL`）；聚合函数 COUNT(*) 计入 NULL，COUNT(col) 不计入。

</details>

<details>

<summary>Q2 SELECT * 有哪几个缺点？</summary>

① 影响覆盖索引（必须回表）；② 网络带宽浪费；③ Server 内存 & 查询缓存变大；④ 表字段变更时业务代码可能受影响。

</details>

<details>

<summary>Q3 自增主键不连续的四个原因？</summary>

① INSERT 失败已分配值不回收；② 事务回滚不回收；③ 批量 INSERT 预分配多值；④ `innodb_autoinc_lock_mode` 参数（2 = interleaved 最不连续但并发好）。

</details>

<details>

<summary>Q4 mysqldump 和 xtrabackup 各适合什么场景？</summary>

mysqldump：逻辑备份，跨版本，小库 & 迁移；xtrabackup：物理备份，快，同版本，大库日常。生产大库常用 xtrabackup + binlog 做 PITR。

</details>

<details>

<summary>Q5 深分页 `LIMIT 100000, 20` 的两种优化方案？</summary>

① **id 递进**：`WHERE id > 上次最大 id LIMIT 20`（需要前端配合）；② **延迟关联**：`JOIN (SELECT id FROM t ORDER BY id LIMIT 100000, 20)`（内层走覆盖索引，外层小回表）。

</details>

#### 📖 原文

-

-

-

-

- 阿里巴巴《Java 开发手册》— MySQL 章节

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0051：**阶段七 · Redis** 开篇 —— 缓存基础 & 为什么用缓存 & 常见缓存挑战。

💬 想问「分库分表怎么选切分键？」「pt-osc 和 gh-ost 区别？」「PITR 遇到 DDL 怎么办？」—— 直接问我。


