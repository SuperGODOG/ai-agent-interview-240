> Lesson 0011 · 阶段二 · 集合框架 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0011 · ArrayList 源码分析：数据结构 & 扩容 & fail-fast

这一课把 的高频考点一次讲透。ArrayList 是面试官最爱翻源码的类之一，因为它足够简单，能考察你「是否真读过 JDK 源码」而不是背题背来的。开场三连击几乎必问：**「`new ArrayList<>()` 初始容量是多少？」「扩容是几倍？」「怎么做到 fail-fast？」**—— 答不上第一题就 gg，因为「初始容量是 10」是被无数博客带偏的标准错误答案。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `new ArrayList<>()` 创建出来的 `elementData` 长度是 10 吗？</summary>

**不是**。默认构造给的是 `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`，一个静态空数组（长度 `0`）。要等到第一次 `add` 时才把它扩容到 `DEFAULT_CAPACITY = 10`。这是「懒加载」优化，第 2 题会展开。

</details>

<details>

<summary>Q0.2 ArrayList 扩容是 1.5 倍还是 2 倍？为什么？</summary>

**1.5 倍**，代码是 `newCapacity = oldCapacity + (oldCapacity >> 1)`。1.5 倍的动机是「Fibonacci 空间局部性 + 复用旧堆内存的概率更高」。HashMap 是 2 倍，那是因为要用 `hash & (n-1)` 位运算 —— 两者动机完全不同。第 5、6 题会展开。

</details>

## 面试场景 1：ArrayList 的底层数据结构是什么？

🎤 面试官

ArrayList 底层是什么？为什么不是用泛型数组？

🧑‍💻 你

底层是一个 `Object[] elementData`，声明如下：

```
transient Object[] elementData;
private int size;
```

几个关键点：

- **是 `Object[]`，不是 `E[]`**。因为 Java 泛型是*类型擦除*的，运行时 `E` 已经不存在，无法 `new E[n]`。

- **用 `transient` 修饰**，不参与默认序列化。ArrayList 重写了 `writeObject`，只序列化 `[0, size)` 范围的有效元素，跳过尾部预留的空位 —— 省流量。

- **`size` 是逻辑长度**（有效元素个数），`elementData.length` 是物理容量（数组长度）。*两者不相等*是常识点。

追问 为什么不能 `new E[capacity]`？

Java 泛型是**编译期类型检查 + 运行时擦除**。运行时 `E` 被擦为 `Object`，JVM 根本不知道 `E` 是什么类型，无法为它分配数组。而 `new Object[capacity]` 是合法的，再向上强转声明成 `E[]` 也可以，但会有 unchecked warning。JDK 选择直接用 `Object[]` 内部存储，取出时强转成 `E`。

追问 ArrayList 实现了哪些接口？`RandomAccess` 有什么用？

继承 `AbstractList`，实现 `List`、`RandomAccess`、`Cloneable`、`Serializable`。其中 `RandomAccess` 是**标记接口（marker interface）**，没有任何方法，仅用于告诉调用方「我支持 O(1) 随机访问」。`Collections.binarySearch` 等算法会 `instanceof RandomAccess` 判断，是的话走下标遍历（快），否则走迭代器遍历（LinkedList 就是后者）。

## 面试场景 2：`new ArrayList<>()` 初始容量是多少？（★经典陷阱）

🎤 面试官

`new ArrayList<>()` 创建出来的 List，其内部数组的长度是多少？

🧑‍💻 你

**是 0，不是 10**。看无参构造源码：

```
private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = {};

public ArrayList() {
this.elementData = DEFAULTCAPACITY_EMPTY_ELEMENTDATA;
}
```

`DEFAULTCAPACITY_EMPTY_ELEMENTDATA` 是一个静态*空数组*（长度 0），所有默认构造的 ArrayList 共享它。真正把容量扩到 10 是在**第一次 `add`**触发的：

```
private static int calculateCapacity(Object[] elementData, int minCapacity) {
if (elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
return Math.max(DEFAULT_CAPACITY, minCapacity);   // DEFAULT_CAPACITY = 10
}
return minCapacity;
}
```

