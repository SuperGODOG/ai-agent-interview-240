> Lesson 0009 · 阶段一 · Java 基础 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0009 · BigDecimal 精度陷阱 & 金额存储方案 & Unsafe 魔法类

这是**阶段一 Java 基础的收尾课**，一次合并三篇 ：、、。这三块内容有个共同点 —— **都是面试常问 + 实际工程必踩坑** 的实用细节：金额一算错就是资损事故，Unsafe 一用错就是 JVM crash。前两块偏工程直觉（结账、库存、汇率），Unsafe 偏底层原理（AQS、Atomic、Netty、Kryo 都靠它撑）。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `new BigDecimal(0.1)` 和 `new BigDecimal("0.1")` 结果一样吗？</summary>

**不一样**。前者打印出 `0.1000000000000000055511151231257827021181583404541015625` —— 因为 `0.1` 是 `double` 字面量，进入构造器之前就已经失真了；后者精确等于 `0.1`。第 2 题会展开。

</details>

<details>

<summary>Q0.2 `Unsafe.allocateInstance(MySingleton.class)` 能绕过构造器创建一个「假」单例吗？</summary>

**能**。`allocateInstance` 只申请对象内存并把字段清零，*不执行任何构造器逻辑*，甚至能绕过反射也无能为力的私有构造器。Kryo、Jackson 的反序列化就靠它绕过没有默认构造器的类。第 8 题会展开。

</details>

## 面试场景 1：为什么要用 BigDecimal？

🎤 面试官

业务里算个折扣、算个金额，为什么不能直接用 `double`？给我举几个失真的例子。

🧑‍💻 你

`float`/`double` 遵循 **IEEE 754** 二进制浮点标准，很多十进制小数在二进制里是*无限循环小数*，只能截断存储，一旦参与运算，误差就会被放大。经典三连翻车：

```
System.out.println(0.1 + 0.2);          // 0.30000000000000004
System.out.println(1.03 - 0.42);        // 0.6100000000000001
System.out.println(0.058 * 100);        // 5.7999999999999995
System.out.println(2.0f - 1.9f);        // 0.100000024
System.out.println(1.8f - 1.7f);        // 0.099999905
```

金额、汇率、税费、利息、库存单价 —— 任何一个环节用 `double` 加减乘除，都可能在对账时和财务打起来。所以业务上要么用 `BigDecimal`（十进制精确算术），要么用 `long` 存最小单位（分/厘）。

追问 浮点精度失真到底是「二进制存不下 0.1」，还是「精度丢失了」？

准确说是前者 —— **二进制根本表示不了精确的 0.1**。0.1 转二进制是 `0.0001100110011001100...` 的无限循环小数，就像十进制表示不了精确的 1/3 一样。`double` 只有 52 位尾数，只能截断，所以你存进去的 `0.1` 实际是 `0.1000000000000000055...`。这不是运算过程「丢」了精度，而是*从一开始就没有精度*。

## 面试场景 2：BigDecimal 的两种构造方式（★经典陷阱）

🎤 面试官

`new BigDecimal(0.1)` 和 `new BigDecimal("0.1")` 有区别吗？

🧑‍💻 你

有巨大区别，这是新人最常踩的坑：

```
System.out.println(new BigDecimal(0.1));
// 0.1000000000000000055511151231257827021181583404541015625   ← ❌ 已失真

System.out.println(new BigDecimal("0.1"));
// 0.1                                                          ← ✅ 精确

System.out.println(BigDecimal.valueOf(0.1));
// 0.1                                                          ← ✅ 精确（内部用 Double.toString）
```

原因：`new BigDecimal(double)` 的**入参 `0.1` 是 `double` 字面量，在写这行代码的时候就已经是失真的二进制值了**，构造器只是把这个失真值忠实地记录下来 —— 救不回来。`String` 版本是把「0.1」这个十进制字符串直接解析成 `BigDecimal`，跳过了浮点表示；`valueOf(double)` 内部走的是 `new BigDecimal(Double.toString(d))`，也是先转字符串。

