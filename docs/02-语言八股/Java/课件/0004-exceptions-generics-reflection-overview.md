> Lesson 0004 · 阶段一 · Java 基础 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0004 · 异常 & 泛型 & 反射 & I/O · 六合一入门

这一课覆盖的入门半径 —— 我把六个大主题（异常、泛型、反射、注解、I/O、SPI/序列化/语法糖）压在同一节里，采用**「宽而不深」**的策略：先把每块的*骨架和高频问答*过一遍，让你面对任意一个话题都能接得住第一枪。

真正的深挖分散在后续几节：**泛型通配符与类型擦除**放在 ，**反射原理 & 动态代理**放在 ，**SPI、序列化、语法糖三合一**放在 ，**BIO/NIO/AIO 网络模型**放在 0038。所以本节遇到「细节太多」的地方我会直接说「深入放在 0005/0006/0008」—— 不是省略，而是分层。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `try { return 1; } finally { return 2; }` 这个方法返回什么？</summary>

返回 `2`。`finally` 里的 `return` 会覆盖 `try` 里的 `return`。这也是**为什么阿里规约禁止在 finally 里写 return**。第 3 题细讲。

</details>

<details>

<summary>Q0.2 `List<String>.class` 和 `List<Integer>.class` 是同一个 `Class` 对象吗？</summary>

是。运行时都是 `List.class`，泛型参数已经**被擦除**。这就是「类型擦除」的核心结论。第 6 题预告，深入放 0005。

</details>

## 面试场景 1：Exception 和 Error 有什么区别？

🎤 面试官

`Exception` 和 `Error` 有什么区别？`OutOfMemoryError` 和 `StackOverflowError` 属于哪一类？

🧑‍💻 你

两者共同父类都是 `Throwable`，整个体系如下：

```
Throwable
├── Error（JVM 无法恢复的严重问题，程序不该 catch）
│     ├── OutOfMemoryError        ← 堆/元空间耗尽
│     ├── StackOverflowError      ← 栈深度溢出
│     └── NoClassDefFoundError    ← 类加载失败
│
└── Exception（程序可以处理的异常）
├── RuntimeException（非受检 / Unchecked）
│     ├── NullPointerException
│     ├── IllegalArgumentException
│     ├── ClassCastException
│     ├── ArrayIndexOutOfBoundsException
│     └── ArithmeticException
│
└── 其他 Exception（受检 / Checked，编译期强制处理）
├── IOException
├── SQLException
└── ClassNotFoundException
```

- **Error**：*程序无法处理*，通常代表 JVM 层面的严重故障，JVM 一般直接终止线程。`OOM`、`StackOverflowError`、`NoClassDefFoundError` 都属于 Error。

- **Exception**：*程序可以处理*，可以用 `try-catch` 捕获并恢复。

追问 `ClassNotFoundException` 和 `NoClassDefFoundError` 有什么区别？

名字相似，但完全不同的东西：**`ClassNotFoundException`** 是 *Exception*，通常发生在*反射*（`Class.forName("com.x.Y")`）或 *类加载器*找不到指定类时抛出，可以 catch；**`NoClassDefFoundError`** 是 *Error*，通常表示*编译期存在但运行时缺失*（比如 jar 包缺失或类初始化失败），JVM 认为这是致命的 —— 常常是 maven 依赖冲突或部署缺 jar 的信号。

## 面试场景 2：受检异常 vs 非受检异常

🎤 面试官

什么是受检（checked）和非受检（unchecked）异常？各举几个例子。

🧑‍💻 你

- **受检异常（Checked Exception）**：编译器强制要求处理 —— 要么 `try-catch`，要么方法签名 `throws`。*不处理编译不过。* 典型例子：`IOException`、`SQLException`、`ClassNotFoundException`、`InterruptedException`。

- **非受检异常（Unchecked Exception）**：`RuntimeException` 及其子类，加上 `Error`。编译器不强制处理。典型例子：`NullPointerException`、`IllegalArgumentException`、`ClassCastException`、`ArithmeticException`、`ArrayIndexOutOfBoundsException`、`NumberFormatException`。

