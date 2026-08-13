> Lesson 0057 · 阶段七 · Redis · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0057 · Redis 内存碎片 & 阻塞原因 & 淘汰策略

Redis 是**单线程处理命令**的（IO 多线程是 6.0 才引入的，只做 IO 不做命令执行），所以主线程一旦被阻塞，*所有*客户端都会卡住 —— 一次几百毫秒的 `DEL bigkey` 就足以让下游微服务的超时告警刷屏。与此同时，Redis 在内存里搞了很多小对象，**jemalloc** 的分档分配会让实际物理内存远大于业务数据 —— 内存碎片是运维体感最强、面试最爱问的性能话题之一。

本课把三个高频运维话题打包：**内存碎片、阻塞原因、内存淘汰策略**。这三个话题的共同底色都是「Redis 单线程 + 内存数据库」的物理约束。

本课主要参考 和 ，并补充 Redis 官方文档里的 *maxmemory-policy* 章节。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Redis 有内存碎片吗？如果碎片率是 1.8，业务数据 10GB，物理内存吃了多少？</summary>

有！`mem_fragmentation_ratio = used_memory_rss / used_memory`。碎片率 1.8 意味着物理内存 **18GB**（10GB × 1.8）。碎片主要来自 jemalloc 按 8B/16B/32B 分档分配 + 删除后不主动归还 OS。清理方式：`CONFIG SET activedefrag yes`，或者主从切换后重启副本。第 3 场景细讲。

</details>

<details>

<summary>Q0.2 Redis 有几种内存淘汰策略？默认是哪种？和「过期删除」是一回事吗？</summary>

**8 种**：`noeviction`（默认）、`allkeys-lru`、`allkeys-lfu`、`allkeys-random`、`volatile-lru`、`volatile-lfu`、`volatile-random`、`volatile-ttl`。*不是*一回事：**淘汰策略**是内存到 `maxmemory` 上限后的行为；**过期删除**是「设了 TTL 的 key 到期后怎么删」，用惰性删除 + 定期删除组合。第 9-10 场景细讲。

</details>

## 面试场景 1：什么是 Redis 内存碎片？为什么会产生？⭐核心

🎤 面试官

你线上 Redis 的物理内存用了 20GB，但 `DBSIZE` 显示业务数据只有 12GB —— 剩下的 8GB 去哪了？

🧑‍💻 你

大概率是**内存碎片（memory fragmentation）**。碎片的定义是「已经被内存分配器占用、但业务数据用不到的那部分内存」。产生原因主要有两个：

1. **分配器按档次分配（内因）**：Redis 默认用 **jemalloc**，它把内存切成固定档次（8B、16B、32B、48B、64B、96B、128B …）。业务申请 17 字节，jemalloc 会给 32 字节，*浪费 15 字节*。key/value 越小、种类越杂，浪费越多。

2. **数据删除后不归还 OS（外因）**：Redis 删除一个 key 时，jemalloc 把这块内存挂到自己的 free list 上，*不会立刻* `munmap` 归还给操作系统 —— 从操作系统视角看，`used_memory_rss`（物理常驻内存）并没有下降。这是设计取舍：归还 OS 太慢，留着自己复用更快。

结果就是：Redis 内部看已释放 8GB，但操作系统看物理内存还是 20GB。这 8GB 就是碎片。

追问 为什么 Redis 默认选 jemalloc 而不是 glibc 的 ptmalloc？

jemalloc 在**多线程场景下抗碎片能力更强**（分 arena、per-thread cache），而且对小对象的分档更细。Redis 虽然单线程处理命令，但内部有 IO 线程、后台线程（BIO），仍受益于 jemalloc 的设计。历史上 Redis 也测过 tcmalloc、ptmalloc，jemalloc 综合表现最好。可以在编译时 `make MALLOC=libc` 换回 glibc，但基本没人这么干。

## 面试场景 2：怎么查内存碎片率？各个数值怎么解读？

🎤 面试官

怎么监控内存碎片？关键指标有哪些？

🧑‍💻 你

用 `INFO memory` 命令，重点看几个字段：

