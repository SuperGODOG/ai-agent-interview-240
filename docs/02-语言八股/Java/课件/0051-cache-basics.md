> Lesson 0051 · 阶段七 · Redis · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0051 · 缓存基础 & 为什么用 Redis

欢迎进入 **阶段七 · Redis**。前面 50 节课我们已经把 Java 语言、并发、JVM、Spring、MySQL 都梳理了一遍 —— 到了 Redis，你终于能把这些拼图组合成一个「能扛真实流量」的后端服务。

本课是阶段七的开篇。我们不急着敲 `redis-cli`，先回答一个更本源的问题：**「为什么要用缓存？」**；再问 **「为什么在众多缓存方案里最终大家都用 Redis？」**。理解这两个问题之后，后续 8 节的数据结构（0052-0054）、持久化（0055）、缓存三兄弟（0056）、分布式锁（0057-0058）、集群（0059）才有意义 —— 它们其实都是在解答同一个问题的不同侧面。

对应  原文：。这一课的面试频次极高，几乎是 Redis 环节的破冰题 —— 但很多人会在 *「Redis 为什么这么快」* 和 *「Redis 是单线程还是多线程」* 这两问上翻车。我们把常见坑一次讲透。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Redis 单线程为什么这么快？（你能说出 3 条原因吗？）</summary>

① 数据在**内存**操作，比磁盘快百万倍；② **单线程**避免了锁和上下文切换；③ **IO 多路复用**（epoll）让一个线程能同时处理数万连接；④ 高效的**数据结构**（SDS、跳表、ziplist）。面试场景 4 会展开。

</details>

<details>

<summary>Q0.2 本地缓存（Caffeine）和分布式缓存（Redis）各自适合什么场景？</summary>

本地缓存适合**读多写少、变化少、能容忍多实例不一致**的数据（如系统配置、字典表、静态资源元数据）；分布式缓存适合**需要多实例共享、容量大、要能持久化**的数据（如 Session、购物车、排行榜）。生产多用**两级缓存**：本地兜命中率，Redis 兜一致性。面试场景 2 展开。

</details>

## 面试场景 1：什么是缓存？为什么要用缓存？⭐核心开场

🎤 面试官

你项目里用了 Redis，为什么要用缓存？直接查数据库不行吗？

🧑‍💻 你

**缓存的本质是「空间换时间」**：把频繁访问的数据放到*更快的存储介质*里，避免每次都去慢介质取。

速度差异很直观 —— 常见存储介质的访问延迟（近似值）：

- CPU L1 Cache：~1 ns

- CPU L2 Cache：~4 ns

- 内存 (RAM)：~100 ns

- SSD 随机读：~150 μs（约 1500 倍于内存）

- HDD 随机读：~10 ms（约 10 万倍于内存）

- 同机房网络往返：~0.5 ms

- 跨机房网络往返：~30-100 ms

所以用 Redis（内存）挡在 MySQL（磁盘）前面，就能把大部分请求的 P99 从几十毫秒压到亚毫秒级。缓存的三大直接收益：

1. **加速读**：热点数据从内存拿，响应时间断崖式下降。

2. **降低 DB 压力**：命中缓存的请求不落到 MySQL，让 MySQL 的连接池、CPU、磁盘 IO 都省下来给写操作。

3. **抗高并发**：单机 Redis QPS 轻松 10w+，MySQL 单机撑到 5000 QPS 就吃力了 —— 差了 20 倍。

追问 那是不是所有查询都应该加缓存？

不是。**缓存有成本**：多一层依赖（Redis 挂了怎么办）、多一份数据（一致性问题）、多一份内存（不便宜）。加缓存的判断标准 —— 满足 **「读多写少 + 命中率能上去 + 对延迟敏感」** 才值得加。写多读少（如日志、埋点）、每次查询都不一样（如个性化推荐结果集）、能容忍慢的（如后台管理页），都不适合。

## 面试场景 2：本地缓存 vs 分布式缓存怎么选？

🎤 面试官

Caffeine 和 Redis 都是缓存，你项目里怎么选？

🧑‍💻 你

核心区别看这张表：

