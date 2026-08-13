> Lesson 0002 · 阶段一 · Java 基础 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 6 道自测

# 0002 · OOP 三大特征 & 接口 vs 抽象类 & Object 方法 & 深浅拷贝

这一课覆盖的全部核心考点。这一篇是 Java 基础三连击（上/中/下）里 **面试频率最高** 的一篇 —— 几乎所有初中级面试都会问：**「接口和抽象类的区别？」「`==` 和 `equals` 的区别？」「重写 `equals` 为什么必须重写 `hashCode`？」「`new String("abc")` 创建了几个对象？」「深拷贝浅拷贝有什么区别？」** —— 一节课打通。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `String s1 = "abc"; String s2 = new String("abc"); s1 == s2` 返回什么？</summary>

`false`。`s1` 指向字符串常量池的 `"abc"`，`s2` 指向堆上新 `new` 出来的 `String` 对象。第 9 题会展开讲字节码级别的分析。

</details>

<details>

<summary>Q0.2 只重写 `equals` 不重写 `hashCode`，把对象放进 `HashMap` 会怎样？</summary>

大概率**存进去找不回来**。`HashMap` 先按 `hashCode` 定位桶，再用 `equals` 比较桶内元素。`hashCode` 没重写就是对象地址哈希，同内容的两个对象落到不同桶 —— 永远查不到。第 7 题细讲。

</details>

## 面试场景 1：面向对象的三大特征是什么？

🎤 面试官

你能简单讲讲面向对象的三大特征吗？重点讲讲多态。

🧑‍💻 你

三大特征是 **封装、继承、多态**：

- **封装**：把对象的属性隐藏起来（`private`），只通过公开方法（`getter`/`setter`）访问。好处是*屏蔽内部实现细节*，外部不能随便改状态。类比：空调的电路板对用户是黑盒，用户只通过遥控器操作。

- **继承**：子类基于父类扩展，复用父类的字段和方法（`private` 除外），并可以增加自己的成员或重写父类方法。Java 单继承，避免菱形问题。

- **多态**：父类引用指向子类对象，**方法调用在运行时才确定实际执行哪个版本** —— 这就是「动态绑定」或「后期绑定」。多态是三大特征里最有威力的一个，Spring 的 `BeanFactory`、JDBC 的 `DriverManager` 全靠它做扩展点。

关于多态，有三条铁律要记住：

1. **只有对象方法（非 `static`、非 `private`、非 `final`）才有多态**。`static` 方法是*静态绑定*，看引用类型不看对象类型。

2. **字段没有多态**。`Parent p = new Child(); p.name` 拿到的是 `Parent` 里的 `name`，字段永远看引用的编译期类型。

3. **多态的前提是继承 + 重写 + 向上转型**。三者缺一不可。

追问 动态绑定在 JVM 里是怎么实现的？

依赖 **方法表（vtable）**。每个类在方法区维护一张方法表，表里存的是虚方法的入口地址。子类重写父类方法后，子类方法表对应槽位会覆盖父类的地址。`invokevirtual` 字节码指令执行时，JVM 从对象头的类型指针找到实际类的方法表，按槽位索引调用 —— 这就是运行时才确定实际方法的机制。`static`/`private`/`final` 方法走 `invokestatic`/`invokespecial`，编译期就把方法地址写死了，所以没有多态。

追问 重载（overload）和重写（override）有什么区别？

**重载**：同一个类内，方法名相同、参数列表不同（个数/类型/顺序）。返回值和访问修饰符不参与重载判定。重载是*编译期*决定调用哪个版本的（静态多态）。**重写**：子类覆盖父类同签名方法，返回值必须相同或是子类型（协变返回），访问修饰符不能更严格，抛出的受检异常不能更宽。重写是*运行时*决定的（动态多态）。

## 面试场景 2：面向对象 vs 面向过程有什么区别？

🎤 面试官

面向对象和面向过程你怎么理解？举个例子。

🧑‍💻 你

核心差异是 **抽象角度**：

- **面向过程（POP）**：把问题拆成一系列*动作/函数*，按步骤调用。C 语言是典型代表。