判断口诀：*「Runtime + Error = 不受检；其他 Exception = 受检」*。

追问 项目里应该优先用受检还是非受检异常？

业界（包括《Effective Java》和阿里规约）主流观点：**默认用非受检异常（RuntimeException）**。理由是受检异常会污染方法签名、逼调用方写大量 `try-catch`，且和 lambda / Stream 不兼容（`Function.apply` 签名不能抛受检异常）。只有*业务逻辑的一部分、调用方必须处理*的场景（比如「余额不足」「订单已关闭」）才考虑受检异常。

陷阱 `SQLException` 是受检的，这也是为什么 Spring 用 `DataAccessException`（*非受检*）把它包了一层 —— 让上层业务代码不用被 `try-catch SQLException` 绑架。这是「受检 vs 非受检」讨论的现实案例。

## 面试场景 3：try-catch-finally 执行顺序 ⭐经典陷阱

🎤 面试官

看这段代码，猜返回值：

```
public static int f(int value) {
try {
return value * value;
} finally {
if (value == 2) {
return 0;
}
}
}
// f(2) = ?
// f(3) = ?
```

🧑‍💻 你

`f(2) = 0`，`f(3) = 9`。规则是：

1. **finally 一定会执行**（除非 `System.exit(int)`、JVM 崩溃或线程被强制杀死）。

2. `try`/`catch` 中的 `return` 会*先把返回值算好并暂存*，然后执行 `finally`，最后才真的返回那个暂存值。

3. 但如果 `finally` 里*自己也有 return*，则会**覆盖**暂存值 —— 这就是坑。

所以 `f(2)`：try 算出 4 暂存 → finally 里 `return 0` 覆盖 → 返回 0。`f(3)`：try 算出 9 暂存 → finally 分支不进 → 返回 9。

追问 `finally` 里改*引用类型字段*能影响返回值吗？

能。如果 `try` 里 `return list;`，finally 里 `list.add(x);`，因为返回的是*引用*，调用方拿到的是同一个 `list` 对象，能看到 `add` 后的变化。**但如果 finally 里 `list = new ArrayList<>();` 重新赋值，则不影响** —— 因为暂存的是原来的引用。

追问 `System.exit(0)` 之后 finally 还执行吗？

不执行。`System.exit` 会请求 JVM 关闭，一旦通过 SecurityManager 校验，JVM 立即终止，*后续的 finally 不再执行*。其他不执行 finally 的情况：`Runtime.getRuntime().halt()`（比 exit 更粗暴）、进程被 `kill -9`、断电、JVM 自身崩溃。

陷阱 **阿里规约「禁止在 finally 中 return」**：一是覆盖 try 的返回值造成困惑；二是会*吞掉 try 抛出的异常*（finally return 后异常就丢了，堆栈里啥都看不到，线上排查噩梦）。

## 面试场景 4：try-with-resources（★推荐用法）

🎤 面试官

为什么 JDK 7 之后推荐 `try-with-resources`？和传统 `try-finally` 关资源相比有什么优势？

🧑‍💻 你

`try-with-resources` 是 JDK 7 引入的语法糖，任何实现了 `java.lang.AutoCloseable`（或它的子接口 `java.io.Closeable`）的对象都能用。声明在 `try(...)` 括号里的资源，会在 try 块结束时**按声明的相反顺序自动 `close()`**。

相比传统写法的三大优势：

1. **更简洁**：省掉手写 `finally { if(x!=null) x.close(); }` 的模板。

2. **不会丢失原始异常**：如果 try 块抛异常 A，随后 `close()` 又抛异常 B，传统写法里 A 会被 B *吃掉*；try-with-resources 会保留 A 作为主异常，B 作为「suppressed exception」附加进去，通过 `Throwable#getSuppressed()` 拿到。

3. **多资源自动逆序关闭**：分号分隔多个资源，无需嵌套 try。

追问 `AutoCloseable` 和 `Closeable` 有什么区别？