逻辑是：如果内部数组的*引用*还等于那个默认的空数组常量，就把需要容量抬到 `max(10, minCapacity)`，让第一次扩容直接一步到 10。

陷阱 有两个都叫「空数组」的常量，别搞混：

- `EMPTY_ELEMENTDATA`：由 `new ArrayList<>(0)` 或空 Collection 构造使用。第一次 add 会走「正常扩容」*不会*直接扩到 10。

- `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`：由 `new ArrayList<>()` 无参构造使用。第一次 add 会*特殊*扩到 10。

两个常量长得一模一样（都是 `{}`），但通过**引用相等（`==`）**来区分身份 —— 这是 JDK 里少见的用引用当「标记」的技巧。

追问 为什么 `new ArrayList<>()` 不直接分配长度 10 的数组？

**懒加载优化**。很多场景下 ArrayList 被 new 出来后从未添加元素（比如作为方法参数占位、条件分支里没走到），预分配 10 个 Object 引用（32 位 40 字节、64 位 80 字节）在*百万级 List 创建*的服务里就是明显的内存浪费。JDK 7 update 40 之后引入这个优化，把「首次 add 才扩容」变成默认行为。

## 面试场景 3：`new ArrayList<>(int)` 和 `new ArrayList<>(Collection)` 分别做了什么？

🧑‍💻 你

**带 `int` 参数的构造**直接按参数 new 数组：

```
public ArrayList(int initialCapacity) {
if (initialCapacity > 0) {
this.elementData = new Object[initialCapacity];
} else if (initialCapacity == 0) {
this.elementData = EMPTY_ELEMENTDATA;              // 注意不是 DEFAULTCAPACITY_...
} else {
throw new IllegalArgumentException("Illegal Capacity: " + initialCapacity);
}
}
```

**带 `Collection` 参数的构造**把源集合的元素拷进来：

```
public ArrayList(Collection<? extends E> c) {
Object[] a = c.toArray();
if ((size = a.length) != 0) {
if (c.getClass() == ArrayList.class) {
elementData = a;
} else {
elementData = Arrays.copyOf(a, size, Object[].class);
}
} else {
elementData = EMPTY_ELEMENTDATA;
}
}
```

细节点：`c.toArray()` 返回的*不一定是 `Object[]`*（比如 `Arrays.asList(...)` 返回的内部 List 的 `toArray` 可能返回 `String[]`），所以要用 `Arrays.copyOf(a, size, Object[].class)` 强制转成 `Object[]`，否则后面 `elementData[i] = someOtherObject` 时会抛 `ArrayStoreException`。这是 JDK 早期一个著名的 bug（bug 6260652）。

追问 什么场景应该用 `new ArrayList<>(int)` 预分配？

已知或能估算最终大小的场景。比如从数据库查出 `List<User> users`，接下来要把 `users` 每个映射成 DTO —— 直接 `new ArrayList<>(users.size())` 一步到位，避免 `add` 过程中多次扩容 + `Arrays.copyOf`。对上万元素的 List 效果尤其明显。

## 面试场景 4：`add(E e)` 的完整流程

🎤 面试官

手撕 `add(E e)` 的执行流程。

🧑‍💻 你

入口非常朴素：

```
public boolean add(E e) {
ensureCapacityInternal(size + 1);      // 1. 确保容量足够容纳 size+1 个元素
elementData[size++] = e;               // 2. 尾部赋值 + size++
return true;
}
```

展开 `ensureCapacityInternal`：

```
private void ensureCapacityInternal(int minCapacity) {
ensureExplicitCapacity(calculateCapacity(elementData, minCapacity));
}

// 首次 add 时把 minCapacity 提到 10
private static int calculateCapacity(Object[] elementData, int minCapacity) {
if (elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
return Math.max(DEFAULT_CAPACITY, minCapacity);
}
return minCapacity;
}

private void ensureExplicitCapacity(int minCapacity) {
modCount++;                             // ★ 记账，fail-fast 靠它
if (minCapacity - elementData.length > 0)
grow(minCapacity);                  // 容量不够就扩
}
```

