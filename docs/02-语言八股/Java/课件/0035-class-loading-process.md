> Lesson 0035 · 阶段四 · JVM · ⭐⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0035 · 类加载过程详解

这一课覆盖 。类加载是「*.class 字节码 → JVM 内部运行时数据结构*」的转换过程。面试常问三件事：**5 大阶段是哪 5 个**、**准备阶段的陷阱**（不做业务赋值）、**初始化时机**（哪些操作会/不会触发 `<clinit>`）。下一课  会讲负责这些流程的*类加载器*本身。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 类加载分几个阶段？请按顺序列出。</summary>

**5 个**：加载 Loading → 验证 Verification → 准备 Preparation → 解析 Resolution → 初始化 Initialization。验证、准备、解析合称「连接（Linking）」。之后还有「使用」和「卸载」但不算加载。第 1 题细讲。

</details>

<details>

<summary>Q0.2 `static int x = 5;` 中 x=5 是哪个阶段做的？</summary>

**不是**准备阶段！准备阶段只赋默认值 `x = 0`；`x = 5` 是*初始化*阶段执行 `<clinit>()` 时做的。这是经典陷阱题。第 4、6 题细讲。

</details>

## 面试场景 1：类加载的 5 大阶段（★核心必背）

🎤 面试官

把 Java 类加载的全过程说一下。

🧑‍💻 你

```
┌─────────┐   ┌─────────────────────────────────┐   ┌──────────┐   ┌─────┐
│ Loading │ → │ Verification → Preparation → Resolution │ → │ Initialization │ → 使用 → 卸载
└─────────┘   └─────────────────────────────────┘   └──────────┘   └─────┘
└────── Linking ────────┘
```

- **加载 Loading**：从 .class（磁盘/JAR/网络/动态生成）读字节流 → 转成方法区结构 → 堆里生成 `Class` 对象作访问入口

- **验证 Verification**：文件格式（魔数/版本）+ 元数据（继承合法性）+ 字节码（指令合法性）+ 符号引用（能不能解析）4 步；防恶意/坏字节码

- **准备 Preparation**：为**类变量（static）**分配内存 + 赋*默认值*（0/null/false，*不是业务代码里的值*）

- **解析 Resolution**：常量池里的符号引用（`CONSTANT_Class_info` 等）替换为直接引用（内存指针）；可延后到实际使用（惰性解析）

- **初始化 Initialization**：执行 `<clinit>()`（编译器把所有 `static` 字段赋值和 `static {}` 块合并成的类构造器）

后面还有*使用（对象访问）*和*卸载（类被 GC）*两个阶段，一般不算「加载」。

## 面试场景 2：加载 Loading 阶段做什么？

🧑‍💻 你

三件事：

1. 通过**全限定名**（如 `com.example.User`）拿到二进制字节流

2. 把字节流转成方法区（元空间）里的*运行时数据结构*

3. 在堆里生成 `java.lang.Class<User>` 对象，作为访问该类元数据的入口（所有反射 API 都从这里出发）

字节流来源非常灵活：JAR/WAR、网络下载（早期 Applet）、加密文件解密后的字节、CGLIB/Javassist 运行时字节码生成、JSP 动态编译等。*加载不等于文件读取*，只要能拿到合法字节数组即可。

## 面试场景 3：验证 Verification 阶段做什么？

🧑‍💻 你

4 步安全检查，任何一步失败都抛异常终止加载：

1. **文件格式验证**：魔数是不是 `0xCAFEBABE`、版本号是否本 JVM 支持、常量池索引是否合法

2. **元数据验证**：类是否继承了 final 类、接口/抽象类实现是否合规、字段方法签名是否重复

3. **字节码验证**：每条指令的操作数栈类型是否匹配、跳转目标是否合法、局部变量表访问是否越界（最耗时）

4. **符号引用验证**：解析阶段前的准备验证，检查符号引用能否被解析（类是否可访问、方法是否存在等）

常见异常：`ClassFormatError`、`VerifyError`、`NoSuchMethodError`、`NoSuchFieldError`、`IllegalAccessError`。*可以用 `-Xverify:none` 关闭验证换取启动速度，但不推荐生产*。

## 面试场景 4：准备 Preparation 阶段（★经典陷阱）

🎤 面试官

`public static int x = 5;` 在准备阶段 x 是多少？

🧑‍💻 你

**x = 0**！准备阶段只做两件事：

1. 给*类变量*（`static` 字段，不含实例变量）分配内存 —— 分配在方法区/元空间

2. 赋**默认零值**（int=0, long=0L, float=0.0f, boolean=false, Object=null 等）

*业务赋值 5 是在初始化阶段的 `<clinit>()` 里做的*。这是最经典的准备/初始化混淆陷阱。

追问 那 `public static final int MAX = 100;` 在准备阶段呢？

