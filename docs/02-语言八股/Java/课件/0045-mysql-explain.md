> Lesson 0045 · 阶段六 · MySQL · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0045 · MySQL 执行计划 explain 分析

上两课（、）我们讨论了「索引应该怎么建」「哪些写法会让索引失效」，都是*纸上推演*。这一课上正菜 —— **explain** 是每个后端每天都在用的实战工具：一条 SQL 到底走没走索引？走了哪个索引？扫了多少行？有没有额外排序？**全靠 explain 一眼看穿**。

本课主源：。面试频次 4 星 —— **DBA、中级/高级 Java、后端架构师面试都会问**，尤其是慢 SQL 优化环节，几乎必让你在白板上写一段 SQL 然后追问「explain 会输出什么？type 是什么级别？」

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 explain 输出的 `type` 字段里，哪几个级别代表「索引在正常工作」？</summary>

从优到差：`system` > `const` > `eq_ref` > `ref` > `range`，这五个都算走了索引。`index`（全索引扫）虽然也用了索引但通常性能不理想。`ALL`（全表扫描）是必须优化的信号。第 5 题会展开讲每一级的触发场景。

</details>

<details>

<summary>Q0.2 explain 的 Extra 列里出现 `Using filesort` 意味着什么？</summary>

MySQL 没能用索引本身的有序性完成 `ORDER BY`，只能把结果集捞出来*额外排一次序*。数据小时在 `sort_buffer` 里排，数据大就要落盘生成临时文件。**通常是需要优化的信号**。第 8 题会展开。

</details>

## 面试场景 1：explain 是什么？怎么用？

🎤 面试官

你平时用 explain 排查慢 SQL 吗？简单说说 explain 是什么、怎么用？

🧑‍💻 你

**explain 是 MySQL 提供的查询分析工具**，用来查看查询优化器为一条 SQL *制定的执行计划* —— 表的访问顺序、用了什么索引、预估扫描多少行、有没有额外排序或临时表等等。

用法非常简单，**在 SELECT 前加 `EXPLAIN` 关键字**：

```
EXPLAIN SELECT * FROM users WHERE age = 25;
```

关键特性有三个：

- **不实际执行 SQL** —— 普通 `explain` 只做分析，不会真的把数据捞出来，所以 `explain UPDATE / DELETE` 也是安全的（只是估算，不会改数据）。

- **MySQL 8.0.18+ 支持 `EXPLAIN ANALYZE`** —— *真正执行*并输出每一步的实际耗时和行数，用于慢 SQL 深度排查。

- **支持 `EXPLAIN FORMAT=JSON`** —— 输出成本模型详细数据，多表 JOIN 调优时特别有用。

支持的语句：`SELECT / DELETE / INSERT / REPLACE / UPDATE`。

追问 explain 会不会真的执行 SQL？UPDATE 呢？

普通 `explain` **不会执行**，只做优化器的静态分析。`explain UPDATE users SET age=100 WHERE id=1` 也不会真的把 `age` 改成 100。*只有 `EXPLAIN ANALYZE`（MySQL 8.0.18+）会真正执行*，所以对生产库跑 `explain analyze update` 要非常小心 —— 建议在从库或测试库跑。

## 面试场景 2：explain 输出的 12 个字段分别是什么？

🎤 面试官

explain 输出会有哪些列？大概说说每一列的含义。

🧑‍💻 你

一共 12 列（MySQL 5.7+），可以按*「表的元信息 → 访问方式 → 索引选择 → 行数估算 → 附加信息」*五组来记：

字段含义看什么

`id`SELECT 序列号多表/子查询的执行顺序
`select_type`SELECT 类型SIMPLE / SUBQUERY / DERIVED / UNION 等
`table`表名可能是真实表名或 `<derivedN>`
`partitions`命中的分区非分区表为 NULL
**`type`**访问方法（★核心）system / const / eq_ref / ref / range / index / ALL
`possible_keys`可能选用的索引优化器*候选清单*
**`key`**实际用的索引（★核心）NULL 就是没走索引
`key_len`索引用到的字节数看联合索引*用了前几列*
`ref`与索引比较的列或常量比如 `const`、`db.t.col`
`rows`预估扫描行数估算值，不是精确值
`filtered`过滤后留存百分比0-100，越高越好
**`Extra`**附加信息（★核心）Using index / Using filesort / Using temporary 等

面试重点看三个：**`type`（访问方式）、`key`（有没有用索引）、`Extra`（有没有 filesort/temporary）**。其它字段用于辅助判断。

