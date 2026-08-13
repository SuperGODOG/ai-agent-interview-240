> Lesson 0052 · 阶段七 · Redis · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 7 个追问

# 0052 · Redis 5 种基本数据类型 & 底层实现 & 使用场景

这一课是 Redis 章节的**核心开局**，也是**面试出场率最高的一课** —— 几乎没有任何一场 Java 后端面试会跳过它。面试官会连珠炮地问：**「Redis 有哪几种基本类型？」「List 底层是什么？」「ZSet 用什么实现？」「排行榜怎么做？」「存对象用 String 还是 Hash？」**—— 每一问都能直接决定是否进入下一轮。本课覆盖 的全部高频考点，并把底层编码（SDS / ziplist / listpack / quicklist / skiplist / intset）串成一条完整逻辑线。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Redis List 底层数据结构是什么？Redis 7.0 之后有变化吗？</summary>

3.2 之前是 `linkedList` 或 `ziplist`；3.2 引入 `quicklist`（双向链表挂多个 `ziplist` 节点）；7.0 起 `ziplist` 被 `listpack` 替代（解决级联更新问题）。所以现在的 List = *双向链表 + listpack 节点*。第 3、7 题细讲。

</details>

<details>

<summary>Q0.2 Sorted Set（ZSet）用什么数据结构实现？为什么不用红黑树？</summary>

小场景用 `ziplist`/`listpack`；大场景用 **跳表 skiplist + hashtable** 组合。不用红黑树的原因：跳表实现简单、范围查询直接沿底层链表走 O(log n) + O(m)、内存开销可控、并发扩展性更好。第 6 题细讲。

</details>

## 面试场景 1：Redis 5 种基本数据类型都是什么？各自底层是什么？

🎤 面试官

先来热身：Redis 有哪几种基本数据类型？各自的底层数据结构是什么？

🧑‍💻 你

Redis 有 **5 种基本数据类型**：`String`、`List`、`Hash`、`Set`、`Sorted Set`（简称 ZSet）。每一种在*数据结构*和*底层编码*之间有一层映射关系 —— Redis 会根据数据量大小自动选择更省内存或更快的编码：

数据类型底层编码切换条件（默认）

`String``int` / `embstr` / `raw`纯整数走 int；≤ 44 字节走 embstr；否则 raw
`List``quicklist`（内部节点用 `listpack`，7.0 前用 `ziplist`）始终 quicklist
`Hash``listpack`（旧版 `ziplist`） / `hashtable`元素 < 128 且每个字段 < 64B 走 listpack
`Set``intset` / `listpack`（7.2+） / `hashtable`全整数且 < 512 走 intset
`ZSet``listpack`（旧版 `ziplist`） / `skiplist + hashtable`元素 < 128 且每个元素 < 64B 走 listpack

核心思路：*小规模*下用**紧凑连续内存**的编码（省内存、命中缓存快），*大规模*下用**正规数据结构**（保证时间复杂度）。这也是 Redis 内存效率的关键设计。

追问 除了这 5 种，Redis 还有哪些数据类型？

还有 3 种**特殊类型**：`Bitmap`（位图，做用户签到、活跃统计）、`HyperLogLog`（基数统计，做大规模 UV）、`Geo`（地理位置，基于 ZSet + GeoHash 实现）。5.0 之后又加了 `Stream`（真正的消息队列）、以及 4.0+ 靠模块加载的 `Bloom Filter`。这些放在下一课 0053 细讲。

## 面试场景 2：String 的底层实现 SDS 是什么？相比 C 字符串有什么优势？

🎤 面试官

Redis 为什么不直接用 C 的字符串，而是自己搞了一个 SDS？

🧑‍💻 你

**SDS（Simple Dynamic String，简单动态字符串）**是 Redis 自研的字符串结构。核心结构大致是：

```
struct sdshdr {
int len;         // 已使用字节数（字符串真实长度）
int free;        // 剩余可用字节数（预分配空间）
char buf[];      // 字符数组（柔性数组，实际存字符）
};
```

相比 C 原生的 `char*`（以 `\0` 判定结束），SDS 有 **5 大优势**：

1. **O(1) 取长度**：`len` 字段直接读，C 字符串要遍历到 `\0`，是 O(N)。所以 `STRLEN` 在 Redis 里是常数时间。

