> Lesson 0036 · 阶段四 · JVM · ⭐⭐⭐⭐⭐ · 预计 55 分钟｜含 8 个面试场景 · 3 段可跑代码 · 5 道自测

# 0036 · 类加载器 & 双亲委派

上一节  讲了类加载的五个阶段。这一节聚焦那个负责「找到 .class 文件」的角色 —— **ClassLoader（类加载器）**，以及它背后那个看似简单却暗藏玄机的**双亲委派模型**。

面试官会问：「双亲委派的目的是什么？怎么打破它？Tomcat 为什么打破？SPI 怎么打破？」—— 这都是高频题。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 你写过自定义 ClassLoader 吗？什么场景需要？</summary>

热部署（不重启换 class）、加密 class 解密加载、从网络/数据库加载 class、多版本 jar 隔离（Tomcat 就是典型）。

</details>

<details>

<summary>Q0.2 JVM 怎么判断两个类是否「相同」？</summary>

**全限定名 + 类加载器** 共同决定唯一性。同一个 .class 被不同 ClassLoader 加载，JVM 认为是**两个不同的类**。

</details>

## 面试场景 1：三层类加载器体系 ⭐核心

🎤 面试官

Java 有哪些类加载器？各自负责加载什么？

🧑‍💻 你

```
┌───────────────────────────────────────────────────────────┐
│          Bootstrap ClassLoader（启动类加载器）               │
│  加载: JAVA_HOME/lib (rt.jar, modules)                      │
│  实现: C++ (HotSpot), 不是 java.lang.ClassLoader 子类        │
│  获取: getClassLoader() 返回 null                           │
└─────────────────────────┬─────────────────────────────────┘
│ 父
┌─────────────────────────▼─────────────────────────────────┐
│          Extension/Platform ClassLoader（扩展/平台加载器）    │
│  加载: JAVA_HOME/lib/ext (JDK 8) / jrt-fs (JDK 9+ 模块)    │
│  实现: sun.misc.Launcher$ExtClassLoader (JDK 8)             │
│        → JDK 9 改名 PlatformClassLoader                     │
└─────────────────────────┬─────────────────────────────────┘
│ 父
┌─────────────────────────▼─────────────────────────────────┐
│          Application/System ClassLoader（应用程序加载器）    │
│  加载: classpath 上的类 (你的业务代码)                        │
│  实现: sun.misc.Launcher$AppClassLoader                     │
│  获取: ClassLoader.getSystemClassLoader()                   │
└───────────────────────────────────────────────────────────┘
│
┌─────────▼─────────┐
│ 自定义 ClassLoader  │
│ (用户自己写的)      │
└───────────────────┘
```

**JDK 9 重要变化**：Extension 机制被**模块系统**取代，ExtClassLoader 改名 PlatformClassLoader。但三层委派关系不变。

追问 怎么验证 Bootstrap ClassLoader 加载了哪些类？

```
// String 是核心类 → Bootstrap 加载 → getClassLoader 返回 null
System.out.println(String.class.getClassLoader()); // null

// 你的类 → AppClassLoader 加载
System.out.println(MyClass.class.getClassLoader());
// sun.misc.Launcher$AppClassLoader@18b4aac2
```

## 面试场景 2：双亲委派模型（Parents Delegation）⭐核心

🎤 面试官

什么是双亲委派？工作流程是怎样的？为什么要这样设计？

🧑‍💻 你

**双亲委派**：一个类加载器收到加载请求后，**自己不先加载**，而是把请求**委派给父加载器**。只有父加载器反馈「找不到」时，才自己去加载。

```
loadClass(String name) 流程:

收到加载请求
│
▼
┌───────────────┐
│ 检查是否已加载？ │──是──→ 直接返回
└───────┬───────┘
│ 否
▼
┌───────────────┐
│ 有父加载器？    │
└───┬───────┬───┘
│是     │否
▼       ▼
父.loadClass()  ┌──────────────┐
│           │findBootstrap │ (尝试 Bootstrap)
▼           │ClassOrNull   │
┌──────────┐    └──────┬───────┘
│ 父成功？  │           │
└──┬───┬───┘    ┌──────▼───────┐
│是 │否      │  findClass() │ ← 自己去加载
▼   ▼       └──────────────┘
返回 自己去加载
```

