> Lesson 0008 · 阶段一 · Java 基础 · ⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0008 · SPI & 序列化 & 语法糖

这一课把三篇  的中频题合并：、、。三块各自不算超高频，但拼起来常在面试尾声出现 —— **SPI 是「你懂 Java 扩展机制吗」的试金石**，**序列化是安全漏洞高发区**，**语法糖是「你有没有看过反编译」的分水岭**。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 SPI 机制为什么要「打破双亲委派」？</summary>

因为 JDK 核心类（如 `DriverManager`、SLF4J 门面）在启动类加载器里，而它们要用到的实现（MySQL Driver、Logback）在应用类加载器里 —— 按双亲委派根本加载不到。SPI 用**线程上下文类加载器（TCCL）**反向委托到应用类加载器加载实现。第 3 题细讲。

</details>

<details>

<summary>Q0.2 为什么大厂几乎都不用 JDK 原生序列化？</summary>

三大死穴：**不跨语言**、**性能差体积大**、**安全漏洞多**（fastjson RCE、Log4Shell、Commons Collections gadget chain 都涉及反序列化）。第 7 题细讲。

</details>

## 面试场景 1：什么是 SPI？和 API 有什么区别？

🎤 面试官

你听过 SPI 吗？它和 API 有什么区别？

🧑‍💻 你

**SPI**（Service Provider Interface）是服务提供者接口。它和 API 的关键差别在于*「谁定接口、谁提供实现」*的方向不同：

- **API**：接口和实现都在*服务提供方*，调用方只用不改（如 `ArrayList` 是 JDK 提供的 API）。

- **SPI**：接口在*调用方（框架/JDK）*定，实现由*第三方（用户/驱动厂商）*提供。调用方在运行时通过 `ServiceLoader` 发现并加载所有实现。

类比：H 公司定芯片标准（SPI），高通/联发科按标准生产不同实现；下游手机厂选一家用。SPI 让扩展点和实现完全解耦。

追问 你平常用过哪些 SPI 的例子？

三个最经典的：**JDBC 驱动**（`java.sql.Driver` 是接口，MySQL / PostgreSQL 各自提供实现）、**SLF4J 日志门面**（`Logger` 接口，Logback / Log4j 提供实现）、**Servlet 容器**（Tomcat / Jetty 提供 `ServletContainerInitializer`）。

## 面试场景 2：SPI 怎么用？完整步骤是什么？

🧑‍💻 你

三步走：

1. **定义接口**（服务方）：`com.example.Logger`

2. **实现方在 JAR 里放约定文件**：`META-INF/services/com.example.Logger`，文件内容是实现类全限定名，每行一个

3. **调用方加载**：`ServiceLoader<Logger> loader = ServiceLoader.load(Logger.class);`，然后 `for (Logger l : loader)` 拿到所有实现

`ServiceLoader` 内部做的事：扫 classpath 下所有 `META-INF/services/<接口全名>` 文件 → 读取实现类名 → 用**线程上下文类加载器** `Class.forName` → `constructor.newInstance` 反射实例化 → 缓存到内部 Map。

追问 `ServiceLoader` 是懒加载还是饥饿加载？

**懒加载**。`ServiceLoader.load()` 只是准备 `LazyIterator`，真正的加载和实例化发生在 `Iterator.next()` 被调用时。已实例化的会缓存，下次 `reload()` 才清空。

## 面试场景 3：SPI 为什么要打破双亲委派？（★核心）

🎤 面试官

SPI 和双亲委派有什么冲突？为什么要打破？

🧑‍💻 你

矛盾在于**加载方向反了**：

- JDK 核心类（`DriverManager`、`ServiceLoader` 本身）由**启动类加载器**（Bootstrap ClassLoader）加载。

- SPI 的实现类（MySQL Driver、Logback 实现）在业务 JAR 里，由**应用类加载器**（App ClassLoader）加载。