2. **二进制安全**：SDS 用 `len` 判定结束，字符数组里可以存 `\0`、图片、序列化对象等任意二进制数据；C 字符串遇 `\0` 就截断。

3. **杜绝缓冲区溢出**：SDS 拼接前会检查 `free` 是否足够，不够就先扩容再拼，天然安全；C 的 `strcat` 不检查目标缓冲区，可能溢出。

4. **动态扩容 + 空间预分配**：扩容时如果扩后 < 1MB 就分配 2 倍，> 1MB 就每次多 1MB。*减少内存分配次数*。

5. **惰性释放**：字符串缩短后不立刻回收内存，暂存到 `free`，下次要扩容时直接用。

追问 String 有几种底层编码？分别什么时候用？

3 种编码，Redis 会根据值自动选择：

- **`int`**：值是能用 `long` 表示的整数（如 `SET k 123`）。直接用 8 字节整数存，不分配 SDS，最省空间。

- **`embstr`**：短字符串（≤ 44 字节）。`redisObject` 和 SDS 分配在一块连续内存，只需 1 次 malloc，缓存友好。

- **`raw`**：长字符串（> 44 字节）。`redisObject` 和 SDS 分开分配，需要 2 次 malloc。

*注意*：编码转换是**不可逆**的 —— 一旦 embstr 因为追加变成了 raw，即使后来缩短了也不会退回 embstr。

## 面试场景 3：List 的底层演进 —— 从 ziplist 到 quicklist 到 listpack

🎤 面试官

Redis List 底层是什么？为什么会经历这么多次演进？

🧑‍💻 你

List 底层**演进三阶段**：

1. **Redis 3.2 之前**：短 List 用 `ziplist`（连续内存、省空间），长 List 用 `linkedList`（双向链表、支持任意长度）。*问题*：ziplist 有级联更新性能陷阱；linkedList 每个节点 3 个指针（prev/next/value）内存浪费。

2. **Redis 3.2 引入 `quicklist`**：双向链表的每个节点*本身就是一个 ziplist*。这样既支持了任意长度（外层是链表），又省内存（内层每个节点存多个元素）。

3. **Redis 7.0 起**：quicklist 的内部节点从 `ziplist` 换成 `listpack`，彻底摆脱级联更新问题。

结构可以这样画：

```
quicklist:
+--------+     +--------+     +--------+
| node1  | <-> | node2  | <-> | node3  |
+--------+     +--------+     +--------+
|              |              |
[listpack]     [listpack]     [listpack]
[a,b,c,d]      [e,f,g,h]      [i,j,k,l]
```

常用命令：`LPUSH` / `RPUSH`（左/右侧插入）、`LPOP` / `RPOP`（左/右弹出）、`LRANGE key 0 -1`（区间查询）、`BLPOP`（阻塞弹出，做消息队列）。

追问 ziplist 的「级联更新」问题是什么？

`ziplist` 是一段连续内存，每个 entry 存前一个 entry 的长度（`prevlen`）。`prevlen` 编码：前节点 < 254 字节用 1 字节存，否则用 5 字节存。**问题来了**：如果修改中间某节点让它长度突破 254 字节，那么它后面那个节点的 `prevlen` 就要从 1 字节扩到 5 字节，这本身又让那个节点变长，可能又触发下下个节点扩容 …… *最坏情况一次修改触发整个 ziplist 所有节点重新编码*，O(N²) 级别性能崩溃。这就是 Redis 7.0 用 `listpack` 替代 ziplist 的直接原因 —— listpack 的每个 entry 只存自己的长度，不存前节点长度，从设计上消除级联更新。

追问 List 的应用场景有哪些？

4 个高频场景：**消息队列**（`LPUSH` + `BRPOP` 生产/消费；但 Stream 之后更推荐用 Stream）、**时间线/信息流**（微博发布 Timeline，`LPUSH` 插最新、`LRANGE 0 9` 取前 10 条）、**最近浏览/点击记录**（`LPUSH` + `LTRIM 0 99` 保留最近 100 条）、**评论列表**（分页 `LRANGE`）。

## 面试场景 4：Hash 的底层实现 & 什么时候用它？

🎤 面试官

Redis 的 Hash 底层是什么？和 Java 的 HashMap 有什么区别？

🧑‍💻 你

Redis Hash 是 **field → value** 的映射表，两种底层编码：