- **面向对象（OOP）**：先把问题抽象成*对象*（数据 + 行为绑定），再让对象之间协作。Java 是典型代表。

拿「洗衣服」举例：

- 面向过程：`加水() → 放洗衣粉() → 搅动() → 漂洗() → 甩干()`，一串函数依次调用，数据（水量、时间、衣物）在函数间以参数传递。

- 面向对象：`Washer washer = new Washer(); washer.wash(clothes);`。洗衣机*自己知道*怎么加水、怎么甩干，用户只关心「洗」这个语义。**数据和操作被封装到了一起**。

OOP 的三大好处：**易维护**（改内部实现不影响调用方）、**易复用**（继承 + 组合）、**易扩展**（多态 + 接口）。

陷阱 「面向对象一定比面向过程慢」是老掉牙的说法。JIT 现代化后，虚方法调用会做 **去虚化（devirtualization）** 和 **内联**，多数场景性能差异可以忽略。真正性能敏感的场景（如高频数值计算），Java 也可以退化成面向过程写法 —— 一个 `static` 方法直接干。

## 面试场景 3：对象和类是什么关系？`new` 到底做了什么？

🎤 面试官

类和对象是什么关系？`new` 关键字底层做了什么？

🧑‍💻 你

**类是对象的模板，对象是类的实例**。类定义了对象拥有哪些字段和方法，对象是这个模板实例化后的一份具体数据。一个类可以实例化任意多个对象，每个对象有独立的字段值。

引用和对象是*分离*的两个东西：

- 一个**引用**指向 0 或 1 个对象（null 或某个具体对象）。

- 一个**对象**可以被 0 或多个引用指向（无引用时可被 GC）。

`new Foo()` 底层拆解成 5 步：

1. **类加载检查**：类没加载先走类加载器（loading → linking → initializing）。

2. **分配内存**：在堆里划一块对象大小的空间（TLAB 优先、指针碰撞或空闲列表）。

3. **零值初始化**：字段全部置为默认值（`int` 为 0、引用为 null、`boolean` 为 false）。

4. **设置对象头**：写入 Mark Word（哈希、锁标志、GC 分代年龄）+ 类型指针（指向类的元数据）。

5. **执行构造方法**：先递归调用父类构造，再执行本类字段初始化和构造代码块。

字节码上对应两条指令：`new #Foo`（前 4 步，分配对象，栈顶是引用）+ `invokespecial <init>`（第 5 步，执行构造）。

追问 字段初始化、构造代码块、构造方法的执行顺序是什么？

顺序是：**父类静态字段/静态代码块（按代码顺序） → 子类静态字段/静态代码块 → 父类非静态字段/实例代码块 → 父类构造方法 → 子类非静态字段/实例代码块 → 子类构造方法**。注意：静态部分只在类加载时执行*一次*；非静态部分每次 `new` 都会执行。这个顺序是笔试超高频考点。

## 面试场景 4：接口和抽象类有什么区别？★核心

🎤 面试官

接口和抽象类的区别？什么时候用接口，什么时候用抽象类？

🧑‍💻 你

从**设计意图**开始讲，再落到**语法细节**：

- **设计意图**：*抽象类*用于「**is-a**」关系，表达一类事物的共性（`Animal` → `Dog`），侧重代码复用；*接口*用于「**can-do**」关系，表达一种能力/契约（`Runnable`、`Comparable`），侧重行为约束。

- **继承 vs 实现**：一个类只能 `extends` 一个抽象类（单继承），但可以 `implements` 多个接口。接口之间也支持多继承（`interface A extends B, C`）。

- **成员变量**：抽象类可有任意访问级别的字段，可以是实例变量；接口的字段隐式为 `public static final`（常量），必须在声明时初始化。

- **方法实现**：抽象类可以有*抽象方法*也可以有*具体方法*，构造方法也允许（供子类 `super()` 调用）；接口从 Java 8 起可以有 `default` 方法、`static` 方法，Java 9 起可以有 `private` 方法（辅助 default 方法内部复用），但**不能有构造方法**。

