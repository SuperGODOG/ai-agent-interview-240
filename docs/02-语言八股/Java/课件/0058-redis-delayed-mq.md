> Lesson 0058 · 阶段七 · Redis · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0058 · Redis 延时任务 & Stream & 分布式锁

Redis 除了做缓存，在后端还承担着三个高频角色：**延时任务**（订单 30 分钟自动取消、优惠券到期回收）、**轻量消息队列**（业务日志、异步通知）、**分布式锁**（防止秒杀超卖、分布式定时任务只跑一份）。这一课把这三块合并讲 —— 面试里它们经常混着问「你们用 Redis 做过什么？」，你得能一口气把三条链路讲清楚。

本课主源： + ，分布式锁的部分是 Redis 面试的经典必考，一并补齐。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 用 Redis 做延时任务，你能想到几种方案？</summary>

至少三种：① `keyspace notification` 监听 key 过期事件（不可靠，不推荐）；② `Sorted Set` 用到期时间戳做 score，轮询捞取（生产常用）；③ Redisson 的 `RDelayedQueue`（封装好的 ZSet 方案）。第 1-3 场景展开。

</details>

<details>

<summary>Q0.2 Redis Stream 相比 Kafka 差在哪？为什么还要用它？</summary>

吞吐差一个数量级（十万 vs 百万 QPS），持久化弱（依赖 RDB/AOF，可能丢秒级数据），无分区并行。但它「不需要引入新组件」—— 已有 Redis 就够了，对轻量业务是最省事的选择。第 5、7 场景讲。

</details>

## 面试场景 1：Redis 实现延时任务的三种方案

🎤 面试官

订单 30 分钟不支付就自动取消，你用 Redis 怎么实现？

🧑‍💻 你

Redis 做延时任务有三种主流方案，按可靠性从低到高：

1. **过期回调（keyspace notification）**：给每个订单设一个 key `order:1001`，`EXPIRE 1800`；订阅 `__keyevent@0__:expired` 频道，key 过期时收到通知去关单。*缺点：不可靠*，后面追问细讲。

2. **Sorted Set + 到期时间戳 score**：`ZADD delay_queue <到期时间戳> order:1001`；后台线程轮询 `ZRANGEBYSCORE delay_queue 0 <now> LIMIT 0 1`，捞到就处理并 `ZREM` 删掉。*生产推荐*。

3. **Redisson RDelayedQueue**：把 ZSet 方案封装成了 Java API，用起来像 JDK 的 `DelayQueue`，底层原理和第二种一样，但省去了轮询、原子性、分布式竞争的手写代码。*Java 项目最推荐*。

三选一的话，看团队：手写方案维护性高 → 用 ZSet；不想造轮子 → 直接 Redisson。

追问 keyspace notification 为什么不可靠？

三个致命问题：① **时效性差**：Redis 的过期策略是「惰性删除 + 定期删除」—— key 过期时间到了但没被访问、也没轮到定期删除扫到，事件就*不会立即发出*；订单可能过期 5 分钟后才触发。② **Pub/Sub 无持久化**：如果订阅者进程挂了或网络断了，这段时间的过期事件*直接丢失*，恢复后无法补齐。③ **广播模式**：多个消费者实例订阅同一个频道会*全部收到*，需要自己做幂等和抢占，处理起来很麻烦。所以  明确不推荐生产用。

追问 为什么 Sorted Set 方案是生产首选？

三个原因：① **持久化**：ZSet 存在 Redis 里，跟着 RDB/AOF 一起落盘，重启不丢。② **可控**：轮询频率、批量大小、消费者数量都自己定，出问题好排查。③ **幂等好做**：捞取后 `ZREM` 删除，天然的「消费一次」语义（配合原子性处理，见场景 2）。

## 面试场景 2：Sorted Set 方案的原子性问题

🎤 面试官

你说的 ZSet 方案，轮询 → 处理 → 删除三步，多个消费者同时跑，会不会重复消费？

🧑‍💻 你

会。三步非原子：`ZRANGEBYSCORE`（查）→ 业务处理 → `ZREM`（删）。两个消费者可能同时 `ZRANGEBYSCORE` 到同一个 key，导致*重复消费*。解决方案有两种：

