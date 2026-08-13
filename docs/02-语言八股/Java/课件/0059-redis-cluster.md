> Lesson 0059 · 阶段七 · Redis 收尾 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 6 处追问亮点

# 0059 · Redis 高可用：主从 & 哨兵 & Cluster

这是**阶段七 · Redis 的收尾课**。前面几课我们看的都是「单机 Redis 怎么跑得快、跑得稳」，但真正到生产环境，只有一台 Redis 是不够的 —— *机器掉电、网卡故障、机房断网*，业务立刻断，缓存击穿到 MySQL，DB 也跟着崩。

Redis 的高可用是**三层递进**的架构：

- **主从复制（Master-Slave）**：给主库配几个从库同步数据，主挂了*手动*切一个从上来当主，同时读走从、写走主实现读写分离。

- **哨兵 Sentinel**：一组独立进程盯着主从，主库挂了*自动*选新主 + 通知客户端 —— 解决「主从复制不自动切」这个痛点。

- **Cluster 集群**：数据分成 `16384` 个槽分布到多个 master 上，去中心化 + 内嵌故障转移 —— 解决「单机内存 + 单机 QPS」的容量上限问题。

这三层不是替代，而是*适用不同规模*：小体量主从就够，主从加哨兵抗故障，数据量超过单机上限（一般 > 30GB）就必须上 Cluster。面试基本每一层都会问到。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 主从复制什么时候会触发**全量同步**？</summary>

从库*首次*连接主库、或者断线太久 `offset` 已经不在 *replication backlog buffer* 内 —— 都会触发全量：主库 `BGSAVE` 生成 RDB 传给从库。第 2 题细讲。

</details>

<details>

<summary>Q0.2 Redis Cluster 有多少个槽（slot）？为什么是这个数字？</summary>

**16384（2¹⁴）**。作者 antirez 的权衡：节点间用 gossip 交换 slot 位图，16384 位 = 2KB，节点数不超过 1000 时消息小；65536 太大浪费带宽。第 8 题细讲。

</details>

## 面试场景 1：Redis 主从复制的作用是什么？

🎤 面试官

你们线上 Redis 为什么要配主从？

🧑‍💻 你

主从复制解决三个问题：

- **读写分离**：写走主，读走从，读 QPS 可以随从库数量线性扩展。

- **数据备份**：从库天然是主库的实时副本，主库磁盘坏了从库还在。

- **故障恢复**：主库挂了，可以把某个从库*手动*提升为新主，业务恢复。

但要说清楚一点：*主从复制本身不解决自动故障转移* —— 主挂了必须运维手动 `SLAVEOF NO ONE` 切主 + 改客户端配置，中间会有几分钟到几十分钟不可用。这就是为什么生产必须配哨兵或 Cluster。

追问 从库能写吗？

默认**不能**。`replica-read-only yes`（旧名 `slave-read-only`）是默认配置，从库只允许读。如果强行把它设为 `no`，从库上写的数据*不会同步给主库*，主库下一次全量同步时又会覆盖掉从库的所有数据，非常危险。所以「从库只读」是铁律。

## 面试场景 2：主从复制的全量同步流程 ⭐核心

🎤 面试官

从库第一次连上主库，数据是怎么同步过来的？

🧑‍💻 你

这就是**全量同步（full resync）**，完整流程：

1. 从库启动，配置了 `replicaof <master-host> <master-port>`，发起连接。

2. 从库发送 `PSYNC ? -1`（第一个参数是主库 `runid`，第二个是复制偏移 `offset`；第一次都不知道，所以填 `? -1`）。

3. 主库收到，回复 `+FULLRESYNC <runid> <offset>`，告诉从库「你要做全量同步，记住我的 runid 和当前 offset」。

4. 主库后台 `fork` 出子进程执行 `BGSAVE` 生成 `RDB` 文件。

5. RDB 生成完，主库把文件通过 socket 发送给从库。

6. 从库*清空自己的旧数据*，加载 RDB。

