> Lesson 0030 · 阶段四 · JVM · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0030 · JVM 概览 & 组成结构 & 常见面试题

欢迎进入 **阶段四 · JVM**。前面的  我们只是从「Java 语言」的角度顺带扫了一眼 JVM；从这一节开始，我们要正式把 JVM 拆开来看。JVM 是 Java 后端面试的**第三大硬块**（前两块 集合、并发 我们已经过完），而且它有个特点：*问得又杂又细*。GC、类加载、内存模型、字节码、JIT、JVM 参数……随便一个都能追问 20 分钟。

本课定位是**阶段四的开篇 · 全景图**：宽而不深，给你一个能挂住后面 7 节内容的骨架。0031 讲运行时数据区、0032 讲对象创建与内存布局、0033 讲 GC、0034 讲 GC 收集器、0035/0036 讲类加载、0037 讲 JVM 参数与调优 —— 现在你脑子里先要有一张「JVM 是什么、由什么组成、代码怎么跑起来」的完整地图。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 JVM 是一个东西还是一份规范？HotSpot 和 JVM 是什么关系？</summary>

JVM 首先是一份**规范**（`JVMS · Java Virtual Machine Specification`），规定字节码指令、内存模型、类文件格式等；HotSpot 是这份规范的**一个实现**（Oracle/OpenJDK 官方实现），还有其他实现如 GraalVM、OpenJ9、Azul Zing 等。所以「JVM」这个词经常兼指规范和实现，要看语境。

</details>

<details>

<summary>Q0.2 一段 Java 代码从 `.java` 到最终在 CPU 上执行，经过了哪几步？</summary>

大致 6 步：**①** 源码 `.java` → **②** `javac` 编译成字节码 `.class` → **③** 类加载器把 `.class` 装进 JVM → **④** 字节码进入运行时数据区（方法区存元数据、栈上开栈帧） → **⑤** 执行引擎（解释器/JIT）翻译字节码 → **⑥** CPU 执行机器码。

</details>

## 面试场景 1：JVM 到底是什么？⭐核心

🎤 面试官

你能用两三句话向一个非 Java 开发讲清楚 JVM 是什么吗？

🧑‍💻 你

JVM（Java Virtual Machine，Java 虚拟机）是一台**「虚构出来的计算机」**：它有自己的指令集（字节码）、自己的内存模型（堆、栈、方法区）、自己的执行引擎。Java 程序不直接运行在物理 CPU 上，而是运行在 JVM 上，由 JVM 把字节码翻译成当前平台的机器码。

它有三个关键身份：

- **一份规范**：由 Oracle 维护的 *JVMS · Java Virtual Machine Specification*，规定字节码指令、`.class` 文件格式、运行时数据区、类加载机制等。

- **多个实现**：HotSpot（Oracle/OpenJDK 官方）、GraalVM、Eclipse OpenJ9（原 IBM J9）、Azul Zing 等，都符合 JVMS，但内部实现各不相同。

- **跨平台的核心**：不同 OS/CPU 各自有一份 JVM 实现，字节码在上面是通用的 —— 这就是 Java *「一次编译，到处运行」* 的技术基石。

追问 JVM 和 JRE、JDK 谁包含谁？

包含关系：**JDK ⊃ JRE ⊃ JVM**。JVM 是执行字节码的虚拟机；JRE = JVM + 基础类库（`java.lang`、`java.util` 等），只想「跑」Java 程序装它就够；JDK = JRE + 开发工具（`javac`、`javap`、`jstack`、`jmap` 等），要「开发」必装 JDK。JDK 9 之后 Oracle 不再单独发 JRE，因为 `jlink` 可以按需裁剪运行时。详见 。

## 面试场景 2：HotSpot、JVM、OpenJDK 是什么关系？

🎤 面试官

你平时用的是 HotSpot 吗？HotSpot、JVM、OpenJDK 之间是什么关系？还有哪些 JVM 实现？

🧑‍💻 你

关系是「规范 → 实现 → 发行版」这条链：