- **访问修饰符**：抽象类方法可以是任意访问级别；接口方法默认 `public`（Java 9 起 `private` 也允许，但只服务接口内部）。

选择原则：**优先用接口**。除非确实需要在多个子类之间共享*状态或部分实现*，才用抽象类。Spring 里几乎所有扩展点都是接口 + 默认实现类的模式（如 `ApplicationContext`）。

追问 Java 8 之后接口能有 `default` 方法了，那接口和抽象类还有什么本质区别？

三点本质区别仍然存在：**（1）字段**：接口字段永远是 `public static final` 常量，不能有实例状态；抽象类可以持有实例字段。**（2）构造方法**：接口没有构造方法，抽象类可以有（子类会走 `super()`）。**（3）多继承**：一个类实现多接口不冲突，继承多个抽象类不允许。`default` 方法只是给接口一个「*不破坏已有实现类*」的演进能力（比如 `List` 加了 `stream()`），并不是把接口变成抽象类。

追问 如果一个类实现的两个接口有同名 `default` 方法怎么办？

编译报错：**The default method 'xxx' is inherited from types A and B**。必须在实现类里显式重写这个方法，可以用 `接口名.super.方法名()` 指定调用哪个接口的默认实现。这就是「菱形问题」的 Java 版解法 —— 强制程序员消歧。

陷阱 接口的字段是 `public static final`，这意味着 `interface Foo { int X = 1; }` 里的 `X` 不是「接口的实例字段」而是**常量**。子类实现接口后拿到的 `X` 是共享的、不可变的。别在接口里定义「状态」—— 编译器会拒绝，或者你只是在定义常量表。

## 面试场景 5：构造方法有哪些特点？能被继承吗？能被重写吗？

🎤 面试官

构造方法有什么特点？能被重写吗？能被继承吗？能加 `static` 吗？

🧑‍💻 你

构造方法的关键点：

- **名字必须和类名相同**，没有返回值声明（不是 `void`，是*压根没有*返回类型这一栏）。

- **不能被 `override`（重写），但可以 `overload`（重载）**。重写要求子类和父类方法签名一致，而构造方法名跟类名绑死 —— 子类和父类类名不同，天然不可能重写。

- **不能被子类继承**。子类只能通过 `super(...)` *调用*父类构造，不能*拥有*父类构造。

- **不能加 `static`**。构造方法是用来初始化*实例*的，`static` 意味着不需要实例 —— 语义冲突。

- **不能加 `abstract`、`final`、`synchronized`**。`abstract` 意思是无实现让子类实现，构造方法必须有实现；`final` 意思是不能被重写，构造方法本来就不能重写；`synchronized` 无意义（对象都还没构造完谁能拿到锁）。

- **隐式 `super()`**：如果构造方法首行没写 `this(...)` 也没写 `super(...)`，编译器会自动插入 `super()` 调用父类无参构造。所以父类如果只有带参构造，子类必须显式 `super(参数)`，否则编译失败。

- **没写构造 = 编译器送一个默认无参构造**；一旦你写了任意构造方法，默认无参构造就不再自动生成。

追问 什么场景下会把构造方法声明为 `private`？

三大典型场景：**（1）单例模式**：`private` 构造禁止外部 `new`，只暴露 `getInstance()`。**（2）工具类**：`Math`、`Collections` 这类全 `static` 方法的类，用 `private` 构造防止实例化。**（3）Builder / 静态工厂**：只允许通过 `Foo.of(...)` 或 `Foo.newBuilder()` 创建，隐藏 `new` 细节，方便未来切换实现或缓存对象（例：`Integer.valueOf(int)`）。

## 面试场景 6：`==` 和 `equals()` 的区别？★核心

🎤 面试官

`==` 和 `equals()` 的区别？`String` 有什么特殊性？

🧑‍💻 你

核心区别：

- **`==` 是运算符**：基本类型比较*值*；引用类型比较*引用地址*（即是否指向同一个对象）。

- **`equals()` 是 `Object` 的方法**：默认实现就是 `return this == obj`，等同于 `==`；但 `String`、`Integer`、`Date` 等类都*重写*了它，改成按**内容/值**比较。

