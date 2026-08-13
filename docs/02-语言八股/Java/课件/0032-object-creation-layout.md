> Lesson 0032 · 阶段四 · JVM · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0032 · 对象创建 & 内存布局 & 逃逸分析

上一节  讲了 JVM 的运行时内存划分 —— 堆、栈、方法区、程序计数器、直接内存。这一节把镜头拉近，聚焦到堆里最重要的居民 **对象**：*怎么被创造出来*、*在内存里长什么样*、*JIT 优化后甚至可能连堆都不进*。

这套内容是 **阿里、字节、美团 JVM 面试的高频三连击**：「new 一个对象经过哪几步？」→「一个对象在内存里几个部分？」→「听说过逃逸分析吗？」。答不上来会被直接判定为「JVM 只停留在 GC 参数调优的皮毛」。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `new Object()` 从 CPU 拿到指令到把引用赋给变量，中间经过哪几步？</summary>

五步：类加载检查 → 分配内存 → 初始化零值 → 设置对象头 → 执行 `<init>` 构造器。面试场景 1 会展开。

</details>

<details>

<summary>Q0.2 Java 里所有对象都必然分配在堆上吗？</summary>

不一定。开启逃逸分析后，JIT 可能把「未逃逸的对象」拆成基本类型放**栈**上（标量替换 + 栈上分配）。面试场景 5、6 详细讲。

</details>

## 面试场景 1：new 一个对象经过哪几步？⭐核心

🎤 面试官

你在代码里写 `Person p = new Person("张三", 20);`，JVM 层面到底做了哪些事？

🧑‍💻 你

标准答案是 **五步**：

1. **类加载检查**：碰到 `new` 字节码指令，先在常量池里定位 `Person` 的*符号引用*，检查这个类有没有被加载、解析、初始化。没有的话先触发类加载（走双亲委派）。

2. **分配内存**：类加载确定后，对象大小就是确定的了 —— 从堆里划一块出来。分配方式有两种：*指针碰撞*（堆规整时）和 *空闲列表*（堆有碎片时）。为解决并发分配冲突，还会走 *TLAB* 或 *CAS + 失败重试*。

3. **初始化零值**：把分配到的这块内存（*不含对象头*）全部置零。这就是为什么 Java 字段不显式赋值也有默认值：`int = 0`、`Object = null`、`boolean = false`。

4. **设置对象头**：往对象头里写元信息 —— 类型指针（指向 `Person` 的 `Class` 元数据）、GC 分代年龄、hashCode（延迟填）、锁标志（初始 01 无锁）等。

5. **执行 `<init>`**：调构造器，按程序员意愿把 `name = "张三"`、`age = 20` 赋进去。只有这一步跑完，对象才是「业务上可用」的。

做完这五步，栈上的 `p` 才拿到这个对象在堆里的引用地址。

追问 指针碰撞和空闲列表分别适用什么 GC？

**指针碰撞**要求堆里已用内存和空闲内存*严格连续* —— 分配时只要把「分界指针」往空闲那侧挪对象大小的距离就行。适用于 **Serial / ParNew / G1** 这些基于「复制算法」或「标记-整理」的收集器，因为它们回收后堆是紧凑的。**空闲列表**则是维护一个「哪些块空闲、哪些块占用」的表，分配时找一块足够大的划出去。适用于 **CMS** 这种「标记-清除」收集器，因为它回收后会留下碎片，堆不规整。

追问 分配内存这一步在多线程下怎么保证不冲突？

两种方案，HotSpot 都用：一是 **CAS + 失败重试**，多个线程 CAS 抢分界指针，抢输了重试；二是 **TLAB（Thread Local Allocation Buffer）**，每个线程在 Eden 里预分配一小块自己的「私人柜台」，柜台里的分配走指针碰撞免锁，柜台用完了才回主流程抢公共内存。TLAB 是默认打开的，面试场景 9 会细讲。

## 面试场景 2：对象在内存里长什么样？⭐核心

🎤 面试官

HotSpot 里一个对象的内存布局分几部分？各存什么？

🧑‍💻 你

