> Lesson 0053 · 阶段七 · Redis · ⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0053 · Redis 3 种特殊数据类型：HyperLogLog & Bitmap & Geo

上一课（）我们把 String、List、Hash、Set、ZSet 5 种基本类型盘完了。这一课要看 3 种**「场景特化」类型** —— HyperLogLog、Bitmap、Geo。它们的共同点很有意思：*都不是全新的存储结构，都建立在 String / ZSet 之上*，只是把某个高频场景（UV 去重、签到、附近的人）打包成一组语法糖。

面试官问它们的角度非常固定：**「大数据量去重用什么？」「怎么设计签到系统？」「附近的人怎么实现？」**—— 三个问题分别对应三种类型。答不出来会被认为「只会用 Redis 的 5 种基本类型」，答上来加分很多，因为大部分候选人只熟前 5 种。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 用 Redis 存 1 亿个用户 UV 去重，如果用 `Set` 大概占多少内存？换成 HyperLogLog 呢？</summary>

Set 存 1 亿个 8 字节 long 至少 800MB 起步（加上 hashtable 元数据可能上 GB）；**HyperLogLog 固定 12KB**。差了 5 个数量级。代价是 HLL 只能估算总数，不能反查具体元素，也不能问「某某在不在」。第 4 场景细讲。

</details>

<details>

<summary>Q0.2 Bitmap 适合什么场景？给你 1 亿用户做「昨天是否登录」标记，最省内存的方案是什么？</summary>

Bitmap 适合**元素可以映射成整数下标**、且状态只有 0/1 的场景。1 亿用户 ID 连续时，只要 *1 亿 bit = 12.5 MB*。用户 ID 稀疏（比如自增 ID 中间有大量空洞）就会浪费很多 bit —— 那就得考虑 HyperLogLog 或分片 Bitmap。第 5、7 场景细讲。

</details>

## 面试场景 1：Redis 除了 5 种基本类型还有哪些？

🎤 面试官

你在项目里都用过哪些 Redis 数据类型？除了 String、List、Hash、Set、ZSet，还知道别的吗？

🧑‍💻 你

基本类型之外，Redis 还提供了 3 种「特殊类型」，它们都是在基本类型之上做的算法/编码封装：

类型底层实现典型场景核心卖点

`HyperLogLog`String（稀疏/稠密矩阵）UV/独立 IP 去重统计1 亿元素只要 12KB，标准误差 0.81%
`Bitmap`String 的位操作签到、活跃用户、在线状态1 亿状态只要 12.5MB
`Geo`ZSet + GeoHash 编码附近的人、外卖配送范围用一个 double 表示二维坐标

Redis 5.0 之后还加了 `Stream`（消息队列），6.0 之后有 `RedisJSON`、`RedisSearch` 等模块，但这些通常算「扩展」不算原生特殊类型。这一课重点讲 3 种经典特殊类型。

追问 既然 HyperLogLog 底层是 String，为什么不直接叫「一种 String 用法」而要单独列一种类型？

因为它有**独立的一组命令（PF 开头）**和*严格的数据布局约定（HYLL 魔数头 + 稀疏/稠密编码）*，普通 String 命令（`GET`、`APPEND`）动它就会破坏结构。API 层面独立、语义独立，就当作独立类型看待。Bitmap 更松一些，是纯 String 位操作，所以 `TYPE` 命令返回的还是 `string`。

## 面试场景 2：HyperLogLog 是什么？为什么这么省内存？⭐核心

🎤 面试官

HyperLogLog 是干嘛的？为什么能用 12KB 存 1 亿个元素？

🧑‍💻 你

**HyperLogLog（简称 HLL）是一种概率型基数统计算法**，用*极小的固定内存估算超大集合的不重复元素数量（基数 cardinality）*。它不存元素本身，只维护一组统计指标。

核心思想一句话：**「用哈希值二进制表示里最长的前导 0 个数，反推出集合的基数」**。直觉解释：

- 抛硬币抛出「连续 k 次正面」的概率是 `1/2^k`。反过来：如果你观察到有人连续抛出 20 次正面，你会猜他大概抛了 `2^20` ≈ 100 万次。

