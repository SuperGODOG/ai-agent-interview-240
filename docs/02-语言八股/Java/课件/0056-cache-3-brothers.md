> Lesson 0056 · 阶段七 · Redis · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 5 段可跑代码 · 5 道自测 · 9 个高频追问 · 3 个陷阱

# 0056 · 缓存三兄弟 & 3 种缓存读写策略

如果说 Redis 面试的**第一硬骨头**是持久化（RDB / AOF / 混合），那 **第二硬骨头** 就是这一课的两大板块 —— **缓存三兄弟**（穿透 / 击穿 / 雪崩）和 **3 种缓存读写策略**（Cache Aside / Read-Write Through / Write Behind）。这两块几乎是每一场 Java 后端面试的必点菜：*能把三兄弟每个的成因和对应方案说清楚，就能过关；能进一步谈 Cache Aside 的顺序陷阱、延迟双删、Canal 兜底*，就是加分项。

本课不背概念，而是从**面试现场**倒推 —— 面试官会怎么串问，你要怎么给出「场景 → 成因 → 方案 → 边界」的四段式回答。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 缓存穿透和缓存击穿有什么区别？一句话说清。</summary>

**穿透**：查询的数据*压根不存在*（缓存和 DB 都没有），每一次都打穿到 DB。**击穿**：数据*DB 里有但缓存刚过期*，热 key 过期那一瞬间大量请求穿透打 DB。区别关键在「DB 有没有这条数据」。第 1、2、3 场景细讲。

</details>

<details>

<summary>Q0.2 Cache Aside 模式的写操作，为什么是「先更新 DB 再删缓存」而不是「先删缓存再更新 DB」？</summary>

如果先删缓存再更新 DB：并发下 A 删了缓存 → B 读缓存 miss → B 读 DB 拿到旧值 → B 把旧值写回缓存 → A 才更新 DB —— 结果*缓存里永久是旧值*。而先更新 DB 再删缓存，最坏情况下不一致窗口是毫秒级，且下一次读 miss 就会从新 DB 回源修正。第 6 场景细讲。

</details>

## 面试场景 1：缓存三兄弟一张表讲清楚 ★核心

🎤 面试官

缓存穿透、缓存击穿、缓存雪崩，先用一张表把三者的区别和成因给我讲清楚。

🧑‍💻 你

三者常被放一起考，但成因完全不同。核心区分维度就一句话：*「请求的 key，缓存里没有；那 DB 里有没有？规模是一个还是一批？」*

维度穿透 Penetration击穿 Breakdown雪崩 Avalanche

数据在 DB 里？**不存在**存在存在
数据在缓存里？不存在刚*过期*了大量 key 刚*同时过期*，或 Redis 宕机
影响 key 规模零散或大量（黑客可构造无穷）单个热 key大量 key 或全部
典型触发黑客用负数 id / 不存在的 id 恶意刷秒杀商品缓存到点失效批量商品全设 30min 过期；Redis 宕机
后果每次都打 DB，缓存*形同虚设*那一瞬间 DB QPS 暴涨可能被打挂DB 直接被打挂，可能雪崩到整个链路
核心方案布隆过滤器 / 缓存空值 / 参数校验互斥锁 / 逻辑过期 / 永不过期过期时间加随机 / 高可用集群 / 多级缓存 / 限流降级

追问 三兄弟里，哪一个最容易被面试官继续追问细节？

**缓存穿透**被追问的频率最高，因为它牵出*布隆过滤器*这个数据结构，考官会顺着问位数组、哈希函数、误判率、扩容、能不能删除元素。**Cache Aside 的一致性**是第二热点。**雪崩**相对简单一点，但会跟高可用、限流降级、Sentinel 关联起来。

## 面试场景 2：缓存穿透 —— 成因与解决方案

🎤 面试官

如果我恶意构造一堆 `id = -1`、`id = 999999999` 这种绝对不存在的请求疯狂打你的接口，怎么防？