维度本地缓存（Caffeine / Guava）分布式缓存（Redis / Memcached）

存储位置JVM 堆内独立服务，网络访问
访问延迟~100 ns（内存直接读）~0.5-1 ms（含网络 RTT）
容量上限受 JVM 堆大小限制（GB 级）受 Redis 内存限制（几十 GB 到 TB 级集群）
多实例共享**不共享**，每个 JVM 一份共享
数据一致性多实例间容易不一致天然一致（单一数据源）
GC 影响大对象拖累 GC与 JVM 无关
宕机丢失JVM 重启就没了可持久化（RDB/AOF）
典型场景字典表、系统配置、防抖去重Session、购物车、排行榜、分布式锁

🧑‍💻 你

生产项目里几乎都用 **两级缓存**：*本地缓存 (L1) + 分布式缓存 (L2)*。查询顺序：

```
请求 → L1 本地缓存 (Caffeine)
│  miss
▼
L2 分布式缓存 (Redis)
│  miss
▼
DB (MySQL)
│  查到后
▼
回写 L2 → 回写 L1 → 返回给用户
```

好处：热点数据在本地，直接节省一次网络往返；Redis 挂了还能扛一会儿；MySQL 更能受保护。

追问 两级缓存怎么解决数据一致性问题？

两级缓存的痛点就是本地缓存不共享 —— A 实例改了 DB，B 实例本地缓存还是旧值。三种常见解法：**① 短 TTL**（本地缓存给个 30s-1min，能忍就用这个，最简单）；**② Redis Pub/Sub**（DB 变更后 publish 一个 key，所有实例订阅后清本地缓存）；**③ Canal 监听 binlog**（DB 变化通过 MQ 广播到所有实例）。方案 ② 和 ③ 都是「最终一致」，不追求强一致。

追问 本地缓存为什么会拖累 GC？

本地缓存对象存在**老年代**（长期存活），如果缓存大对象或者数量很多，老年代占用大 → Full GC 频率高 → STW 时间长。所以 Caffeine 官方推荐**限制最大条目数**（`maximumSize`）或**基于权重**（`maximumWeight`）淘汰。真正想避开 GC 影响，就用 **OHC / Chronicle Map** 这类堆外缓存 —— 但 90% 场景 Caffeine + `maximumSize` 已经够了。

## 面试场景 3：Redis 是什么？为什么这么流行？

🧑‍💻 你

Redis (**RE**mote **DI**ctionary **S**erver) 是一个用 **C 语言**写的开源 **Key-Value 内存数据库**，2009 年由 Salvatore Sanfilippo 开源，现在已经是分布式缓存事实标准。它流行的核心原因：

1. **快**：数据放内存，单机 QPS 10w+，P99 亚毫秒。

2. **数据结构丰富**：不只 KV，还有 *Hash*（对象）、*List*（队列/栈）、*Set*（去重）、*ZSet*（排行榜）、*Bitmap*（签到）、*HyperLogLog*（UV 统计）、*Geo*（地理位置）、*Stream*（消息队列）—— 一个 Redis 能覆盖十几种业务场景。

3. **持久化**：支持 RDB 快照 + AOF 日志（0055 课细讲），宕机不丢数据。

4. **高可用**：*主从复制* + *Sentinel 哨兵* + *Cluster 集群*三级方案（0059 课）。

5. **单线程模型**：避免并发问题，命令天然原子。

6. **生态成熟**：Spring Data Redis、Redisson、Jedis、Lettuce 客户端都非常成熟；运维工具（redis-cli、RedisInsight）也齐全。

追问 Redis 除了缓存还能做什么？

非常多。看下面「面试场景 10」的完整列表 —— Redis 在生产项目里的定位早就超出了「缓存」，它是**「内存数据结构服务」**。分布式锁、限流、排行榜、Session、消息队列、Geo 附近的人、Bloom Filter（RedisBloom 模块）都能用它做。

## 面试场景 4：Redis 为什么这么快？⭐经典必问

🎤 面试官

Redis 号称 QPS 十万，你觉得它为什么这么快？

🧑‍💻 你

四个核心原因，按重要性排序：