**结论**：任何时候构造 `BigDecimal`，只用 `String` 构造器或 `valueOf(double)`，永远别用 `new BigDecimal(double)`。阿里巴巴 Java 开发手册强制这一条。

陷阱 `BigDecimal.valueOf(int)`、`valueOf(long)` 都是安全的（整数没有精度问题）；*只有 `valueOf(double)` 是「绕道字符串」的救命写法*。别以为 `BigDecimal` 全家桶都能防坑。

## 面试场景 3：BigDecimal 的四则运算（divide 的坑）

🧑‍💻 你

四则运算方法名清晰：`add`、`subtract`、`multiply`、`divide`。**注意 `BigDecimal` 是不可变对象**（immutable），所有方法都返回新对象，原对象不变 —— 忘接返回值是新人第二大坑：

```
BigDecimal a = new BigDecimal("1.0");
BigDecimal b = new BigDecimal("0.9");

a.add(b);                                          // 1.9  ← 结果被丢弃！a 还是 1.0
BigDecimal sum = a.add(b);                         // ✅ 必须接住返回值

a.subtract(b);                                     // 0.1
a.multiply(b);                                     // 0.90（scale = 两个操作数 scale 之和）

// divide 是最容易踩的坑：
a.divide(b);
// ❌ ArithmeticException: Non-terminating decimal expansion; no exact representable decimal result
//    1.0 / 0.9 = 1.1111... 无限循环，不指定 scale 就抛异常

a.divide(b, 2, RoundingMode.HALF_UP);              // ✅ 1.11
a.divide(b, 4, RoundingMode.HALF_UP);              // ✅ 1.1111
```

追问 `divide` 什么情况下不用指定 scale 也不会抛异常？

只有**除法能除尽**（结果是有限小数）时才不会抛。比如 `new BigDecimal("1.0").divide(new BigDecimal("0.5"))` = `2`，能除尽。但除不尽（如 1/3、1/7、10/3）就必须指定 `scale + RoundingMode`，否则 `ArithmeticException: Non-terminating decimal expansion; no exact representable decimal result`。**生产代码里所有 `divide` 无脑加上 scale 和舍入模式**，别赌能不能除尽。

## 面试场景 4：BigDecimal 的 equals 陷阱（★经典）

🎤 面试官

看这段代码：

```
BigDecimal a = new BigDecimal("1");
BigDecimal b = new BigDecimal("1.0");
System.out.println(a.equals(b));     // ?
System.out.println(a.compareTo(b));  // ?
```

结果是什么？为什么？

🧑‍💻 你

结果是 **`false`** 和 **`0`**。这是 `BigDecimal` 最经典的陷阱：

- `equals()` 同时比较 **value（值）** 和 **scale（精度）**。`"1"` 的 scale 是 0，`"1.0"` 的 scale 是 1，虽然值相等但精度不同 —— 返回 `false`。

- `compareTo()` 只比较**值**，忽略 scale。返回 `0` 表示相等，`-1`/`1` 表示小于/大于。

**结论**：判断两个 `BigDecimal` 数值是否相等，永远用 `a.compareTo(b) == 0`，绝不用 `equals`。

陷阱 用 `BigDecimal` 做 `HashMap` 的 key、放进 `HashSet`，走的是 `equals + hashCode` 语义，会区分 `1` 和 `1.0`！生产上经常出现「明明存了 1.0，用 1 查不到」的诡异 bug。要么统一 scale（`setScale(2, HALF_UP)`），要么改用 `TreeMap`（走 `compareTo`）。

追问 为什么 `compareTo` 相等而 `equals` 不等？设计者是抽风吗？

不是。`equals` 的契约是「代表相同的对象」，而 `BigDecimal` 的完整语义包含 `(unscaledValue, scale)` 二元组 —— `1` 和 `1.0` 表达的*业务精度*不一样（前者是「整数 1」，后者是「精确到 1 位小数的 1.0」），在金融/科学场景里这个差别是有意义的。所以 `equals` 严格按对象定义比较是合理的；只是*业务上比较数值大小*时用 `compareTo`。

