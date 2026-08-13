> Lesson 0037 · 阶段四 · JVM · ⭐⭐⭐⭐ · 预计 55 分钟｜含 8 个面试场景 · 4 段可跑命令 · 5 道自测

# 0037 · JVM 参数 & 监控工具 & 线上排查

前面  已经把 JVM 的原理讲透了。这一节是**压轴实战课** —— 面试官问你「线上 CPU 飙升你怎么排查？」「Full GC 频繁怎么办？」「OOM 怎么抓现场？」你得能立刻报出**参数名 + 工具名 + 排查路径**。

学完这节，加上前面 7 节课，你就是 JVM 面试「八股文全通关」。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 你线上排查问题最常用的三个 JDK 自带命令？</summary>

jstack（线程堆栈）、jstat（GC 统计）、jmap（内存 dump）。Arthas 也算，但不是 JDK 自带的。

</details>

<details>

<summary>Q0.2 `-Xms` 和 `-Xmx` 设成一样有什么好处？</summary>

避免 JVM 在运行期动态扩缩堆带来停顿和 GC 压力。线上一般都设成一样。

</details>

## 面试场景 1：核心 JVM 参数速查 ⭐核心

🎤 面试官

你常用的 JVM 参数有哪些？分几类？

🧑‍💻 你

### 堆内存参数

参数含义示例

`-Xms`初始堆大小`-Xms2g`
`-Xmx`最大堆大小`-Xmx4g`
`-Xmn`新生代大小`-Xmn1g`
`-XX:NewRatio`老/新比例（默认 2）`-XX:NewRatio=2`
`-XX:SurvivorRatio`Eden/Survivor 比例（默认 8）`-XX:SurvivorRatio=8`
`-XX:MaxTenuringThreshold`晋升年龄阈值（默认 15）`-XX:MaxTenuringThreshold=15`
`-XX:MetaspaceSize`元空间初始大小`-XX:MetaspaceSize=256m`
`-XX:MaxMetaspaceSize`元空间最大大小`-XX:MaxMetaspaceSize=512m`

### GC 参数

参数含义

`-XX:+UseG1GC`使用 G1（JDK 9+ 默认）
`-XX:+UseZGC`使用 ZGC（JDK 15+）
`-XX:+UseParallelGC`吞吐量优先
`-XX:MaxGCPauseMillis=200`G1 最大停顿目标

### OOM / Dump 参数（线上必配）

参数含义

`-XX:+HeapDumpOnOutOfMemoryError`OOM 时自动 dump 堆
`-XX:HeapDumpPath=/path/dump.hprof`dump 文件路径
`-XX:OnOutOfMemoryError=`OOM 时执行脚本（如自动重启）
`-XX:+PrintGCDetails`打印 GC 详情（JDK 8）

### JDK 9+ 统一日志

```
-Xlog:gc*=info:file=gc.log:time,uptime,level,tags
```

## 面试场景 2：jstack —— 线程堆栈分析 ⭐必会

🎤 面试官

线上 CPU 突然飙到 100%，你怎么排查？

🧑‍💻 你

**四步排查法**：

```
# 1. top 找到 CPU 最高的 Java 进程 PID
top -H -p <PID>

# 2. 找到 CPU 最高的线程 tid（转十六进制）
printf "%x\n" <tid>

# 3. jstack 导出线程堆栈，搜这个十六进制 tid
jstack <PID> | grep -A 30 <hex_tid>

# 4. 看线程在哪个方法的哪一行 —— 那就是 CPU 热点
```

**线程状态速查**：

状态含义常见原因

RUNNABLE运行中/等待 CPU正常 / CPU 密集计算
BLOCKED等待锁synchronized 竞争 → 死锁
WAITING无限等待Object.wait() / LockSupport.park()
TIMED_WAITING限时等待Thread.sleep() / LockSupport.parkNanos()

**死锁检测**：jstack 输出末尾会自动显示 `Found one Java-level deadlock`，或者 `jstack -l <PID> | grep BLOCKED` 找互相等待的线程。

## 面试场景 3：jmap —— 内存分析 ⭐必会

🎤 面试官

线上 OOM 了，你怎么排查？用什么工具看 dump 文件？

🧑‍💻 你

```
# 1. 导出堆 dump（优先用这个，通过 JVM 机制导出）
jmap -dump:format=b,file=heap.hprof <PID>

# 2. 查看堆概览
jmap -heap <PID>

# 3. 查看对象统计（看谁最占内存）
jmap -histo:live <PID> | head -30
```

**Dump 分析工具**：

- **MAT（Eclipse Memory Analyzer）**：最专业，看 Dominator Tree、Leak Suspects。

- **JProfiler / YourKit**：商业版，功能丰富。

- **Arthas**：阿里开源，`heapdump` 命令直接 dump，不需要 jmap。

- **jhat**：JDK 自带但已 deprecated，不推荐在生产用。