7. 在 RDB 生成 + 传输 + 加载这段时间里，主库继续接受写命令；这些新写命令都缓存在 **replication backlog buffer**（一个环形缓冲区）里，等从库加载完 RDB 后再逐条补发过去。

8. 之后进入*命令传播*阶段：主库每执行一条写命令，都异步转发给从库。

陷阱 全量同步**非常重**：数据量大（10GB+）的主库，一次 BGSAVE 可能占几十秒、CPU 尖峰 + 内存 `copy-on-write` 翻倍、RDB 传输占用带宽。所以生产上要*避免频繁全量*：把 `repl-backlog-size` 调大（默认 1MB 太小），把从库网络稳住。

追问 全量同步的 RDB 是从磁盘读还是内存直接传？

Redis 2.8.18 之前**必须**先把 RDB 落到磁盘再读出来发给从库 —— 磁盘 IO 是瓶颈。2.8.18 起支持**无盘复制 diskless replication**：`repl-diskless-sync yes` 开启后，主库 `fork` 出的子进程直接把 RDB 序列化*流式*写到 socket，不落磁盘，快很多。适用场景：磁盘慢但网络快（比如云主机 SSD 一般 + 万兆内网）。

## 面试场景 3：主从复制的增量同步

🎤 面试官

如果从库断了一会儿又连上，还要再全量同步一次吗？

🧑‍💻 你

不一定，Redis 2.8 起支持**部分重同步（partial resync）**，也就是*增量同步*：

1. 从库重连后依然发 `PSYNC <runid> <offset>`，但这次*带着自己上次的 runid 和 offset*。

2. 主库判断：**如果 runid 匹配**（还是我这个主）**且从库的 offset 还在 replication backlog buffer 内**，就只把 `offset` 之后的写命令补发过去。

3. 否则退回全量同步。

关键在 `replication backlog buffer`：这是主库上一个*环形缓冲区*，默认 1MB，缓存最近的写命令流。`repl-backlog-size` 应该设为 *主库峰值写入速率 × 从库可能断线的秒数*。比如写入 5MB/s、担心从库断线 5 分钟，那 backlog 至少 `5 × 60 × 5 = 1500MB`。

追问 主库重启后，从库为什么必然全量同步？

主库重启会生成*新的 runid*（除非用 `debug reload` 或 4.0+ 的 `PSYNC2` 优化），从库带着旧 runid 来 `PSYNC`，主库发现「runid 不匹配 → 我不是原来那个我」，直接触发全量。所以主库*绝对不能随便重启*，尤其大内存实例。

## 面试场景 4：哨兵 Sentinel 是什么？⭐核心

🎤 面试官

只配主从有什么问题？哨兵解决了什么？

🧑‍💻 你

主从的痛点：*主库挂了没人管*。生产上不能真让运维半夜爬起来手动切主，所以出现了 **Redis Sentinel**：

- Sentinel 是一组**独立进程**（不是数据节点），部署在几台机器上，专门监控 Redis 主从集群。

- Sentinel 之间自己组网、互相通信。

- 发现主库挂了 → *自动*从从库中选一个提升为主 → 通知其他从库改跟新主 → 通知客户端新主地址。

生产至少部署 **3 个哨兵（奇数）**，分布在不同机器、最好不同机架/可用区。奇数是为了避免脑裂时投票平票，也为了满足「过半判定」。

陷阱 Sentinel **只能管非 Cluster 架构的主从**。如果你已经用 Redis Cluster，就*不需要也不能*再配 Sentinel —— Cluster 自带故障转移机制，两套并存反而会打架。

## 面试场景 5：哨兵的工作机制

🧑‍💻 你

哨兵通过三个机制协作：

1. **监控**：每个哨兵定期（默认 1 秒）向所有主从节点、其他哨兵发 `PING`。

2. **主观下线 sdown（subjectively down）**：*某一个*哨兵连续 `down-after-milliseconds`（默认 30 秒）没收到主库回复，就*单方面*判定「我觉得它挂了」。

3. **客观下线 odown（objectively down）**：这个哨兵去问其他哨兵「你们也觉得主挂了吗？」，超过配置的 `quorum`（法定人数，通常 > 哨兵总数一半）都同意，才升级为客观下线 —— 才真正启动故障转移。