`Closeable`（`java.io`，JDK 5）继承自 `AutoCloseable`（`java.lang`，JDK 7），差别在 `close()` 抛出的异常：`Closeable.close()` 抛 `IOException`，`AutoCloseable.close()` 抛更宽泛的 `Exception`。**新代码用 `AutoCloseable`**，语义更通用（数据库连接、锁、临时资源等都能用）。

## 面试场景 5：异常链和自定义异常

🎤 面试官

什么是「异常链」？项目里怎么设计业务异常？

🧑‍💻 你

**异常链（Exception Chaining）**：捕获底层异常后，用它作为「原因」包装成上层异常再抛出，形成链式结构。通过 `Throwable` 的两个构造器实现：

```
public Throwable(String message, Throwable cause);
public Throwable(Throwable cause);
```

示例：

```
try {
userDao.findById(id);
} catch (SQLException e) {
throw new BusinessException("查询用户失败, userId=" + id, e);  // ← e 是 cause
}
```

好处是**保留完整堆栈**：上层拿到 `BusinessException` 后能通过 `getCause()` 一路追到根因，日志里也会打印 `Caused by: ...`。

**自定义业务异常**的常见套路：

1. 继承 `RuntimeException`（非受检，不污染签名）。

2. 带 `errorCode`（错误码）+ `message`（提示） + `cause`（根因）。

3. 配合*全局异常处理器*（Spring 的 `@RestControllerAdvice + @ExceptionHandler`）统一转成 JSON 返回。

追问 为什么不推荐 `catch (Exception e)` 兜底？

兜底 `Exception` 会**把 `RuntimeException` 也一起吃了**，包括 `NPE`、`ClassCastException` 这类*本该暴露出来修 bug* 的异常，导致线上「静默失败」—— 数据错了但日志里啥也没有，排查极难。正确姿势：*只 catch 你能处理的具体异常类型*，兜不住的让它往上抛，由框架的全局处理器统一记录并返回 5xx。

## 面试场景 6：泛型有哪些使用方式？

🎤 面试官

Java 泛型有哪几种使用方式？项目里在哪些地方用过？

🧑‍💻 你

三种典型使用方式：

1. **泛型类**：`class Box<T> { T value; }`

2. **泛型接口**：`interface Comparator<T> { int compare(T a, T b); }`

3. **泛型方法**：`public static <E> List<E> asList(E... elements)`（类型参数写在返回值前面）

项目里的高频场景：

- **统一响应包装 `CommonResult<T>`**：`Result<User>`、`Result<List<Order>>`，前端解析格式固定，业务字段类型灵活。

- **DAO / Service 基类**：`BaseService<T, ID>`，MyBatis-Plus 的 `BaseMapper<T>` 就是这个套路。

- **集合工具**：`Collections.sort(List<T>)`、`Collectors.toMap`。

- **Excel / JSON 工具**：`ExcelUtil<T>.parse(inputStream)`、`JSON.parseObject(str, new TypeReference<List<User>>(){})`。

核心价值：**编译期类型检查 + 免强制转换**，代码可读性和安全性都提升。

追问 类型擦除后 `List<String>` 和 `List<Integer>` 运行时是同一个 Class 吗？

是。Java 泛型是**「伪泛型」**，编译后所有类型参数都会被擦除为它们的边界（默认 `Object`）。所以运行时 `list1.getClass() == list2.getClass()` 为 `true`，都是 `class java.util.ArrayList`。这直接导致了很多有趣的现象：*不能 `new T[]`、不能 `instanceof List<String>`、不能重载同名方法只靠泛型参数区分*。深入放 。

## 面试场景 7：反射是什么？主要用途？

🎤 面试官

解释一下反射，实际项目里哪些地方用到反射？

🧑‍💻 你

**反射（Reflection）**是 Java 在*运行时*动态获取类信息（字段、方法、注解、构造器）并操作对象的能力。入口是 `Class` 对象，三种拿法：

```
Class<?> c1 = User.class;                    // 编译期已知
Class<?> c2 = user.getClass();               // 有实例
Class<?> c3 = Class.forName("com.x.User");   // 只有类名字符串
```

项目里几乎*所有框架*都深度依赖反射：