```
JVMS 规范（Oracle 维护）
│
├── HotSpot         ← Oracle/OpenJDK 官方 JVM 实现（99% 的开发者都在用）
├── GraalVM         ← Oracle 新一代多语言 JVM，支持 AOT Native Image
├── Eclipse OpenJ9  ← 原 IBM J9，主打低内存和快启动
├── Azul Zing       ← 商业版，主打无停顿 GC（C4）
└── ... （历史上还有 JRockit，已并入 HotSpot）

发行版（JDK Distribution）
│
├── Oracle JDK      ← Oracle 官方，商用有 License 限制
├── OpenJDK         ← 开源参考实现，HotSpot 就在里面
├── Adoptium Temurin ← 社区维护的 OpenJDK 构建
├── Amazon Corretto ← 亚马逊维护的 OpenJDK 构建
└── Azul Zulu / Zing、Alibaba Dragonwell、腾讯 Kona ...
```

要点：

1. **JVM 是规范，HotSpot 是最主流的实现**。你 `java -version` 输出里通常会看到 *「HotSpot 64-Bit Server VM」*。

2. **OpenJDK 是「JDK 的开源参考实现」**，包含了 HotSpot；各家发行版（Temurin、Corretto、Dragonwell）本质都是从 OpenJDK 源码构建。

3. 不同 JVM 实现的字节码是通的（都遵循 JVMS），但 GC、JIT、内存策略差异巨大。

追问 同一段 Java 代码在不同 JVM 实现下会有性能差异吗？

**会，而且可能很大**。差异主要来自三处：**①** GC 策略不同（HotSpot G1 vs Zing C4 vs OpenJ9 gencon）；**②** JIT 激进度不同（GraalVM 的 Graal 编译器比 HotSpot C2 更激进）；**③** 内存布局和对象头压缩策略不同（OpenJ9 主打「更省内存」，同样应用能少用 30-50% 堆）。生产选型时通常会做 A/B 压测，别只看 benchmark。

## 面试场景 3：JVM 由哪几部分组成？⭐核心

🎤 面试官

能画一下 JVM 的整体架构吗？它由哪几个核心子系统组成？

🧑‍💻 你

JVM 的架构可以拆成 **5 大块**：