- **`listpack`**（旧版为 `ziplist`）：元素少且短时用。默认*字段数 < 128 且每个字段/值长度 < 64 字节*时启用。紧凑内存布局，省空间。

- **`hashtable`**：超过阈值转此。结构类似 JDK 1.7 的 HashMap（数组 + 拉链），采用*渐进式 rehash*（rehash 时新旧两个表并存，每次访问搬一小部分）避免大 Hash 一次性 rehash 阻塞。

常用命令：`HSET` / `HGET`（单字段读写）、`HMSET` / `HMGET`（批量）、`HGETALL`（取所有字段，注意大 Hash 会阻塞）、`HINCRBY`（字段自增）、`HDEL`、`HLEN`、`HEXISTS`。

典型场景：**对象字段级存储** —— 比如用户信息 `user:1001 {name: Alice, age: 20, city: SH}`，需要修改单个字段时（`HSET user:1001 age 21`）不用整体反序列化。相比 `String` 存 JSON 更灵活。

追问 Redis 的 rehash 和 Java HashMap 的 resize 有什么区别？

Java HashMap 的 resize 是**一次性搬完**所有 bucket，大表 resize 会卡住业务线程。Redis 用**渐进式 rehash**：分配一个新表 `ht[1]`（老表 `ht[0]` 依旧存在），每次执行 `HSET` / `HGET` / `HDEL` 时顺手把 `ht[0]` 里一个 bucket 迁移到 `ht[1]`；再加一个定时任务兜底。*期间读操作先查 ht[0] 再查 ht[1]，写操作只写 ht[1]*。全部迁移完成后释放 `ht[0]`。这样把 O(N) 的 rehash 拆成 N 次 O(1) 的操作，不阻塞主线程。

## 面试场景 5：Set 的底层实现 & intset 什么时候转 hashtable？

🎤 面试官

Set 底层是什么？`intset` 什么情况下会转成 `hashtable`？

🧑‍💻 你

Set 是**无序不重复**集合。底层三种编码：

- **`intset`**：全是整数*且元素数 < 512*时启用。有序数组，二分查找 O(log n)。

- **`listpack`**（Redis 7.2+ 新加）：非整数但元素少（< 128）时启用，紧凑省内存。

- **`hashtable`**：超过阈值转此，value 全是 null 的哈希表，O(1) 查找。

常用命令：`SADD`（加元素）、`SMEMBERS`（取所有）、`SISMEMBER`（判断是否存在，O(1)）、`SCARD`（元素数）、`SINTER`/`SUNION`/`SDIFF`（交/并/差集）、`SPOP`（随机弹出）、`SRANDMEMBER`（随机取但不删）。

典型场景：**标签系统**（文章打标签，一篇文章一个 Set）、**小规模去重**（UV 少量 IP 存 Set；大规模用 HyperLogLog）、**共同好友**（两个 Set 求 `SINTER`）、**随机抽奖**（`SPOP` 每次弹一个中奖用户，不重复）。

追问 一旦 intset 转成 hashtable，之后元素减少了能不能转回 intset？

**不能，转换不可逆**。一旦触发升级到 hashtable，后续即便删掉所有非整数元素或元素数减到 100，Set 也不会再退回 intset。原因：反复来回转换的开销大于内存收益，且实现复杂。同理，Hash / ZSet 从 listpack 升级到 hashtable / skiplist 后也不会退回。

## 面试场景 6：ZSet 的底层实现 & 为什么用跳表不用红黑树？⭐核心

🎤 面试官

Sorted Set 底层是什么？为什么选跳表而不是红黑树或 AVL 树？

🧑‍💻 你

ZSet 是**带 score 排序的去重集合**。两种底层编码：

- **`listpack`**（旧版 ziplist）：元素少且短时用。默认*元素数 < 128 且每个元素长度 < 64 字节*。

- **`skiplist + hashtable`**：超过阈值转此。*组合结构*：跳表按 score 有序排列支持范围查询 `ZRANGE`；hashtable 存 member → score 映射支持 O(1) 查 `ZSCORE`。两个结构指向同一份数据，不重复存。

为什么选跳表而不是红黑树（面试标准答案 4 点）：

1. **范围查询更快**：跳表底层就是有序链表，找到起点后直接沿链表往后走 O(m)；红黑树要中序遍历，实现复杂常数更大。ZSet 的 `ZRANGEBYSCORE` 场景极常见，跳表天然适配。