用 `String` 举例最清楚：

```
String s1 = "hello";                 // 常量池对象
String s2 = "hello";                 // 复用同一常量池对象
String s3 = new String("hello");     // 堆上新对象

s1 == s2         // true  ← 常量池引用相同
s1 == s3         // false ← 堆对象 vs 常量池对象，地址不同
s1.equals(s3)    // true  ← String 重写 equals 按内容比
```

规则总结：**比较基本类型用 `==`；比较引用类型内容用 `equals()`；比较引用是否指同一对象才用 `==`**。

追问 `Object` 的 `equals()` 源码长什么样？

就一行：

```
public boolean equals(Object obj) {
return (this == obj);
}
```

所以任何类**不重写** `equals` 就等同于 `==` —— 引用比较。重写规范由 JLS 定义（`Object#equals` Javadoc），要满足**自反、对称、传递、一致、非 null** 五个契约。

追问 `String` 的 `equals` 是怎么实现的？

大致逻辑（简化）：先判 `this == obj` 快速返回 true；再判 `obj instanceof String`；然后按 `value` 数组逐字符比较（Java 9+ 里 `value` 是 `byte[]`，还要按编码 Latin-1/UTF-16 分支）。**关键点**：`String.equals` 内部依赖的是*不可变的字符数组*，所以两个内容相同的 `String` 一定 equals。

陷阱 `"abc".equals(someString)` 比 `someString.equals("abc")` 更安全 —— 前者永远不会 NPE，后者当 `someString` 为 `null` 时抛 NPE。这就是所谓的「**常量在前的 equals 写法**」，代码 review 里经常被要求。

## 面试场景 7：`hashCode()` 和 `equals()` 什么关系？★核心

🎤 面试官

为什么重写 `equals()` 必须重写 `hashCode()`？如果不重写会怎样？

🧑‍💻 你

先讲两个方法的**契约**（`Object` Javadoc 明确规定）：

1. `a.equals(b) == true` ⟹ `a.hashCode() == b.hashCode()`（**equal 必等哈希**）

2. `a.hashCode() == b.hashCode()` ⇏ `a.equals(b) == true`（哈希相同不代表相等，因为存在**哈希碰撞**）

3. `a.hashCode() != b.hashCode()` ⟹ `a.equals(b) == false`（哈希不同必然不等）

为什么必须同时重写？—— **因为 `HashMap`、`HashSet` 依赖这个契约做查找**。`HashMap.get(key)` 的算法：

1. 算 `key.hashCode()`，扰动后按数组长度取模，找到桶索引。

2. 遍历这个桶（链表或红黑树），用 `equals()` 逐个比对。

如果重写了 `equals`（比如按业务字段判等）但没重写 `hashCode`：两个*业务上相等*的对象哈希值不同 → 落到不同桶 → `get()` 永远找不回来。你 `put(user1, "A")`，再用 `new User(same fields)` `get`，返回 `null`。这是**最经典的 HashMap bug**。

追问 为什么 `hashCode` 相等两个对象 `equals` 不一定相等？

因为 `hashCode` 返回 `int`（40 亿种可能），但对象空间无限大 —— 必然有**多个不同对象哈希到同一个值**，这就是*哈希碰撞*。`HashMap` 用链表/红黑树处理碰撞，桶里可能有多个哈希相同但内容不同的对象，所以还要用 `equals` 精确比对。反过来：`equals` 相等 *必* `hashCode` 相等 —— 这是契约，重写时你必须保证。

追问 `Object.hashCode()` 默认实现是啥？和内存地址有关吗？

规范只要求「相同对象多次调用返回相同值」，没规定必须基于地址。**HotSpot** 默认实现是「*基于随机数的一次性生成*」：第一次调用时算出 hash 存进对象头 `Mark Word`，后续直接返回。所以既不是地址、也不是内容 —— 而是每个对象生成时的一个随机值。你可以用 `-XX:hashCode` 参数切换生成算法。