```
┌────────────────────────── JVM ──────────────────────────┐
│                                                          │
│   ①  类加载子系统 (ClassLoader Subsystem)                 │
│         Bootstrap → Extension/Platform → App → Custom    │
│         负责：加载 .class → Class 对象 → 方法区           │
│                       │                                  │
│                       ▼                                  │
│   ②  运行时数据区 (Runtime Data Areas)                    │
│         ┌─── 线程共享 ───┐   ┌── 线程私有 ──┐             │
│         │  堆 Heap        │   │  程序计数器 PC │           │
│         │  方法区(元空间) │   │  Java 虚拟机栈 │           │
│         └────────────────┘   │  本地方法栈    │           │
│                              └───────────────┘           │
│                       │                                  │
│                       ▼                                  │
│   ③  执行引擎 (Execution Engine)                          │
│         解释器 Interpreter  +  JIT 编译器 (C1/C2/Graal)   │
│         + 垃圾回收器 GC (作为执行引擎的一部分)             │
│                       │                                  │
│                       ▼                                  │
│   ④  本地方法接口 JNI (Java Native Interface)             │
│         Java 调 C/C++ 库的桥梁 (native 方法)              │
│                       │                                  │
│                       ▼                                  │
│   ⑤  本地方法库 (Native Method Libraries)                 │
│         libjvm.so、libc、libssl 等 OS 层动态库             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

一句话总结每块的职责：

- **类加载子系统**：把磁盘/网络上的 `.class` 加载进 JVM，生成 `Class` 对象，放到方法区。

- **运行时数据区**：程序运行时占用的所有内存 —— 堆放对象、栈放方法调用、方法区放类元数据。

- **执行引擎**：把字节码「翻译」成机器码。冷代码走解释器，热代码走 JIT。GC 也归执行引擎管。

- **JNI**：Java 调用 C/C++ 库的桥梁。`Thread.currentThread()`、`Object.hashCode()`、`System.arraycopy()` 底下都是 native。

- **本地方法库**：JVM 自身实现（`libjvm.so`）和依赖的 OS 库（`libc` 等）。

追问 「执行引擎」和「垃圾回收器」是并列关系还是包含关系？

严格按 HotSpot 架构划分，**GC 是执行引擎的一部分**。执行引擎负责「代码怎么跑」，包含解释器、JIT 编译器、垃圾回收器三个子模块。之所以经常把 GC 单独拎出来讲，是因为 GC 太重要、变化太快（Serial → Parallel → CMS → G1 → ZGC → Shenandoah 一路演进），面试问得也最多，所以在教学上单独成一大块。

## 面试场景 4：Java 代码的完整执行链条

🎤 面试官

从写 `Hello.java` 到 CPU 上跑出 `Hello, World`，中间到底发生了什么？

🧑‍💻 你

把  里的链条画得更细：

```
[写代码]
Hello.java  (源码，人类可读)
│
│  javac Hello.java     ← 编译阶段 (Java 源码 → 字节码)
▼
Hello.class (字节码，JVM 可读)
│
│  java Hello           ← 启动 JVM
▼
┌── JVM 启动 ─────────────────────────────────┐
│                                              │
│  ① 类加载子系统                              │
│     BootStrap → Ext → App → 加载 Hello.class │
│     解析成 Class 对象，放到 方法区(元空间)   │
│                    │                         │
│                    ▼                         │
│  ② 运行时数据区                              │
│     - main 线程创建 → 分配 PC/虚拟机栈       │
│     - 调 main() → push 栈帧                  │
│     - 遇到 new Object → 堆上分配             │
│                    │                         │
│                    ▼                         │
│  ③ 执行引擎                                  │
│     - 冷代码：解释器 逐条翻译字节码          │
│     - 热代码：JIT (C1/C2) 编译成机器码       │
│                    │                         │
│                    ▼                         │
│  ④ CPU 执行机器码                            │
│                                              │
└──────────────────────────────────────────────┘
│
▼
Hello, World  ← 通过 JNI 调 write() 系统调用输出
```

核心是三层翻译：**源码 → 字节码 → 机器码**。第一层由 `javac` 静态完成，第二层由 JVM 运行时动态完成（解释器边走边翻，JIT 挑热点批量翻）。

追问 类加载是「一次全加载」还是「用到才加载」？

**「用到才加载」**，即*惰性加载 · Lazy Loading*。JVM 只在**主动使用**一个类时才触发加载（如 `new`、访问静态字段/方法、反射、初始化子类等）。启动 `Hello` 只会加载 `Hello` 和它直接引用到的类，不会一口气把整个 classpath 全加载。0035 会展开讲。

## 面试场景 5：运行时数据区一览（为 0031 铺路）

🎤 面试官

JVM 的运行时数据区分哪几块？每一块存什么？哪些是线程共享，哪些是线程私有？

🧑‍💻 你

JVMS 定义了 **5 个** 运行时数据区，按线程可见性分成两类：

区域可见性存什么OOM 可能

**程序计数器 PC**
线程私有
当前线程执行的字节码指令地址
*唯一无 OOM 的区域*

**Java 虚拟机栈**
线程私有
方法调用的栈帧（局部变量表、操作数栈、返回地址）
StackOverflowError / OOM

**本地方法栈**
线程私有
native 方法调用的栈帧
StackOverflowError / OOM

**堆 Heap**
线程共享
所有对象实例和数组（GC 主战场）
OOM: Java heap space

**方法区（元空间）**
线程共享
类元数据、常量池、静态变量、JIT 代码缓存
OOM: Metaspace

助记口诀：*「一个计数、两个栈、一堆一区」*。计数器和两个栈是**随线程生死**的（线程结束就没了），堆和方法区是**跟着 JVM 生死**的（JVM 关了才回收）。

追问 Java 8 之后为什么把「永久代」改成「元空间」？

三个原因：**①** 永久代*大小固定*（`-XX:PermSize/-XX:MaxPermSize`），加载类多时容易 `OOM: PermGen space`，尤其是热部署反复加载类的场景；**②** 元空间用*本地内存*（Native Memory），只受机器物理内存限制，可自动扩容，默认无上限；**③** 配合 JDK 9 模块系统和字符串常量池已经在 JDK 7 迁到堆的优化，永久代已经没有存在必要，Oracle 顺势合并 HotSpot 和 JRockit 时干掉了它。

追问 程序计数器为什么是唯一不会 OOM 的区域？

因为它只存一个「当前执行到哪一条字节码指令的地址」，**大小固定**（就是一个指针宽度），不会随程序运行动态增长，所以不可能内存不足。JVMS 明确规定这块区域没有 `OutOfMemoryError`。

## 面试场景 6：执行引擎 —— 解释器 vs JIT（回顾 0001，细讲）

🎤 面试官

JVM 的执行引擎里，解释器和 JIT 编译器是什么关系？为什么两个都要有？

🧑‍💻 你

HotSpot 采用**「解释器 + JIT」混合模式**，两者互补：

```
字节码
│
├─────► 解释器 Interpreter (启动即用)
│           ▲
│           │  统计执行次数
│           ▼
├─────► JIT 编译器 (方法/循环 热点后触发)
│           │
│           ├── C1 客户端编译器 (Client Compiler)
│           │     快速编译，弱优化 (适合启动、GUI)
│           │
│           └── C2 服务端编译器 (Server Compiler)
│                 慢速编译，激进优化
│                 (内联、逃逸分析、去虚化、循环展开...)
│
└─────► 机器码 → CPU 执行
```

为什么两个都要有：

- **启动阶段**：JIT 还没积累 profile 数据，只能保守编译，收益低甚至负收益 → *解释器负责启动*，秒级出结果。

- **冷代码**：只执行一两次的方法，JIT 编译的开销（几十 ms - 秒级）远大于收益 → *解释器直接跑*，省 CPU 和内存。

- **热代码**：反复执行的方法（Web 服务的核心接口、计算循环）→ *JIT 编译成机器码*，性能可以逼近甚至超越 C++ 静态编译。

- **去优化 Deoptimization**：JIT 基于假设做的激进优化（如「这个方法从来没抛过异常」）一旦被打破，需要*回退到解释器*重新执行 —— 解释器是保底方案。

追问 HotSpot 是怎么判定「热点代码」的？

**基于计数器**：每个方法维护 *方法调用计数器*，每个循环维护 *回边计数器*（Back Edge Counter）。超过阈值就触发 JIT。Client 模式阈值 `1500`，Server 模式 `10000`，可用 `-XX:CompileThreshold` 调。回边计数器专门用来支持 **OSR（On-Stack Replacement，栈上替换）**—— 在一个巨大的循环还没跑完时，能把方法编译成机器码然后*在栈上直接切换*。

追问 解释器为什么还没被 JIT 完全取代？

三个理由：**①** *启动阶段没有 profile*，JIT 拿不到分支预测/类型频率信息，编译不出好代码；**②** *冷代码 JIT 收益为负*，编译一个只跑一次的方法纯属浪费；**③** *去优化时需要回退*，解释器是保底。所以现代 JVM 都是「解释器 + JIT」的混合执行模型，未来也不太可能砍掉解释器。

## 面试场景 7：JVM 规范 vs JVM 实现

🎤 面试官

你能说清 JLS、JVMS、HotSpot 分别是什么，以及它们的关系吗？

🧑‍💻 你

缩写全称规定什么面向谁

**JLS**
Java Language Specification
Java *语言* 语义：关键字、语法、类型系统、泛型、Lambda
Java 语言开发者

**JVMS**
Java Virtual Machine Specification
JVM *行为*：`.class` 文件格式、字节码指令集、内存模型、类加载机制
JVM 实现者

**JMM**
Java Memory Model
多线程 *可见性/有序性*：happens-before、volatile、synchronized 语义（是 JLS 的一部分）
并发程序员 + JVM 实现者

**HotSpot**
—
JVMS 的*一个 C++ 实现*，包含解释器、C1/C2 JIT、多种 GC
使用者（我们）

关系可以类比：**JLS/JVMS 是「HTTP 协议规范」，HotSpot 是「Nginx」**—— 规范定义「必须支持哪些行为」，实现决定「用什么算法怎么实现得又快又省」。

追问 一个 JVM 实现只要符合 JVMS 就够了吗？

不够。**Java SE 认证 (TCK · Technology Compatibility Kit)** 才是「你能不能叫自己 Java」的准入证。TCK 包含数万个测试用例，覆盖 JLS + JVMS + 标准类库行为。GraalVM、OpenJ9、Azul Zing 都通过了 TCK，所以能合法叫「Java 虚拟机」。历史上 Google 在 Android 里用 Dalvik/ART，因为没通过 TCK 就不敢自称 Java（当年还被 Oracle 告到最高法院打了十年官司）。

## 面试场景 8：GraalVM 是什么？和 HotSpot 有什么区别？

🎤 面试官

最近这几年很火的 GraalVM 是什么？和 HotSpot 相比有什么优势和劣势？

🧑‍💻 你

GraalVM 是 Oracle 从 2018 年开始主推的**新一代多语言 JVM**，核心组件有三个：

1. **Graal 编译器**：用 *Java* 写的 JIT 编译器（HotSpot 的 C2 是用 C++ 写的，可维护性差）。可以作为 HotSpot 的 JIT 替换项，激活参数 `-XX:+UseJVMCICompiler`。

2. **Truffle 框架**：让 JavaScript、Python、Ruby、R 都能跑在 JVM 上，且互相调用（Polyglot）。

3. **Native Image (AOT)**：把 Java 程序 **提前编译成独立的原生可执行文件**（Linux ELF / Windows EXE），启动几十毫秒、内存占用几十兆，无需 JVM。

和 HotSpot 的核心区别：

维度HotSpotGraalVM (JIT 模式)GraalVM Native Image (AOT)

编译器C1 + C2 (C++)C1 + Graal (Java)Graal AOT (构建时)
启动时间秒级 (需预热)秒级 (需预热)几十毫秒
峰值性能高*某些场景略高*低于 JIT (无 profile)
内存占用大 (JVM + JIT 代码缓存)大小 (几十 MB)
反射/动态代理完全支持完全支持*需构建时声明*
典型场景长时间运行的 Web 服务吞吐敏感的服务Serverless、CLI 工具

追问 GraalVM Native Image 能替代 HotSpot 吗？

**不能全面替代，是互补关系**。适合替代 HotSpot 的场景：Serverless（AWS Lambda 冷启动）、CLI 工具（GraalVM 自己的 `native-image` 命令就是 native）、K8s Function、边缘计算。不适合的场景：长期运行的 Web 服务 —— HotSpot 预热后的 JIT 峰值性能仍然占优，因为它有*运行时 profile*，能做出比 AOT 更激进的优化（内联、去虚化、逃逸分析基于真实调用频率）。

追问 Spring Boot 3.x 为什么要押注 GraalVM？

为了打「云原生」的仗。传统 Spring Boot 启动 3-10 秒、内存 200-500 MB，在 Serverless/K8s 场景冷启动完全不能看。Spring Boot 3 + Native Image 编译后启动 50ms、内存 50MB，可以直接跟 Go/Rust 的服务竞争。代价是构建时间从秒级涨到几分钟，且反射需要 `reflect-config.json` 显式声明（Spring 提供了 `@RegisterReflectionForBinding` 等工具类降低负担）。

## 面试场景 9：JIT 分级编译（C1/C2 是什么？）

🎤 面试官

你提到过 C1 和 C2，能展开讲讲吗？为什么要分级？

🧑‍💻 你

HotSpot 有两个 JIT 编译器：

- **C1 (Client Compiler)**：编译速度快，优化少（方法内联、无用代码消除等简单优化），启动性能好，峰值性能一般。历史上是 *Client 模式* 的默认编译器。

- **C2 (Server Compiler)**：编译速度慢（可能几百 ms），但做**激进优化**：深度内联、逃逸分析（栈上分配、锁消除、标量替换）、循环展开、去虚化（devirtualization）、公共子表达式消除等，峰值性能极高。历史上是 *Server 模式* 的默认编译器。

JDK 7 引入 **分级编译 (Tiered Compilation)**，默认开启（`-XX:+TieredCompilation`）后 HotSpot 会*同时使用 C1 和 C2*，代码经过 5 层演进：

```
Level 0: 解释器执行 (刚启动)
│
▼
Level 1: C1 编译，无 profile 信息 (小方法，一步到位)
│
▼
Level 2: C1 编译，带方法调用计数 (中等热度)
│
▼
Level 3: C1 编译，带完整 profile (方法/循环/类型 信息)
│
▼
Level 4: C2 编译，基于 Level 3 的 profile 做激进优化 (最热的代码)
```

好处：*启动快*（先走 Level 1/3 快速拿到编译代码），*峰值高*（最热的代码最终升到 Level 4）。JDK 8 之后这是默认策略，几乎不需要手动调。

追问 什么时候会关掉分级编译？

两种情况：**①** *纯短命 CLI 工具*，只用解释器 + C1（`-XX:TieredStopAtLevel=1`），省掉 C2 编译成本；**②** *某些老应用调优*，怀疑 C2 编译出的机器码触发了 JIT bug 时，可以退到只用 C1 观察是否复现。日常业务几乎从不需要动。

## 面试场景 10：JVM 常见面试题总览（本课的地图 → 后续课的入口）

🎤 面试官

你觉得 JVM 面试通常会问哪些方向？

🧑‍💻 你

JVM 面试基本围绕 **7 大主题**展开，每个主题至少能追问 15 分钟。这也是我们阶段四剩余课程的分工：

主题典型问题对应课

① 内存区域
堆栈方法区各存什么？OOM 有哪几种？

② 对象创建
`new` 一个对象经过哪几步？对象在堆里怎么布局？
0032

③ 垃圾回收
怎么判定对象死亡？三种 GC 算法？分代回收？

④ 垃圾收集器
Serial/Parallel/CMS/G1/ZGC 分别适合什么场景？
0034

⑤ 类加载机制
类加载七阶段？双亲委派？怎么破坏？
0035

⑥ 类加载器
Bootstrap/Ext/App/自定义 分工？Tomcat 打破双亲委派的原因？
0036

⑦ JVM 参数与调优
`-Xmx`/`-Xms`/`-Xss` 怎么调？OOM 怎么排查？
0037

今天这节的作用就是**让你脑子里有全景图**：知道每个问题属于哪一块，问某一块的时候能自然带出上下文（比如问 GC 时你能主动提「GC 主要发生在堆，方法区元数据 GC 触发条件不同」）。后面每节课我们会逐块深挖。

陷阱 面试官很喜欢**「跳块提问」**—— 你在讲 GC，他突然问「那类加载器和 GC 有什么关系？」。答案是：*类加载器本身也是对象，也会被 GC 回收*；一个类被卸载的条件之一就是「加载它的 ClassLoader 已经不可达」。所以面试时不要死守单一主题，要能自然链接。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：看看你用的是哪个 JVM 实现

```
$ java -version
openjdk version "21.0.1" 2023-10-17
OpenJDK Runtime Environment Temurin-21.0.1+12 (build 21.0.1+12)
OpenJDK 64-Bit Server VM Temurin-21.0.1+12 (build 21.0.1+12, mixed mode, sharing)