**源码层面**（ClassLoader.loadClass 核心逻辑）：

```
protected Class<?> loadClass(String name, boolean resolve) {
synchronized (getClassLoadingLock(name)) {
// 1. 检查是否已加载
Class<?> c = findLoadedClass(name);
if (c == null) {
try {
// 2. 委托父加载器
if (parent != null) {
c = parent.loadClass(name, false);
} else {
c = findBootstrapClassOrNull(name); // Bootstrap
}
} catch (ClassNotFoundException e) {}
// 3. 父加载不了，自己来
if (c == null) {
c = findClass(name);
}
}
if (resolve) resolveClass(c);
return c;
}
}
```

**为什么要双亲委派？两个核心目的**：

1. **避免重复加载**：父加载器加载过的类，子加载器不用再加载，保证一个类只被加载一次。

2. **安全隔离**：防止核心 API 被篡改。比如你写一个 `java.lang.String` 类放 classpath 里，Bootstrap 已经加载了 rt.jar 里的 String，你的自定义 String**永远不会被加载**。

追问 双亲委派是强制性的吗？

不是语言强制的，是 **ClassLoader.loadClass() 的实现建议**。你可以 override loadClass 打破它。但 JDK 1.2 之后推荐只 override `findClass()` 而不是 `loadClass()`，以保持双亲委派结构。但现实中有很多打破的案例（见面试场景 5）。

## 面试场景 3：为什么需要自定义 ClassLoader？

🎤 面试官

什么时候需要自己写一个 ClassLoader？怎么写？

🧑‍💻 你

**四个典型场景**：

1. **加载非 classpath 的类**：从网络、数据库、加密文件加载。

2. **类隔离**：同一个类的不同版本同时存在（Tomcat 的每个 WebApp 有自己的 ClassLoader，不同应用的 Spring 版本互不干扰）。

3. **热部署**：检测到 .class 文件变化后，用新的 ClassLoader 重新加载。

4. **字节码增强**：加载时修改字节码（AOP 框架常用）。

**最简单写法**：继承 ClassLoader，只 override `findClass`：

```
class MyClassLoader extends ClassLoader {
private String path;

public MyClassLoader(String path) { this.path = path; }

@Override
protected Class<?> findClass(String name) throws ClassNotFoundException {
byte[] bytes = loadClassBytes(name);
return defineClass(name, bytes, 0, bytes.length);
}

private byte[] loadClassBytes(String name) {
// 从 path 读 .class 文件 → byte[]
String file = path + "/" + name.replace('.', '/') + ".class";
// Files.readAllBytes ...
}
}
```

## 面试场景 4：破坏双亲委派 —— SPI 机制 ⭐核心

🎤 面试官

双亲委派有什么缺点？有哪些经典的「打破」案例？

🧑‍💻 你

双亲委派的模型有个**致命缺陷**：**父加载器无法访问子加载器的类**。

### 案例 1：JDBC 驱动的 SPI 机制 ⭐必考

JDBC 的核心接口（`java.sql.Driver`）在 rt.jar 里，由 **Bootstrap ClassLoader** 加载。但具体的驱动实现（如 `mysql-connector-java.jar`）在 classpath 下，由 **AppClassLoader** 加载。

问题来了：`DriverManager`（Bootstrap 加载的）需要通过 SPI 发现并加载 `com.mysql.cj.jdbc.Driver`（AppClassLoader 加载的）。但 Bootstrap 向下委派给子加载器是**做不到的**！

**解决方案：线程上下文类加载器 Thread Context ClassLoader（TCCL）**

```
// DriverManager 内部实际做法
ServiceLoader<Driver> sl = ServiceLoader.load(Driver.class);
// ServiceLoader 会拿当前线程的 TCCL（默认是 AppClassLoader）去加载实现类
```

这就是 SPI 的「逆向委派」：核心 API 通过 TCCL 回调子加载器加载实现类，**打破了双亲委派自顶向下的单向性**。

