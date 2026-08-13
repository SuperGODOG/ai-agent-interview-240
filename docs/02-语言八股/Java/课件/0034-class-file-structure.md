> Lesson 0034 · 阶段四 · JVM · ⭐⭐⭐ · 预计 45 分钟｜含 8 个面试场景 · 3 段可跑代码 · 5 道自测

# 0034 · 类文件结构

上一节  讲完了 GC，现在我们把镜头从「运行时」拉回「编译时」—— 看看 Java 编译器吐出来的 `.class` 文件里到底装的什么。

面试官问类文件结构，不是要你背二进制格式，而是考察你对 **「平台无关性」的本质理解**：「Java 凭什么一次编译到处运行？.class 文件里放了哪些东西让 JVM 能正确加载执行？」

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 .class 文件的前 4 个字节是什么？</summary>

**魔数 Magic Number**：`0xCAFEBABE`。JVM 用来快速识别「这是不是合法的 class 文件」。面试官最爱问。

</details>

<details>

<summary>Q0.2 你平时用 `javap` 吗？它能看到什么？</summary>

`javap -c` 查看字节码指令，`javap -v` 查看完整的常量池、方法表等。面试场景 6-8 会实操。

</details>

## 面试场景 1：.class 文件的整体结构 ⭐核心

🎤 面试官

一个 .class 文件里包含哪些内容？画一下结构。

🧑‍💻 你

Class 文件是一组以 **8 位字节** 为基础的二进制流，各项数据严格按照顺序紧凑排列，**没有任何分隔符**。JVM 规范定义了严格的格式：

```
ClassFile {
u4             magic;                  // 魔数 0xCAFEBABE
u2             minor_version;          // 次版本号
u2             major_version;          // 主版本号 (JDK 8 = 52, JDK 17 = 61, JDK 21 = 65)
u2             constant_pool_count;    // 常量池数量
cp_info        constant_pool[count-1]; // 常量池（索引从 1 开始！）
u2             access_flags;           // 访问标志
u2             this_class;             // 本类在常量池中的索引
u2             super_class;            // 父类在常量池中的索引
u2             interfaces_count;       // 接口数量
u2             interfaces[count];      // 接口索引表
u2             fields_count;           // 字段数量
field_info     fields[count];          // 字段表
u2             methods_count;          // 方法数量
method_info    methods[count];         // 方法表
u2             attributes_count;       // 属性数量
attribute_info attributes[count];      // 属性表
}
```

记不住没关系，面试时抓住**四大核心**就行：**魔数版本 → 常量池 → 字段方法 → 属性**。

追问 常量池索引为什么从 1 开始而不是 0？

因为设计者把 0 号索引保留给了「不引用任何常量」的语义。这样那些不需要引用常量的数据项（如父类索引、接口索引）就可以填 0 表示「没有」。

## 面试场景 2：魔数（Magic Number）0xCAFEBABE ⭐必问

🎤 面试官

class 文件的魔数是多少？为什么要有魔数？

🧑‍💻 你

**0xCAFEBABE**，4 个字节。作用是让 JVM 判断「这个文件是不是合法的 class 文件」—— 非 class 文件（比如有人把 .txt 后缀改成 .class）开头不会是 CAFEBABE，JVM 直接拒绝加载。

很多文件格式都有魔数：

格式魔数

Java class`0xCAFEBABE`
PNG 图片`0x89504E47`
GIF 图片`GIF89a / GIF87a`
ZIP/JAR`0x504B0304` (PK)
ELF (Linux 可执行文件)`0x7F454C46`

**趣事**：CAFEBABE 是 Sun 公司工程师 James Gosling 起的，据说是为了纪念一家叫「Cafe Babe」的咖啡馆。

## 面试场景 3：常量池（Constant Pool）⭐核心

🎤 面试官

常量池里存的是什么？它有什么作用？

🧑‍💻 你

常量池是 class 文件的**资源仓库**，存两大类常量：

- **字面量 Literal**：文本字符串、final 常量值等。

- **符号引用 Symbolic Reference**：类和接口的全限定名、字段的名称和描述符、方法的名称和描述符。

Java 代码编译时不保存「方法在内存里的最终入口地址」，而是保存**符号引用**。在类加载的「解析」阶段，JVM 才把符号引用替换为**直接引用**（内存地址）。这是 Java 动态链接的基础。

常量池中的每一项都是一个表，共 17 种类型（JDK 21）：

类型标志存什么

CONSTANT_Utf81UTF-8 编码的字符串
CONSTANT_Integer34 字节 int
CONSTANT_Float44 字节 float
CONSTANT_Long58 字节 long
CONSTANT_Double68 字节 double
**CONSTANT_Class**7类或接口的符号引用
CONSTANT_String8String 字面量
**CONSTANT_Fieldref**9字段的符号引用
**CONSTANT_Methodref**10方法的符号引用
CONSTANT_NameAndType12字段/方法的名称+描述符

