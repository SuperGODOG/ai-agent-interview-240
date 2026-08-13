> Lesson 0055 · 阶段七 · Redis · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 8 个追问

# 0055 · Redis 持久化：RDB & AOF & 混合

Redis 号称「内存数据库」，跑得快是因为一切都在内存里。**可一旦机器宕机、进程被 kill、断电，内存全清空 —— 你的数据就消失了**。持久化就是给这颗跳动的心脏一根救命稻草：让重启后能把数据恢复回来。

这一课覆盖的全部核心内容。面试极高频题：**「RDB 和 AOF 有什么区别？」「生产环境 Redis 你怎么配持久化？」「BGSAVE 的原理讲讲？」「AOF 重写为什么不是简单去重？」**—— 这些问题几乎每场 Redis 面试都会碰到，答不上来就会被判定为「只会用 API 不懂原理」。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 RDB 和 AOF 有什么区别？如果只让你选一个用你选哪个？</summary>

RDB 是*数据快照*（定期把内存 dump 成二进制文件），AOF 是*命令日志*（把每条写命令追加到文本文件）。RDB 文件小恢复快但可能丢较多数据；AOF 数据完整但文件大恢复慢。生产环境通常两个都开 —— 用 **混合持久化**（Redis 4.0+）取两者之长。第 8 题细讲。

</details>

<details>

<summary>Q0.2 `BGSAVE` 命令执行时，Redis 主线程会阻塞吗？</summary>

不会（几乎）。`BGSAVE` 通过 `fork()` 出一个子进程去写 RDB，父进程继续处理请求。*但 `fork()` 本身是阻塞操作* —— 内存越大阻塞越久（10GB 数据可能阻塞几百 ms）。这是 RDB 最大的性能坑。第 3 题详解。

</details>

## 面试场景 1：Redis 为什么需要持久化？

🎤 面试官

Redis 是内存数据库，那持久化是干嘛的？为什么要持久化？

🧑‍💻 你

Redis 的数据完全在内存里 —— 速度快是因为不落盘。但内存有个致命弱点：**断电、宕机、进程被 kill，数据全丢**。持久化就是把内存数据周期性写到磁盘，解决三件事：

1. **崩溃恢复**：Redis 重启后能加载磁盘文件把数据恢复回来，而不是从空缓存重跑一遍所有请求（那会瞬间打穿后端 DB —— 就是「缓存雪崩」）。

2. **数据备份**：定期把 `dump.rdb` 拷到别的机器/对象存储，做异地容灾。

3. **主从复制的基础**：主库通过 `BGSAVE` 生成 RDB 快照传给从库做*全量同步*，这是主从架构的启动步骤。

Redis 提供三种持久化方案：**RDB（快照）、AOF（命令日志）、混合持久化（RDB + AOF）**。生产环境几乎一定要开持久化，只有*纯缓存场景*（数据丢了也无所谓，从 DB 重建）才可以关。

追问 Redis 宕机后到底能恢复到什么程度？

完全取决于你的持久化配置：**只 RDB** → 恢复到最后一次快照，可能丢几分钟数据；**只 AOF 且 `appendfsync everysec`** → 最多丢 1 秒数据；**混合持久化** → RDB 快照 + AOF 增量，最多丢 1 秒且恢复速度快（读 RDB 只要几秒，纯 AOF 要几十秒）；**没开持久化** → 全丢。所以生产环境标准答案是混合持久化。

## 面试场景 2：RDB 是什么？怎么触发？（★核心）

🎤 面试官

介绍一下 RDB 持久化，它是怎么触发的？

🧑‍💻 你

**RDB（Redis Database）**是把某个时间点的内存数据完整*拍个照*，压缩成二进制文件（默认 `dump.rdb`）。理解成「定期给内存拍快照存档」。

触发方式有三种：

- **`SAVE`（同步）**：主线程直接写 RDB，*整个过程阻塞*所有客户端请求。生产禁用 —— 大内存下能卡几秒到几十秒。

- **`BGSAVE`（后台）**：`fork()` 一个子进程去写 RDB，父进程继续服务。*只在 fork 那一瞬间短暂阻塞*。生产用这个。