- **Spring IoC**：扫描 `@Component` / `@Service`，用反射 `newInstance()` 创建 Bean，用反射 `setField` 注入依赖。

- **JSON 序列化**（Jackson / Fastjson / Gson）：反射读所有 `getter` / 字段名生成 JSON key，反射 `set` 值反序列化。

- **ORM**（MyBatis / Hibernate）：反射把 `ResultSet` 列映射到对象字段。

- **单元测试 mock**（Mockito）：反射替换方法、访问 private 字段。

- **动态代理**：`Proxy.newProxyInstance` + `InvocationHandler`，本质是反射调用真实方法。

**优点**：灵活、通用、解耦。**缺点**：性能开销（JIT 优化受限）、破坏封装（能访问 private）、错误延迟到运行时。深入放 。

追问 反射的性能开销大在哪？项目里怎么优化？

反射的性能开销主要来自*方法查找、访问检查、参数装箱、JIT 无法内联*。优化手段：(1) **缓存 `Method` / `Field` 对象**，别每次调用都 `getDeclaredMethod`；(2) 反复调用前 `setAccessible(true)` 跳过访问检查；(3) JDK 7 之后可用 `MethodHandle`（比反射快很多）；(4) 对性能敏感路径用*字节码生成*（ByteBuddy / ASM / CGLIB）代替反射。

## 面试场景 8：注解的本质是什么？

🎤 面试官

Java 注解本质上是什么？`@Retention` 的三个值各在什么阶段起作用？

🧑‍💻 你

**注解本质是一个继承了 `java.lang.annotation.Annotation` 的特殊接口**（编译器帮你生成）。它自身不做任何事，只是*贴标签*，具体行为靠**注解处理器**解析后执行。

定义注解时用**四大元注解**：

- `@Target`：注解能贴在哪（类 `TYPE`、方法 `METHOD`、字段 `FIELD`、参数 `PARAMETER`...）。

- `@Retention`：注解活到什么阶段（下面详解）。

- `@Documented`：`javadoc` 生成文档时是否包含。

- `@Inherited`：子类是否继承父类的这个注解。

`@Retention` 的三个值：

值存在阶段处理时机典型例子

`SOURCE`只在源码编译器读完就丢`@Override`、`@SuppressWarnings`、Lombok `@Data`
`CLASS`存在 .class 字节码类加载时丢，运行时反射拿不到默认值，多用于字节码增强工具
`RUNTIME`加载进 JVM 后依然存在反射能拿到Spring 的 `@Component`、`@Autowired`、JUnit 的 `@Test`

**注解处理器**分两大类：

1. **编译期处理器**：APT（Annotation Processing Tool），代表如 Lombok（生成 getter/setter）、MapStruct（生成 Bean 映射代码）、Dagger（生成依赖注入代码）。特点是*不影响运行时性能*。

2. **运行期处理器**：靠反射，代表如 Spring 全家桶、JUnit。特点是*灵活但有反射开销*。

追问 `@Override` 为什么是 `SOURCE`？

因为它只在*编译期*提示编译器「检查这个方法是否真的重写了父类方法」，检查完就没用了 —— 字节码里保留它没意义。相似的 `@SuppressWarnings`、`@FunctionalInterface` 也是 `SOURCE`。

## 面试场景 9：I/O 分类（字节流 vs 字符流 & BIO/NIO/AIO）

🎤 面试官

Java I/O 有哪些分类？BIO、NIO、AIO 的区别用一句话说清楚。

🧑‍💻 你

先看**数据单位**维度，Java I/O 分两大流派，每派各有输入输出：

类别抽象基类处理单位典型子类

字节输入流`InputStream`1 byte`FileInputStream`、`BufferedInputStream`
字节输出流`OutputStream`1 byte`FileOutputStream`、`BufferedOutputStream`
字符输入流`Reader`1 char (2 byte)`FileReader`、`BufferedReader`
字符输出流`Writer`1 char (2 byte)`FileWriter`、`PrintWriter`