1. **纯内存操作**：所有读写都在内存里，比磁盘随机 IO 快 5-6 个数量级。这是最主要的因素。

2. **单线程避免竞争开销**：不用加锁，不用做上下文切换，不用处理并发数据结构。CPU cache 命中率高，指令流水线不被打断。

3. **IO 多路复用（epoll）**：一个线程用 `epoll_wait` 同时监听上万个 socket，谁有数据来就处理谁。这是 Redis 能*单线程扛高并发*的关键 —— 请求本身还是并发的，只是命令*处理*串行化了。

4. **高效的数据结构**：Redis 底层数据结构都是精心设计的 —— *SDS*（简单动态字符串，避免 C 字符串溢出）、*ziplist / listpack*（小数据用连续内存节省空间）、*skiplist*（跳表 O(log n) 排序）、*quicklist*（List 底层，兼顾速度和内存）。

还有几个次要因素：**自己实现的事件驱动库 ae**（避免 libevent 的通用开销）、**协议 RESP 简单**（解析快）、**命令用汇编级别优化**（如 SIMD 加速 CRC）。

陷阱 面试官问「Redis 为什么快」时，别只答「因为在内存里」—— 这只是必要条件不是充分条件。**Memcached、H2 也在内存里，Redis 单线程反而是唯一的。** 一定要把「单线程 + IO 多路复用 + 高效数据结构」这套组合拳讲全。

追问 Redis 单线程遇到耗时命令怎么办？

**会阻塞整个 Redis！** 这是单线程模型的致命缺陷。常见炸弹命令：`KEYS *`（O(n) 扫全库，百万 key 直接卡几秒）、`FLUSHALL`、`SMEMBERS`（大 set）、`HGETALL`（大 hash）、大 key 的 `DEL`。生产做法：**用 `SCAN` 代替 `KEYS`**（游标分批）；**大 key 用 `UNLINK` 代替 `DEL`**（4.0+ 异步删除）；**业务上避免大 key**（拆分、上限）。

## 面试场景 5：Redis 是单线程还是多线程？⭐版本敏感

🎤 面试官

都说 Redis 是单线程，那 Redis 6 引入的多线程是怎么回事？

🧑‍💻 你

这个问题要按版本回答，非常容易踩坑。核心一句话：**「命令处理永远是单线程，其它辅助工作在不同版本引入了多线程。」**

版本主线程后台线程 (BIO)IO 线程

4.0 之前处理所有事情：接收连接、读 socket、执行命令、写 socket、AOF fsync无无
4.0+执行命令（单线程）**引入 BIO**：`UNLINK`（异步删大 key）、AOF fsync、清理过期无
6.0+执行命令（**仍然单线程**）同 4.0**网络 IO 多线程**：多线程 read/write socket、解析协议；命令执行仍单线程

🧑‍💻 你

为什么 Redis 6 要加 IO 多线程？—— 因为随着网卡越来越快（10Gbps+），单线程处理网络 IO 成了瓶颈。CPU 花了大量时间在 `read/write` 系统调用和协议解析上，命令执行本身反而闲着。多线程 IO 让 *网络处理* 和 *命令执行* 解耦。

但注意：**Redis 6 的多线程默认关闭**，需要手动开：

```
# redis.conf
io-threads 4              # IO 线程数（不建议超过 CPU 核数的一半）
io-threads-do-reads yes   # 读 socket 也用多线程（默认只多线程写）
```

追问 Redis 6 多线程 IO 是不是命令也多线程了？

**不是。** 这是最常被误解的一点。Redis 6 只多线程了「读 socket 数据 + 解析协议」和「写 socket 响应」这两个 IO 环节。**命令执行仍然是主线程单线程完成**。这样既解决了单线程 socket 瓶颈，又保留了「命令天然原子」「无锁竞争」「数据结构无需线程安全」这些优势。

追问 为什么 Redis 不做成命令也多线程？

做成多线程要付出巨大代价：① **所有数据结构都要加锁**（哈希表、跳表、ziplist 都得线程安全）；② **丧失命令天然原子性**，事务和 Lua 脚本模型都要重构；③ **锁竞争会抵消多线程收益**（性能反而下降）；④ **代码复杂度爆炸**。作者 Salvatore 多次表态：Redis 单线程性能已经够用，加机器（集群）比加线程性价比高得多。