```
127.0.0.1:6379> INFO memory
# Memory
used_memory:1073741824              # Redis 分配器分配的内存（业务视角）
used_memory_human:1.00G
used_memory_rss:1610612736          # 操作系统实际分配的物理内存（RSS）
used_memory_rss_human:1.50G
mem_fragmentation_ratio:1.50        # 关键：碎片率 = rss / used_memory
mem_allocator:jemalloc-5.2.1
```

核心指标：`mem_fragmentation_ratio = used_memory_rss / used_memory`。解读表：

碎片率含义处理

**< 1**物理内存 < 逻辑分配 —— 说明部分数据被换到 *swap*非常糟！立刻查 swap，扩容或关 swap
1 ~ 1.5正常水位无需处理
**> 1.5**碎片严重（存 2GB 数据需要 3GB+ 物理内存）开 activedefrag 或主从切换重启
骤降可能刚删除大量 key，jemalloc 未归还 OS观察一段时间，不一定要立刻处理

追问 为什么 `mem_fragmentation_ratio < 1` 反而是最糟的？

正常情况下，物理内存 *永远* 大于等于逻辑分配（分配器只会多要不会少要）。`< 1` 只有一种可能：Redis 逻辑上要 10GB，操作系统只给了 8GB 物理内存 —— 剩下 2GB 被 **swap 到磁盘**了。一旦 Redis 访问到 swap 的部分，就是内存到磁盘的随机读，延迟从纳秒级飙到毫秒级，QPS 断崖式下跌。生产上一定要 `vm.swappiness=1`（甚至关闭 swap），并设置 `maxmemory` 硬上限。

## 面试场景 3：怎么清理内存碎片？activedefrag 怎么调？

🧑‍💻 你

三种方案，从推荐到不推荐：

1. **Redis 4.0+ 主动碎片整理（activedefrag）**：Redis 会在主线程空隙做*渐进式*整理，把分散的 key 重新分配到连续内存块。

2. **主从切换 + 重启副本**：让副本重启，它会用 RDB 重新加载，一次性消除碎片；然后主从切换让副本上位，再重启原主。零停机。

3. **直接重启 Redis**：单机场景兜底方案，短暂不可用。

activedefrag 的核心参数（都可以 `CONFIG SET` 动态改）：

```
# 打开开关
CONFIG SET activedefrag yes

# 触发条件（同时满足才启动）
CONFIG SET active-defrag-ignore-bytes 100mb    # 碎片总量 > 100MB 才考虑
CONFIG SET active-defrag-threshold-lower 10    # 碎片率 > 10% 才启动
CONFIG SET active-defrag-threshold-upper 100   # 碎片率 > 100% 时全力整理

# CPU 资源上限（避免整理反噬业务）
CONFIG SET active-defrag-cycle-min 5           # 至少占 5% CPU
CONFIG SET active-defrag-cycle-max 25          # 最多占 25% CPU
```

追问 activedefrag 有什么代价？为什么默认关闭？

会占 CPU！单线程 Redis 的 CPU 就是主线程，整理时会挤占业务命令的处理时间，*P99 延迟可能升高*。所以默认关闭，需要 DBA 根据场景开启。生产建议：**低峰期开、参数从保守值起调、监控 P99 变化**。`active-defrag-cycle-max` 一定要设，避免整理时把 CPU 打满。

追问 activedefrag 内部怎么实现的？为什么单线程能做碎片整理？

本质是**把 key 从「碎片密集的内存块」搬到「新分配的紧凑内存块」**，然后释放旧块给 jemalloc（jemalloc 拿到完整空块后就可以整块 `munmap` 归还 OS）。搬迁是一次一小批，每次只挪几十个 key，做完就让主线程回去处理业务命令 —— 类似 GC 的 *增量式回收*。因为 Redis 的 key 是通过 dict 索引的，改指针成本很低，所以搬迁本身也很快。

## 面试场景 4：大 key 操作为什么会阻塞？怎么办？⭐经典事故

🎤 面试官

业务反馈 Redis 每天凌晨都会有几次尖刺延迟，你 `SLOWLOG` 看到几条 `DEL user:profile:xxx` 耗时 800ms。怎么解释？怎么修？

🧑‍💻 你

典型的**大 key（bigkey）删除阻塞**。 给的经验阈值是：*String value > 1MB*、*Hash/List/Set/ZSet 元素数 > 5000* 就算大 key。