三部分：**对象头（Header）+ 实例数据（Instance Data）+ 对齐填充（Padding）**。

```
┌────────────────── Object Layout ──────────────────┐
│                                                    │
│  ┌──────────── Header ────────────┐               │
│  │  Mark Word    (8 bytes)         │  ← 锁/hash/GC │
│  │  Klass Pointer(8 or 4 bytes)    │  ← 类型指针   │
│  │  [Array Length](4 bytes, 仅数组) │              │
│  └─────────────────────────────────┘               │
│                                                    │
│  ┌──────── Instance Data ─────────┐               │
│  │  long / double 字段              │              │
│  │  int / float 字段                │              │
│  │  short / char 字段               │              │
│  │  byte / boolean 字段             │              │
│  │  reference 字段                  │              │
│  └─────────────────────────────────┘               │
│                                                    │
│  ┌────────── Padding ─────────────┐               │
│  │  填 0，让整个对象大小为 8 的倍数  │              │
│  └─────────────────────────────────┘               │
└────────────────────────────────────────────────────┘
```

- **对象头**：两部分 ——「Mark Word」8 字节，存 hashCode / GC 分代年龄 / 锁状态；「Klass Pointer」类型指针，64 位默认 8 字节，*开启指针压缩后 4 字节*；如果是数组对象再多 4 字节存长度。

- **实例数据**：字段值本身。HotSpot 会按类型宽度*重排*字段（long/double 优先，同宽度的字段挨在一起放），目的是尽量填满 8 字节槽，减少 Padding。父类字段永远排在子类字段前面。

- **对齐填充**：仅仅是占位，让整个对象大小对齐到 **8 字节的倍数**。原因是 CPU 按 8 字节字宽读内存，未对齐会跨 cacheline 或触发两次内存访问，慢一倍。

追问 一个空 `new Object()` 占多少字节？

64 位 JVM 默认开启指针压缩：Mark Word 8 字节 + Klass Pointer *4 字节*（压缩过）+ 实例数据 0 字节 = 12 字节。**加 4 字节 Padding 对齐到 16 字节**。如果关闭指针压缩（`-XX:-UseCompressedOops`），Klass Pointer 变 8 字节，总共 16 字节，此时 Padding 为 0。所以标准答案：**开压缩 16 字节、关压缩 16 字节，恰好都是 16**（Object 太小，压缩省下的 4 字节又被 Padding 补回去了）。用 `ClassLayout.parseInstance(new Object())` 可以亲眼验证。

追问 为什么 HotSpot 要按类型重排字段？

为了**省内存**。假设按声明顺序放 `byte a; long b; byte c;`，会因为 `long` 要 8 字节对齐而在 `a` 后面填 7 字节，`c` 后面再填 7 字节，浪费 14 字节。HotSpot 重排成 `long b; byte a; byte c;`，只在末尾填 6 字节，节省 8 字节。规则是「宽度大的先放」（long/double → int/float → short/char → byte/boolean → reference），同宽度的连着放。父类字段永远在最前面，避免破坏子类内存偏移。

## 面试场景 3：Mark Word 具体存了什么？

🎤 面试官

对象头里的 Mark Word 具体是什么结构？

🧑‍💻 你

Mark Word 是一个 **64 位**（64 位 JVM）的紧凑数据区，采用*分时复用*的设计 —— 同一段位在不同锁状态下代表不同含义。低 2 位是**锁标志位**，决定整体怎么解读：

锁状态低 2 位其余位含义

无锁`01`unused(25) | hashCode(31) | age(4) | biased=0(1)
偏向锁`01`threadId(54) | epoch(2) | age(4) | biased=1(1)
轻量级锁`00`指向栈中 Lock Record 的指针(62)
重量级锁`10`指向 Monitor（ObjectMonitor）的指针(62)
GC 标记`11`GC 用（表明对象已被标记）

这正是  讲锁升级路径 *无锁 → 偏向锁 → 轻量级锁 → 重量级锁* 的底层依据 —— 升级本质上就是改写这 2 位标志 + 换其他位的含义。