## 面试场景 6：Redis vs Memcached 有什么区别？⭐经典

🎤 面试官

为什么现在大家都用 Redis 不用 Memcached 了？

维度RedisMemcached

数据结构**丰富**：String / Hash / List / Set / ZSet / Bitmap / HyperLogLog / Geo / Stream只支持 **Key-Value 字符串**
持久化支持 **RDB + AOF**，宕机可恢复**不支持**，重启数据全丢
线程模型单线程（命令）+ 多线程 IO（6.0+）原生多线程
集群方案**原生 Redis Cluster**（3.0+），支持自动分片和主从无原生集群，靠**客户端一致性哈希分片**（如 ketama）
事务支持 `MULTI/EXEC`、Lua 脚本原子性**不支持**
发布订阅支持 Pub/Sub 和 Stream不支持
过期策略惰性删除 + 定期删除惰性删除
内存管理自研（jemalloc/tcmalloc）Slab 分配（内存碎片少但可能浪费）
最大 value512 MB1 MB（默认，可调）
性能单机 10w+ QPS相当，多线程模型简单场景略高

🧑‍💻 你

总结：**Memcached 只在「纯 KV + 大对象」场景有一点点优势**（比如缓存整个网页 HTML），其它场景 Redis 完胜。所以现在国内一线大厂几乎全线换成了 Redis，Memcached 只在遗留系统里能看到。

追问 Memcached 多线程为什么反而没打过 Redis 单线程？

三个原因：① **Redis 数据结构丰富**，一个 ZSet 能干掉 Memcached 一堆 KV 拼凑出来的排行榜；② **Memcached 没持久化**，重启后缓存穿透 DB 直接被打爆，生产不敢裸用；③ **Memcached 没集群**，客户端分片扩容时数据要重新哈希，Redis Cluster 只挪迁移的槽位。综合下来 Redis 的*工程收益*远大于「多线程带来的一点点 QPS」。

追问 Redis vs MySQL，什么场景才需要 Redis？

四个信号出现任一个就该上 Redis：① **读远多于写**（读写比 10:1 以上）；② **对延迟敏感**（P99 < 5ms）；③ **数据结构简单**（KV、Hash、List、Set 能表达）；④ **不需要复杂查询**（没有 JOIN、GROUP BY、模糊搜索）。反过来，如果要跑复杂 SQL、要事务强一致、数据量 TB 级、变更频繁，那老实用 MySQL。

## 面试场景 7：本地缓存三巨头 —— HashMap / Guava / Caffeine / Ehcache 怎么选？

🧑‍💻 你

本地缓存框架有一个进化史，面试常见的四个选手：

方案特点是否推荐

`ConcurrentHashMap`
JDK 自带；线程安全；**无淘汰、无过期**，只能自己造轮子
只用于超简单、不会撑爆的场景

Guava Cache
Google 出品；有 LRU 淘汰、过期、加载器；**已被 Caffeine 替代**
老项目还能见，新项目不推荐

**Caffeine**
Guava Cache 作者重写；**W-TinyLFU** 算法命中率更高；异步驱逐；性能比 Guava 快 **5-8 倍**；Spring 5+ 默认本地缓存
**首选**

Ehcache
企业级；支持**持久化到磁盘**、堆外内存、多级缓存；配置复杂；Hibernate 二级缓存标配
需要持久化或和 Hibernate 集成时用

追问 Caffeine 相比 Guava Cache 好在哪？

四个关键改进：① **W-TinyLFU 淘汰算法**（结合 LRU 和 LFU 的优点，用 Count-Min Sketch 记录访问频率，命中率显著高于纯 LRU）；② **异步驱逐**（Guava 是查询时同步做淘汰，会拖慢当前请求；Caffeine 有独立线程做，请求路径更平滑）；③ **更细粒度锁**（分段锁 + CAS，Guava 的锁竞争更多）；④ **基于时间轮的过期**（O(1) 处理过期，Guava 是 O(log n)）。综合下来吞吐提升 5x+，尾延迟更稳。