## 面试场景 3：id 字段的语义是什么？

🎤 面试官

explain 输出的 id 有时候相同、有时候不同，甚至有 NULL —— 怎么解读？

🧑‍💻 你

`id` 是 SELECT 的**序列标识**，反映查询的执行顺序。三条规则：

1. **id 相同 → 从上往下依次执行**。多表 JOIN 时，同一个 SELECT 里的所有表 id 都相同，*顺序即 JOIN 顺序*（谁是驱动表由优化器定，通常小表在上）。

2. **id 不同 → id 大的先执行**。子查询、派生表会产生新的 id，*越里层 id 越大越先跑*（因为要先算出子查询结果，外层才能用）。

3. **id 为 NULL → UNION RESULT 或某些合并操作**，不需要单独执行，只是结果的汇总。

举个例子：

```
EXPLAIN
SELECT * FROM users u
WHERE u.dept_id IN (SELECT id FROM dept WHERE name = 'RD');

-- 输出：
-- id  select_type  table   ...
--  1   PRIMARY     u       ← 外层
--  2   SUBQUERY    dept    ← 子查询（id 大，先跑）
```

追问 UNION 查询里出现 `id=NULL, table=<union1,2>` 是什么意思？

说明这一行是 **UNION 的结果合并步骤**：把 id=1、id=2 两个 SELECT 的结果去重/合并（UNION 会自动去重，UNION ALL 不去重）。`<union1,2>` 就是「id=1 和 id=2 结果集的并集」。这一步通常还伴随 `Extra: Using temporary`，因为去重需要临时表。

## 面试场景 4：select_type 常见值有哪些？

🧑‍💻 你

`select_type` 描述这个 SELECT 在整个查询中的*角色*：

- **SIMPLE**：简单查询，不含 UNION、不含子查询。绝大多数日常 SQL。

- **PRIMARY**：包含子查询/UNION 时，*最外层*的那个 SELECT。

- **SUBQUERY**：子查询中的第一个 SELECT（一般是相关子查询或独立子查询）。

- **DERIVED**：`FROM (SELECT ...)` 里的派生表，MySQL 会先物化它再和外层 JOIN。

- **UNION**：UNION 中除第一个 SELECT 外的其它 SELECT。

- **UNION RESULT**：UNION 结果的合并（对应 `id=NULL, table=<unionM,N>`）。

- **DEPENDENT SUBQUERY**：依赖外层查询的相关子查询（*性能通常很差*，因为外层每一行都要触发子查询）。

陷阱 看到 `DEPENDENT SUBQUERY` 要警觉 —— 相关子查询会让子查询按外层行数*反复执行*。**能改写成 JOIN 就改写成 JOIN**，性能通常有数量级提升。MySQL 5.6 之后优化器会尝试自动改写为半连接（semijoin），但不是所有场景都能优化到。

## 面试场景 5：type 字段（★核心）—— 从优到差有哪些级别？

🎤 面试官

**这是重点**：explain 里 type 有哪些取值？从好到差怎么排？各自触发场景是什么？

🧑‍💻 你

type 描述**访问表的方式**，官方完整排序（从最优到最差）：

```
system > const > eq_ref > ref > fulltext > ref_or_null
> index_merge > unique_subquery > index_subquery
> range > index > ALL
```

面试要能默写*常考的 7 个*：

级别触发场景性能

`system`表只有一行数据（*常见于 MyISAM/Memory 引擎的系统表*）最优
`const`**主键或唯一索引**做等值查询，最多命中 1 行。如 `WHERE id = 5`极优
`eq_ref`多表 JOIN 时，*被驱动表*用主键或唯一非空索引匹配，每条驱动行只匹配一条被驱动行优
`ref`用**普通索引**做等值查询，可能匹配多行。如 `WHERE age = 25`（age 有普通索引）良
`range`索引**范围扫描**：`>`、`<`、`BETWEEN`、`IN`、`LIKE 'abc%'`可接受
`index`**遍历整棵索引树**（不是回表）。常见于覆盖索引场景较差
**`ALL`****全表扫描**，必须优化最差

经验法则：**生产上要求至少 `range`，能到 `ref` 更好**。看到 `ALL` 立刻加索引或改 SQL；看到 `index` 也要评估是否可以变成 `range` 或 `ref`。

追问 `type = index` 和 `type = ALL` 有什么区别？