# 关键字段解读：
# openjdk           ← 发行版是 OpenJDK 系
# Temurin           ← 由 Eclipse Adoptium 社区构建
# 64-Bit Server VM  ← 用的是 HotSpot Server 模式
# mixed mode        ← 解释器 + JIT 混合模式 (默认)
# sharing           ← 开启了 Class Data Sharing (CDS) 提速启动
```

### 验证 2：观察 JIT 编译日志

```
// HotJit.java
public class HotJit {
public static void main(String[] args) {
long sum = 0;
for (int i = 0; i < 100_000_000; i++) {
sum += hot(i);
}
System.out.println(sum);
}
static long hot(int x) { return x * 2L + 1; }
}
```

```
$ javac HotJit.java
$ java -XX:+PrintCompilation HotJit

55    1       3       java.lang.String::hashCode (49 bytes)
56    2       3       java.lang.Object::<init> (1 bytes)
...
123    8       4       HotJit::hot (7 bytes)              ← C2 (Level 4) 编译了 hot 方法
123    5       3       HotJit::main (25 bytes)            ← C1 (Level 3) 编译了 main

# 输出列含义：
# 时间戳(ms)  编译ID  Level  方法名  字节码大小
# Level 3 = C1 带 profile，Level 4 = C2 激进优化
```

### 验证 3：观察分级编译的效果

```
$ time java HotJit                                # 默认: 分级编译 (C1+C2)
real    0m0.42s

