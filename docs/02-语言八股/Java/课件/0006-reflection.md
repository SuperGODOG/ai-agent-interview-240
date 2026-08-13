> Lesson 0006 · 阶段一 · Java 基础 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0006 · 反射机制深挖：Class & 反射调用 & 性能 & 框架应用

反射（Reflection）是 Java **运行时窥探并操作类的能力**—— 拿到一个 `Class` 对象后，你能在完全不知道具体类名的情况下 *创建实例、调用方法、读写字段、扫描注解*。这一课要把 **「反射为什么慢」** 讲透，还要串起 **Spring IoC、MyBatis 结果集映射、Jackson 序列化、JUnit 扫描 @Test** —— 你日常用的框架，本质上就是一层反射外套。面试频次极高，几乎必被追问到「性能开销来自哪里」和「如何优化」。

本课对应 ，并在此基础上补足 *MethodHandle、LambdaMetafactory、JDK 9 模块化访问限制* 等大厂追问区。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `Class.forName("com.foo.Bar")` 和 `ClassLoader.loadClass("com.foo.Bar")` 有什么关键区别？</summary>

前者会**触发类初始化**（执行 `<clinit>`，即静态代码块与静态字段赋值），JDBC 驱动就靠这个自注册；后者**只做加载和链接，不初始化**，Spring 早期扫描 BeanDefinition 常用后者以避免过早执行副作用。

</details>

<details>

<summary>Q0.2 反射调用一个方法（`Method.invoke`）比直接调用大约慢多少倍？</summary>

数量级上一般是 **数十倍到上百倍**：直接调用被 JIT 内联后接近 *1 ns*，冷的 `Method.invoke` 在 *30–100 ns* 之间；缓存 Method 并 `setAccessible(true)` 后能压到 *5–20 ns*；用 `MethodHandle` + `LambdaMetafactory` 编译后可以逼近直接调用。第 7、8 场景细讲。

</details>

## 面试场景 1：什么是反射？反射的用途是什么？

🎤 面试官

你能用自己的话解释一下反射是什么吗？平时开发里在哪些地方会用到？

🧑‍💻 你

**反射**是 Java 提供的一套 API（集中在 `java.lang.reflect` 包），允许程序在 *运行时* 分析和操作任何一个类：拿到它的字段、方法、构造器、注解、父类、接口，甚至可以在完全不知道类名的情况下 *动态创建实例*、*动态调用方法*、*动态修改字段*。核心入口是 `Class` 对象。

日常能感觉到的反射应用：

- **Spring IoC 容器**：读取 `@Component`、`@Autowired` 后反射 `newInstance` + 反射注入依赖。

- **MyBatis / Hibernate**：从 `ResultSet` 用反射把列值 `set` 进 POJO 的字段。

- **JSON 序列化框架**（Jackson / Gson / Fastjson）：反射遍历字段做序列化和反序列化。

- **JDK 动态代理**：`Proxy.newProxyInstance` 生成的代理类内部靠 `Method.invoke` 转发。

- **JUnit / TestNG**：扫描 `@Test` 注解方法并反射调用。

- **IDE 自动补全 / Debugger**：反射读取对象结构在 IDE 里展开树。

- **JDBC 驱动加载**：`Class.forName("com.mysql.cj.jdbc.Driver")` 触发驱动向 `DriverManager` 自注册。

追问 反射为什么被称为「Java 动态性的基石」？

因为 Java 是静态强类型语言，编译期一切类型都要确定。反射是 Java 在运行时保留 **类型元数据**（method table、field table、annotation）并暴露给程序的唯一官方通道。没有反射，就没有 Spring 这类基于配置/注解装配的框架，也就没有 `Proxy`、`Serializable`、`ORM` 这些「不写死类型」的能力。它是编译期确定性和运行时灵活性之间的桥。

## 面试场景 2：反射的优缺点

维度优点缺点

灵活性
运行时才决定要调用哪个类/方法，适合 *插件化、配置化、注解驱动*
—

封装性
—
**破坏封装**：`setAccessible(true)` 可以直接读写 `private` 字段

安全性
—
绕过泛型的编译期检查（泛型运行时擦除），可以往 `List<Integer>` 塞 `String`