- **自动触发**：`redis.conf` 里配置 `save M N` —— M 秒内至少 N 个 key 变化就自动执行 `BGSAVE`。

典型的默认配置：

```
save 3600 1       # 3600s（1 小时）内 >= 1 个 key 变化 → BGSAVE
save 300 100      # 300s（5 分钟）内 >= 100 个 key 变化 → BGSAVE
save 60 10000     # 60s（1 分钟）内 >= 10000 个 key 变化 → BGSAVE
```

三行条件*只要满足一条*就触发。这个策略的思路：变化少就慢慢存（省 IO），变化多就赶紧存（少丢数据）。

陷阱 **永远不要在生产环境执行 `SAVE` 命令**。哪怕只是排查问题时手动敲一下，如果内存有几个 G，主线程会阻塞十几秒，期间所有客户端请求超时 —— 上游服务连锁雪崩。要手动触发，用 `BGSAVE`。

## 面试场景 3：BGSAVE 的原理 —— fork + Copy-On-Write（★核心）

🎤 面试官

`BGSAVE` 说是「不阻塞」，那它怎么保证子进程和父进程看到的数据一致？内存不是父子共享吗，父进程写数据会不会污染快照？

🧑‍💻 你

这里的关键是 Linux 的 **`fork()` + Copy-On-Write（写时复制）** 机制：

1. **fork 瞬间**：内核创建子进程，*不复制物理内存*，而是让子进程和父进程共享同一份物理页 —— 但只复制页表（虚拟地址映射）。所以 fork 很快也很省内存。

2. **子进程遍历数据集**：把当前内存里的所有键值序列化写入新的 RDB 临时文件，写完 `rename` 覆盖旧 `dump.rdb`。

3. **父进程继续处理请求**：如果父进程要修改某个内存页，内核触发 *页错误*，把那一页复制一份（COW），父进程改新页，*子进程还看到旧页*。这样保证 RDB 快照是「fork 那一刻的一致性视图」。

所以 RDB 的一致性来自 OS 内核的 COW 机制，不是 Redis 应用层做的。这也是为什么 Redis 在 Linux 上跑得最好 —— Windows 上没有 fork。

追问 fork 到底会阻塞多久？为什么大内存 fork 慢？

`fork()` 虽然不复制物理内存，但要**复制页表**。每 4KB 的物理内存对应一个页表项，10GB 内存 ≈ 2.6M 个页表项 ≈ 20MB 页表数据 —— 复制这么多页表就是几百 ms 的 CPU 开销，主线程期间无法响应请求。数据集越大 fork 越慢：< 1GB 通常 < 10ms；1-10GB 可能 10-100ms；> 50GB 可能超过 1s。所以大内存实例要么加从库分担、要么用 Redis Cluster 分片，别让单实例超过 10GB。

追问 fork 之后子进程崩了怎么办？

子进程崩溃父进程会收到 `SIGCHLD` 信号并回收资源，本次 `BGSAVE` 失败（RDB 落空），但*不影响 Redis 服务*；下次到达自动触发条件或客户端再发 `BGSAVE` 时会重试。`INFO persistence` 里 `rdb_last_bgsave_status` 会显示 `err`，运维需要监控这个字段告警。

陷阱：THP（透明大页） Linux 默认可能开启 THP —— 把内存页从 4KB 合并成 2MB。*灾难性影响*：客户端改 10 字节，COW 会复制整个 2MB 页 —— 内存放大 512 倍，容易 OOM。**Redis 部署第一件事：关掉 THP**：`echo never > /sys/kernel/mm/transparent_hugepage/enabled`。Redis 启动日志里也会明确警告这一点。

## 面试场景 4：AOF 是什么？（★核心）

🎤 面试官

AOF 呢？它和 RDB 有什么本质不同？

🧑‍💻 你

**AOF（Append Only File）**换了一个思路：不存*数据*，存*写命令*。每来一条写命令（`SET`、`DEL`、`INCR` 等），就把命令本身以 RESP 协议格式追加到 AOF 文件末尾。重启时 Redis 把 AOF 里的命令*重放一遍*就能恢复数据。

类比：**RDB 像定期给硬盘拍全盘镜像，AOF 像 MySQL 的 binlog —— 记录每一次操作**。

