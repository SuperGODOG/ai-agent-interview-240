> Lesson 0033 · 阶段四 · JVM · ⭐⭐⭐⭐⭐ · 预计 75 分钟｜含 12 个面试场景 · 5 段可跑代码 · 6 道自测

# 0033 · JVM 垃圾回收算法与收集器

上一节  讲了对象怎么诞生、怎么在内存里摆放。这一节讲它们的**死亡与回收** —— GC（Garbage Collection）是 Java 面试里仅次于并发的第二大硬核板块，也是 P7/P8 级别的必考题。

面试官要的不是「Java 有 GC 不用手动释放」这种入门级回答，而是你能**画出一张分代堆的图、讲清 G1 的 Region 设计、对比 CMS 和 G1 的 Stop-The-World 差异**。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 引用计数法为什么没被 Java 采用？</summary>

因为它搞不定**循环引用**：A 引用 B、B 引用 A，两个对象计数器都是 1，永远不为 0 也就永远不被回收。Python 同样用引用计数，但额外加了「标记-清除」处理循环引用。

</details>

<details>

<summary>Q0.2 `System.gc()` 一定会立刻触发 GC 吗？</summary>

不会。它只是「建议」JVM 做一次 Full GC，JVM 完全可能忽略。加上 `-XX:+DisableExplicitGC` 甚至直接禁掉。生产里永远不要依赖它。

</details>

## 面试场景 1：怎么判断一个对象死了？⭐核心

🎤 面试官

JVM 怎么知道一个对象可以回收了？

🧑‍💻 你

两种主流算法：**引用计数法和可达性分析法**。JVM 用的是后者。

### 引用计数法（Reference Counting）—— JVM 没采用

- 每个对象维护一个 `refCount` 计数器，有引用指向它就 +1，引用失效就 -1。

- 计数器为 0 时回收。

- **致命缺陷：循环引用**。A→B、B→A，两者计数器都是 1，永远不为 0 → 内存泄漏。

### 可达性分析（Reachability Analysis）—— JVM 采用

从一组称为 **GC Roots** 的根对象出发，顺着引用链往下找。能追踪到的对象就是「活」的，追踪不到的就是「死」的、可以回收。

