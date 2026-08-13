> Lesson 0031 · 阶段四 · JVM · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码（含 3 种 OOM demo）· 5 道自测

# 0031 · JVM 内存区域详解

这一课覆盖的全部考点。**这是 JVM 面试三大硬骨头之一**（另外两个是 GC 和类加载）—— 面试官几乎一定会连环追问：

1. 「你能画出 JVM 运行时数据区图吗？每块存什么？」

2. 「哪些线程私有？哪些线程共享？」

3. 「JDK 8 之后方法区去哪了？为什么要改？」

4. 「你在生产环境见过哪种 OOM？怎么定位？」

答不上来直接扣分。这一课的目标是让你 *闭着眼睛能默画出内存区域图*，并且能对每一块讲出 *「存什么 + 谁独占 + 什么情况 OOM + 什么参数控制」*。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 JDK 8 之后方法区还叫方法区吗？还存在吗？</summary>

「方法区」是 **JVM 规范里的逻辑概念**，永远存在。JDK 8 只是换了实现：从 `PermGen`（永久代，在堆里）换成 `Metaspace`（元空间，在本地内存）。所以说「JDK 8 取消了方法区」是错的，应该说「JDK 8 用元空间实现方法区，取消了永久代」。

</details>

<details>

<summary>Q0.2 `"abc".intern()` 把字符串存到哪个区？</summary>

存到 **字符串常量池（String Table）**。JDK 6 常量池在*永久代*；JDK 7 起搬到*堆*里；JDK 8 元空间登场后，字符串常量池仍留在**堆**。所以 `intern()` 后拿到的引用指向堆内对象，会被普通 GC 回收。

</details>

## 面试场景 1：JVM 运行时数据区分几块？★核心必背

🎤 面试官

你能画出 JVM 运行时数据区（Runtime Data Areas）图吗？每一块的作用是什么？

🧑‍💻 你

按照 JVM 规范，运行时数据区一共 **5 块**，可分为「线程私有」和「线程共享」两类：