$ time java -XX:-TieredCompilation HotJit          # 关闭分级，只用 C2
real    0m0.58s   ← 启动慢了 (C2 编译成本高)

$ time java -XX:TieredStopAtLevel=1 HotJit         # 只到 C1，不上 C2
real    0m0.61s   ← 峰值弱了 (C1 优化少)

# 结论：默认的分级编译是启动速度和峰值性能的最优折中，别乱关
```

### 验证 4：观察运行时数据区各分块（用 jcmd 看内存）

```
// LongRunning.java
public class LongRunning {
public static void main(String[] args) throws Exception {
// 让程序跑起来，方便 jcmd 观察
Thread.sleep(60_000);
}
}

$ javac LongRunning.java
$ java LongRunning &
[1] 12345

$ jcmd 12345 VM.native_memory summary
Native Memory Tracking:
Total: reserved=1234MB, committed=234MB
-                 Java Heap (reserved=256MB, committed=64MB)   ← 堆
(mmap: reserved=256MB, committed=64MB)
-                     Class (reserved=1024MB, committed=8MB)   ← 元空间 (方法区)
-                    Thread (reserved=20MB, committed=2MB)     ← 虚拟机栈
-                      Code (reserved=245MB, committed=8MB)    ← JIT 代码缓存
-                        GC (reserved=6MB, committed=6MB)      ← GC 元数据
-                  Compiler (reserved=2MB, committed=2MB)      ← JIT 编译器