## 面试场景 5：保留小数（RoundingMode 八种模式）

🧑‍💻 你

保留小数用 `setScale(scale, RoundingMode)`。`RoundingMode` 一共 8 种，面试常问的是 `HALF_UP` 和 `HALF_EVEN`：

模式1.55 保留 1 位1.45 保留 1 位说明

`UP`1.61.5远离 0（绝对值向上）
`DOWN`1.51.4朝 0（绝对值截断）
`CEILING`1.61.5向 +∞
`FLOOR`1.51.4向 −∞
`HALF_UP`1.61.5四舍五入（日常用）
`HALF_DOWN`1.51.4五舍六入（不常用）
`HALF_EVEN`1.61.4**银行家舍入**：靠向偶数
`UNNECESSARY`抛异常抛异常断言无需舍入，否则 `ArithmeticException`

**银行家舍入（`HALF_EVEN`）**：0.5 严格居中时，向*相邻偶数*靠拢。1.55 → 1.6（往 6 靠），1.45 → 1.4（往 4 靠）。这样在大量四舍五入时正负偏差会互相抵消，**金融业务的默认选择**（IEEE 754 默认舍入模式也是它）。`HALF_UP` 长期使用会有微小正偏，账目对不上分。

追问 `UNNECESSARY` 什么时候用？

用作**断言**：「我确信这一步不需要舍入」，如果实际需要就抛异常，防止悄悄丢精度。典型场景是接口入参校验，`amount.setScale(2, RoundingMode.UNNECESSARY)` —— 如果传入的金额小数位超过 2 位，直接报错，防止上游把 `0.005` 混进结算流程。

## 面试场景 6：金额用 long 还是 BigDecimal？（★经典设计题）

🎤 面试官

做一个电商系统，商品价格、订单金额、余额 —— 用 `long` 存分还是 `BigDecimal` 存元？

🧑‍💻 你

看场景，两者都有生产环境的合理位置：

维度long 存分（或存厘）BigDecimal

精度固定 2 位（分）或 4 位（厘）任意 scale，运行时决定
性能原生 CPU 整数运算，快软件模拟十进制，慢一个数量级
内存8 字节对象头 + BigInteger + int scale，几十字节
可读性差（要记住「这是分」）好（`19.99` 就是 19.99 元）
溢出Long.MAX 约 92 亿亿分，够用；但 `+`/`*` 溢出不报错，需 `Math.addExact`理论无溢出（内部按需扩展）
序列化JSON 是数字，简单JSON 用字符串防前端 `Number` 精度丢失
折扣/汇率难以表达 `0.85` 折扣天然支持任意小数

**决策原则**：

- **小额高频、单位固定**（订单金额、余额、C 端交易）→ `long` 存分。快、稳、序列化简单。

- **大额低频、需要中间小数**（汇率、税费、利息、分润比例、按比例结算）→ `BigDecimal`。

- **混合方案（推荐生产实践）**：*计算阶段用 `BigDecimal` 保留中间精度，落库/传输前 `movePointRight(2).longValueExact()` 转成分单位的 `long`*。

追问 用 `long` 存分，最大能表示多少人民币？

`Long.MAX_VALUE` = `2^63 - 1` ≈ `9.22 × 10^18` 分，也就是约 **9200 万亿元**。全球 GDP 总和才 100 万亿美元级，个人余额、订单金额都富余到不用担心。真正要小心的是**中间乘法溢出**：两个 `long` 相乘（比如单价 × 数量 × 汇率倍数）容易越界，所以要用 `Math.multiplyExact`，或者中间结果转 `BigDecimal`。

追问 前端如何接收后端的金额字段？

如果用 `long` 存分：前端拿到整数除 100 展示，简单。但要注意 **JavaScript 的 `Number` 只有 53 位精度**（`Number.MAX_SAFE_INTEGER = 2^53 - 1`），超过 9 千万亿 JSON 数值传过去就会失真。所以订单号、金额（如果可能超过 9 千万亿分）都建议**后端序列化为字符串**返回。`BigDecimal` 同理，Jackson 有 `WRITE_BIGDECIMAL_AS_PLAIN` 开关，避免科学计数法。