陷阱 别把可变字段放进 `hashCode`。举例：`User { id, name }` 只用 `id` 算 hash 安全；如果用 `name`，那对象放进 `HashSet` 后修改 `name` —— 哈希值变了，`contains()` 直接找不到自己。这就是**「Set 里的对象 mutability」陷阱**。工业实践：`hashCode`/`equals` 只用*不可变的业务主键*。

## 面试场景 8：`String`、`StringBuilder`、`StringBuffer` 的区别？

🎤 面试官

这三个类都用来搞字符串，区别是什么？

🧑‍💻 你

维度`String``StringBuffer``StringBuilder`

可变性不可变（`final` 字段 `value`）可变可变
线程安全安全（不可变天然安全）安全（方法加 `synchronized`）不安全
性能差（修改就 new）中（同步开销）好（无锁）
诞生版本JDK 1.0JDK 1.0JDK 1.5（补 `StringBuffer` 性能坑）
使用场景少量、只读、共享字符串多线程可变字符串（很少见）单线程可变字符串（默认选它）

三个类都继承 `AbstractStringBuilder`（`String` 除外），底层都是*字符数组*。Java 9 起 `String` 底层从 `char[]` 改为 `byte[]` + 编码标志（Latin-1 或 UTF-16），叫 **Compact Strings**，纯 ASCII 字符串内存直接减半。

**选择原则**：单线程拼字符串永远 `StringBuilder`；`StringBuffer` 基本不用（多线程共享字符串一般走别的同步机制）；短字符串或字面量直接 `String`，简洁。

追问 `String` 为什么设计成不可变？

四大原因：**（1）字符串常量池**：不可变才能安全共享，否则一个引用改字符串会影响所有引用。**（2）`hashCode` 缓存**：`String` 内部缓存了 `hashCode`，不可变意味着 hash 算一次终身有效 —— `HashMap` 用 `String` 做 key 极快。**（3）线程安全**：不可变对象跨线程共享无需同步。**（4）安全性**：文件路径、数据库连接串、类名等被作为 `String` 传递，如果可变会引入 TOCTOU（time-of-check to time-of-use）攻击面。

追问 `String s = "a" + "b" + "c"` 编译后是什么？和 `String s = a + b + c`（变量）有什么不同？

**常量拼接**会被编译器做*常量折叠*：`"a" + "b" + "c"` 直接变成常量池里的 `"abc"`，字节码里就是 `ldc "abc"` 一条指令。**变量拼接**就不能折叠了，编译器会把它翻成 `new StringBuilder().append(a).append(b).append(c).toString()`。*坑点*：在循环里 `s += x` 每次循环都会 `new StringBuilder()`，性能极差 —— 必须自己在循环外 `new` 一个 `StringBuilder`。此外，`final String` 变量视同常量，也能参与折叠。

## 面试场景 9：字符串常量池 & `new String("abc")` 创建几个对象？★经典陷阱

🎤 面试官

`String s = new String("abc")` 这一行代码创建了几个对象？`intern()` 又是干什么的？

🧑‍💻 你

先讲**字符串常量池**：JVM 专门维护的一块区域（HotSpot 里在堆里，Java 7 之前在方法区），存放*字符串字面量*，实现字符串共享，避免重复创建。`String s = "abc"` 就是从常量池拿引用；`String s = "abc"; String t = "abc";` 两者 `s == t` 为 `true`。

回到问题：**`new String("abc")` 创建 1 或 2 个对象**：

- 如果常量池里*还没有* `"abc"`：**2 个** —— 常量池创建一个（编译期就把 `"abc"` 字面量登记进常量池，运行到 `ldc` 指令时确保存在），堆上 `new` 一个。

- 如果常量池里*已有* `"abc"`：**1 个** —— 只在堆上 `new` 一个，常量池那个不重复创建。

字节码验证：

```
0: new           #2   // class java/lang/String   ← 堆上分配空 String
3: dup
4: ldc           #3   // String "abc"             ← 从常量池拿"abc"引用
6: invokespecial #4   // Method <init>(Ljava/lang/String;)V  ← 用"abc"初始化堆对象
9: astore_1
```

**`intern()`**：把当前 `String` 对象*登记到常量池*并返回常量池里的引用：

- 常量池已有相同内容 → 返回*池里那个*的引用。