追问 W-TinyLFU 到底是什么？

**Window-TinyLFU**：把缓存分成两段 —— 小的 *Window Cache (1%)* 用 LRU 接收新数据（避免突发流量把热数据挤掉），大的 *Main Cache (99%)* 用 SLRU + TinyLFU。*TinyLFU* 用 **Count-Min Sketch** 这种概率数据结构（类似 Bloom Filter 记频次）以极小内存追踪访问频率。淘汰时新旧候选打擂台，赢家留下。相比 LRU 在扫描型 workload 下命中率能高 20-40%。

## 面试场景 8：缓存的三大用途

🧑‍💻 你

面试官如果让你抽象一下缓存的价值，三条：

1. **加速读**：热点数据挡在 DB 前，把 P99 从几十毫秒压到亚毫秒。这是最直接的收益。

2. **降低 DB 压力**：命中缓存的请求不到 DB。假设命中率 95%，MySQL 的负载能直接降到 1/20。这是*抗流量*的核心手段。

3. **解耦系统**：缓存作为中间层，可以隔离前后端节奏差异 —— 前端 QPS 突增时 Redis 顶住，异步刷回 DB；也能作为多个服务之间的共享数据源（Session、限流计数）。

追问 为什么说缓存能「削峰填谷」？

抢购/秒杀场景，前端瞬间几十万请求打进来。如果直接查 DB，MySQL 连接池秒炸。用 Redis 做「库存扣减 + 结果缓存」，可以扛住瞬时高峰；真正下单的用户异步入 DB。*缓存把「同步的高峰」变成了「异步的平稳流」*—— 这就是削峰。反过来，低峰时把缓存预热好，也能填补 DB 的空闲期。

## 面试场景 9：缓存的三大挑战（下一课伏笔）

🧑‍💻 你

缓存不是白吃的午餐，用得越深越会遇到三类问题：

1. **数据一致性**：DB 改了，缓存里的旧值怎么办？—— *Cache Aside / Read Through / Write Through / Write Behind* 四种模式，每种都有各自的一致性权衡。**0053 课细讲**。

2. **缓存三兄弟**：

- *缓存穿透*：查一个 DB 里都没有的 key，缓存永远 miss，请求全打到 DB。

- *缓存击穿*：某个热点 key 突然过期，瞬间大量并发查 DB。

- *缓存雪崩*：大量 key 同时过期（或 Redis 挂了），DB 被压垮。

**0056 课细讲**解法（布隆过滤器 / 互斥锁 / TTL 打散 / 熔断降级）。

3. **缓存高可用**：Redis 单点挂了业务停摆。—— *主从复制 + Sentinel 哨兵 + Cluster 集群*。**0059 课细讲**。

这三个问题是 Redis 面试的*深水区*。本课先埋种子，让你带着问题往下学。

追问 数据一致性问题为什么这么难解？

因为你要维护两份数据（DB + Cache）在异步环境下的一致 —— 而分布式系统的第一定律是「不可能同时保证一致性、可用性、分区容错性」（CAP）。任何双写方案都会在某个时序下出现不一致：先删缓存再改 DB？中间 miss 会读到旧值。先改 DB 再删缓存？删失败缓存脏了。加分布式锁？性能爆炸。所以工业界普遍接受**「最终一致」** —— 通过短 TTL、订阅 binlog、双删等手段收敛不一致的窗口。追求强一致就别用缓存。

## 面试场景 10：实际项目里 Redis 用来做什么？

🎤 面试官

你项目里 Redis 除了缓存还做过什么？

🧑‍💻 你

Redis 在生产项目里典型的 8 个场景，每个背后都有对应的数据结构：

场景数据结构典型 API

Session 存储String / Hash`SET session:xxx {...} EX 1800`
限流（令牌桶/固定窗口）String + INCR / Lua`INCR + EXPIRE` 或 Redisson RateLimiter
分布式锁String`SET key val NX EX 30`（0057-0058 课）
排行榜（Top N）ZSet`ZADD / ZREVRANGE`
点赞 / 计数String / Hash`INCR post:123:likes`
消息队列List / Stream`LPUSH / BRPOP` 或 `XADD / XREAD`
附近的人Geo`GEOADD / GEOSEARCH`
验证码 / 短链String + TTL`SET code:phone xxx EX 300`
UV 统计HyperLogLog`PFADD / PFCOUNT`
签到 / 布隆过滤器Bitmap / RedisBloom`SETBIT / GETBIT`