陷阱 CONSTANT_Long 和 CONSTANT_Double 在常量池里**占两个索引位置**（index 和 index+1）。所以如果常量池里有 long/double，后面的常量索引需要跳过这个「空位」。这就是为什么常量池 actual_count = constant_pool_count - 1。

## 面试场景 4：访问标志 & 类索引

🎤 面试官

class 文件怎么表示 public / final / abstract 这些修饰符？

🧑‍💻 你

用 **access_flags** 的位掩码（bitmask）：2 字节（u2），每个 bit 代表一个修饰符：

标志名值含义

ACC_PUBLIC0x0001public
ACC_FINAL0x0010final（类不可被继承）
ACC_SUPER0x0020invokespecial 新语义（JDK 1.0.2 后强制设为 1）
ACC_INTERFACE0x0200是接口不是类
ACC_ABSTRACT0x0400abstract
ACC_ANNOTATION0x2000是注解类型
ACC_ENUM0x4000是枚举

比如 `public class Foo extends Bar` 的 access_flags = ACC_PUBLIC | ACC_SUPER = 0x0021。

**this_class** 和 **super_class** 都是 u2 类型，存的是**常量池的索引号**，指向 CONSTANT_Class_info。

## 面试场景 5：字段表 & 方法表

🎤 面试官

编译器怎么描述一个字段和一个方法？

🧑‍💻 你

### 字段表 field_info

每个字段包含：access_flags（修饰符）+ name_index（字段名，指向常量池）+ descriptor_index（类型描述符，指向常量池）+ attributes（如 ConstantValue 存 final 默认值）。

**描述符**是 JVM 专用的类型简写：

描述符Java 类型