**OOM 排查 SOP**：打开 MAT → Histogram 看哪些类实例最多 → Dominator Tree 看谁占的内存比例最大 → Leak Suspects 看可疑泄漏点 → 分析 GC Root 路径。

陷阱 `jmap -dump` 会**STW（Stop The World）**！堆越大停顿越久。生产环境优先用**在线诊断工具**（Arthas）或提前配好 `-XX:+HeapDumpOnOutOfMemoryError`。不要没事在生产上 jmap -dump！

## 面试场景 4：jstat —— GC 实时监控 ⭐必会

🎤 面试官

怎么实时看 GC 情况？

🧑‍💻 你

```
# 每 1 秒输出一次 GC 统计
jstat -gc <PID> 1000

# 输出列:
# S0C S1C S0U S1U  EC   EU   OC    OU    MC    MU
# Survivor 大小/使用  Eden 大小/使用  Old 大小/使用  Metaspace 大小/使用
# YGC YGCT FGC FGCT GCT
# YoungGC次数/时间  FullGC次数/时间  GC总时间
```

**关键指标**：

- **FGC 次数**涨很快 → Full GC 频繁 → 老年代满或碎片严重。

- **OU / OC** 接近 100% → 老年代要满了。

- **YGC 间隔**很短 → 新生代太小或分配速率太高。

## 面试场景 5：Arthas —— 阿里在线诊断神器 ⭐实战首选

🎤 面试官

用过 Arthas 吗？举几个常用命令。

🧑‍💻 你

**Arthas** 是目前 Java 线上诊断的事实标准（阿里开源，GitHub 35k+ stars）：

命令作用场景

`dashboard`实时面板：线程、内存、GC一进 Arthas 先看 dashboard
**`thread`**线程堆栈、CPU 排行、死锁CPU 飙高排查
**`jad`**反编译线上运行的 class确认线上跑的代码版本对不对
**`watch`**方法执行观测（入参、返回值、异常）想看某个方法的实际输入输出
**`trace`**方法链路追踪 + 耗时接口慢，找哪个环节慢
**`stack`**输出方法被哪些路径调用想看谁在调这个方法
`heapdump`在线 dump 堆比 jmap 快，无 STW（fork 子进程）
`vmtool`强制 GC、获取 spring bean调 spring 配置、手动触发 GC

```
# 安装 & 启动
curl -O https://arthas.aliyun.com/arthas-boot.jar
java -jar arthas-boot.jar

# 选了 PID 后，看 CPU 最高线程
$ thread -n 3          # CPU 最高的 3 个线程

# 反编译线上的 Controller
$ jad com.example.MyController

# 观测方法调用
$ watch com.example.UserService getUser '{params, returnObj}' -x 3
```

## 面试场景 6：线上问题排查套路大全 ⭐核心

🎤 面试官

总结一下：线上出问题了，你的排查 SOP 是什么？

🧑‍💻 你

现象第一工具排查路径

**CPU 飙高**
top + jstack
top -H 找高 CPU 线程 → 转十六进制 → jstack 搜 → 找热点代码

**内存泄漏 / OOM**
jmap + MAT
jmap -dump 导出 → MAT 分析 Dominator Tree → 跟踪 GC Root

**Full GC 频繁**
jstat + GC 日志
看 FGC 频率/耗时 → 分析 GC 日志 → 调参或扩堆

**死锁**
jstack -l
jstack 输出末尾直接标注 Found deadlock → 看线程名

**接口慢 / 超时**
Arthas trace
`trace` 看链路耗时 → 定位到慢的方法 → jad 看代码

**不知道哪出问题了**
**Arthas dashboard**
一屏看完 CPU + 内存 + GC + 线程 → 哪个异常看哪个

**黄金 5 分钟原则**：生产故障，前 5 分钟先保现场（dump 堆、保存 GC 日志、jstack 线程快照），再考虑重启。

## 面试场景 7：生产环境 JVM 参数模板

🎤 面试官

给你一个新项目，你会怎么设 JVM 参数？给一个生产环境模板。

🧑‍💻 你

### JDK 17 G1 模板（通用，4C8G 机器）

```
java \
-Xms4g -Xmx4g \                           # 堆 4G，一样大避免动态扩缩
-XX:+UseG1GC \                             # JDK 17 默认 G1
-XX:MaxGCPauseMillis=200 \                 # G1 最大停顿 200ms
-XX:+HeapDumpOnOutOfMemoryError \          # OOM 自动 dump
-XX:HeapDumpPath=/var/log/app/heap.hprof \ # dump 路径
-XX:+ExitOnOutOfMemoryError \              # OOM 直接退出（由 K8s 重启）
-Xlog:gc*=info:file=/var/log/app/gc.log:time,uptime \ # GC 日志
-Dfile.encoding=UTF-8 \                    # 字符编码
-jar app.jar
```

