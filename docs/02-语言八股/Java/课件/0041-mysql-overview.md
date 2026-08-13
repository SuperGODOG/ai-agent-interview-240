> Lesson 0041 · 阶段六 · MySQL · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑 SQL · 5 道自测 · 7 个追问

# 0041 · MySQL 概览 & 存储引擎 & 三大范式

欢迎来到**阶段六 · MySQL**。Java 后端面试的第二大板块就是 MySQL——第一大是 Java 本体，第二就是它。一场技术面 60 分钟，Java 通常占 25 分钟，MySQL 至少 15-20 分钟，剩下的才轮到 Redis / 消息队列 / 分布式。

阶段六一共 9 节（0041-0049），主线是：**本课全景铺垫 → 0042 SQL 执行流程 → 0043-0045 索引三连 → 0046-0048 事务/隔离/MVCC → 0049 日志与主从**。这节课「宽而不深」，把所有 MySQL 面试官会用来暖场的概念题一次讲透，把后面 8 节要展开的深水区（索引、事务、MVCC、日志）留出接口。

本课覆盖  里的*概念部分*。索引、事务、锁、日志的细节留给 0043-0049。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 假如你现在建一张订单表 `orders`，MyISAM 和 InnoDB 该选哪个？为什么？</summary>

InnoDB。订单是核心业务，必须**支持事务**（下单要跟库存、余额一起原子提交）、**行锁**（高并发下不能一下单锁全表）、**崩溃恢复**（宕机不能丢单）。MyISAM 三样都没有，只有「读多写少的日志/统计表」才可能选它——但从 MySQL 5.5 起 InnoDB 已经是默认，生产上 MyISAM 基本被淘汰。第 3、4 题细讲。

</details>

<details>

<summary>Q0.2 `char(10)` 和 `varchar(10)` 有什么区别？存 `'abc'` 的时候各占多少空间？</summary>

char 定长——总占 10 个字符位（不足的用空格补齐，查出来时空格会被去掉）；varchar 变长——只占实际长度 3 个字符 + 1-2 字节的长度前缀。char 适合定长字段（性别 M/F、MD5 32 位、身份证 18 位），varchar 适合变长字段（用户名、地址）。第 6 题细讲。

</details>

## 面试场景 1：MySQL 是什么？有什么特点？

🎤 面试官

用一分钟介绍一下 MySQL 这个数据库。

🧑‍💻 你

MySQL 是一款**开源**的**关系型数据库管理系统（RDBMS）**，由 Oracle 维护。它的核心特点：

- **关系模型 + SQL**：数据以行列表格形式组织，用标准 SQL 查询。

- **开源免费**（社区版），生态成熟——ORM 框架（MyBatis / JPA）、连接池（HikariCP / Druid）、监控（Percona / Prometheus）都一应俱全。

- **可插拔存储引擎**：InnoDB（默认，支持事务）、MyISAM（老引擎，无事务）、Memory（内存表）等。

- **ACID 事务**（InnoDB 引擎下）：原子性、一致性、隔离性、持久性。

- **主从复制 + 读写分离**：基于 binlog 的异步/半同步复制，是水平扩展的基础。

- **跨平台**：Linux / macOS / Windows 全支持。

追问 MySQL 8 相比 5.7 有哪些重要变化？

面试高频。核心变化有六个：**(1) 默认字符集从 latin1 改成 utf8mb4**（真正的 4 字节 UTF-8，能存 emoji 和生僻字）；**(2) 移除了查询缓存**（命中率低、失效开销大，8.0 直接删掉）；**(3) 引入窗口函数**（`ROW_NUMBER()` / `RANK()` / `LAG()`，SQL 报表必备）；**(4) 支持 CTE 公用表表达式**（`WITH ... AS`，递归查询写树形结构非常方便）；**(5) 不可见索引**（`ALTER TABLE ... INVISIBLE`，可以先隐藏观察性能再决定是否删）；**(6) 原子 DDL**（`ALTER TABLE` 要么全成功要么全回滚，不再中途失败留下半成品）。此外还有更强的 JSON 函数、性能整体提升、密码认证插件改成 `caching_sha2_password`。