**特殊！**如果字段有 `ConstantValue` 属性（`final` 修饰 + 编译期常量），准备阶段就*直接赋成 100*，不再等初始化。这也是为什么访问其他类的 `static final` 常量不会触发对方类的初始化 —— 常量早就被内联进使用者的常量池了。

## 面试场景 5：解析 Resolution 阶段

🧑‍💻 你

把常量池里的**符号引用**（如 `CONSTANT_Class_info { name_index=#3 }`，只是一个名字）替换为**直接引用**（真实的内存指针/偏移量）。

解析对象包括：类/接口引用、字段引用、方法引用、接口方法引用、方法类型/句柄、动态调用点。

解析是*惰性的*：JVM 可以选择「加载后立刻解析」或「实际使用时才解析」。`invokedynamic`（Lambda）必须延迟到使用时解析。

## 面试场景 6：初始化 Initialization 阶段（★核心）

🧑‍💻 你

真正开始执行**业务代码**：`<clinit>()` 类构造器。它是编译器*自动生成*的方法，包含：

- 所有 `static` 字段的*赋值*语句（`static int x = 5;` 里的 5）

- 所有 `static {}` 静态代码块

合并顺序**按源代码顺序**：

```
class Foo {
static int a = 1;         // 1
static {                   // 2
b = 3;                 // 覆盖 b 的默认 0
}
static int b = 2;         // 3
}
// 执行完 Foo.b 是 2（第 3 步覆盖第 2 步）
```

**JVM 保证 `<clinit>()` 在多线程下只执行一次** —— 通过内部锁；其他线程会阻塞等待。这也是*DCL 单例*和*枚举单例*能天然线程安全的原因（枚举本身是 `static final` 字段，靠 `<clinit>` 的锁）。

## 面试场景 7：类初始化的 6 种触发时机（★核心）

🧑‍💻 你

1. **字节码指令触发**：`new`、`getstatic`、`putstatic`、`invokestatic`（对应 Java 代码：new 对象、读/写 static 字段、调用 static 方法）

2. **反射**：`Class.forName("xxx")` 默认触发（`ClassLoader.loadClass` 不触发）

3. **初始化子类前，先初始化父类**（接口除外 —— 接口 *被使用*时才初始化）

4. **JVM 启动**：`main` 方法所在的主类

5. **MethodHandle** 首次调用对应的类

6. **接口 default 方法（JDK 8+）**：实现类初始化前，其带 default 方法的接口先初始化

## 面试场景 8：哪些操作*不会*触发初始化？

🧑‍💻 你

- **通过子类引用父类静态字段**：`Child.parentStatic`，只初始化父类不初始化子类

- **数组定义**：`new String[10]`，只触发数组类 `[Ljava.lang.String;` 的加载，不初始化 String

- **引用 `static final` 编译期常量**：`ConstClass.CONST`，常量早已内联到使用者的常量池

- **`ClassLoader.loadClass("xxx")`**：只到加载阶段，不初始化（Spring 就靠这个避免加载类的副作用）

- **`Class.forName(name, false, loader)`**：第二个参数 `initialize=false`，明确要求不初始化

## 面试场景 9：`<clinit>` vs `<init>` 完整对比

维度`<clinit>()``<init>()`

含义类构造器（class initializer）实例构造器（instance initializer）
触发时机类首次使用时（初始化阶段）每次 `new` 对象
作用主体类（全局一次）每个对象实例
包含内容`static` 字段赋值 + `static {}` 块实例字段赋值 + `{}` 实例块 + 构造器代码
父类关系子类 `<clinit>` 前 JVM 会自动先执行父类的子类 `<init>` 里第一句必是 `super()`
线程安全JVM 保证只执行一次每次 new 都执行
是否必生成无 static 内容则不生成无参构造器编译器默认生成

追问 一个类的 `static` 字段和 `static {}` 块交错声明，执行顺序是？

严格按**源代码声明顺序**合并到 `<clinit>`。编译器不会为你排序 —— 谁先写谁先执行。如果 `static {}` 在 `static x` 前引用 `x`，看到的是准备阶段的默认值 0。

## 面试场景 10：`Class.forName` vs `ClassLoader.loadClass`

维度`Class.forName(name)``ClassLoader.loadClass(name)`

加载后是否初始化**是**（执行 `<clinit>`）**否**（只到连接/解析）
使用哪个 ClassLoader调用者的 ClassLoader指定的 ClassLoader
典型使用者JDBC 早期驱动加载、想触发 static 块Spring 加载 Bean 类（避免副作用）
可控性`Class.forName(name, initialize, loader)` 三参版本可控只到 linking，一致

陷阱 JDBC 4.0 起可以不用 `Class.forName("com.mysql.cj.jdbc.Driver")`，因为 `DriverManager` 会通过 SPI + `ServiceLoader` 自动发现驱动。但如果你的老代码里还留着这行 `Class.forName`，它*依赖 static 块把 Driver 注册到 DriverManager* —— 这就是「触发初始化」在实际项目里的经典应用。