## 面试场景 7：数据库中金额字段用什么类型？

🧑‍💻 你

三个选项，只有前两个是对的：

- **`DECIMAL(p, s)`**：定点小数，精确无失真。*p 是总位数，s 是小数位数*。金额常用 `DECIMAL(20, 4)`（支持超大额 + 4 位小数容纳厘/毛的中间值），汇率用 `DECIMAL(18, 8)`。Java 侧映射 `BigDecimal`。

- **`BIGINT`**：8 字节整数，配合 `long` 存分。字段命名一律带单位后缀：`amount_cents`、`price_fen`。查询性能最好。

- **`FLOAT`/`DOUBLE`**：❌ 禁用。二进制浮点，同样会存 `0.1` 存成 `0.1000000...055`。**阿里 MySQL 军规 & 财务系统绝对红线**。

再补一条：字段设计要考虑**正负**。存的是「余额变动流水」时要允许负值（退款、扣减）；存的是「订单金额」时可以约束 `>= 0`。

## 面试场景 8：Unsafe 是什么？为什么叫「魔法类」？

🎤 面试官

你听过 `Unsafe` 类吗？它为什么叫「魔法类」？

🧑‍💻 你

`sun.misc.Unsafe`（JDK 9+ 迁移到 `jdk.internal.misc.Unsafe`，老类保留在 `jdk.unsupported` 模块下）是 JDK 内部的一个「后门」类，让 Java 代码**拥有类似 C 语言指针的能力**：直接分配堆外内存、直接读写任意内存地址、CAS、park/unpark 线程、跳过构造器创建对象……*全都在绕过 JVM 的安全边界*。

叫「魔法类」有两层意思：

1. **能力魔法**：普通 Java 代码做不到的事它都能做，AQS、Atomic、ConcurrentHashMap、LockSupport、DirectByteBuffer、Netty、Kryo、Disruptor 都靠它撑底层。

2. **获取魔法**：不能直接 `Unsafe.getUnsafe()` —— 那个方法内部会检查调用者的类加载器是不是 `Bootstrap ClassLoader`（只有 JDK 自己能拿），普通业务代码调会抛 `SecurityException`。要靠**反射拿它的 `theUnsafe` 静态字段**：

```
Field f = Unsafe.class.getDeclaredField("theUnsafe");
f.setAccessible(true);
Unsafe unsafe = (Unsafe) f.get(null);
```

陷阱 `Unsafe` 是 **sun.*** 私有 API，不属于 Java 标准；JDK 各版本可以随时改甚至删。生产代码*不要直接用*，除非你在写框架（Netty、Disruptor 那种）或者标准库替代方案（`VarHandle`、`MemorySegment`）解决不了问题。

## 面试场景 9：Unsafe 的核心能力和典型应用

🧑‍💻 你

能力代表方法典型应用

堆外内存`allocateMemory` / `freeMemory` / `putLong` / `getLong`Netty `PooledByteBufAllocator`、`DirectByteBuffer`、堆外缓存（OHC、Chronicle Map）
CAS 原子操作`compareAndSwapInt/Long/Object``AtomicInteger`、`AtomicReference`、`AQS.state`、`ConcurrentHashMap` 的 `counterCells`
线程调度`park` / `unpark``LockSupport.park`、`ReentrantLock`、`CountDownLatch`、所有 AQS 派生类的线程阻塞
内存屏障`loadFence` / `storeFence` / `fullFence``StampedLock` 乐观读、无锁数据结构（LMAX Disruptor）
跳过构造器`allocateInstance`Kryo/Jackson 反序列化没有默认构造器的类、破坏单例、Hibernate 代理对象
字段偏移`objectFieldOffset` / `putObjectVolatile``AtomicIntegerFieldUpdater`、无锁数据结构定位字段做 CAS
数组偏移`arrayBaseOffset` / `arrayIndexScale``AtomicIntegerArray`、`ConcurrentHashMap` 桶数组的 CAS
类定义`defineClass` / `defineAnonymousClass`动态生成类（CGLIB、部分 Lambda 实现）