```
┌────────────────────── JVM 运行时数据区 ──────────────────────┐
│                                                              │
│   ┌────────────── 线程私有（每个线程独占一份） ─────────┐    │
│   │                                                     │    │
│   │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│   │  │   PC     │  │ JVM Stack    │  │ Native Stack │   │    │
│   │  │ (程序    │  │ (Java 虚拟   │  │ (本地方法栈) │   │    │
│   │  │  计数器) │  │  机栈)       │  │              │   │    │
│   │  └──────────┘  └──────────────┘  └──────────────┘   │    │
│   │                                                     │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                              │
│   ┌────────────── 线程共享（全 JVM 只有一份） ──────────┐    │
│   │                                                     │    │
│   │  ┌────────────────────┐  ┌───────────────────────┐  │    │
│   │  │       Heap         │  │  Method Area          │  │    │
│   │  │  （对象实例、数组、│  │  （类元数据、常量池、 │  │    │
│   │  │    GC 主战场）     │  │    JIT 代码缓存）     │  │    │
│   │  └────────────────────┘  └───────────────────────┘  │    │
│   │                                                     │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

区域线程存什么会 OOM 吗

程序计数器 PC私有当前字节码指令的地址（行号）**不会**（唯一）
Java 虚拟机栈私有栈帧（局部变量表、操作数栈、动态链接、方法出口）会 + StackOverflow
本地方法栈私有native 方法的栈帧会 + StackOverflow
堆 Heap共享几乎所有对象实例、数组会（最常见）
方法区（元空间）共享类元数据、方法字节码、运行时常量池、JIT 缓存会

追问 同一 JVM 实例里堆和元空间各只有一个吗？

是。**堆**是全 JVM 共享的一块连续（逻辑上）内存，从 JVM 启动到关闭只有一个实例；**元空间**也是全 JVM 共享一份。而 **PC、JVM 栈、本地方法栈**是每线程一份 —— 起 1000 个线程就有 1000 个 PC + 1000 个栈。所以栈的默认大小（`-Xss` 一般 512KB~1MB）× 线程数 会占用巨大内存，这也是「一个 JVM 起太多线程会 OOM」的原因。

追问 直接内存（Direct Memory）属于运行时数据区吗？

**严格说不属于**。JVM 规范里的运行时数据区只有上面 5 块，*直接内存不算*。它是 NIO（`ByteBuffer.allocateDirect()`）通过 `Unsafe.allocateMemory()` 在*堆外*分配的原生内存，不受 `-Xmx` 限制，但会受 `-XX:MaxDirectMemorySize` 和物理内存约束。生产环境 OOM 有一大部分是它 —— Netty、Kafka、Elasticsearch 都重度依赖直接内存。所以面试答题时要提一句：「直接内存虽然不在 JVM 规范里，但属于 Java 应用的 OOM 高发区。」

## 面试场景 2：程序计数器 PC —— 唯一不会 OOM 的区域

🎤 面试官

PC 程序计数器是干什么的？为什么是线程私有？

🧑‍💻 你

**PC (Program Counter Register)** 是一小块内存，可以看成 *「当前线程所执行的字节码的行号指示器」*。字节码解释器工作时，就是通过改变 PC 的值来选取下一条要执行的字节码指令 —— 分支、循环、跳转、异常处理、线程恢复等基础功能都依赖它。

为什么是线程私有：Java 是多线程的，OS 调度靠**时间片轮转**，一个 CPU 核心在任意时刻只执行一个线程。线程被切走再切回来时，得能*接着上次的位置继续跑*，所以每个线程必须有**自己独立的 PC**，互不干扰。

两个细节：

- 如果线程正在执行 **Java 方法**，PC 记录的是*正在执行的字节码指令地址*。

- 如果线程正在执行 **native 方法**，PC 值为 `undefined`（因为 native 走的是本地方法栈，不由 JVM 字节码解释器管）。

追问 PC 为什么是唯一不会 OOM 的区域？

因为它**存的东西不会增长**。PC 只是一个记录字节码偏移量的整数（几个字节），空间需求*固定且极小*，线程活着就存在、线程结束就回收，不像栈会随方法调用越压越深，也不像堆会随对象创建不断膨胀。JVM 规范里明确说：「此内存区域是唯一一个在 Java 虚拟机规范中没有规定任何 `OutOfMemoryError` 情况的区域。」

## 面试场景 3：Java 虚拟机栈 —— 方法调用的载体 ★核心

🎤 面试官

Java 虚拟机栈里存什么？一个栈帧包含哪几个部分？

🧑‍💻 你

Java 虚拟机栈（JVM Stack）是**线程私有**的，生命周期和线程相同。它描述的是 *Java 方法执行的内存模型*：**每个方法在调用时都会创建一个「栈帧」（Stack Frame）**压入栈顶，方法返回或抛异常时栈帧弹出。

一个栈帧内部有四大件：

1. **局部变量表（Local Variable Table）**：存放方法参数和方法内部定义的*基本类型*、*对象引用*（指向堆对象的指针）、*returnAddress*。以「变量槽 (slot)」为单位，long/double 占 2 个 slot，其它占 1 个。

2. **操作数栈（Operand Stack）**：字节码指令的工作台。`iadd`、`invokevirtual` 等指令都是从操作数栈取参数、把结果压回栈顶。

3. **动态链接（Dynamic Linking）**：指向运行时常量池中该栈帧所属方法的引用，支持运行时把符号引用解析成直接引用（配合多态、反射）。

4. **方法返回地址（Return Address）**：方法正常返回或异常返回时，恢复上层方法执行需要的位置信息。

栈的两种异常：

- `StackOverflowError`：线程请求的栈深度*大于*虚拟机允许的深度（栈大小固定的情况下）。经典触发场景：**无限递归**。

- `OutOfMemoryError`：如果栈是*可动态扩展*的，扩展时申请不到足够内存（HotSpot 里其实栈大小固定，主要是「起太多线程」时触发）。

陷阱 「Java 栈只存基本类型和引用，对象都在堆」—— 这句话*大部分场景成立*，但不严谨。开启逃逸分析（`-XX:+DoEscapeAnalysis`，JDK 7+ 默认开）后，JVM 可能对**未逃逸的小对象**做*标量替换*，把对象拆成基本类型直接放在栈上 —— 这就是所谓「栈上分配」。下一课 0032 会细讲。

追问 `-Xss` 参数越大越好吗？

不是。`-Xss` 控制**每个线程的栈大小**（默认 512KB~1MB，因平台而异）。调大能允许更深的递归，但每个线程都占更多内存 —— *能起的线程数就变少了*。一个进程虚拟内存有限，假设总量 4GB，`-Xss=1M` 顶多起 4000 线程，`-Xss=10M` 就只能起 400 线程了。所以微服务、Netty 这种高并发场景反而希望 `-Xss` 小一点。

## 面试场景 4：本地方法栈 Native Method Stack

🧑‍💻 你

本地方法栈和 Java 虚拟机栈作用非常相似，区别只在于：

- **虚拟机栈**为 *Java 方法*（字节码）服务。

- **本地方法栈**为 *native 方法*（用 C/C++ 写的、通过 JNI 调用的方法）服务，比如 `Object.hashCode()`、`Thread.currentThread()`、`System.arraycopy()`。

它同样是**线程私有**，同样会抛 `StackOverflowError` 和 `OutOfMemoryError`。

**关键实现细节**：*HotSpot 虚拟机把本地方法栈和 Java 虚拟机栈合二为一*。所以你在 HotSpot 里看不到两个独立的栈 —— 一个线程只有一个「栈」，Java 帧和 native 帧混着压。

追问 那 JVM 规范为什么还要把它拆成两块？

规范是*逻辑定义*，把语义分开是为了让不同厂商的 JVM 实现有选择余地 —— *可以*分开、也*可以*合并。HotSpot 出于实现简单和性能考量选择合并，其他 JVM（比如已停更的 J9）就可能真的拆成两块。面试答题时说清「规范上是两个，HotSpot 合成一个」，最能显示你读过规范。

## 面试场景 5：堆 Heap —— GC 的主战场 ★核心

🎤 面试官

堆的结构是怎样的？为什么要分代？

🧑‍💻 你

堆是 JVM 管理内存中**最大的一块**，被**所有线程共享**。*几乎所有的对象实例和数组*都在堆上分配（少数会栈上分配，见 0032）。堆是 **GC 的主战场**，也叫 GC 堆。

JDK 8 之前的堆结构（分代收集）：

```
┌──────────────────────── Heap ────────────────────────┐
│                                                      │
│  ┌────── Young Generation（新生代 1/3）─────────┐    │
│  │   ┌───────┐  ┌─────────┐  ┌─────────┐        │    │
│  │   │ Eden  │  │ Survivor│  │ Survivor│        │    │
│  │   │ 8/10  │  │  From   │  │   To    │        │    │
│  │   │       │  │  1/10   │  │   1/10  │        │    │
│  │   └───────┘  └─────────┘  └─────────┘        │    │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌────── Old Generation（老年代 2/3）───────────┐    │
│  │             长寿命对象、大对象               │    │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  ┌────── PermGen（永久代，仅 JDK 7 及以前）────┐    │
│  │        类元数据、方法字节码、常量池          │    │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

