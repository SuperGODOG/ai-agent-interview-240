> Lesson 0005 · 阶段一 · Java 基础 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 8 处追问

# 0005 · 泛型 & 通配符深挖 & 类型擦除 & PECS

这一课是 的深挖版，主源仍是 。面试里泛型有三个必考点，一个都躲不开：**「什么是类型擦除？」「上下界通配符怎么用？」「PECS 是什么？」**—— 这三题背后其实是同一件事：*Java 的泛型只在编译期存在，运行时全被擦成 Object 或边界类型*。理解了这一点，通配符、桥接方法、擦除限制就都是它的推论。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `new ArrayList<String>().getClass() == new ArrayList<Integer>().getClass()` 返回什么？</summary>

`true`。运行时两者都是 `java.util.ArrayList`，泛型参数被**类型擦除**抹掉了。面试场景 3 会讲透。

</details>

<details>

<summary>Q0.2 `List<? extends Number> list = new ArrayList<Integer>(); list.add(1);` 能编译通过吗？</summary>

**不能**。上界通配符只允许「取」不允许「存」（除了 null）。原因是编译器不知道 `?` 具体是 `Integer` 还是 `Double`，无法保证类型安全。面试场景 5 展开。

</details>

## 面试场景 1：什么是泛型？为什么要引入泛型？

🎤 面试官

先说说你理解的泛型是什么，Java 为什么要加入这个特性？

🧑‍💻 你

**泛型（Generics）**是 JDK 5 引入的特性，允许在类、接口、方法上定义**类型参数**，把「操作的数据类型」当成参数传递。核心价值有三点：

1. **编译期类型安全**：`List<String>` 只能塞 `String`，塞 `Integer` 直接编译报错。JDK 5 之前只能塞进去到运行时才 `ClassCastException`。

2. **免去手动强转**：`String s = list.get(0)` 直接拿，不用 `(String) list.get(0)`。编译器帮你插入的 checkcast 指令仍然存在，只是对开发者透明。

3. **代码复用**：一份 `ArrayList<T>` 源码，可以对任意引用类型工作，不需要为每种类型写一份 `StringArrayList`、`IntegerArrayList`。

追问 为什么说 Java 泛型是「伪泛型」？和 C++ 模板有什么本质区别？

Java 泛型是**编译期特性**：编译器做类型检查和自动插入 checkcast，编译后*擦除*成 raw type，运行时只剩 `List` 而不是 `List<String>`。所以叫「伪泛型」或「编译期泛型」。C++ 模板是**运行前特化**：编译器为 `vector<int>` 和 `vector<string>` 分别*生成两份完全不同的机器码*（模板实例化），运行时每份都保留具体类型。两条路线的取舍是：Java 换取了向后兼容和更小的产物；C++ 换取了运行时类型信息和更强的编译期特化能力（比如 `if constexpr`）。所以你会看到 C++ 里能 `new T()`、能 `sizeof(T)`，Java 里全都不行。

## 面试场景 2：泛型的三种使用方式

🎤 面试官

泛型有几种使用方式？各写一段最小示例。

🧑‍💻 你

三种：**泛型类、泛型接口、泛型方法**。

**① 泛型类**：类名后声明类型参数，作用域是整个类体。

```
public class Box<T> {
private T value;
public Box(T value) { this.value = value; }
public T get() { return value; }
}

Box<Integer> b = new Box<>(123);   // JDK 7+ 菱形推导
```

**② 泛型接口**：实现类可以「延迟指定」或「立即指定」类型。

```
public interface Generator<T> {
T next();
}

// 延迟指定：实现类自己也是泛型
class ListGen<T> implements Generator<T> {
public T next() { return null; }
}

// 立即指定：实现类固定绑一个具体类型
class StringGen implements Generator<String> {
public String next() { return "hello"; }
}
```

**③ 泛型方法**：类型参数写在*返回值前面*，只在这个方法里有效，可以出现在普通类上。

```
public static <E> void printArray(E[] arr) {
for (E e : arr) System.out.print(e + " ");
}

printArray(new Integer[]{1, 2, 3});
printArray(new String[]{"a", "b"});
```