陷阱 JDK 15 起 **偏向锁被废弃**（`-XX:+UseBiasedLocking` 默认关），因为现代应用大量使用线程池，偏向锁的收益抵不过撤销偏向的成本。JDK 18 直接删除。所以现在的 Mark Word 通常只在「无锁 / 轻量级 / 重量级」三态间切换。

## 面试场景 4：对象访问方式 —— 句柄 vs 直接指针

🎤 面试官

栈上的 `reference` 变量怎么找到堆里的对象？

🧑‍💻 你

JVM 规范没规定，主流实现有两种：

```
【方案 A · 句柄访问】
Stack                Heap
┌────────┐    ┌──────────────┐    ┌────────────────┐
│ ref ───┼──► │ 句柄池        │    │ 对象实例数据    │
└────────┘    │ ├─inst ptr ──┼───►│                │
│ └─type ptr ──┼─┐  └────────────────┘
└──────────────┘ │  ┌────────────────┐
└─►│ 类型元数据      │
└────────────────┘

【方案 B · 直接指针】（HotSpot 采用）
Stack                Heap
┌────────┐    ┌──────────────────┐
│ ref ───┼──► │ Header (klass ptr)│──► 类型元数据
└────────┘    │ Instance Data     │
└──────────────────┘
```

- **句柄**：堆里划出一块句柄池，`reference` 存的是句柄地址；句柄里再放两个指针 —— 一个指向实例数据、一个指向类型信息。*优点*：GC 移动对象时只改句柄里的实例数据指针，`reference` 本身不用动。*缺点*：每次访问对象要两次指针跳转，慢。

- **直接指针**：`reference` 直接存对象地址，对象头里的 Klass Pointer 指类型信息。*优点*：一次寻址就到，快。*缺点*：GC 移动对象时需要更新所有指向它的 `reference`。

**HotSpot 用直接指针**，因为对象访问远比 GC 移动频繁，用「访问速度」换「GC 更新成本」值得。

追问 直接指针方案下 GC 移动对象后怎么更新引用？

靠 **OopMap**（Oop = Ordinary Object Pointer）—— HotSpot 在 JIT 编译时会在*安全点*记录当前栈帧里哪些槽位是对象引用。GC 触发时所有线程停到安全点，GC 就能精确知道每个引用在哪、直接改写它们指向新地址。这也是「精确式 GC」相对「保守式 GC」（C/C++ Boehm GC 那种猜哪个是指针）的优势。

## 面试场景 5：什么是逃逸分析？⭐核心

🎤 面试官

听说过逃逸分析吗？它能做什么？

🧑‍💻 你

**逃逸分析（Escape Analysis）**是 JIT 编译器的一项静态分析优化 —— 分析一个对象的作用域是否*逃出了它被创建的方法或线程*。根据结果分三档：

- **不逃逸**：对象只在方法内使用，方法返回时就消失。→ 可以做 *栈上分配 / 标量替换 / 同步消除*。

- **方法逃逸**：对象被作为返回值返回、被塞进外部集合，逃出了当前方法但没跨线程。→ 只能保守分配到堆，但可以做 *同步消除*。

- **线程逃逸**：对象被赋给了共享变量、被其他线程访问。→ 必须堆分配 + 保留同步。

基于分析结果，JIT 会做三种优化：

1. **栈上分配**（面试场景 6）：不逃逸 → 放栈里。

2. **标量替换**（面试场景 6）：把对象拆成基本类型字段，直接当局部变量用。

3. **锁消除**（面试场景 7）：加锁但没逃出线程 → 锁没意义，直接删掉。

逃逸分析在 HotSpot 里由 `-XX:+DoEscapeAnalysis` 控制，从 JDK 8 起**默认开启**（-server 模式，Server VM）。

追问 逃逸分析为什么不总是生效？

三个原因：**(1) JIT 需要预热** —— 方法调用次数超过 `-XX:CompileThreshold`（Server VM 默认 10000）才会被 JIT 编译，之前解释器执行时全都老实堆分配。**(2) 分析本身有开销**，JIT 只在觉得「值得」时才做（比如方法足够热、对象足够简单）。**(3) 保守性**：一旦分析不出来对象是否逃逸（比如通过反射操作、复杂的方法内联失败），JIT 会保守假定「逃逸了」，走堆分配。可以用 `-XX:+PrintEscapeAnalysis` 和 `-XX:+PrintEliminateAllocations` 观察哪些对象被消除了。

