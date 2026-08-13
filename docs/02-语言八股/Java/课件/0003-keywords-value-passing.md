> Lesson 0003 · 阶段一 · Java 基础 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0003 · Java 关键字总结 & 值传递详解

这一课把  的两篇高频文章合并成一课：和。前半段扫清 `final`/`static`/`this`/`super`/`volatile`/`transient` 等关键字的常考语义；后半段用「三段论」彻底讲清面试官最爱问的一道题 —— **「Java 到底是值传递还是引用传递？」** 这道题几乎是每场 Java 面试的必考题，答不清楚会被直接判定为「基础不牢」。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `final int[] arr = {1, 2, 3}; arr[0] = 99;` 能编译通过吗？运行会怎样？</summary>

能编译通过，运行也没问题，`arr[0]` 会变成 `99`。**`final` 修饰引用类型，锁的是「引用不能重新指向别的对象」，不是「对象内容不能改」**。第 1 题会展开。

</details>

<details>

<summary>Q0.2 方法里写 `obj = new Foo()`，外部传进来的那个 `obj` 会变吗？</summary>

**不会变**。因为 Java 只有值传递，形参 `obj` 只是外部引用值的*副本*，副本重新指向新对象，跟外部的引用没关系。第 8-9 题是本课核心。

</details>

## 面试场景 1：final 关键字的三种用法

🎤 面试官

`final` 关键字有几种用法？分别是什么语义？

🧑‍💻 你

`final` 意思是「最终的、不可修改的」，主要有三种用法：

- **修饰类**：该类不能被继承，所有成员方法隐式为 `final`。典型例子是 `java.lang.String`、`Integer` 等包装类。

- **修饰方法**：该方法不能被子类重写（override）。目的是防止子类改变方法的语义。

- **修饰变量**：只能赋值一次。

- 修饰*基本类型*：值不可改，例如 `final int MAX = 100;`。

- 修饰*引用类型*：**引用不能指向别的对象，但对象内部字段可以改**。例如 `final List<Integer> list = new ArrayList<>(); list.add(1);` 完全合法，但 `list = new LinkedList<>();` 编译报错。

追问 `final` 变量、常量、immutable 对象有什么区别？

三者是不同层次的概念：**`final` 变量**只保证「引用不能改指向」；**常量**通常指 `public static final` 修饰的编译期字面量（例如 `Integer.MAX_VALUE`），会被编译器直接内联到调用处；**immutable（不可变）对象**是一种设计模式，要求对象一旦构造完成，所有字段（包括嵌套对象）都不能被修改，典型代表是 `String`、`Integer`、`LocalDateTime`。要做到真正 immutable，除了字段 `final`，还要防御性拷贝、类本身也 `final`（防子类破坏）。

追问 `final` 修饰方法参数是什么效果？

只表示**方法内部不能给这个参数变量重新赋值**，不影响调用方，也不影响对象内部字段是否可改。例如 `void f(final List l) { l.add(1); }` 合法，但 `l = null;` 编译报错。这个用法在 Lambda / 匿名内部类里曾经很重要（JDK 8 前要求捕获的局部变量必须 `final`），JDK 8 之后放宽成「effectively final」（事实 final），显式写 `final` 只是习惯。

## 面试场景 2：static 关键字的四种用法

🎤 面试官

`static` 关键字有哪些使用场景？

🧑‍💻 你

四种典型场景：

1. **静态成员变量 / 静态方法**：属于类而不是对象，被*所有实例共享*。调用方式 `类名.成员`，无需 `new`。

2. **静态代码块**：定义在类中方法外，**类加载时执行一次**，多个静态块按文本顺序执行。常用于加载配置、初始化连接池、注册驱动。

3. **静态内部类**：与外围类同级，不持有外围类实例的隐式引用；不能访问外围类的非 `static` 成员。典型应用是「静态内部类单例」实现懒加载 + 线程安全。

4. **静态导包**：`import static java.lang.Math.*;`，之后可直接写 `sqrt(2)` 而不用 `Math.sqrt(2)`。

初始化顺序（易考）：**父类静态块 → 子类静态块 → 父类非静态块 → 父类构造 → 子类非静态块 → 子类构造**。静态部分只在类加载时执行一次。

追问 静态变量存在哪个内存区域？JDK 7 前后有什么变化？