性能
—
比直接调用慢一个数量级，JIT 内联困难（见场景 7）

可维护性
—
方法名变字符串后 IDE 重构失效，编译期错误变运行时错误

模块化
—
JDK 9+ 强封装 `java.base` 内部类，非法反射默认告警，未来会禁

追问 「反射性能差」在业务里真的是问题吗？

大多数场景 **不是瓶颈**。Spring 启动时反射几百次装配 Bean，占用的是启动时间而不是 QPS；MyBatis 在做 `ResultSet → POJO` 时反射，但 IO 早就把这点开销盖过去了。真正会成为瓶颈的场景：*高频热路径每请求反射*（例如你在 Controller 里每次都 `getMethod`），此时必须做**缓存 + `setAccessible` + 甚至用 `MethodHandle`**（见场景 8）。

## 面试场景 3：获取 Class 对象的四种方式

🧑‍💻 你

Java 里获取 `Class` 对象一共四种方式，各有不同用途：

方式写法触发类初始化？典型场景

类字面量
`User.class`
否（仅加载 & 链接）
编译期已知类型，最快、最推荐

对象实例
`user.getClass()`
已初始化过
运行时对象已存在，比如做通用 `toString`

`Class.forName`
`Class.forName("com.foo.User")`
**是**（执行 `<clinit>`）
JDBC 驱动加载、Spring `@Configuration`

`ClassLoader.loadClass`
`cl.loadClass("com.foo.User")`
**否**（只到加载阶段）
Spring 扫描 BeanDefinition、字节码增强工具

追问 为什么 `类名.class` 是最快的？

因为它是一个 **编译期常量**：`javac` 会把 `User.class` 编译成 `ldc` 字节码指令，直接从常量池拿到 `Class` 引用，*不走 `ClassLoader.loadClass`*，也不需要字符串查找。相比之下 `Class.forName` 至少有一次字符串到类的哈希查找。

陷阱 `int.class`、`void.class` 也合法！基本类型和 `void` 都有对应的 `Class` 对象（`Integer.TYPE` 就是 `int.class`），反射操作方法参数类型时经常要用。`Class.forName("int")` 反而会抛 `ClassNotFoundException`—— 基本类型不能通过字符串加载。

## 面试场景 4：Class.forName vs ClassLoader.loadClass ⭐经典追问

🎤 面试官

这两个都能通过字符串拿到 `Class`，工作里应该怎么选？为什么 JDBC 一定要用 `Class.forName`？

🧑‍💻 你

核心差别在 **类加载的三阶段（加载 → 链接 → 初始化）走到哪一步**：

- `ClassLoader.loadClass("X")`：只走 *加载*（把 `.class` 读进方法区、生成 `Class` 对象）—— 静态代码块、静态变量赋值 **都不会执行**。

- `Class.forName("X")`：默认走完 *加载 + 链接 + 初始化*—— **静态代码块会被执行**。也有 3 参重载可以关掉初始化：`Class.forName("X", false, classLoader)`。

JDBC 里 `Class.forName("com.mysql.cj.jdbc.Driver")` 之所以是「魔法一句话」，就是因为 MySQL 驱动的 `Driver` 类里写了：

```
public class Driver implements java.sql.Driver {
static {
// 类初始化时向 DriverManager 注册自己
DriverManager.registerDriver(new Driver());
}
}
```

只有 `Class.forName` 会触发这个静态块，`ClassLoader.loadClass` 不会，所以后者拿到 `Class` 后 `DriverManager.getConnection()` 会找不到驱动。

追问 Spring 为什么倾向用 `ClassLoader.loadClass`？

Spring 在启动的 *Bean 扫描阶段* 只需要 **元数据**（类上有没有 `@Component`、有哪些方法带 `@Bean`），此时并不希望把用户所有类都触发 `<clinit>` —— 静态块里可能有耗时初始化甚至是*依赖尚未就绪*的调用。等真正要实例化 Bean 时，才走 `Class.forName` 或 `Constructor.newInstance`，才会触发初始化。这样能把「知道有哪些类」和「真正启动这些类」解耦。

追问 JDBC 4.0 以后为什么不再需要 `Class.forName` 了？