完整链路：`add → ensureCapacityInternal → calculateCapacity（首次提升到 10）→ ensureExplicitCapacity（modCount++）→ 容量不够则 grow → elementData[size++] = e`。

追问 `size++` 和 `++size` 这里能互换吗？

不能。`elementData[size++] = e` 是「先用旧 `size` 当下标赋值，然后 `size` 自增」—— 正确。如果写成 `elementData[++size] = e`，就变成「先自增再用新 `size` 当下标」，会在下标 1 而不是 0 的位置写入第一个元素，还会漏一个位置。

## 面试场景 5：扩容 `grow()` 是怎么算新容量的？（★核心）

🎤 面试官

手写 `grow()` 方法。

🧑‍💻 你

```
private void grow(int minCapacity) {
int oldCapacity = elementData.length;
int newCapacity = oldCapacity + (oldCapacity >> 1);   // ★ 1.5 倍
if (newCapacity - minCapacity < 0)
newCapacity = minCapacity;                          // 保护：新容量还不够就直接用 minCapacity
if (newCapacity - MAX_ARRAY_SIZE > 0)
newCapacity = hugeCapacity(minCapacity);            // 超大数组的边界处理
elementData = Arrays.copyOf(elementData, newCapacity);
}

private static int hugeCapacity(int minCapacity) {
if (minCapacity < 0)                                    // 溢出成负数了
throw new OutOfMemoryError();
return (minCapacity > MAX_ARRAY_SIZE)
? Integer.MAX_VALUE
: MAX_ARRAY_SIZE;                                   // MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8
}
```

核心是 `oldCapacity + (oldCapacity >> 1)`，位运算等价于 `oldCapacity * 1.5`，但比乘法快一点点。三步分层：

1. **算新容量 = 旧容量 × 1.5**（向下取整）。

2. **如果 1.5 倍还不够放下 `minCapacity`**（比如你一次 `addAll` 加了很多），就直接用 `minCapacity`。

3. **如果超过 `MAX_ARRAY_SIZE`（`Integer.MAX_VALUE - 8`）**，走 `hugeCapacity` 处理边界。留 8 个位置是给数组对象头。

最后一步 `Arrays.copyOf` 底层就是 `System.arraycopy`（native）—— 老数组内容整体搬到新数组，旧数组等待 GC。

陷阱 JDK 版本差异：

- **JDK 6 及以前**：`int newCapacity = (oldCapacity * 3) / 2 + 1;` —— 也是 1.5 倍，但 `+1` 是为了防止 `oldCapacity = 1` 时算出来还是 1 陷入死循环。

- **JDK 7-8**：改成 `oldCapacity + (oldCapacity >> 1)`，并靠「`newCapacity < minCapacity 时用 minCapacity`」这条兜底避免死循环。

- **JDK 11+**：整体逻辑不变，但 `MAX_ARRAY_SIZE` 相关的 `hugeCapacity` 校验更完善。

追问 扩容用的 `Arrays.copyOf` 底层是什么？

是 native 方法 `System.arraycopy`。它由 JVM 用 C++ 实现，能直接用 `memcpy` 级别的批量内存拷贝，比在 Java 层写 `for` 循环快一到两个数量级。JIT 还会把它内联优化。

## 面试场景 6：为什么扩容是 1.5 倍不是 2 倍？

🎤 面试官

HashMap 扩容是 2 倍，为什么 ArrayList 只用 1.5 倍？

🧑‍💻 你

两者动机完全不同：

- **HashMap 用 2 倍**是因为「容量必须是 2 的幂」，才能用 `hash & (n-1)` 替代 `hash % n`（位运算比取模快得多），并且扩容时旧下标的元素要么留在原位，要么移到「原位 + 旧容量」，rehash 只需要判断多出的一位 —— 2 倍是*算法要求*。

- **ArrayList 选 1.5 倍**是*时空平衡*：

1. **省内存**：2 倍在数据量大时非常吃内存 —— 假设从 100M 扩到 200M，浪费的空间就是 100M。1.5 倍只浪费 50M。

