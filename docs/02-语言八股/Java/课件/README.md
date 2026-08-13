# Java 面试体系化课件（66 篇）

> 按「面试场景 + 追问 + 代码 + 自测」组织的 Java 后端面试课件，从 JVM 基础到 Spring 生态全覆盖。
> 建议配合 [11 篇手撕笔记](../../README.md) 使用：课件学体系，手撕笔记做冲刺。

## 目录

### 阶段一（9 篇）

- [0001 · Java 概览 & JVM/JDK/JRE/字节码](0001-jvm-jdk-jre-bytecode.md)
- [0002 · OOP 三大特征 & 接口 vs 抽象类 & Object 方法 & 深浅拷贝](0002-oop-interfaces-value-passing.md)
- [0003 · Java 关键字总结 & 值传递详解](0003-keywords-value-passing.md)
- [0004 · 异常 & 泛型 & 反射 & I/O · 六合一入门](0004-exceptions-generics-reflection-overview.md)
- [0005 · 泛型 & 通配符深挖 & 类型擦除 & PECS](0005-generics-wildcards.md)
- [0006 · 反射机制深挖：Class & 反射调用 & 性能 & 框架应用](0006-reflection.md)
- [0007 · 代理模式深挖：静态代理 & JDK 动态代理 & CGLIB & Spring AOP 应用](0007-proxy.md)
- [0008 · SPI & 序列化 & 语法糖](0008-spi-serialization-sugar.md)
- [0009 · BigDecimal 精度陷阱 & 金额存储方案 & Unsafe 魔法类](0009-bigdecimal-money-unsafe.md)

### 阶段二（8 篇）

- [0010 · 集合框架概览 & 使用注意事项](0010-collection-overview.md)
- [0011 · ArrayList 源码分析：数据结构 & 扩容 & fail-fast](0011-arraylist-source.md)
- [0012 · LinkedList 源码分析 & Deque 定位](0012-linkedlist-source.md)
- [0013 · HashMap 源码深挖：数据结构 & hash 扰动 & 扩容 & 树化 & 线程不安全](0013-hashmap-source.md)
- [0014 · LinkedHashMap 源码 & 手撕 LRU 实现](0014-linkedhashmap-lru.md)
- [0015 · ConcurrentHashMap 源码深挖](0015-concurrent-hashmap-source.md)
- [0016 · CopyOnWriteArrayList & 写时复制](0016-copyonwritearraylist.md)
- [0017 · 阻塞队列 ArrayBlockingQueue & DelayQueue](0017-blocking-queue.md)

### 阶段三（12 篇）

- [0018 · 线程基础 & 生命周期 & Thread vs Runnable & 常用方法陷阱](0018-thread-basics.md)
- [0019 · synchronized 深入 & 锁升级](0019-synchronized.md)
- [0020 · JMM &amp; happens-before &amp; volatile 全面解析](0020-volatile-jmm.md)
- [0021 · 乐观锁 vs 悲观锁 & CAS & ABA](0021-cas.md)
- [0022 · Atomic 原子类家族](0022-atomic-classes.md)
- [0023 · AQS 详解（★核心）](0023-aqs.md)
- [0024 · ReentrantLock &amp; Condition &amp; 公平/非公平锁](0024-reentrantlock.md)
- [0025 · ThreadLocal 详解：原理 & 内存泄漏 & InheritableThreadLocal & TTL](0025-threadlocal.md)
- [0026 · 线程池详解：核心 7 参数 & 执行流程 & 拒绝策略 & ctl](0026-thread-pool.md)
- [0027 · 线程池最佳实践 &amp; 常见错误 &amp; 参数选型 &amp; 动态线程池](0027-thread-pool-best-practices.md)
- [0028 · 并发容器全览 & CompletableFuture 异步编程](0028-concurrent-collections-cf.md)
- [0029 · 虚拟线程（Project Loom）](0029-virtual-thread.md)

### 阶段四（8 篇）