**JDK 7 之前**：静态变量存在*方法区*（HotSpot 用「永久代 PermGen」实现）。**JDK 7**：静态变量从永久代*移到 Java 堆*（Class 对象里），字符串常量池也一并迁移。**JDK 8**：永久代被*元空间 Metaspace*（本地内存）替代，但静态变量依然在 Java 堆里，元空间只放类元数据（Class 结构、方法字节码等）。所以标准答案：JDK 7 起静态变量在堆，跟着 Class 对象走。

追问 为什么静态方法不能访问非静态成员？

因为**静态方法属于类，非静态成员属于对象**。静态方法可以在*没有任何对象实例*的情况下被调用（`类名.方法名()`），此时非静态成员根本不存在（还没 `new`），自然无法访问。反之，非静态方法可以访问静态成员，因为「有对象」意味着「类已经被加载了」，静态成员一定已经初始化好了。

陷阱 静态代码块里可以对*其后声明*的静态变量赋值，但**不能读取**（会编译报错「Illegal forward reference」）。例如 `static { x = 1; System.out.println(x); } static int x;` —— 赋值 OK，打印那行编译不过。

## 面试场景 3：this 和 super 的调用规则

🎤 面试官

`this()` 和 `super()` 在构造器里有什么调用规则？

🧑‍💻 你

- `this` 引用**当前对象实例**，可以访问实例变量、调用实例方法。写不写都行，但显式写更清晰（尤其字段名和参数名冲突时必须写，例如 `this.name = name;`）。

- `super` 引用**父类的成员**，用来访问父类的字段、调用父类的方法、调用父类的构造器。

- 在构造器里调用 `this(...)`（调用本类其他构造器）或 `super(...)`（调用父类构造器），**必须是构造器的第一行语句**。

- 这两者**不能同时出现**在同一个构造器的首行（要么调本类，要么调父类）。

- 如果一个构造器*没有显式写* `this()` 或 `super()`，编译器会自动插入 `super()`（调用父类无参构造器）；如果父类没有无参构造器，编译报错。

- **`this` 和 `super` 都不能用在 `static` 方法中**：静态上下文没有「当前实例」也没有「父类实例」的概念。

追问 为什么 `super()` / `this()` 必须写在构造器第一行？

为了保证**对象初始化的严格顺序**：必须先把父类部分构造完（继承的字段先初始化），才能构造子类部分。如果允许在中间调用，就可能出现「使用还没初始化的字段」的悬空引用。同理 `this()` 也必须首行，避免同一个对象被初始化两次。JDK 22 起有个预览特性放宽了这一限制（JEP 447 Statements before super），允许在 `super()` 前做一些参数校验，但主流版本依然按老规则考。

## 面试场景 4：访问修饰符 public/protected/default/private

🧑‍💻 你

Java 的访问修饰符从宽到严有四级，作用范围如下：

修饰符本类同包子类（跨包）任意包典型用法

`public`✅✅✅✅对外 API、Service 接口
`protected`✅✅✅❌希望被子类扩展的字段/方法
`default`（不写）✅✅❌❌包内工具类、内部实现
`private`✅❌❌❌字段封装、内部辅助方法

追问 `protected` 和 `default` 最容易混。它俩的区别到底在哪？

**关键区别在「跨包子类」**。`default`（包访问级别）只允许同一个包内的类访问，跨包了子类也没辙；`protected` 除了同包外，*额外允许跨包的子类*访问（且只能通过子类自身的引用访问，不能通过父类引用直接访问其他实例的 protected 成员 —— 这条细节很少被问但确实存在）。

追问 顶级类（外层类）能用 `private` 或 `protected` 修饰吗？

**不能**。顶级类只允许 `public` 或 `default`（不写修饰符）。`private` / `protected` 只能修饰*成员*（字段、方法、内部类）。原因很直观：`private` 顶级类没人能访问它，毫无意义；`protected` 顶级类没有「子类作用域」可言。

## 面试场景 5：volatile 关键字（可见性 + 禁重排）

🎤 面试官

`volatile` 关键字有什么作用？能保证原子性吗？

🧑‍💻 你

`volatile` 修饰变量后，提供两个语义保证：

1. **可见性**：一个线程修改 `volatile` 变量后，其他线程能*立即看到*最新值。底层通过缓存一致性协议（如 MESI）+ 内存屏障实现：写后强制刷回主存 + 使其他 CPU 的缓存行失效，读前从主存重新加载。