🧑‍💻 你

这就是典型的缓存穿透。攻击流程：请求 → 查 Redis miss → 查 MySQL 也 miss → 结果*没有任何东西可以缓存下来* → 下次同样的 key 还是全打到 DB。我会分四层来防：

1. **参数校验（第一道墙）**：接口层判掉明显非法的入参 —— `id <= 0`、超长字符串、格式不合规 —— 直接 400 拒了，根本进不到查缓存这一步。

2. **缓存空值（简单粗暴但有效）**：查 DB 也 miss 时，往 Redis 里塞一个 `null` 占位符，**加较短 TTL（5-10 分钟）**。下次同 key 请求直接命中「已知不存在」，不打 DB。

3. **布隆过滤器（工业级方案）**：把*所有存在的 key*预加载进 BloomFilter，请求先经过它 —— 判断「一定不存在」直接拒；「可能存在」再走缓存/DB。判存在有误判但判不存在*绝无漏判*，正好符合我们只想拦「不存在」的诉求。

4. **接口限流**：按 IP / userId 做限流，异常访问 pattern（比如 1 秒内构造 100 个不同 id）直接拉黑名单。这是最后一道兜底。

陷阱 **缓存空值方案的两个副作用**：

1. *Redis 内存被无用 null 占满* —— 如果攻击者每次用不同 key（`id = -1, -2, -3...`），你的 Redis 会存一堆没意义的 null。TTL 一定要短。

2. *短时间内新增数据看不到* —— 假设商品 id=100 刚才不存在，你缓存了 null 5 分钟；结果运营 1 分钟后真的创建了这条商品，用户 5 分钟内一直看不到。所以「写路径」也要能主动删除这个 null。

追问 布隆过滤器有什么缺点？

四个：
**①有误判率**（判「存在」可能其实不存在，但判「不存在」100% 正确 —— 幸好我们用它挡穿透正好只关心「不存在」）；
**②不能删除元素**（一个位可能被多个元素共同置 1，删了会误伤 —— 变体 *Counting Bloom Filter* 用计数代替 0/1 才能删）；
**③需要预热填充**（服务启动时得把 DB 里所有合法 key 灌进去，量大时初始化慢）；
**④扩容成本高**（位数组长度固定，超容后误判率飙升，要 rehash 整个过滤器）。生产上常用 *RedisBloom 模块*，能持久化能扩容能限制误判率。

追问 布隆过滤器的误判率怎么算？我要 100 万 key、误判率 1% 需要多少空间？

公式：位数组长度 `m ≈ -n·ln(p) / (ln2)²`，哈希函数个数 `k ≈ (m/n)·ln2`。代入 *n=1,000,000, p=0.01*：`m ≈ 9,585,058 bit ≈ 1.14 MB`，`k ≈ 7` 个哈希函数。可以看到 **100 万元素只要 1MB 左右**，比缓存空值那种 O(n) 存 null 省得多。这就是为什么工业上宁可复杂也用 BloomFilter。

## 面试场景 3：缓存击穿 —— 热 key 过期那一瞬

🎤 面试官

秒杀活动的商品详情页，缓存 30 分钟过期。到点那一瞬间几十万请求同时打进来，怎么办？

🧑‍💻 你

这是缓存击穿的经典场景 —— 只有**一个热 key**过期，几十万请求发现 Redis miss，几十万个线程*同时*去查 MySQL，DB 直接被打挂。三种解法从简单到进阶：

1. **互斥锁（Mutex Lock）★ 面试首推**：miss 时先用 `SET lock_key uuid EX 30 NX` 抢锁。抢到的那一个线程去查 DB、写缓存、释放锁；没抢到的*短暂 sleep + 重试读缓存*，或直接返回降级值。全局只有 1 个线程打 DB。