1. **`ZPOPMIN`（Redis 5.0+ 推荐）**：*原子*弹出 score 最小的元素。只要检查弹出的元素 score 是否 ≤ 当前时间戳，就是「到期任务」。多个消费者调用不会重复。

2. **Lua 脚本**：把「查 + 删」封装成一个 Lua 脚本，Redis 保证脚本执行原子性。适合复杂逻辑（如批量捞取 + 条件判断）。

另外还要防「业务失败但已 `ZREM`」—— 可以先 `ZREM` 再处理，失败就重新 `ZADD` 一个稍后的时间；或者引入「处理中集合」做二段消费（类似 Stream 的 PEL 思路）。

陷阱 `BZPOPMIN`（阻塞版）看起来很美，但*不适合延时任务* —— 它阻塞到「有元素」就返回，不管到期没到期。ZSet 里已经有一个还没到期的元素时，`BZPOPMIN` 立刻返回它，你还得判断时间戳 + 塞回去，反而更复杂。老老实实短轮询 `ZPOPMIN` + 判断 score 就好。

## 面试场景 3：Redis 延时方案 vs 其他生产延时方案

🎤 面试官

除了 Redis，还有哪些常见的延时任务方案？各自适合什么场景？

方案核心机制可靠性性能适用场景

`DelayQueue`（JDK）
无界优先级队列 + 小根堆
差（进程内存，宕机全丢）
高（单机 O(log n)）
单机、任务可丢失（如缓存刷新）

时间轮（Netty `HashedWheelTimer`）
环形数组 + tick 推进
差（同 DelayQueue）
极高（O(1) 添加）
单机海量短周期定时（心跳、超时）

Redis ZSet
分数排序 + 轮询捞取
中（RDB/AOF 可能丢秒级）
中（万级 QPS）
分布式、任务量中等（订单超时）

RocketMQ 定时消息
MQ 内置延时级别 / 任意时间
高（磁盘持久化 + 主从）
高（十万 QPS）
*生产推荐*：高可靠 + 分布式

数据库轮询
定时扫描 `expire_at < now`
高（DB 持久化）
低（拖 DB）
小流量兜底、审计

选型口诀：**单机短任务用时间轮 → 分布式中量用 Redis → 分布式高可靠用 MQ**。`DelayQueue` 详见 。

追问 RocketMQ 定时消息为什么比 Redis 延时更可靠？

三点：① **刷盘策略可选**，同步刷盘保证消息落盘再返回成功；② **主从架构**，主节点挂了从节点自动接管，消息不丢；③ **消费 ACK + 重试队列**，消费失败会自动重试、达到最大次数进入死信队列，不会像 Redis ZSet 那样「一 `ZREM` 就没了」。代价是要额外部署一套 MQ 集群。

## 面试场景 4：Redis 5 之前用什么做消息队列？为什么后来引入 Stream？

🧑‍💻 你

Redis 5 之前有两种土办法，都不太好用：

1. **List（`LPUSH` / `BRPOP`）**：

- 生产者 `RPUSH myList msg`，消费者 `BRPOP myList 0`（阻塞取）。

- 缺点：*消息弹出即删除，无 ACK*；消费者拿到后崩了消息就丢；*不支持消费组*，一条消息只能被一个消费者处理，想广播得复制多份 List；无法追溯历史消息。

2. **Pub/Sub（`PUBLISH` / `SUBSCRIBE`）**：

- 生产者 `PUBLISH channel msg`，订阅者 `SUBSCRIBE channel`。

- 缺点：*发后即忘*，发布时没有订阅者消息直接丢弃；订阅者掉线期间的消息永久丢失；*无持久化*，Redis 重启后订阅关系全丢。适合广播通知，不适合可靠消息传递。

所以 Redis 5.0 借鉴 Kafka 的设计引入了 **Stream** —— 持久化 + 消费组 + ACK + 消息 ID 追溯，终于像样了。

## 面试场景 5：Stream 是什么？核心概念有哪些 ⭐核心

🧑‍💻 你

Stream 是 Redis 5.0 引入的 **持久化、append-only 的消息日志结构**，参考 Kafka 设计。核心概念有四个：