BbyteCchar
DdoubleFfloat
IintJlong
SshortZboolean
VvoidL类名;引用类型
[数组（每多一个 [ 多一维）

例子：`int[]` → `[I`；`String[][]` → `[[Ljava/lang/String;`；`List<String>` → `Ljava/util/List;`（泛型擦除了！）。

### 方法表 method_info

结构类似字段表。方法描述符格式：`(参数列表)返回值`，如 `int add(int, int)` → `(II)I`。

追问 字段表和方法表会不会包含父类继承来的东西？

**不会**。字段表和方法表**只列本类定义**的字段和方法，不包含父类。父类的字段/方法在加载时通过 super_class 链去找。但编译器可能会生成一些「额外」的方法，比如默认构造器 `<init>` 和类构造器 `<clinit>`。

## 面试场景 6：属性表 —— Code 属性 ⭐核心

🎤 面试官

方法的 Code 属性里存的是什么？max_stack 和 max_locals 有什么意义？

🧑‍💻 你

Code 属性是方法表里最重要的属性，存储**Java 代码编译后的字节码指令**。关键字段：

- **max_stack**：操作数栈的最大深度（编译期可精确计算）。JVM 依此分配栈帧大小。

- **max_locals**：局部变量表需要的最大槽数（包括 `this` 和方法参数）。

- **code[]**：字节码指令序列，每条指令 1 字节操作码 + 0~N 字节操作数。

- **exception_table**：异常处理表（finally 块就是靠它实现的）。

除了 Code 属性，class 文件还有很多其他属性：

属性位置用途

ConstantValue字段final 常量值
**Code**方法字节码指令
LineNumberTableCode 中行号映射（调试用）
LocalVariableTableCode 中局部变量名（调试用）
**Exceptions**方法throws 声明的异常
SourceFile类源文件名
Signature类/字段/方法泛型签名（擦除前的原始泛型信息）
BootstrapMethods类invokedynamic 引导方法

追问 LineNumberTable 去掉会影响运行吗？

不影响运行，但**影响调试和异常堆栈**。去掉后异常堆栈里只显示方法名，不显示行号；Debug 时断点也没法打了。编译器默认都会生成，除非加 `-g:none`。

## 面试场景 7：字节码指令速览

🎤 面试官

说几个常见的字节码指令，new 一个对象在字节码层面怎么体现？

🧑‍💻 你

`Object o = new Object();` 编译后对应三条指令：

```
0: new           #2    // 分配内存，创建 Object 实例（引用压栈）
3: dup                 // 复制栈顶引用（一份给 invokespecial，一份给赋值）
4: invokespecial #3    // 调用 Object.<init>() 构造器
7: astore_1            // 把栈顶引用存入局部变量表 slot 1
```

常用字节码指令分类：

类别典型指令

加载/存储iload, istore, aload, astore, iconst_0, bipush
算术iadd, isub, imul, idiv
类型转换i2l, i2f, i2d, l2i, checkcast
对象创建new, newarray, getfield, putfield
方法调用invokevirtual, invokespecial, invokestatic, invokeinterface, invokedynamic
控制转移ifeq, ifne, goto, tableswitch, lookupswitch
同步monitorenter, monitorexit

**五条方法调用指令的区别**（面试高频）：

- **invokestatic**：调用静态方法（编译期确定版本）

- **invokespecial**：调用构造器、私有方法、父类方法

- **invokevirtual**：调用虚方法（动态分派，多态的核心）

- **invokeinterface**：调用接口方法（需要接口方法表 itable 查）

- **invokedynamic**：动态调用（JDK 7 引入，lambda 表达式的基石）

## 面试场景 8：javap 实战

🎤 面试官

你平时怎么查看字节码？javap 有哪些常用参数？

🧑‍💻 你

```
# 基本反编译
javap Hello.class

# 查看字节码指令（-c = code）
javap -c Hello.class

# 查看完整信息：常量池、字段表、方法表、字节码（-v = verbose）
javap -v Hello.class

# 同时显示行号
javap -l Hello.class

# 反编译 JDK 源码
javap -v java.lang.String
```

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：javap -v 看常量池

```
// Hello.java
public class Hello {
private String name = "world";
public static final int MAX = 100;

public void say() {
System.out.println("Hello " + name);
}
}
```

```
$ javac Hello.java
$ javap -v Hello.class

// 看到:
// Constant pool:
//   #1 = Methodref    #6.#20   // java/lang/Object."<init>":()V
//   #2 = String        #21      // world
//   #3 = Fieldref      #5.#22   // Hello.name:Ljava/lang/String;
//   ...
//   #21 = Utf8         world
//   #22 = NameAndType  #8:#23   // name:Ljava/lang/String;
```

### 验证 2：对比不同 JDK 版本的 class 版本号

```
$ javap -v Hello.class | grep "major"
major version: 52     # JDK 8
major version: 61     # JDK 17
major version: 65     # JDK 21
```

### 验证 3：看 synchronized 的字节码

```
// SyncTest.java
public class SyncTest {
public void doSync() {
synchronized (this) {
System.out.println("locked");
}
}
}
```

```
$ javap -c SyncTest
0: aload_0
1: dup
2: astore_1
3: monitorenter
4: getstatic     #2
7: ldc           #3
9: invokevirtual #4
12: aload_1
13: monitorexit          # 正常退出，释放锁
14: goto          22
17: astore_2             # 异常退出，也要释放锁
18: aload_1
19: monitorexit
20: aload_2
21: athrow
22: return
```

注意看：编译器自动生成了 **两处 monitorexit** —— 正常路径一个，异常路径一个。这就是为什么 synchronized 代码块即使抛异常也不会死锁。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 class 文件的魔数是多少？有什么用？</summary>

0xCAFEBABE。JVM 用魔数快速判断文件是否为合法的 class 文件，防止加载非 class 文件。

</details>

<details>

<summary>Q2 常量池里存什么？为什么要有符号引用？</summary>

存字面量和符号引用。符号引用是动态链接的基础 —— 编译时不保存方法的内存地址，只保存全限定名和描述符，等类加载的「解析」阶段再替换为直接引用（内存地址）。

</details>

<details>

<summary>Q3 `int[]` 和 `List<String>` 的描述符分别是什么？</summary>

`int[] → [I`；`List<String> → Ljava/util/List;`。注意泛型被擦除了，描述符里不包含 String，但 Signature 属性里会保留完整的泛型信息。

</details>

<details>

<summary>Q4 new 一个对象对应哪几条字节码指令？</summary>

new → dup → invokespecial → astore。new 只分配内存，invokespecial 才调构造器，dup 是因为构造器会消耗掉栈顶引用。

</details>

<details>

<summary>Q5 五条方法调用指令分别什么时候用？</summary>

invokestatic（静态方法）、invokespecial（构造器/私有方法/父类方法）、invokevirtual（虚方法动态分派）、invokeinterface（接口方法）、invokedynamic（lambda/动态语言）。

</details>

#### 📖 原文

-  —— 本课主源

- 《深入理解 Java 虚拟机（第 3 版）》第 6 章「类文件结构」—— 权威参考

- JVM Spec §4 · The class File Format —— 官方规范

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0035：**类加载过程** —— 加载/验证/准备/解析/初始化，每步干什么？准备阶段和初始化阶段的「赋值」有什么区别？

💬 有任何疑问 —— 「javap 输出看不懂怎么办？」「常量池索引 0 为啥不能用？」「invokedynamic 和 lambda 的关系？」—— 直接问我。