一句话总结：**并发包（`j.u.c`）和高性能框架的底层 90% 都在用 `Unsafe`**。你写的 `new AtomicInteger()`、`synchronized` 之外的每一次原子操作、每一次 `LockSupport.park()`，进去一层都是 `Unsafe`。

追问 `LockSupport.park()` 为什么可以 park 一个「还没被 unpark」的线程，而不是像 `wait()` 那样必须先拿锁？

因为 `Unsafe.park/unpark` 用的是**许可证（permit）**语义，不是条件变量。每个线程有一个「许可证」标志位（0 或 1，不累积）：`unpark` 把它置 1，`park` 检查如果是 1 就直接消耗返回、如果是 0 就阻塞。*先 unpark 后 park 也没问题，因为许可证已经在了*，park 立刻返回。而 `Object.wait` 依赖 monitor，没先拿锁就抛 `IllegalMonitorStateException`；且没有 `notify` 就等着永远醒不来。这也是为什么 AQS 全线用 park/unpark 而不用 wait/notify。

追问 `Unsafe.allocateInstance` 到底能绕过什么？为什么 Kryo 要用它？

能绕过 **构造器**（包括所有初始化逻辑：字段初始值、构造体里的赋值、父类构造器调用）—— 得到的对象*所有字段都是默认零值*（int=0、boolean=false、Object=null）。所以能绕过：**私有构造器（破坏单例）、无默认构造器的类、构造器里的参数校验、final 字段的初始化**。Kryo 反序列化要还原一个对象，构造器可能有副作用（打日志、注册监听器）也可能需要参数它没有，所以直接 `allocateInstance` 拿到「空壳」，再通过反射+Unsafe 把字段值填进去 —— 完美绕过所有构造逻辑，性能还比反射调构造器高。

## 面试场景 10：Unsafe 在 JDK 9+ 的变化 & VarHandle 替代

🎤 面试官

JDK 9 之后 `Unsafe` 有什么变化？官方推荐用什么替代？

🧑‍💻 你

三个关键变化：

1. **类被拆成两份**：JDK 内部新增 `jdk.internal.misc.Unsafe`（真正的实现），老的 `sun.misc.Unsafe` 保留在 `jdk.unsupported` 模块里，方法基本是转发调用。这样 JDK 内部可以自由演进，同时不马上砸掉全世界依赖 `sun.misc.Unsafe` 的老代码（Netty、Cassandra、Spark 一大票）。

2. **模块系统访问限制**：JDK 9 引入 JPMS，`sun.misc.Unsafe` 属于 `jdk.unsupported`，虽然默认可访问但会有警告；`jdk.internal.misc.Unsafe` 严格封闭，业务代码用不了。

3. **官方推荐的替代方案**：

- `java.lang.invoke.VarHandle`（JDK 9+）—— 替代大部分 CAS、内存屏障、volatile 读写。API 更规范、类型安全，性能持平。

- `java.lang.foreign.MemorySegment`（JDK 22 正式）+ Foreign Function & Memory API —— 替代堆外内存操作，比 `allocateMemory` 更安全（自动释放、边界检查）。

- `java.util.concurrent` —— 替代大部分 park/unpark 场景。

方向很明确：**JDK 在慢慢把 `Unsafe` 藏起来 / 拆掉**。JDK 23 已经把内存访问相关方法标记为 *terminally deprecated*，写新代码优先选标准 API。

追问 `VarHandle` 相比直接用 `Unsafe.compareAndSwapInt` 有什么优势？