JDBC 4.0（Java 6）引入了 **SPI 机制**：`DriverManager` 会通过 `ServiceLoader` 自动扫描 `META-INF/services/java.sql.Driver` 文件里声明的驱动实现类，自动加载并注册。所以现代代码只要 `DriverManager.getConnection(url, ...)` 就够了，`Class.forName` 只是历史习惯。

## 面试场景 5：反射操作类的三大对象 —— Constructor / Method / Field

🧑‍💻 你

拿到 `Class` 之后，反射的三个核心 API 是：

- `Constructor`：创建实例。常用 `clazz.getDeclaredConstructor(...).newInstance(...)`。

- `Method`：调用方法。`clazz.getDeclaredMethod("name", 参数类型).invoke(obj, 参数值)`。

- `Field`：读写字段。`clazz.getDeclaredField("name").set(obj, value)` / `.get(obj)`。

要区分 **`getXxx` vs `getDeclaredXxx`**：

- `getMethods()`：*所有 public 方法*，包括从父类和接口继承的。

- `getDeclaredMethods()`：*当前类声明的所有方法*（public/protected/private/default），但 **不含继承**。

- 字段、构造器同理。

追问 想同时拿到「当前类 + 所有父类」的字段怎么办？

没有一步到位的 API，得自己写循环：`while (clazz != null) { fields.addAll(Arrays.asList(clazz.getDeclaredFields())); clazz = clazz.getSuperclass(); }`。Spring 的 `ReflectionUtils.doWithFields(Class, FieldCallback)` 已经封装好了这个模板，业务里推荐直接用。

追问 反射能拿到运行时的泛型信息吗？

能，但要通过 *专门的泛型反射 API*：`Method.getGenericReturnType()` / `Field.getGenericType()` 返回的是 `Type`，可以强转成 `ParameterizedType` 后调用 `getActualTypeArguments()` 拿到 `<T>`。**注意**：只有*声明处*保留的泛型才拿得到（字段、方法签名、父类），像 `new ArrayList<String>()` 这种局部变量因擦除拿不到。所以 Jackson 在反序列化泛型集合时要用 `TypeReference` 匿名子类的技巧保留泛型。

## 面试场景 6：setAccessible(true) 是什么？有什么风险？

🧑‍💻 你

`setAccessible(true)` 会 **跳过 JVM 的访问权限检查**，让你能读写 `private` 字段、调用 `private` 方法。它作用在 `AccessibleObject`（`Method`/`Field`/`Constructor` 的共同父类）上。

它做的两件事：

1. 关掉 *Java 语言层面* 的 `public/protected/private` 校验。

2. 顺带跳过每次 invoke 时的访问权限检查，是**性能优化**的重要一环 —— 缓存 Method 时基本必开。

风险：

- **破坏封装**：能改任意 `private final`（甚至 `String` 的 `value[]`），后果不可控。

- **模块化冲突**（JDK 9+）：如果被访问的类在一个未 `opens` 给你模块的包里，会抛 `InaccessibleObjectException`。运行时报错，编译期发现不了。

- **SecurityManager**（已废弃但历史遗留系统仍在跑）会检查 `ReflectPermission("suppressAccessChecks")`。

追问 JDK 9 模块化后反射访问 `java.base` 内部类为什么会失败？

JDK 9 引入 **JPMS 模块系统**，规定「模块内部包」默认对外*强封装*—— 除非模块显式 `opens` 或 `exports` 出来。`java.base` 里的很多内部类（如 `sun.misc.Unsafe`、`jdk.internal.*`）不再对未命名模块开放。想访问必须在启动时加参数：`--add-opens java.base/java.lang=ALL-UNNAMED`。这也是很多老框架升级到 JDK 17 后启动报 `InaccessibleObjectException` 的根因。

陷阱 JDK 17 起，即使 `setAccessible(true)` 也无法反射修改 `String` 的 `value` 数组 —— `java.lang` 包对未命名模块并未 `opens`。这是当年「反射改字符串常量池」这种恶趣味代码彻底失效的原因。

## 面试场景 7：反射为什么慢？⭐核心

🎤 面试官

反射调用比直接调用慢，你能说出至少三个原因吗？

🧑‍💻 你

反射慢的根因是「本来编译期能确定的事，全被推到运行时」，展开有四条：

