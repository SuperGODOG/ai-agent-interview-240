# 03 · JVM

## 一、内存区域（运行时数据区）

### 线程私有
- 程序计数器：当前线程执行的字节码行号；唯一不 OOM 的区域；多线程切换恢复位置用。
- 虚拟机栈（Java 栈）：栈帧 = 局部变量表 + 操作数栈 + 动态链接 + 方法出口；StackOverflowError（递归太深）/ OOM（栈太大）。
- 本地方法栈：执行 native 方法（HotSpot 中与虚拟机栈合并）。

### 线程共享
- 堆：对象实例和数组；GC 主战场；分代：新生代（Eden + 两个 Survivor，默认 8:1:1）+ 老年代；OOM 主要来源（-Xms/-Xmx）。
- 方法区（JDK 8 起为元空间 Metaspace，用本地内存）：类信息、常量、静态变量、运行时常量池；JDK 7 之前叫永久代 PermGen；元空间默认不受 -Xmx 限制，用本地内存，可能 OOM（-XX:MaxMetaspaceSize）。
- 字符串常量池：JDK 7 起移到堆；intern() 入池。

### 对象创建流程
1. 类加载检查（new 指令 → 常量池定位类符号引用，检查是否已加载/初始化）。
2. 分配内存：指针碰撞（GC 压缩）/ 空闲列表；并发分配用 CAS + 失败重试或 TLAB 线程本地分配缓冲。
3. 初始化零值（对象字段默认值）。
4. 设置对象头（Mark Word + 类型指针 + 数组长度）。
5. 执行 `<init>` 构造方法。

### 对象访问定位
- 句柄（稳定，多一次间接）vs 直接指针（HotSpot 默认，快）。

## 二、判断对象存活

- 引用计数法：循环引用无法回收，JVM 不用。
- 可达性分析（GC Roots 为起点）：GC Roots = 栈帧局部变量引用的对象、静态变量、常量、JNI 引用、活跃线程等。
- 两次标记：不可达 → 第一次标记；无 finalize 覆盖或未复活 → 第二次回收（finalize 不推荐，已废弃）。

### 引用类型
- 强引用：不回收（OOM 也不收）。
- 软引用：内存不足才回收（缓存）。
- 弱引用：下次 GC 必回收（ThreadLocal key）。
- 虚引用：最弱，用于堆外内存回收通知（DirectByteBuffer 配合 Cleaner）。

## 三、GC 算法

1. 标记-清除：效率低、产生内存碎片。
2. 标记-复制：新生代用，Eden:Survivor=8:1:1，浪费 10%，无碎片，效率高（存活对象少时划算）。
3. 标记-整理：老年代用，移动存活对象消除碎片，有移动开销。
- 分代收集：新生代复制、老年代标记-整理/清除。

## 四、常见收集器

- Serial/Serial Old：单线程，客户端默认。
- Parallel Scavenge/Parallel Old：吞吐优先，多线程，JDK8 默认。
- CMS：低延迟（标记-清除），并发标记清除；缺点：碎片、并发失败（退化 Serial Old）、浮动垃圾。
- G1（JDK 9+ 默认）：Region 分区，可预测停顿，同时兼顾吞吐；回收按价值优先（Mixed GC）；ZGC/Shenandoah：超低停顿（<10ms），染色指针 + 读屏障，适合超大堆。

## 五、类加载机制

### 过程
加载（读字节码生成 Class）→ 验证 → 准备（静态变量赋零值）→ 解析（符号引用转直接引用）→ 初始化（执行 `<clinit>`，静态块/静态变量赋值）→ 使用 → 卸载。

### 双亲委派
- 自下而上委派，自上而下加载：Bootstrap（rt.jar/JDK 核心）→ Extension/Platform（JDK9+）→ Application（classpath）→ 自定义。
- 作用：避免核心类被篡改（Object 唯一）、避免重复加载。
- 打破：JDBC（SPI 通过 Thread.contextClassLoader 反向加载驱动实现）、热部署（自定义 ClassLoader 隔离）、Tomcat 先自己加载 web 应用类。

### 什么时候初始化类（主动引用）
- new/静态字段/静态方法、反射、初始化子类先初始化父类、main 类、JDK7 动态语言句柄。

## 六、JMM（Java 内存模型）

### 三大特性
- 原子性：synchronized/Lock/原子类保证。
- 可见性：volatile/synchronized/final。
- 有序性：volatile 屏障/synchronized；as-if-serial。

### happens-before 规则（记 6 条核心）
1. 程序次序：单线程内按代码顺序。
2. volatile 变量：写 happens-before 读。
3. 锁：解锁 happens-before 后加锁。
4. 传递性：A→B→C 则 A→C。
5. 线程 start/join。
6. 线程中断/interrupted。

### volatile 内存屏障
- 写：StoreStore + StoreLoad；读：LoadLoad + LoadStore；防止指令重排。

## 七、排查与调优（常被追问）

### 常用命令
- jps：Java 进程列表
- jstat -gcutil <pid>：GC 状态
- jmap -dump:format=b,file=heap.bin <pid>：堆转储（生产慎用，会 STW）
- jstack <pid>：线程栈（查死锁、CPU 高）
- jinfo：JVM 参数
- MAT / VisualVM / jconsole：分析 dump

### OOM 场景与排查思路
1. 堆 OOM：jmap dump → MAT 看大对象/泄漏；设置 -XX:+HeapDumpOnOutOfMemoryError。
2. 元空间 OOM：动态生成类（反射/CGLIB）过多。
3. 栈溢出：递归无限。
- 思路：先看监控（GC、内存曲线）→ dump 线程栈和堆 → 定位代码 → 修 bug 或调参。

### 常见调优参数
- -Xms -Xmx（堆大小）、-Xmn（新生代）、-XX:MetaspaceSize、-XX:MaxGCPauseMillis、-XX:+UseG1GC、-XX:MaxDirectMemorySize（堆外）、-XX:+PrintGCDetails。

## 八、常问追问

1. 新生代为什么 8:1:1？→ 复制算法空间浪费与存活对象比例的折中。
2. 什么时候对象直接进老年代？→ 大对象、晋升阈值（15 次 Minor GC）、动态年龄判断、Survivor 放不下。
3. 什么是 STW？→ Stop The World，GC 时暂停业务线程；G1/ZGC 尽量缩短。
4. 双亲委派为什么能防篡改？→ 核心类由 Bootstrap 加载，用户代码永远加载不到同名类。
5. 强引用 OOM 怎么排查？→ dump 分析是否有大对象、集合无限增长。
6. 你项目的 JVM 怎么配的？→ 根据内存/延迟要求答：堆、GC 选择、dump 参数。
7. 类初始化时机判断？→ 主动引用 6 种场景。
8. final 的可见性？→ 构造器正确退出后 final 字段保证可见。