- 常量池没有 → 把当前对象引用*放进池*（Java 7+ 不复制，直接存堆引用），再返回。

```
String a = new String("hello");
String b = a.intern();
String c = "hello";
System.out.println(a == b);  // false ← a 在堆，b 在常量池
System.out.println(b == c);  // true  ← 都指向常量池同一对象
```

追问 `String.intern()` 在 Java 6 和 Java 7+ 有什么区别？

**Java 6**：字符串常量池在*方法区（PermGen）*，`intern()` 是把字符串**复制**到常量池，返回复制品引用。**Java 7+**：常量池搬到*堆*里（跟随 PermGen → Metaspace 改造），`intern()` 不再复制 —— 如果常量池里没有，直接把*堆里当前对象的引用*登记进池。所以 Java 7 之后：`String s = new StringBuilder("hello").toString(); s.intern() == s` 可能是 `true`（只要 `"hello"` 之前没进过常量池）。这是 R 大和周志明《深入理解 Java 虚拟机》里的经典案例。

陷阱 别滥用 `intern()`。它会把字符串放进 JVM 全局常量池 —— 生命周期极长（几乎和 JVM 同寿）。高并发下把用户输入的字符串（比如日志、请求参数）都 `intern()`，会撑爆常量池，OOM 风险极高。`intern()` 只在*枚举一小组固定字符串*（如状态码、类型标识）时才值得用。

## 面试场景 10：深拷贝、浅拷贝、引用拷贝有什么区别？

🎤 面试官

深拷贝、浅拷贝、引用拷贝分别是什么？`Object.clone()` 是哪种？

🧑‍💻 你

三个概念的关键区分：

- **引用拷贝**：`Foo a = new Foo(); Foo b = a;` —— 只是让两个引用指向*同一个对象*，堆上还是 1 个对象。*本质上不是「拷贝」，是别名*。

- **浅拷贝**：在堆上*创建新对象*，但对象内部的**引用类型字段**依然指向原来的对象。`Object.clone()` 默认就是浅拷贝。

- **深拷贝**：新对象及其*所有引用字段递归*都是新对象。改一个不影响另一个。

拿 `Person(Address addr)` 举例：

```
Person p1 = new Person(new Address("武汉"));
Person p2 = p1.clone();                 // 浅拷贝
p1 == p2                                // false ← 是新对象
p1.getAddress() == p2.getAddress()      // true  ← 内部 Address 共享（浅）
p2.getAddress().setCity("北京");         // p1.getAddress().getCity() 也变了！
```

深拷贝要手动递归：

```
@Override
public Person clone() throws CloneNotSupportedException {
Person p = (Person) super.clone();
p.address = this.address.clone();   // 递归 clone 内部引用
return p;
}
```

实现深拷贝的常见姿势：**（1）手写递归 `clone`**（复杂对象容易漏字段）；**（2）序列化再反序列化**（Java 原生序列化 / JSON / protobuf，简单但慢）；**（3）拷贝构造器 / 静态工厂方法**（*Effective Java* 推荐，比 `Cloneable` 干净）。

追问 `Cloneable` 接口是什么鬼？为什么它是空接口？

`Cloneable` 是一个**标记接口**（marker interface），里面没有方法，只是给 `Object.clone()` 一个「你允许被 clone」的许可 —— 没实现 `Cloneable` 而调 `clone()` 会抛 `CloneNotSupportedException`。*Joshua Bloch* 在 Effective Java 里明确批评过这个设计：「接口不定义方法却影响父类方法行为」违反接口契约。而且 `clone()` 语义模糊（浅/深不清楚）、异常声明奇怪。工业实践：**不要用 `Cloneable`，用拷贝构造器或静态工厂方法替代**。

追问 深拷贝用 `Cloneable + super.clone()` 有什么坑？

