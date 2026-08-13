> Lesson 0044 · 阶段六 · MySQL · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0044 · MySQL 索引失效场景 & 隐式转换陷阱

上一课（）讲清了 B+ Tree 索引「正常工作时长什么样」——聚簇 vs 非聚簇、回表、覆盖索引。但真到面试和线上排障，几乎所有慢查询都不是「没建索引」，而是**「建了但没走上」**。这一课就是把索引失效的所有典型场景一次串起来，也是面试官最爱问的开场之一：*「你排查过 MySQL 慢查询吗？说说你踩过的索引失效的坑。」*

本课两条主线：**（1）SQL 写法层面的失效**（函数、通配符、OR、最左前缀、!=、隐式转换……）；**（2）优化器成本层面的「主动放弃」**（占比高时全表扫更快）。搞清这两条，就能回答几乎所有变体。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 字段 `phone` 是 `varchar(11)` 上面有索引，`WHERE phone = 13800138000`（数字不加引号）为什么走不了索引？</summary>

发生了**隐式类型转换**——MySQL 官方规则：一方是数字、一方是字符串，两边都转成浮点数比较。相当于对字段套上了 `CAST(phone AS DOUBLE)`，等同于「在索引列上做函数运算」，B+ Tree 存的是原始 varchar 值，函数处理后无序，索引失效。加个引号 `WHERE phone = '13800138000'` 就能走。第 3 场景细讲。

</details>

<details>

<summary>Q0.2 `LIKE '%abc'` 和 `LIKE 'abc%'` 哪个能走索引？为什么？</summary>

只有 `LIKE 'abc%'` 能走。B+ Tree 是按字段值*从左往右*排序的，前缀确定才能定位扫描区间；前导通配符相当于「前缀未知」，只能全表扫。第 5 场景细讲，并给出一个「覆盖索引」的例外。

</details>

## 面试场景 1：索引列上做计算、函数或表达式 ⭐经典

🎤 面试官

你有一张订单表，`create_time` 上建了索引。业务要统计 2024 年的订单量，同事写了 `WHERE YEAR(create_time) = 2024`，说慢得离谱。为什么？

🧑‍💻 你

**索引列上一旦套函数、做算术、做类型转换，索引就会失效。** 反面教材有三类：

- `WHERE YEAR(create_time) = 2024`——套函数

- `WHERE id + 1 = 100`——做算术

- `WHERE UPPER(name) = 'ALICE'`——套函数

核心原理：**B+ Tree 索引存的是字段的原始值**，按原始值排序。函数处理后的结果在索引里根本不存在这种顺序，MySQL 没法二分定位，只能退化成把每一行拿出来算函数、再比较——这就是全表扫描。

追问 MySQL 8.0 的「函数索引」能救吗？

能，但要事先建。`CREATE INDEX idx_year ON orders((YEAR(create_time)));` 建了之后，`WHERE YEAR(create_time) = 2024` 就能走。**局限**：函数索引是「表达式索引」，只对完全匹配这个表达式的 SQL 有效；改写成 `MONTH(create_time)` 或 `YEAR(create_time)+1` 都用不上。生产上更推荐第 2 场景的「改写成范围」，一劳永逸。

## 面试场景 2：正确姿势——把函数改写成范围查询

🧑‍💻 你

上一场景的 `WHERE YEAR(create_time) = 2024`，正确写法是：

```
SELECT * FROM orders
WHERE create_time >= '2024-01-01 00:00:00'
AND create_time <  '2025-01-01 00:00:00';
```

为什么这样能走索引？——因为 `>=` 和 `<` 都是对**原始字段值**的比较，B+ Tree 完全可以定位到 `2024-01-01` 那个叶子节点，然后顺序扫描到 `2025-01-01` 停下来，这就是「索引范围扫描」（`type=range`）。

同理：

- `WHERE id + 1 = 100` → 改成 `WHERE id = 99`（把算术移到右侧常量）

- `WHERE UPPER(name) = 'ALICE'` → 存储时统一大小写（业务层解决）或建函数索引