```
┌─────────────────────────────────────────┐
│                GC Roots                  │
│  ┌─────────┐ ┌───────┐ ┌────────────┐  │
│  │栈帧引用  │ │静态变量│ │JNI 引用    │  │
│  └────┬────┘ └───┬───┘ └─────┬──────┘  │
│       │          │           │          │
│       ▼          ▼           ▼          │
│  ┌────┴──────────┴───────────┴────┐     │
│  │    可达对象（存活，不回收）       │     │
│  └─────────────────────────────────┘     │
│                                          │
│  ┌─────────────────────────────────┐     │
│  │  不可达（可回收）  ← 没有任何 GC Root │     │
│  │  ┌───┐    ┌───┐    能追到它         │     │
│  │  │obj1│◄──►│obj2│  (循环引用也不行)  │     │
│  │  └───┘    └───┘                    │     │
│  └─────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

**GC Roots 包括**：

- 虚拟机栈（栈帧中的局部变量表）中引用的对象

- 方法区中**静态属性**引用的对象

- 方法区中**常量**引用的对象（String Table 里的引用）

- 本地方法栈中 JNI（Native 方法）引用的对象

- Java 虚拟机内部的引用（基本类型对应的 Class 对象、常驻的异常对象、系统类加载器）

- 所有被 `synchronized` 持有的对象

追问 可达性分析具体怎么「找」？会不会漏？

从 GC Roots 出发做 **图遍历**（DFS/BFS），标记所有能到达的对象。不会漏 —— 因为它是「从根出发穷举所有可达路径」。但这引出了性能问题：堆越大、对象越多，遍历越慢。所以才有了分代、分区、增量、并发等优化（面试场景 4-10 展开）。

## 面试场景 2：四种引用类型 ⭐高频

🎤 面试官

Java 里引用分几种？各自什么时候被回收？

🧑‍💻 你

引用类型回收时机典型用途

**强引用 Strong**
永不回收（除非 GC Roots 不可达）
99% 的 `new` 都是

**软引用 Soft**
内存不足时 (OOM 之前) 回收
图片缓存、本地缓存

**弱引用 Weak**
下次 GC 就回收（不管内存够不够）
WeakHashMap、ThreadLocal 的 Entry

**虚引用 Phantom**
对象被 GC 回收时收到通知
NIO DirectByteBuffer 的 Cleaner

```
Object obj = new Object();             // 强引用
SoftReference<Object> sf = new SoftReference<>(obj);   // 软引用
WeakReference<Object> wf = new WeakReference<>(obj);   // 弱引用
PhantomReference<Object> pf = new PhantomReference<>(obj, queue); // 虚引用
```

追问 软引用和弱引用的区别到底在哪？

一句话：**软引用「内存不够才回收」，弱引用「下次 GC 就回收」**。所以软引用适合做「容忍性缓存」（如 Guava Cache），弱引用适合做「一旦对象只被弱引用指向就清除」的场景（如 ThreadLocal 的 key 是弱引用，防止 ThreadLocal 本身导致内存泄漏）。

陷阱 虚引用 **不能单独用来获取对象实例**—— `phantomRef.get()` 永远返回 `null`。它的唯一用途是配合 `ReferenceQueue`，在对象被回收时收到系统通知，用于堆外内存释放等清理工作。

## 面试场景 3：finalize() —— 对象的「临终遗言」

🎤 面试官

对象死前还有什么机会复活吗？finalize() 还会执行吗？

🧑‍💻 你

可达性分析发现对象不可达后，它**不是立即死亡**，还要经过两次标记过程：

1. **第一次标记**：发现不可达后，检查是否覆盖了 `finalize()` 且还没被 JVM 调过。

2. 如果满足条件，放进 **F-Queue**，由一个低优先级的 Finalizer 线程去执行 `finalize()`。

3. GC 稍后对 F-Queue 中对象做**第二次标记**：如果在 `finalize()` 里把自己重新关联到 GC Roots（比如 `SomeClass.staticRef = this`），则**复活**、移出回收集合；否则正式回收。

**但面试时一定要补一句**：`finalize()` 在 JDK 9 被标记为 **deprecated**，JDK 18 彻底移除。它的执行时机不确定、可能永远不执行、性能极差。替代方案是 **`Cleaner` + `PhantomReference`** 或 try-with-resources。

追问 那现在用什么替代 finalize？

**Cleaner API**（JDK 9+）：

```
Cleaner cleaner = Cleaner.create();
cleaner.register(obj, () -> {
// 清理资源 —— 类似 finalize 但更可靠
System.out.println("对象被回收了");
});
```

但最佳实践永远是 **try-with-resources + AutoCloseable**，让释放变得确定性，不依赖 GC。

## 面试场景 4：三大基础 GC 算法 ⭐核心

🎤 面试官

画一下标记-清除、标记-复制、标记-整理三种算法，各有什么优缺点？

🧑‍💻 你

### 算法一：标记-清除（Mark-Sweep）—— 最基础

```
【回收前】                      【回收后】
┌─┬─┬─┬─┬─┬─┬─┬─┐          ┌─┬───┬─┬───┬─┬─┬─┐
│A│B│C│D│E│F│G│H│   ──►   │A│   │C│   │E│F│H│
└─┴─┴─┴─┴─┴─┴─┴─┘          └─┴───┴─┴───┴─┴─┴─┘
存活: A C E F H  删除 B D G      碎片！碎片！
```

- 第一步 **Mark**：从 GC Roots 出发标记所有可达对象。

- 第二步 **Sweep**：遍历堆，回收没被标记的对象。

- **优点**：简单直接，不需要移动对象。

- **致命缺点**：回收后产生大量**内存碎片**。碎片多了可能明明总空闲够用却分配不了大对象，提前触发下一次 GC。

### 算法二：标记-复制（Mark-Copy / Semi-space）—— 解决碎片

```
【回收前】              【回收后】
┌─┬─┬─┬─┬─┬─┐        ┌─┬─┬─┬─┬─┬─┐
│A│B│C│D│E│F│  From  │A│C│E│F│ │ │  To（紧凑排列）
└─┴─┴─┴─┴─┴─┘        └─┴─┴─┴─┴─┴─┘
← 原来的 From 整块清空
```

- 把堆分成大小相等的 **From 和 To 两块**。每次只使用一块。

- GC 时把 From 里存活的对象**复制到 To**，然后清空整个 From。

- **优点**：没有碎片，分配只需指针碰撞，极快。

- **致命缺点**：可用内存**只剩一半**。对象存活率高时复制成本极大。

- 这也解释了为什么分代 GC 的**新生代用复制算法**：新生代对象 98% 朝生夕死，复制成本很低，性价比极高。

### 算法三：标记-整理（Mark-Compact）—— 老年代专用

```
【回收前】              【回收后】
┌─┬─┬─┬─┬─┬─┬─┬─┐    ┌─┬─┬─┬─┬───┬───┬───┐
│A│B│C│D│E│F│G│H│ ─► │A│C│E│F│H│   │   │   │
└─┴─┴─┴─┴─┴─┴─┴─┘    └─┴─┴─┴─┴─┴───┴───┴───┘
↑ 往一侧紧凑，没有碎片
```

- 先标记存活对象，然后**把所有存活对象往内存一端移动**，清理边界外的内存。

- **优点**：没有碎片，不浪费一半内存。

- **缺点**：移动对象意味着要更新所有指向它的引用，**STW 时间长**。老年代对象多，移动成本很大。

**面���口诀：「新生代复制、老年代整理、CMS 靠清除但碎片多」**。

追问 为什么不用一种算法打天下？

因为**分代假说（Weak Generational Hypothesis）**：绝大多数对象是朝生夕死的（新生代），少数熬过去的活得很久（老年代）。新对象存活率低 → 复制算法最优；老对象存活率高 → 复制成本太大 → 标记-清除或标记-整理更优。这就是分代收集的理论基础。

## 面试场景 5：分代收集 & HotSpot 堆结构 ⭐核心

🎤 面试官

画一个 HotSpot 分代堆结构，讲讲新生代到老年代的晋升过程。

🧑‍💻 你

```
┌────────────────── Young Generation ──────────────────┐
│  ┌──── Eden ────┐  ┌── S0 ──┐  ┌── S1 ──┐           │
│  │              │  │        │  │        │           │
│  │  新对象出生地  │  │ Survivor│  │ Survivor│          │
│  │  (8/10)      │  │  (1/10) │  │  (1/10) │          │
│  └──────────────┘  └────────┘  └────────┘           │
│   默认比例 Eden:S0:S1 = 8:1:1                        │
└──────────────────────────────────────────────────────┘
│ 熬过 15 次 Minor GC
▼
┌────────────────── Old Generation ────────────────────┐
│                                                      │
│              Tenured / Old 区                         │
│         存放大对象 & 长期存活对象                       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**一次 Minor GC（Young GC）的完整流程**：