四个大坑：**（1）`final` 字段无法在 `clone()` 里重新赋值** —— 因为 `super.clone()` 已经把 `final` 字段浅拷贝了，你再改会编译报错。**（2）构造方法不会被调用**：`clone()` 绕过构造方法，靠 JVM 直接分配 + 内存拷贝，如果构造方法里有校验/注册逻辑，深拷贝出的对象没走这段。**（3）递归 clone 容易漏字段**：新加了字段忘了 clone，浅拷贝陷阱悄悄回归。**（4）循环引用**：`A.b = B; B.a = A;` 深拷贝会无限递归。序列化方式有对象 ID 表可以处理，手写 `clone` 处理不了。所以推荐用 **拷贝构造器** 或 **Jackson/Gson 反序列化** 做深拷贝。

陷阱 `ArrayList.clone()` 是**浅拷贝**：新 `ArrayList`，但内部元素是共享引用。`List<User> b = (List) ((ArrayList) a).clone();` 之后修改 `b.get(0).setName(...)`，`a.get(0)` 的 name 也变了。想深拷贝 `List`，得手动 `stream().map(User::copy).toList()`。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：多态的动态绑定 + 字段没有多态

```
class Animal {
String name = "animal";
String speak() { return "animal sound"; }
static String kind() { return "Animal.kind"; }
}
class Dog extends Animal {
String name = "dog";
@Override String speak() { return "wang wang"; }
static String kind() { return "Dog.kind"; }
}
public class PolyDemo {
public static void main(String[] args) {
Animal a = new Dog();
System.out.println(a.speak());   // wang wang     ← 方法有多态（动态绑定）
System.out.println(a.name);      // animal        ← 字段没有多态（静态绑定）
System.out.println(a.kind());    // Animal.kind   ← static 方法没有多态
}
}
```

### 验证 2：`equals` 和 `hashCode` 的 `HashMap` 陷阱

```
import java.util.HashMap;
import java.util.Objects;

class User {
String id;
User(String id) { this.id = id; }
@Override public boolean equals(Object o) {
if (!(o instanceof User)) return false;
return Objects.equals(id, ((User) o).id);
}
// ❌ 故意不重写 hashCode()
}

public class HashMapBug {
public static void main(String[] args) {
HashMap<User, String> map = new HashMap<>();
map.put(new User("u1"), "Alice");
String v = map.get(new User("u1"));
System.out.println(v);   // null !!! 明明 put 进去了却找不到
}
}
// 修复：加上
// @Override public int hashCode() { return Objects.hash(id); }
```

### 验证 3：`new String("abc")` 创建了几个对象

```
public class StringPool {
public static void main(String[] args) {
String s1 = "abc";                   // 常量池
String s2 = new String("abc");       // 堆
String s3 = s2.intern();             // 返回常量池那个

System.out.println(s1 == s2);        // false
System.out.println(s1 == s3);        // true
System.out.println(s2 == s3);        // false
System.out.println(s1.equals(s2));   // true
}
}
// javap -c StringPool 观察字节码：
//   ldc "abc"       ← s1 直接取常量池
//   new String; dup; ldc "abc"; invokespecial <init>  ← s2 是堆对象
```

### 验证 4：`String` 拼接 —— 常量折叠 vs `StringBuilder`

```
public class Concat {
public static void main(String[] args) {
String a = "he" + "llo";             // 编译期折叠成 "hello"
String b = "hello";
System.out.println(a == b);          // true ← 折叠后同一个常量池对象

String x = "he";
String y = x + "llo";                // 运行期拼，new StringBuilder().append(x).append("llo")
System.out.println(y == b);          // false

final String x2 = "he";              // final 视同常量
String y2 = x2 + "llo";              // 编译期折叠
System.out.println(y2 == b);         // true
}
}
// 用 javap -c 看会更清楚：y 那行会有 new StringBuilder / invokevirtual append 调用
```

### 验证 5：浅拷贝的坑