## 面试场景 2：MySQL 的整体架构长什么样？

🎤 面试官

你能画一下 MySQL 的架构图吗？一条 SQL 从进来到返回结果走过了哪些组件？

🧑‍💻 你

MySQL 分为两层：**Server 层**（所有引擎共用）+ **存储引擎层**（可插拔）。

```
┌──────────────── Client（JDBC / mysql CLI） ────────────────┐
│
┌──────────────────────── Server 层 ──────────────────────────┐
│                                                             │
│  ① 连接器 Connector    ← 管理连接、鉴权、权限                 │
│         │                                                   │
│  ② 查询缓存 Cache      ← 5.7 有 / 8.0 移除                   │
│         │                                                   │
│  ③ 分析器 Parser       ← 词法分析 + 语法分析，生成解析树      │
│         │                                                   │
│  ④ 优化器 Optimizer    ← 决定索引、join 顺序，生成执行计划    │
│         │                                                   │
│  ⑤ 执行器 Executor     ← 调用存储引擎接口取数据               │
│                                                             │
└─────────────────────────────┬───────────────────────────────┘
│
┌──────────────── 存储引擎层（Pluggable） ─────────────────────┐
│                                                             │
│   InnoDB（默认）   MyISAM   Memory   Archive   CSV  ...      │
│         │                                                   │
│         ▼                                                   │
│      磁盘/内存（.ibd 数据文件 + 日志）                        │
└─────────────────────────────────────────────────────────────┘
```

关键点：**SQL 的解析、优化、权限校验都在 Server 层**，Server 层不关心数据到底怎么存；**真正的数据落盘 / 索引 / 事务实现都在存储引擎层**。这就是为什么 MySQL 能「换引擎」——上层 SQL 语法不变，底层实现可以完全不同。

追问 查询缓存为什么在 8.0 被移除？

因为它**「设计初衷很好，但工程上得不偿失」**。缓存 key 是 SQL 字符串的精确匹配（多一个空格都算 miss），命中率天然低；更糟的是，**只要表被更新，这张表相关的所有缓存全部失效**——对于写多的 OLTP 系统，缓存刚建就被推翻。加上维护缓存本身要加锁，反而拖慢并发。官方评估后直接在 8.0 删除。想缓存 SQL 结果请用 Redis / Caffeine，在应用层做。

## 面试场景 3：InnoDB 和 MyISAM 有什么区别？★经典必背

🎤 面试官

你能对比一下 InnoDB 和 MyISAM 这两个存储引擎吗？

维度InnoDBMyISAM

**事务**支持 ACID不支持
**锁粒度**行锁（也能升级到表锁）只有表锁
**外键**支持不支持
**崩溃恢复**支持（靠 redo log）不支持（宕机可能损坏）
**MVCC**支持（多版本并发控制）不支持
**索引结构**聚簇索引（数据 = 主键索引 B+ 树的叶节点）非聚簇（索引和数据分离，叶节点存数据行地址）
**全文索引**5.6+ 支持原生支持
**`SELECT COUNT(*)`**需要扫描（8.0 有优化）常数时间（内部维护了行数）
**文件**`.ibd`（数据+索引在一起）`.MYD`（数据）+ `.MYI`（索引）分开

**一句话总结**：InnoDB 面向 OLTP（在线事务处理，业务表标配）；MyISAM 面向读多写少、无事务需求的场景（现在几乎只在老系统的日志表里还能见到）。

追问 InnoDB 表主键为什么强烈推荐用自增 ID，而不是 UUID？

因为 InnoDB 是**聚簇索引**——数据行按主键顺序物理存储在 B+ 树的叶节点里。**自增 ID** 的插入永远是「追加到最后」，B+ 树顺序追加、页填满就开新页，**不会触发页分裂**，空间紧凑，范围查询（`WHERE id BETWEEN ...`）走顺序 IO 极快。**UUID 是随机值**，每次插入都可能插到 B+ 树中间的某个已满的页，触发**页分裂**（旧页拆一半到新页），一是性能抖动，二是页填充率下降（大量半空的页），空间浪费。此外 UUID 是 16-36 字节，比 8 字节的 `bigint` 大得多，每个二级索引的叶节点都要存主键值，会让所有索引都膨胀。