### 案例 2：Tomcat 的类加载器 ⭐必考

Tomcat 为了做到**Web 应用隔离**，完全打破了双亲委派：

- 每个 WebApp 有自己的 **WebappClassLoader**，优先自己加载（不走父委派）。

- 只对 JRE 核心类（java.*）走双亲委派（保证安全）。

- 目的：不同应用可以用不同版本的 Spring、不同的 jar，互不干扰。

### 案例 3：OSGi / 模块化

OSGi 的类加载是「网状」的，完全不走树形委派。

陷阱 使用 TCCL 时注意线程池场景 —— 线程池里的线程是复用的，TCCL 可能被前一个任务改过。所以很多框架（Dubbo、Spring Cloud）在任务开始时会 **setContextClassLoader + finally reset**。

## 面试场景 5：类的唯一性 & 对象相等

🎤 面试官

用两个不同的 ClassLoader 加载同一个 class 文件，得到的类相等吗？

🧑‍💻 你

**不相等**。JVM 用「全限定名 + 类加载器实例」作为类的唯一标识。同一个 .class 文件被两个 ClassLoader 加载 → JVM 认为这是**两个不同的类** → `instanceof` 返回 false、`cast` 抛 `ClassCastException`。

```
MyLoader loader1 = new MyLoader("/path1");
MyLoader loader2 = new MyLoader("/path1"); // 同样的 class 文件

Class<?> c1 = loader1.loadClass("com.example.Foo");
Class<?> c2 = loader2.loadClass("com.example.Foo");

System.out.println(c1 == c2);           // false
System.out.println(c1.equals(c2));      // false
```

这就是 **「ClassCastException: com.example.Foo cannot be cast to com.example.Foo」**这种诡异异常的根因 —— 其实它们不是同一个 Foo。

## 面试场景 6：loadClass vs findClass vs defineClass

🎤 面试官

ClassLoader 里 loadClass、findClass、defineClass 分别什么作用？

🧑‍💻 你

方法作用是否 override

**loadClass**实现双亲委派逻辑。先查缓存 → 委派父加载器 → 自己 findClass一般**不** override（否则打破委派）
**findClass**找到 class 文件的字节码。默认抛 ClassNotFoundException**必须** override（自定义加载逻辑）
**defineClass**把 byte[] 转换成 Class 对象（native 方法）不 override，在 findClass 里调用

```
// 自定义 ClassLoader 的标准模板
class MyLoader extends ClassLoader {
@Override
public Class<?> findClass(String name) {
byte[] bytes = loadClassData(name);   // 1. 你自己的加载逻辑
return defineClass(name, bytes, 0, bytes.length); // 2. 调 defineClass
}
// 不 override loadClass！保持双亲委派！
}
```

## 面试场景 7：破坏双亲委派的实际案例 —— Tomcat 深入

🎤 面试官

Tomcat 的类加载器是怎么设计的？每个 WebApp 为什么能隔离？

🧑‍💻 你

```
┌─────────────────────────────────────────────────┐
│           Bootstrap ClassLoader                   │
│           (JRE/lib, 核心类)                        │
└──────────────────────┬──────────────────────────┘
│
┌──────────────────────▼──────────────────────────┐
│           System ClassLoader                      │
│           (Tomcat 启动类, catalina.jar)            │
└──────────────────────┬──────────────────────────┘
│
┌──────────────────────▼──────────────────────────┐
│           Common ClassLoader                      │
│           ($CATALINA_HOME/lib, 共享 jar)           │
└──────┬───────────────────────────────┬──────────┘
│                               │
┌──────▼──────────┐           ┌───────▼──────────┐
│ WebappClassLoader│           │ WebappClassLoader │
│ (App1/WEB-INF)   │           │ (App2/WEB-INF)   │
│ 加载顺序:         │           │ 两者隔离！        │
│ 1. 自己先找       │           │ App1 的 Spring 5 │
│ 2. 委托 Common    │           │ App2 的 Spring 6 │
│ 3. 委托 System   │           │ 互不干扰          │
└─────────────────┘           └──────────────────┘
```