## 面试场景 6：栈上分配 & 标量替换 ⭐核心

🎤 面试官

逃逸分析发现对象没逃逸，具体是怎么把它「不放堆里」的？

🧑‍💻 你

准确说 HotSpot 目前*不做真正意义上的栈上分配*，而是通过 **标量替换（Scalar Replacement）** 达到「不进堆」的效果。

假设有代码：

```
void hot() {
Point p = new Point(1, 2);   // 未逃逸
System.out.println(p.x + p.y);
}
class Point { int x, y; Point(int x, int y){ this.x=x; this.y=y; } }
```

JIT 优化后等效于：

```
void hot() {
int p_x = 1;   // ← 标量替换：把 Point 拆成两个 int 局部变量
int p_y = 2;
System.out.println(p_x + p_y);
}
```

- **标量替换**：把「聚合对象」拆解为一组基本类型（scalar）字段，就当它们是普通的局部变量。

- 拆掉之后，这些 int 直接躺在栈帧的局部变量表里，**方法返回栈帧弹出就自然回收**，完全不给 GC 添麻烦。

- 控制参数：`-XX:+DoEscapeAnalysis`（开逃逸分析）+ `-XX:+EliminateAllocations`（开标量替换），默认都开。

好处：**降低 GC 压力、避免堆分配开销、提升缓存命中率**（栈本身在 L1 cache 里）。这是为什么循环里创建大量小对象在 JIT 预热之后并不总是灾难。

追问 那「栈上分配」这个说法从哪来的？

《深入理解 Java 虚拟机》里提到栈上分配是逃逸分析的一种*理论上的*优化方向，但 HotSpot 从来没实现「整个对象放栈上」这种做法 —— 而是选择更彻底的**标量替换**：连对象概念都不留，直接把字段当局部变量。所以面试时严谨的表述是「逃逸分析 → *标量替换* → 效果等价于栈上分配」。

## 面试场景 7：锁消除（Lock Elision）

🎤 面试官

逃逸分析除了栈上分配还能做什么优化？举个锁消除的例子。

🧑‍💻 你

逃逸分析发现某个 **锁对象没有逃出当前线程**，那这个锁就没有任何意义 —— 单线程访问不需要同步。JIT 直接把 `monitorenter / monitorexit` 字节码消掉。

经典例子是 `StringBuilder`：

```
String concat(String s1, String s2, String s3) {
StringBuffer sb = new StringBuffer();   // 注意是 StringBuffer 不是 StringBuilder
sb.append(s1);
sb.append(s2);
sb.append(s3);
return sb.toString();
}
```

`StringBuffer.append` 是 `synchronized` 的，理论上每次调用都要加锁。但这里 `sb` 是局部变量，构造完就在方法内被消费，**不可能有其他线程访问**。JIT 逃逸分析发现后直接把三次 `synchronized` 消掉，运行时和 `StringBuilder` 性能几乎一样。

参数：`-XX:+EliminateLocks`，默认开启。

追问 锁消除和锁粗化是一回事吗？

不是。**锁消除**是「本来该加的锁被证明没必要加，删掉」；**锁粗化（Lock Coarsening）**是「本来分散在多次调用里的加锁，被合并成一次大的加锁」—— 比如连续 100 次 `sb.append()`，每次都加锁解锁开销很大，JVM 会把 100 次加锁合并成「第一次进入前加一次、最后一次退出时解一次」。两者都是同步优化，但方向不同：一个是*消除*，一个是*合并*。

## 面试场景 8：指针压缩 CompressedOops

🎤 面试官

什么是指针压缩？为什么要压缩？

🧑‍💻 你