- 把元素哈希成均匀分布的 bit 串。哈希值前导 0 越多，说明这个元素越「罕见」，能出现越罕见的元素，说明看过的元素总数越大。

- 用*最大前导 0 数 k* 估算基数 `≈ 2^k`。

单个估算方差太大，HLL 用**分桶平均**降低方差：Redis 里分 `2^14 = 16384` 个桶，每个桶存 6 bit（记录该桶见过的最大前导 0 数）。总内存 = `16384 × 6 / 8 = 12288 字节 ≈ 12KB`。用调和平均和偏差修正得到最终基数。

**标准误差 0.81%**：估算 1 亿，误差在 ±81 万左右。对 UV/PV 场景够用。

追问 HyperLogLog 底层算法叫什么？谁发明的？

就叫 **HyperLogLog 算法**，由法国计算机科学家 *Philippe Flajolet* 等人在 2007 年论文《HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm》里提出。它是 Flajolet 早年 LogLog、SuperLogLog 算法的进化版 —— 「Hyper」意思是「用调和平均代替几何平均，进一步降低方差」。Redis 2.8.9 引入并做了稀疏/稠密两种编码优化。

追问 HyperLogLog 会不会误判某个元素已存在？能问「用户 A 昨天来过没」吗？

**不能**！HLL 只保留统计指标，不保留元素本身，*没有「查询单个元素是否存在」的能力*。它只能回答「昨天大概有多少不同用户来过」。判断某元素在不在，得用 `Set`（精确）或**布隆过滤器**（概率型 + 允许假阳）。别把 HLL 当去重集合用。

陷阱 HLL 的 0.81% 是**相对标准误差**，不是绝对误差。基数 100 时误差约 ±0.81，基数 1 亿时误差约 ±81 万。*基数越大绝对误差越大*，但对做 UV 展示、报表趋势足够。金融、反作弊、账单场景要精确，就别用 HLL。

## 面试场景 3：HyperLogLog 常用命令有哪些？

🧑‍💻 你

HLL 命令统一以 `PF` 开头（致敬发明者 *Philippe Flajolet*），只有 3 个核心命令：

命令作用复杂度

`PFADD key ele [ele ...]`添加元素，内部哈希后更新桶O(1) 每元素
`PFCOUNT key [key ...]`估算基数；多 key 时是并集基数O(1) 单 key，O(N) 多 key
`PFMERGE dest src1 [src2 ...]`把多个 HLL 合并到 dest（并集）O(N) N=key 数

典型用法（统计每日 UV 并按周聚合）：

```
# 用户 u1001 访问了 20260727 这天的站点
PFADD uv:20260727 u1001 u1002 u1003
PFCOUNT uv:20260727                        # → 3（估算）

# 一周 UV 合并（PFMERGE 求并集）
PFMERGE uv:week01 uv:20260721 uv:20260722 uv:20260723 \
uv:20260724 uv:20260725 uv:20260726 uv:20260727
PFCOUNT uv:week01                          # → 一周去重后的 UV
```

追问 `PFCOUNT key1 key2` 会修改数据吗？

会。多 key 的 `PFCOUNT` 内部要在内存里构造一个临时合并 HLL，虽然结果只读，*但可能会缓存中间态到主 HLL*，属于「写命令」—— 从副本执行会被拒绝。别在读多写少的从库跑多 key `PFCOUNT`。

## 面试场景 4：HyperLogLog 相比 Set 省了多少内存？代价是什么？

🧑‍💻 你

对比 1 亿 UV 统计的两种方案：

方案内存（估算）精度能否反查元素能否判断存在

`Set`（存 8 字节 long ID）800MB+（加 hashtable 元数据可上 1.5GB）100% 精确能（`SMEMBERS`）能（`SISMEMBER`）
`HyperLogLog`固定 12KB±0.81% 相对误差不能不能
差距**约 5 个数量级**误差可接受——

结论：**需要精确 + 元素反查 → Set；只要总数 + 内存敏感 → HLL**。中间地带（要判断存在但接受少量假阳）走*布隆过滤器*（第 0056 课细讲）。

陷阱 HLL 内存不是从 12KB 开始的。Redis 用了**稀疏编码 + 稠密编码**两种存储：