1. 新对象都在 **Eden** 分配。Eden 满了触发 Minor GC。

2. 把 Eden + 当前用着的 Survivor（From）里存活的对象**复制到另一块 Survivor（To）**。

3. 活得久的对象每熬过一次 GC 就 **age + 1**（存在对象头的 Mark Word 里）。

4. 年龄超过 `-XX:MaxTenuringThreshold`（默认 15）的，**晋升到老年代**。

5. 如果 Survivor 里同龄对象总大小超过 Survivor 的一半，**动态年龄判断**直接让大于等于这个年龄的对象全晋升。

6. 清空 Eden 和 From Survivor，From 和 To 角色互换。

所以 **Survivor 区至少有一个永远是空的**，这就是复制算法的「半区」设计。

追问 什么情况对象会直接进老年代，不走 Survivor？

四种情况：(1) **大对象**，超过 `-XX:PretenureSizeThreshold`（默认 0 即关闭，只对 Serial/ParNew 有效）；(2) **Survivor 放不下**的存活对象直接去老年代（空间分配担保）；(3) **动态年龄**，Survivor 里某年龄的所有对象大小超 Survivor 一半；(4) G1 的 **Humongous 对象**（超过 Region 一半大小）。

## 面试场景 6：经典收集器全景图（JDK 8 时代）

🎤 面试官

JDK 8 有哪些 GC 收集器？新生代和老年代怎么搭配？

🧑‍💻 你

收集器代算法线程特点

**Serial**新生代复制单线程STW，Client 模式默认
**ParNew**新生代复制多线程Serial 的多线程版，唯一能和 CMS 搭配的新生代
**Parallel Scavenge**新生代复制多线程关注**吞吐量**（用户代码时间 / 总时间）
**Serial Old**老年代标记-整理单线程Client 模式老年代默认
**Parallel Old**老年代标记-整理多线程搭配 Parallel Scavenge 的吞吐量优先组合
**CMS**老年代标记-清除多线程并发追求**最短停顿**（JDK 14 被移除）

**经典搭配**：