- 按双亲委派，启动类加载器只能向上找父加载器 —— *无法向下*看到应用类加载器里的东西。所以 `DriverManager` 按传统方式根本加载不到 MySQL 的 `com.mysql.cj.jdbc.Driver`。

解决方案：**线程上下文类加载器（Thread Context ClassLoader, TCCL）**。`Thread.currentThread().setContextClassLoader(appClassLoader)`，然后 `ServiceLoader` 内部 `Class.forName(name, false, Thread.currentThread().getContextClassLoader())` —— 通过 TCCL 反向拿到应用类加载器加载实现类。这样在*不违背双亲委派单向查找*的前提下，实现了「父加载器加载的类调用子加载器加载的类」。

陷阱 JDBC 4.0（JDK 6+）之后代码里可以省略 `Class.forName("com.mysql.cj.jdbc.Driver")`，就是因为 `DriverManager` 静态初始化时通过 `ServiceLoader` + TCCL 自动加载了所有 Driver 实现。老代码里的 `Class.forName` 现在只是「双保险」。

## 面试场景 4：Dubbo/Spring 为什么不用 JDK SPI，要自研？

🧑‍💻 你

JDK SPI 有三大痛点，撑不起 Dubbo/Spring 这种大框架：

1. **一次加载全部实现**：`ServiceLoader` 会遍历所有实现类挨个初始化。想只用「com.mysql.Driver」也得把「Oracle」「PostgreSQL」都实例化一遍，浪费。

2. **不能按 key 挑选**：JDK SPI 拿到的是 List，只能自己写循环判断类型。Dubbo 想要 `ExtensionLoader.getExtension("mysql")` 直接按名字取。

3. **不支持 IoC/AOP**：JDK SPI 只 `newInstance()`，不能注入依赖、加过滤链。

所以 Dubbo 自研了 **Dubbo SPI**（`@SPI` + `@Adaptive` + `@Activate`），支持按 key 加载、自适应扩展（运行时按 URL 参数选实现）、依赖注入。Spring 的 `spring.factories`（SpringBoot 2）/ `AutoConfiguration.imports`（SpringBoot 3）也是同样思路的自研 SPI。

追问 Dubbo SPI 的 `@Adaptive` 是干什么的？

让扩展点能**运行时按 URL 参数选实现**。Dubbo 在加载 `@SPI` 接口时会生成一个「自适应类」（`xxx$Adaptive`），方法体里读 `URL.getParameter("key")` 然后到 `ExtensionLoader` 找对应实现调用。核心机制是*字节码生成 + 动态代理*，让扩展的选择延迟到方法调用时。

## 面试场景 5：Serializable 和 Externalizable 有什么区别？

维度`Serializable``Externalizable`

接口类型标记接口（无方法）有 `writeExternal` / `readExternal`
序列化机制JVM 反射自动处理开发者自行写读/写逻辑
性能较慢（反射 + 类元数据）较快（无反射开销）
构造器反序列化不调用构造器反序列化**会调用无参构造器**
字段控制`transient` 排除；或写 `writeObject` 覆盖完全手动
实际使用99% 场景几乎不用（更好的选择是 Protobuf/Kryo）

## 面试场景 6：serialVersionUID 的作用是什么？有什么陷阱？

🧑‍💻 你

`serialVersionUID` 是序列化的**版本号**。反序列化时 JVM 会比对流里的 UID 和当前类的 UID，不一致就抛 `InvalidClassException: local class incompatible`。

如果不显式声明，JVM 会根据类结构（字段、方法签名等）**自动生成**一个。这有两个坑：

- **字段/方法一变 UID 就变**：老数据反序列化直接崩。生产事故常客。

- **跨 JVM 生成算法可能有差异**：老版本 JDK 序列化的数据在新 JDK 上反序列化可能失败。

所以规范：**任何 `Serializable` 类都要显式声明 `private static final long serialVersionUID = 1L;`**，然后字段增删要评估兼容性再决定是否升 UID。