2. **逻辑过期（Logical Expiration）**：缓存*物理永不过期*，但 value 里存一个 `expireAt` 字段。读的时候比较：没到期直接返回；到期了返回旧值 + 用异步线程去刷新缓存。**请求永不阻塞**，代价是可能读到「刚过期但还没刷新」的旧值 —— 秒杀这种一致性容忍度低的不适合，商品详情 / 排行榜合适。

3. **热点 key 永不过期**：业务允许的话最省事。秒杀期间锁定不过期，活动结束后手动删除或缓慢淘汰。

追问 击穿方案里的互斥锁，怎么用 Redis 实现？释放锁要注意什么？

加锁：`SET lock:sku:100 <uuid> EX 30 NX` —— *NX 保证只有一个线程能设成功*，EX 兜底防止持锁线程崩溃死锁。释放锁必须用 **Lua 脚本原子判断**：先看 value 是不是自己的 uuid，是才 DEL。否则可能出现「A 的锁超时被 B 拿到 → A 完成后误删 B 的锁」这种典型 bug。*更工业级的方案是用 Redisson 的 RLock，它自带 uuid 判断、可重入、看门狗自动续期*。

追问 逻辑过期方案里的「异步刷新」，怎么保证只有一个线程去刷？

刷新前再抢一次互斥锁 `SETNX refresh:sku:100` —— 抢到的线程提交给线程池去异步刷新缓存，没抢到的直接返回旧值。*这个方案本质是把「击穿方案 1 互斥锁」的锁范围从「所有请求」缩到「刷新任务」*，请求永远拿旧值不阻塞，用户体验最好。

## 面试场景 4：缓存雪崩 —— 大面积同时失效

🎤 面试官

你们运营把 1 万个商品缓存全设了 30 分钟 TTL，30 分钟后*集体过期*，DB 瞬间被打挂。这叫什么问题，怎么防？

🧑‍💻 你

典型缓存雪崩。雪崩有两大成因，方案也分两条线：

**成因 A：大量 key 同时过期**

- **过期时间加随机值（最简单最有效）**：`ttl = baseTtl + random(0, 300)`，把 1 万个 key 的过期时间散在 30-35 分钟之间，不会瞬间集体失效。*一行代码解决 90% 的雪崩*。

- **缓存预热**：低峰期把即将过期的热点 key 提前重新加载。

- **永不过期 + 后台异步更新**：跟击穿方案 3 类似。

**成因 B：Redis 集群整个宕机**

- **Redis 高可用架构**：*Sentinel 哨兵*做主从切换，或用 *Redis Cluster* 分片 + 副本，避免单点故障。这是从根上防雪崩。

- **本地缓存兜底（多级缓存）**：Redis 挂了还有 *Caffeine / Guava Cache* 在应用本地扛一层。虽然容量小、有副本不一致，但能救命。

- **限流 + 降级 + 熔断**：Redis 挂时用 *Sentinel / Resilience4j* 限制打到 DB 的 QPS，超限直接降级返回默认值或错误。**保 DB 不死是底线**。

陷阱 雪崩和击穿的界限：*雪崩是一批 key，击穿是单个 key*。有些教材把「Redis 宕机导致所有 key 失效」也归到雪崩，理解为「广义的缓存整体不可用」；但如果只是*一个*热 key 集中过期打 DB，那就是击穿。面试时说清楚成因即可，别纠结定义边界。

追问 本地缓存 + Redis 两级方案，怎么处理不同节点本地缓存的不一致？

有两种打法：**①短 TTL 容忍** —— 本地缓存设 30 秒左右，接受短时间不一致，读性能最高；**②消息广播** —— 用 Redis Pub/Sub 或 MQ 通知所有节点删除本地缓存条目，一致性更好但复杂度上升。*大部分业务用短 TTL 就够了，只有对一致性有要求的配置类数据才用广播*。

## 面试场景 5：Cache Aside Pattern —— 3 种策略里最常用