陷阱 用 `BETWEEN '2024-01-01' AND '2024-12-31'` 会漏掉 `2024-12-31 23:59:59` 之后到 `2025-01-01 00:00:00` 之前那一天最后的记录吗？——如果字段是 `DATETIME`，那 `'2024-12-31'` 会被隐式补成 `'2024-12-31 00:00:00'`，那一天大部分数据都被漏掉了。稳妥写法就是 **左闭右开区间**：`>= '2024-01-01' AND < '2025-01-01'`。

## 面试场景 3：隐式类型转换 ⭐核心考点

🎤 面试官

表结构：

```
CREATE TABLE user (
id      BIGINT PRIMARY KEY,
phone   VARCHAR(11),
age     INT,
INDEX idx_phone (phone),
INDEX idx_age   (age)
);
```

为什么下面两条 SQL 一个快、一个慢？

```
-- ① 快
SELECT * FROM user WHERE phone = '13800138000';
-- ② 慢
SELECT * FROM user WHERE phone = 13800138000;
```

🧑‍💻 你

**② 触发了隐式类型转换，索引失效。** MySQL 官方比较规则第 7 条：*一方是数字、一方是字符串，两边都转为浮点数比较*。所以 SQL ② 等价于：

```
SELECT * FROM user WHERE CAST(phone AS DOUBLE) = 13800138000;
```

相当于在索引列 `phone` 上套了函数——回到了场景 1 的坑。B+ Tree 按原始 varchar 排，被 `CAST` 之后无序，只能全表扫。

**致命性在哪**：这类失效在开发环境（10 条数据）根本发现不了，一上生产（千万行）直接把库拖垮。而且 `EXPLAIN` 的 `type` 会从 `ref` 掉到 `ALL`，`rows` 从 1 变成千万级。

追问 为什么 `WHERE phone = '13800138000'`（字符串包住）就没事？

两侧类型一致（都是字符串），根本不触发隐式转换，直接按字符串比较，能走 `idx_phone`。**结论**：字段是 varchar，条件值必须加引号。

追问 反过来——字段是 `INT`，条件传字符串（如 `WHERE age = '25'`）为什么通常不失效？

还是转成浮点比较，但转换发生在**常量侧**（字符串 `'25'` 转成数字 `25`），索引列 `age` 本身没被套函数，B+ Tree 仍能按 `age` 的原始值二分。**关键判定**：转换只要落在*索引列一侧*就失效；落在常量侧则没事。

追问 数字型字符串的转换有什么坑？

MySQL 字符串转数字规则：*非数字开头一律转 0*（`'abc'` → 0）；*数字开头则截到第一个非数字字符*（`'10000a'` → 10000，`'5.3xx'` → 5.3）。所以 `WHERE phone = 13800138000` 转换后，`'13800138000'`、`'13800138000abc'`、`'013800138000'` 都会等值，语义上就变了——这也是为什么 MySQL 必须全表扫：*多个不同 varchar 可能转成同一个数字，索引的一对一定位失效*。

## 面试场景 4：字符集 / 排序规则不匹配

🎤 面试官

两张表 JOIN，连接字段都有索引，为什么走不了？

🧑‍💻 你

常见元凶：**两表的连接字段 charset 或 collation 不同**。比如：

```
-- t1.user_no 是 utf8mb4 / utf8mb4_general_ci
-- t2.user_no 是 utf8    / utf8_general_ci
SELECT * FROM t1 JOIN t2 ON t1.user_no = t2.user_no;
```

MySQL 会把较窄的字符集**隐式转换**成较宽的字符集（`utf8` → `utf8mb4`），转换发生在被驱动表的连接字段上——又是「索引列被套函数」的翻版，被驱动表的索引失效，退化成 *nested loop 全表扫*。

**生产规范**：所有表统一 `utf8mb4 + utf8mb4_0900_ai_ci`（MySQL 8）或 `utf8mb4_general_ci`（MySQL 5.7）。DDL 评审时必须校对。

追问 排查手段？