**为什么分字节和字符？**字符流本质是字节流 + 编码转换（`InputStreamReader` 就是桥）。如果直接用字节流处理*文本*，容易踩两个坑：(1) 一个中文占多个字节，读半个字节就打印会乱码；(2) 你必须知道文件编码。字符流帮你把编码这层*屏蔽*了。经验规则：*处理文本用字符流，处理二进制（图片、音视频、序列化对象）用字节流*。

**再看 I/O 模型**维度：

- **BIO**（Blocking I/O，JDK 1.0）：`InputStream.read()` 会*阻塞*直到有数据。一个连接一个线程，高并发场景线程爆炸。

- **NIO**（Non-blocking I/O，JDK 1.4）：基于*Channel + Buffer + Selector*，一个线程可以监听多个 Channel，Netty 就是它的封装。

- **AIO**（Asynchronous I/O，JDK 1.7）：真正异步 —— 发起 I/O 调用立刻返回，OS 完成后通过回调通知。Linux 上底层还是 epoll 模拟，用得不多。

深入放 0038。

追问 NIO 和 BIO 的核心区别是什么？一句话答。

BIO 是*「一个连接一个线程 + 线程阻塞等数据」*，NIO 是*「一个线程用 Selector 轮询多个 Channel + 有数据才处理」*。核心区别是**「阻塞 vs 多路复用」**。

## 面试场景 10：序列化 & 语法糖 & SPI 概览

🎤 面试官

什么是序列化？什么是语法糖？SPI 又是什么？（三个小问题一起过）

🧑‍💻 你

**序列化**：把内存里的对象转成可存储/传输的字节流（或 JSON/XML）；反序列化是反向过程。JDK 内置 `Serializable` 接口 + `ObjectOutputStream`，但业界主流是 JSON（Jackson）、Protobuf、Kryo —— 因为 JDK 原生序列化*不跨语言、体积大、还有反序列化 RCE 安全漏洞*。`serialVersionUID` 用来在类结构变化后*校验兼容性*。深入放 。

**语法糖（Syntactic Sugar）**：编译器提供的*写法便利*，JVM 层面并不认识。`javac` 会在编译期把语法糖*解糖*成基础语法。常见语法糖：泛型（擦除）、自动装箱拆箱（`Integer.valueOf`）、增强 for 循环（迭代器）、变长参数（数组）、try-with-resources、Lambda（`invokedynamic`）、字符串 switch（hash + equals）、枚举（`Enum` 子类）。深入放 0008。

**SPI（Service Provider Interface）**：JDK 内置的*服务发现机制*，让「接口」和「实现」解耦。调用方定义接口，第三方在 `META-INF/services/<接口全限定名>` 文件里写实现类，`ServiceLoader.load(接口)` 在运行时自动发现所有实现。典型用途：JDBC 驱动加载（`DriverManager` 就是 SPI）、SLF4J 日志适配、Dubbo 的扩展点机制（增强版 SPI）。**SPI vs API**：API 由实现方定接口和实现，调用方调用；SPI 由*调用方*定接口，实现方按规则提供实现 —— 控制权反了。深入放 。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：finally 覆盖 return 的经典陷阱

```
public class FinallyReturn {
public static int f(int value) {
try {
return value * value;      // 暂存返回值
} finally {
if (value == 2) {
return 0;               // 覆盖！
}
}
}

public static void main(String[] args) {
System.out.println(f(2));       // 0
System.out.println(f(3));       // 9
}
}
```

### 验证 2：try-with-resources 的抑制异常

```
public class SuppressedDemo implements AutoCloseable {
private final String name;
SuppressedDemo(String name) { this.name = name; }

void work() { throw new RuntimeException("work failed: " + name); }

@Override
public void close() { throw new RuntimeException("close failed: " + name); }

public static void main(String[] args) {
try (SuppressedDemo d = new SuppressedDemo("A")) {
d.work();                    // 抛主异常
} catch (Exception e) {
System.out.println("main: " + e.getMessage());
for (Throwable s : e.getSuppressed()) {
System.out.println("suppressed: " + s.getMessage());
}
}
}
}
// 输出：
// main: work failed: A
// suppressed: close failed: A
```

观察点：主异常保留了 `work failed`，而 `close()` 抛的异常作为 suppressed 附加进去，一个都没丢。传统 `try-finally` 里 `close` 的异常会*覆盖* work 的异常。