## 面试场景 4：为什么 MySQL 默认引擎是 InnoDB？

🧑‍💻 你

MySQL **从 5.5 版本起**把默认引擎从 MyISAM 换成了 InnoDB，原因就是场景 3 的对比表：

1. **事务**是绝大多数业务系统的刚需——转账、下单、扣库存必须原子。

2. **行锁**让高并发写入成为可能——一个用户下单不会锁住整张订单表。

3. **崩溃恢复**靠 redo log 保证——宕机后重启数据不丢、事务不断。

4. **MVCC** 提供高性能的一致性读——读不阻塞写，写不阻塞读（细节留给 0048）。

5. **聚簇索引**让主键查询几乎零额外 IO——B+ 树叶节点直接就是完整的行数据。

这五点每一个都是生产系统的刚需，MyISAM 一个都不满足。所以「默认引擎从 MyISAM 换到 InnoDB」不是偏好问题，是**互联网时代对数据库要求变了**——从「读多写少的目录/资讯站」变成了「高并发交易系统」。

## 面试场景 5：三大范式（1NF / 2NF / 3NF）

🎤 面试官

数据库设计的三大范式你还记得吗？举个例子说明。

🧑‍💻 你

范式是**关系模型的规范化规则**，目的是减少数据冗余、避免更新异常。

**1NF（第一范式）—— 字段原子性**：每个字段不可再分。

反例：`联系方式 = '138xxxx, zhang@x.com'`（一个字段塞了电话+邮箱）。

正例：拆成 `phone` 和 `email` 两列。

**2NF（第二范式）—— 非主键字段完全依赖主键（消除部分依赖）**：前提是满足 1NF，且非主键字段必须依赖于整个主键，不能只依赖主键的一部分。*只在联合主键场景才有意义*。

反例：订单明细表 `order_items(order_id, product_id, product_name, quantity)`，联合主键是 `(order_id, product_id)`，但 `product_name` 只依赖 `product_id`——这就是「部分依赖」。

正例：把 `product_name` 拿出来放到 `products` 表，`order_items` 只留主键 + `quantity`。

**3NF（第三范式）—— 非主键字段不依赖其他非主键字段（消除传递依赖）**：前提是满足 2NF，且非主键字段之间不能有依赖关系。

反例：员工表 `employees(emp_id, dept_id, dept_name)`，`dept_name` 依赖 `dept_id`，而 `dept_id` 又依赖 `emp_id`——这就是「传递依赖 `emp_id → dept_id → dept_name`」。

正例：拆出 `departments(dept_id, dept_name)` 表，`employees` 只保留 `dept_id`。

追问 反范式（冗余字段）是错的吗？实际项目里怎么用？

**不是错，是权衡**。范式的目的是消除冗余、保证一致性；**反范式的目的是消除 JOIN、提升查询性能**。典型场景：

- **报表/大宽表**：把订单表冗余进商品名、用户名、店铺名，一条 SQL 就能出报表，不用 4 表 JOIN。

- **历史快照**：订单表里的 `product_name`、`unit_price` 必须冗余——商品表后来改名或涨价，历史订单不能跟着变。

- **热点计数**：文章表冗余 `comment_count`、`like_count`，避免每次列表页都要 `COUNT(*)`。

代价是**写复杂度上升**（改一个地方要同步多处）+ **数据可能不一致**（异常情况下冗余字段跟源头对不上）。做架构决策时看业务：读多写少、对实时一致性要求不高，就大胆冗余；核心账户/资金/库存，宁可 JOIN 也要保证范式化。

## 面试场景 6：char 和 varchar 的区别？★经典

维度`char(n)``varchar(n)`