2. **禁止指令重排**：JIT 和 CPU 都可能对指令重排以优化性能，`volatile` 会插入*内存屏障*禁止跨越屏障的重排。经典应用是**双重检查锁定（DCL）单例**里 `private volatile static Singleton instance;` —— 防止 `new Singleton()` 的三步操作（分配内存 / 初始化对象 / 引用指向）被重排。

**`volatile` 不保证原子性**。因为它只解决「读到最新值」的问题，不解决「读+改+写」是否会被打断的问题。所以 `volatile int i;` 上做 `i++` 在多线程下依然会丢更新。

追问 `volatile` 为什么保证不了 `i++` 的原子性？

因为 `i++` 编译后是**三条字节码**：`getfield`（读 i）→ `iadd`（加 1）→ `putfield`（写回）。`volatile` 只能保证每一步单独的读/写从/到主存，但两个线程可能同时读到同一个旧值 `i=5`，各自 +1 变成 6，再各自写回，结果本应是 7 却变成 6。要原子性得用 `synchronized`、`AtomicInteger`（CAS）或 `LongAdder`。

追问 `volatile` 和 `synchronized` 有什么区别？

**粒度**：`volatile` 只修饰变量，`synchronized` 修饰代码块/方法。**能力**：`volatile` 只保证可见性 + 有序性；`synchronized` 三者全包（可见性 + 有序性 + 原子性）。**开销**：`volatile` 是「无锁」内存屏障，代价小；`synchronized` 是重量级锁（虽有偏向锁/轻量级锁优化），代价大。**阻塞**：`volatile` 不阻塞线程；`synchronized` 会阻塞。选择原则：只需要可见性就 `volatile`，需要原子操作就 `synchronized` 或 `Atomic*`。

## 面试场景 6：synchronized 关键字（简要覆盖）

🧑‍💻 你

`synchronized` 用于实现**同步方法或同步代码块**，保证同一时刻只有一个线程能进入被保护的临界区。三种典型用法：

- **修饰实例方法**：锁的是*当前实例*（`this`）。

- **修饰静态方法**：锁的是*当前类的 Class 对象*（全局唯一）。

- **修饰代码块**：`synchronized(obj) { ... }`，锁的是括号里指定的对象。

JDK 6 起 HotSpot 对 `synchronized` 做了大量优化：**偏向锁 → 轻量级锁 → 重量级锁** 的锁升级路径。JDK 15 起偏向锁被默认关闭并逐步废弃（JEP 374）。深入细节留到并发章节（Lesson 0043 附近）细讲。

陷阱 `synchronized(String)` 或 `synchronized(Integer)` 是常见坑：字符串会命中常量池、包装类会命中缓存池，多个不相关的代码可能锁到同一个对象，出现意外阻塞或死锁。**永远用 `private final Object lock = new Object();` 作为专用锁对象**。

## 面试场景 7：transient —— 序列化时忽略字段

🎤 面试官

`transient` 关键字有什么用？

🧑‍💻 你

`transient` 修饰的字段，在**对象序列化时会被跳过**，反序列化后该字段恢复为对应类型的默认值（引用类型是 `null`，`int` 是 `0`，`boolean` 是 `false`）。典型使用场景：

- **敏感信息**：密码、token、私钥不应被序列化到磁盘或网络。

- **可推导字段**：能从别的字段算出来的缓存值，没必要占带宽存储。

- **不可序列化的字段**：例如 `Thread`、`Socket`、`InputStream`，本身没实现 `Serializable`，如果不加 `transient` 会抛 `NotSerializableException`。

`static` 字段本身就不参与序列化（属于类而非对象），无需再加 `transient`。

追问 `transient` 只对 Java 原生序列化有效吗？

**是的，只对 `java.io.Serializable` 机制生效**。JSON 序列化（Jackson / Gson / Fastjson）不认 `transient`，它们各有自己的忽略注解 —— Jackson 用 `@JsonIgnore`，Gson 用 `transient`（巧合，Gson 恰好支持）或 `@Expose`，Fastjson 用 `@JSONField(serialize=false)`。Redis 存储用的 Kryo、Protostuff 也各有各的规则。

## 面试场景 8：Java 是值传递还是引用传递？ ⭐极高频

🎤 面试官

Java 是值传递还是引用传递？请举例说明。