2. **Fibonacci-like，复用旧内存概率高**：1.5 倍下每次扩容的*新老容量之和*大约等于「上上次的容量」（`1 + 1.5 = 2.5 < 1.5³ ≈ 3.375`）—— 每次扩容释放的旧数组内存有机会被下次的新数组复用，减少堆碎片。2 倍就*永远*无法复用（新的一定大于所有历史空间之和）。

追问 「1.5 倍能复用旧内存」是理论最优吗？

数学上最优增长因子是**黄金比例 φ ≈ 1.618**（Fibonacci 生成函数的极限）—— 严格保证「新分配空间 = 之前所有释放空间之和」。C++ STL 的 `vector` 在 GCC 里选 2 倍（Windows MSVC 选 1.5 倍），Java 选 1.5 是*接近*黄金比例、且能用位运算 `>> 1` 快速计算的折中。

## 面试场景 7：`remove(int index)` 的实现

🧑‍💻 你

```
public E remove(int index) {
rangeCheck(index);
modCount++;                                         // ★ 记账，触发 fail-fast

E oldValue = elementData(index);
int numMoved = size - index - 1;
if (numMoved > 0)
System.arraycopy(elementData, index + 1,
elementData, index, numMoved); // 后面的元素整体左移一位
elementData[--size] = null;                         // ★ 尾部置 null 帮助 GC
return oldValue;
}
```

要点：

1. **`rangeCheck`** 只查 `index >= size`（负数下标由数组访问抛 `ArrayIndexOutOfBoundsException`）。

2. **`System.arraycopy` 左移**：把 `[index+1, size)` 的元素整体挪到 `[index, size-1)`。所以 `remove(0)` 是 `O(n)`，性能最差；`remove(size-1)` 时 `numMoved = 0`，不用拷贝，`O(1)`。

3. **`elementData[--size] = null`**：*必须把尾部的引用置 `null`*，否则那个位置还持有已被「删除」对象的强引用，会阻止 GC 回收 —— 内存泄漏隐患。

追问 `remove(Object o)` 和 `remove(int index)` 会重载冲突吗？

不会，签名不同。但用 `Integer` 调用时要小心：`list.remove(1)` 会调 `remove(int)` 按下标删；`list.remove(Integer.valueOf(1))` 才是按对象值删。这是**自动装箱陷阱**常见题，牵扯到「精确匹配优于自动装箱」的方法解析规则。

追问 为什么 `ArrayList` 没有 `ensureCapacity` 的*自动缩容*？

因为 `remove` 场景不像 `add` 那样自然连续，很难判断「什么时候值得缩」—— 缩了下一秒又扩就纯亏。JDK 把缩容主动权交给用户，需要显式调 `trimToSize()`：

```
public void trimToSize() {
modCount++;
if (size < elementData.length) {
elementData = (size == 0)
? EMPTY_ELEMENTDATA
: Arrays.copyOf(elementData, size);
}
}
```

典型用法是「批量加载完成后，长期只读」的 List，调一次 `trimToSize` 释放尾部预留空间。

## 面试场景 8：fail-fast 机制（★核心）

🎤 面试官

ArrayList 是怎么实现 fail-fast 的？源码在哪儿？

🧑‍💻 你

三个关键点：

1. **`modCount` 字段**：定义在父类 `AbstractList` 里，每次*结构性修改*（add/remove/clear/ensureCapacity 等）都自增。

2. **迭代器初始化时快照**：`Itr` 构造时把当前 `modCount` 存进 `expectedModCount`。

3. **每次 `next()` / `remove()` 前校验**：一旦 `modCount != expectedModCount`，立刻抛 `ConcurrentModificationException`。