1. **JIT 无法内联**：直接调用 `obj.foo()`，JIT 能识别调用点、做*去虚化 + 内联*，最终甚至内联穿透多层调用。而 `method.invoke(obj)` 对 JIT 来说是「调用 `Method.invoke` 这个方法本身」，具体转发到哪个真实方法要看 `Method` 对象的运行时状态，无法在调用点被内联优化。

2. **每次都要做访问权限检查**：`invoke` 会检查调用者是否有权访问目标 `Method`（除非提前 `setAccessible(true)`）。

3. **参数装箱 + Object[] 分配**：`invoke(Object obj, Object... args)` 签名决定了所有基本类型参数必须装箱成 `Integer`、`Long`；可变参数 `Object...` 每次都要 `new Object[]`，返回值也可能装箱。热路径下 GC 压力显著。

4. **方法查找开销**：如果每次都 `clazz.getMethod("foo")`，字符串到 `Method` 的匹配走的是遍历 + `equals`，比缓存后的直接引用调用慢一个数量级。

量级参考（同一台机器 JMH 粗测）：

- 直接调用：**~1 ns**（甚至 JIT 内联后无开销）

- 缓存 Method + `setAccessible(true)`：**~5–20 ns**

- 不缓存 Method：**~30–100 ns**

- 每次都 `Class.forName + getMethod + invoke`：**微秒级**

追问 「JIT 无法内联反射」这个说法在新 JDK 上还准确吗？

不完全准确。JDK 8 之后 HotSpot 引入了 **MethodAccessor 膨胀机制**：一个 `Method` 被 `invoke` 超过 15 次（阈值可用 `-Dsun.reflect.inflationThreshold` 调）后，JVM 会动态生成一个专门的字节码 `Accessor` 类去替换原来的本地方法调用，之后就能被 JIT 优化。所以「反射预热后并不像想象中那么慢」，但仍慢于直接调用 —— 主要瓶颈从「解释执行」转到了「参数装箱 + Object[] 分配」。

## 面试场景 8：反射性能怎么优化？

🧑‍💻 你

从最简单到最极致，四个层次的优化：

1. **缓存 `Class`/`Method`/`Field`**：只在类加载或首次访问时通过反射查一次，之后放到 `ConcurrentHashMap` 里复用。Spring 的 `ReflectionUtils`、Jackson 的 `BeanPropertyDefinition` 都这样做。

2. **`setAccessible(true)`**：跳过每次 invoke 的访问权限检查。基本上只要缓存 Method 就应该同时开这个。

3. **`MethodHandle`（JDK 7+）**：`java.lang.invoke` 提供的更底层调用机制。`MethodHandle.invokeExact` 的调用签名*精确匹配*，JIT 可以像直接调用一样内联；没有 `Object[]` 装箱开销。性能通常是 `Method.invoke` 的 2–5 倍。

4. **`LambdaMetafactory`（JDK 8+）**：把反射调用编译成一个 `Lambda`（本质是 `invokedynamic` 生成的匿名 SAM 实现类），后续调用等同于直接调用一个接口方法。适合「反射一次、后续百万次调用」的场景，如 ORM 的 getter/setter。这是**目前性能上限**，能逼近直接调用。

追问 `MethodHandle` 比 `Method.invoke` 快，具体快在哪里？

三点：**①** `invokeExact` 的签名在 `invokedynamic` 层做类型匹配，参数无需装箱；**②** JVM 把 `MethodHandle` 视为「一等公民」，`MutableCallSite` 让 JIT 能对调用点做内联、去虚化；**③** 没有 `MethodAccessor` 的膨胀开销，从第一次调用就走优化路径。代价是 API 比反射难用（签名必须精确匹配，多一个类型都不行），错用会直接 `WrongMethodTypeException`。

追问 Fastjson 2 / Jackson Blackbird 之类的库为什么号称「零反射」？

它们并不是不用反射，而是**在类第一次遇到时用反射「一次性」生成一个 Getter/Setter 的字节码代理类**（借助 ASM 或 `LambdaMetafactory`），后续序列化就直接调用这个代理，等价于手写代码。所谓「零反射」指的是 *热路径上没有 `Method.invoke`*，冷路径的反射生成依然存在。

## 面试场景 9：反射在主流框架里到底怎么用？