然后哨兵们通过一个**类 Raft** 的选举，选出一个 *leader 哨兵* 来执行故障转移（避免多个哨兵同时切主导致混乱）。

追问 哨兵脑裂怎么处理？

网络分区场景：主库和一部分哨兵在 A 区，从库和另一部分哨兵在 B 区。B 区哨兵判定主客观下线，选出新主；A 区的老主还在接受客户端写入 —— 出现两个主，脑裂了。网络恢复后，老主会被降为从并做全量同步，*期间它接受的写入全部丢失*。防御：配 `min-replicas-to-write N` + `min-replicas-max-lag M`（旧名 `min-slaves-*`），要求主库至少有 N 个从连接、且延迟 < M 秒才允许写入；少数派主区一旦从库掉光就自动拒绝写，把损失控制到最小。

## 面试场景 6：哨兵故障转移的完整流程

🧑‍💻 你

Leader 哨兵一旦被选出，故障转移分四步：

1. **选新主**：从所有从库中挑一个，优先级顺序是：

- `replica-priority`（旧 `slave-priority`）小的优先（0 代表永不参选）

- 再看*复制偏移 offset*：谁同步的数据最新（offset 最大）谁上

- 都相同就选 *runid 字典序小*的

2. **提升**：对选中的从库执行 `SLAVEOF NO ONE`（新版 `REPLICAOF NO ONE`），它变成新主。

3. **切从**：对其他从库执行 `SLAVEOF <新主 host> <port>`，让它们跟新主同步。

4. **通知客户端**：客户端要么直连哨兵订阅 `+switch-master` 事件，要么用 Jedis/Lettuce 的 *Sentinel-aware* 客户端，自动拿到新主地址。老主如果之后恢复，会被降为从跟新主同步。

## 面试场景 7：Redis Cluster 是什么？⭐核心

🎤 面试官

数据量到 100GB 还能用主从 + 哨兵吗？

🧑‍💻 你

不能。主从架构的*每个节点都存全量数据*，单机内存是硬上限（一般单实例超过 30GB 就要考虑分片，因为 fork 时 COW 内存翻倍很危险）。数据量超过这个门槛必须用 **Redis Cluster**：

- Redis 3.0 引入的*官方原生*分片方案。

- **去中心化**：没有单独的 proxy/coordinator，所有节点平等，通过 *gossip* 协议互相同步 slot 分布信息。

- **数据分片**：整个数据空间分成 `16384` 个槽（slot），分配给多个 master 节点，每个 master 负责一段槽（比如 6 主 → 每个 master 约 2730 槽）。

- **每个 master 可挂多个 replica**：既能读写分离（如果开 `READONLY`），也用于 master 故障时自动提升。

- **内嵌故障转移**：不再需要 Sentinel，Cluster 协议本身就带故障检测和主备切换。

生产最小规模：**3 主 3 从**（3 个 master 分片，每个各一个 replica，共 6 个进程分布在 3+ 台机器上）。

## 面试场景 8：为什么 Cluster 的槽数是 16384？

🎤 面试官

为什么不是 1024 或 65536？

🧑‍💻 你

这是 Redis 作者 antirez 在 GitHub issue #2576 里亲自解释过的**工程权衡**，两个关键约束：

1. **gossip 消息大小**：Cluster 节点之间要频繁交换*「我知道哪些 slot 属于哪些节点」*这份信息，用*位图*编码。16384 个 slot = `16384 / 8 = 2048 字节 = 2KB`；如果是 65536，就是 8KB —— 每秒几十次心跳，带宽白白浪费。

2. **节点数上限**：Cluster 设计上限约 1000 个节点。*slot 数远大于节点数*就够用了：16384 / 1000 ≈ 16 slot/节点，粒度足够细做数据均衡。真上到 65536 也没有额外好处。

此外，*CRC16 输出是 16 位（65536 种）*，作者选 16384 是 65536 的 1/4，正好用 `CRC16(key) & 0x3FFF` 一步取模到 [0, 16383]，位运算比 `% 65536` 稍微省点 CPU。综合下来 16384 是最平衡的选择。