追问 面试时怎么把 Redis 用途说得有层次？

推荐用*「三层结构」*作答：**① 基础层（缓存加速）**——「读多写少的数据挡在 DB 前」；**② 数据结构层（业务能力）**——「利用 ZSet 做排行、Bitmap 做签到、Geo 做附近」；**③ 协调层（分布式基础设施）**——「Redis 天然的单线程 + 原子性，很适合做分布式锁、限流、幂等控制」。三层依次讲出，面试官会觉得你不是「只会 SET/GET」的水货。

## 💻 代码验证（跑一遍就懂）

### 验证 1：redis-cli 基本命令 —— 感受一下 Redis

```
# 启动 Redis（Docker 一键）
$ docker run -d --name redis -p 6379:6379 redis:7-alpine

# 进入客户端
$ docker exec -it redis redis-cli

# String —— 最基础的 KV
127.0.0.1:6379> SET user:1001 "Alice"
OK
127.0.0.1:6379> GET user:1001
"Alice"
127.0.0.1:6379> SET code:phone "8964" EX 300     # 5 分钟过期
OK
127.0.0.1:6379> TTL code:phone
(integer) 300

# INCR —— 原子自增（点赞、计数、限流）
127.0.0.1:6379> INCR post:123:likes
(integer) 1
127.0.0.1:6379> INCR post:123:likes
(integer) 2

# Hash —— 存对象
127.0.0.1:6379> HSET user:1001 name "Alice" age 28
(integer) 2
127.0.0.1:6379> HGETALL user:1001
1) "name"
2) "Alice"
3) "age"
4) "28"
```

### 验证 2：ZSet 排行榜 —— Redis 秒杀 MySQL 的场景

```
# 游戏排行榜：玩家分数排序
127.0.0.1:6379> ZADD leaderboard 100 "player:A"
(integer) 1
127.0.0.1:6379> ZADD leaderboard 200 "player:B"
(integer) 1
127.0.0.1:6379> ZADD leaderboard 150 "player:C"
(integer) 1

# 查 Top 3（从高到低）
127.0.0.1:6379> ZREVRANGE leaderboard 0 2 WITHSCORES
1) "player:B"
2) "200"
3) "player:C"
4) "150"
5) "player:A"
6) "100"

# 查某玩家排名
127.0.0.1:6379> ZREVRANK leaderboard "player:A"
(integer) 2

# 加分（点赞、金币）
127.0.0.1:6379> ZINCRBY leaderboard 50 "player:A"
"150"
```

对比 MySQL 做同样的事：要维护一张 `ORDER BY score DESC LIMIT 3`，每次改分数都得重排；Redis 底层是**跳表**，插入和排名查询都是 O(log n)，天然为排序服务。

### 验证 3：验证 Redis 单线程 —— 观察 KEYS * 的阻塞

```
# 造 100 万个 key
127.0.0.1:6379> DEBUG POPULATE 1000000
OK
(1.86s)

# 危险命令：全库扫描
127.0.0.1:6379> KEYS *
# ← 这里 Redis 主线程完全阻塞，
#   其它客户端的所有请求都会排队等
#   1000000 条 key 打印，耗时数秒

# 安全做法：用 SCAN 分批
127.0.0.1:6379> SCAN 0 COUNT 100
1) "1245184"          ← 下次游标
2) 1) "key:12345"
2) "key:67890"
...
# 每次 O(1)，主线程不阻塞
```

陷阱 生产环境 **永远不要执行 `KEYS *`**。运维禁令的第一条。要遍历 key，用 `SCAN`；要删大 key，用 `UNLINK`；要看 key 总数，用 `DBSIZE`（O(1) 直接读元数据）。这几个命令是 SRE 面试的高频加分点。

### 验证 4：Spring Boot 集成 Redis（Spring Data Redis）