陷阱 `serialVersionUID` 虽然是 `static final`，但序列化机制会**特殊处理**它 —— 把它当版本号写进流。别误以为「static 字段不会被序列化，所以 UID 也不参与」，这是常见误解。

追问 `transient` 和 `static` 字段的序列化行为？

**都不会**被序列化，反序列化后 `transient` 字段是类型默认值（int=0, Object=null）。`static` 字段属于类不属于对象，天然不会。*密码、Session、大对象引用*应该用 `transient`。

## 面试场景 7：为什么不建议用 JDK 原生序列化？（★核心）

🧑‍💻 你

四大死穴：

1. **不跨语言**：序列化后的字节流只有 Java 能反序列化。微服务用 Go/Python 调用就废。

2. **性能差 & 体积大**：反射 + 大量元数据（类名、字段名都要写进流）。同一个 POJO，Kryo 比 JDK 原生快 5-10 倍，体积小 3-5 倍。

3. **安全漏洞高发**：`ObjectInputStream.readObject` 会自动执行目标类的 `readObject` / `readResolve` 等钩子。如果 classpath 里有「gadget 类」（如 Commons Collections 的 `InvokerTransformer`），攻击者可以构造恶意流触发任意代码执行（RCE）。真实案例：*Apache Commons Collections 漏洞、fastjson AutoType 漏洞、Log4Shell（虽然主要是 JNDI 但也涉及）*。

4. **接口耦合**：所有要序列化的类都得 `implements Serializable`，业务代码里到处飘这个标记接口，很丑。

追问 为什么 Protobuf 天然更安全？

Protobuf 用 **IDL 编译**：先写 `.proto`，编译生成强类型 Java 类。反序列化时只能填这些字段，不会像 `readObject` 那样触发任意类的钩子。没有 gadget chain 的入口。

## 面试场景 8：常见序列化协议对比

协议速度体积跨语言典型场景

**Kryo**极快极小❌ 仅 Java纯 Java 高性能场景（Dubbo/Redis 缓存对象）
**Protobuf**快极小✅ 全语言gRPC 通信、跨服务持久协议
**ProtoStuff**快小✅无需 IDL 的 Protobuf 替代品
**Hessian**中中✅（有限）Dubbo 2.x 默认，兼容老系统
**JSON**慢大✅ 全语言HTTP API、日志、调试
**JDK 原生**最慢最大❌基本不用

追问 Dubbo 3 的默认序列化改成什么了？

Dubbo 3 推荐 **Hessian2**（兼容 2.x）和 **Fastjson2 / Protobuf**（新场景）。因为 Kryo 虽然快但不跨语言，Dubbo 3 强调「云原生 + 多语言」，Kryo 不再是默认。

## 面试场景 9：Java 有哪些语法糖？

🧑‍💻 你

「语法糖」指编译器帮你写的便捷语法，字节码里其实都是基础指令。Java 常见的十几种：

1. **增强 for（for-each）**：数组解糖为普通 `for(int i)`；集合解糖为 `Iterator.hasNext/next`。

2. **switch on String**：先算 `hashCode` 分派，再 `equals` 验证防哈希碰撞。

3. **switch on 枚举**：编译期生成一个 `int[]` 映射表。

4. **自动装箱/拆箱**：`Integer.valueOf(int)` / `Integer.intValue()`。

5. **泛型**：类型擦除 —— 编译后所有 `<T>` 都变 `Object`（或边界类型）。

6. **可变参数**：`String... args` 编译为 `String[] args`。

7. **枚举**：`enum` 编译为继承 `java.lang.Enum` 的 `final` 类。

8. **内部类**：编译为独立 `Outer$Inner.class`，通过合成方法访问外部私有成员。

9. **try-with-resources**：编译器展开成 `try-finally + close() + addSuppressed()`。

10. **Lambda**：*不是*匿名内部类的糖 —— 编译为 `invokedynamic` + `LambdaMetafactory`，运行时才生成实现类，比匿名内部类快且不生成额外 `.class`。