- **消息 ID**：格式是 `<时间戳ms>-<序列号>`（如 `1625000000000-0`），自增唯一。用 `*` 让 Redis 自动生成，也可手动指定。

- **消费组（Consumer Group）**：一个 Stream 可以有多个消费组，每组独立维护消费位置；*组内多个消费者分担消息*（类似 Kafka 的 Consumer Group）。

- **last_delivered_id**：消费组的游标，记录已经派发到哪条消息；组内任一消费者读取都会推进它。

- **PEL（Pending Entries List）**：*已派发但还没 ACK* 的消息列表；消费者崩了可以通过 `XCLAIM` 让别的消费者接管；这是 Stream 相比 List 的关键升级。

底层数据结构是**基数树（Radix Tree）**而不是链表：因为消息 ID 有前缀重复（同一毫秒生成的 ID 前缀相同），基数树能压缩存储 + 支持范围查询 `XRANGE`。

追问 Stream 的消费组和 Kafka 的消费组有什么区别？

相似之处：都是「组内负载均衡、组间独立消费」。不同之处：① **并行度**：Kafka 靠 Partition 并行（一个消费者独占一个 partition），Stream 是*单 Stream 内多消费者抢消息*，无分区概念，并行度受限。② **消息保留**：Kafka 按 offset 提交，消息按 retention 时间保留；Stream 消息 `XACK` 后*仍留在 Stream 里*，得手动 `XDEL` 或用 `XTRIM MAXLEN` 修剪长度。③ **吞吐**：Kafka 百万 QPS，Stream 十万 QPS 已到顶。

## 面试场景 6：Stream 常用命令速记

命令作用面试要点

`XADD key * field val ...`追加消息`*` 表示自动生成 ID
`XLEN key`消息条数不含已 `XDEL` 的
`XRANGE key - +`范围读取`-` / `+` 表示最小/最大 ID
`XREAD COUNT n STREAMS key id`普通消费（无组）类似 `tail -f`，起始 ID 之后
`XGROUP CREATE key group $`创建消费组`$` 从最新开始；`0` 从头开始
`XREADGROUP GROUP g c COUNT n STREAMS key >`组内消费`>` 表示未派发的新消息
`XACK key group id`确认消息从 PEL 移除
`XPENDING key group`查看 PEL排查未确认的悬挂消息
`XCLAIM key group consumer min-idle id`转移悬挂消息消费者崩了让别人接管
`XDEL key id`删除消息物理删除，不影响 ID 生成
`XTRIM key MAXLEN n`修剪长度限制 Stream 内存占用

## 面试场景 7：Stream vs Kafka / RocketMQ 该怎么选？

维度Redis StreamKafkaRocketMQ

吞吐十万 QPS百万 QPS（分区并行）十万-百万 QPS
延迟亚毫秒毫秒级毫秒级
持久化RDB/AOF，可能丢秒级磁盘原生 + 副本磁盘原生 + 主从
消息堆积受内存限制TB 级磁盘TB 级磁盘
消息回溯按 ID / 时间按 offset按时间
运维成本*无*（复用 Redis）高（依赖 ZK/KRaft）中
顺序保证单 Stream 全局有序partition 内有序队列内有序

结论：Stream 的定位是**「够用就好的轻量方案」**—— 已经用了 Redis，业务 QPS 万级，消息堆积不会超过内存，能容忍极低概率丢消息，就用 Stream；否则老实上专业 MQ。

追问 List 做消息队列相比 Stream 有什么劣势？

四点：① **无 ACK 机制**：`BRPOP` 弹出就删除，消费者崩了消息丢失；Stream 有 PEL 保存已派发未确认的消息。② **无消费组**：List 一条消息只能被一个消费者拿到，想让多个消费组独立消费得复制多份 List；Stream 原生支持消费组，一份数据多组消费。③ **无消息 ID 追溯**：List 无法回放历史消息，Stream 可以 `XRANGE` 按 ID 范围重放。④ **无 `XPENDING` 恢复机制**：消费者宕机后 List 的消息丢了就丢了，Stream 可以查 PEL 让别的消费者用 `XCLAIM` 接管。