🧑‍💻 你

**Java 只有值传递，没有引用传递。** 我用三段论证明：

**先明确定义**：

- **值传递**：方法接收的是实参值的*拷贝*（副本），修改副本不影响原件。

- **引用传递**：方法接收的是实参本身的*地址*（别名），修改形参就是修改原变量。

**场景一：传基本类型**

```
public static void swap(int a, int b) {
int temp = a; a = b; b = temp;
}
int num1 = 10, num2 = 20;
swap(num1, num2);
// num1 依然是 10，num2 依然是 20 —— 副本被修改，原件不动
```

**场景二：传对象引用（修改字段）**

```
public static void change(int[] array) {
array[0] = 0;
}
int[] arr = {1, 2, 3};
change(arr);
// arr[0] 变成了 0 —— 因为形参 array 和实参 arr 保存的是同一个引用值副本，
// 都指向同一个堆上的数组对象，通过副本能操作到同一份数据
```

**场景三：传对象引用（重新赋值 / swap）**

```
public static void swap(Person p1, Person p2) {
Person temp = p1; p1 = p2; p2 = temp;
}
Person xiaoZhang = new Person("小张");
Person xiaoLi = new Person("小李");
swap(xiaoZhang, xiaoLi);
// xiaoZhang 依然是「小张」，xiaoLi 依然是「小李」
// 因为交换的只是形参 p1、p2 保存的「引用副本」，没动到外部变量的引用
```

三个场景一起看就能定论：Java 传的永远是「实参存的那个值」的拷贝 —— 基本类型拷字面量，引用类型拷引用值（也就是那个「指向堆对象的地址」）。这就叫值传递。

追问 场景二里明明能改到外部数组，为什么还叫值传递？

关键要区分「**改对象内容**」和「**改引用指向**」。场景二里我们改的是*对象内部的字段*（`array[0] = 0`），此时形参 `array` 和实参 `arr` 虽然是两个不同的变量，但它们保存的引用值指向同一个堆对象 —— 所以能改到同一份数据。这不能证明是引用传递。真正区分值传递 vs 引用传递的方式是场景三：让形参重新赋值（`p1 = p2`），如果外部变量也跟着变才是引用传递。Java 里外部变量纹丝不动，所以是值传递。

追问 方法里写 `obj = new Foo()`，外部的 obj 会变吗？为什么？

**不会变。** 图示如下：

```
调用前:
外部 obj ────► [Foo@1 堆对象]

进入方法，传参（值传递，拷贝引用值）:
外部 obj ────► [Foo@1]
形参 obj ────► [Foo@1]          ← 两个变量、同一个引用值

方法内 obj = new Foo():
外部 obj ────► [Foo@1]          ← 外部纹丝不动
形参 obj ────► [Foo@2 新对象]   ← 只改了副本

方法返回:
外部 obj ────► [Foo@1]          ← 依然指向老对象
```

本质：形参和实参是两个独立变量，只是「初始值」相同（都存着指向 Foo@1 的引用）。给形参重新赋值只影响形参自己。

## 面试场景 9：值传递 vs 引用传递的本质区别

🧑‍💻 你

关键在于形参在栈上是**「拷贝」还是「别名」**：

```
┌────────────── 值传递（Java）──────────────┐
│                                              │
│  main 栈帧            method 栈帧            │
│  ┌──────────┐         ┌──────────┐           │
│  │ arr: 0x88│────┐    │array:0x88│────┐      │
│  └──────────┘    │    └──────────┘    │      │
│                  │                    │      │
│                  └─────► [堆: {1,2,3}] ◄─────┘
│                                              │
│  两个独立变量，值恰好相同（都是 0x88），      │
│  改 array = null 不影响 arr                  │
└──────────────────────────────────────────────┘

┌────────── 引用传递（C++ 的 T&）────────────┐
│                                              │
│  main 栈帧            method 栈帧            │
│  ┌──────────┐         ┌──────────┐           │
│  │ age: 10  │◄────────│ num: 别名│           │
│  └──────────┘         └──────────┘           │
│                                              │
│  num 就是 age 的别名，同一个存储位置          │
│  num++ 会真正修改 age                        │
└──────────────────────────────────────────────┘
```

维度值传递引用传递