```
// pom.xml
<dependency>
<groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>

// application.yml
spring:
data:
redis:
host: localhost
port: 6379
lettuce:
pool:
max-active: 8
max-idle: 8
min-idle: 0

// 使用
@Service
public class UserService {
@Autowired
private StringRedisTemplate redis;

public User getUser(Long id) {
String key = "user:" + id;
String cached = redis.opsForValue().get(key);
if (cached != null) {
return JSON.parseObject(cached, User.class);  // 命中
}
User user = userMapper.selectById(id);            // 回源 DB
if (user != null) {
redis.opsForValue().set(key, JSON.toJSONString(user),
Duration.ofMinutes(30));                  // 回写缓存
}
return user;
}
}
```

这就是最经典的 **Cache Aside 模式**—— 「先查缓存，miss 就查 DB 并回写」。下节课 0053 会展开四种缓存读写模式的取舍。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话解释「本地缓存」和「分布式缓存」最本质的区别。</summary>

本地缓存在**进程内**，无网络开销但**多实例不共享**；分布式缓存是**独立服务**，有网络往返但**多实例共享一份数据**。生产常用两级缓存 —— 本地兜命中率，Redis 兜一致性。

</details>

<details>

<summary>Q2 Redis 为什么这么快？请说出 4 条。</summary>

① **纯内存操作**（比磁盘快 5-6 个数量级）；② **单线程避免锁竞争和上下文切换**；③ **IO 多路复用**（epoll，一个线程管万级连接）；④ **高效数据结构**（SDS、跳表、ziplist、listpack、quicklist）。

</details>

<details>

<summary>Q3 Redis 6 引入的多线程是不是让命令执行也变多线程了？</summary>

不是。Redis 6 只让**网络 IO（读 socket、协议解析、写 socket）**多线程，**命令执行仍是主线程单线程**。这样既解决了单线程 socket 瓶颈，又保留了命令天然原子性和无锁数据结构。

</details>

<details>

<summary>Q4 Redis vs Memcached，请说出至少 4 个区别。</summary>

① **数据结构**：Redis 有 String/Hash/List/Set/ZSet 等十几种，Memcached 只 KV；② **持久化**：Redis 有 RDB/AOF，Memcached 无；③ **集群**：Redis Cluster 原生，Memcached 靠客户端一致性哈希；④ **事务**：Redis 有 MULTI/EXEC 和 Lua 脚本，Memcached 无；⑤ **发布订阅**：Redis 有，Memcached 无。

</details>

<details>

<summary>Q5 项目里 Redis 除了做缓存，你还用它做过什么？至少举 5 个场景并说出对应数据结构。</summary>

① **Session 存储**（String / Hash + TTL）；② **分布式锁**（`SET NX EX`）；③ **排行榜**（ZSet）；④ **限流**（INCR + EXPIRE 或 Redisson RateLimiter）；⑤ **点赞计数**（INCR）；⑥ **消息队列**（List/Stream）；⑦ **UV 统计**（HyperLogLog）；⑧ **签到**（Bitmap）；⑨ **附近的人**（Geo）；⑩ **验证码**（String + TTL）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Redis 官方文档 · Reference —— 命令、数据结构、协议规范

- Caffeine Wiki · W-TinyLFU Efficiency —— 淘汰算法命中率对比

- Memcached 官网 —— 用来对比参考

#### 🔗 关联课件

-  —— 上一课

-  —— 下一课

-  —— 本课「三大挑战」的细讲

-  —— 本课「高可用」的细讲

#### 🧭 下一课预告

Lesson 0052：**Redis 五种基础数据类型 —— String / Hash / List / Set / ZSet**。会深入到每种类型的*底层编码（SDS / ziplist / listpack / quicklist / skiplist）*、*典型业务场景*和*常见误用陷阱*。为后面的持久化、缓存挑战、集群打好数据结构地基。

💬 有任何疑问 —— 「Redis 6 的多线程默认为什么关闭？」「Caffeine 的 maximumSize 应该设多大？」「面试被问『你们线上 QPS 多少』我不敢乱答怎么办？」—— 直接问我。阶段七的每一课都可以随时回来加深。