**JDK 8+ 的堆结构**：去掉了永久代，方法区改由*本地内存里的元空间*实现，堆内只剩新生代 + 老年代。

为什么分代？**「弱分代假说」**：绝大多数对象*朝生夕死*（新生代 Minor GC 每次能回收 90%+），少数对象存活很久（老年代）。分代之后可以对新老对象*用不同的 GC 算法*（新生代复制算法，老年代标记-整理/标记-清除），效率高得多。详见下一课 0033 GC。

追问 对象在新生代怎么「升级」到老年代？

三种情况：**① 年龄够了**（每熬过一次 Minor GC 年龄 +1，达到 `-XX:MaxTenuringThreshold` 默认 15 就晋升）；**② 大对象直接进老年代**（超过 `-XX:PretenureSizeThreshold` 的对象绕开 Eden）；**③ 动态年龄判定**（Survivor 中同龄对象累计大小超过 Survivor 一半，年龄 >= 该年龄的对象一起晋升）。对象头 Mark Word 里的年龄字段只有 *4 bit*，所以最大 15。

追问 堆一定连续吗？

**逻辑上连续，物理上可以不连续**。JVM 只保证从*用户视角*堆是一块连续的地址空间；实际底层可以是多段离散内存拼起来（尤其 G1、ZGC 这种 Region 化的收集器，堆被切成 2048 个 Region，之间可以是散的）。

## 面试场景 6：方法区 vs 元空间的历史演进 ★经典

🎤 面试官

JDK 8 为什么用元空间替换永久代？带来了什么好处？

🧑‍💻 你

维度PermGen（JDK 7 及以前）Metaspace（JDK 8+）