## 面试场景 9：Cluster 的数据路由 & MOVED / ASK / hash tag

🧑‍💻 你

客户端发一个 `GET user:1`，Cluster 怎么知道去哪台机器取？

1. 算槽：`slot = CRC16("user:1") & 16383`（等价于 `% 16384`）。

2. 客户端本地已经缓存了 *slot → 节点* 的映射表（首次连接时通过 `CLUSTER SLOTS` 拉到），直接连正确的 master。

3. 如果客户端映射过期了 → 请求发到了错误节点 → 节点回 `-MOVED <slot> <正确的 host:port>`，客户端更新缓存并重试。

4. 如果 slot 正在*迁移中*（比如扩容 reshard），旧节点回 `-ASK <slot> <新节点>`，客户端*临时一次性*跳到新节点并加 `ASKING` 前缀请求 —— 但不更新本地映射，因为迁移未完成。

**hash tag**：默认情况下不同 key 大概率落到不同 slot，事务/Lua/multi-key 命令跨 slot 直接报错。*用花括号 `{}` 包起来的部分才参与 CRC16 计算*：

```
{user:1}.name  → CRC16("user:1")
{user:1}.email → CRC16("user:1")
// 两个 key 落到同一 slot，可以放在同一个事务里
```

追问 Cluster 的读能不能走从库？

默认**不能**。客户端算出 slot 之后只连该 slot 对应的 master。想读从库要在连接上先发 `READONLY`，之后这个连接就允许读该 master 的 replica，但读到的可能是*延迟数据*。所以「读多写少 + 允许弱一致」的场景才开，比如商品详情、排行榜；订单、账户余额这类必须走 master。

追问 Cluster 扩容/缩容怎么做？

用 `redis-cli --cluster reshard <host:port>`：交互式指定「迁移多少 slot、从哪个源节点、到哪个目标节点」。底层过程：源节点把 slot 内的 key 一个个 `MIGRATE` 到目标节点，迁移期间该 slot 状态为 *MIGRATING/IMPORTING*，请求打到源节点如果 key 还在就直接处理，如果 key 已迁走就回 `-ASK` 重定向。缩容同理，先把目标节点的 slot 全迁走再下线节点。*整个过程业务无感*，但迁移大 key 会阻塞源节点，所以要避免大 key。

## 面试场景 10：Cluster 的故障检测与转移

🧑‍💻 你

Cluster 内嵌的故障机制，逻辑上和哨兵类似但自己搞：

1. **心跳**：所有节点之间通过 *gossip 协议*相互 `PING/PONG`，每次带一部分节点状态。

2. **PFAIL（Possibly Fail，主观下线）**：某节点连续超过 `cluster-node-timeout`（默认 15 秒）没收到某个 master 的响应，就在本地标记它 PFAIL。

3. **FAIL（客观下线）**：这个节点把 PFAIL 消息 gossip 给其他节点，如果*半数以上 master* 都认为该 master PFAIL，就统一升级为 FAIL 状态，向全集群广播。

4. **选新主**：故障 master 的 replica 们发起一个*类 Raft 的选举*：向所有 master 请求投票，先获得半数 master 票的 replica 胜出。选举依据同样看 *复制偏移最大* 优先（数据最新）。

5. **提升**：胜出的 replica 执行 `REPLICAOF NO ONE`，接管原 master 的所有 slot，并 gossip 通知全集群更新路由。

追问 Cluster 的*脑裂*怎么处理？

和哨兵类似的问题：网络分区导致少数派 master 依然接受写入，等分区恢复被降为 replica 时数据丢失。同样用 `min-replicas-to-write` + `min-replicas-max-lag` 缓解 —— 少数派 master 一旦从库联系不上就自动拒绝写。另外*不要跨机房部署 Cluster*，跨机房网络抖动会让 `cluster-node-timeout` 频繁触发不必要的故障转移。

追问 Redis Cluster 和 Sentinel 能一起用吗？