三点：**1) 类型安全** —— `VarHandle` 在获取时就绑定了字段类型，编译期就能查错，不像 `Unsafe` 靠字段偏移量 + 泛型方法容易传错类型；**2) 语义丰富** —— 提供 `getAcquire/setRelease/getVolatile/getOpaque/weakCompareAndSet` 等一整套 memory ordering 明确的方法，对应 Java 内存模型标准语义，不像 `Unsafe` 只有 `Volatile`/普通两档；**3) 官方标准** —— 属于 `java.lang.invoke`，未来不会突然被移除。缺点是 API 比 `Unsafe` 稍绕（要先 `MethodHandles.lookup().findVarHandle` 拿句柄）。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：BigDecimal 字符串 vs double 构造对比

```
import java.math.BigDecimal;

public class BigDecimalConstructor {
public static void main(String[] args) {
System.out.println(new BigDecimal(0.1));
// 0.1000000000000000055511151231257827021181583404541015625  ❌ 失真

System.out.println(new BigDecimal("0.1"));
// 0.1                                                        ✅ 精确

System.out.println(BigDecimal.valueOf(0.1));
// 0.1                                                        ✅ 精确（内部走 Double.toString）

// 加法直观对比：
System.out.println(new BigDecimal(0.1).add(new BigDecimal(0.2)));
// 0.3000000000000000166533453693773481063544750213623046875  ❌

System.out.println(new BigDecimal("0.1").add(new BigDecimal("0.2")));
// 0.3                                                        ✅
}
}
```

### 验证 2：equals vs compareTo 陷阱

```
import java.math.BigDecimal;
import java.util.HashSet;
import java.util.Set;

public class BigDecimalEquals {
public static void main(String[] args) {
BigDecimal a = new BigDecimal("1");
BigDecimal b = new BigDecimal("1.0");

System.out.println(a.equals(b));        // false  ← scale 不同
System.out.println(a.compareTo(b) == 0); // true  ← 值相等

// HashSet 里的坑：
Set<BigDecimal> set = new HashSet<>();
set.add(new BigDecimal("1"));
System.out.println(set.contains(new BigDecimal("1.0")));  // false ！！！

// 修法一：统一 scale
Set<BigDecimal> fixed = new HashSet<>();
fixed.add(new BigDecimal("1").setScale(2));
System.out.println(fixed.contains(new BigDecimal("1.0").setScale(2)));  // true
}
}
```

### 验证 3：Unsafe.allocateInstance 破坏单例

```
import sun.misc.Unsafe;
import java.lang.reflect.Field;

public class BreakSingleton {
static class Singleton {
private static final Singleton INSTANCE = new Singleton();
private final String tag;
private Singleton() {
this.tag = "constructed";  // 构造器初始化
}
public static Singleton getInstance() { return INSTANCE; }
public String getTag() { return tag; }
}

public static void main(String[] args) throws Exception {
// 拿到 Unsafe 实例
Field theUnsafe = Unsafe.class.getDeclaredField("theUnsafe");
theUnsafe.setAccessible(true);
Unsafe unsafe = (Unsafe) theUnsafe.get(null);

Singleton normal = Singleton.getInstance();
Singleton fake = (Singleton) unsafe.allocateInstance(Singleton.class);

System.out.println(normal == fake);            // false 两个不同对象
System.out.println(normal.getTag());           // "constructed"
System.out.println(fake.getTag());             // null  ← 构造器根本没跑，final 字段也是 null！
}
}
// 编译时可能需要 --add-opens java.base/sun.misc=ALL-UNNAMED（JDK 17+）
```

### 验证 4：Unsafe 手撸 CAS 原子递增