存储方式定长——不足 n 用空格补齐变长——只存实际长度
长度前缀无1 字节（<=255）或 2 字节（>255）
读取时行为末尾空格会被去掉末尾空格保留
最大长度255 字符65535 字节（受行大小限制）
适用场景长度几乎固定的字段长度差异大的字段
性能定长——快，无需处理长度变长——省空间但要额外读长度

**怎么选**：

- 用 `char`：`gender char(1)`、`md5_hash char(32)`、`id_card char(18)`、`country_code char(2)`——长度固定且比较短。

- 用 `varchar`：`username varchar(50)`、`address varchar(200)`、`title varchar(100)`——长度差异大。

陷阱 `varchar(n)` 里的 n 是**字符数**不是字节数（MySQL 4.1+）。用 `utf8mb4`（每个字符最多 4 字节）时，`varchar(100)` 最多能存 100 个字符，占 400 字节。所以 *「长度只影响能存多少字符，不影响实际占用空间」*——只按实际内容算。

追问 那 `varchar(50)` 和 `varchar(200)` 存同样内容占用空间一样，为什么还要区分？

两个理由：**(1) 语义约束**——声明 50 就是告诉后来者「这个字段业务上不会超过 50 个字符」，超过会报错，防脏数据；**(2) 内存分配**——MySQL 在处理 `ORDER BY`、临时表、变长内存分配时，会按声明的最大长度预留空间。声明 `varchar(65535)` 会让排序缓冲区快速爆掉。所以**「够用就好，别贪大」**。

## 面试场景 7：金额字段用什么类型？DECIMAL vs FLOAT/DOUBLE

🎤 面试官

存商品价格、账户余额这种金额字段，你会用什么类型？

🧑‍💻 你

必须用 `DECIMAL`，**不能**用 `FLOAT` / `DOUBLE`。

- `DECIMAL(M, D)`：**定点数**，精确存储。M 是总位数，D 是小数位数。`DECIMAL(10, 2)` 能存 `-99999999.99` 到 `99999999.99`。

- `FLOAT` / `DOUBLE`：**浮点数**，IEEE 754 二进制近似表示，*会有精度损失*——存 `0.1` 实际是 `0.100000001490116...`。

金融、汇率、账户余额这种**不允许一分钱误差**的场景，浮点数是绝对禁区。这跟 0009 课讲的 Java `BigDecimal` 是完全一个道理——都是*用十进制的字符串/整数存法避开二进制浮点*。

Java 侧对应：MySQL 的 `DECIMAL` 用 JDBC 取出来就是 `java.math.BigDecimal`，两者天然打通。

追问 除了 DECIMAL，还有什么办法存金额？

**用 `bigint` 存最小货币单位**——比如金额以「分」为单位存（100 元 = 10000 分）。优点是整数运算永远精确、性能比 `DECIMAL` 好、索引空间小。缺点是应用层要记得除 100 显示、加减乘除都要注意单位。国内互联网大厂（阿里、字节的交易系统）很多都用这个方案。选择上：**加法为主的记账类用 `bigint`；有大量乘除、汇率转换的用 `DECIMAL`**。

## 面试场景 8：datetime 和 timestamp 有什么区别？

维度`DATETIME``TIMESTAMP`

存储空间8 字节4 字节
范围1000-01-01 到 9999-12-311970-01-01 到 2038-01-19（★2038 问题）
时区不受时区影响，存什么读什么存的是 UTC，读的时候按会话时区转换
默认值MySQL 5.6+ 才支持 `DEFAULT CURRENT_TIMESTAMP`原生支持 `DEFAULT CURRENT_TIMESTAMP`
自动更新需要显式声明可用 `ON UPDATE CURRENT_TIMESTAMP`

**怎么选**：

- 如果业务只服务国内，用 `datetime` 就好——直观、无 2038 隐患。

- 如果业务跨时区（用户在美/欧/亚都有），可以用 `timestamp` 让 MySQL 帮你自动做 UTC 转换；但更推荐**在应用层统一用 UTC 存 `datetime`**，展示时按用户时区渲染——一致性更强，也躲开了 2038 问题。