框架反射用在哪关键 API

Spring IoC
扫描 `@Component`、实例化 Bean、注入 `@Autowired` 字段
`Constructor.newInstance` / `Field.set` / `Method.invoke`（`BeanUtils.instantiateClass`）

Spring AOP
JDK 动态代理（接口）、CGLIB（子类）内部都靠反射转发
`Proxy.newProxyInstance` + `InvocationHandler.invoke(Method, args)`

MyBatis
ResultSet → POJO 的字段填充；Mapper 接口的动态代理
`MetaObject` + `Reflector`（内部缓存 Method）

Jackson / Gson
遍历字段/getter 序列化；反射调用无参构造 + setter 反序列化
`Field.getDeclaredFields` + Lambda 优化路径

JUnit
扫描 `@Test`/`@BeforeEach`，反射调用
`Class.getDeclaredMethods` + 注解读取

Lombok
*不用反射*！它是编译期注解处理器（APT）直接改 AST
—

追问 Spring 是通过什么机制实例化你的 `@Component` 类的？

核心链路：`ClassPathBeanDefinitionScanner` 扫到带 `@Component` 的类 → 生成 `BeanDefinition` → `BeanFactory.getBean` 时调 `createBeanInstance` → `SimpleInstantiationStrategy.instantiate` 内部走 `BeanUtils.instantiateClass` → 最终是 `Constructor.newInstance`。字段注入走 `AutowiredAnnotationBeanPostProcessor.postProcessProperties`，反射 `Field.set` 塞值。有兴趣可以在 `BeanUtils.instantiateClass` 打断点看，很直观。

追问 Lombok 明明也在类上加了注解，为什么不算反射？

Lombok 用的是 **Java 编译期注解处理器（`javax.annotation.processing`）**，它在 `javac` 编译阶段就介入 AST 生成，把 `@Data` 展开成真实的 `getter/setter/equals` 字节码。所以运行时的 `.class` 里已经有这些方法了，跟你手写没差别，*零运行时开销*。这也是 Lombok 在字节码里能被 JIT 完美内联的原因。

## 面试场景 10：反射能破坏单例吗？如何防御？

🎤 面试官

如果我用双检锁写了个单例，你能用反射破坏它吗？如何防御？

🧑‍💻 你

能。双检锁、静态内部类等经典单例都有一个共同点：**只是把构造器设成 `private`**，而反射的 `setAccessible(true)` 可以直接跳过。攻击代码就是 `getDeclaredConstructor().setAccessible(true) + newInstance()`，能拿到*新的*实例，破坏「唯一性」。

两种防御手段：

1. **私有构造器里主动抛异常**：如果检测到实例已存在就 `throw new IllegalStateException()`。缺点是要多一段防御代码，且不能防御*第一次反射抢先创建*。

2. **用 `enum` 实现单例**（Effective Java 推荐）：`Constructor.newInstance` 对枚举类会主动检查并抛 `IllegalArgumentException("Cannot reflectively create enum objects")`，从 JDK 层面堵死。同时枚举天然线程安全、序列化不会创建新实例。是**唯一能同时防反射 + 防序列化**的单例写法。

追问 序列化为什么也能破坏单例？枚举怎么防的？

普通类被 `ObjectInputStream` 反序列化时，*不会*走构造器，而是通过 `Unsafe.allocateInstance` 直接开辟内存 —— 单例又被绕过。防御方式是实现 `readResolve()` 方法返回单例实例。枚举根本不需要写 `readResolve`：JVM 保证枚举的反序列化只会返回已存在的枚举值（`Enum.valueOf`），底层就堵住了。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：四种方式获取 Class 对象 + `Class.forName` 触发初始化

```
public class HowToGetClass {
static class Target {
static { System.out.println("<clinit> executed!"); }
private String secret = "hidden";
public void hello() { System.out.println("hello, " + secret); }
}

public static void main(String[] args) throws Exception {
// 方式 1：类字面量（编译期常量，最快，不触发初始化）
Class<?> c1 = Target.class;

// 方式 2：对象.getClass()（对象已存在，早就初始化过）
Target obj = new Target();       // ← 这一行才触发 <clinit>
Class<?> c2 = obj.getClass();

// 方式 3：Class.forName —— 触发初始化（会再打印 clinit 吗？不会，已初始化过）
Class<?> c3 = Class.forName(
"HowToGetClass$Target");

// 方式 4：ClassLoader.loadClass —— 只加载不初始化
Class<?> c4 = HowToGetClass.class
.getClassLoader()
.loadClass("HowToGetClass$Target");

// 四个都是同一个 Class 对象（JVM 保证每个类在同一个 ClassLoader 下唯一）
System.out.println(c1 == c2 && c2 == c3 && c3 == c4);  // true
}
}
// 输出：
// <clinit> executed!
// true
```