陷阱 泛型方法的 `<E>` 是**方法自己的类型参数**，和所在类的类型参数没有任何关系。写 `public <T> T foo()` 时，即使类里也有个 `<T>`，这里的 `T` 会*遮蔽*类上的 `T`，是两个不同的类型。这是常见的漏答点。

## 面试场景 3：类型擦除是什么？（★核心）

🎤 面试官

你说 Java 泛型是伪泛型，具体讲讲类型擦除机制。

🧑‍💻 你

**类型擦除（Type Erasure）**是 Java 泛型的实现方式：*编译期做类型检查，编译后把泛型信息全部擦掉，字节码里只剩 raw type*。擦除规则很简单：

- 无界的类型参数（`<T>`）擦除为 `Object`。

- 有界的类型参数（`<T extends Number>`）擦除为**第一个边界**（这里是 `Number`）。

- 需要类型转换的地方，编译器自动插入 `checkcast` 字节码。

- 类文件的 `Signature` 属性里保留泛型声明（供反射用），但 `getClass()` 拿不到。

所以：

```
List<String>  a = new ArrayList<>();
List<Integer> b = new ArrayList<>();
System.out.println(a.getClass() == b.getClass());  // true
```

两者在运行时都是 `java.util.ArrayList`，同一个 `Class` 对象。这是 Java 为了兼容 JDK 5 之前老代码做的妥协 —— *老代码用 raw type 编译出来的 `.class`，和新代码用泛型编译出来的 `.class`，二进制层面完全兼容*。

追问 类型擦除后，怎么在运行时拿到泛型的实际类型？

三条路：

1. **字段/方法/参数上的泛型**：类文件里有 `Signature` 属性，反射 API 提供 `Field.getGenericType()`、`Method.getGenericReturnType()`、`Method.getGenericParameterTypes()`，返回 `ParameterizedType`，能拿到 `List<String>` 里的 `String`。

2. **父类/父接口的泛型**：子类继承时的实参也保留在 `Signature` 里，用 `getClass().getGenericSuperclass()` 拿。**超类型令牌（Super Type Token）**就是靠这个：定义匿名子类 `new TypeReference<List<String>>() {}`，通过父类拿到 `List<String>`。Jackson 的 `TypeReference`、Guice 的 `TypeLiteral`、Spring 的 `ParameterizedTypeReference` 全是这个套路。

3. **方法内部的局部变量泛型**：*拿不到*。这是彻底擦除的，字节码里连 `Signature` 都没有。

## 面试场景 4：类型擦除带来了哪些限制？

🧑‍💻 你

擦除决定了运行时没有 `T`，很多操作因此做不到：

禁止的写法原因

`new T()`擦除后不知道调哪个构造器；解决方式是传 `Class<T>` 或 `Supplier<T>`。
`new T[10]`擦除后 `T` 变 `Object`，无法在运行时做 ArrayStore 检查，可能污染数组。JDK 用 `(T[]) new Object[10]` + `@SuppressWarnings` 绕。
`list instanceof List<String>`运行时都是 `List`，无法区分 `List<String>` 和 `List<Integer>`。只能写 `list instanceof List<?>`。
基本类型作为类型参数（`List<int>`）擦除到 `Object`，基本类型不是 `Object` 子类，只能用包装类 `List<Integer>`。
static 字段/方法引用类的类型参数类型参数属于实例；static 属于类。*静态泛型方法自己声明的 `<T>` 是可以的*。
方法重载 `foo(List<String>)` 和 `foo(List<Integer>)`擦除后签名相同，编译报错「same erasure」。
`catch (T e)` / 泛型类 extends ThrowableJVM 抛异常时通过运行时类型匹配，泛型异常无法在运行时识别。

陷阱 `class MyException<T> extends RuntimeException` 也是禁止的 —— 编译器直接报错。因为异常表按类型匹配，如果允许 `MyException<String>`，运行时无法区分 `MyException<String>` 和 `MyException<Integer>`，异常处理就乱了。

## 面试场景 5：上界通配符 `<? extends T>`（Producer）