阻塞根源：**释放大量内存也是需要时间的**。`DEL` 一个大 Hash 时，Redis 要遍历 Hash 内部的所有 entry 逐个 free，操作系统还要维护空闲块链表 —— 这个过程整个都在主线程里，几百 MB 的大 key 可能阻塞几百毫秒。

常见的大 key 操作黑名单：

- `DEL bigkey` —— 同步删除

- `HGETALL 大Hash`、`LRANGE 大List 0 -1`、`SMEMBERS 大Set`、`ZRANGE 大ZSet 0 -1`

- `FLUSHDB`、`FLUSHALL`（同步版）

- 集群扩容时大 key 迁移（两端都阻塞）

解决方案：

1. **用 `UNLINK` 替代 `DEL`**（Redis 4.0+）：`UNLINK` 只把 key 从字典摘掉，实际释放丢给*后台线程 BIO*，主线程立刻返回。

2. **用 `FLUSHDB ASYNC` / `FLUSHALL ASYNC`**：同理，后台异步清库。

3. **分片存储**：大 Hash 拆成 `user:profile:xxx:part1`、`part2`；大 ZSet 按时间/ID 分段。

4. **用 `SCAN` / `HSCAN` / `SSCAN` / `ZSCAN` 遍历**：分批处理，每批 100 个，中间让出主线程。

5. **提前预警**：`redis-cli --bigkeys` 定期扫描，或者接入内部平台监控 `MEMORY USAGE key`。

追问 如何找出所有大 key？线上能直接跑 `KEYS *` 吗？

绝对不能 `KEYS *`（O(n) 阻塞主线程，正是场景 5 要讲的）。正确姿势：

1. `redis-cli --bigkeys`：官方工具，内部用 `SCAN` + 各类型的 *抽样* 命令，安全地扫出每种类型的最大 key。缺点：只找每类的 Top1，不全。

2. `redis-cli --memkeys`：更准，基于 `MEMORY USAGE`。

3. 离线分析 RDB：用 rdb-tools 把 RDB 转成 CSV，SQL 找 Top-N。零线上影响。

4. 自己写脚本：`SCAN` 遍历 + 对每个 key 调 `MEMORY USAGE key SAMPLES 0`（`SAMPLES 0` 表示精确统计而非抽样）。

## 面试场景 5：CPU 密集型命令阻塞

🧑‍💻 你

时间复杂度 O(n) 或更高的命令，随着数据规模会拖慢主线程。 列的黑名单：

危险命令复杂度替代方案

`KEYS pattern`O(n) 全库遍历`SCAN cursor MATCH pattern COUNT 100`
`HGETALL / HKEYS / HVALS`O(n)`HSCAN`
`SMEMBERS`O(n)`SSCAN`
`ZRANGE key 0 -1`O(n)`ZSCAN` 或分页 `ZRANGE key 0 99`
`SINTER / SUNION / SDIFF`O(n×m) 甚至 O(n²)预计算存 Set；或用 `SINTERSTORE` 落到临时 key 再分批读
`SORT`O(n + m log m)业务层排序；或加 `LIMIT`
`ZREMRANGEBYRANK / BYSCORE`O(log n + m)分批小范围删

SCAN 系列的核心特性：**基于游标的渐进式遍历**，单次调用只返回一小批，多次调用累积完整结果。它保证「一直存在的 key 一定被扫到」，但不保证「扫的过程中新加的 key 会被返回」，也可能返回重复 key —— 业务层要去重。

追问 `SCAN` 的 COUNT 参数是精确批大小吗？调到多大合适？

不是精确大小，只是*提示*。Redis 内部按 hashtable 的 bucket 遍历，返回的元素数可能少于/多于 COUNT。经验值：**100 ~ 1000**。太小 RTT 多，太大单次耗时长。生产上做全量遍历（比如清理过期业务数据）建议 COUNT=500 + 每批之间 sleep 1ms 让主线程喘气。

## 面试场景 6：fork 阻塞（BGSAVE / BGREWRITEAOF）

🎤 面试官

Redis 明明是异步的 `BGSAVE`，为什么还会阻塞主线程？