位置在**堆**里（虚拟机内存）在**本地内存**（Native Memory，堆外）
大小上限`-XX:MaxPermSize`，默认 64MB~82MB，*固定*`-XX:MaxMetaspaceSize`，*默认无上限*（受物理内存）
OOM 消息`OOM: PermGen space``OOM: Metaspace`
GC 触发只在 Full GC 时回收，*回收效率低*类卸载时回收，更及时
字符串常量池位置JDK 6 在永久代，JDK 7 已搬到堆在堆
典型问题动态生成类多（CGLIB/JSP）就爆基本不会爆，除非 `-XX:MaxMetaspaceSize` 限死

**为什么替换**：

1. **永久代大小死板**：`MaxPermSize` 固定，业务积累的类多了（Spring 反射生成、CGLIB 动态代理、Groovy 动态类）容易撑爆，运维只能加大参数重启。

2. **永久代回收难**：类元数据回收条件苛刻（该类所有实例被回收 + ClassLoader 被回收 + 无反射引用），大多数场景形同虚设。

3. **为 Oracle 合并 HotSpot 和 JRockit 铺路**：JRockit 从来没有永久代的概念，两个 JVM 要合并就必须统一。

**换成元空间的好处**：使用本地内存，*动态扩容*，不再受 JVM 内存限制；GC 更简单；避免 PermGen OOM。

追问 JDK 8 引入元空间后 OOM 变多了还是变少了？

**方法区相关的 OOM 变少了**。永久代时代，`-XX:MaxPermSize` 死锁在 64MB~256MB，业务一堆类就爆；元空间用本地内存动态扩容，只要物理内存够就不会 OOM。但也带来*新风险*：如果*不设 `-XX:MaxMetaspaceSize`*，元空间会一直吃本地内存直到把整个机器搞挂（更难排查）。所以生产环境**建议显式设置 `-XX:MaxMetaspaceSize`**，让 JVM 提前 OOM 好过让 OS OOM Killer 杀进程。

追问 元空间的关键参数有哪些？

`-XX:MetaspaceSize=N`：初始阈值，触发第一次 Full GC 卸载类的门槛。`-XX:MaxMetaspaceSize=N`：最大值，默认无限。`-XX:MinMetaspaceFreeRatio` / `-XX:MaxMetaspaceFreeRatio`：GC 后空闲比例，控制自动扩缩容节奏。

## 面试场景 7：方法区存什么？

🧑‍💻 你

方法区存的是 **「已被虚拟机加载的类信息」**，具体分四类：

1. **类元数据（Class Metadata）**：类的完整结构 —— 类名、修饰符、父类、接口、字段列表、方法列表（含每个方法的字节码）、访问标志。

2. **运行时常量池（Runtime Constant Pool）**：Class 文件里的常量池表，被加载到方法区后就叫运行时常量池，存字面量（字符串、数字）和符号引用（类名、方法名、字段名）。

3. **静态变量（Static Fields）**：*JDK 7 之前*在永久代；*JDK 7 起*已经搬到堆上（连着 `Class` 对象一起放堆）。所以严格说 JDK 8 元空间里已经不存静态变量了 —— 面试要小心这个陷阱。

4. **JIT 编译后的代码（Code Cache）**：C1/C2 编译产生的机器码，放在 *Code Cache*（也是方法区的一部分/相邻区域，视实现而定）。

陷阱 「静态变量在方法区」是**过时的说法**。JDK 7 起，静态变量和字符串常量池已经从永久代迁到*堆*里（跟 `Class` 对象一起）；JDK 8 元空间只放*类元数据 + 方法字节码 + 运行时常量池的符号引用*。所以标准答案是：「JDK 7 之前静态变量在方法区（永久代），JDK 7 之后在堆。」

## 面试场景 8：字符串常量池的搬家 ★经典

🎤 面试官

字符串常量池在哪个区域？`intern()` 方法的行为在 JDK 6 和 JDK 7 有什么区别？

🧑‍💻 你

JDK 版本字符串常量池位置`String.intern()` 行为

JDK 6永久代（PermGen 里）如果常量池不存在，*复制*一份到永久代
JDK 7堆（Heap）如果常量池不存在，*只存堆里对象的引用*（不复制）
JDK 8+堆（Heap）同 JDK 7

关键差异：JDK 7 之后 `intern()` *不再复制字符串*，只是把「堆里已存在的对象引用」登记到常量池表里。这就出现了 **经典面试题**：