把 `new Target()` 这行注释掉，改成先 `ClassLoader.loadClass` 再 `Class.forName`—— 你会看到 `<clinit>` 是在 `Class.forName` 那行才被打出来的，直观验证「加载 ≠ 初始化」。

### 验证 2：Constructor / Method / Field 三大对象完整演示

```
import java.lang.reflect.*;

public class ReflectAll {
public static class User {
private String name;
public User() {}
public User(String name) { this.name = name; }
private String greet(String greeting) {
return greeting + ", " + name;
}
}

public static void main(String[] args) throws Exception {
Class<User> clazz = User.class;

// === Constructor：调用带参构造器 ===
Constructor<User> ctor = clazz.getDeclaredConstructor(String.class);
User u = ctor.newInstance("Alice");

// === Field：直接读写 private 字段 ===
Field nameField = clazz.getDeclaredField("name");
nameField.setAccessible(true);           // 跳过访问检查
System.out.println(nameField.get(u));    // Alice
nameField.set(u, "Bob");                 // 直接改 private
System.out.println(nameField.get(u));    // Bob

// === Method：调用 private 方法 ===
Method greet = clazz.getDeclaredMethod("greet", String.class);
greet.setAccessible(true);
String result = (String) greet.invoke(u, "Hello");
System.out.println(result);              // Hello, Bob

// === getMethods vs getDeclaredMethods ===
System.out.println("declared: " + clazz.getDeclaredMethods().length);
// 包含 private greet；不含 Object.toString/hashCode
System.out.println("public:   " + clazz.getMethods().length);
// 不含 private greet；含继承来的 toString/hashCode/equals 等
}
}
```

### 验证 3：性能对比 —— 直接调用 vs 反射 vs 缓存反射 vs MethodHandle

```
import java.lang.invoke.*;
import java.lang.reflect.Method;

public class ReflectPerf {
static int counter = 0;
public static void bump() { counter++; }

public static void main(String[] args) throws Throwable {
int N = 10_000_000;

// === 1) 直接调用 ===
long t1 = System.nanoTime();
for (int i = 0; i < N; i++) bump();
long d1 = System.nanoTime() - t1;

// === 2) 反射：每次都 getMethod（最慢）===
long t2 = System.nanoTime();
for (int i = 0; i < N; i++) {
ReflectPerf.class.getDeclaredMethod("bump").invoke(null);
}
long d2 = System.nanoTime() - t2;

// === 3) 反射：缓存 Method + setAccessible ===
Method m = ReflectPerf.class.getDeclaredMethod("bump");
m.setAccessible(true);
long t3 = System.nanoTime();
for (int i = 0; i < N; i++) m.invoke(null);
long d3 = System.nanoTime() - t3;

// === 4) MethodHandle ===
MethodHandle mh = MethodHandles.lookup().findStatic(
ReflectPerf.class, "bump", MethodType.methodType(void.class));
long t4 = System.nanoTime();
for (int i = 0; i < N; i++) mh.invokeExact();
long d4 = System.nanoTime() - t4;

System.out.printf("direct:        %,d ns / %,.1f ns per call%n", d1, d1 * 1.0 / N);
System.out.printf("reflect (raw): %,d ns / %,.1f ns per call%n", d2, d2 * 1.0 / N);
System.out.printf("reflect (opt): %,d ns / %,.1f ns per call%n", d3, d3 * 1.0 / N);
System.out.printf("MethodHandle:  %,d ns / %,.1f ns per call%n", d4, d4 * 1.0 / N);
}
}
// 典型输出（M1 / JDK 21，仅供数量级参考）：
// direct:              5,000,000 ns /   0.5 ns per call
// reflect (raw):     650,000,000 ns /  65.0 ns per call
// reflect (opt):      60,000,000 ns /   6.0 ns per call
// MethodHandle:       10,000,000 ns /   1.0 ns per call
```