2. **实现简单**：跳表就是多层链表 + 随机高度，代码量小、bug 少；红黑树的旋转和着色规则复杂。

3. **内存更可控**：跳表节点高度随机（几何分布，平均 1/(1-p)），可以通过调 `ZSKIPLIST_P`（Redis 默认 0.25）平衡内存和查询速度。

4. **并发扩展性好**：跳表在*局部修改*只影响一小段指针（虽然 Redis 主线程单线程用不到，但理论上易做无锁化）。

常用命令：`ZADD key score member`、`ZSCORE`（查分数）、`ZRANGE key 0 -1 WITHSCORES`（按 score 升序）、`ZREVRANGE`（降序）、`ZRANGEBYSCORE`（按 score 区间）、`ZRANK` / `ZREVRANK`（查排名）、`ZINCRBY`（分数自增）。

追问 ZSet 用 skiplist + hashtable 双结构不是浪费内存吗？

并不完全浪费。**两个结构指向同一份 member 数据，只是索引不同**。hashtable 只存 `member → score` 的指针映射，多出来的内存开销是可以接受的 —— 换来的是 `ZSCORE` 从跳表的 O(log n) 降到 O(1)。这是*空间换时间*的经典权衡。

## 面试场景 7：Redis 7.0 为什么用 listpack 替代 ziplist？

🧑‍💻 你

直接原因就是**消灭 ziplist 的级联更新**。两者结构对比：

特性ziplistlistpack

每个 entry 存的长度信息存*前一个 entry* 的长度（`prevlen`）只存*自己*的长度
级联更新风险有（一次修改可能触发全表重编码）**无**
反向遍历靠 prevlen 反算把 length 放在 entry 末尾同样能反向解析
整体总长字段有 `zltail` 记尾有 `total-bytes` 和 `num-elements`

Redis 7.0 之后 Hash / ZSet / List 内部小结构全面切到 listpack，性能更稳定 —— 尤其在*业务里出现变长字段频繁修改*时不会突然卡顿。

## 面试场景 8：编码切换的阈值配置有哪些？

🧑‍💻 你

Redis 提供了一组 `redis.conf` 参数控制编码切换阈值（默认值可能因版本略异）：

```
# Hash：小于阈值走 listpack，否则 hashtable
hash-max-listpack-entries 128
hash-max-listpack-value   64

# List：quicklist 内部每个 listpack 节点大小上限
list-max-listpack-size    -2     # 负数表示按大小限制：-2 = 8KB
list-compress-depth       0      # 中间节点压缩深度（LZF）

# ZSet：小于阈值走 listpack，否则 skiplist
zset-max-listpack-entries 128
zset-max-listpack-value   64

# Set：全整数且小于此值走 intset
set-max-intset-entries    512
# Redis 7.2+ 新增：小 Set 走 listpack
set-max-listpack-entries  128
set-max-listpack-value    64
```

面试时不需要背具体值，但要说清**「有这么一组参数」「小规模紧凑编码、大规模正规结构」「转换不可逆」**三个要点即可。

## 面试场景 9：String 是二进制安全的吗？最大能存多大？

🎤 面试官

Redis 的 String 是二进制安全的吗？最大能存多大？实际用的时候有什么注意点？

🧑‍💻 你

**是二进制安全的**。SDS 用 `len` 字段判定字符串长度，而不是像 C 字符串那样遇 `\0` 就截断。所以理论上可以存图片、视频、序列化对象、加密密文等任意二进制内容 —— 只要长度不超过上限。

**最大 512MB**（这是 Redis 官方限制）。但*强烈不建议接近这个上限*，实际生产里单 key 建议 < 10KB。原因：

1. **网络阻塞**：Redis 单线程处理网络 IO，一个大 key 的 `GET` 会占满带宽阻塞其他请求。

2. **删除阻塞**：`DEL` 大 key 是 O(N)，主线程会卡住（4.0+ 可用 `UNLINK` 异步删）。

3. **过期删除阻塞**：过期时同步删除也会阻塞。

4. **集群模式下 rehash 慢**：迁移大 key 会长时间占用槽位。

解决方案：**拆分**（大 JSON 拆成多个字段用 Hash；大 List 按时间分片）、**压缩**（gzip / Snappy 后再存）、**放对象存储**（图片/视频存 OSS/S3，Redis 只存 URL）。