**不用也不该用**。Cluster 已经把故障检测（PFAIL/FAIL）+ 选举（类 Raft）+ 主备切换全部内嵌到集群协议里；Sentinel 是*为非 Cluster 主从架构*设计的独立监控组件。两者的适用场景是*互斥*的：数据量小选「主从 + 哨兵」，数据量大选「Cluster」。同时装 Sentinel 只会造成配置和故障处理的混乱。

## 💻 代码 & 命令验证

### 验证 1：一分钟起主从

```
# 一台机器起主
redis-server --port 6379 --daemonize yes

# 起两个从（新版语法用 replicaof；旧版 slaveof 也兼容）
redis-server --port 6380 --daemonize yes --replicaof 127.0.0.1 6379
redis-server --port 6381 --daemonize yes --replicaof 127.0.0.1 6379

# 主库看角色和复制状态
redis-cli -p 6379 INFO replication
# role:master
# connected_slaves:2
# slave0:ip=127.0.0.1,port=6380,state=online,offset=1234,lag=0
# slave1:ip=127.0.0.1,port=6381,state=online,offset=1234,lag=0
# master_replid:ab12...           ← runid
# master_repl_offset:1234         ← 当前偏移

# 从库看
redis-cli -p 6380 INFO replication
# role:slave
# master_host:127.0.0.1
# master_link_status:up
# master_last_io_seconds_ago:1
# slave_read_only:1               ← 从库只读，默认开
```

### 验证 2：Sentinel 起 3 个哨兵

```
# sentinel.conf（每个哨兵一份，端口和 pid 文件改一下）
port 26379
sentinel monitor mymaster 127.0.0.1 6379 2
# ↑ 监控名为 mymaster 的主库 127.0.0.1:6379；quorum=2 意思是需要 2 个哨兵同意才算 odown
sentinel down-after-milliseconds mymaster 30000
sentinel failover-timeout mymaster 180000
sentinel parallel-syncs mymaster 1
# ↑ 故障转移时，一次让几个从库并行去同步新主。太大网络会挤，一般 1

# 启动
redis-sentinel /path/to/sentinel.conf
redis-sentinel /path/to/sentinel-2.conf    # port 26380
redis-sentinel /path/to/sentinel-3.conf    # port 26381

# 查看当前主库是谁
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
# 1) "127.0.0.1"
# 2) "6379"

# 手动触发一次故障演练
redis-cli -p 26379 SENTINEL failover mymaster
```

### 验证 3：一键起 3 主 3 从 Cluster

```
# 起 6 个 Redis 实例，都要开 cluster-enabled
for port in 7000 7001 7002 7003 7004 7005; do
mkdir -p /tmp/redis-$port
redis-server --port $port --daemonize yes \
--cluster-enabled yes \
--cluster-config-file nodes-$port.conf \
--cluster-node-timeout 15000 \
--dir /tmp/redis-$port
done

# 一键创建 cluster：--cluster-replicas 1 表示每个 master 配 1 个 replica
redis-cli --cluster create \
127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
--cluster-replicas 1

# 输出会显示 slot 分配：
# M: 7000  slots 0-5460
# M: 7001  slots 5461-10922
# M: 7002  slots 10923-16383
# S: 7003 → 7000  (replica of 7000)
# ...

# 客户端用 -c 参数才会自动处理 MOVED 重定向
redis-cli -c -p 7000
127.0.0.1:7000> SET user:1 alice
-> Redirected to slot [8422] located at 127.0.0.1:7001
OK

# 查看集群状态
redis-cli -p 7000 CLUSTER INFO
redis-cli -p 7000 CLUSTER NODES
```

### 验证 4：hash tag 让多 key 落到同一 slot