`SHOW CREATE TABLE t1; SHOW CREATE TABLE t2;` 对比 `CHARSET` 和 `COLLATE`；或直接 `EXPLAIN` 看 `Extra` 里出现 `Using where; Using join buffer (hash join)` 且被驱动表 `type=ALL`——就是这个坑。修复：`ALTER TABLE t2 CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;`（注意大表要做低峰期 Online DDL 或 gh-ost）。

## 面试场景 5：LIKE 前导通配符

🧑‍💻 你

- `LIKE 'abc%'` ✅ 走索引（前缀确定，等价于范围扫）

- `LIKE '%abc'` ❌ 失效（前缀未知）

- `LIKE '%abc%'` ❌ 失效

原理和场景 1 是同一套：B+ Tree 按字段值从左往右排，前缀不确定就没法定位扫描起点，只能全表扫。

追问 `LIKE '%abc%'` 就完全没救吗？

**有一个例外：覆盖索引**。如果 `SELECT` 的列全都被索引覆盖（比如 `SELECT name FROM user WHERE name LIKE '%abc%'`，`name` 上有索引），MySQL 会走 **索引全扫**（`type=index`）而不是*表全扫*（`type=ALL`）——因为索引通常远小于原表，扫索引比扫表快得多，还不用回表。`EXPLAIN` 会看到 `Extra: Using where; Using index`。这仍然不是「走索引」的最优 `range/ref`，但已经比全表扫强一个量级。

更根本的方案：大文本模糊搜换 **Elasticsearch** 或 **MySQL 8 的全文索引（FULLTEXT）**——都是用*倒排索引*而不是 B+ Tree。

## 面试场景 6：OR 条件的坑

🎤 面试官

`SELECT * FROM user WHERE name = 'Alice' OR phone = '13800138000';`——`name` 有索引，`phone` 也有索引，走得上吗？

🧑‍💻 你

三种情况：

1. **只要 OR 任一侧的字段没索引**——直接全表扫。因为 OR 意味着「任一命中即可」，无索引侧必须全表扫，那另一侧走索引也没意义。

2. **两侧都有索引**——MySQL 可能触发 **Index Merge**（`type=index_merge`，`Extra: Using union(idx_name, idx_phone)`），分别用两个索引查出主键再合并。但如果优化器估算 Index Merge 成本高于全表扫，仍会放弃。

3. **解决方案**：用 `UNION ALL` 明确拆开，强制各自走索引；或者建覆盖两个字段的联合索引。

```
-- 推荐改写
SELECT * FROM user WHERE name  = 'Alice'
UNION ALL
SELECT * FROM user WHERE phone = '13800138000'
AND name <> 'Alice';  -- 手动去重，避免 UNION 全量去重开销
```

追问 为什么用 `UNION ALL` 而不是 `UNION`？

`UNION` 会做全量去重（相当于 `DISTINCT`），要额外开临时表排序，性能损失大。`UNION ALL` 直接拼接，快得多，但需要业务层保证不重复（如上面用 `name <> 'Alice'` 手动排除）。

## 面试场景 7：联合索引违反最左前缀

🧑‍💻 你

假设联合索引 `idx_abc (a, b, c)`，B+ Tree 是先按 `a` 排序，`a` 相等再按 `b`，`b` 相等再按 `c`。所以：

SQL能否走索引说明

`WHERE a=1`✅ 走 a最左前缀
`WHERE a=1 AND b=2`✅ 走 a,b连续最左前缀
`WHERE a=1 AND b=2 AND c=3`✅ 走全索引完整覆盖
`WHERE b=2`❌ 失效跳过 a 直接找 b，B+ Tree 里 b 是无序的
`WHERE a=1 AND c=3`⚠️ 走 a 段，c 段失效中间跳过 b，c 只能在 a=1 的区间里过滤
`WHERE a=1 AND b>2 AND c=3`⚠️ 走 a,b，c 失效b 是范围后 c 无序

追问 联合索引 `(a,b,c)` 中 `WHERE a=1 AND c>2 ORDER BY b` 能走全索引吗？