陷阱 · 2038 问题 `TIMESTAMP` 底层是 32 位有符号整数，存 UTC 秒数。到 **2038-01-19 03:14:07 UTC** 就会溢出，回到 1970 年——跟 Unix 时间戳的 Y2K38 问题是同一个。想活到 2038 年之后的表，别用 `timestamp`，用 `datetime` 或 `bigint` 存毫秒。

## 面试场景 9：NULL 的坑—— `WHERE col = NULL` 为什么查不到？

🎤 面试官

看这条 SQL：`SELECT * FROM users WHERE deleted_at = NULL`，为什么查不到数据？

🧑‍💻 你

因为 SQL 里 **NULL 不是一个值，而是「未知」**。任何值和 NULL 做比较，结果都是 NULL（不是 `TRUE`，也不是 `FALSE`），`WHERE` 只保留结果为 `TRUE` 的行——所以永远查不到。

正确写法：

```
SELECT * FROM users WHERE deleted_at IS NULL;      -- 找未删除的
SELECT * FROM users WHERE deleted_at IS NOT NULL;  -- 找已删除的
```

NULL 的其他坑：

- **聚合函数忽略 NULL**：`SUM(col)`、`AVG(col)`、`COUNT(col)` 都会跳过 NULL 行；*只有 `COUNT(*)` 会数上*。

- **NULL 参与算术全变 NULL**：`NULL + 1 = NULL`、`CONCAT('a', NULL) = NULL`。

- **唯一索引允许多个 NULL**：一个字段声明 UNIQUE，也可以有多行都是 NULL（因为 NULL != NULL）。

- **索引效率下降**：NULL 会让索引统计不准、优化器估算行数偏差；InnoDB 的 NULL 值也要单独存 NULL 位图。

阿里 Java 规约的建议：**能 `NOT NULL` 就 `NOT NULL`**，给个合理默认值（数字给 0，字符串给 `''`）。

追问 `WHERE col != NULL` 为什么也查不到？

同样的原因：`col != NULL` 结果也是 NULL，不是 `TRUE`。要查「不为 NULL」必须用 `IS NOT NULL`。想同时匹配「不等于某个值 OR 为 NULL」，得写成 `WHERE col <> 5 OR col IS NULL`；或者用 MySQL 特有的**安全等于运算符** `<=>`：`col <=> NULL` 会返回 `TRUE`。

## 面试场景 10：JOIN 的分类 & SQL 执行顺序

🎤 面试官

你说说 `INNER JOIN`、`LEFT JOIN`、`RIGHT JOIN`、`CROSS JOIN` 的区别。再说说一条完整的 SQL 是按什么顺序执行的。

🧑‍💻 你

**JOIN 分类**：

- **INNER JOIN**：两表交集，只保留匹配上的行。*最常用*。

- **LEFT JOIN**：以左表为主，左表所有行都保留；右表没匹配上的列用 NULL 填充。*「查用户和他的订单，没订单的用户也要显示」的场景*。

- **RIGHT JOIN**：跟 LEFT 对称，以右表为主。实际很少用——习惯上都写成 LEFT JOIN 把表调换顺序。

- **CROSS JOIN**：笛卡尔积，两表所有行组合。生产上几乎不用，只在生成日期序列、测试数据爆量的场景。

- （附：**FULL OUTER JOIN** —— 两表并集，MySQL 不原生支持，要 `UNION` 模拟）

**SQL 执行顺序（★面试常考）**：注意跟书写顺序完全不同！

```
-- 书写顺序（我们写 SQL 的顺序）
SELECT     ...
FROM       ...
JOIN       ...  ON ...
WHERE      ...
GROUP BY   ...
HAVING     ...
ORDER BY   ...
LIMIT      ...

-- 逻辑执行顺序（MySQL 实际处理的顺序）
1. FROM       ← 先定位主表
2. JOIN / ON  ← 关联其它表
3. WHERE      ← 行过滤（此时还没聚合，用不了聚合函数）
4. GROUP BY   ← 分组
5. HAVING     ← 组过滤（可以用聚合函数）
6. SELECT     ← 选列 / 计算表达式 / 应用别名
7. ORDER BY   ← 排序（可以用 SELECT 里的别名，因为在它之后）
8. LIMIT      ← 截取
```