🧑‍💻 你

`BGSAVE` 和 `BGREWRITEAOF` 的*大部分*工作在子进程做，但 fork 那一瞬间是**阻塞主线程**的 —— fork 需要复制*页表*（COW 只复制页表不复制数据页，但页表本身也不小）。

影响 fork 耗时的因素：

- **实例越大 fork 越慢**：10GB 实例 fork 约 100-200ms，40GB 可达 500ms+。这段时间主线程*完全卡住*。

- **透明大页 THP（Transparent Huge Page）会加重**：THP 用 2MB 大页替代 4KB 小页，COW 时任何一次小写都会复制整个 2MB，放大延迟。*生产必关*：`echo never > /sys/kernel/mm/transparent_hugepage/enabled`。

- **虚拟化环境更慢**：VM/容器里 fork 通常比裸机慢 2-3 倍。

缓解手段：

1. 单实例内存别超过 **10GB**（超过就水平拆分或走 Cluster）。

2. 关闭 THP。

3. 用 `INFO stats` 看 `latest_fork_usec`（最近一次 fork 耗时，微秒），持续监控。

4. 把持久化压力放到副本节点做（主节点关 AOF/RDB，从节点开）。

追问 AOF 重写为什么也涉及 fork？和 RDB 的 BGSAVE 是同一个 fork 吗？

不是同一个但机制类似。`BGREWRITEAOF` 也 fork 子进程，子进程用当前内存快照生成一份紧凑 AOF；重写期间主进程新写入的命令先缓存到 *AOF 重写缓冲区*，重写结束后追加到新文件，然后原子替换旧文件。fork 的开销和 BGSAVE 一样。**重要：Redis 有互斥机制，同一时刻只允许一个 fork 子进程**，AOF 重写期间 BGSAVE 会被延后。

## 面试场景 7：AOF fsync 阻塞

🧑‍💻 你

AOF 有三种刷盘策略（`appendfsync`）：

策略行为数据安全性能阻塞风险

`always`每次写命令都在*主线程*调 fsync最高（最多丢 1 条）最差每次写都可能阻塞
`everysec`（默认推荐）写命令进 AOF buffer，*后台线程*每秒 fsync 一次最多丢 1 秒好后台 fsync 卡住时会阻塞主线程写入
`no`只写 AOF buffer，fsync 交给 OS 决定差（宕机可能丢几十秒）最好无

`everysec` 的阻塞机制值得说清楚：主线程写命令进 buffer 时会*检查*后台 fsync 是否卡住 —— 如果上一次 fsync 已经超过 2 秒还没完成（一般是磁盘 IO 打满），主线程会**等它完成再写**，防止 buffer 无限膨胀。这就是「AOF fsync 阻塞主线程」的真实场景。

相关参数：

- `no-appendfsync-on-rewrite yes`：AOF 重写期间不做 fsync（避免和重写子进程抢磁盘 IO），代价是宕机可能丢重写期间的所有数据。

- `aof-use-rdb-preamble yes`：混合持久化，AOF 文件前半段是 RDB 二进制，后半段是增量命令，重写快、恢复快。

追问 除了 AOF，还有哪些操作会「隐式」用后台线程？

Redis 有专门的 **BIO（Background IO）线程池**，处理不适合主线程做的重活：

1. `UNLINK` / 惰性释放 —— 大 key 的内存释放丢到 BIO。

2. AOF fsync（`everysec` 模式）—— 独立 BIO 线程做。

3. 关闭文件描述符（`lazyfree-lazy-*` 系列参数控制）。

Redis 6.0 又新增了 **IO 多线程**（`io-threads`），但只做*网络包读写*，不做命令执行 —— 所以「Redis 命令是单线程」的说法直到今天仍成立。

## 面试场景 8：网络 IO 与其他冷门阻塞点

🧑‍💻 你

除了内存和 CPU，网络和运维层面还有几个隐蔽阻塞：

1. **未用 pipeline，命令来回 RTT**：客户端串行发 N 条命令要 N 次 RTT。同机房 RTT ~0.5ms，1000 条就是 500ms 纯网络耗时。*解法*：`PIPELINE` 一次发多个、批量返回；或用 `MSET`/`MGET`/`HMSET`。