- **ParNew + CMS**：JDK 8 互联网标配，追求低延迟。

- **Parallel Scavenge + Parallel Old**：JDK 8 默认，追求吞吐量（适合批处理）。

- **Serial + Serial Old**：Client 模式或单核小内存。

## 面试场景 7：CMS 深度剖析 ⭐核心

🎤 面试官

CMS 的全称是什么？它的回收分几个阶段？哪些阶段会 STW？

🧑‍💻 你

**CMS（Concurrent Mark Sweep）**，老年代收集器，目标是**最短回收停顿时间**。四个阶段：

```
1. 初始标记 (Initial Mark)         [STW]  标记 GC Roots 能直接关联的对象，很快
2. 并发标记 (Concurrent Mark)      [并发]  从 GC Roots 出发遍历对象图，耗时长但不 STW
3. 重新标记 (Remark)               [STW]  修正并发标记期间变化了的对象，比初始标记长
4. 并发清除 (Concurrent Sweep)     [并发]  清除未标记对象，不 STW
```

**CMS 的三大缺陷**（面试官最爱追问）：

- **并发占用 CPU**：并发阶段占用一部分线程，吞吐量下降。默认 GC 线程数 = (CPU 核数 + 3) / 4，CPU 少于 4 核时对应用影响大。

- **浮动垃圾 & Concurrent Mode Failure**：并发清理阶段用户线程还在产生垃圾（浮动垃圾），CMS 来不及清。如果预留内存不够了，触发 **Serial Old** 做一次单线程 Full GC —— 停顿时间爆炸。

- **内存碎片**：标记-清除算法不整理内存，碎片多了即使总空闲够用也分配不了大对象，又触发 Full GC。

**JDK 9 标记为 deprecated，JDK 14 正式移除**。替代者是 **G1**。

追问 CMS 的「Concurrent Mode Failure」怎么排查？

GC 日志里看到 `Concurrent Mode Failure` 后紧跟一个 `Full GC (Allocation Failure)`。原因是老年代剩余空间不够容纳并发期间新晋升的对象。**解决方案**：调大 `-XX:CMSInitiatingOccupancyFraction` 对应的老年代使用率阈值（默认 92%，降到 70-80%），让 CMS 提早点开工。或者调大 Survivor 区减少过早晋升。

## 面试场景 8：G1 垃圾收集器 ⭐核心（JDK 9+ 默认）

🎤 面试官

G1 和 CMS 有什么区别？G1 的 Region 设计解决了什么问题？

🧑‍💻 你

### G1（Garbage First）的核心设计：抛弃分代物理隔离，用 Region

```
┌────────────────── G1 Heap ──────────────────────────┐
│ ┌──R──┐ ┌──R──┐ ┌──R──┐ ┌──R──┐ ┌──R──┐ ┌──R──┐    │
│ │ Eden │ │ Old │ │ Eden│ │Humong│ │Surv│ │Free │    │
│ └─────┘ └─────┘ └─────┘ └──────┘ └────┘ └─────┘    │
│ ┌──R──┐ ┌──R──┐ ┌──R──┐ ┌──R──┐ ┌──R──┐ ┌──R──┐    │
│ │ Old │ │ Eden│ │ Old │ │Surv │ │Free │ │Old  │    │
│ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    │
│                                                      │
│   每个 Region 大小固定（1~32MB，2 的幂），不物理隔离    │
│   角色（Eden/Survivor/Old/Humongous）可动态切换        │
└──────────────────────────────────────────────────────┘
```

- **Region**：堆被划分成大小相等的 Region（默认 2048 个）。Region 可以动态标识为 Eden、Survivor、Old、Humongous（存大对象，跨多个连续 Region）。

- **RSet（Remembered Set）**：每个 Region 维护一个 RSet，记录「别的 Region 里的哪些对象引用了我的对象」。避免做 GC Roots 扫描时扫全堆。

- **CSet（Collection Set）**：本次 GC 要回收的 Region 集合。G1 会优先选**垃圾最多的 Region**（Garbage First 名字的来源）。

### G1 的 GC 模式

- **Young GC**：回收所有 Eden Region，把存活对象拷贝到 Survivor/Old。STW。

- **Mixed GC**：回收所有 Young + 一部分 Old Region（选垃圾最多的几个）。STW，但可以分多次，用户可设定停顿目标。

- **Full GC**：Mixed GC 跟不上分配速度时退化为 Serial Old。G1 会尽量不触发 Full GC。