```
redis-cli -c -p 7000

# 两个不相关的 key，大概率不同 slot
127.0.0.1:7000> SET user1:name alice
-> Redirected to slot [3232] at 127.0.0.1:7000
127.0.0.1:7000> SET user1:email a@x.com
-> Redirected to slot [10023] at 127.0.0.1:7001

# 想做事务？跨 slot 直接报错
127.0.0.1:7000> MULTI
127.0.0.1:7000> SET user1:name alice
127.0.0.1:7000> SET user1:email a@x.com
127.0.0.1:7000> EXEC
(error) CROSSSLOT Keys in request don't hash to the same slot

# 用 hash tag {user:1} 强制同槽
127.0.0.1:7000> SET {user:1}.name alice
-> Redirected to slot [5474] at 127.0.0.1:7001
127.0.0.1:7000> SET {user:1}.email a@x.com
OK                       ← 同一 slot，无需重定向

# 现在可以 MULTI/EXEC 了
127.0.0.1:7001> MULTI
127.0.0.1:7001> SET {user:1}.name bob
127.0.0.1:7001> SET {user:1}.email b@x.com
127.0.0.1:7001> EXEC
1) OK
2) OK
```

追问 主从复制的延迟怎么办？

*异步复制天然有延迟*，写完主库到从库可见有几毫秒到几百毫秒不等。三个应对策略：**1)** 关键读走主（订单、余额），非关键读走从（商品详情、排行榜）；**2)** 配 `replica-serve-stale-data no`，当从库和主库断连或延迟过大时，从库*拒绝服务*而不是给出脏数据；**3)** 业务层写后立即读时，加短暂重试或强制走主。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 主从复制的全量同步与增量同步分别在什么条件下触发？</summary>

全量：从库*首次*连接、或者从库带来的 `runid` 与主库不匹配、或者 `offset` 已经不在 `replication backlog buffer` 中。增量：runid 匹配且 offset 仍在 backlog 内，主库只补发差量。

</details>

<details>

<summary>Q2 哨兵的「主观下线」和「客观下线」分别是什么？为什么要分两步？</summary>

主观下线（sdown）：单个哨兵 `down-after-milliseconds` 内没收到主库响应，自己认为它挂了。客观下线（odown）：多数哨兵（≥ quorum）都同意，才算真挂。分两步是为了避免*单个哨兵网络抖动*就误判触发不必要的故障转移。

</details>

<details>

<summary>Q3 Redis Cluster 有多少个 slot？如何把 key 映射到 slot？</summary>

16384 个（2¹⁴）。映射公式：`slot = CRC16(key) & 16383`。带 hash tag 时只对 `{}` 内的子串算 CRC16，用于把多个相关 key 强制放到同一 slot。

</details>

<details>

<summary>Q4 Cluster 里 MOVED 和 ASK 有什么区别？</summary>

MOVED：slot 已经*永久*属于新节点，客户端更新本地 `slot → 节点` 映射并重试。ASK：slot 正在*迁移中*（临时状态），客户端只本次跳过去并加 `ASKING` 前缀，*不更新映射*，因为迁移未完成。

</details>

<details>

<summary>Q5 什么场景该用主从+哨兵？什么场景该用 Cluster？</summary>

数据量在单机内存承受范围（一般 < 30GB）+ 需要读扩展和自动故障转移 → 主从 + 哨兵，架构简单运维成本低。数据量超过单机上限、或写 QPS 也需要水平扩展 → 上 Cluster 做分片。两者*不共存*：Cluster 自带故障转移，用哨兵反而添乱。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

- （付费专栏，公开的免费版可看题目梗概）

-  —— 集群/主从/哨兵章节

- Redis 官方文档 · Replication

- Redis 官方文档 · High availability with Sentinel

- Redis 官方文档 · Cluster specification

- GitHub · antirez 解释为什么是 16384 个 slot

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

**阶段八 · Spring**：Lesson 0060 **Spring 概览 & 常见面试题** —— Redis 阶段收官，从此进入 Java 后端最热的框架章节。会先俯瞰整个 Spring 生态（Spring Framework / Spring Boot / Spring Cloud 的关系），再切入 IoC、AOP、Bean 生命周期这些必考题。

💬 阶段七收尾了！关于主从复制的 offset 机制、哨兵的 Raft 类选举细节、Cluster 的 gossip 协议实现，或者「线上真实运维过 Redis 集群翻车经历」的追问，都可以直接抛给我。下一课我们就翻篇进 Spring 了。