11. **字符串加号**：JDK 8 及以前编译为 `StringBuilder.append`；JDK 9+ 改为 `invokedynamic + StringConcatFactory`。

12. **数字字面量下划线**：`1_000_000` 编译后就是 `1000000`。

13. **断言 assert**：编译为 `if` + `throw AssertionError`，默认关闭（需 `-ea` 开启）。

14. **var（JDK 10+）**：仅编译期类型推断，字节码里是完整类型。

陷阱 **for-each 里 `list.remove()` 抛 `ConcurrentModificationException`**：因为迭代器维护 `expectedModCount`，集合的 `remove` 改了 `modCount`，下次 `next()` 校验不过就 CME。正确姿势：`Iterator.remove()` 或 `list.removeIf(pred)`。

## 面试场景 10：`"a" + "b" + "c"` 编译后是什么？

🎤 面试官

Java 里字符串拼接是 `+`，底层怎么实现的？

🧑‍💻 你

分两种情况：

- **编译期常量拼接**（全是字面量）：编译期直接折叠成一个 `String` 常量。`"a"+"b"` 就是 `"ab"`，走字符串常量池。

- **运行时变量拼接**（含变量）：

- JDK 8 及以前：编译为 `new StringBuilder().append(a).append(b).toString()`。

- JDK 9+：编译为 `invokedynamic` 指令，绑定到 `java.lang.invoke.StringConcatFactory.makeConcatWithConstants`。JVM 运行时会选最优拼接策略（如提前算总长一次分配 char[]），比 StringBuilder 快 30-50%。

所以现代 JDK 里普通 `+` 已经足够快，**不需要手动 `StringBuilder`**。但循环里累加字符串还是要用 `StringBuilder`：`for (String s : list) result += s;` 每次迭代都新建一个 `StringBuilder`，退化成 O(n²)。

追问 为什么 JDK 9 改用 `invokedynamic` 而不继续 `StringBuilder`？

三个理由：**字节码更短**（一条 `invokedynamic` 代替好几条 `new/dup/invokespecial/append/toString`）、**运行时选策略**（可以针对小字符串走定长 char[] 快速路径）、**为未来 Value Types 铺路**（Project Valhalla）。这类似 Lambda 的思路 —— *延迟决策到运行时*。

## 💻 代码验证

### 验证 1：手写一个 SPI 完整示例

```
// ==== 1. 定义接口 ====
package com.example.spi;
public interface Greeter {
String hello(String name);
}

// ==== 2. 实现 A ====
package com.example.spi.impl;
public class EnglishGreeter implements Greeter {
public String hello(String name) { return "Hello, " + name; }
}

// ==== 3. 实现 B ====
public class ChineseGreeter implements Greeter {
public String hello(String name) { return "你好，" + name; }
}

// ==== 4. 约定文件：src/main/resources/META-INF/services/com.example.spi.Greeter ====
// 内容：
com.example.spi.impl.EnglishGreeter
com.example.spi.impl.ChineseGreeter

// ==== 5. 调用方 ====
import java.util.ServiceLoader;
public class SpiDemo {
public static void main(String[] args) {
ServiceLoader<Greeter> loader = ServiceLoader.load(Greeter.class);
for (Greeter g : loader) {
System.out.println(g.hello("Java"));
}
}
}
// 输出：
// Hello, Java
// 你好，Java
```

### 验证 2：serialVersionUID 陷阱演示

```
import java.io.*;

// 第一版
class User implements Serializable {
// 没写 serialVersionUID → JVM 自动生成
String name;
int age;
}

// 主程序 A：序列化
try (var out = new ObjectOutputStream(new FileOutputStream("u.bin"))) {
User u = new User();
u.name = "Alice"; u.age = 30;
out.writeObject(u);
}

// 之后你给 User 加了一个字段 email —— 结构变了，自动 UID 也变

// 主程序 B：反序列化老数据
try (var in = new ObjectInputStream(new FileInputStream("u.bin"))) {
User u = (User) in.readObject();  // ← 抛 InvalidClassException！
}

// 正确做法：一开始就写死
class UserSafe implements Serializable {
private static final long serialVersionUID = 1L;   // ← 显式声明
String name;
int age;
}
```