```
private class Itr implements Iterator<E> {
int cursor;              // 下一个要返回的元素下标
int lastRet = -1;        // 上一个返回的下标（供 remove 用）
int expectedModCount = modCount;

public E next() {
checkForComodification();
int i = cursor;
// ... 越界检查 ...
Object[] elementData = ArrayList.this.elementData;
cursor = i + 1;
return (E) elementData[lastRet = i];
}

public void remove() {
// ... 状态检查 ...
try {
ArrayList.this.remove(lastRet);      // 走外层 remove，modCount 会 ++
cursor = lastRet;
lastRet = -1;
expectedModCount = modCount;         // ★ 同步回来，不抛 CME
} catch (IndexOutOfBoundsException ex) {
throw new ConcurrentModificationException();
}
}

final void checkForComodification() {
if (modCount != expectedModCount)
throw new ConcurrentModificationException();
}
}
```

所以「用 `Iterator.remove()` 是安全的」*不是因为它不改 `modCount`*，而是因为它调完外层 `remove` 后**把 `expectedModCount` 也同步更新了**。

追问 for-each 遍历时用 `list.remove()` 一定会抛 CME 吗？

**不一定**。for-each 编译后就是 `Iterator`。如果你 remove 的是*倒数第二个元素*，remove 完 `size` 减一，`cursor` 已经指向了原「倒数第一个」的位置，但新 `size` 正好等于 `cursor`，`hasNext()` 返回 `false`，循环直接退出 —— *根本没走到下一次 `checkForComodification`*，就漏检了。这也是 JDK 官方明确说的：「fail-fast 不能作为并发正确性依据，只能作为 bug 探测器」。

追问 怎样安全地在遍历中删除元素？

三种方式：

1. **用 `Iterator.remove()`**：手动写 `Iterator<E> it = list.iterator(); while(it.hasNext()) { if(...) it.remove(); }`。

2. **用 `removeIf(predicate)`**：JDK 8+，一行搞定，内部就是安全的迭代器删除。

3. **倒序 for 循环 + 下标删**：`for (int i = list.size()-1; i >= 0; i--) if(...) list.remove(i);`。倒序避免了下标错位。

## 面试场景 9：fail-fast 和 fail-safe 的区别 & 应用场景

维度fail-fastfail-safe

典型集合ArrayList / HashMap / HashSet / LinkedListCopyOnWriteArrayList / ConcurrentHashMap
迭代时看到的数据底层集合本身（同一份数组）底层集合的*快照副本*或*弱一致视图*
并发修改行为探测到就抛 `ConcurrentModificationException`不抛异常，迭代器仍走原快照
能看到修改后的数据吗可能能（如果没被 fail-fast 打断）看不到（COW）/ 弱一致能看到（CHM）
适用场景单线程；用来快速暴露并发使用错误读多写少并发场景
典型代价依赖 `modCount`，非线程安全（modCount 本身也不是 volatile）写时复制内存翻倍 / 遍历只见旧数据

追问 fail-fast 能 100% 检测到并发修改吗？

**不能，只是概率高**。三种漏检场景：

- **modCount 不是 volatile**：另一个线程改了 `modCount`，当前线程可能还看到旧值。

- **hasNext 提前退出**（上一场景 8 提过的倒数第二个删除坑）。

- **modCount 恰好一致**：一个线程 add，另一个 remove，两次结构修改相互抵消到 `+2`，如果中间没触发 `next`，就检不出来（虽然实际值 `modCount` 确实变了，但只要检查点看到的差值不是 `expectedModCount+k` 就漏）。*严格说这个例子不太现实*，但理论存在。

## 面试场景 10：ArrayList 为什么线程不安全？如何做到线程安全？

🧑‍💻 你

ArrayList 的 `add`、`remove`、`size++` 都**不是原子操作**。多线程同时 `add` 会出这些问题：

- **数据覆盖**：两个线程都读到 `size = 5`，都执行 `elementData[5] = e`，一个覆盖另一个。

- **size 不一致**：`size++` = read/modify/write 三步，多线程下最终 `size` 小于实际 add 次数。

- **ArrayIndexOutOfBoundsException**：一个线程刚扩到 10，另一个线程 `elementData[10] = e` 时数组已经被*它自己*的扩容替换成了新数组（但 `size` 又刚好等于 10）——数组下标可能越界。

- **NPE / 空洞**：多次并发 add 后，中间可能出现`null`洞（因为 `elementData[size++] = e` 拆开来看不是原子的）。