AOF 的工作流程有 5 步：

1. **append（追加）**：命令执行后追加到 AOF 缓冲区（`aof_buf`，内存里的一段字节流）。

2. **write（写入）**：把缓冲区数据通过 `write()` 系统调用交给 OS 内核缓冲区。*此时数据还在内核 page cache，没落盘*。

3. **fsync（同步）**：根据 `appendfsync` 策略调用 `fsync()` 让内核把 page cache 刷到磁盘 —— **这一步才算真正持久化**。

4. **rewrite（重写）**：AOF 文件会越写越大，定期压缩重写。

5. **load（加载）**：Redis 启动时逐条重放 AOF 恢复数据。

开启 AOF 只要一行配置：`appendonly yes`。默认文件名 `appendonly.aof`。

追问 AOF 为什么是*命令执行后*再记录，不是先记录再执行？

Redis 选择「执行后记录」有两个好处：**避免语法检查开销**（不用先解析命令再执行）、**不阻塞命令返回**。代价是：如果命令执行完还没写 AOF 就宕机，这条命令会丢；下一条命令依赖它时会因为 AOF 落后而看不到最新状态。这个取舍是「性能优先，接受极端场景的少量丢失」—— 相比 MySQL 的「redo log 先写后执行（WAL）」是不同的设计哲学。

## 面试场景 5：AOF 三种刷盘策略 `appendfsync`（★背下来）

🎤 面试官

AOF 的 `appendfsync` 有几种策略？各自的取舍是什么？

🧑‍💻 你

三种策略，是一个典型的「性能 vs 数据安全」滑块：

策略时机丢数据风险性能影响适用场景

`always`
每条命令都 `fsync`
几乎不丢（当前命令保证已落盘才返回）
**最差**：QPS 可能只有几千
金融、订单等极端敏感场景

`everysec`（默认，**推荐**）
后台线程每秒 `fsync` 一次
最多丢 1 秒（极端场景 2 秒）
基本无影响，主流写 QPS 稳定 10w+
**绝大多数生产环境**

`no`
由 OS 决定（Linux 默认 30 秒）
可能丢 30 秒或更多
最好（Redis 完全不管 fsync）
缓存场景，数据丢了无所谓

🧑‍💻 你（续）

面试标准答案：**生产环境用 `everysec`**。它由 *bio 后台线程*做 fsync，主线程只负责 `write` 到内核缓冲区，性能几乎无损；最多丢 1 秒数据在绝大多数业务里是可接受的。

陷阱：everysec 不总是「最多丢 1 秒」 当磁盘 IO 极度繁忙、上次后台 `fsync` 卡了超过 2 秒还没完成，Redis 主线程会**强制阻塞**等待 fsync 完成 —— 这是 Redis 源码里的保护逻辑，防止 AOF 缓冲区无限堆积。极端场景下能丢*约 2 秒*的数据。要监控 `INFO persistence` 里的 `aof_delayed_fsync` 计数器，非 0 说明磁盘性能不足。

## 面试场景 6：AOF 重写机制（BGREWRITEAOF）

🎤 面试官

AOF 文件不是会越写越大吗？怎么控制？

🧑‍💻 你

是的，比如对同一个 key 做 100 次 `INCR`，AOF 就存 100 条命令 —— 但恢复时其实只需要一条 `SET key 100`。所以 Redis 有 **AOF 重写**机制来压缩文件。

触发方式：

- **手动**：`BGREWRITEAOF` 命令。

- **自动**：满足 `auto-aof-rewrite-percentage 100` +`auto-aof-rewrite-min-size 64mb` 两个条件（*当前 AOF 大小相比上次重写后至少增长 100%，且至少 64MB*）。

重写*不是*去读旧 AOF 文件做去重 —— 那样又慢又不准。真正的做法是：

1. **fork 子进程**：和 `BGSAVE` 一样 fork（同样有 COW 开销）。

2. **子进程读当前内存状态**：遍历所有 key，为每个 key 生成能重建它的*最少命令集*，写入新 AOF 文件。

3. **父进程双写**：期间新来的写命令一边写老 AOF（保证不中断持久化），一边追加到*AOF 重写缓冲区*。