🎤 面试官

`List<? extends Number>` 和 `List<Number>` 有什么区别？前者能 `add(1)` 吗？

🧑‍💻 你

**不能 `add`**（除了 `null`）。这是理解通配符的关键分水岭。

- `List<Number>`：类型精确锁死为 `Number`，只能装 `Number`（也可以装子类如 `Integer`，但会被视作 `Number`）。

- `List<? extends Number>`：*类型未知，但确定是 `Number` 的某个子类型*。可能是 `List<Integer>`，也可能是 `List<Double>`。

正因为不知道具体是哪个子类，编译器**不敢让你写入**：假如它允许 `list.add(1)`，但底层其实是 `List<Double>`，就把 `Integer` 塞进了 `List<Double>`，运行时就爆。

但可以放心**读取**：无论 `?` 是 `Integer` 还是 `Double`，都一定是 `Number` 的子类，赋给 `Number` 变量绝对安全。这就是「上界通配符是 **Producer**（生产者）」的由来 —— 只往外吐数据。

```
List<? extends Number> list = new ArrayList<Integer>();
Number n = list.get(0);     // ✅ 一定是 Number
// list.add(1);             // ❌ 编译错，不知道 ? 是什么
list.add(null);             // ✅ null 是所有引用类型的合法值
```

追问 那为什么 Java 泛型要设计成「不变（invariant）」？允许 `List<Integer>` 赋给 `List<Number>` 不行吗？

不行，会破坏类型安全。假设允许：`List<Number> ns = new ArrayList<Integer>()`，那 `ns.add(3.14)` 就把 `Double` 塞进了 `List<Integer>`，取出来 `Integer i = xs.get(0)` 直接 ClassCastException。所以 Java 选择**泛型默认不变（invariant）**，需要变化时用通配符显式表达变化方向（extends = 协变，super = 逆变）。这也是它和数组（协变但不安全）最大的区别，场景 10 会对比。

## 面试场景 6：下界通配符 `<? super T>`（Consumer）

🧑‍💻 你

**下界通配符能写不能读（读只能当 Object）**，正好和上界相反。

`List<? super Integer>` 表示「类型未知，但确定是 `Integer` 的某个父类型」，可能是 `List<Integer>`、`List<Number>`、`List<Object>`。

- **能写**：无论 `?` 是哪个父类，塞 `Integer` 进去都安全（子类实例可以赋给父类容器）。

- **读只能当 `Object`**：不知道具体父类是什么，只能安全地当 `Object` 用。

```
List<? super Integer> list = new ArrayList<Number>();
list.add(1);               // ✅ Integer 可以安全塞进任何 Integer 的父类容器
list.add(Integer.valueOf(2));
// Integer i = list.get(0);   // ❌ 编译错
Object o = list.get(0);    // ✅ 只能当 Object
```

这就是「下界是 **Consumer**（消费者）」的意思 —— 只吃数据不吐数据。

## 面试场景 7：PECS 原则（★核心）

🎤 面试官

PECS 原则是什么？在 JDK 里有例子吗？

🧑‍💻 你

**PECS = Producer Extends, Consumer Super**，Joshua Bloch 在《Effective Java》里提出的通配符使用口诀：

- 如果参数是「**生产者**」（数据从它流*出*到你的代码），用 `<? extends T>`。

- 如果参数是「**消费者**」（数据从你的代码流*入*它），用 `<? super T>`。

- 如果既读又写，就不用通配符，用具体 `T`。

JDK 教科书级例子是 `Collections.copy`：

```
public static <T> void copy(List<? super T> dest, List<? extends T> src) {
for (int i = 0; i < src.size(); i++) {
dest.set(i, src.get(i));
}
}
```

`src` 是数据源（生产者），只从里面 `get`，用 `extends`；`dest` 是目的地（消费者），只往里面 `set`，用 `super`。这样调用就能非常灵活：`copy(List<Object>, List<Integer>)` 也合法。

另一个经典例子是 `Collections.sort`：

```
public static <T> void sort(List<T> list, Comparator<? super T> c)
```