- [0030 · JVM 概览 & 组成结构 & 常见面试题](0030-jvm-overview.md)
- [0031 · JVM 内存区域详解](0031-jvm-memory-area.md)
- [0032 · 对象创建 & 内存布局 & 逃逸分析](0032-object-creation-layout.md)
- [0033 · JVM 垃圾回收算法与收集器](0033-jvm-gc.md)
- [0034 · 类文件结构](0034-class-file-structure.md)
- [0035 · 类加载过程详解](0035-class-loading-process.md)
- [0036 · 类加载器 & 双亲委派](0036-classloader.md)
- [0037 · JVM 参数 & 监控工具 & 线上排查](0037-jvm-params-tools.md)

### 阶段五（3 篇）

- [0038 · Java IO 基础 & 设计模式（装饰器/适配器/工厂）](0038-io-basis-patterns.md)
- [0039 · IO 模型：BIO/NIO/AIO & 多路复用 select/poll/epoll](0039-io-model.md)
- [0040 · Java NIO 核心：Buffer & Channel & Selector 三件套](0040-nio-core.md)

### 阶段六（10 篇）

- [0041 · MySQL 概览 & 存储引擎 & 三大范式](0041-mysql-overview.md)
- [0042 · SQL 执行过程 & Server 层 vs 引擎层](0042-sql-execution.md)
- [0043 · MySQL 索引详解：B+ 树 & 聚簇/非聚簇 & 回表 & 覆盖索引 & 最左前缀](0043-mysql-index.md)
- [0044 · MySQL 索引失效场景 & 隐式转换陷阱](0044-mysql-index-invalidation.md)
- [0045 · MySQL 执行计划 explain 分析](0045-mysql-explain.md)
- [0046 · 事务 ACID & 四大隔离级别](0046-transaction-isolation.md)
- [0047 · InnoDB MVCC 详解](0047-mysql-mvcc.md)
- [0048 · MySQL 锁全景](0048-mysql-lock.md)
- [0049 · MySQL 三大日志详解](0049-mysql-logs.md)
- [0050 · MySQL 优化规范 & 备份恢复](0050-mysql-optimization.md)

### 阶段七（9 篇）

- [0051 · 缓存基础 & 为什么用 Redis](0051-cache-basics.md)
- [0052 · Redis 5 种基本数据类型 & 底层实现 & 使用场景](0052-redis-basic-types.md)
- [0053 · Redis 3 种特殊数据类型：HyperLogLog & Bitmap & Geo](0053-redis-special-types.md)
- [0054 · Redis 跳表 & ziplist & listpack](0054-redis-skiplist.md)
- [0055 · Redis 持久化：RDB & AOF & 混合](0055-redis-persistence.md)
- [0056 · 缓存三兄弟 & 3 种缓存读写策略](0056-cache-3-brothers.md)
- [0057 · Redis 内存碎片 & 阻塞原因 & 淘汰策略](0057-redis-blocking.md)
- [0058 · Redis 延时任务 & Stream & 分布式锁](0058-redis-delayed-mq.md)
- [0059 · Redis 高可用：主从 & 哨兵 & Cluster](0059-redis-cluster.md)

### 阶段八（7 篇）

- [0060 · Spring 概览 & Spring 全家桶 & 面试题总结](0060-spring-overview.md)
- [0061 · Spring IoC & AOP & Bean 生命周期 & 循环依赖](0061-spring-ioc-aop.md)
- [0062 · Spring AOP 深入：JDK vs CGLIB & Bean 后置处理器 & 常见坑](0062-spring-aop-deep.md)
- [0063 · Spring 事务：ACID & 7 种传播行为 & 隔离级别 & 失效场景](0063-spring-transaction.md)
- [0064 · Spring 常用注解 & MVC 请求流程 & 参数校验](0064-spring-annotations.md)
- [0065 · SpringBoot 自动装配原理 & starter & 条件注解](0065-springboot-autoconfig.md)
- [0066 · Spring 设计模式 & @Async 原理](0066-spring-design-patterns.md)