观察点：*「每次都 getMethod」*比*「缓存 + setAccessible」*慢十倍以上，这就是场景 8 「缓存」优化的真金白银。

### 验证 4：反射破坏单例 & 枚举防御

```
import java.lang.reflect.Constructor;

public class SingletonAttack {
// 经典双检锁单例
public static class DoubleCheck {
private static volatile DoubleCheck INSTANCE;
private DoubleCheck() {}
public static DoubleCheck get() {
if (INSTANCE == null) {
synchronized (DoubleCheck.class) {
if (INSTANCE == null) INSTANCE = new DoubleCheck();
}
}
return INSTANCE;
}
}

// 枚举单例
public enum EnumSingleton {
INSTANCE;
public void doWork() { /* ... */ }
}

public static void main(String[] args) throws Exception {
DoubleCheck a = DoubleCheck.get();

// === 反射攻击双检锁 ===
Constructor<DoubleCheck> c = DoubleCheck.class.getDeclaredConstructor();
c.setAccessible(true);
DoubleCheck b = c.newInstance();  // ← 成功！单例被破坏
System.out.println("DoubleCheck same? " + (a == b));  // false

// === 反射攻击枚举 ===
try {
Constructor<EnumSingleton> ec =
EnumSingleton.class.getDeclaredConstructor(String.class, int.class);
ec.setAccessible(true);
ec.newInstance("HACK", 1);
} catch (Exception ex) {
System.out.println("Enum blocked: " + ex);
// java.lang.IllegalArgumentException: Cannot reflectively create enum objects
}
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话概括「反射」在 Java 里到底是什么。</summary>

Java 提供的一套运行时 API，能通过 `Class` 对象在编译期不知道具体类型的前提下，读取类的元数据（字段/方法/构造器/注解）并动态创建实例、调用方法、读写字段。

</details>

<details>

<summary>Q2 `Class.forName("X")` 和 `ClassLoader.loadClass("X")` 的关键区别？各举一个使用场景。</summary>

前者默认**触发类初始化**（执行静态代码块），JDBC 驱动通过它触发 `DriverManager.registerDriver`；后者**只加载不初始化**，Spring 扫描 BeanDefinition 时用它避免过早触发用户类的副作用。

</details>

<details>

<summary>Q3 反射调用比直接调用慢的四个原因？</summary>

① JIT 无法内联反射调用点；② 每次 invoke 要做访问权限检查（`setAccessible(true)` 可关）；③ 参数装箱 + `Object[]` 分配带来 GC 压力；④ 每次 `getMethod` 字符串查找开销大（可缓存）。

</details>

<details>

<summary>Q4 想优化一段热路径里的反射调用，你会做哪三件事？</summary>

① 缓存 `Class`/`Method`/`Field` 到 `ConcurrentHashMap`；② 缓存后调 `setAccessible(true)` 跳过权限检查；③ 换成 `MethodHandle.invokeExact` 或 `LambdaMetafactory` 生成的接口调用，逼近直接调用性能。

</details>

<details>

<summary>Q5 为什么「枚举单例」被认为是唯一同时防反射和防序列化的写法？</summary>

反射：`Constructor.newInstance` 对枚举类特判抛 `IllegalArgumentException("Cannot reflectively create enum objects")`；序列化：JVM 保证枚举反序列化走 `Enum.valueOf` 返回已有实例，不走 `Unsafe.allocateInstance`，无需手写 `readResolve`。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.lang.reflect` API —— 反射三大对象官方文档

- JDK 21 · `MethodHandle` —— 反射的高性能替代

- JEP 261 · Module System —— JDK 9 模块化对反射的限制

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0007：**动态代理 —— JDK Proxy vs CGLIB vs ByteBuddy**。反射的直接下游，Spring AOP 的底层原理，面试同样必考。

💬 有任何疑问 —— 「MethodHandle 到底怎么用？」「Spring 具体在哪一行调 `newInstance`？」「JDK 17 之后哪些反射玩法彻底失效？」—— 直接问我。我是你的老师，也是你的追问陪练。