- *稀疏编码*：元素少（基数 < 数千）时用行程编码（RLE）压缩，实际只占几十到几百字节 —— 别一看 `MEMORY USAGE` 才 200B 就以为 HLL 出 bug 了。

- *稠密编码*：基数变大自动转成 16384 桶 × 6bit = 12KB 定长。

转换阈值由 `hll-sparse-max-bytes`（默认 3000 字节）控制。

## 面试场景 5：Bitmap 是什么？和 String 什么关系？

🎤 面试官

Bitmap 你用过吗？跟 String 是什么关系？

🧑‍💻 你

**Bitmap 不是一种独立类型，而是 String 上的「位操作」协议**。Redis 提供了 `SETBIT / GETBIT / BITCOUNT / BITOP` 等命令，把一个 String 值当成 bit 数组访问。`TYPE mykey` 返回的还是 `string`。

为什么要这么设计？因为 **1 个 bit 就能表示 2 种状态**，很多业务问题的本质就是「N 个对象各自处于哪种状态」：

- 用户是否签到（0/1）

- 用户是否活跃（0/1）

- 某文章是否被点赞（0/1）

- 某位置是否被占用（0/1）

对比用 String 存 `"true"/"false"`：1 亿状态用 String 至少 4 字节/条 × 1 亿 = 400MB+；用 Bitmap 只要 *1 亿 bit ÷ 8 = 12.5MB*。省了 30 倍以上。

底层实现：Redis String 最大 512MB，也就是最多 `512 × 1024 × 1024 × 8 ≈ 43 亿` bit。Bitmap 的 offset 范围就是 [0, 2^32)。

追问 Bitmap 的 offset 从 0 开始设 `SETBIT key 1000000 1`，会怎样？

Redis 会**自动扩容 String 到能容纳该 offset 的最小字节数**，中间未设置的 bit 全填 0。所以 `SETBIT key 1000000 1` 会立刻把 String 撑到 125001 字节（≈ 122KB）。*如果只有一个孤立的高 offset，就非常浪费* —— 这就是「稀疏 ID 用 Bitmap 会浪费内存」的原因。

## 面试场景 6：Bitmap 常用命令怎么用？

🧑‍💻 你

命令作用复杂度

`SETBIT key offset 0|1`设置某 bit，返回原值O(1)
`GETBIT key offset`读某 bit，未设过返回 0O(1)
`BITCOUNT key [start end]`统计范围内 1 的个数（默认全串）O(N)
`BITOP AND|OR|XOR|NOT dest src...`多 key 位运算，结果存 destO(N)
`BITPOS key 0|1 [start end]`找第一个 0 或 1 的位置O(N)
`BITFIELD key ...`按任意位宽操作整数字段（进阶）O(1)/字段

组合使用示例（后面「代码验证 2」有完整跑法）：

- 「用户 u1 连续签到多少天」→ 一个用户一个 key，日期偏移量做 offset，`BITCOUNT` 数 1。

- 「今日活跃用户数」→ 一天一个 key，用户 ID 做 offset，`BITCOUNT`。

- 「过去 7 天都活跃的用户」→ 7 个日 key 做 `BITOP AND`，再 `BITCOUNT`。

- 「至少一天活跃的用户」→ `BITOP OR`。

追问 `BITCOUNT` 的 `start end` 参数是 bit 还是 byte 索引？

默认是 **byte 索引**（`BITCOUNT key 0 -1` 表示第 0 到最后一个字节）。Redis 7.0 起加了 `BIT` / `BYTE` 选项：`BITCOUNT key 0 100 BIT` 才是按 bit 计。写代码时要显式指定，别被默认 byte 语义坑到。

## 面试场景 7：Bitmap 典型场景怎么设计 Key？

🎤 面试官

设计一个「用户签到系统」，要能查：今天谁签了、某用户本月签几天、某用户连续签到多少天。用 Bitmap 怎么设计？

🧑‍💻 你

关键是**「维度选谁做 key，谁做 offset」**。签到系统有两种设计，各有取舍：

**方案 A：一个用户一个 key，日期做 offset**（更适合「个人视角」查询）