可以走 **a** 段做等值定位；**b** 因为在同一个 a 值下本身就是有序的，正好符合 `ORDER BY b`——所以 ORDER BY 可以直接利用索引避免 *filesort*；**c** 段因为中间跳过了 b，只能在 `a=1` 的范围里做过滤（`Extra: Using where`），无法用索引定位。总的看：`type=ref`，`key_len` 只到 a 的长度，无 filesort。

追问 MySQL 8.0 的 Index Skip Scan 能救「跳过最左列」吗？

8.0.13 引入了 **Skip Scan**：对于 `(a,b)` 索引，如果 `a` 的 distinct 值很少（如性别只有 2 种），`WHERE b=xxx` 可以在内部展开成 `WHERE a='M' AND b=xxx UNION WHERE a='F' AND b=xxx` 从而利用索引。**但生产不推荐依赖**：仅在 `a` 的基数极低时优化器才会启用，且 8.0.31 之前存在丢数据 Bug（MySQL Bug #109248）。稳妥做法：*建索引就按查询顺序建*，别指望 Skip Scan。

## 面试场景 8：`!=` / `NOT IN` / `NOT EXISTS`

🧑‍💻 你

反向匹配「通常失效」，但不是绝对：

- `WHERE status != 1`：无法在 B+ Tree 上定位「不等于 1」的连续区间，通常全表扫。

- `WHERE id NOT IN (1,2,3)`：常量列表下同理，全表扫描证明每条记录都不在集合里。

- `NOT EXISTS` 关联子查询：**子查询字段有索引通常能走**（外表全扫但子查询每次 lookup 走索引，比 `NOT IN` 更稳）。

**但要看优化器估算**：如果 `status` 只有几种值且分布倾斜，`WHERE status != 1` 可能被估成小结果集，仍会走索引扫描。所以「一定失效」是不严谨的说法，正确说法是*「大概率失效，取决于统计信息和优化器估算」*。

追问 `NOT IN` 换成 `NOT EXISTS` 一定快吗？

不一定，但通常更稳。`NOT IN` 对子查询结果集敏感——如果子查询返回百万行，主查询每条都要对这百万行做 *not in* 匹配，非常慢；而 `NOT EXISTS` 一般被优化成 *anti-semi-join*，外表每行只需要子查询做一次 exists 判断，子查询走索引即可停。此外 `NOT IN` 遇到子查询结果含 `NULL` 会直接返回空集（三值逻辑坑），`NOT EXISTS` 没这个问题。

## 面试场景 9：`IS NULL` / `IS NOT NULL`

🧑‍💻 你

MySQL 的 B+ Tree 索引**会记录 NULL 值**（放在最左端），所以 `IS NULL` 和 `IS NOT NULL` 理论上都能走索引。**能不能走，看两个因素**：

1. **选择性**：如果 `WHERE col IS NULL` 命中数据只占 1%，走索引；占 30% 以上，优化器可能改全表扫（回场景 10）。

2. **字段是否 NOT NULL**：如果字段本身声明了 `NOT NULL`，`IS NULL` 永远返回空集，优化器直接短路，看不到索引使用。

**面试口径**：不要武断说 *「IS NULL 一定不走索引」*——这个说法是 Oracle 早期规则遗留，MySQL 从很早就支持了。要说「取决于选择性和统计」。

## 面试场景 10：优化器主动放弃索引 ⭐认知升级

🎤 面试官

我明明建了索引，SQL 里也没有函数、没有隐式转换、条件符合最左前缀，`EXPLAIN` 却显示 `type=ALL`——这是 Bug 吗？

🧑‍💻 你

**不是 Bug，是优化器的理性决策。** MySQL 的成本模型大致是：

```
索引方案成本 ≈ 索引扫描行数 × 随机 IO 单价 + 回表次数 × 回表 IO 单价
全表扫方案成本 ≈ 全表行数 × 顺序 IO 单价
```

关键差异：**索引扫描是随机 IO，全表扫描是顺序 IO**。当查询命中数据占表比例超过一个阈值（经验值 **20%~30%**），随机 IO 加回表的总成本会超过顺序扫描——优化器就主动放弃索引。