64 位 JVM 里原生指针（`oop`，Ordinary Object Pointer）默认是 **8 字节**。但绝大多数应用堆都不会超过几十 GB —— 用 8 字节纯属浪费。**CompressedOops** 把堆内对象指针从 8 字节压到 **4 字节**存储，访问时再动态还原成 64 位地址。

原理是**左移 3 位对齐**：

```
物理地址 = 压缩指针 << 3   （相当于 × 8）
```

因为对象都是 8 字节对齐的，最低 3 位一定是 0，直接省略。4 字节能表示 2³² = 42 亿个「对齐槽位」，每槽 8 字节，最多可寻址 **32 GB 堆**。

- 参数：`-XX:+UseCompressedOops`（对象指针）+ `-XX:+UseCompressedClassPointers`（Klass 指针），JDK 8+ 默认开。

- 堆超过 32 GB 时 JVM 自动关闭指针压缩，此时反而*更费内存*（每个对象头多 4 字节，每个引用多 4 字节）—— 所以有个经验法则：**要么堆 < 32G 用压缩，要么堆 > 48G 才划算不压缩**，中间的 32-48G 是「大坑区」。

追问 指针压缩为什么恰好支持 32 GB？

因为 **2³² × 8 字节 = 32 GB**。4 字节压缩指针能寻址 2³² 个位置，每个位置代表一个 8 字节的对齐槽（对象地址一定是 8 的倍数所以能省 3 位）。所以最大可寻址堆 = 2³² × 8 = 32 GB。想要更大的堆就得用 8 字节完整指针，或调 `-XX:ObjectAlignmentInBytes=16` 换 64 GB 上限（代价是 Padding 更多）。

追问 指针压缩为什么小堆能省 20-40% 内存？

典型 Java 应用里，堆内容大约 40% 是对象头 + 引用类型字段。指针压缩把 Klass Pointer 从 8 字节→4 字节，把所有 `Object`、`String`、集合内的引用字段都从 8 字节→4 字节。假设应用里引用占 40%，指针压缩正好把这 40% 折半，总内存节省 **20% 左右**；引用密集型应用（比如大量 `HashMap`）能到 30-40%。

## 面试场景 9：TLAB 是什么？

🎤 面试官

多线程同时 `new` 对象会不会抢内存？JVM 怎么处理？

🧑‍💻 你

会。100 个线程同时 `new`，如果都去堆里抢分界指针，那就是 100 个线程 CAS 抢一个指针 —— 竞争极其激烈。HotSpot 用 **TLAB（Thread Local Allocation Buffer）** 解决：

- 线程启动时，在 Eden 里预分配一小块（默认 *Eden / (线程数 × 2)*）作为该线程的私有缓冲区。

- 该线程之后 `new` 对象，先在自己的 TLAB 里指针碰撞分配 —— **免锁，无竞争**。

- TLAB 用光了或对象太大放不下，才回主流程走公共 Eden 的 CAS 分配。

参数：`-XX:+UseTLAB`（默认开）；`-XX:TLABSize` 调初始大小；`-XX:+PrintTLAB` 观察每个线程的使用情况。

追问 TLAB 会不会导致内存浪费？

会 —— 每个线程的 TLAB 用不完时也是它「独占」的，其他线程没法用。所以 HotSpot 会做动态调整（`-XX:+ResizeTLAB`）：根据线程分配频率动态调 TLAB 大小；线程结束时归还剩余给 Eden；GC 时也会重置。此外 TLAB 用完前如果剩余空间放不下下一个对象但还有一点空间，会做*refill*（丢弃剩余、重新申请一块）—— 但也不是无脑丢，有个`-XX:TLABRefillWasteFraction` 阈值控制。

## 面试场景 10：对象的三种「去处」

🎤 面试官

Java 对象一定分配在堆上吗？梳理一下对象可能出现在哪里。

🧑‍💻 你

三种去处：

位置触发条件回收方式典型例子

**堆（默认）**
普通 `new`，逃逸出方法
GC 管理
成员变量、返回给外部的对象

**栈**（标量替换）
JIT 逃逸分析发现未逃逸 + 结构简单
栈帧弹出自动回收
方法内临时的 `Point`、`Iterator`