都是*「扫全部数据」*，但读取路径不同：**`index` 是遍历索引 B+ 树**的所有叶子节点，通常按索引顺序读取，且如果满足覆盖索引就不用回表；**`ALL` 是按主键顺序（或磁盘顺序）扫聚簇索引**，读的是完整行数据。*索引通常比完整行小很多*，所以同样是扫全部，`index` 的 I/O 更少、还有覆盖索引优化的机会 —— 但对于超大表，`index` 仍然可能产生大量随机 I/O，别以为它就一定好。

追问 `const` 和 `eq_ref` 有什么区别？

都涉及主键/唯一索引的*唯一匹配*，但场景不同：**`const` 是单表查询**用主键/唯一索引直接命中一行，条件是*常量*；**`eq_ref` 是多表 JOIN**时被驱动表用主键/唯一索引匹配驱动表的字段（不是常量，而是*另一张表的列*），每条驱动行对应一条被驱动行。可以理解为：`const` 是「一次性抓一条」，`eq_ref` 是「循环里每次抓一条」。

## 面试场景 6：key、possible_keys、key_len 分别是什么？

🧑‍💻 你

- **`possible_keys`**：优化器*可能*选用的索引列表 —— 只是候选，不代表真用。

- **`key`**：优化器*实际选用*的索引。**为 NULL 就是没走索引**。这个字段最重要。

- **`key_len`**：索引*用到的字节数*。对**联合索引**特别重要 —— 通过字节数可以反推*用了前几个字段*。

典型场景：`possible_keys` 有多个但 `key` 只选一个 —— 优化器基于成本选择了它认为最优的那个。也有 `possible_keys` 不为空但 `key = NULL` 的情况（优化器认为全表扫更快，通常小表会这样）。

追问 key_len 怎么算？有什么用？

基本规则（*InnoDB / utf8mb4 字符集*）：

- `INT`：4 字节

- `BIGINT`：8 字节

- `CHAR(N)`：N × 字符集字节数（utf8mb4 = 4）

- `VARCHAR(N)`：N × 字符集字节数 + 2 字节长度前缀

- 可为 NULL 的字段：**+1 字节** 标记位

- 联合索引：*所有用到的列求和*

举例：联合索引 `(a INT NOT NULL, b VARCHAR(20) NULL)` 在 utf8mb4 下：

- 只用了 `a`：`key_len = 4`

- 用了 `a + b`：`key_len = 4 + (20×4 + 2 + 1) = 4 + 83 = 87`

**用途**：反推*联合索引到底用了几个字段*。比如索引 `(a, b, c)`，如果 `key_len` 只等于 `a` 的长度，说明 `b` 和 `c` 没用上 —— 可能是最左前缀原则被违反了。

## 面试场景 7：rows 和 filtered 怎么解读？

🧑‍💻 你

**`rows`**：预估要扫描的行数 —— *注意是估算值，不是精确值*。InnoDB 基于索引统计信息（默认随机采样 20 页）算出来，频繁变动或批量导入后偏差可能 10%-50% 甚至更大。想让统计准，跑 `ANALYZE TABLE tbl_name`。

**`filtered`**：存储引擎返回给 Server 层的行中，*能通过所有 WHERE 条件的百分比*（0-100）。计算公式：

```
filtered = (WHERE 过滤后行数 / 存储引擎返回行数) × 100
```

解读规则：

- **filtered = 100**：存储引擎返回的都是满足条件的行 —— *索引很给力*。

- **filtered < 100**：Server 层还要再过滤 —— 索引没能完全覆盖 WHERE 条件。

成本估算的核心公式：

```
估算成本 ≈ rows × 每行操作成本
JOIN 扇出行数 ≈ rows × (filtered / 100)
```

多表 JOIN 时特别重要：*扇出行数决定了下一张被驱动表要匹配多少次*。`rows` 大且 `filtered` 低是明显的性能瓶颈信号 —— 考虑加索引、用索引下推（ICP）减少扇出。

追问 有个 SQL `explain` 显示 `rows = 100 万`，怎么快速判断有没有问题？

不能只看 rows。综合三点判断：

1. **看 `type`**：如果是 `ALL`，100 万必须优化；如果是 `range` 或 `ref`，可能是查询范围本来就大。

2. **看 `filtered`**：如果 filtered=1，实际处理只有 1 万行，可能没问题；如果 filtered=100，就是真的要处理 100 万。

3. **看 `Extra`**：有 `Using filesort` / `Using temporary` 就是重要的优化点。