4. **合并**：子进程写完，父进程把重写缓冲区里的增量命令追加到新 AOF 尾部，然后 `rename` 覆盖旧文件。

本质：**用「当前内存快照」代替「历史命令日志」** —— 从头执行历史那 100 条 `INCR`，不如直接一条 `SET key 100` 来得干净。

追问 AOF 重写为什么不是「读 AOF 去重」？

三个原因：**不准**（TTL 过期的 key、被 `DEL` 的 key 都要判断，逻辑复杂）；**慢**（要重新解析整个大文件）；**没必要**（内存里已经有最终状态，直接读内存生成命令更快更准）。所以设计上就是「以当前内存为准」，AOF 只是产物。

追问 Redis 7.0 的 AOF 有什么变化？（Multi-Part AOF）

Redis 7.0 引入 **Multi-Part AOF**：把一个 AOF 拆成多个文件 —— `BASE`（基础文件，由重写产生）+ 若干 `INCR`（增量文件）+ `HISTORY`（重写完自动删）+ 一个 `manifest` 元数据文件。*核心好处*：重写期间新命令直接写新 `INCR` 文件，不再需要「AOF 重写缓冲区」在内存里堆积，也不再有「重写完成后追加缓冲区」这一步 —— **消除了重写期间的双写和内存开销**。缺点：多了 `manifest` 单点，损坏会导致恢复失败，要单独备份。默认目录 `appenddirname appendonlydir`。

## 面试场景 7：RDB vs AOF 完整对比（★背下来）

维度RDBAOF

存储形式二进制数据快照文本命令日志（RESP 协议）
文件大小**小**（压缩 + 只存最终值）大（每条命令追加）
恢复速度**快**（秒级，直接解析二进制）慢（分钟级，逐条重放命令）
数据完整性差（可能丢几分钟）**好**（`everysec` 最多丢 1 秒）
性能开销fork 时一次性阻塞持续 write/fsync IO
可读性差（二进制，看不懂）**好**（文本，能 `tail -f`）
误操作恢复难（只能回到上次快照）**易**（删掉误操作命令后重启）
版本兼容差（二进制格式跨大版本可能不兼容）好（命令格式稳定）
校验和有（CRC64）无（逐条解析验证）
典型用途冷备份、主从全量同步崩溃恢复、避免丢数据

🧑‍💻 你

一句话总结：**RDB 是*空间和恢复速度*最优，AOF 是*数据完整性*最优**。两者不是二选一 —— 生产环境两个都开，用*混合持久化*取长补短，下一场景细说。

## 面试场景 8：混合持久化（Redis 4.0+，★核心）

🎤 面试官

那生产环境到底怎么配持久化？纯 RDB 还是纯 AOF？

🧑‍💻 你

都不是。生产标准是 **混合持久化（Mixed Persistence，Redis 4.0+）**。开启方式：

```
appendonly yes
aof-use-rdb-preamble yes     # Redis 7.0+ 默认已是 yes
```

它把 RDB 和 AOF 结合成一个文件，结构长这样：

```
┌─────────────────────────────────┐
│   RDB 快照部分（二进制 + CRC64）  │ ← AOF 重写触发时生成
├─────────────────────────────────┤
│   AOF 增量命令（RESP 文本）       │ ← 重写后新来的写命令追加
└─────────────────────────────────┘
```

工作原理：**AOF 重写**触发时，子进程不再生成命令文本，而是把当前内存以 RDB 二进制格式写入新 AOF 文件的开头；重写完成后新来的命令继续以 AOF 命令格式追加在后面。恢复时先读 RDB 部分（*快*），再重放后面的 AOF 增量命令（*准*）。

两个好处一起拿到：

- **恢复快**：RDB 部分直接解析二进制，1GB 数据集 SSD 上大概 2-5 秒；纯 AOF 要 30-60 秒。

- **数据完整**：AOF 增量部分保证最多丢 1 秒（配合 `appendfsync everysec`）。

缺点：RDB 部分不可读（二进制），需要 CPU 做 RDB 压缩/解压。但相比收益微不足道。**Redis 7.0 已经把 `aof-use-rdb-preamble` 默认改成 yes**，说明官方也把它当作标准配置。