2. **大响应包阻塞**：`LRANGE list 0 -1` 返回 10MB 数据，主线程要把这 10MB 序列化并写入 socket buffer，期间无法处理其他命令。*解法*：分页读取。

3. **swap 交换**（前面提过）：Redis 内存被换到磁盘，访问时随机 IO，延迟毫秒级。*检测*：`cat /proc/{pid}/smaps | grep Swap`；*预防*：设 `maxmemory`、`vm.swappiness=1`。

4. **CPU 竞争**：Redis 是 CPU 密集型进程，混部在其他吃 CPU 的服务上会被抢核。*解法*：绑核（`taskset -cp 2 <pid>`）、独占物理机、和 IO 密集型服务混部。

5. **网卡软中断打在 Redis 所在 CPU**：所有网络包中断集中处理会挤占 Redis 的 CPU 时间。*解法*：RSS/RPS 把中断分散到多个核，避开 Redis 的核。

追问 pipeline 和 事务（MULTI/EXEC）有什么区别？

本质不同：**pipeline 只是网络优化**，客户端把多个命令打包一次发、一次收，服务端*该怎么执行还怎么执行*（命令之间可以插入别的客户端的命令）。**事务**是服务端语义：`MULTI` 开启后所有命令入队，`EXEC` 时一次性顺序执行，中间不会被打断。两者可以组合：pipeline 里发 `MULTI` + 若干命令 + `EXEC`，就同时拿到网络优化和原子性。

## 面试场景 9：Redis 8 种内存淘汰策略 ⭐经典

🎤 面试官

Redis 达到 `maxmemory` 上限后会怎么处理？有几种策略？你线上选哪种？

🧑‍💻 你

由 `maxmemory-policy` 配置，共 **8 种**（4.0 之前是 6 种，4.0 加了 LFU 两种）：

策略作用范围淘汰规则典型场景

`noeviction`—**不淘汰**，写命令直接报错 *OOM command not allowed*默认；重要数据不可丢的场景
`allkeys-lru`所有 key淘汰最久未访问的（Least Recently Used）纯缓存，最常用
`allkeys-lfu`所有 key淘汰访问频次最低的（Least Frequently Used，4.0+）缓存 + 存在少量超热 key
`allkeys-random`所有 key随机淘汰key 访问概率均匀（几乎没这种业务）
`volatile-lru`*只淘汰设了 TTL 的 key*在带 TTL 的 key 里淘汰 LRU缓存和持久数据混存，永久数据不能丢
`volatile-lfu`只淘汰设了 TTL 的 key在带 TTL 的 key 里淘汰 LFU同上，热点分布陡峭
`volatile-random`只淘汰设了 TTL 的 key在带 TTL 的 key 里随机淘汰兜底
`volatile-ttl`只淘汰设了 TTL 的 key淘汰*剩余 TTL 最短*的（快到期的先走）业务对短过期 key 无所谓

选型经验：**纯缓存选 `allkeys-lru` 或 `allkeys-lfu`**；**缓存 + 持久混存选 `volatile-lru`**；**绝不能丢数据的场景选 `noeviction` + 严格监控内存**。*不要用* `random` 系列，几乎没有对得起它的业务模型。

追问 Redis 的 LRU 和标准 LRU 有什么不同？

标准 LRU 需要维护一个*完整的双向链表*，每次访问把节点挪到头部，淘汰尾部 —— 内存开销大（每个 key 多两个指针）。Redis 用**近似 LRU（approximated LRU）**：*不维护链表*，只在每个 key 的元数据里记一个 24 位的*最近访问时间戳*。淘汰时*随机采样* N 个 key（`maxmemory-samples` 默认 5，可调到 10），从中挑最老的淘汰。采样越多越接近真实 LRU，但耗时也越多。这就是「精度换空间」的经典 tradeoff。

追问 LFU 相比 LRU 好在哪？Redis 的 LFU 计数怎么不溢出？

LFU 关注*访问频次*而非最近时间。经典 case：一个大 key 在凌晨被批处理扫了一次，LRU 会认为它「最新访问」而把真正的热点顶掉；LFU 只加 1 次频次，不影响热点。