**直接内存**
显式调 `ByteBuffer.allocateDirect(n)` 或 `Unsafe.allocateMemory`
`Cleaner` 弱引用 + `System.gc`；`Unsafe.freeMemory`
Netty 的 `DirectByteBuf`、NIO 零拷贝

「堆外内存」不受堆大小 `-Xmx` 限制，但受 `-XX:MaxDirectMemorySize` 限制，超了会抛 `OutOfMemoryError: Direct buffer memory`。Netty 就是靠堆外内存 + 池化实现零 GC、高性能。

追问 为什么直接内存能避免一次内存拷贝？

常规 `ByteBuffer` 在堆内 —— 做 IO 时数据要先从堆拷到*非堆的 native buffer*，再由 OS 送到网卡（因为堆内内存可能被 GC 移动，OS 不敢直接引用）。`DirectByteBuffer` 直接分配在堆外的 native 内存，OS 可以直接读写，**省掉一次「堆内→堆外」拷贝**。适合大数据量、高频 IO 场景。代价是分配和释放比堆内慢很多。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：用 JOL 库观察对象内存布局 ⭐必看

JOL（Java Object Layout）是 OpenJDK 官方出的工具，能精确打印对象在内存里每个字节的用途。Maven 依赖：

```
<dependency>
<groupId>org.openjdk.jol</groupId>
<artifactId>jol-core</artifactId>
<version>0.17</version>
</dependency>
```

```
import org.openjdk.jol.info.ClassLayout;
import org.openjdk.jol.vm.VM;

public class JolDemo {
static class Point {
boolean flag;
int x;
long y;
Object ref;
}

public static void main(String[] args) {
// 打印 JVM 环境（是否开启指针压缩、对齐字节数）
System.out.println(VM.current().details());

// 打印空 Object 布局
System.out.println(ClassLayout.parseInstance(new Object()).toPrintable());

// 打印自定义对象布局
System.out.println(ClassLayout.parseInstance(new Point()).toPrintable());
}
}
```

典型输出（64 位、开压缩）：

```
java.lang.Object object internals:
OFFSET  SIZE   TYPE DESCRIPTION                VALUE
0     4        (object header: mark)      0x0000000000000001
4     4        (object header: mark)      0x0000000000000000
8     4        (object header: class)     0x00000007
12     4        (object alignment gap)     ← 4 字节 Padding
Instance size: 16 bytes    ← 一个空 Object = 16 字节

JolDemo$Point object internals:
OFFSET  SIZE      TYPE DESCRIPTION
0     4           (object header: mark)
4     4           (object header: mark)
8     4           (object header: class)
12     4       int Point.x            ← int 排在 boolean 前面！
16     8      long Point.y            ← long 靠后但对齐
24     4    Object Point.ref
28     1   boolean Point.flag
29     3           (object alignment gap)
Instance size: 32 bytes
```

观察点：(1) 空 Object 就是 16 字节；(2) 字段被 HotSpot **按类型宽度重排**，声明顺序 `boolean flag; int x; long y; Object ref` 变成实际布局 `int → long → Object → boolean`；(3) 最后 3 字节 Padding 让总大小对齐到 32。

### 验证 2：验证指针压缩

用两个 JVM 参数分别跑一次 JolDemo，观察 Object 布局的差异：

```
# 关闭指针压缩
$ java -XX:-UseCompressedOops JolDemo
# 输出里 class pointer 变 8 字节，Object 头变 16 字节，无 Padding

# 开启指针压缩（默认）
$ java -XX:+UseCompressedOops JolDemo
# class pointer 4 字节，头 12 字节 + 4 字节 Padding = 16 字节
```

### 验证 3：证明标量替换真的会「消除」对象分配

```
public class EscapeDemo {
static int sum;
static class Point { int x, y; Point(int x, int y){this.x=x; this.y=y;} }

public static void main(String[] args) {
long start = System.currentTimeMillis();
for (int i = 0; i < 100_000_000; i++) {
allocate(i, i + 1);
}
System.out.println("耗时: " + (System.currentTimeMillis() - start) + " ms");
System.out.println("sum = " + sum);
}

static void allocate(int a, int b) {
Point p = new Point(a, b);   // 未逃逸 —— 会被标量替换
sum += p.x + p.y;
}
}
```