追问 怎么快速判断一个 AOF 文件是不是混合持久化格式？

看文件头前 5 个字节。混合持久化的 AOF 文件*开头是 RDB 的 magic number*：`REDIS`（5 个 ASCII 字符）。用 `head -c 5 appendonly.aof` 输出 `REDIS` 就是混合；输出 `*3\r\n` 之类的 RESP 协议就是纯 AOF。也可以 `redis-cli CONFIG GET aof-use-rdb-preamble` 查配置。

## 面试场景 9：持久化对性能的影响

🎤 面试官

开启持久化会不会拖慢 Redis？具体哪些点影响性能？

🧑‍💻 你

会有影响，但可控。分三块：

1. **RDB fork 阻塞**：`BGSAVE` 那一刻，fork 复制页表阻塞主线程。10GB 数据大约 100 ms，50GB 可能超过 1 秒 —— 期间所有客户端请求延迟飙升。对策：控制单实例内存 < 10GB，或用 Redis Cluster 分片。

2. **AOF 写入 IO**：

- `everysec`：后台线程 fsync，通常 < 1ms，主线程基本无感。

- `always`：每条命令同步落盘，QPS 从 10w 掉到几千 —— *只有金融强一致场景才考虑*。

- `no`：完全不管，性能等同关 AOF。

3. **fsync 阻塞主线程**：极端场景下磁盘 IO 卡住，`everysec` 的后台 fsync 超过 2 秒没完成，主线程会强制阻塞等它 —— 表现为客户端*突然*批量超时。有个参数可缓解：`no-appendfsync-on-rewrite yes`，AOF 重写期间暂停主线程 fsync（*性能优先，接受可能丢更多数据*）；默认是 `no`（安全优先）。

还要监控 `latency` 相关指标：`redis-cli --latency`、`INFO latencystats`、`SLOWLOG` 都能看到持久化引起的抖动。

追问 内存写满时会不会 fork 失败？

会。`fork()` 需要额外内存放页表（虽然物理页共享，但 COW 会逐渐消耗内存）。如果 Redis 用了 30GB，OS 只有 32GB 且没配 swap，fork 时内核可能*直接拒绝*（`ENOMEM`）或触发 OOM Killer 把 Redis 杀掉。*Linux 上要开 `vm.overcommit_memory = 1`*，让内核允许「乐观分配」—— 因为大多数 COW 页永远不会被真的复制。Redis 启动日志里也会明确警告这个参数。

## 面试场景 10：主从复制和持久化的关系

🎤 面试官

Redis 主从复制会用到 RDB 或 AOF 吗？关闭持久化会影响主从吗？

🧑‍💻 你

会用到 **RDB**，但和用户配置的持久化是*独立的两条链路*。

**全量同步流程**（从库首次连主库或复制断连很久）：

1. 从库发 `PSYNC ? -1` 请求全量同步。

2. 主库触发一次 `BGSAVE`，fork 子进程生成 RDB。

3. RDB 通过网络传给从库。

4. 期间主库把新写命令暂存到 *replication backlog buffer*（复制积压缓冲区，环形队列）。

5. 从库加载 RDB 后，主库把 backlog 里的增量命令补给它。

**增量同步**（复制断连后短时间重连）：从库带上上次的复制偏移量 `PSYNC replid offset`，主库如果发现该偏移量还在 backlog 里，只补发这段增量即可，*不用重新 BGSAVE*。

关键区分：**持久化的 RDB/AOF 用于崩溃恢复，主从的 RDB 用于复制** —— 是两个独立机制，各走各的。就算你关掉持久化（`save ""`），主从复制该 `BGSAVE` 还是会 `BGSAVE`。

追问 主从同步时 backlog 不够会怎样？

触发**全量同步** —— 主库要重新 `BGSAVE` 传整份 RDB，大内存实例开销极大（fork 慢 + 网络传输大 + 从库加载慢），期间主库性能明显下降。*预防*：把 `repl-backlog-size` 从默认 1MB 调大到 100MB 或更大，让短时间断连能走增量同步。评估公式：`backlog 大小 ≥ 主库每秒写字节数 × 从库断连能容忍的秒数`。