陷阱 生产事故常见起因就是 **big key**：某个 Hash 存了几十万字段、某个 List 攒了几百万条、某个 ZSet 排行榜没做截断。`redis-cli --bigkeys` 是排查利器，定期跑一遍能提前发现隐患。

## 面试场景 10：存对象用 String JSON 还是 Hash？⭐经典

🎤 面试官

业务里要缓存一个用户对象，你会用 String 存 JSON 还是用 Hash？为什么？

🧑‍💻 你

两种方案各有优劣，选型看**读写模式**：

维度String + JSONHash

存储方式`SET user:1 '{"name":"A","age":20}'``HSET user:1 name A age 20`
整体读取**极快**：一次 `GET` + 一次反序列化需 `HGETALL`（大 Hash 慢），拿到 flat map 再组装
单字段读必须 `GET` 全部 + 反序列化`HGET user:1 age`，直接取
单字段改GET → 反序列化 → 改 → 序列化 → SET，5 步且非原子`HSET user:1 age 21`，1 步且原子
字段自增需要在应用层做`HINCRBY user:1 score 10`，服务端原子
内存开销较小（JSON 紧凑）略大（Hash 元数据）
过期粒度整个对象一起过期只能整个 Hash 过期，字段级过期 7.4 后才支持

**选型结论**：

- *整读整写多、字段修改少* → **String + JSON**（如：商品详情、文章内容缓存）。

- *需要频繁读写单个字段*或*需要字段级原子操作* → **Hash**（如：用户资料的最后登录时间、购物车的商品数量、积分自增）。

- 字段特别多且大 → 拆表，别塞进一个 key。

## 💻 代码验证（打开 redis-cli 跑一遍）

### 验证 1：String 编码切换 int → embstr → raw

```
127.0.0.1:6379> SET k1 12345
OK
127.0.0.1:6379> OBJECT ENCODING k1
"int"                       # 纯整数走 int

127.0.0.1:6379> SET k2 "hello redis"
OK
127.0.0.1:6379> OBJECT ENCODING k2
"embstr"                    # 短字符串（≤ 44 字节）走 embstr

127.0.0.1:6379> SET k3 "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
OK
127.0.0.1:6379> OBJECT ENCODING k3
"raw"                       # 长字符串（> 44 字节）走 raw

127.0.0.1:6379> APPEND k2 " append-more"
(integer) 23
127.0.0.1:6379> OBJECT ENCODING k2
"raw"                       # embstr 一旦被修改会立刻升级 raw（且不可逆）
```

### 验证 2：List 的 quicklist 编码（7.0+ 内部是 listpack）

```
127.0.0.1:6379> RPUSH tasks "task-1" "task-2" "task-3"
(integer) 3
127.0.0.1:6379> OBJECT ENCODING tasks
"listpack"                  # 7.0+ 小 List 直接 listpack（无外层 quicklist）
127.0.0.1:6379> LRANGE tasks 0 -1
1) "task-1"
2) "task-2"
3) "task-3"
127.0.0.1:6379> LPOP tasks
"task-1"                    # 左侧弹出（可做消息队列消费端）
127.0.0.1:6379> BRPOP tasks 5
1) "tasks"
2) "task-3"                 # 阻塞式弹出，5 秒无消息则超时
```

### 验证 3：Hash 的 listpack ↔ hashtable 切换

```
127.0.0.1:6379> HSET user:1 name Alice age 20 city SH
(integer) 3
127.0.0.1:6379> OBJECT ENCODING user:1
"listpack"                  # 元素少，走 listpack

# 用脚本塞入 200 个字段
127.0.0.1:6379> EVAL "for i=1,200 do redis.call('HSET', KEYS[1], 'f'..i, i) end return 1" 1 user:1
(integer) 1
127.0.0.1:6379> OBJECT ENCODING user:1
"hashtable"                 # 超过 128，升级 hashtable（不可逆）

127.0.0.1:6379> HGET user:1 name
"Alice"
127.0.0.1:6379> HINCRBY user:1 age 1
(integer) 21                # 单字段原子自增
```

### 验证 4：ZSet 做排行榜