# 每一行就对应本课讲的一块。Java Heap = 堆，Class = 元空间，Thread = 栈
# 需要启动时加 -XX:NativeMemoryTracking=summary
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话解释 JVM、HotSpot、OpenJDK 三者的关系。</summary>

JVM 是一份**规范**（JVMS）；HotSpot 是这份规范的**官方实现**（C++ 写的）；OpenJDK 是**包含 HotSpot 的开源 JDK 发行版**。你日常用的 Temurin、Corretto、Dragonwell 本质都是从 OpenJDK 源码构建，跑的都是 HotSpot。

</details>

<details>

<summary>Q2 JVM 的核心组成有哪 5 块？分别负责什么？</summary>

① **类加载子系统**：加载 `.class`；② **运行时数据区**：程序运行时的所有内存（堆、栈、方法区、PC、本地方法栈）；③ **执行引擎**：解释器 + JIT + GC，负责翻译字节码和回收内存；④ **JNI**：调 C/C++ 库的桥梁；⑤ **本地方法库**：`libjvm.so` 和 OS 库。

</details>

<details>

<summary>Q3 Java 代码从 `.java` 到 CPU 执行的完整链条是什么？</summary>

① `javac` 编译源码为字节码 `.class`；② 启动 JVM，类加载器加载 `.class` 到方法区，生成 `Class` 对象；③ 创建主线程，分配 PC 和虚拟机栈；④ 调 `main()`，栈上开栈帧、堆上分配对象；⑤ 执行引擎翻译字节码：冷代码走解释器，热代码 JIT (C1/C2) 编译为机器码；⑥ CPU 执行机器码，通过 JNI 调 OS 系统调用输出。