这个顺序解释了很多「为什么」：

- 为什么 `WHERE` 里不能写聚合函数？—— 因为 `WHERE` 在 `GROUP BY` 之前执行。

- 为什么 `WHERE` 里不能用 `SELECT` 起的别名？—— 因为 `SELECT` 在 `WHERE` 之后。

- 为什么 `ORDER BY` 里可以用 `SELECT` 的别名？—— 因为 `ORDER BY` 在 `SELECT` 之后。

追问 GROUP BY 之后要过滤某些组，用 WHERE 还是 HAVING？

**用 `HAVING`**。`WHERE` 在 `GROUP BY` 之前，只能过滤原始行；`HAVING` 在 `GROUP BY` 之后，可以过滤分组结果，也可以用聚合函数。举例：查「订单数超过 10 单的用户」
`SELECT user_id, COUNT(*) AS cnt FROM orders GROUP BY user_id HAVING cnt > 10;`
—— 这里的 `cnt > 10` 涉及聚合函数结果，只能放 HAVING。
性能上：能放 `WHERE` 的过滤条件（对原始行的筛选，跟聚合无关）尽量放 `WHERE`——先减少参与分组的数据量，效率更高。

## 💻 代码验证（打开 `mysql` CLI 跑一遍）

### 验证 1：InnoDB vs MyISAM 事务差异

```
-- 建两张同样结构、不同引擎的表
CREATE TABLE t_innodb (id INT PRIMARY KEY, name VARCHAR(20)) ENGINE=InnoDB;
CREATE TABLE t_myisam (id INT PRIMARY KEY, name VARCHAR(20)) ENGINE=MyISAM;

-- InnoDB 事务能回滚
BEGIN;
INSERT INTO t_innodb VALUES (1, 'a'), (2, 'b');
ROLLBACK;
SELECT * FROM t_innodb;   -- 空。事务回滚，插入被撤销

-- MyISAM 不支持事务，ROLLBACK 无效
BEGIN;
INSERT INTO t_myisam VALUES (1, 'a'), (2, 'b');
ROLLBACK;
SELECT * FROM t_myisam;   -- 有两行。MyISAM 忽略事务，数据落地了
```

### 验证 2：char vs varchar 的末尾空格行为

```
CREATE TABLE t_str (
c CHAR(10),
v VARCHAR(10)
);
INSERT INTO t_str VALUES ('abc   ', 'abc   ');   -- 都存 'abc' + 三个空格

SELECT
CONCAT('[', c, ']') AS c_val,
LENGTH(c)           AS c_len,
CONCAT('[', v, ']') AS v_val,
LENGTH(v)           AS v_len
FROM t_str;

-- 结果：
-- c_val = '[abc]'         c_len = 3   ← char 末尾空格被去掉
-- v_val = '[abc   ]'      v_len = 6   ← varchar 保留末尾空格
```

### 验证 3：DECIMAL 精确 vs DOUBLE 失真

```
CREATE TABLE t_money (
d  DECIMAL(20, 4),
f  DOUBLE
);
INSERT INTO t_money VALUES (0.1, 0.1);
INSERT INTO t_money VALUES (0.2, 0.2);

SELECT SUM(d), SUM(f) FROM t_money;

-- SUM(d) = 0.3000                    ← DECIMAL 精确
-- SUM(f) = 0.30000000000000004       ← DOUBLE 二进制误差
```

### 验证 4：NULL 的比较陷阱

```
CREATE TABLE t_null (id INT, name VARCHAR(10));
INSERT INTO t_null VALUES (1, 'a'), (2, NULL), (3, 'b');

-- 这三条都查不到 name 为 NULL 的第 2 行！
SELECT * FROM t_null WHERE name = NULL;    -- 0 行
SELECT * FROM t_null WHERE name != NULL;   -- 0 行
SELECT * FROM t_null WHERE name <> NULL;   -- 0 行

-- 正确写法
SELECT * FROM t_null WHERE name IS NULL;       -- id=2
SELECT * FROM t_null WHERE name IS NOT NULL;   -- id=1, id=3

-- MySQL 特有的安全等于
SELECT * FROM t_null WHERE name <=> NULL;      -- id=2

-- 聚合函数忽略 NULL
SELECT COUNT(*), COUNT(name) FROM t_null;      -- 3, 2
```