🎤 面试官

说说你项目里缓存是怎么读怎么写的？

🧑‍💻 你

我们用的是最常见的 **Cache Aside Pattern（旁路缓存）**，读写流程都由*应用层*控制：

```
┌───────── 读流程 ─────────┐
│ 1. 先读 Redis            │
│ 2. HIT  → 直接返回        │
│ 3. MISS → 读 MySQL        │
│         → 写回 Redis      │
│         → 返回            │
└──────────────────────────┘

┌───────── 写流程 ─────────┐
│ 1. 先更新 MySQL          │
│ 2. 再删除 Redis 中该 key  │
└──────────────────────────┘
```

关键词是**「先 DB 后删缓存」+「删除不更新」**。生产 99% 的场景用它就够。

追问 Cache Aside 有哪些缺陷？

三个：**①首次请求必 miss**（可以做缓存预热缓解）；**②频繁删除会降低命中率**（写多的场景不适合，可以加短 TTL + 不删只更新，但要接受一致性风险）；**③强一致场景不适用**（存在毫秒级窗口，需要 Canal 或延迟双删补丁，见场景 10）。

## 面试场景 6：Cache Aside 为什么先 DB 再删缓存？★ 经典

🎤 面试官

为什么写操作是「先更 DB 再删缓存」？先删缓存再更 DB 不行吗？画一下并发时序。

🧑‍💻 你

**「先删缓存再更 DB」的翻车时序**：

```
时间线   写请求 A                读请求 B
t1     删除缓存 (cache=null)
t2                              读缓存 miss
t3                              读 DB → 旧值 V1
t4                              把 V1 写回缓存
t5     更新 DB → 新值 V2
------------------------------------------
最终:  DB = V2, 缓存 = V1 ← 永久不一致！只能等 TTL 到期才修复。
```

**「先更 DB 再删缓存」的最坏时序**：

```
时间线   写请求 A                读请求 B
t1                              读缓存 miss (刚好过期)
t2                              读 DB → 旧值 V1
t3     更新 DB → 新值 V2
t4     删除缓存
t5                              把 V1 写回缓存
------------------------------------------
最终:  DB = V2, 缓存 = V1 ← 也不一致，但……
```

这种「先 DB 后删」的翻车需要满足*非常苛刻的条件*：读请求刚好在 t1 miss、且读 DB 的耗时长于「写 DB + 删缓存」的耗时。**概率极低，且下次读 miss 就能自愈**。而「先删后更 DB」翻车条件宽松、后果永久，这就是选择「先 DB 后删」的根本原因。

追问 「先更新 DB 再删缓存」的短暂不一致窗口能接受吗？

多数业务能。窗口是*毫秒级*，加上缓存本身有 TTL 兜底，一般 5-30 分钟内自动纠正。**金融、库存、订单**这些强一致场景不能接受，得配合 *Canal 订阅 MySQL binlog 异步删缓存*，或直接用*本地事务表 + 消息队列*做两次删除。见场景 10。

## 面试场景 7：Cache Aside 为什么是「删除」缓存而不是「更新」缓存？

🎤 面试官

写的时候直接把新值更新到缓存不是更快？为什么非要删掉让下次读再回源？

🧑‍💻 你

三个理由，按优先级排序：

1. **懒加载原则**：这个 key 如果没人读，更新它就是白干。特别是那种「更新一次要 join 几张表才能算出缓存值」的场景 —— 每次写都算一遍太浪费。删掉，等有人真读了再计算。

2. **并发一致性**：并发更新缓存*顺序可能错乱*。假设 A、B 两个写请求：A 先更 DB 到 V1，B 后更 DB 到 V2；但网络抖动导致 B 先更缓存到 V2、A 后更缓存到 V1 —— 结果缓存是 V1，DB 是 V2，*永久不一致*。**删除操作是幂等的**，两次删除的结果一样，没这个问题。