形参本质实参值的*拷贝*，独立的栈变量实参的*别名*，共享同一存储
形参赋新值不影响实参直接修改实参
典型语言Java、Python、Go、JavaScriptC++（`T&`）、C#（`ref`）、Pascal（`var`）
能否 swap 两个变量❌ 不能（必须返回新值或用容器）✅ 能

陷阱 网上很多老资料说「Java 传对象是引用传递」—— **这是错的**。正确说法是「Java 传对象时，传的是*引用的值*，即引用类型的值传递」。这两句话看着像绕口令，但面试官会揪着「拷贝 vs 别名」的区别追问，答错就崩。

## 面试场景 10：为什么 Java 设计成只有值传递？

🧑‍💻 你

Java 之父 James Gosling 在语言设计上遵循**「简单、安全」**原则，摒弃了 C++ 中容易出错的复杂特性。具体到传参：

1. **更安全**：如果允许引用传递，方法内部对参数变量的重新赋值会*直接改到调用者*的变量，调用者对自己变量的状态就失去了可预期性。值传递让方法成为一个「输入→输出」的黑盒，调用者的局部变量永远由调用者掌控。

2. **更简单**：只有一种传参语义（拷贝值），学习者不用记「什么时候是值、什么时候是引用、要不要加 `&`」。C++ 里传参一不小心少写个 `&`，行为就完全不同，是很多 bug 的来源。

3. **不失表达力**：想让方法「修改」调用者的数据，可以通过*返回新值*、*传入可变对象*（借助场景二的机制）、*使用包装类容器*（`AtomicReference`、单元素数组）等模式实现，语义清晰。

相比之下，C++ 的引用传递（`void incr(int& n) { n++; }`）虽然写起来简洁，但需要程序员时时警觉「这个参数会不会被偷偷改掉」，认知负担高。Java 选择放弃这一点便利，换来更简单、更安全的心智模型。

追问 Java 里怎么实现「让方法修改调用者的变量」这种需求？

四种常见套路：**①返回新值**（最常用，函数式风格）；**②传入可变对象**并修改其字段（`List.add`、`StringBuilder.append`）；**③传入单元素数组或 `AtomicReference`**（伪装成「out 参数」）；**④使用回调**（传入 Lambda，由方法回调修改）。第一种最推荐，其他方式除非必要否则不用 —— 会让接口的副作用变得难追踪。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：static 与初始化顺序

```
class Parent {
static { System.out.println("1. 父类静态块"); }
{        System.out.println("3. 父类非静态块"); }
Parent() { System.out.println("4. 父类构造"); }
}

class Child extends Parent {
static { System.out.println("2. 子类静态块"); }
{        System.out.println("5. 子类非静态块"); }
Child() { System.out.println("6. 子类构造"); }
}

public class InitOrder {
public static void main(String[] args) {
System.out.println("--- new Child() 第一次 ---");
new Child();
System.out.println("--- new Child() 第二次 ---");
new Child();
}
}
// 输出：
// --- new Child() 第一次 ---
// 1. 父类静态块      ← 类加载，只这一次
// 2. 子类静态块      ← 类加载，只这一次
// 3. 父类非静态块
// 4. 父类构造
// 5. 子类非静态块
// 6. 子类构造
// --- new Child() 第二次 ---
// 3. 父类非静态块    ← 第二次没有静态块了
// 4. 父类构造
// 5. 子类非静态块
// 6. 子类构造
```

### 验证 2：final 修饰引用类型 vs 基本类型

```
import java.util.ArrayList;
import java.util.List;

public class FinalDemo {
public static void main(String[] args) {
final int MAX = 100;
// MAX = 200;                    // ❌ 编译报错：cannot assign to final variable

final List<Integer> list = new ArrayList<>();
list.add(1);                     // ✅ 合法：修改对象内部
list.add(2);
System.out.println(list);        // [1, 2]

// list = new ArrayList<>();     // ❌ 编译报错：引用不能重新指向

final int[] arr = {1, 2, 3};
arr[0] = 99;                     // ✅ 合法
System.out.println(arr[0]);      // 99
}
}
```

### 验证 3：三段论证明值传递