### 验证 5：SQL 执行顺序 & WHERE vs HAVING

```
CREATE TABLE orders (
id       INT PRIMARY KEY,
user_id  INT,
amount   DECIMAL(10, 2),
status   VARCHAR(10)
);
INSERT INTO orders VALUES
(1, 100, 50.00,  'paid'),
(2, 100, 30.00,  'paid'),
(3, 100, 20.00,  'cancelled'),
(4, 200, 100.00, 'paid'),
(5, 300, 10.00,  'paid');

-- 查每个用户的已支付订单金额，且总金额 > 40
SELECT
user_id,
SUM(amount) AS total
FROM orders
WHERE status = 'paid'         -- 先过滤行（在 GROUP BY 之前）
GROUP BY user_id
HAVING total > 40             -- 再过滤组（可以用 SELECT 的别名 total）
ORDER BY total DESC;

-- 结果：
-- user_id=200, total=100.00
-- user_id=100, total=80.00
-- （user_id=300 的 total=10.00 被 HAVING 过滤；已 cancelled 的行被 WHERE 过滤）
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 InnoDB 相比 MyISAM 最关键的四个优势是什么？</summary>

事务（ACID）、行锁、崩溃恢复、外键。第五个是 MVCC。这四个是绝大多数业务系统的刚需，所以 MySQL 5.5+ 默认引擎从 MyISAM 换成了 InnoDB。

</details>

<details>

<summary>Q2 一条 SELECT 语句从 Client 发到 MySQL Server 后，会依次经过哪些组件？</summary>

连接器（鉴权） → 查询缓存（8.0 已移除） → 分析器（词法/语法） → 优化器（选索引、定 join 顺序） → 执行器（调存储引擎接口） → 存储引擎层（InnoDB 等）取数据 → 返回。

</details>

<details>

<summary>Q3 三大范式各自消除了什么问题？举一句反例。</summary>

1NF 消除字段不原子（例：`联系方式='138xxxx, x@x'`）；2NF 消除部分依赖（例：`order_items` 里存 `product_name`——只依赖 `product_id`，不依赖复合主键的全部）；3NF 消除传递依赖（例：`employees` 里存 `dept_name`——通过 `dept_id` 传递依赖）。

</details>

<details>

<summary>Q4 `char` 和 `varchar` 各适合什么场景？各自的最大长度是多少？</summary>

char 定长，适合长度几乎固定的字段（性别、MD5、身份证、国家码），最大 255 字符；varchar 变长，适合长度差异大的字段（用户名、地址、标题），最大 65535 字节（一整行的限制里）。

</details>

<details>

<summary>Q5 为什么 `WHERE col = NULL` 永远查不到数据？正确写法是什么？</summary>

因为 NULL 表示「未知」，任何值和 NULL 比较结果都是 NULL 而不是 TRUE，`WHERE` 只保留 TRUE 的行。正确写法：`WHERE col IS NULL`；MySQL 还有安全等于 `WHERE col <=> NULL`。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源（本课只覆盖概念部分，索引/事务/日志留给 0043-0049）

- MySQL 8.0 Reference · Alternative Storage Engines —— InnoDB / MyISAM 官方对比

- MySQL 8.0 Reference · Data Types —— 所有数据类型的权威说明

#### 🔗 关联课件

- （上一课 · 阶段五收尾）

- （下一课，深入 Server 层）

-

-

#### 🧭 下一课预告

Lesson 0042：**一条 SQL 的执行流程详解** —— 把本课架构图里的 Server 层五个组件（连接器/缓存/分析器/优化器/执行器）逐一展开，讲清楚「一条 SQL 是怎么变成执行计划、又怎么落到 InnoDB 的」。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