```
# key: sign:{userId}:{yyyyMM}   offset: 当月第几天（0-based）
SETBIT sign:u1001:202607 26 1              # u1001 于 7 月 27 日签到
BITCOUNT sign:u1001:202607                 # → 本月签到天数
GETBIT sign:u1001:202607 26                # → 今天是否签到
# 连续签到：BITPOS 从当前位置往前找第一个 0
```

**方案 B：一天一个 key，用户 ID 做 offset**（更适合「全站视角」查询）

```
# key: active:{yyyyMMdd}   offset: 用户 ID
SETBIT active:20260727 1001 1
BITCOUNT active:20260727                   # → 今日活跃用户数
# 过去 7 天都活跃：
BITOP AND active:week active:20260721 active:20260722 ... active:20260727
BITCOUNT active:week
```

实际系统里 A、B 常**双写**：A 服务个人页面，B 服务运营报表。

追问 Bitmap 存用户 ID 需要连续吗？稀疏 ID 怎么办？

不需要连续，但要 *offset < 2^32*，且**ID 稀疏时会大量浪费内存**（中间的 0 bit 也占空间）。解决方案：

1. **ID 重映射**：维护一个「原始 ID → 紧凑序号」的映射表（可放 Hash），Bitmap 存序号。

2. **分片 Bitmap**：按 `userId / 1000000` 分桶，每桶一个 key。稀疏桶就不创建。

3. **换 Roaring Bitmap**：Redis 原生不支持，需要 Redis Stack 或应用侧计算。

面试能提到「稀疏 ID 陷阱 + Roaring Bitmap」就非常加分。

追问 Redis 的布隆过滤器是 Bitmap 实现的吗？

是的，本质就是**「一个大 Bitmap + k 个哈希函数」**。写入时用 k 个哈希函数把 key 映射到 Bitmap 的 k 个位置，全部置 1；查询时看这 k 个位置*是否都为 1*：全 1 说明「可能存在」（有假阳），只要有 1 个为 0 就一定「不存在」（无假阴）。Redis 原生没这个类型，官方社区插件 *RedisBloom* 提供，命令 `BF.ADD / BF.EXISTS`。第 0056 课「缓存三兄弟」会讲用它防缓存穿透。

## 面试场景 8：Geo 是什么？底层怎么存的？

🎤 面试官

Geo 你用过吗？它是怎么把二维经纬度存到 Redis 里的？

🧑‍💻 你

**Geo 是 Redis 3.2 引入的地理位置类型，底层复用了 ZSet**：把二维经纬度用 *GeoHash 算法*编码成一个 52 位整数，塞进 ZSet 的 score，元素名（member）就是地点标识。所以 Geo 本质是「ZSet 的语法糖」，可以直接用 `ZRANGE` 查看：

```
GEOADD shops 116.404 39.915 "gate-of-heavenly-peace"
TYPE shops                # → zset  ← 底层就是 ZSet
ZSCORE shops "gate-of-heavenly-peace"   # → 4069885364411786（GeoHash 编码后的 score）
```

**GeoHash 算法核心思想**：把地球表面递归二分。经度 [-180, 180]、纬度 [-90, 90]，每次二分选左半区间记 0、右半区间记 1，把经纬度各切 26 次，交叉编织成 52 bit（Redis 用 52 位精度）。

这样编码有个精妙的性质：*地理位置越接近的两个点，GeoHash 值的前缀越长相同*。ZSet 按 score 排序，就能高效查「score 相近的点」= 「地理位置相近的点」。查附近的人本质就是「score 在某区间内的所有元素」+ 精确距离过滤。

52 位精度约 **0.6 米**，日常场景绰绰有余。

追问 既然底层是 ZSet，能用 ZSet 命令操作 Geo 吗？

可以，但要小心：`ZRANGE / ZCARD / ZREM` 都能用，`ZREM` 是*官方推荐的删除 Geo 元素的方式*（Geo 本身没提供 `GEODEL`）。**但不要用 `ZADD` 直接写**，因为 score 必须是合法的 GeoHash 编码，手写容易破坏结构。查询用 `GEOSEARCH` 系列，因为它会自动做距离过滤，直接用 ZSet 的 `ZRANGEBYSCORE` 拿到的是「GeoHash 前缀相近的点」不等于「实际距离近的点」（存在*地理边界问题*）。