`Comparator` 是消费者（吃 T 输出 int），所以用 `super` —— `List<Integer>` 就可以复用一个 `Comparator<Number>`。

追问 PECS 记不住怎么办？有没有直觉理解？

用**「箭头方向」**记：`extends` 是*数据往上流*（从子类往父类走），因为你只能保证读出来的是父类 —— 所以是「生产者」向外供货。`super` 是*数据往下流*（从父类往子类走），因为你可以把子类塞进父类容器 —— 所以是「消费者」进货。或者用一个更贴合业务的比喻：*「往购物车里放东西」就用 super（购物车能装我这个具体商品的所有父类容器），「从冰箱里拿东西」就用 extends（冰箱里放的都是我要的父类的子类，拿出来当父类用）*。

追问 `List<? extends Number> list; list.add(1)` 到底为什么不行？编译器内部怎么想的？

编译器内部有个概念叫**「通配符捕获（capture）」**：遇到 `?`，编译器把它捕获成一个*新的匿名类型变量*，比如 `CAP#1`，且只知道 `CAP#1 extends Number`。`list.add(x)` 需要 `x` 是 `CAP#1`，但你传的 `1` 是 `Integer`，编译器无法证明 `Integer` 就是 `CAP#1`（因为 `CAP#1` 可能是 `Double`）。**只有 `null` 一定是任意引用类型的合法值**，所以 `list.add(null)` 允许。

## 面试场景 8：无界通配符 `<?>` 和 raw type 的区别

🎤 面试官

`List<?>` 和 `List`（raw type）有什么区别？看起来都是「什么都能装」。

🧑‍💻 你

看着像，实际差别很大：

维度`List<?>``List`（raw type）

本质参数化类型，*某个具体但未知*的 `T`原生类型，*放弃泛型检查*
`add(Object)`❌ 编译错（除了 `null`）⚠️ 允许，但有 unchecked 警告
类型安全安全（编译器仍在保护你）不安全（会把 ClassCastException 推迟到运行时）
使用场景只需要读或不关心类型时（如 `list.size()`、`list.clear()`）仅用于兼容 JDK 5 之前的旧 API，新代码不推荐

```
List<?> wild = new ArrayList<String>();
// wild.add("x");         // ❌ 编译错
wild.add(null);           // ✅
Object o = wild.get(0);   // ✅ 只能当 Object

List raw = new ArrayList<String>();
raw.add(1);               // ⚠️ warning: unchecked call
raw.add("hello");         // ⚠️ 没保护，把 Integer 塞进了 List<String>
```

陷阱 用了 raw type 之后，整个类的**所有**泛型检查都会失效，不只是那一行。比如 `List raw = ...; raw.iterator()` 返回的是 `Iterator` 而不是 `Iterator<T>`。所以工程实践里禁止 raw type，SonarQube、Checkstyle 都会标红。

## 面试场景 9：桥接方法（bridge method）是什么？为什么会产生？

🎤 面试官

说说桥接方法，为什么编译器要生成它？

🧑‍💻 你

**桥接方法是编译器为了在类型擦除后保持多态而自动合成的方法**。看这段：

```
class Node<T> {
public void setData(T data) { /* ... */ }
}

class IntNode extends Node<Integer> {
@Override
public void setData(Integer data) { /* ... */ }
}
```

类型擦除后，父类 `Node` 的方法签名其实是 `setData(Object)`，子类的是 `setData(Integer)` —— *签名不同，本来算不上重写*。多态就断了：`Node n = new IntNode(); n.setData(x)` 会走到父类的 `setData(Object)`。

为了修复这个断裂，编译器在 `IntNode` 里自动加一个**桥接方法**：

```
// 编译器合成，javap -c 能看到
public void setData(Object data) {   // 和父类签名一致
setData((Integer) data);         // 转发到真正的实现
}
```

这样多态就恢复了：外部调用 `setData(Object)` 走桥接方法，桥接方法转发到 `setData(Integer)`。桥接方法的 access flag 里有 `ACC_BRIDGE` 和 `ACC_SYNTHETIC`。