陷阱：主库关持久化 + 自动重启 = 数据全丢 如果*主库关闭持久化*且开启自动重启（如 systemd），主库宕机重启后是**空数据** —— 从库看到主库变空会跟着全量同步覆盖成空。生产铁律：**主库要么开持久化，要么关自动重启（让运维手动介入切主）**。

## 💻 代码验证（打开 `redis-cli` 跑一遍）

### 验证 1：`redis.conf` 生产推荐配置（混合持久化）

```
# ========== 持久化路径 ==========
dir /var/lib/redis                       # RDB/AOF 存放目录

# ========== RDB 配置 ==========
save 3600 1                              # 1h 内 1 个 key 变化触发 BGSAVE
save 300 100                             # 5min 内 100 个 key 变化触发
save 60 10000                            # 1min 内 10000 个 key 变化触发
rdbchecksum yes                          # RDB 文件写 CRC64 校验和
dbfilename dump.rdb                      # RDB 文件名

# ========== AOF 配置 ==========
appendonly yes                           # 开启 AOF
appendfilename "appendonly.aof"          # AOF 文件名
appendfsync everysec                     # 推荐：每秒 fsync

# ========== 重写策略 ==========
auto-aof-rewrite-percentage 100          # AOF 相比上次重写增长 100% 触发
auto-aof-rewrite-min-size 64mb           # 至少 64MB 才触发
no-appendfsync-on-rewrite no             # 重写期间仍 fsync（安全优先）

# ========== 混合持久化 ==========
aof-use-rdb-preamble yes                 # Redis 4.0+ 混合持久化

# ========== 容灾 ==========
aof-load-truncated yes                   # AOF 尾部损坏时自动截断继续启动
```

### 验证 2：手动触发和查看持久化状态

```
# 手动触发 RDB（后台）
127.0.0.1:6379> BGSAVE
Background saving started

# 查看上次 RDB 保存时间戳
127.0.0.1:6379> LASTSAVE
(integer) 1723892100

# 手动触发 AOF 重写
127.0.0.1:6379> BGREWRITEAOF
Background append only file rewriting started

# 查看持久化详细信息
127.0.0.1:6379> INFO persistence
# Persistence
loading:0
rdb_changes_since_last_save:5
rdb_bgsave_in_progress:0
rdb_last_save_time:1723892100
rdb_last_bgsave_status:ok
rdb_last_bgsave_time_sec:0
rdb_last_cow_size:589824              # 上次 BGSAVE 的 COW 内存开销
aof_enabled:1
aof_rewrite_in_progress:0
aof_last_rewrite_time_sec:-1
aof_current_size:2048
aof_base_size:1024
aof_delayed_fsync:0                   # ← 关注这个，非 0 说明磁盘慢
```

### 验证 3：查看 AOF 文件内容（体会「命令日志」是什么样）

```
# 前置：先执行几条写命令
127.0.0.1:6379> SET name alice
127.0.0.1:6379> INCR counter
127.0.0.1:6379> LPUSH todo "learn redis"

# 查看 AOF 文件（纯 AOF 格式，RESP 协议）
$ cat appendonly.aof
*2
$6
SELECT
$1
0
*3
$3
SET
$4
name
$5
alice
*2
$4
INCR
$7
counter
*3
$5
LPUSH
$4
todo
$11
learn redis

# 说明：*N 是数组长度，$N 是字符串字节数，\r\n 分隔
# 每条命令就是一个 RESP 数组，追加到文件末尾
```

### 验证 4：验证是否开启了混合持久化

```
# 方法 1：看配置
127.0.0.1:6379> CONFIG GET aof-use-rdb-preamble
1) "aof-use-rdb-preamble"
2) "yes"

# 方法 2：看 AOF 文件头
# 触发一次重写让混合持久化格式生效
127.0.0.1:6379> BGREWRITEAOF

# 等重写完成后查看文件头
$ head -c 5 appendonly.aof
REDIS                    # ← 输出 REDIS 说明是混合持久化
#   （纯 AOF 会输出 *2\r\n 之类）

# 也可以用 file 命令
$ file appendonly.aof
appendonly.aof: Redis RDB file, version 11
```