## 面试场景 9：Geo 常用命令怎么用？

🧑‍💻 你

命令作用版本

`GEOADD key lon lat member [...]`添加地理位置3.2
`GEOPOS key member [...]`查坐标（有误差，因为 GeoHash 有损）3.2
`GEODIST key m1 m2 [m|km|mi|ft]`算两点距离（Haversine 球面公式）3.2
`GEORADIUS key lon lat r m|km ...`查半径内的点（*6.2 废弃*）3.2
`GEORADIUSBYMEMBER key m r`以某点为中心查半径（*6.2 废弃*）3.2
`GEOSEARCH key FROMLONLAT/FROMMEMBER BYRADIUS/BYBOX`统一的查询命令，支持圆和矩形6.2+
`GEOSEARCHSTORE dest src ...`查询并把结果存到新 key6.2+

**Redis 6.2+ 用 `GEOSEARCH`，不要用 `GEORADIUS`**（后者已废弃）。示例后面「代码验证 3」有完整跑法。

追问 Geo 的 GeoHash 精度和距离怎么算？

**精度**：Redis 用 52 位 GeoHash，理论精度约 0.6 米。地球赤道周长约 4 万公里，2^26 分格后每格约 *0.6m × 0.6m*。**距离**：`GEODIST` 用 *Haversine 球面距离公式*（假设地球是完美球体），单位可选 `m`（默认）/`km`/`mi`/`ft`。精度对绝大多数导航、外卖场景够用；*大地测量级*要用 Vincenty 公式，Redis 不做。

## 面试场景 10：Geo 适合什么规模的数据？外卖平台会用吗？

🎤 面试官

你说 Geo 能查「附近的商家」，那外卖平台（几百万商家、几千万骑手）会直接用 Redis Geo 吗？

🧑‍💻 你

**不会直接扛主流量**。Redis Geo 适合*中小规模（万级到低百万级点）*的*「附近搜索」*场景：

- ✅ 适合：小城市共享单车定位（几万辆）、社区团购团长（几万个）、单城市附近的人（活跃在线用户几十万级）。

- ❌ 不适合：全国商家搜索（几百万到千万）、复杂地理查询（多边形、路径规划、KNN 搜索）、结合多字段过滤（品类 + 距离 + 评分）。

为什么？Redis Geo 底层是单 ZSet，所有数据在**一个 key 里**：

1. 单 key 内存受限（一般 < 几个 G），无法横向扩容。

2. 不支持二级索引，查询只能按距离，无法组合过滤。

3. `GEOSEARCH` 大半径 + 大数据集会拉高延迟（要扫描 GeoHash 相近的整片区域）。

工业界典型架构：**Redis Geo 做前置缓存/热点区域** + **Elasticsearch geo_shape / geo_point 做主索引**（支持多字段过滤）+ **PostGIS 做精准地理计算**（多边形、路径）。或者直接上专业的 *Uber H3 / Google S2* 六边形网格库。

追问 Redis Geo 能查「矩形范围」吗？

能。`GEOSEARCH ... BYBOX width height km` 支持矩形查询（Redis 6.2+）。以前的 `GEORADIUS` 只支持圆形。矩形对「屏幕视口」类查询更自然 —— 地图 App 的可视范围就是矩形，用 BYBOX 一次拉全屏幕的点，比用外接圆再筛选省 30% 左右。

追问 Geo 数据要删除某个 member 怎么办？

用 **`ZREM key member`**。Redis 没有专门的 `GEODEL` 命令 —— 因为底层就是 ZSet，直接用 ZSet 的删除命令就行。这也是「Geo 是 ZSet 语法糖」的又一佐证。

## 💻 代码验证（打开 redis-cli 跑一遍）

### 验证 1：HyperLogLog 的估算精度