```
public class ValuePassing {

static void swapPrimitive(int a, int b) {
int t = a; a = b; b = t;
}

static void modifyArray(int[] arr) {
arr[0] = 999;                    // 改对象内容 —— 外部能看到
}

static void swapReference(int[] a, int[] b) {
int[] t = a; a = b; b = t;       // 只交换形参副本 —— 外部无感
}

public static void main(String[] args) {
// 场景 1：基本类型
int x = 10, y = 20;
swapPrimitive(x, y);
System.out.println("基本类型: x=" + x + " y=" + y);
// 输出：x=10 y=20  ← 没变

// 场景 2：引用类型（改内容）
int[] arr = {1, 2, 3};
modifyArray(arr);
System.out.println("改内容后: arr[0]=" + arr[0]);
// 输出：arr[0]=999  ← 变了

// 场景 3：引用类型（swap 引用）
int[] p = {1}, q = {2};
swapReference(p, q);
System.out.println("swap 后: p[0]=" + p[0] + " q[0]=" + q[0]);
// 输出：p[0]=1 q[0]=2  ← 没交换
}
}
```

### 验证 4：transient 忽略序列化字段

```
import java.io.*;

class User implements Serializable {
private static final long serialVersionUID = 1L;
String username;
transient String password;          // ← 不参与序列化

User(String u, String p) { username = u; password = p; }

@Override public String toString() {
return "User{username='" + username + "', password='" + password + "'}";
}
}

public class TransientDemo {
public static void main(String[] args) throws Exception {
User u = new User("alice", "secret123");

// 写出
try (ObjectOutputStream oos =
new ObjectOutputStream(new FileOutputStream("u.ser"))) {
oos.writeObject(u);
}

// 读回
try (ObjectInputStream ois =
new ObjectInputStream(new FileInputStream("u.ser"))) {
User back = (User) ois.readObject();
System.out.println(back);
// 输出：User{username='alice', password='null'}
//                              ↑ password 被 transient 丢弃
}
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `final` 修饰引用类型时，能改什么、不能改什么？</summary>

**能**改对象内部字段（比如 `list.add(x)`、`arr[0] = 99`）；**不能**让引用重新指向别的对象（`list = new ArrayList()` 会编译报错）。`final` 锁的是引用，不是对象本身。

</details>

<details>

<summary>Q2 类初始化时，父子类的静态块、非静态块、构造器执行顺序是什么？</summary>

**父静态 → 子静态 → 父非静态 → 父构造 → 子非静态 → 子构造**。静态部分只在类加载时执行一次；每次 `new` 时执行非静态部分和构造器。

</details>

<details>

<summary>Q3 `volatile` 保证哪些语义？为什么不能保证 `i++` 的原子性？</summary>

保证**可见性**（写后立即刷主存 + 读时从主存加载）和**禁止指令重排**，但**不保证原子性**。`i++` 是「读-改-写」三步字节码，`volatile` 只能保证每步单独读写从/到主存正确，但多个线程可能同时读到同一个旧值再各自 +1 写回，导致丢更新。要原子性得用 `synchronized` 或 `AtomicInteger`。

</details>

<details>

<summary>Q4 Java 是值传递还是引用传递？用一句话总结。</summary>

**Java 只有值传递**。基本类型传字面量值的拷贝；引用类型传引用值（地址）的拷贝。形参是独立的栈变量，只是初始值和实参相同。这就是为什么方法内 `p1 = p2` 交换后，外部的两个变量纹丝不动。

</details>

<details>

<summary>Q5 方法内 `array[0] = 0` 能改到外部数组，但方法内 `array = new int[]{...}` 改不到外部。为什么？</summary>

因为「**改对象内容**」和「**改引用指向**」是两回事。`array[0] = 0` 是通过引用副本访问同一个堆对象、修改其内部数据 —— 外部引用也指向这个对象，自然能看到。`array = new int[]{...}` 是让形参引用副本指向新的堆对象，外部引用还是老的，不受影响。这正是 Java 值传递的核心证据。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 关键字部分主源

-  —— 值传递部分主源

- JLS §8.8.7.1 · Explicit Constructor Invocations —— `this()` / `super()` 调用规则规范

- JLS §8.3.1.4 · `volatile` Fields —— `volatile` 语义规范

#### 🔗 关联课件

- （前一课）

- （下一课）

- （并发深入）

-

#### 🧭 下一课预告

Lesson 0004：**String 为什么不可变 & StringBuilder / StringBuffer & 字符串常量池** —— 承接本课「值传递场景三」提到的 String 特性，把面试官最爱盘问的 `String s = "a" + "b"` 到底会创建几个对象讲透。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