追问 桥接方法能通过反射拿到吗？怎么和普通方法区分？

能拿到。`getDeclaredMethods()` 会同时返回真实方法和桥接方法。区分它们用 `Method.isBridge()`：桥接方法返回 `true`，普通方法返回 `false`。Spring 的 `BridgeMethodResolver.findBridgedMethod(bridge)` 就是用这个 API 把桥接方法映射回真实方法 —— 因为拿桥接方法上的注解会拿不到（注解写在真实方法上），必须先解到真实方法。*面试里能顺嘴说出 `isBridge()` 和 Spring `BridgeMethodResolver`，就到高级候选人档位了*。

## 面试场景 10：数组和泛型有什么区别？（协变 vs 不变）

🧑‍💻 你

维度数组泛型

变型**协变**：`Integer[]` 是 `Number[]` 的子类型**不变**：`List<Integer>` 不是 `List<Number>` 的子类型
运行时类型**具化（reified）**，保留元素类型**擦除**，运行时只有 raw type
类型检查运行时（`ArrayStoreException`）编译时（编译报错）
安全性不安全（写入错类型只在运行时爆）安全（编译期就拦下）

典型的数组协变陷阱：

```
Number[] arr = new Integer[3];   // ✅ 编译通过（协变）
arr[0] = 3.14;                   // 💥 运行时 ArrayStoreException

List<Number> list = new ArrayList<Integer>();  // ❌ 编译就报错（不变）
```

正因为数组是协变但保留类型的、泛型是不变但被擦除的，两者**互不兼容**：所以不能 `new T[10]`，也不能 `new List<String>[10]`。想要泛型数组，只能 `(T[]) new Object[10]` 或用 `Class<T>` + `Array.newInstance()`。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：类型擦除 —— 两个 List 是同一个 Class

```
import java.lang.reflect.Method;
import java.util.*;

public class ErasureDemo {
public static void main(String[] args) throws Exception {
List<String>  a = new ArrayList<>();
List<Integer> b = new ArrayList<>();
System.out.println(a.getClass() == b.getClass());   // true
System.out.println(a.getClass().getName());         // java.util.ArrayList

// 反射绕过泛型检查，把 String 塞进 List<Integer>
Method add = b.getClass().getMethod("add", Object.class);
add.invoke(b, "not an int");
System.out.println(b);                              // [not an int]
// Integer i = b.get(0);   // 💥 编译器插入的 checkcast 在这里 ClassCastException
}
}
```

### 验证 2：擦除后签名冲突 —— 无法重载

```
public class OverloadFail {
// 编译错：name clash, both methods have same erasure
public void print(List<String>  list) { }
public void print(List<Integer> list) { }
}
```

### 验证 3：PECS 演示 —— `Collections.copy` 的灵活性

```
import java.util.*;

public class PecsDemo {
// 自己写一个 copy 感受 PECS
static <T> void copy(List<? super T> dest, List<? extends T> src) {
for (int i = 0; i < src.size(); i++) {
dest.set(i, src.get(i));
}
}

public static void main(String[] args) {
List<Integer> src  = Arrays.asList(1, 2, 3);
List<Number>  dst  = new ArrayList<>(Arrays.<Number>asList(0, 0, 0));
List<Object>  dst2 = new ArrayList<>(Arrays.<Object>asList("", "", ""));

copy(dst,  src);   // ✅ dst 是 List<Number>，src 是 List<Integer>
copy(dst2, src);   // ✅ dst2 是 List<Object> 也 OK
System.out.println(dst);   // [1, 2, 3]
System.out.println(dst2);  // [1, 2, 3]
}
}
```

### 验证 4：桥接方法 —— 用 javap 看到编译器合成

```
// Node.java
public class Node<T> {
public void setData(T data) { }
}

public class IntNode extends Node<Integer> {
@Override
public void setData(Integer data) { }
}
```