## 面试场景 8：Redis 分布式锁的最简实现 ⭐经典

🎤 面试官

秒杀场景要防止超卖，你怎么用 Redis 实现分布式锁？

🧑‍💻 你

最简可用的实现就一行加锁 + 一段 Lua 释放：

```
# 加锁：原子设置 key + 过期时间 + 仅当不存在时设置
SET lock:sku:1001 <random_uuid> EX 30 NX

# 返回 OK   → 加锁成功
# 返回 nil  → 已被别人持有
```

三个参数缺一不可：

- `NX`：*Not eXists*，key 不存在才设置 —— 保证互斥。

- `EX 30`：过期时间 30 秒 —— *防死锁*，持锁进程崩了锁会自动释放。

- `<random_uuid>`：value 存*唯一标识*（如 `UUID`） —— 释放时校验，防止误删别人的锁。

释放锁必须用 Lua 保证原子：

```
-- unlock.lua
if redis.call('get', KEYS[1]) == ARGV[1] then
return redis.call('del', KEYS[1])
else
return 0
end
```

这里 `SET NX EX` 一条命令搞定「加锁 + 过期」；Lua 脚本保证「校验 + 删除」不被其他命令穿插。这是 Redis 分布式锁的*最小正确实现*。

## 面试场景 9：分布式锁的三大坑

🎤 面试官

你上面写的锁看起来简单，但生产上有哪些坑？

🧑‍💻 你

三个经典坑，每个都能挂业务：

1.
**误删别人的锁**

如果释放时直接 `DEL lock:xxx`，会出现：A 持锁 → 业务耗时超过 30s → 锁过期 → B 拿到锁 → A 恢复执行 `DEL` → *把 B 的锁删了*。
解决：加锁时 value 存 uuid，释放时用 Lua 判断 `GET == uuid` 才 `DEL`。

2.
**过期时间不够业务时间**

业务实际跑了 40s，锁 30s 就过期了，别人已经拿到锁并发执行 —— 就算你没误删，业务的*互斥性也已经被破坏*。
解决：**看门狗（Watchdog）**—— 后台线程定期检查持锁进程还活着，就 `PEXPIRE` 续期。Redisson 内置了这个机制。

3.
**Redis 主从切换导致锁丢失**

Redis Cluster 里，客户端在 master 上加锁成功 → master 还没把数据同步到 slave 就挂了 → slave 上位成为新 master → *锁不存在了* → 别人再来加锁能成功，两个客户端同时持锁。
解决：**RedLock 算法** —— 在 N 个独立 master（不是主从！）上都尝试加锁，超过半数（N/2+1）成功且总耗时小于锁过期时间才算加锁成功。

追问 Redisson 的看门狗具体怎么实现的？

Redisson 加锁默认过期时间是 30s。加锁成功后启动一个后台*定时任务*，每隔 `internalLockLeaseTime / 3`（默认 10s）检查一次：如果持锁线程还活着 → 执行 `PEXPIRE lock 30000` 把锁续到 30s；如果线程已释放锁或已死亡 → 取消定时任务。*注意*：只有`lock()` 不传超时时间才会启用看门狗；传了 `lock(10, TimeUnit.SECONDS)` 就*不启用*，到点就过期。

追问 RedLock 有什么争议？

2016 年 Martin Kleppmann 发文《How to do distributed locking》质疑 RedLock：① **依赖时钟**：多台 Redis 实例的系统时钟不同步（NTP 跳变、GC 停顿）会导致锁提前过期；② **GC 停顿**：客户端在 GC 期间可能已经过了锁的有效期还以为自己持锁；③ **fsync 语义**：Redis 默认不同步刷盘，master 崩了消息可能没落盘。
作者 Antirez 反驳这些问题在别的分布式锁方案里也存在。*生产建议*：一般场景用*单实例 Redis + 短业务 + 看门狗*足够；对锁互斥性极其苛刻（如账务）用 Zookeeper 或 etcd 更稳。

## 面试场景 10：为什么生产上推荐用 Redisson？

🧑‍💻 你

手写分布式锁至少要处理五件事：*原子加锁、uuid 校验、Lua 释放、看门狗续期、可重入*。Redisson 已经全都封装好了：