典型触发：

- `WHERE status = 1` 而 90% 的行都是 status=1

- `WHERE create_time >= '2020-01-01'` 而表里 95% 数据都在这之后

- `SELECT *` 需要回表拿所有列，回表成本被放大

处理思路：

1. **先接受它**——多数情况下优化器是对的，别一上来就 `FORCE INDEX`。

2. **让统计信息准**——`ANALYZE TABLE user;` 更新统计后重跑，可能就走索引了。

3. **用覆盖索引消掉回表**——`SELECT id, status FROM user WHERE status = 1` 只需索引不回表，成本瞬间下降。

4. **业务层拆分**——比如加上更强的过滤条件缩小结果集。

5. **最后才是 `FORCE INDEX`**——业务确认索引方案更快时兜底。

追问 索引失效但业务必须查，四种应急手段？

① **改 SQL 消除失效原因**（去掉函数、加引号、拆 OR、调整最左前缀）——治本，优先做；② **加合适的索引**（联合索引 / 覆盖索引 / 函数索引）；③ **强制走索引** `SELECT * FROM t FORCE INDEX(idx_xxx) WHERE ...`——治标，防优化器抽风；④ **反范式冗余字段**——例如把 `DATE(create_time)` 存成额外的 `create_date` 字段并加索引，从根本上避免函数。

## 💻 代码验证（打开 MySQL 跑一遍）

### 验证 1：造一张千万级表观察隐式转换

```
-- 建表 + 写数据（1000 万行，约 3~5 分钟）
CREATE TABLE t_user (
id     BIGINT AUTO_INCREMENT PRIMARY KEY,
phone  VARCHAR(11) NOT NULL,
age    INT         NOT NULL,
INDEX idx_phone (phone),
INDEX idx_age   (age)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用存储过程灌数据（省略），phone 类似 '13800000001' ~ '13810000000'
```

```
-- 场景 A：加引号，走索引
EXPLAIN SELECT * FROM t_user WHERE phone = '13800138000';
-- type: ref     key: idx_phone     rows: 1

-- 场景 B：不加引号，触发隐式转换
EXPLAIN SELECT * FROM t_user WHERE phone = 13800138000;
-- type: ALL     key: NULL          rows: 10000000  ← 全表扫！

-- 反过来：字段是 int，条件传字符串，仍能走索引
EXPLAIN SELECT * FROM t_user WHERE age = '25';
-- type: ref     key: idx_age       rows: N
```

### 验证 2：函数索引失效 vs 范围改写

```
-- 反面
EXPLAIN SELECT * FROM orders WHERE YEAR(create_time) = 2024;
-- type: ALL   key: NULL

-- 正面
EXPLAIN SELECT * FROM orders
WHERE create_time >= '2024-01-01 00:00:00'
AND create_time <  '2025-01-01 00:00:00';
-- type: range  key: idx_create_time

-- MySQL 8.0 函数索引救场
CREATE INDEX idx_create_year ON orders((YEAR(create_time)));
EXPLAIN SELECT * FROM orders WHERE YEAR(create_time) = 2024;
-- type: ref   key: idx_create_year
```

### 验证 3：联合索引最左前缀观察 key_len

```
CREATE TABLE t_abc (
a INT, b INT, c INT,
INDEX idx_abc (a, b, c)
);

-- 完整走 a,b,c    → key_len = 4+4+4 = 12（假设 int 4 字节且允许 NULL 各加 1 字节，此处示意）
EXPLAIN SELECT * FROM t_abc WHERE a=1 AND b=2 AND c=3;

-- 只走 a          → key_len = 4
EXPLAIN SELECT * FROM t_abc WHERE a=1 AND c=3;

-- 完全失效       → key=NULL
EXPLAIN SELECT * FROM t_abc WHERE b=2;
```

**阅读技巧**：`key_len` 是判断「联合索引实际用了几段」的黄金指标，比 `key` 字段更精确——后者只告诉你用了哪个索引，前者告诉你用了这个索引的几个字段。下一课（）会展开。