```
$ javac Node.java IntNode.java
$ javap -c -p IntNode

public class IntNode extends Node<java.lang.Integer> {
public void setData(java.lang.Integer);        // 你写的真实方法

public void setData(java.lang.Object);          // 🔥 编译器合成的桥接方法
Code:
0: aload_0
1: aload_1
2: checkcast     #7   // class java/lang/Integer
5: invokevirtual #13  // Method setData:(Ljava/lang/Integer;)V
8: return
}
```

用反射也能观察到：

```
for (Method m : IntNode.class.getDeclaredMethods()) {
System.out.println(m + " isBridge=" + m.isBridge());
}
// public void IntNode.setData(java.lang.Integer) isBridge=false
// public void IntNode.setData(java.lang.Object)  isBridge=true
```

### 验证 5：数组协变的运行时坑

```
public class ArrayCovariance {
public static void main(String[] args) {
Number[] arr = new Integer[3];   // 数组协变，编译通过
arr[0] = Integer.valueOf(1);     // OK
arr[1] = 3.14;                    // 💥 ArrayStoreException

// 泛型不变，同样意图直接编译报错
// List<Number> list = new ArrayList<Integer>();  // ❌
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 一句话解释「类型擦除」。</summary>

编译期做类型检查、编译后把泛型信息擦成 raw type（无界擦为 `Object`，有界擦为第一个边界），运行时不保留具体类型实参 —— 目的是与 JDK 5 之前的旧字节码保持兼容。

</details>

<details>

<summary>Q2 `List<? extends Number>` 为什么不能 `add`？`List<? super Integer>` 为什么可以 `add`？</summary>

前者只知道 `?` 是 `Number` 的某个子类，但具体是哪个不知道，写入无法保证安全（只有 `null` 除外）。后者只知道 `?` 是 `Integer` 的某个父类，无论哪个父类，把 `Integer` 塞进去（子类实例赋给父类容器）都是安全的。

</details>

<details>

<summary>Q3 用 PECS 解释 `Collections.sort(List<T> list, Comparator<? super T> c)` 里 `super` 的意义。</summary>

`Comparator` 是消费者（它「吃」`T` 输出比较结果），按 PECS 应该用 `? super T`。这样 `List<Integer>` 可以复用一个 `Comparator<Number>`，因为能比较 `Number` 的比较器一定也能比较 `Integer`。

</details>

<details>

<summary>Q4 桥接方法是什么？怎么用反射把它和真实方法区分开？</summary>

编译器为保留类型擦除后的多态而合成的方法，签名和父类擦除后的签名一致，内部转发到真实方法。反射用 `Method.isBridge()` 判断，桥接方法返回 `true`，注解一般不会写在桥接方法上，需要用 Spring 的 `BridgeMethodResolver` 或手动反查真实方法。

</details>

<details>

<summary>Q5 说出至少三条「类型擦除带来的使用限制」。</summary>

不能 `new T()`、不能 `new T[]`、不能 `instanceof List<String>`、不能用基本类型作泛型参数、static 字段不能引用类的类型参数、不能重载 `foo(List<String>)` 和 `foo(List<Integer>)`、不能 catch 泛型异常、泛型类不能 extends Throwable。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Oracle Java Tutorial · Generics —— 官方教程，PECS、桥接方法讲得最全

- JLS §4.6 · Type Erasure —— 类型擦除的规范定义

- 《Effective Java (3rd)》 Item 26-33 —— Joshua Bloch 关于泛型的 8 条建议，PECS 就出自 Item 31

#### 🔗 关联课件

- （本课的入门篇）

- （下一课，配合超类型令牌拿泛型实参）

- （`HashMap<K, V>` 是泛型最经典的使用现场）

#### 🧭 下一课预告

Lesson 0006：**反射深挖** —— `Class`、`Method`、`Field`、`Constructor` 四大 API，结合本课的超类型令牌讲怎么在运行时拿到 `List<String>` 里的 `String`；再顺带聊 `setAccessible`、性能损耗、Spring/Jackson 里的反射。

💬 有任何疑问 —— 「PECS 的 super 我还是搞混」「桥接方法在 lambda 里也会有吗？」「为什么 Kotlin 有 reified 泛型 Java 没有？」—— 直接问我。我是你的老师，也是你的追问陪练。