```
class Address implements Cloneable {
String city;
Address(String c) { this.city = c; }
@Override protected Address clone() throws CloneNotSupportedException {
return (Address) super.clone();
}
}
class Person implements Cloneable {
String name;
Address address;
Person(String n, Address a) { this.name = n; this.address = a; }

// 浅拷贝
@Override protected Person clone() throws CloneNotSupportedException {
return (Person) super.clone();
}
// 深拷贝：解开注释即可
// @Override protected Person clone() throws CloneNotSupportedException {
//     Person p = (Person) super.clone();
//     p.address = this.address.clone();
//     return p;
// }
}
public class CloneDemo {
public static void main(String[] args) throws Exception {
Person p1 = new Person("Tom", new Address("Wuhan"));
Person p2 = p1.clone();
System.out.println(p1 == p2);                        // false
System.out.println(p1.address == p2.address);        // true  ← 浅拷贝共享 Address
p2.address.city = "Beijing";
System.out.println(p1.address.city);                 // Beijing !! 原对象被改了
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 面向对象三大特征是什么？多态的三个前提是什么？</summary>

封装、继承、多态。多态三前提：**继承 + 重写 + 向上转型**。三者缺一不可，且只对实例方法生效，字段和 `static` 方法没有多态。

</details>

<details>

<summary>Q2 用一段话总结接口和抽象类的核心区别。</summary>

抽象类表达 is-a 关系、单继承、可含实例字段和构造方法；接口表达 can-do 契约、多实现、字段隐式 `public static final`、无构造方法。Java 8 后接口可有 `default`/`static` 方法，Java 9 后可有 `private` 方法，但接口**永远没有实例状态**。默认选接口，需要共享部分实现或状态时才用抽象类。

</details>

<details>

<summary>Q3 重写 `equals` 不重写 `hashCode` 会导致什么？为什么？</summary>

对象放进 `HashMap`/`HashSet` 会找不到自己。因为哈希容器先按 `hashCode` 定位桶，再用 `equals` 精确比对。两个 `equals` 相等的对象若 `hashCode` 不同（默认基于对象生成时的随机值），会落到不同桶 —— `get`/`contains` 永远返回 null/false。

</details>

<details>

<summary>Q4 `String s = new String("abc")` 创建了几个对象？给出两种情况。</summary>

1 或 2 个：常量池已有 `"abc"` 则堆里只新建 1 个；常量池没有 `"abc"` 则常量池新建 1 个 + 堆新建 1 个，共 2 个。字节码上是 `new String / ldc "abc" / invokespecial <init>` 三条指令。

</details>

<details>

<summary>Q5 `String`、`StringBuilder`、`StringBuffer` 的选择原则？为什么 `String` 不可变？</summary>

单线程拼字符串用 `StringBuilder`；多线程可变字符串（很少见）用 `StringBuffer`；短字符串/字面量用 `String`。`String` 不可变的四大原因：字符串常量池共享安全、`hashCode` 缓存高效、天然线程安全、安全性（防路径/类名被恶意修改）。

</details>

<details>

<summary>Q6 深拷贝、浅拷贝、引用拷贝的区别？`Object.clone()` 是哪种？</summary>

引用拷贝：两个引用指同一对象（不是真拷贝）。浅拷贝：新对象，但内部引用字段共享。深拷贝：新对象 + 所有引用字段递归都是新对象。`Object.clone()` 默认是**浅拷贝**，要深拷贝得手动递归 `clone`，或用序列化/拷贝构造器。工业实践优先用拷贝构造器，避开 `Cloneable` 的设计缺陷。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JLS §8 · Classes —— 类、字段、方法、构造方法的官方规范

- JLS §9 · Interfaces —— 接口、default 方法、marker 接口的官方规范

- `Object#equals` Javadoc —— equals 五大契约的原文

- `String#intern` Javadoc —— intern 语义规范

#### 🔗 关联课件

-  —— 上一课

-  —— 下一课

-  —— 深拷贝在金额场景的应用

-  —— `equals`/`hashCode` 契约在容器里的完整落地

#### 🧭 下一课预告

Lesson 0003：**泛型、反射、异常体系** —— 面试从「基础」进阶到「机制」的关键一跳。泛型擦除、反射三巨头、受检 vs 非受检异常，一次讲透。

💬 有任何疑问 ——「接口 default 方法冲突到底怎么手动消歧？」「`String.intern()` 在 Java 6 和 7 之后到底差在哪？」「`Cloneable` 为啥被 Joshua Bloch 骂？」—— 直接问我。我是你的老师，也是你的追问陪练。