```
127.0.0.1:6379> ZADD rank 100 Alice 250 Bob 180 Cindy 90 David
(integer) 4

# 取 Top-3（降序，带分数）
127.0.0.1:6379> ZREVRANGE rank 0 2 WITHSCORES
1) "Bob"
2) "250"
3) "Cindy"
4) "180"
5) "Alice"
6) "100"

# 查某人的排名（从 0 开始）
127.0.0.1:6379> ZREVRANK rank Alice
(integer) 2                 # Alice 排第 3

# 给 Alice 加 200 分
127.0.0.1:6379> ZINCRBY rank 200 Alice
"300"                       # 现在 Alice 300 分，登顶

# 按分数区间查（100 <= score <= 200）
127.0.0.1:6379> ZRANGEBYSCORE rank 100 200 WITHSCORES
1) "Cindy"
2) "180"
```

### 验证 5：Set 交集做「共同关注」

```
127.0.0.1:6379> SADD user:1:following Alice Bob Cindy David
(integer) 4
127.0.0.1:6379> SADD user:2:following Alice Cindy Eve Frank
(integer) 4

# 求交集：user:1 和 user:2 共同关注的人
127.0.0.1:6379> SINTER user:1:following user:2:following
1) "Alice"
2) "Cindy"

# 求差集：user:1 关注但 user:2 没关注（可作为好友推荐）
127.0.0.1:6379> SDIFF user:1:following user:2:following
1) "Bob"
2) "David"

# 随机抽奖：从活动 Set 中随机弹 3 个（弹出即删除）
127.0.0.1:6379> SADD lottery u1 u2 u3 u4 u5 u6 u7 u8 u9 u10
(integer) 10
127.0.0.1:6379> SPOP lottery 3
1) "u7"
2) "u2"
3) "u9"
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 Redis 5 种基本数据类型分别是什么？各自最常见的一个使用场景？</summary>

String（缓存对象 JSON / 计数器）、List（消息队列 / 时间线）、Hash（对象字段级存储）、Set（去重 / 共同好友）、Sorted Set（排行榜 / 优先级队列）。

</details>

<details>

<summary>Q2 SDS 相比 C 字符串的 5 个优势是什么？</summary>

① O(1) 取长度（`len` 字段直接读）；② 二进制安全（用 len 判定结束，可存任意二进制）；③ 杜绝缓冲区溢出（拼接前检查 free）；④ 动态扩容 + 空间预分配（减少 malloc 次数）；⑤ 惰性释放（缩短后先攒着）。

</details>

<details>

<summary>Q3 Redis 7.0 为什么用 listpack 替代 ziplist？</summary>

消灭 ziplist 的**级联更新**问题。ziplist 每个 entry 存的是*前一个 entry 的长度*，一旦某节点扩容突破 254 字节临界值，会触发后续节点全部重编码，最坏 O(N²)。listpack 每个 entry 只存自己的长度，从设计上消除级联更新。

</details>

<details>

<summary>Q4 ZSet 为什么选跳表而不是红黑树？</summary>

① 范围查询更快 —— 底层就是有序链表，找起点后 O(m) 遍历；② 实现简单，代码量少 bug 少；③ 内存可控 —— 通过调 p 参数平衡；④ 并发扩展性好。此外 ZSet 用**跳表 + hashtable 双结构**：跳表支持范围查（`ZRANGE`），hashtable 支持 O(1) 单查（`ZSCORE`），两者指向同一份 member。

</details>

<details>

<summary>Q5 存对象用 String JSON 还是 Hash 怎么选？</summary>

看**读写模式**：整读整写多、字段修改少 → **String + JSON**（如商品详情、文章缓存）；需要频繁读写单个字段或需要字段级原子操作（如 `HINCRBY`） → **Hash**（如用户资料的最后登录时间、购物车数量、积分自增）。字段特别多要拆表。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

-  —— 跳表深挖

- Redis 官方 · Data types —— 权威命令表

#### 🔗 关联课件

- （上一课）

- （下一课）

- （数据结构深挖）

#### 🧭 下一课预告

Lesson 0053：**Redis 3 种特殊数据类型** —— Bitmap 做签到、HyperLogLog 做亿级 UV、Geo 做附近的人。这三种是「基础 5 种」之外的高频加分项，也是简历上「Redis 熟悉」的验证题。

💬 有任何疑问 —— 「listpack 结构再画一遍？」「跳表和 B+ 树区别？」「redis.conf 里编码阈值调大有什么风险？」—— 直接问我。我是你的老师，也是你的追问陪练。