3. **写性能**：删除比更新轻，尤其是复杂对象。删就是 `DEL key`，更新可能要序列化/反序列化整个大 JSON。

陷阱 有面试官会问「那我加分布式锁串行化写不就行了？」——*能行，但代价太大*。加锁把并发写变成串行，QPS 掉到几百；而 Cache Aside 「删除」方案下并发依然存在，翻车概率极低。**用简单方案解决 99% 场景，是工程判断**。

## 面试场景 8：Read/Write Through Pattern

🎤 面试官

除了 Cache Aside，还有哪些缓存读写策略？

🧑‍💻 你

还有 **Read Through / Write Through**（读写穿透）。核心区别：*Cache Aside 里应用层同时和缓存 + DB 打交道；Read/Write Through 里应用只跟缓存打交道，缓存组件自己去同步 DB*。

```
Cache Aside:                Read/Write Through:
┌──App──┐                    ┌──App──┐
│       │                    │       │
├──R/W──┤                    ├──R/W──┤
▼       ▼                    ▼
Cache    DB                  Cache ──── DB
(缓存组件负责同步)
```

- **Read Through**：读缓存 miss 时，*缓存组件*去查 DB 并回填，对应用透明。

- **Write Through**：写请求由缓存组件同步写 DB + 写缓存，都成功才返回。

- **优点**：应用代码简单，读写逻辑都封装在缓存层。

- **缺点**：需要重型缓存组件支持（比如 Guava `LoadingCache`、Caffeine `LoadingCache`、EhCache），Redis 本身不支持这种模式 —— 要么应用层自己封装一层，要么用*本地缓存*。所以国内 Java 项目主流还是 Cache Aside。

追问 Read Through 和 Cache Aside 的读流程唯一区别是什么？

「回填缓存」这一步的*责任方*不同。Cache Aside 是应用代码显式 `cache.put(key, value)`；Read Through 是缓存组件在 miss 时自动调用*预先注册的 CacheLoader*去 DB 拿数据。写流程的区别是 Write Through 由缓存组件同步双写、Cache Aside 由应用层控制先后。

## 面试场景 9：Write Behind Pattern（写回 / 异步写入）

🎤 面试官

说说 Write Behind 模式。什么场景会用？

🧑‍💻 你

**写只写缓存，立即返回；由后台异步线程批量、合并地刷回 DB**。写性能*无与伦比*（单机可以到几十万 QPS），代价是：

- **数据可能丢失**：缓存宕机时未刷回的数据全没。

- **不支持强一致**：交易、库存这种钱相关的绝对不能用。

- **实现复杂**：需要队列、合并逻辑、失败重试、宕机恢复。

典型应用场景 —— 其实*比我们想的普遍*：

1. **MySQL InnoDB Buffer Pool**：数据修改先在内存 Buffer Pool 完成 + 写 redo log，异步 checkpoint 刷盘。*数据库自己就是 Write Behind 的信徒*。

2. **操作系统 Page Cache**：`write()` 只写到 page cache 就返回，`fsync()` 才真落盘。

3. **高频计数**：文章浏览量、点赞数、播放量 —— 每次都写 DB 太贵，用 Redis 计数，1 分钟批量刷一次。

4. **日志埋点**：先写内存/本地文件，异步批量上报。

追问 3 种策略对比总结？

见下表。

策略读流程写流程一致性写性能典型场景

**Cache Aside**App 读 Cache→miss 读 DB→回填App 更新 DB→删除 Cache最终一致（毫秒窗口）中★ 通用业务（99% 场景）
**Read/Write Through**Cache 自己 miss 时查 DBCache 组件同步双写强一致（同步双写）低（双写等待）本地缓存 Caffeine / Guava
**Write Behind**同上只写 Cache 立即返回，异步刷 DB弱一致（可能丢数据）★ 极高InnoDB Buffer Pool、计数器