业务上还要评估：*这个查询的 QPS × rows = 每秒总扫描行数*。10 QPS × 100 万 = 每秒扫 1000 万行，DB 大概率扛不住。

## 面试场景 8：Extra 字段（★核心）—— 关键值有哪些？

🎤 面试官

Extra 列有几十种取值，讲讲最重要的几个 —— 哪些是好信号、哪些必须优化？

🧑‍💻 你

Extra 是 explain 的*灵魂*，很多问题只从这里看出来。分三类：

### 好信号（尽量出现）

- **`Using index`**：*覆盖索引*，查询字段全在索引里，**无需回表**，效率最高。

- **`Using index condition`**：*索引下推 ICP*生效 —— 存储引擎在遍历索引时就应用 WHERE 条件过滤，减少回表次数。MySQL 5.6+ 默认开启。

### 中性（要结合 type 判断）

- **`Using where`**：Server 层对存储引擎返回的行做*二次过滤*。*不是坏事*，只是说明索引没完全覆盖 WHERE 条件。

### 危险信号（通常要优化）

- **`Using filesort`**：*无法利用索引完成排序*，需要在结果集上额外排一次。数据量小时在 `sort_buffer` 内排；量大时借临时磁盘文件（*「filesort」这个名字有误导性，不一定真落盘*）。

- **`Using temporary`**：*创建了临时表*存储中间结果，常见于 `GROUP BY`、`UNION`、`DISTINCT`。临时表可能在内存也可能落磁盘，量大就是灾难。

- **`Using join buffer (Block Nested Loop)`**：JOIN 时被驱动表*没走索引*，只能用 join buffer 缓存驱动表数据、遍历被驱动表匹配 —— **复杂度 O(N×M)**。

- **`Using join buffer (hash join)`**：MySQL 8.0.18+ 引入，*仅用于等值 JOIN*。构建 O(N) + 探测 O(M)，比 BNL 好很多。8.0.20 起默认替代 BNL。

陷阱 「`Using where`」不是坏信号 —— 只是说 Server 层要做一层过滤。真正要警惕的是 **`Using filesort` 和 `Using temporary`**，这两个八股面试里几乎必考。见到就要思考：*能不能通过合适的索引让排序或分组直接走索引？*

追问 Using filesort 一定要消除吗？

看数据量。*小结果集（几十行以内）*filesort 在 `sort_buffer` 内完成，成本很低，没必要为消除它专门加索引 —— 加了反而增加写成本。*大结果集或分页深翻*就必须消除 —— 要么让 `ORDER BY` 的字段本身走索引（联合索引里包含 ORDER BY 字段且顺序一致），要么用「延迟关联」（先用索引拿主键、再回表查完整行）。

## 面试场景 9：常见优化模式 —— 从 explain 结果反推怎么改

🧑‍💻 你

基于 explain 结果的优化路径，通常沿三条主线：

### ① 让 type 升级：ALL → range → ref → const

- 看到 `type = ALL`：*加索引*（或者检查现有索引为什么没被选中，可能违反最左前缀、或字段类型不匹配触发隐式转换）。

- 看到 `type = index`：评估能否变成 `range` 或 `ref`，比如加更精确的 WHERE 条件。

- 看到 `type = range`：范围太大时缩小范围，或改用*覆盖索引*让至少 `Extra = Using index`。

### ② 消除 filesort

- 让 `ORDER BY` 字段直接走索引（顺序一致、方向一致）。

- 联合索引 `(a, b)`，`WHERE a=1 ORDER BY b` 可以直接用索引排序 —— 不产生 filesort。

- *ASC/DESC 混用*：MySQL 8.0 才支持 Descending Index，之前版本 `ORDER BY a ASC, b DESC` 一定 filesort。

### ③ 消除 temporary

- 合理组织 `GROUP BY` 字段顺序，让它能利用索引。

- 能用 UNION ALL 就别用 UNION（UNION 要去重、要临时表）。

- `DISTINCT + ORDER BY` 组合是重灾区，考虑重写。

### ④ 强制走索引（谨慎使用）

```
SELECT * FROM orders FORCE INDEX (idx_user_time)
WHERE user_id = 1 AND created_at > '2024-01-01';
```

**只在优化器选错索引时用**。滥用 FORCE INDEX 会让 SQL 失去优化器的自适应能力 —— 数据分布变化后可能反而更慢。生产上更推荐用 `ANALYZE TABLE` 更新统计信息，让优化器自己选对。

追问 优化器为什么会选错索引？