```
# 启动本地 Redis
$ redis-cli

# 添加 10 万个不重复元素（用 shell 循环）
127.0.0.1:6379> DEBUG SLEEP 0     # 确认连上
127.0.0.1:6379> exit

$ for i in $(seq 1 100000); do
redis-cli PFADD uv:test "user_$i" > /dev/null
done

$ redis-cli PFCOUNT uv:test
(integer) 99725                    # ← 估算值，真实 100000，误差 0.275%

$ redis-cli MEMORY USAGE uv:test
(integer) 12344                    # ← 大概 12KB（稠密编码 + 少量元数据）

# 观察稀疏编码：小基数时非常省
$ redis-cli DEL uv:small
$ redis-cli PFADD uv:small a b c d e
$ redis-cli MEMORY USAGE uv:small
(integer) 88                       # ← 才 88 字节！稀疏编码威力
```

### 验证 2：Bitmap 做签到 & 全站活跃

```
# 场景 A：用户 u1001 的 2026 年 7 月签到（1-based 换算成 0-based offset）
127.0.0.1:6379> SETBIT sign:u1001:202607 0 1     # 7 月 1 日签到
(integer) 0
127.0.0.1:6379> SETBIT sign:u1001:202607 26 1    # 7 月 27 日签到（今天）
(integer) 0
127.0.0.1:6379> BITCOUNT sign:u1001:202607
(integer) 2

# 场景 B：全站今日活跃 —— 用户 ID 做 offset
127.0.0.1:6379> SETBIT active:20260727 1001 1
(integer) 0
127.0.0.1:6379> SETBIT active:20260727 1002 1
(integer) 0
127.0.0.1:6379> SETBIT active:20260727 9999 1
(integer) 0
127.0.0.1:6379> BITCOUNT active:20260727
(integer) 3

# 场景 C：过去 2 天都活跃的用户
127.0.0.1:6379> SETBIT active:20260726 1001 1
(integer) 0
127.0.0.1:6379> SETBIT active:20260726 1002 1
(integer) 0
127.0.0.1:6379> BITOP AND active:both active:20260726 active:20260727
(integer) 1250                     # ← 结果 Bitmap 的字节数
127.0.0.1:6379> BITCOUNT active:both
(integer) 2                        # ← 1001、1002 两个都连活

# 场景 D：找连续签到中断的位置（第一个 0 bit）
127.0.0.1:6379> BITPOS sign:u1001:202607 0
(integer) 1                        # ← 从第 1 位开始就是 0，说明 7 月 2 日没签

# 场景 E：陷阱演示 —— 稀疏 offset 会撑爆 String
127.0.0.1:6379> SETBIT sparse:demo 10000000 1
(integer) 0
127.0.0.1:6379> STRLEN sparse:demo
(integer) 1250001                  # ← 一个 bit 撑出 1.25MB
```

### 验证 3：Geo 查询附近的地铁站

```
# 添加北京几个知名地点
127.0.0.1:6379> GEOADD landmarks 116.404 39.915 "tiananmen" \
116.397 39.909 "wangfujing" \
116.383 39.933 "xidan" \
116.446 39.918 "guomao" \
116.310 40.005 "wudaokou"
(integer) 5

# 天安门到王府井距离
127.0.0.1:6379> GEODIST landmarks tiananmen wangfujing m
"810.4034"                         # ← 约 810 米

# Redis 6.2+ 用 GEOSEARCH：以天安门为中心，5 公里内所有点
127.0.0.1:6379> GEOSEARCH landmarks FROMMEMBER tiananmen \
BYRADIUS 5 km ASC \
WITHCOORD WITHDIST WITHHASH
1) 1) "tiananmen"
2) "0.0000"
3) (integer) 4069885364411786
4) 1) "116.40399992465972900"
2) "39.91500029902867997"
2) 1) "wangfujing"
2) "0.8104"                     # ← 距离 km
...

# BYBOX 矩形查询（模拟地图视口）：以天安门为中心，宽 10km × 高 6km
127.0.0.1:6379> GEOSEARCH landmarks FROMMEMBER tiananmen \
BYBOX 10 6 km ASC COUNT 3

# Geo 就是 ZSet：直接用 ZRANGE 看
127.0.0.1:6379> TYPE landmarks
zset
127.0.0.1:6379> ZCARD landmarks
(integer) 5

# 删除元素用 ZREM
127.0.0.1:6379> ZREM landmarks wudaokou
(integer) 1
```