## 面试场景 10：Cache Aside 的极端一致性 —— 延迟双删 & Canal ★ 进阶

🎤 面试官

你说 Cache Aside 有毫秒级不一致窗口，如果我的业务不能接受这个窗口，怎么办？

🧑‍💻 你

三个进阶方案，工业界都在用：

**方案 A：延迟双删**

```
1. 删缓存
2. 更新 DB
3. sleep(500ms)   ← 关键
4. 再删一次缓存
```

解决什么问题？—— 场景 6 提到的「读请求在删缓存前就 miss 并读了旧值，写完成后才把旧值写回」。第二次删除会把这个「后写入的旧值」再抹掉。sleep 时长要*略大于「一次读 DB + 写缓存」的耗时*，通常 500ms-1s。生产上更常用*延迟消息队列*（RocketMQ 延时消息、Redis ZSET 定时任务）做第二次删除，别真在业务线程里 sleep 阻塞。

**方案 B：Canal 订阅 MySQL binlog**

```
App → 只更新 MySQL
↓ (写 binlog)
Canal 伪装 Slave 订阅 binlog
↓
解析 binlog 事件 → 发 MQ / 直接删 Redis
```

这是*业内最优雅的方案*：应用层完全不用管缓存，只更新 DB；Canal 保证「DB 变更后一定会有 delete cache 事件」。缺点是*引入外部组件、部署复杂*，适合大流量强一致场景（电商库存、账户余额）。

**方案 C：本地事务消息表 + 重试**

更新 DB 时在同一事务里写一条「待删缓存」记录到 `t_cache_delete` 表，事务提交后由消费者读取表 → 删缓存 → 成功后删除记录。失败可以重试。*用事务保证「DB 更新」和「删缓存意图」的原子性*。

追问 Canal 方案有没有缺点？是不是能保证 100% 一致？

缺点：**①部署复杂度上升**（要维护 Canal 集群 + Zookeeper）；**②主从延迟**（Canal 是伪 Slave，MySQL 主从复制延迟会传递给它）；**③消息队列不保证顺序**（同一个 key 的多次更新，如果分到不同 partition，可能乱序删缓存 —— 需要按 key hash 到同一 partition）。所以 Canal 保证的是*最终一致 + 更短的窗口*（秒级 → 毫秒级），仍非 100%。小系统别上 Canal，直接 *Cache Aside + 短 TTL 兜底*就够。

追问 「先更新 DB 再删缓存」也有短暂不一致，业务真的能接受吗？

多数业务能。**毫秒级窗口 + 天然收敛**：下一次读 miss 就会从新 DB 回源修正；而且 Redis 通常有 5-30 分钟 TTL 兜底。*钱相关的强一致场景*（订单支付、库存扣减、账户余额）不能接受 —— 上 Canal 或本地事务表。*非钱业务*（商品详情、用户资料、评论列表）延迟几百毫秒不影响业务，绝大多数团队默认 Cache Aside 就交付。

## 💻 代码验证（打开 IDE + Redis 跑一遍）

### 代码 1：Cache Aside 读写模板（Spring Data Redis）

```
@Service
public class ProductService {

@Autowired private ProductMapper productMapper;
@Autowired private StringRedisTemplate redis;

private static final String KEY_PREFIX = "product:";
private static final Duration TTL = Duration.ofMinutes(30);

// 读：Cache Aside
public Product getById(Long id) {
String key = KEY_PREFIX + id;
String cached = redis.opsForValue().get(key);
if (cached != null) {
return JSON.parseObject(cached, Product.class);   // HIT
}
// MISS → 回源
Product p = productMapper.selectById(id);
if (p != null) {
redis.opsForValue().set(key, JSON.toJSONString(p), TTL);
}
return p;
}

// 写：先 DB 后删缓存
@Transactional
public void update(Product p) {
productMapper.updateById(p);           // 1. 先更 DB
redis.delete(KEY_PREFIX + p.getId());  // 2. 再删缓存
}
}
```