### 验证 3：语法糖反编译观察

```
// Sugar.java
import java.util.List;
public class Sugar {
public static void main(String[] args) {
List<String> list = List.of("a", "b", "c");
for (String s : list) {             // 语法糖：增强 for
System.out.println(s);
}

String day = "MON";
switch (day) {                      // 语法糖：switch on String
case "MON" -> System.out.println("Monday");
case "TUE" -> System.out.println("Tuesday");
}
}
}

$ javac Sugar.java
$ javap -c Sugar

// 你会看到：
// for-each 部分：变成 Iterator + hasNext + next 的循环
// switch 部分：先算 day.hashCode() 分派 tableswitch，
//              再 String.equals 确认（防止 hashCode 碰撞）
```

### 验证 4：字符串加号 JDK 8 vs JDK 17 反编译对比

```
// Concat.java
public class Concat {
public static String make(int i) {
return "value=" + i + ",twice=" + (i * 2);
}
}

// 用 JDK 8 编译 + javap -c：
//   new StringBuilder
//   invokespecial <init>
//   ldc "value="
//   invokevirtual append(Ljava/lang/String;)
//   iload_0
//   invokevirtual append(I)
//   ...
//   invokevirtual toString

// 用 JDK 17 编译 + javap -c：
//   iload_0
//   iload_0
//   iconst_2
//   imul
//   invokedynamic #7,  0    // makeConcatWithConstants
// 一条 invokedynamic 搞定，JVM 运行时选最优实现。
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 SPI 三步走的具体步骤是什么？</summary>

1) 定义接口；2) 实现方在 JAR 里放 `META-INF/services/<接口全名>` 文件，内容是实现类全名；3) 调用方 `ServiceLoader.load(接口.class)` 遍历。

</details>

<details>

<summary>Q2 `Class.forName("com.mysql.cj.jdbc.Driver")` 从 JDBC 4.0 起为什么可以省略？</summary>

因为 `DriverManager` 静态初始化时通过 `ServiceLoader` + 线程上下文类加载器（TCCL）自动发现并加载 classpath 里所有 `Driver` 实现。JDBC 驱动 JAR 里的 `META-INF/services/java.sql.Driver` 文件就是钩子。

</details>

<details>

<summary>Q3 为什么规范要求所有 `Serializable` 类显式声明 `serialVersionUID`？</summary>

不显式声明的话 JVM 会根据类结构自动生成，任何字段/方法变动都会让 UID 变，导致老数据反序列化时抛 `InvalidClassException`。显式声明后，UID 变不变由开发者控制。

</details>

<details>

<summary>Q4 Lambda 表达式的底层实现是什么？和匿名内部类有什么区别？</summary>

Lambda 编译为 `invokedynamic` 指令，由 `LambdaMetafactory` 在运行时按需生成实现类（不写成 `.class` 文件）。相比匿名内部类：*不产生额外 class 文件、启动更快、可以复用生成的类*。

</details>

<details>

<summary>Q5 循环里 `result += s` 慢在哪？怎么改？</summary>

JDK 8 每次 `+=` 都新建 `StringBuilder`；JDK 9+ 每次都走 `invokedynamic` 也会分配新 char[]。累计是 O(n²)。改成显式复用同一个 `StringBuilder`：`var sb = new StringBuilder(); for (var s : list) sb.append(s);`。

</details>

#### 📖 原文

-

-

-

- JDK · `ServiceLoader` API

- JDK · `StringConcatFactory` API

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0009：**BigDecimal & 金额存储 & Unsafe** —— 阶段一最后一课，讲工程实战里常踩的精度坑和 Unsafe 魔法类。

💬 想追问「Dubbo 自适应扩展是怎么生成字节码的？」「Kryo 具体怎么用？」「反序列化漏洞怎么防？」—— 随时问我。