### G1 vs CMS 对比

维度CMSG1

内存模型分代物理隔离Region 化，不隔离
内存碎片严重（标记-清除）无（复制/整理）
可预测停顿没有有（`-XX:MaxGCPauseMillis`）
大堆性能4-6G 以上退化几十到上百 GB 都很稳
CPU 占用并发阶段占用一定 CPU更高（RSet 维护 + SATB）

**JDK 9+ 默认就是 G1**，JDK 17 LTS 也是 G1。

追问 G1 的「可预测停顿」是怎么做到的？

用户设 `-XX:MaxGCPauseMillis=200`（默认 200ms）。G1 根据历史数据建模，预测回收每个 Region 需要的时间，然后只把「能在 200ms 内回收完的垃圾最多 Region」放进 CSet。这次回收不完的下次再收 —— 把一次大停顿拆成多次小停顿。

## 面试场景 9：三色标记算法 ⭐进阶

🎤 面试官

并发标记的时候，用户线程还在改引用关系 —— 怎么保证不标漏活对象？

🧑‍💻 你

并发标记的核心算法是 **三色标记（Tri-color Marking）**：

- **白色**：还没被访问到的对象（初始全白，结束后还是白色的就是垃圾）。

- **灰色**：对象本身被标记了，但它的子引用还没全扫完。

- **黑色**：对象本身和所有子引用全扫完了，确定是活的。

并发标记的问题是：用户线程可能同时做两种破坏性操作：

1. **把黑色对象的引用指向白色对象**（新增引用）

2. **删掉灰色对象到白色对象的引用**（删除引用）

两个条件同时满足 → 白色对象**漏标**（明明活着却被当垃圾回收了，严重 Bug）。

两种解决方案：

- **增量更新 Incremental Update（CMS 用）**：当黑色对象新增对白色对象的引用时，把黑色对象**变回灰色**，重新扫一遍。

- **原始快照 SATB（G1 用）**：在并发标记开始时拍一个引用关系的**快照**。即使后来引用被删了，快照里的关系仍然有效 —— 宁可多标（浮动垃圾），绝不漏标（活对象被回收）。

**SATB = Snapshot At The Beginning**。G1 的重新标记阶段负责修正快照之后的变化。

追问 SATB「多标」会有什么副作用？

多标意味着把本应死亡的「垃圾」暂时当活对象保留了，这次 GC 不收它，下次才收。这就是**浮动垃圾（Floating Garbage）**。CMS 和 G1 都有，只是 CMS 漏标会死人（活对象被回收 → JVM 崩溃），G1 多标只是延迟回收，安全得多。

## 面试场景 10：ZGC & Shenandoah —— 亚毫秒级停顿

🎤 面试官

听说过 ZGC 吗？它和 G1 有什么不同？

🧑‍💻 你

特性G1ZGCShenandoah

目标停顿~200ms< 1ms (亚毫秒)< 10ms
JDK 引入JDK 7 (实验)JDK 11 (实验), JDK 15 (生产)JDK 12 (实验)
核心技��Region + RSet染色指针 + 读屏障Brooks 指针 + 读屏障
最大堆几百 GB16 TB（理论）无硬限制
并发整理有（Mixed GC 部分整理）全部并发整理全部并发整理
分代有JDK 21 起支持分代不分代

**ZGC 的核心创新：染色指针（Colored Pointers）**

ZGC 在 64 位指针里嵌入 GC 状态信息（Finalizable / Remapped / Marked），利用指针的高位 bit 做标记 —— 不用额外对象头、不用读屏障之外的额外开销。这要求操作系统支持「多映射内存」，目前在 Linux/x64 上可用。

**什么时候选 ZGC？**低延迟要求极高（如交易系统、实时风控）、堆很大（TB 级）、愿意接受稍低的吞吐量。

**JDK 21+ 的 Generational ZGC** 进一步优化了吞吐量，让 ZGC 在大堆场景下也能打。

陷阱 ZGC 的「1ms 停顿」说的是**STW 时间**，不是整个 GC 周期。ZGC 的并发阶段可能持续几分钟甚至更久，只是用户线程几乎不受影响。

## 面试场景 11：GC 日志 & 调优思路 ⭐实战

🎤 面试官

线上 GC 频繁怎么办？你怎么看 GC 日志？

🧑‍💻 你

**看 GC 日志的命令**（JDK 9+ 统一日志）：