### 代码 2：缓存穿透 —— 缓存空值 + 布隆过滤器双保险

```
@Autowired private RBloomFilter<Long> productBloom;   // Redisson 布隆过滤器

public Product getByIdSafe(Long id) {
// 1. 参数校验
if (id == null || id <= 0) return null;

// 2. 布隆过滤器：一定不存在直接拒
if (!productBloom.contains(id)) return null;

String key = KEY_PREFIX + id;
String cached = redis.opsForValue().get(key);
if (cached != null) {
// 3. 缓存空值：命中 "NULL" 占位符也直接返回
return "NULL".equals(cached) ? null : JSON.parseObject(cached, Product.class);
}

Product p = productMapper.selectById(id);
if (p == null) {
// 4. DB 也 miss → 写入短 TTL 的空值防穿透
redis.opsForValue().set(key, "NULL", Duration.ofMinutes(5));
return null;
}
redis.opsForValue().set(key, JSON.toJSONString(p), TTL);
return p;
}

// 服务启动时预热布隆过滤器
@PostConstruct
public void initBloom() {
productBloom = redisson.getBloomFilter("productIds");
productBloom.tryInit(1_000_000L, 0.01);          // 100 万 key、误判率 1%
productMapper.selectAllIds().forEach(productBloom::add);
}
```

### 代码 3：缓存击穿 —— Redis 互斥锁

```
public Product getByIdWithMutex(Long id) {
String key = KEY_PREFIX + id;
String cached = redis.opsForValue().get(key);
if (cached != null) return JSON.parseObject(cached, Product.class);

// MISS → 尝试抢锁
String lockKey = "lock:" + key;
String uuid = UUID.randomUUID().toString();
Boolean got = redis.opsForValue().setIfAbsent(lockKey, uuid, Duration.ofSeconds(10));

if (Boolean.TRUE.equals(got)) {
try {
// 双检：可能已被别的线程加载好
cached = redis.opsForValue().get(key);
if (cached != null) return JSON.parseObject(cached, Product.class);

Product p = productMapper.selectById(id);
redis.opsForValue().set(key, JSON.toJSONString(p), TTL);
return p;
} finally {
// Lua 脚本原子释放锁 —— 防止误删别人的锁
String script = "if redis.call('get', KEYS[1]) == ARGV[1] " +
"then return redis.call('del', KEYS[1]) else return 0 end";
redis.execute(new DefaultRedisScript<>(script, Long.class),
Collections.singletonList(lockKey), uuid);
}
} else {
// 没抢到锁 → 短暂等待后重试读缓存
try { Thread.sleep(50); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
return getByIdWithMutex(id);
}
}
```

### 代码 4：缓存雪崩 —— 过期时间加随机值

```
import java.util.concurrent.ThreadLocalRandom;

public void setWithJitter(String key, Object value) {
long baseSeconds = 30 * 60;                                     // 30 分钟基准
long jitter = ThreadLocalRandom.current().nextLong(0, 5 * 60);  // 0-5 分钟抖动
redis.opsForValue().set(key, JSON.toJSONString(value),
Duration.ofSeconds(baseSeconds + jitter));
}

// 效果：1 万个 key 的过期时间打散在 30-35 分钟，永远不会「同一秒集体过期」
```

### 代码 5：延迟双删（用 Spring 异步 + 延迟队列）