```
// JDK 7+ 的诡异输出
String s1 = new StringBuilder("go").append("od").toString();
System.out.println(s1.intern() == s1);       // true

String s2 = new StringBuilder("ja").append("va").toString();
System.out.println(s2.intern() == s2);       // false
```

解释：`"good"` 之前从没被 JVM 加载过（不在常量池），`s1.intern()` 就把 s1 这个堆对象的引用登记进常量池，之后 `s1.intern()` 返回的正是 s1 本身，所以 `==` 为 `true`。

但 `"java"` 是 JVM 启动时就已经加载到常量池的字符串（`java.lang.String` 类名之类），s2.intern() 返回的是常量池里那个更早的对象，跟堆里 `new` 出来的 s2 不是同一个，所以 `==` 为 `false`。

追问 为什么 JDK 7 要把字符串常量池搬到堆？

因为永久代*只在 Full GC 时才回收*，字符串泛滥（尤其大量 `intern()`）会撑爆永久代；搬到堆之后，字符串常量池能被*普通 Young/Old GC 回收*，管理更灵活也更及时。这也为后来 JDK 8 干脆干掉永久代做了铺垫。

## 面试场景 9：对象在哪些区域被引用？

🧑‍💻 你

一个对象生活在堆里，但*指向它的引用*可能来自多个区域，这是 GC Roots 枚举的基础：

1. **虚拟机栈的局部变量表**：方法内的 `User user = new User()`，`user` 这个引用变量在栈帧的局部变量表里，指向堆里的 User 实例。方法返回、栈帧弹出，引用就没了 —— 对象可能被 GC。

2. **方法区中类的静态变量**：`public static User CURRENT_USER = ...`，静态字段（JDK 7+ 在堆里，作为 Class 对象的一部分）持有堆对象引用。类不卸载，引用就不断。

3. **方法区中的常量**：`public static final String NAME = "abc"`，常量池里的引用。

4. **本地方法栈中 JNI 引用的对象**：JNI Global Reference。

5. **被同步锁持有的对象**：`synchronized(lock)` 里的 lock。

6. **反映 Java 虚拟机内部情况的 JMXBean、JVMTI 回调等**。

这 6 类就是 **GC Roots** —— 可达性分析算法从它们出发，能到达的对象都是「存活」。

## 面试场景 10：各区域 OOM 触发场景 ★经典

🎤 面试官

你在生产环境遇到过哪些 OOM？怎么定位？

🧑‍💻 你

按区域分类，OOM 有 5 种典型形态：

类型报错典型原因排查手段

堆 OOM
`OOM: Java heap space`
`-Xmx` 太小；大对象（图片/Excel）没释放；集合类无限增长（如缓存无淘汰）
`jmap -dump:live,format=b,file=heap.hprof <pid>`；MAT / VisualVM 分析

GC 时间过长
`OOM: GC Overhead Limit Exceeded`
JVM 花 98% 时间 GC 但回收 < 2%；通常是堆快满、频繁 Full GC
GC 日志 `-Xlog:gc*`；调大堆或修复内存泄漏

栈 OOM / StackOverflow
`StackOverflowError`
*无限递归*；递归深度过深（如 JSON 深层嵌套）
看栈帧数量；重构成迭代或调大 `-Xss`

元空间 OOM
`OOM: Metaspace`
动态生成大量类 —— CGLIB 反复代理、Groovy/JSP、类加载器泄漏
`jcmd <pid> VM.metaspace`；限制动态类生成

直接内存 OOM
`OOM: Direct buffer memory`
NIO ByteBuffer 大量分配不释放；Netty/Kafka 频繁堆外
`-XX:MaxDirectMemorySize` 显式设置；关注 NMT（`-XX:NativeMemoryTracking`）

追问 一个对象什么情况下会分配在栈上而不是堆上？

需要满足三个条件：**① 开启逃逸分析**（`-XX:+DoEscapeAnalysis`，JDK 7+ 默认开）；**② 逃逸分析判定对象*未逃逸***（即对象只在方法内部使用，没被外部方法/线程/字段引用）；**③ 触发标量替换**（`-XX:+EliminateAllocations`），把对象拆成基本类型分别放栈上，从而完全绕开堆分配 —— 严格说不是「对象在栈上」，而是「对象被替换成了栈上的一堆基本变量」。下一课 0032 深挖。