### 验证 5：AOF 文件损坏的修复（工具演示）

```
# 模拟：AOF 尾部被截断（比如宕机时 fsync 未完成）
$ echo "GARBAGE_DATA" >> appendonly.aof

# 直接启动 Redis 会失败（如果 aof-load-truncated no）
$ redis-server /etc/redis/redis.conf
# Bad file format reading the append only file:
# make a backup of your AOF file, then use ./redis-check-aof --fix <filename>

# 用官方工具修复（会从错误位置截断）
$ redis-check-aof --fix appendonly.aof
0x              1234:   Expected \r\n, got: 4741
AOF analyzed: size=4660, ok_up_to=4660, diff=13
This will shrink the AOF from 4673 bytes, with 13 bytes, to 4660 bytes
Continue? [y/N]: y
Successfully truncated AOF                 # ← 修复成功

# 原文件已备份为 appendonly.aof.broken
$ ls -la appendonly.aof*
-rw-r--r-- 1 redis redis 4660 appendonly.aof
-rw-r--r-- 1 redis redis 4673 appendonly.aof.broken
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话说清 RDB 和 AOF 的本质区别，以及生产环境应该怎么选。</summary>

RDB 存*数据快照*（二进制），AOF 存*命令日志*（文本）。生产环境标准是开**混合持久化**（`appendonly yes` + `aof-use-rdb-preamble yes`）+ `appendfsync everysec`，兼得 RDB 的快恢复和 AOF 的数据完整。

</details>

<details>

<summary>Q2 `BGSAVE` 说是「后台执行不阻塞」，那它到底会不会阻塞主线程？为什么？</summary>

会短暂阻塞。`BGSAVE` 通过 `fork()` 创建子进程，*fork 那一瞬间需要复制父进程的页表*（不是数据），阻塞主线程；页表大小和内存大小成正比 —— 10GB 内存约阻塞 100ms，50GB 可能超过 1 秒。fork 完成后子进程独立写 RDB，父进程恢复响应请求。

</details>

<details>

<summary>Q3 `appendfsync everysec` 一定「最多丢 1 秒数据」吗？什么场景会丢更多？</summary>

不一定。当磁盘 IO 极度繁忙、后台 `fsync` 超过 2 秒还没完成，主线程会强制阻塞等 fsync；这种场景可能丢*约 2 秒*数据。要监控 `INFO persistence` 里的 `aof_delayed_fsync` 计数器，非 0 说明磁盘性能不足需要换 SSD 或降 QPS。

</details>

<details>

<summary>Q4 AOF 重写为什么不是「读旧 AOF 去重」？</summary>

因为「读内存生成最小命令集」*更准更快*：内存里已经是最终状态，遍历所有 key 生成能重建它的最少命令即可；不需要处理 TTL 过期、`DEL` 等复杂逻辑，也不需要重新解析大文件。重写期间新来的命令会走「AOF 重写缓冲区」，重写完成后合并到新 AOF（Redis 7.0 的 Multi-Part AOF 优化掉了这个缓冲区）。

</details>

<details>

<summary>Q5 Redis 主库关闭持久化 + 开启自动重启，为什么危险？</summary>

主库宕机重启后是**空数据集**；从库看到主库变空会触发全量同步*把自己也覆盖成空* —— 集群数据全部丢失。铁律：主库要么开持久化，要么关自动重启（让运维手动 `failover` 到某个数据完整的从库上）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Redis 官方文档 · Persistence —— RDB/AOF 权威描述

- Redis 官方 · BGSAVE 命令

- Redis 官方 · BGREWRITEAOF 命令

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0056：**缓存三兄弟 —— 缓存穿透、缓存击穿、缓存雪崩**。持久化解决「Redis 自己的数据不丢」，三兄弟解决「Redis 之外的 DB 不被打爆」—— 是 Redis 章节的下一个必背高频题。

💬 有任何疑问 —— 「fork 到底怎么算阻塞时间？」「AOF 重写缓冲区满了会怎样？」「面试问到 Redis 7.0 Multi-Part AOF 怎么答得让人眼前一亮？」—— 直接问我。我是你的老师，也是你的追问陪练。