```
java -Xlog:gc*=info:file=gc.log:time,uptime,level,tags
```

一条典型的 G1 GC 日志：

```
[2024-01-15T10:30:15.123+0800][info][gc,start] GC(42) Pause Young (G1 Evacuation Pause)
[2024-01-15T10:30:15.200+0800][info][gc,heap] GC(42) Eden: 512M(512M)->0M(480M) Survivor: 32M->64M Heap: 3.2G(8G)->2.1G(8G)
[2024-01-15T10:30:15.201+0800][info][gc] GC(42) Pause Young (G1 Evacuation Pause) 3200M->2100M (8G) 78.123ms
```

**常见问题排查思路**：

现象可能原因调优方向

Young GC 太频繁Eden 太小 / 对象分配速率高调大 Eden（增大 `-Xmn` 或 `G1NewSizePercent`）
Young GC 停顿长Survivor 复制太多 / 对象太大增大 Survivor 或调大 `-XX:G1ReservePercent`
Full GC 频繁老年代满 / 大对象频繁分配调大堆、排查内存泄漏、调大 `-XX:InitiatingHeapOccupancyPercent`
Concurrent Mode FailureCMS 并发跟不上分配速度提前 CMS 触发阈值（`CMSInitiatingOccupancyFraction`）
Humongous Allocation 失败G1 大对象没连续 Region避免超大对象、调大 Region Size

**三板斧**：GC 日志 → GCeasy / GCViewer 可视化 → 根据瓶颈调参数。记住 **G1 调优只有两个核心参数：`-Xmx` 和 `-XX:MaxGCPauseMillis`**，其余尽量不要手调。

## 面试场景 12：GC 选择决策树

🎤 面试官

给你一个新项目，你会怎么选 GC？

🧑‍💻 你

```
堆大小 < 100MB？
├── 是 → Serial（单核小应用，没有并发的必要）
└── 否 → 停顿时间要求？
├── < 1ms（极致低延迟）→ ZGC / Shenandoah
├── < 200ms（低延迟）→ G1（JDK 9+ 默认就是它）
└── 无所谓（吞吐量优先）→ Parallel GC
```

**一句话总结**：JDK 17/21 生产环境**闭眼选 G1**。极低延迟需求再上 ZGC。Parallel GC 适合批处理/CICD 短任务。Serial 只适合嵌入式/客户端。CMS 已死，不要再提。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：触发一次 GC 并看日志

```
// 编译: javac GCDemo.java
// 运行: java -Xlog:gc*=info GCDemo
public class GCDemo {
public static void main(String[] args) {
for (int i = 0; i < 100; i++) {
byte[] arr = new byte[10 * 1024 * 1024]; // 10MB
}
System.out.println("Done.");
}
}
```

### 验证 2：对比不同 GC 的停顿

```
# Serial GC（纯 STW，停顿明显）
$ java -XX:+UseSerialGC -Xms512m -Xmx512m -Xlog:gc*=info GCDemo

# Parallel GC（吞吐量优先）
$ java -XX:+UseParallelGC -Xms512m -Xmx512m -Xlog:gc*=info GCDemo

# G1（默认，低停顿）
$ java -XX:+UseG1GC -Xms512m -Xmx512m -Xlog:gc*=info GCDemo

# ZGC（亚毫秒级，JDK 15+）
$ java -XX:+UseZGC -Xms512m -Xmx512m -Xlog:gc*=info GCDemo
```

### 验证 3：四种引用的回收行为

```
import java.lang.ref.*;

public class RefDemo {
public static void main(String[] args) {
// 强引用
Object strong = new Object();

// 软引用 —— 内存不足才回收
SoftReference<Object> soft = new SoftReference<>(new Object());

// 弱引用 —— 下次 GC 就回收
WeakReference<Object> weak = new WeakReference<>(new Object());

// 虚引用 —— 配合队列，GC 后收到通知
ReferenceQueue<Object> queue = new ReferenceQueue<>();
PhantomReference<Object> phantom = new PhantomReference<>(new Object(), queue);

System.gc();  // 建议 GC

System.out.println("强引用: " + strong);                    // 有值
System.out.println("软引用: " + soft.get());                // 不一定null（内存够就不回收）
System.out.println("弱引用: " + weak.get());                // null
System.out.println("虚引用: " + phantom.get());             // 永远 null
System.out.println("队列里有通知吗: " + (queue.poll() != null)); // true
}
}
```