Redis 的 LFU 用 8 位存频次（`counter`），最大 255 —— 直接自增早溢出了。Redis 用 **Morris counter 概率计数**：counter 越大，自增概率越低（对数级）。同时有*衰减机制*（`lfu-decay-time`），一段时间没访问就减少 counter，避免「历史热点永远压制新热点」。参数：`lfu-log-factor`（增长速率）、`lfu-decay-time`（衰减周期分钟）。

## 面试场景 10：过期删除策略（和内存淘汰不是一回事！）

🎤 面试官

Redis 的过期删除和内存淘汰，是同一件事吗？分别是什么机制？

🧑‍💻 你

不是同一件事：

- **过期删除（expire）**：处理「设了 TTL 的 key 到期后什么时候真正被删掉」。

- **内存淘汰（eviction）**：处理「内存到 `maxmemory` 上限后要不要删、删哪些」。

过期删除用**惰性删除 + 定期删除**组合：

1. **惰性删除（lazy expiration）**：客户端访问 key 时，Redis 先判断是否过期，过期就删除并返回 nil。*优点*：CPU 友好，只处理真正被访问的 key。*缺点*：过期但一直没被访问的 key 会一直占内存。

2. **定期删除（active expiration）**：Redis 每秒运行 10 次（由 `hz` 配置，默认 10）主动扫描：

- 从「设了 TTL 的 key 的字典」里随机抽 **20 个** key。

- 删除其中过期的。

- 如果*过期比例 > 25%*，继续再抽 20 个，直到比例低于 25% 或超时。

两者互补：惰性删除兜底真被访问的 key，定期删除兜底闲置的过期 key。

追问 Redis 的定期删除会漏掉过期 key 吗？漏掉的怎么办？

会漏！定期删除只是*随机抽样*，本身就是概率性的。漏掉的过期 key 有三条兜底路径：

1. **被访问时惰性删除** —— 大部分漏网之鱼在下次访问时被清。

2. **触发内存淘汰** —— 内存到 `maxmemory` 时，`volatile-*` 策略会优先干掉带 TTL 的 key。

3. **下一轮定期删除再抽** —— 概率总会命中。

如果业务对「过期数据不能被读到」有强要求，客户端应用侧要*再判断一次时间*，别只依赖 Redis 的 TTL —— 主从复制延迟场景下副本可能读到主已经删掉但还没同步过来的过期数据。

## 💻 代码验证（redis-cli 直接跑）

### 验证 1：查看内存碎片

```
$ redis-cli
127.0.0.1:6379> INFO memory
# Memory
used_memory:2147483648                # 2GB 业务数据
used_memory_human:2.00G
used_memory_rss:3221225472            # 3GB 物理内存
used_memory_rss_human:3.00G
mem_fragmentation_ratio:1.50          # 碎片率 1.5，边缘警戒
mem_allocator:jemalloc-5.2.1

# 只看关键指标
127.0.0.1:6379> INFO memory | grep -E "fragmentation|used_memory_(rss|human)"
```

### 验证 2：找出并安全删除大 key

```
# 扫描大 key（内部用 SCAN，不阻塞主线程）
$ redis-cli --bigkeys

# 精确测量单个 key 内存
127.0.0.1:6379> MEMORY USAGE user:profile:12345 SAMPLES 0
(integer) 5242880          # 5MB，是个大 key

# 危险：同步删除会阻塞
127.0.0.1:6379> DEL user:profile:12345        # 主线程释放 5MB，可能几十毫秒阻塞

# 推荐：异步删除
127.0.0.1:6379> UNLINK user:profile:12345     # 主线程立刻返回，BIO 后台释放

# 批量清库时也用异步
127.0.0.1:6379> FLUSHDB ASYNC
```

### 验证 3：开启主动碎片整理

```
# 动态开启（无需重启）
127.0.0.1:6379> CONFIG SET activedefrag yes
OK

# 从保守值起调
127.0.0.1:6379> CONFIG SET active-defrag-ignore-bytes 100mb
127.0.0.1:6379> CONFIG SET active-defrag-threshold-lower 10
127.0.0.1:6379> CONFIG SET active-defrag-cycle-min 5
127.0.0.1:6379> CONFIG SET active-defrag-cycle-max 25

# 持久化到配置文件（避免重启后失效）
127.0.0.1:6379> CONFIG REWRITE

# 观察整理进度
127.0.0.1:6379> INFO memory | grep defrag
active_defrag_running:1               # 1 表示正在整理
active_defrag_hits:1234
active_defrag_misses:56
active_defrag_key_hits:78
active_defrag_key_misses:9
```