常见三种原因：（1）**统计信息过时** —— `ANALYZE TABLE` 后重新采样通常能修复；（2）**索引区分度低** —— 比如性别字段建的索引，优化器算完成本觉得不如全表扫；（3）**成本模型误判** —— 隐式转换、函数、类型不匹配都可能让优化器算错行数。解决顺序：先 `ANALYZE TABLE`，再检查 SQL 写法，最后才考虑 `FORCE INDEX`。

## 面试场景 10：explain analyze（MySQL 8）—— 更强的排查利器

🎤 面试官

MySQL 8 的 explain analyze 和普通 explain 有什么区别？什么时候用？

🧑‍💻 你

`EXPLAIN ANALYZE` 是 MySQL 8.0.18+ 引入的*「真实执行 + 分阶段计时」*版本。区别在：

维度`EXPLAIN``EXPLAIN ANALYZE`

是否实际执行不执行**会执行**
行数信息估算 `rows`估算 + **实际扫描行数**
时间信息无**每个 stage 的实际耗时**
输出格式表格树形（迭代器执行树）
适用场景快速看走没走索引慢 SQL 深度排查

示例输出片段：

```
-> Nested loop inner join  (cost=1.15 rows=1)
(actual time=0.061..0.062 rows=1 loops=1)
-> Index lookup on u using PRIMARY (id=1)
(cost=0.35 rows=1) (actual time=0.031..0.032 rows=1 loops=1)
-> Index lookup on d using idx_user (user_id=u.id)
(cost=0.80 rows=1) (actual time=0.024..0.025 rows=1 loops=1)
```

关键在*括号里的 `actual time`、`rows`、`loops`* —— 直接告诉你哪一步实际慢在哪。这是**普通 explain 拿不到的信息**（估算和实际差距大时特别有用）。

陷阱 `EXPLAIN ANALYZE` **真的会执行 SQL**！`EXPLAIN ANALYZE UPDATE ... SET ...` 会真的改数据、`EXPLAIN ANALYZE DELETE` 会真的删数据。生产上一定要*在只读从库或测试库跑*。这一点和普通 `EXPLAIN` 有本质区别。

## 💻 代码验证（打开 MySQL 客户端跑一遍）

### 验证 1：建表 + 造数据 + 基础 explain

```
-- 创建一张用户表，联合索引 (age, score)
CREATE TABLE users (
id       INT PRIMARY KEY AUTO_INCREMENT,
name     VARCHAR(50) NOT NULL,
age      INT NOT NULL,
score    INT NOT NULL,
email    VARCHAR(100),
KEY idx_age_score (age, score),
KEY idx_email (email)
) ENGINE=InnoDB;

-- 造 10 万条测试数据（用存储过程）
DELIMITER //
CREATE PROCEDURE fill_users()
BEGIN
DECLARE i INT DEFAULT 0;
WHILE i < 100000 DO
INSERT INTO users(name, age, score, email)
VALUES (CONCAT('user_', i), FLOOR(RAND()*80)+1,
FLOOR(RAND()*100), CONCAT('u', i, '@x.com'));
SET i = i + 1;
END WHILE;
END //
DELIMITER ;
CALL fill_users();

-- 基础 explain
EXPLAIN SELECT * FROM users WHERE age = 25;
-- id | select_type | table | type | possible_keys  | key           | key_len | ref   | rows | Extra
--  1 | SIMPLE      | users | ref  | idx_age_score  | idx_age_score | 4       | const | 1200 | NULL
```

观察点：`type=ref`（普通索引等值）、`key=idx_age_score`（用了联合索引）、`key_len=4`（只用了 `age` 一个 int 字段）、`rows=1200`（估算扫 1200 行）。

### 验证 2：观察 type 从 ALL → range → ref 的变化

```
-- ① 没有 WHERE：全表扫
EXPLAIN SELECT * FROM users;
-- type=ALL, rows=100000  ← 最差

-- ② 范围查询：走范围扫描
EXPLAIN SELECT * FROM users WHERE age BETWEEN 20 AND 30;
-- type=range, key=idx_age_score, rows=约 12000

-- ③ 等值查询：走 ref
EXPLAIN SELECT * FROM users WHERE age = 25;
-- type=ref, key=idx_age_score, rows=约 1200

-- ④ 主键等值：走 const
EXPLAIN SELECT * FROM users WHERE id = 100;
-- type=const, key=PRIMARY, rows=1  ← 最优
```

### 验证 3：Extra 观察 —— Using index / Using filesort / Using temporary