关键设计：**WebappClassLoader 违背双亲委派，优先自己加载**，只对 JRE 核心类走委派。同时 Common 层提供共享 jar（如 JDBC 驱动），避免每个应用都放一份。

## 面试场景 8：JDK 9 模块化对类加载的影响

🎤 面试官

JDK 9 模块化后类加载器有什么变化？

🧑‍💻 你

- **ExtClassLoader → PlatformClassLoader**：名字变了，职责变成加载 Java SE 平台的模块。

- **不再有 rt.jar**：JDK 本身被拆成多个模块（`java.base`、`java.sql` 等），以 jrt 文件系统形式存在。

- **三层关系不变**：Bootstrap → Platform → App 仍然是父子。

- **模块可见性**：模块可以声明 `requires` 和 `exports`，没 export 的包即使 classpath 有，ClassLoader 也拒绝加载。

## 💻 代码验证

### 验证 1：看各层 ClassLoader 加载了什么

```
public class LoaderDemo {
public static void main(String[] args) {
// Bootstrap
System.out.println(String.class.getClassLoader());  // null

// Platform (JDK 8 是 ExtClassLoader)
System.out.println(java.sql.Driver.class.getClassLoader());

// Application
System.out.println(LoaderDemo.class.getClassLoader());

// TCCL
System.out.println(Thread.currentThread().getContextClassLoader());
}
}
```

### 验证 2：自定义 ClassLoader 打破双亲委派

```
class BreakParentLoader extends ClassLoader {
@Override
public Class<?> loadClass(String name) throws ClassNotFoundException {
// 先自己加载 —— 打破双亲委派
try {
return findClass(name);
} catch (Exception e) {
return super.loadClass(name); // fallback
}
}
}
```

### 验证 3：同一个类不同 Loader → instanceof 失败

```
Class<?> c1 = loader1.loadClass("Foo");
Class<?> c2 = loader2.loadClass("Foo");
Object obj1 = c1.newInstance();
Object obj2 = c2.newInstance();

System.out.println(obj1 instanceof Foo); // 取决于 Foo 是用哪个 Loader 加载的
// 如果 Foo 是 AppClassLoader 加载的，而 c1 是自定义加载的
// → instanceof 会返回 false！
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 Java 有哪几层类加载器？各加载什么？</summary>

Bootstrap（JAVA_HOME/lib 核心类，C++，getClassLoader 返回 null）、Platform/Extension（扩展类，JDK 9 起改名）、Application（classpath 用户代码）。三者是父子委派关系。

</details>

<details>

<summary>Q2 双亲委派的工作流程和设计目的？</summary>

收到加载请求 → 先查缓存 → 委托父加载器 → 父无法加载才自己加载。目的：避免重复加载 + 安全隔离（防止核心 API 被篡改）。

</details>

<details>

<summary>Q3 SPI 为什么打破了双亲委派？怎么解决的？</summary>

核心接口（Bootstrap 加载）需要调子加载器的实现类，父找不了子。通过 Thread Context ClassLoader（TCCL）实现逆向委派。JDBC 的 DriverManager 是典型案例。

</details>

<details>

<summary>Q4 Tomcat 为什么打破双亲委派？</summary>

WebApp 隔离：每个应用用独立的 WebappClassLoader，优先自己加载，不同应用可以使用不同版本的 jar 互不干扰。只对 JRE 核心类保持委派。

</details>

<details>

<summary>Q5 同一个 class 文件被两个 ClassLoader 加载，instanceof 结果？</summary>

false。JVM 用「全限定名 + ClassLoader」作为类的唯一标识，不同 Loader 加载的相同文件被视为两个不同的类。

</details>

#### 📖 原文

-

- 《深入理解 Java 虚拟机（第 3 版）》第 7 章 §7.4 类加载器

- JDK 8 ClassLoader API

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0037：**JVM 参数 & 监控工具 & 线上排查** —— 调优实战：堆大小怎么设？jstack/jmap/jstat 怎么用？OOM 怎么现场保存？

💬 有任何疑问 —— 「TCCL 为什么存在？」「Tomcat 的 ClassLoader 日志怎么看？」「热部署怎么用 ClassLoader 实现？」—— 直接问我。