### 验证 3：类型擦除的证据

```
import java.util.ArrayList;
import java.util.List;

public class ErasureProof {
public static void main(String[] args) {
List<String> ls = new ArrayList<>();
List<Integer> li = new ArrayList<>();

System.out.println(ls.getClass() == li.getClass());   // true
System.out.println(ls.getClass().getName());          // java.util.ArrayList

// 编译报错：不能只靠泛型参数区分重载
// void m(List<String> l) {}
// void m(List<Integer> l) {}   // ← 「同名方法擦除后签名相同」
}
}
```

### 验证 4：反射三连击 —— 创建对象 + 调方法 + 改私有字段

```
import java.lang.reflect.Field;
import java.lang.reflect.Method;

public class ReflectQuickTour {
static class User {
private String name = "default";
public String greet(String who) { return name + " says hi to " + who; }
}

public static void main(String[] args) throws Exception {
// 1) 拿 Class
Class<?> clazz = Class.forName("ReflectQuickTour$User");

// 2) 反射创建实例
Object user = clazz.getDeclaredConstructor().newInstance();

// 3) 反射改 private 字段
Field name = clazz.getDeclaredField("name");
name.setAccessible(true);       // ← 破坏封装
name.set(user, "Alice");

// 4) 反射调方法
Method greet = clazz.getDeclaredMethod("greet", String.class);
Object result = greet.invoke(user, "Bob");

System.out.println(result);     // Alice says hi to Bob
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `OutOfMemoryError` 属于 Exception 还是 Error？该不该 catch？</summary>

属于 `Error`。**不该 catch** —— JVM 已经处于内存耗尽的危险状态，即使 catch 也很难恢复；正确做法是让进程崩溃、由外部（K8s / systemd）重启，同时接监控告警。个别场景（如批处理任务里想跳过大对象继续处理）会 catch，但不是主流。

</details>

<details>

<summary>Q2 说出「finally 一定执行」的两个反例。</summary>

(1) `System.exit(int)` 在 finally 之前调用（JVM 关闭）；(2) JVM 崩溃或进程被 `kill -9` / 断电。其他极端情况如 `Runtime.getRuntime().halt()`、线程被强制 stop 也算。*但普通异常抛出、线程正常结束时，finally 一定执行。*

</details>

<details>

<summary>Q3 `@Retention` 的三个值中，Spring 的 `@Autowired` 是哪一个？为什么？</summary>

**`RUNTIME`**。因为 Spring 需要在*运行时*用反射扫描 `@Autowired` 注解并注入依赖 —— 如果是 `SOURCE` 或 `CLASS`，运行时反射就拿不到，功能就废了。

</details>

<details>

<summary>Q4 `List<String>` 和 `List<Integer>` 运行时是否同一个 Class？这个现象叫什么？</summary>

是同一个 `Class`（都是 `java.util.ArrayList`）。这叫**类型擦除（Type Erasure）**—— 编译后所有泛型参数都被擦除为它们的边界（默认 `Object`），JVM 层面没有「泛型」概念。深入放 0005。

</details>

<details>

<summary>Q5 一句话说清 BIO、NIO、AIO 的区别。</summary>

BIO 是*同步阻塞*（一连接一线程，线程 `read()` 阻塞等数据）；NIO 是*同步非阻塞 + 多路复用*（一个线程用 `Selector` 监听多个 `Channel`，Netty 底座）；AIO 是*异步非阻塞*（发起 I/O 立即返回，OS 完成后回调通知）。核心演进是「阻塞 → 多路复用 → 事件回调」。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源，覆盖异常/泛型/反射/注解/SPI/I/O/序列化/语法糖

- Oracle Tutorial · Lesson: Exceptions —— 异常体系的官方教程

- Oracle Tutorial · Lesson: Generics —— 泛型入门

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0005：**泛型深挖 —— `<? extends T>` / `<? super T>` / PECS 原则 / 类型擦除的所有副作用**。会把本节场景 6 里所有「深入放 0005」的悬念一次填完。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