### 验证 4：OR 条件失效 → UNION ALL 拯救

```
-- 反面
EXPLAIN SELECT * FROM t_user WHERE phone = '13800138000' OR age = 25;
-- 可能 type: ALL 或 index_merge，看优化器估算

-- 正面
EXPLAIN
SELECT * FROM t_user WHERE phone = '13800138000'
UNION ALL
SELECT * FROM t_user WHERE age = 25
AND phone <> '13800138000';   -- 手动去重
-- 两个 SELECT 都 type: ref
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 字段是 `varchar(20)` 上有索引，`WHERE code = 123` 为什么慢？加什么就能快？</summary>

发生隐式类型转换：MySQL 把字符串字段转成浮点数比较（等价 `CAST(code AS DOUBLE) = 123`），索引列被套函数导致失效。**加引号**：`WHERE code = '123'`，两侧类型一致，直接走 `idx_code`。

</details>

<details>

<summary>Q2 `LIKE '%abc'` 一定不能走索引吗？请举一个例外。</summary>

不是一定。**覆盖索引**场景下（如 `SELECT name FROM user WHERE name LIKE '%abc'`，且 `name` 上有索引）会走「索引全扫」（`type=index`，`Extra: Using where; Using index`）——扫索引比扫原表快，仍是次优但比全表扫强。

</details>

<details>

<summary>Q3 联合索引 `(a,b,c)` 下，`WHERE a=1 AND b>2 AND c=3` 索引利用到哪一段？为什么 c 段失效？</summary>

利用到 **a 段**（等值定位）和 **b 段**（范围扫描）；**c 段失效**。原因：B+ Tree 中当 `b` 处于范围（比如 b 从 2 扫到 100）时，`c` 只在同一个 `b` 值内部有序，跨 `b` 值就无序了——无法用索引定位，只能作为 `Using where` 逐行过滤。`key_len` 只会包含 a 和 b 两段。

</details>

<details>

<summary>Q4 优化器为什么会「明明有索引却主动放弃」？给出至少两个真实触发条件。</summary>

因为**成本模型判定全表扫（顺序 IO）更便宜**。典型触发：① 查询命中数据占表 20%~30% 以上（如 `WHERE status = 1` 而 90% 都是 status=1）；② `SELECT *` 大字段回表成本高；③ 统计信息陈旧误判基数——跑 `ANALYZE TABLE` 后可能就走索引了。这是*正常优化*，不是 bug。

</details>

<details>

<summary>Q5 索引失效但业务必须查，你的处理顺序是什么？</summary>

① **改 SQL** 消除失效原因（首选，治本）——去函数、加引号、拆 OR、调整最左前缀顺序；② **加合适索引**——联合索引、覆盖索引、必要时 MySQL 8 函数索引；③ **更新统计** `ANALYZE TABLE`；④ **覆盖索引**消掉回表；⑤ **兜底 `FORCE INDEX`**——业务确认索引方案更优时使用，不要作为第一选择；⑥ **反范式冗余字段**——例如为 `DATE(create_time)` 冗余存一个 `create_date` 字段并加索引。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

- MySQL 8.0 Reference · Type Conversion in Expression Evaluation —— 官方类型转换规则

- MySQL 8.0 · Functional Key Parts —— 函数索引官方文档

#### 🔗 关联课件

-  —— 上一课，索引「正常工作」的样子

-  —— 下一课，教你怎么*观察*索引是否失效

-  —— 索引失效在生产的完整应对手册

#### 🧭 下一课预告

Lesson 0045：**EXPLAIN 执行计划详解**——本课多次提到 `type`、`key`、`key_len`、`rows`、`Extra`，下节课把 EXPLAIN 输出的每一列都吃透，让你看一眼就能判断 SQL 走没走索引、走的哪一段。

💬 有任何疑问 ——「我们线上遇到过 XX 变体的失效怎么办？」「这种 SQL 该改还是加索引？」「面试真被问过 XX 追问，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