```
import sun.misc.Unsafe;
import java.lang.reflect.Field;

public class UnsafeCasCounter {
private volatile int counter = 0;
private static final Unsafe UNSAFE;
private static final long OFFSET;

static {
try {
Field f = Unsafe.class.getDeclaredField("theUnsafe");
f.setAccessible(true);
UNSAFE = (Unsafe) f.get(null);
OFFSET = UNSAFE.objectFieldOffset(
UnsafeCasCounter.class.getDeclaredField("counter"));
} catch (Exception e) { throw new RuntimeException(e); }
}

public void increment() {
int cur;
do {
cur = counter;
} while (!UNSAFE.compareAndSwapInt(this, OFFSET, cur, cur + 1));
// ↑ AtomicInteger.incrementAndGet 的底层实现就是这个循环
}

public static void main(String[] args) throws InterruptedException {
UnsafeCasCounter c = new UnsafeCasCounter();
Thread[] ts = new Thread[10];
for (int i = 0; i < ts.length; i++) {
ts[i] = new Thread(() -> {
for (int j = 0; j < 100_000; j++) c.increment();
});
ts[i].start();
}
for (Thread t : ts) t.join();
System.out.println(c.counter);   // 1000000  ← 十个线程并发 CAS，无锁但正确
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 为什么 `new BigDecimal(0.1)` 存进去的值不是 0.1？该怎么写才对？</summary>

因为 `0.1` 作为 `double` 字面量本身就无法精确表示（IEEE 754 二进制无限循环），传入构造器前已经失真。正确写法是 `new BigDecimal("0.1")` 或 `BigDecimal.valueOf(0.1)`（内部会先 `Double.toString` 转成字符串）。

</details>

<details>

<summary>Q2 判断两个 `BigDecimal` 数值相等应该用 `equals` 还是 `compareTo`？为什么？</summary>

用 `compareTo(other) == 0`。`equals` 会同时比较 value 和 scale，`"1"` 和 `"1.0"` equals 返回 false；`compareTo` 只比较值，返回 0。所以 `BigDecimal` 也不能安全地作为 `HashSet`/`HashMap` 的 key。

</details>

<details>

<summary>Q3 `BigDecimal.divide` 什么情况下必须指定 `scale + RoundingMode`？金融业务默认用哪种舍入？</summary>

当除法结果是无限循环小数（除不尽）时必须指定，否则抛 `ArithmeticException: Non-terminating decimal expansion`。生产代码建议无脑加上。金融业务默认用 `HALF_EVEN`（银行家舍入），能让大量四舍五入的正负偏差互相抵消，避免长期系统性偏差。

</details>

<details>

<summary>Q4 金额存储用 `long`（分）还是 `BigDecimal`？数据库应该用什么字段类型？</summary>

小额高频、单位固定的场景（订单金额、余额）用 `long` 存分，性能好、序列化简单；需要中间小数的场景（汇率、税费、折扣）用 `BigDecimal`；工程上常混合使用（计算用 BigDecimal，落库用 long）。数据库对应 `BIGINT` 或 `DECIMAL(p,s)`（如 `DECIMAL(20,4)`），**绝不能用 `FLOAT`/`DOUBLE`**。

</details>

<details>

<summary>Q5 `Unsafe` 的核心能力是什么？在 JDK 9+ 官方推荐用什么替代？</summary>

核心能力：堆外内存分配 / CAS 原子操作 / `park/unpark` 线程阻塞 / 内存屏障 / `allocateInstance` 跳过构造器 / 字段与数组的偏移量访问。JDK 9+ 后 `sun.misc.Unsafe` 挪到 `jdk.unsupported` 模块保留兼容，真正实现在 `jdk.internal.misc.Unsafe`。官方推荐替代：`VarHandle`（原子操作、内存屏障）、`java.lang.foreign.MemorySegment`（堆外内存）、`java.util.concurrent`（线程同步）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 主源 A

-  —— 主源 B

-  —— 主源 C

- JDK 21 · `java.math.BigDecimal` API

- JDK 21 · `java.lang.invoke.VarHandle` API —— Unsafe 官方替代

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

**阶段二 · 集合**：Lesson 0010 **集合概览 & 使用注意事项** —— 阶段一 Java 基础到此收官，下一课正式进入面试第二重灾区：集合框架。会先俯瞰 `Collection`/`Map` 的整体结构，再把新人最容易踩的 *fail-fast、Arrays.asList 陷阱、Collection.toArray 类型问题、Comparable vs Comparator* 一次讲透，为后面的 `ArrayList`、`HashMap`、`ConcurrentHashMap` 深挖打底。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。阶段一 Java 基础到此收关，如果哪节课还没完全吃透，现在是回头补漏的最佳时机。