### 验证 4：配置内存淘汰策略 + 观察淘汰

```
# 设置内存上限（重要！生产必设）
127.0.0.1:6379> CONFIG SET maxmemory 4gb

# 设淘汰策略：纯缓存选 allkeys-lfu
127.0.0.1:6379> CONFIG SET maxmemory-policy allkeys-lfu

# 采样数调大提高精度（默认 5，建议 10）
127.0.0.1:6379> CONFIG SET maxmemory-samples 10

# 观察淘汰次数
127.0.0.1:6379> INFO stats | grep evicted
evicted_keys:12345                    # 累计被淘汰的 key 数量

# 观察过期删除
127.0.0.1:6379> INFO stats | grep expired
expired_keys:98765                    # 累计过期删除的 key 数量
expired_stale_perc:0.05               # 过期但未及时删除的估算比例
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `mem_fragmentation_ratio` 的三个关键区间（< 1、1~1.5、> 1.5）分别代表什么？</summary>

**< 1**：物理内存少于逻辑分配，说明用了 swap，非常危险（延迟从 ns 级涨到 ms 级）。**1 ~ 1.5**：正常水位。**> 1.5**：碎片严重，考虑开启 activedefrag 或主从切换重启。

</details>

<details>

<summary>Q2 `DEL bigkey` 阻塞主线程的根本原因？两个替代命令是什么？</summary>

根因：释放大量内存需要遍历数据结构 + 更新 OS 空闲块链表，全在主线程。替代：`UNLINK key` 异步删除（4.0+），`FLUSHDB ASYNC` / `FLUSHALL ASYNC` 异步清库。也可以配 `lazyfree-lazy-*` 参数让 DEL 也走异步。

</details>

<details>

<summary>Q3 为什么 `BGSAVE` 明明有子进程还会阻塞主线程？</summary>

fork 那一瞬间要复制页表，实例越大页表越大，10GB 实例通常 100-200ms 阻塞，40GB+ 可达秒级。透明大页 THP 会加重（COW 单位从 4KB 变 2MB）。缓解：控制单实例 <10GB、关 THP、监控 `latest_fork_usec`。

</details>

<details>

<summary>Q4 列出 Redis 8 种内存淘汰策略，并说明纯缓存业务应该选哪种。</summary>

8 种：`noeviction`（默认，不淘汰报错）、`allkeys-lru`、`allkeys-lfu`、`allkeys-random`、`volatile-lru`、`volatile-lfu`、`volatile-random`、`volatile-ttl`。纯缓存选 `allkeys-lru`（简单场景）或 `allkeys-lfu`（热点分布陡峭时更好，避免偶发大扫顶掉真热点）。

</details>

<details>

<summary>Q5 过期删除的两种机制是什么？定期删除的具体算法？</summary>

**惰性删除**：客户端访问 key 时才判断并删除。**定期删除**：每秒 10 次（`hz=10`）从「带 TTL 的 key 字典」抽 20 个检查，过期比例 > 25% 就再抽一轮，直到低于 25% 或超时。漏掉的 key 靠惰性删除或 `volatile-*` 淘汰兜底。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

- Redis 官方 · Key eviction —— 8 种 maxmemory-policy 官方说明

- Redis 官方 · Memory optimization —— jemalloc / defrag 官方指南

#### 🔗 关联课件

-  —— 单线程为什么阻塞是致命的

-  —— fork / fsync 阻塞的上下文

-  —— 上一课

#### 🧭 下一课预告

Lesson 0058：**** —— List / ZSet / Stream 三种方案的取舍。

💬 有任何疑问 —— 「activedefrag 参数怎么在我们业务场景调？」「allkeys-lru 和 volatile-lru 到底选哪个？」「大 key 遗留怎么灰度清理？」—— 直接问我。我是你的老师，也是你的追问陪练。