```
Config config = new Config();
config.useSingleServer().setAddress("redis://127.0.0.1:6379");
RedissonClient redisson = Redisson.create(config);

RLock lock = redisson.getLock("myLock");
lock.lock();               // 阻塞加锁 + 看门狗自动续期
try {
// 业务逻辑
} finally {
lock.unlock();         // 可重入减到 0 才真释放
}
```

Redisson 提供的锁类型：

- `RLock`：基础可重入锁（大部分场景）

- `RFairLock`：公平锁（按加锁顺序拿）

- `RReadWriteLock`：读写锁

- `RSemaphore`：分布式信号量

- `RedissonRedLock`：多节点 RedLock 算法（需苛刻场景）

此外 Redisson 还封装了 **`RDelayedQueue` 延时队列**、**`RStream` Stream 客户端**、`RMap`、`RSet` 等 —— Java 后端项目基本就是 Spring Data Redis + Redisson 双客户端组合。

## 💻 代码验证（打开 redis-cli 跑一遍）

### 验证 1：Sorted Set 实现订单延时取消

```
# 生产者：下单，30 分钟后到期
127.0.0.1:6379> ZADD delay_queue 1737963000 order:1001
(integer) 1
127.0.0.1:6379> ZADD delay_queue 1737963120 order:1002
(integer) 1

# 消费者：轮询捞取到期的（假设当前时间戳 1737963050）
127.0.0.1:6379> ZRANGEBYSCORE delay_queue 0 1737963050 LIMIT 0 10
1) "order:1001"

# 处理完删除（Redis 5+ 推荐直接 ZPOPMIN 原子弹出）
127.0.0.1:6379> ZPOPMIN delay_queue
1) "order:1001"
2) "1737963000"     # 弹出的是 score 最小的
# 应用层判断 score <= now 才算「到期」，否则塞回去
```

### 验证 2：Stream 完整生产消费流程

```
# 1. 生产：追加两条消息，* 让 Redis 自动生成 ID
127.0.0.1:6379> XADD orders * order_id 1001 amount 99.9
"1737963000000-0"
127.0.0.1:6379> XADD orders * order_id 1002 amount 88.8
"1737963000001-0"

# 2. 建消费组，从最新位置开始（$ 表示只消费新消息）
127.0.0.1:6379> XGROUP CREATE orders g1 $
OK

# 3. 组内消费：consumer_a 拉一条（> 表示未派发的）
127.0.0.1:6379> XREADGROUP GROUP g1 consumer_a COUNT 1 STREAMS orders >
1) 1) "orders"
2) 1) 1) "1737963000002-0"
2) 1) "order_id"
2) "1003"

# 4. 查未 ACK 的（PEL）
127.0.0.1:6379> XPENDING orders g1
1) (integer) 1
2) "1737963000002-0"
3) "1737963000002-0"
4) 1) 1) "consumer_a"
2) "1"

# 5. 消费者 a 挂了，让 consumer_b 接管 idle > 60000ms 的消息
127.0.0.1:6379> XCLAIM orders g1 consumer_b 60000 1737963000002-0

# 6. 处理完确认
127.0.0.1:6379> XACK orders g1 1737963000002-0
(integer) 1
```

### 验证 3：手写 SET NX EX 分布式锁（redis-cli）

```
# 客户端 A 加锁
127.0.0.1:6379> SET lock:sku:1001 uuid-aaa EX 30 NX
OK

# 客户端 B 同时想加锁 → 失败
127.0.0.1:6379> SET lock:sku:1001 uuid-bbb EX 30 NX
(nil)

# 客户端 A 用 Lua 原子释放（防止误删 B 的锁）
127.0.0.1:6379> EVAL "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end" 1 lock:sku:1001 uuid-aaa
(integer) 1

# 此时 B 可以拿到锁了
127.0.0.1:6379> SET lock:sku:1001 uuid-bbb EX 30 NX
OK
```

### 验证 4：Redisson 分布式锁 + 延时队列（Java）