追问 生产环境预防 OOM 的通用姿势？

**4 件套**：① `-XX:+HeapDumpOnOutOfMemoryError`（OOM 时自动 dump）；② `-XX:HeapDumpPath=/path/`（指定 dump 位置）；③ `-Xlog:gc*:file=gc.log`（GC 日志留证据）；④ 显式设置 `-Xmx = -Xms`（避免动态扩缩容抖动）+ `-XX:MaxMetaspaceSize`（防元空间失控）+ `-XX:MaxDirectMemorySize`（防堆外失控）。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：触发 StackOverflowError —— 栈深超限

```
/**
* 运行参数建议 -Xss256k（把栈调小，更容易观察）
* 输出：Exception in thread "main" java.lang.StackOverflowError
*      at StackOverflowDemo.recurse(StackOverflowDemo.java:6)
*      ...重复几千次...
*/
public class StackOverflowDemo {
private static int depth = 0;

public static void recurse() {
depth++;
recurse();          // ← 无限递归，栈帧永远不弹
}

public static void main(String[] args) {
try {
recurse();
} catch (Throwable t) {
System.out.println("栈深度：" + depth);   // 打印崩溃时的递归层数
t.printStackTrace();
}
}
}
```

观察点：把 `-Xss` 从 `256k` 改成 `1m`、`4m`，能看到递归深度线性增长 —— *栈大小和最大递归深度成正比*。

### 验证 2：触发堆 OOM —— Java heap space

```
import java.util.ArrayList;
import java.util.List;

/**
* 运行参数：-Xms20m -Xmx20m -XX:+HeapDumpOnOutOfMemoryError
* 输出：java.lang.OutOfMemoryError: Java heap space
*      Dumping heap to java_pid12345.hprof ...
*/
public class HeapOomDemo {
static class Blob { byte[] bytes = new byte[1024 * 1024]; }   // 1MB

public static void main(String[] args) {
List<Blob> list = new ArrayList<>();
int i = 0;
while (true) {
list.add(new Blob());        // 强引用不断累积，GC 无法回收
System.out.println("已分配 " + (++i) + "MB");
}
}
}
```

观察点：会在 15~18MB 附近爆 OOM（堆里还要给类元数据、栈等留位置），并生成 `.hprof` 文件 —— 用 *Eclipse MAT* 打开就能看到 ArrayList 里满满的 Blob，一眼定位泄漏点。

### 验证 3：触发元空间 OOM —— 动态生成海量类

```
import net.sf.cglib.proxy.Enhancer;
import net.sf.cglib.proxy.MethodInterceptor;

/**
* 依赖：cglib:cglib:3.3.0
* 运行参数：-XX:MaxMetaspaceSize=20m
* 输出：java.lang.OutOfMemoryError: Metaspace
*/
public class MetaspaceOomDemo {
static class Target { public void hello() {} }

public static void main(String[] args) {
int i = 0;
while (true) {
Enhancer enhancer = new Enhancer();
enhancer.setSuperclass(Target.class);
enhancer.setUseCache(false);        // ← 关键：关缓存，每次都生成新类
enhancer.setCallback((MethodInterceptor) (obj, method, argsX, proxy) ->
proxy.invokeSuper(obj, argsX));
enhancer.create();                  // 每次生成一个新 Class 塞进元空间
System.out.println("已生成第 " + (++i) + " 个动态类");
}
}
}
```

观察点：几千个类之后爆 `OOM: Metaspace`。这就是*为什么 Spring AOP 早期版本推荐启用 CGLIB 缓存*、以及为什么 **ClassLoader 泄漏**（如反复 `reload` Web 应用）会拖垮生产。

### 验证 4：观察局部变量在栈、对象在堆 —— javap 视角

```
public class WhereIsWhat {
public static void main(String[] args) {
int x = 42;                     // 基本类型 → 局部变量表
String s = "hello";             // 引用 → 局部变量表；字符串对象 → 堆里的常量池
WhereIsWhat w = new WhereIsWhat();   // 引用 → 局部变量表；对象实例 → 堆
}
}

// $ javap -c WhereIsWhat
// public static void main(java.lang.String[]);
//   Code:
//      0: bipush        42          ← 42 压入操作数栈
//      2: istore_1                  ← 存到局部变量表 slot 1（x）
//      3: ldc           #7          ← 从运行时常量池加载 "hello"
//      5: astore_2                  ← 引用存到局部变量表 slot 2（s）
//      6: new           #9          ← 在堆上分配对象
//      9: dup
//     10: invokespecial #11         ← 调用 <init>（构造器）
//     13: astore_3                  ← 引用存到 slot 3（w）
//     14: return
```