四种线程安全方案：

1. **`Collections.synchronizedList(list)`**：包装类，每个方法内部 `synchronized(mutex)`，简单粗暴。*缺点*：迭代必须*外部*手动 `synchronized`。

2. **`CopyOnWriteArrayList`**：写时复制，读无锁 —— 适合*读远多于写*的场景。*缺点*：每次写都全量 copy 底层数组，内存和 GC 压力大；读到的可能不是最新数据（弱一致）。

3. **`Vector`**：老一辈线程安全 List，方法都加了 `synchronized`。*缺点*：粒度粗、性能差、已经被 JDK 官方建议替代。

4. **手动加锁**：外部 `ReentrantLock` 或 `synchronized(list)`，粒度可控。

追问 `CopyOnWriteArrayList` 的 `add` 大概怎么写？

核心就是*加锁 + 拷贝新数组 + 替换引用*：

```
public boolean add(E e) {
final ReentrantLock lock = this.lock;
lock.lock();
try {
Object[] elements = getArray();
int len = elements.length;
Object[] newElements = Arrays.copyOf(elements, len + 1);   // 全量拷贝
newElements[len] = e;
setArray(newElements);                                     // volatile 写
return true;
} finally {
lock.unlock();
}
}
```

迭代时用的是*迭代器创建时刻的快照数组*，永远不会 CME，也永远看不到迭代开始后的写入 —— 这就是「弱一致性」。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：初始容量 = 0，不是 10（反射看 elementData.length）

```
import java.lang.reflect.Field;
import java.util.ArrayList;

public class InitialCapacityTest {
public static void main(String[] args) throws Exception {
ArrayList<Integer> list = new ArrayList<>();

Field f = ArrayList.class.getDeclaredField("elementData");
f.setAccessible(true);

Object[] arr = (Object[]) f.get(list);
System.out.println("刚 new 完，elementData.length = " + arr.length);   // 0

list.add(1);
arr = (Object[]) f.get(list);
System.out.println("add 一个元素后，elementData.length = " + arr.length); // 10
}
}
```

### 验证 2：观察扩容规律（10 → 15 → 22 → 33 → ...）

```
import java.lang.reflect.Field;
import java.util.ArrayList;

public class GrowRuleTest {
public static void main(String[] args) throws Exception {
ArrayList<Integer> list = new ArrayList<>();
Field f = ArrayList.class.getDeclaredField("elementData");
f.setAccessible(true);

int lastCap = -1;
for (int i = 0; i < 100; i++) {
list.add(i);
int cap = ((Object[]) f.get(list)).length;
if (cap != lastCap) {
System.out.printf("size=%d 触发扩容，新容量=%d%n", i + 1, cap);
lastCap = cap;
}
}
}
}
// 输出：
// size=1  触发扩容，新容量=10
// size=11 触发扩容，新容量=15    (10 + 10>>1 = 10 + 5)
// size=16 触发扩容，新容量=22    (15 + 15>>1 = 15 + 7)
// size=23 触发扩容，新容量=33    (22 + 22>>1 = 22 + 11)
// size=34 触发扩容，新容量=49
// size=50 触发扩容，新容量=73
// size=74 触发扩容，新容量=109
```

### 验证 3：触发 fail-fast 抛 CME

```
import java.util.ArrayList;
import java.util.List;

public class FailFastDemo {
public static void main(String[] args) {
List<Integer> list = new ArrayList<>(List.of(1, 2, 3, 4, 5));

// 方式 A：for-each 中直接 list.remove —— 抛 CME
try {
for (Integer i : list) {
if (i == 2) list.remove(Integer.valueOf(2));
}
} catch (Exception e) {
System.out.println("方式 A: " + e);
// 方式 A: java.util.ConcurrentModificationException
}

// 方式 B：Iterator.remove —— 安全
List<Integer> list2 = new ArrayList<>(List.of(1, 2, 3, 4, 5));
var it = list2.iterator();
while (it.hasNext()) {
if (it.next() == 2) it.remove();
}
System.out.println("方式 B（安全）: " + list2);   // [1, 3, 4, 5]

// 方式 C：removeIf —— 一行搞定
List<Integer> list3 = new ArrayList<>(List.of(1, 2, 3, 4, 5));
list3.removeIf(x -> x == 2);
System.out.println("方式 C（推荐）: " + list3);   // [1, 3, 4, 5]
}
}
```