## 💻 代码验证

### 验证 1：`-XX:+TraceClassLoading` 观察类加载全过程

```
// Hello.java
public class Hello {
public static void main(String[] args) {
System.out.println("Hello");
}
}

$ javac Hello.java
$ java -XX:+TraceClassLoading Hello

# 输出（节选）：
[Loaded java.lang.Object from shared objects file]
[Loaded java.lang.String from shared objects file]
[Loaded Hello from file:./]
...
# 每个类被加载都会打印一行 —— 帮你诊断「谁触发了这个类」
```

### 验证 2：准备阶段陷阱演示

```
public class PrepDemo {
static int x = 5;
static final int MAX = 100;      // 编译期常量，准备阶段就是 100
static int y;                    // 无显式赋值，准备阶段 = 0

static {
System.out.println("clinit: x=" + x);   // clinit 时 x=5
}

public static void main(String[] args) {
System.out.println(x + " " + MAX + " " + y);   // 5 100 0
}
}
```

### 验证 3：触发初始化 vs 不触发的对比

```
class Parent {
static { System.out.println("Parent init"); }
static int a = 1;
}

class Child extends Parent {
static { System.out.println("Child init"); }
static final int CONST = 100;
}

public class InitTiming {
public static void main(String[] args) {
// 1) 通过子类引用父类字段 → 只初始化父类
System.out.println(Child.a);
//   输出: Parent init
//         1

// 2) 引用编译期常量 → 谁都不初始化
System.out.println(Child.CONST);
//   输出: 100 （Child 都没打 init）

// 3) 数组定义 → 不初始化 Child
Child[] arr = new Child[10];
//   输出: 无

// 4) 显式 new 才触发 Child 初始化
new Child();
//   输出: Child init
}
}
```

### 验证 4：`<clinit>` 线程安全（枚举单例的底层）

```
public class LazySingleton {
private LazySingleton() { }

// JVM 保证 Holder 的 <clinit> 只执行一次，且是线程安全的
private static class Holder {
static final LazySingleton INSTANCE = new LazySingleton();
}

public static LazySingleton getInstance() {
return Holder.INSTANCE;    // 首次访问时才触发 Holder 初始化
}
}

// 这就是「静态内部类单例模式」—— 借助 <clinit> 的天然线程安全性，
// 比 DCL 更简洁（不用 volatile + synchronized 双检）
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 类加载的 5 大阶段是哪 5 个？「连接」包含哪几个？</summary>

加载 → 验证 → 准备 → 解析 → 初始化。连接 = 验证 + 准备 + 解析。

</details>

<details>

<summary>Q2 `static int x = 5;` 在准备阶段 x 是多少？为什么？</summary>

**0**。准备阶段只赋默认零值；`x = 5` 是初始化阶段执行 `<clinit>` 时做的。*例外*：`static final int MAX = 100;` 因为有 ConstantValue 属性，准备阶段就是 100。

</details>

<details>

<summary>Q3 `Class.forName` 和 `ClassLoader.loadClass` 的关键区别？</summary>

`Class.forName` 默认触发初始化（执行 `<clinit>`），JDBC 老代码依赖它注册 Driver；`ClassLoader.loadClass` 只加载不初始化，Spring 用它避免副作用。可用 `Class.forName(name, false, loader)` 三参版本手动控制。

</details>

<details>

<summary>Q4 列出 5 种不会触发类初始化的情况。</summary>

① 通过子类引用父类静态字段（只初始化父类）；② 数组定义 `new Foo[10]`；③ 引用 `static final` 编译期常量；④ `ClassLoader.loadClass`；⑤ `Class.forName(name, false, loader)`。

</details>

<details>

<summary>Q5 静态内部类单例模式为什么线程安全？</summary>

JVM 保证类的 `<clinit>()` 只执行一次（内部锁），且延迟到 *Holder 类首次被访问*时才触发。这天然实现了「懒加载 + 线程安全」，比 DCL 更简洁。

</details>

#### 📖 原文

-

- JVMS §5 · Loading, Linking, and Initializing（一手规范）

- JLS §12.4 · Initialization of Classes and Interfaces

#### 🔗 关联课件

-

-

-

- ``

#### 🧭 下一课预告

Lesson 0036：**类加载器 & 双亲委派模型** —— Bootstrap / Extension / App / 自定义 类加载器；双亲委派的「委派 → 破坏 → 场景」（JDBC、Tomcat、SPI 都涉及）。

💬 想问「JDK 9 模块化后类加载有什么变化？」「静态内部类单例为什么比 DCL 好？」「Tomcat 的 WebappClassLoader 怎么打破双亲委派？」—— 直接问我。