```
# 开启逃逸分析（默认）
$ java EscapeDemo
耗时: ~300 ms    ← 快

# 强制关闭逃逸分析
$ java -XX:-DoEscapeAnalysis EscapeDemo
耗时: ~3000 ms   ← 慢 10 倍，因为每次循环真的 new Point，GC 累死
```

差距会非常明显 —— 这就是逃逸分析 + 标量替换的威力。

### 验证 4：观察锁消除

```
public class LockElisionDemo {
public static void main(String[] args) {
long start = System.currentTimeMillis();
for (int i = 0; i < 10_000_000; i++) {
concat("a", "b", "c");
}
System.out.println("耗时: " + (System.currentTimeMillis() - start) + " ms");
}

public static String concat(String s1, String s2, String s3) {
StringBuffer sb = new StringBuffer();   // 未逃逸的 synchronized 对象
sb.append(s1).append(s2).append(s3);
return sb.toString();
}
}
```

```
# 默认（锁消除开启）
$ java LockElisionDemo
耗时: ~200 ms

# 关闭锁消除
$ java -XX:-EliminateLocks LockElisionDemo
耗时: ~800 ms   ← 每次 append 老实加锁解锁
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 new 一个对象的完整五步是什么？</summary>

类加载检查 → 分配内存（指针碰撞 / 空闲列表）→ 初始化零值（不含对象头）→ 设置对象头（类型指针、GC 年龄等）→ 执行 `<init>` 构造器。

</details>

<details>

<summary>Q2 对象的内存布局三部分是什么？各占大概多少字节？</summary>

对象头（Mark Word 8 字节 + Klass Pointer 4/8 字节，数组多 4 字节长度）+ 实例数据（字段值，按类型宽度重排）+ 对齐填充（补到 8 的倍数）。空 Object 通常 16 字节。

</details>

<details>

<summary>Q3 逃逸分析能做哪三种优化？哪些默认开启？</summary>

栈上分配（*实际是标量替换*）、标量替换、锁消除。三个都默认开：`-XX:+DoEscapeAnalysis`、`-XX:+EliminateAllocations`、`-XX:+EliminateLocks`。JDK 8+ 的 Server VM 默认全开。

</details>

<details>

<summary>Q4 指针压缩支持的最大堆是多少？为什么？超过后会怎样？</summary>

32 GB。因为 4 字节压缩指针 = 2³² 个对齐槽，每槽 8 字节，2³² × 8 = 32 GB。超过后 JVM 自动关掉指针压缩，回到 8 字节完整指针 —— 此时每个对象头多 4 字节、每个引用多 4 字节，内存反而变大。所以 32-48 GB 是「大坑区」，堆要么小于 32G，要么大于 48G 才划算。

</details>

<details>

<summary>Q5 Java 对象一定分配在堆上吗？梳理三种去处。</summary>

不一定。三种：(1) **堆**（默认，GC 管）；(2) **栈**（JIT 逃逸分析 → 标量替换后，字段变局部变量）；(3) **直接内存**（`ByteBuffer.allocateDirect`、`Unsafe.allocateMemory`，堆外，`Cleaner` 或手动释放）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- 《深入理解 Java 虚拟机（第 3 版）》第 2 章「Java 内存区域与内存溢出异常」§2.3 HotSpot 虚拟机对象探秘 —— 权威参考

- OpenJDK · JOL（Java Object Layout）项目主页 —— 观察对象布局的标准工具

- HotSpot Wiki · CompressedOops —— 指针压缩官方文档

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0033：**JVM 垃圾回收算法与收集器** —— 对象在堆里怎么被回收？可达性分析、三色标记、Serial/CMS/G1/ZGC 全景。

💬 有任何疑问 —— 「JOL 打印出来对不上怎么办？」「逃逸分析在我业务里真能生效吗？」「指针压缩关掉性能会怎样？」—— 直接问我。我是你的老师，也是你的追问陪练。