### 验证 4：模拟 OOM 观察 GC 行为

```
import java.util.ArrayList;
import java.util.List;

// 运行: java -Xms64m -Xmx64m -XX:+HeapDumpOnOutOfMemoryError OOMDemo
public class OOMDemo {
public static void main(String[] args) {
List<byte[]> list = new ArrayList<>();
while (true) {
list.add(new byte[1024 * 1024]); // 每次 1MB
}
}
}
```

### 验证 5：finalize 复活演示（仅学习用）

```
public class FinalizeDemo {
static FinalizeDemo SAVE_HOOK;  // 复活钩子

public static void main(String[] args) throws Exception {
SAVE_HOOK = new FinalizeDemo();
SAVE_HOOK = null;
System.gc();
Thread.sleep(500);
System.out.println("第一次 GC 后: " + (SAVE_HOOK != null ? "复活了!" : "死了"));

SAVE_HOOK = null;
System.gc();
Thread.sleep(500);
System.out.println("第二次 GC 后: " + (SAVE_HOOK != null ? "复活了!" : "死了"));
// finalize 只能复活一次
}

@Override
protected void finalize() throws Throwable {
super.finalize();
System.out.println("finalize 执行!");
SAVE_HOOK = this; // 自救！
}
}
// 输出: finalize 执行! → 复活了! → 死了（第二次不再走 finalize）
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 JVM 怎么判断一个对象可以回收？</summary>

**可达性分析**：从 GC Roots 出发顺着引用链找，能到达的存活，到达不了的可回收。GC Roots 包括栈帧引用、静态变量、常量、JNI 引用等。引用计数法因为循环引用缺陷被 JVM 放弃。

</details>

<details>

<summary>Q2 标记-清除、标记-复制、标记-整理各有什么优缺点？</summary>

标记-清除：简单但有**碎片**；标记-复制：无碎片、分配快但**浪费一半内存**，适合存活率低的新生代；标记-整理：无碎片、无浪费但**移动对象成本高**（STW 长），适合老年代。

</details>

<details>

<summary>Q3 Minor GC 的完整流程是怎样的？对象什么时候晋升老年代？</summary>

Eden 满 → Eden + From Survivor 存活对象复制到 To Survivor → age + 1 → age 超过 15（MaxTenuringThreshold）或动态年龄判断触发 → 晋升老年代。四次提前晋升：大对象、Survivor 放不下、动态年龄、G1 Humongous。

</details>

<details>

<summary>Q4 CMS 的四个阶段和三大缺陷是什么？</summary>

四阶段：初始标记(STW) → 并发标记 → 重新标记(STW) → 并发清除。三大缺陷：CPU 敏感（并发占资源）、浮动垃圾 + Concurrent Mode Failure、内存碎片（标记-清除算法）。JDK 14 已移除。

</details>

<details>

<summary>Q5 G1 比 CMS 好在哪里？Region 设计解决了什么？</summary>

Region 化：堆不再物理隔离分代，而是切成 2048 个 Region，角色动态切换。好处：无碎片（复制/整理）、可预测停顿（MaxGCPauseMillis）、大堆友好。代价：RSet 维护和 SATB 有额外内存和 CPU 开销。

</details>

<details>

<summary>Q6 JDK 17/21 生产环境默认用什么 GC？极致低延迟选什么？</summary>

默认 **G1**（JDK 9+）。极致低延迟（<1ms 停顿）选 **ZGC**（JDK 15+ 生产可用，JDK 21+ 分代）。吞吐量优先批处理选 **Parallel GC**。Serial 仅用于客户端/嵌入式。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- 《深入理解 Java 虚拟机（第 3 版）》第 3 章「垃圾收集器与内存分配策略」—— 权威参考

- Oracle · HotSpot GC Tuning Guide (JDK 8)

- OpenJDK Wiki · ZGC —— ZGC 官方文档

- GCeasy —— 在线 GC 日志分析工具

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0034：**类文件结构** —— 打开一个 .class 文件看看里面到底是什么？魔数、常量池、访问标志、字段表、方法表，手把手拆解字节码。

💬 有任何疑问 —— 「G1 的 Mixed GC 和 Young GC 怎么区分？」「ZGC 的染色指针具体怎么实现的？」「线上 Full GC 频繁到底怎么定位？」—— 直接问我。GC 是面试最难的一关，我们一起拿下。