```
// pom.xml: org.redisson:redisson:3.27.x
Config config = new Config();
config.useSingleServer().setAddress("redis://127.0.0.1:6379");
RedissonClient redisson = Redisson.create(config);

// ---------- 分布式锁 ----------
RLock lock = redisson.getLock("lock:sku:1001");
lock.lock();  // 默认 30s 过期，看门狗自动续期
try {
// 扣库存业务
System.out.println("持锁执行，线程 " + Thread.currentThread().getName());
} finally {
lock.unlock();
}

// ---------- 延时队列 ----------
RBlockingQueue<String> blockingQueue = redisson.getBlockingQueue("order_queue");
RDelayedQueue<String> delayedQueue = redisson.getDelayedQueue(blockingQueue);

// 生产者：30 分钟后订单进入 blockingQueue
delayedQueue.offer("order:1001", 30, TimeUnit.MINUTES);

// 消费者：从 blockingQueue 阻塞取
new Thread(() -> {
while (true) {
try {
String order = blockingQueue.take();  // 阻塞直到有到期任务
System.out.println("处理超时订单: " + order);
} catch (InterruptedException e) {
Thread.currentThread().interrupt();
break;
}
}
}).start();

// 记得 shutdown
Runtime.getRuntime().addShutdownHook(new Thread(redisson::shutdown));
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用 Redis 实现延时任务，为什么不建议用 keyspace notification？</summary>

三个原因：① Redis 过期策略是惰性 + 定期删除，事件不是精确到期就发；② Pub/Sub 无持久化，订阅者掉线消息丢；③ 广播模式多消费者都收到，去重麻烦。生产用 Sorted Set 或 Redisson RDelayedQueue。

</details>

<details>

<summary>Q2 Sorted Set 延时方案下，多个消费者怎么防止重复消费？</summary>

用 `ZPOPMIN`（Redis 5+）原子弹出 score 最小的元素，再判断 score 是否 ≤ 当前时间戳；或用 Lua 脚本把「查 + 删」封装成原子操作。`ZRANGEBYSCORE` + `ZREM` 两步非原子会导致重复。

</details>

<details>

<summary>Q3 Redis Stream 和 List 做消息队列相比，多了哪些核心能力？</summary>

① 消息 ID + 持久化 + 可回溯（`XRANGE`）；② 消费组（多组独立消费）；③ ACK 机制 + PEL 悬挂列表；④ `XCLAIM` 消息转移（消费者崩了让别人接管）。本质上是 Redis 内置的轻量 Kafka。

</details>

<details>

<summary>Q4 Redis 分布式锁 `SET key uuid EX 30 NX` 三个参数各解决什么问题？</summary>

`NX` 保证互斥（不存在才设置）；`EX 30` 防死锁（进程崩了自动释放）；`uuid` 防误删（释放时 Lua 校验 `GET == uuid` 才 `DEL`，避免删掉别人的锁）。释放锁必须用 Lua 保证原子。

</details>

<details>

<summary>Q5 Redisson 的看门狗机制解决了分布式锁的哪个坑？</summary>

解决「业务执行时间 > 锁过期时间」的问题。加锁默认 30s 过期，后台线程每 10s 检查一次持锁线程还活着就 `PEXPIRE` 续到 30s，避免业务还没跑完锁就过期被别人抢走。*注意*：只有 `lock()` 不传超时时间才启用；`lock(10, TimeUnit.SECONDS)` 传了超时就不启用。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

- Redis 官方文档 · Streams —— `XADD`/`XREADGROUP`/`XPENDING` 完整语义

- Redis 官方文档 · Distributed Locks —— RedLock 算法作者 Antirez 的原始描述

- Martin Kleppmann · How to do distributed locking —— 对 RedLock 的经典质疑

- Redisson Wiki —— `RLock` / `RDelayedQueue` / `RStream` API

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0059：**Redis Cluster 集群 & 数据分片 & 主从复制** —— 阶段七 Redis 收尾课，把「16384 槽位怎么分」「分片路由」「哨兵 vs 集群」「持久化 RDB/AOF」一次讲透。

💬 有任何疑问 —— 「ZSet 方案的 QPS 到底能撑多大？」「RedLock 争议到底谁对？」「Stream 的 PEL 超时了怎么办？」—— 直接问我。我是你的老师，也是你的追问陪练。