### 验证 4：「倒数第二个删除」漏检 fail-fast

```
import java.util.ArrayList;
import java.util.List;

public class FailFastMissDemo {
public static void main(String[] args) {
List<Integer> list = new ArrayList<>(List.of(1, 2, 3, 4));
// 删除倒数第二个 (值 3)
for (Integer i : list) {
System.out.println("遍历到 " + i);
if (i == 3) list.remove(Integer.valueOf(3));
}
System.out.println("最终 list = " + list);
// 输出：
// 遍历到 1
// 遍历到 2
// 遍历到 3
// 最终 list = [1, 2, 4]
// 没抛 CME！因为删掉 3 后 size=3，cursor=3，hasNext 返回 false 直接退出。
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `new ArrayList<>()` 后立刻反射看 `elementData.length`，是几？add 一个元素后呢？</summary>

刚 new 完是 **0**（引用指向 `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` 空数组）。add 第一个元素时，`calculateCapacity` 检测到是这个特殊常量，把 minCapacity 提到 `DEFAULT_CAPACITY = 10`，触发 grow 后变成 **10**。

</details>

<details>

<summary>Q2 用一行代码写出 ArrayList 扩容后的新容量。为什么是 1.5 倍不是 2 倍？</summary>

`int newCapacity = oldCapacity + (oldCapacity >> 1);`。选 1.5 倍是*时空平衡*：省内存 + Fibonacci 特性使旧数组内存有机会被下次分配复用，减少碎片。HashMap 用 2 倍是因为要保持 2 的幂做 `hash & (n-1)`，动机完全不同。

</details>

<details>

<summary>Q3 `remove(int index)` 里为什么最后要 `elementData[--size] = null`？</summary>

「删除」只是把后面的元素 `arraycopy` 左移一位，尾部那个位置还持有原对象的强引用，GC 无法回收 → 内存泄漏。手动置 `null` 后引用断开，对象才能被回收。

</details>

<details>

<summary>Q4 描述 fail-fast 的实现原理，并说明为什么 `Iterator.remove()` 不会抛 CME。</summary>

原理：ArrayList 用 `modCount` 记录结构性修改次数；迭代器创建时用 `expectedModCount` 快照；每次 `next()` 前 `checkForComodification()` 比较两者，不一致就抛 CME。
`Iterator.remove()` 内部调外层 `ArrayList.remove(index)`（`modCount` 会自增），然后**立刻 `expectedModCount = modCount`** 同步回来 —— 所以下一次校验依然一致。

</details>

<details>

<summary>Q5 生产上要在遍历时删除 List 的部分元素，你会选哪种写法？为什么不选 for-each + list.remove？</summary>

推荐 **`list.removeIf(predicate)`**（JDK 8+，最简洁且内部安全）或手写 `Iterator.remove()`。不选 for-each + `list.remove()` 是因为它*时对时错*：绝大多数情况下抛 CME，但删「倒数第二个」时又不抛 —— 这种「不确定的错」比稳定报错更危险，测试可能漏过、上线才炸。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.util.ArrayList` API —— 官方 API 文档

- JDK 21 · `ConcurrentModificationException` —— 官方对 fail-fast 的定义

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0012：**LinkedList 源码分析 —— 双向链表、Node 结构、addFirst/addLast、为什么 LinkedList 不支持 RandomAccess？** 会和 ArrayList 做完整对照，帮你彻底记住「什么时候选 ArrayList、什么时候选 LinkedList」（剧透：绝大多数场景都该选 ArrayList）。

💬 有任何疑问 —— 「扩容 1.5 倍那段位运算能不能画个图？」「fail-fast 的漏检真会在生产上出问题吗？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