```
@Autowired private DelayQueue<DelayedTask> delayQueue;
@Autowired private ScheduledExecutorService scheduler;

@Transactional
public void updateWithDoubleDelete(Product p) {
String key = KEY_PREFIX + p.getId();
redis.delete(key);                        // 1. 先删缓存
productMapper.updateById(p);              // 2. 更新 DB

// 3. 延迟 500ms 再删一次（用调度器，别在业务线程 sleep）
scheduler.schedule(() -> redis.delete(key), 500, TimeUnit.MILLISECONDS);
}

// 生产上推荐用 RocketMQ 延时消息或 Redis ZSET 定时任务，
// 避免应用重启导致延时任务丢失。
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一张三行表区分缓存穿透 / 击穿 / 雪崩：DB 里是否存在、影响的 key 规模、核心方案。</summary>

**穿透**：DB 里不存在 · 单个或大量 · 布隆过滤器 + 缓存空值 + 参数校验。

**击穿**：DB 里存在但缓存刚过期 · 单个热 key · 互斥锁 + 逻辑过期 + 永不过期。

**雪崩**：DB 里存在但大量 key 同时过期或 Redis 宕机 · 大面积 · 过期时间加随机 + 高可用集群 + 多级缓存 + 限流降级。

</details>

<details>

<summary>Q2 为什么布隆过滤器能防缓存穿透而不用担心误判？</summary>

因为它*判「不存在」100% 准确、判「存在」才可能误判*。而防穿透的诉求恰好是「拦截一定不存在的 key」—— 判「不存在」时直接拒，正好对上。误判为「存在」的少量请求会走到缓存/DB，也不会有正确性问题，只是没被拦掉而已。

</details>

<details>

<summary>Q3 Cache Aside 写操作为什么是「先更 DB 再删缓存」而不是「先删缓存再更 DB」？</summary>

先删缓存再更 DB 会有致命时序：A 删缓存 → B 读缓存 miss → B 读到 DB 旧值 → B 写回缓存 → A 更 DB → *缓存永久是旧值*。而先更 DB 再删缓存的翻车条件极苛刻（读请求在写请求之前 miss 且读 DB 慢于写 DB+删缓存），概率极低且下次读能自愈。

</details>

<details>

<summary>Q4 3 种缓存读写策略，哪种性能最高、哪种最常用、哪种最少见？</summary>

写性能最高：**Write Behind**（只写缓存立即返回，异步刷 DB —— MySQL InnoDB Buffer Pool 就是这么干的）。

最常用：**Cache Aside**（应用层控制读写，99% Java 业务的默认选择）。

Redis 场景最少见：**Read/Write Through**（Redis 本身不支持，主要出现在本地缓存 Caffeine / Guava LoadingCache）。

</details>

<details>

<summary>Q5 如果业务要求缓存和 DB 强一致，Cache Aside 的毫秒窗口不能接受，你有哪些工业级方案？</summary>

**①延迟双删**：删缓存 → 更 DB → 延迟 500ms 再删一次（用调度器/延时 MQ，别真 sleep）。

**②Canal 订阅 binlog**：应用只更 DB；Canal 伪装 Slave 消费 binlog → 发 MQ → 消费者删 Redis。*业内最优雅方案*，代价是引入外部组件。

**③本地事务消息表**：更新 DB 时同事务写「待删缓存」记录，消费者读表删缓存 + 失败重试。*用事务保证「更 DB」和「删缓存意图」原子性*。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B（含穿透/击穿/雪崩章节）

- Redis 官方 · Bloom Filter（RedisBloom 模块） —— 生产级布隆过滤器

- Alibaba Canal · MySQL binlog 订阅 —— 强一致方案的核心组件

#### 🔗 关联课件

-  —— 上一课，Redis 面试第一硬骨头

-  —— 下一课

-  —— 集群是防雪崩的根基

-  —— Bitmap 是布隆过滤器的底层

#### 🧭 下一课预告

Lesson 0057：**Redis 内存碎片 & 阻塞排查** —— big key、hot key、慢查询、defrag，生产 Redis 出问题第一时间要看什么。

💬 有任何疑问 —— 「这里为什么这样？」「Redisson 的 RLock 底层怎么实现？」「Canal 的具体部署我不懂」「我们业务应该选延迟双删还是 Canal？」—— 直接问我。我是你的老师，也是你的追问陪练。