</details>

<details>

<summary>Q4 运行时数据区的 5 块里，哪些是线程私有，哪些是线程共享？哪一块唯一不会 OOM？</summary>

线程私有：**程序计数器、Java 虚拟机栈、本地方法栈**（随线程生死）；线程共享：**堆、方法区（元空间）**（随 JVM 生死）。**程序计数器**是唯一不会 OOM 的区域 —— 它只存一个字节码指令地址，大小固定不增长。

</details>

<details>

<summary>Q5 HotSpot 为什么要「解释器 + JIT」混合模式？分级编译 (C1+C2) 又解决了什么问题？</summary>

混合模式的原因：**启动阶段**走解释器（JIT 还没 profile）；**冷代码**走解释器（编译成本高于收益）；**热代码**走 JIT（性能极高）；**去优化**时回退到解释器（保底）。分级编译 (Tiered Compilation) 让 C1 和 C2 同时用：C1 快速编译拿到早期性能，C2 基于 C1 收集的 profile 做激进优化拿到峰值性能，兼顾启动速度和峰值性能。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Oracle · Java Virtual Machine Specification (Java SE 21) —— JVMS 官方规范

- OpenJDK · HotSpot Group —— HotSpot 官方主页

- GraalVM · Docs —— GraalVM 官方文档

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0031：**JVM 运行时数据区详解** —— 把今天扫过的堆/栈/方法区/PC/本地方法栈逐块拆开，讲清每一块的结构、大小限制、OOM 触发条件、面试最爱问的追问。

💬 有任何疑问 —— 「HotSpot 和 OpenJ9 到底该怎么选？」「Graal 编译器是 JIT 还是 AOT？」「分级编译具体几层，能不能只用 C1？」—— 直接问我。我是你的老师，也是你的追问陪练。