### 验证 4：三种类型的内存对比（1 万独立元素）

```
# Set 存 10000 个 8 字节 long
$ for i in $(seq 1 10000); do redis-cli SADD test:set $i > /dev/null; done
$ redis-cli MEMORY USAGE test:set
(integer) 445256                   # ≈ 435 KB

# HyperLogLog 存 10000 个
$ for i in $(seq 1 10000); do redis-cli PFADD test:hll $i > /dev/null; done
$ redis-cli MEMORY USAGE test:hll
(integer) 12344                    # ≈ 12 KB（省 36 倍）
$ redis-cli PFCOUNT test:hll
(integer) 10023                    # 误差 0.23%

# Bitmap 存 10000 个 offset
$ for i in $(seq 1 10000); do redis-cli SETBIT test:bmp $i 1 > /dev/null; done
$ redis-cli MEMORY USAGE test:bmp
(integer) 1304                     # ≈ 1.3 KB（连续 ID 时最省）
$ redis-cli BITCOUNT test:bmp
(integer) 10000                    # 100% 精确

# 结论：ID 连续/稠密 → Bitmap 最省；ID 稀疏/只要总数 → HLL；要精确反查 → Set
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话说清 HyperLogLog、Bitmap、Geo 各自的核心用途和底层实现。</summary>

HyperLogLog = 概率型基数统计（底层 String + HLL 桶编码），12KB 估 1 亿 UV，误差 0.81%；Bitmap = String 的位操作，1 亿状态只要 12.5MB，适合签到/活跃统计；Geo = 二维坐标查询（底层 ZSet + 52 位 GeoHash score），适合中小规模「附近搜索」。

</details>

<details>

<summary>Q2 HyperLogLog 的 3 个命令是什么？`PFMERGE` 有什么用？</summary>

`PFADD`（加元素）、`PFCOUNT`（估算基数）、`PFMERGE`（多 HLL 合并）。`PFMERGE` 用来把多个 HLL 求并集，例如按日 HLL 合并成周/月 HLL 计算跨日 UV。

</details>

<details>

<summary>Q3 「过去 7 天连续签到」如何用 Bitmap 实现？</summary>

按日建 Bitmap（`active:{date}`，offset 为用户 ID），把过去 7 天的 7 个 Bitmap 做 `BITOP AND`，再 `BITCOUNT` 结果即得连续 7 天都活跃的用户数。如果要看某个用户连续签到多少天，则改用「用户为 key、日期为 offset」的方案，配合 `BITPOS ... 0` 找最近一次未签的位置。

</details>

<details>

<summary>Q4 Geo 为什么底层用 ZSet？删 Geo 元素怎么做？</summary>

因为 GeoHash 算法把二维坐标编码成一个整数，ZSet 按 score 有序，能高效查「附近点」= 「score 相近的点」。Redis 没提供 `GEODEL`，删除直接用 ZSet 的 `ZREM key member`。

</details>

<details>

<summary>Q5 判断「用户 A 昨天来过没」能用 HyperLogLog 吗？该用什么？</summary>

不能！HLL 只保留统计指标，不保留元素，无法查单个元素是否存在。要判存在：精确查用 `SISMEMBER`（Set）或 `GETBIT`（Bitmap，需 ID 可映射成 offset）；允许少量假阳的大规模场景用**布隆过滤器**（RedisBloom 插件，`BF.EXISTS`）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Redis 官方文档 · HyperLogLog —— 稀疏/稠密编码细节

- Redis 官方文档 · Bitmap —— `BITFIELD` 进阶

- Redis 官方文档 · Geo —— `GEOSEARCH` 完整参数

- Flajolet 2007 原论文 · HyperLogLog —— 想深挖算法的看这里

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0054：**Redis 跳表（Skip List）** —— ZSet 的核心数据结构，Geo 也是靠它撑起来的。为什么 Redis 选跳表而不是红黑树？面试常问。

💬 有任何疑问 —— 「HyperLogLog 桶数为什么是 16384？」「Bitmap 存 IP 地址（4 字节）合适吗？」「Geo 大半径查询怎么优化？」—— 直接问我。我是你的老师，也是你的追问陪练。