### JDK 21 ZGC 模板（低延迟优先）

```
java \
-Xms8g -Xmx8g \
-XX:+UseZGC \                              # ZGC
-XX:+ZGenerational \                       # 分代 ZGC（JDK 21+）
-XX:+HeapDumpOnOutOfMemoryError \
-XX:HeapDumpPath=/var/log/app/heap.hprof \
-Xlog:gc*=info:file=/var/log/app/gc.log \
-jar app.jar
```

## 面试场景 8：JVM 调优经验

🎤 面试官

说说你实际做过哪些 JVM 调优？有没有踩过坑？

🧑‍💻 你

说几个典型实际案例（面试官要听你**真的做过**）：

- **案例 1：Metaspace OOM** — 系统运行几天就 OOM，GC 日志显示 Metaspace 满。jmap -clstats 发现大量 Groovy 动态生成的类。原因是脚本引擎每次动态编译生成新类但没清理。解决：限制 Metaspace、升级到可清理的 ClassLoader。

- **案例 2：GC 停顿 > 1s** — 用户偶尔卡顿。GC 日志看 CMS Remark 阶段慢。调到 G1 + MaxGCPauseMillis=200，问题解决。

- **案例 3：堆外内存 OOM** — `-Xmx` 设了 4G 但进程 RSS 到了 8G。发现是 NIO DirectByteBuffer 没释放。jcmd 看 NIO 直接内存使用量。解决：加 `-XX:MaxDirectMemorySize` 限制。

## 💻 实操命令

### 命令 1：一行看全 JVM 运行时参数

```
$ java -XX:+PrintFlagsFinal -version | grep -E "MaxHeapSize|UseG1GC|UseCompressedOops"
size_t MaxHeapSize     = 4294967296    {product} {default}
bool UseG1GC           = true          {product} {default}
bool UseCompressedOops = true          {lp64_product} {ergonomic}
```

### 命令 2：查看进程的 JVM 参数

```
$ jinfo -flags <PID>           # JDK 8
$ jhsdb jinfo --pid <PID>      # JDK 9+
```

### 命令 3：jcmd —— 万能瑞士军刀（JDK 7+）

```
$ jcmd                          # 列出所有 Java 进程
$ jcmd <PID> help              # 列出所有可用命令
$ jcmd <PID> GC.run            # 触发一次 GC
$ jcmd <PID> Thread.print      # 等价 jstack
$ jcmd <PID> VM.native_memory  # 看堆外内存
$ jcmd <PID> GC.heap_dump /path/dump.hprof  # dump 堆（比 jmap 轻）
```

### 命令 4：jhsdb（JDK 9+ 替代 jmap/jstack/jinfo）

```
$ jhsdb jmap --heap --pid <PID>
$ jhsdb jstack --pid <PID>
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 CPU 飙高的排查步骤？</summary>

top -H 找高 CPU 线程 → 转十六进制 tid → jstack 搜 → 定位到具体代码行。Arthas 的话直接用 `thread -n 3`。

</details>

<details>

<summary>Q2 哪些 JVM 参数是线上必配的？</summary>

`-Xms`/`-Xmx`（设一样大）、`-XX:+HeapDumpOnOutOfMemoryError`（OOM 自动 dump）、`-XX:HeapDumpPath`（dump 路径）、GC 日志（JDK 9+: -Xlog:gc*）、OOM 自动退出（-XX:+ExitOnOutOfMemoryError，让 K8s 重启）。

</details>

<details>

<summary>Q3 jmap 和 Arthas heapdump 有什么区别？</summary>

jmap -dump 会 STW，堆越大停越久。Arthas heapdump fork 子进程做，几乎不停顿。生产环境优先用 Arthas。

</details>

<details>

<summary>Q4 jstat 里 FGC 频繁说明什么问题？</summary>

Full GC 频繁 = 老年代快满了或碎片严重。常见原因：内存泄漏、大对象频繁分配、Survivor 太小导致提前晋升、老年代太小。

</details>

<details>

<summary>Q5 JDK 17 生产环境默认用哪个 GC？要调什么参数？</summary>

G1。核心参数：`-Xmx` 和 `-XX:MaxGCPauseMillis=200`，其余不建议手调。需要极致低延迟换 ZGC（-XX:+UseZGC）。

</details>

#### 📖 原文 & 工具

-

- Arthas 官方文档

- JDK 8 工具文档

- MAT 用户手册

#### 🔗 关联课件

-

-

- 0038 · IO 基础 & 设计模式（下一阶段）

#### 🧭 阶段四完成！下一阶段预告

**阶段五：IO**（3 课）—— BIO/NIO/AIO、select/poll/epoll 多路复用、Netty 的 Reactor 模型。

💬 JVM 八讲到此结束。有任何疑问 —— 「mat 分析结果怎么看？」「线上不敢 jmap 怎么办？」「G1 调优有什么实际经验？」—— 直接问我。


