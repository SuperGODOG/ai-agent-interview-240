# Java 核心、JVM 与并发编程面试题索引

> **分类描述**: 涵盖 HashMap 底层与位运算寻址、ConcurrentHashMap、线程池核心参数、JMM 内存模型、volatile 内存屏障、GC 垃圾收集与类加载机制。
> **题目统计**: 共 21 题
> **唯一语料数据源**: `agent-project-grill/references/题库/items.json`

| 题目 ID | 行号 | 深度 | 标签 | 题目简述 |
|---|---|---|---|---|
| `L337` | 337 | LNone | Java | 请对比进程和线程的区别。为什么主流应用（如Java）更倾向于使用多线程而非多进程？线程上下文切换的开销主要体现在哪些方面？ |
| `L338` | 338 | LNone | Java | 请详细阐述 Java 线程池的工作原理、核心参数以及任务拒绝策略。 |
| `L339` | 339 | LNone | Java | 请介绍JVM的内存区域划分，说明哪些区域是线程私有、哪些是线程共享的，并解释为什么程序计数器不会发生内存溢出（OOM）。在JVM堆内存的分代模型中，为什么新生代要设计成一个Eden区加两个Survivor区的结构？ |
| `L340` | 340 | LNone | Java | 如果让你脱离 JDK 自行设计一个线程池组件，你会如何设计它的核心数据结构和任务调度流程？ |
| `L341` | 341 | LNone | Java | Java 中的 Class 文件是如何被加载到 JVM 中的？请详细描述类加载的双亲委派模型及生命周期。 |
| `L347` | 347 | LNone | Java | 在生产环境中，如果遇到堆内存溢出（OOM），通常的排查思路和步骤是什么？如何有效区分内存泄漏（Memory Leak）与内存溢出（Out of Memory）？ |
| `L349` | 349 | LNone | Java | 请谈谈对 Spring Boot 框架核心设计思想的理解，是否深入阅读过其核心源码？ |
| `L350` | 350 | LNone | Java | 请详细阐述 Spring Boot 的启动流程与自动装配原理（Auto-Configuration）。 |
| `L351` | 351 | LNone | Java | 在阅读 Spring Boot 源码的过程中，针对配置加载机制（如 PropertySource、Binder 等）的源码实现有何理解？ |
| `L353` | 353 | LNone | Java | 在高并发或生产环境下使用 RocketMQ 时，遇到过哪些常见问题（如消息堆积、重复消费、消息丢失），如何解决？ |
| `L354` | 354 | LNone | Java | 针对分布式消息传递，如何设计可靠的消息消费幂等性方案？ |
| `L417` | 417 | L3 | Java | CompletableFuture 三个方法并行时一个失败怎么办？线程池机制、超时、重试和降级如何设计？ |
| `L424` | 424 | L3 | RAG | Code RAG 如何按 Java 方法、JavaParser AST 和 MyBatis XML 切 Chunk？Lua 等非 Java 文件怎么处理？ |
| `L451` | 451 | L3 | Java | HashMap 扩容和红黑树转换条件是什么？并发为什么不安全，ConcurrentHashMap 如何保证安全？ |
| `L453` | 453 | L3 | Java | volatile 如何实现可见性？ThreadLocal 为什么可能内存泄漏，项目中如何规避？ |
| `L515` | 515 | L3 | Spring AOP | Spring AOP 有哪些应用场景？底层原理是什么？ |
| `L525` | 525 | L2 | Spark/技术栈 | 了解 Spark 吗？用它做过什么？除了 Java、Spring Boot 还会哪些技术栈？ |
| `L558` | 558 | L4 | OOM/JVM排障 | 如果出现 OutOfMemory 应该怎么排查问题？ |
| `L580` | 580 | L3 | Java/JVM内存泄漏 | 既然有 GC，为什么还会出现内存泄漏？ |
| `L591` | 591 | L3 | Java/HashMap底层/位运算 | HashMap 的容量为什么必须设计为 2 的幂次方？hash() 扰动函数与 (n - 1) & hash 寻址优化的底层原理是什么？ |
| `L592` | 592 | L3 | Java/JMM/volatile/可见性 | 请详细阐述 Java 内存模型（JMM）：主内存与工作内存抽象、可见性与有序性保证、happens-before 原则，以及 volatile 底层如何通过内存屏障保证共享变量的可见性与禁止指令重排？ |