```
-- ① 覆盖索引：Extra 出现 Using index（不回表，最好）
EXPLAIN SELECT age, score FROM users WHERE age = 25;
-- type=ref, key=idx_age_score, Extra=Using index

-- ② 排序无法走索引：出现 Using filesort
EXPLAIN SELECT * FROM users WHERE age = 25 ORDER BY email;
-- Extra=Using where; Using filesort  ← 因为 email 不在 (age,score) 联合索引里

-- ③ 排序走联合索引第二列：无 filesort
EXPLAIN SELECT * FROM users WHERE age = 25 ORDER BY score;
-- Extra=Using index  ← 完美，(age,score) 索引本身就按 score 有序

-- ④ GROUP BY 触发临时表
EXPLAIN SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
-- Extra=Using temporary  ← 需要临时表聚合
```

### 验证 4：explain analyze 深度排查（MySQL 8.0.18+）

```
EXPLAIN ANALYZE
SELECT u.name, COUNT(*)
FROM users u
WHERE u.age BETWEEN 20 AND 40
GROUP BY u.name
ORDER BY COUNT(*) DESC
LIMIT 10;

-- 输出片段（树形）：
-- -> Limit: 10 row(s)  (actual time=180.5..180.5 rows=10 loops=1)
--     -> Sort: count(0) DESC, limit input to 10 row(s) per chunk
--        (actual time=180.4..180.5 rows=10 loops=1)
--         -> Table scan on <temporary>
--            (actual time=178.2..179.9 rows=30000 loops=1)
--             -> Aggregate using temporary table
--                (actual time=178.1..178.1 rows=30000 loops=1)
--                 -> Filter: (u.age between 20 and 40)
--                    (cost=5100 rows=25000)
--                    (actual time=0.05..85.3 rows=25200 loops=1)
--                     -> Index range scan on u using idx_age_score
--                        (cost=5100 rows=25000)
--                        (actual time=0.04..70.1 rows=25200 loops=1)
```

观察点：*实际耗时最长的两步*是 `Index range scan`（70ms 扫 25200 行）和 `Sort`（180ms）—— 如果要优化，重点在*排序阶段*，考虑给 `(age, name)` 建联合索引让 GROUP BY 也能走索引。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 explain 输出里，最需要关注的三个字段是什么？为什么？</summary>

`type`（访问方式，看有没有走合适级别的索引）、`key`（实际用了哪个索引，NULL 就是没走）、`Extra`（是否有 filesort / temporary 等危险信号）。这三个是判断 SQL 好坏的核心。

</details>

<details>

<summary>Q2 type 字段从优到差写出至少 5 个常见级别。</summary>

`system > const > eq_ref > ref > range > index > ALL`。生产上要求至少 `range`，看到 `ALL` 必须优化。

</details>

<details>

<summary>Q3 `Using index`、`Using where`、`Using index condition` 三者有何区别？</summary>

`Using index` = 覆盖索引不用回表（最好）；`Using where` = Server 层要额外过滤（中性）；`Using index condition` = 索引下推 ICP 生效，存储引擎层就过滤（较好）。

</details>

<details>

<summary>Q4 联合索引 `(a, b, c)`，`key_len` 显示只等于 `a` 一列的长度，说明什么？</summary>

只用了联合索引的*第一列 `a`*，`b` 和 `c` 没被用上。通常是违反了最左前缀原则（比如没有 `WHERE a=?` 直接查 `WHERE b=?`），或者 `a` 上有范围条件把后面的列切断了。

</details>

<details>

<summary>Q5 `EXPLAIN ANALYZE UPDATE users SET age=100 WHERE id=1` 会不会真的把 `age` 改成 100？普通 `EXPLAIN UPDATE` 呢？</summary>

**会**。`EXPLAIN ANALYZE` 真实执行 SQL —— 更新、删除都会生效，生产上要在从库或测试库跑。普通 `EXPLAIN UPDATE` *不会执行*，只做优化器估算，是安全的。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- MySQL 8.0 Reference · EXPLAIN Output Format —— 官方字段完整定义

- MySQL 8.0 Reference · EXPLAIN ANALYZE —— 树形输出规范

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0046：**MySQL 事务隔离级别 & MVCC 原理** —— 从性能优化转到数据一致性，同样是面试必考点。

💬 有任何疑问 ——「这里为什么这样？」「能不能再举一个 explain 输出例子？」「我在公司真遇到过 XX 场景怎么办？」—— 直接问我。我是你的老师，也是你的追问陪练。