观察点：`istore_1`/`astore_2`/`astore_3` 都在操作局部变量表；`new` 指令才是在堆里分配。字节码把「谁存哪」讲得一清二楚。

### 验证 5：字符串常量池的位置（JDK 7+ 在堆里）

```
import java.util.ArrayList;
import java.util.List;

/**
* 运行参数：-Xmx10m -Xms10m -XX:-UseGCOverheadLimit
* JDK 7+ 输出：java.lang.OutOfMemoryError: Java heap space
*   ← 注意是 heap space，不是 PermGen，说明常量池在堆
*/
public class StringPoolLocationDemo {
public static void main(String[] args) {
List<String> keeper = new ArrayList<>();   // 防止 GC 回收 intern 的字符串
int i = 0;
while (true) {
String s = String.valueOf(i++).intern();  // 每个新数字都 intern 进常量池
keeper.add(s);
}
}
}
```

观察点：如果字符串常量池在*永久代*（JDK 6 及以前），OOM 会是 `OOM: PermGen space`；JDK 7+ 报的是 `Java heap space`，直接证明字符串常量池**已经搬到堆里**。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 JVM 运行时数据区分几块？哪几块线程私有？哪几块线程共享？哪一块不会 OOM？</summary>

5 块：**程序计数器 PC、Java 虚拟机栈、本地方法栈**（三者线程私有）+ **堆、方法区**（两者线程共享）。其中 *PC 是唯一不会 OOM 的区域*，因为它存的是当前字节码指令地址（固定大小的整数），不会随程序运行膨胀。

</details>

<details>

<summary>Q2 一个栈帧包含哪四大件？</summary>

**局部变量表**（存基本类型和对象引用）、**操作数栈**（字节码指令的工作台）、**动态链接**（指向运行时常量池中方法的引用，支持运行时符号解析）、**方法返回地址**（方法返回或异常时用来恢复调用者上下文）。

</details>

<details>

<summary>Q3 JDK 8 为什么用元空间替换永久代？带来了什么好处？</summary>

因为永久代大小死板（`MaxPermSize` 固定，动态类多容易爆）、GC 效率低（只在 Full GC 回收）、和 JRockit 合并需要统一模型。元空间用*本地内存*、大小*动态扩容*、GC 更及时，避免了永久代 OOM。代价：如果不设 `-XX:MaxMetaspaceSize`，可能吃光本地内存拖垮机器。

</details>

<details>

<summary>Q4 字符串常量池在 JDK 6、7、8 分别在哪个区？</summary>

JDK 6 在*永久代*；JDK 7 起搬到*堆*；JDK 8 元空间登场后，字符串常量池*仍留在堆*。搬到堆的目的是让常量池能被普通 GC 回收，不再依赖 Full GC。

</details>

<details>

<summary>Q5 生产环境列举 5 种 OOM，各由什么触发？</summary>

① `Java heap space` —— 大对象/缓存无淘汰/堆太小；② `GC Overhead Limit` —— 频繁 Full GC 但回收极少；③ `StackOverflowError` —— 无限递归或栈太小；④ `Metaspace` —— 动态生成大量类（CGLIB / ClassLoader 泄漏）；⑤ `Direct buffer memory` —— NIO 堆外内存未释放。防御姿势：`-XX:+HeapDumpOnOutOfMemoryError` + 显式设 `-Xmx = -Xms` + `-XX:MaxMetaspaceSize` + `-XX:MaxDirectMemorySize`。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JVMS §2.5 · Runtime Data Areas —— 官方规范原文

- HotSpot GC Tuning Guide · Metaspace —— 元空间调参指南

#### 🔗 关联课件

-

-

-

-

-

#### 🧭 下一课预告

Lesson 0032：**对象的创建、内存布局与访问定位** —— 追一个对象从 `new` 到访问的完整生命周期，包含逃逸分析、TLAB、对象头、句柄 vs 直接指针的抉择。

💬 有任何疑问 —— 「这块内存实际生产遇到过什么坑？」「MAT 怎么分析 hprof？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


