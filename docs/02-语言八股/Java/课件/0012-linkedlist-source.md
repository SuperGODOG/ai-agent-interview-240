> Lesson 0012 · 阶段二 · 集合框架 · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 6 个追问

# 0012 · LinkedList 源码分析 & Deque 定位

这一课要打破一个几乎所有初学者都有的错觉 ——「LinkedList 的插入删除比 ArrayList 快」。**这句话在大多数情况下是错的**。LinkedList 面试题看似简单：底层是双向链表、插入 O(1)、随机访问 O(n)……但只要面试官顺手一句「那 `list.add(500, x)` 是什么复杂度？」，或者「你们项目里哪儿用了 LinkedList？」，很多人就答不上来。

本课对齐 ，把 LinkedList 的每一个关键源码方法都拆开看一遍，然后落到最重要的一个问题：**在 2026 年的真实业务里，你还有理由选 LinkedList 吗？**（提示：几乎没有。）

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 LinkedList 是单向链表还是双向链表？头尾各有几个指针？</summary>

**双向链表**。每个 `Node` 有 `prev` 和 `next` 两个指针；LinkedList 本体维护 `first` 和 `last` 两个指针分别指向头尾，所以头尾两端操作都是 O(1)。

</details>

<details>

<summary>Q0.2 `linkedList.get(500)` 的时间复杂度是 O(1) 还是 O(n)？</summary>

**O(n)**。链表不能像数组那样按下标偏移，必须从头（或从尾，见下面 `node(int)` 优化）遍历。这是 LinkedList 相比 ArrayList 最大的性能劣势。

</details>

## 面试场景 1：LinkedList 的底层数据结构？

🎤 面试官

说说 LinkedList 的底层数据结构，它实现了哪些接口？

🧑‍💻 你

LinkedList 底层是 **双向链表（doubly-linked list）**。类签名是：

```
public class LinkedList<E>
extends AbstractSequentialList<E>
implements List<E>, Deque<E>, Cloneable, java.io.Serializable
```

两个关键点：

- 继承 `AbstractSequentialList`（而不是 ArrayList 继承的 `AbstractList`）—— 这个抽象类的定位就是「顺序访问型」列表，随机访问要靠迭代器实现。

- 同时实现 `List` 和 `Deque` —— 这就是 LinkedList 存在感的一半：它可以当作双端队列/栈/普通队列用。

核心字段：

```
transient int size = 0;
transient Node<E> first;   // 头指针
transient Node<E> last;    // 尾指针

private static class Node<E> {
E item;
Node<E> next;
Node<E> prev;

Node(Node<E> prev, E element, Node<E> next) {
this.item = element;
this.next = next;
this.prev = prev;
}
}
```

加上从 `AbstractList` 继承来的 `modCount`（fail-fast 用）—— 一个 LinkedList 实例的所有状态就这些。

追问 LinkedList 有没有实现 `RandomAccess`？为什么？

**没有**。`RandomAccess` 是一个空标记接口，含义是「实现类支持 O(1) 随机访问」。LinkedList 是链表，按下标访问必须遍历，所以不能声明这个接口。`Collections.binarySearch`、`Collections.shuffle` 等工具方法会用 `instanceof RandomAccess` 判断，走不同分支：ArrayList 走下标循环，LinkedList 走迭代器循环。

## 面试场景 2：LinkedList 的 add(int, e) 是 O(1) 吗？⭐核心陷阱

🎤 面试官

大家都说 LinkedList 的插入是 O(1)。那我问你，`list.add(500, "x")`（假设 list 大小是 1000）的时间复杂度是多少？

🧑‍💻 你

**不是 O(1)，是 O(n)**。这是初学者最容易被绕进去的陷阱。看源码：

```
public void add(int index, E element) {
checkPositionIndex(index);
if (index == size)
linkLast(element);                 // 尾部插入：O(1)
else
linkBefore(element, node(index));  // 中间插入：先要定位到 index
}
```

关键在 `node(index)` —— 它必须先**遍历链表**找到第 index 个节点，才能拿到指针做「断链-接链」。`linkBefore` 这一步本身确实是 O(1)（几行赋值），但 `node(index)` 是 O(n)，整体就是 O(n)。

所以严格的表述是：

- **头/尾插入删除**（`addFirst/addLast/removeFirst/removeLast`）：真正的 O(1)。

- **已经拿到 Node 引用**的中间插入删除：O(1)。

- **按下标**的中间插入删除：*定位 O(n) + 断链 O(1) = O(n)*。

陷阱 「LinkedList 插入删除比 ArrayList 快」是**不严谨**的说法。ArrayList 中间插入的开销是「定位 O(1) + 数组搬移 O(n)」；LinkedList 中间插入的开销是「定位 O(n) + 断链 O(1)」—— 两者都是 O(n)，实际测下来 ArrayList 因为内存连续、可以用 `System.arraycopy`（底层 memcpy），常常还更快。LinkedList 只有在**头部插入**这一个具体场景下明显赢。

追问 LinkedList 相比 ArrayList 到底「插入」快在哪？

快在**已经定位到位置**之后的插入是 O(1)（改几个指针就行）；ArrayList 定位后还得搬移 index 之后的所有元素。但「定位」本身，LinkedList 是 O(n)、ArrayList 是 O(1)。所以只有**头部插入**（`addFirst`，定位 O(1)）或者**用迭代器边遍历边插入**（定位摊销 O(1)）这两个场景，LinkedList 才有优势。

## 面试场景 3：LinkedList 的 get(i) 是几阶？

🧑‍💻 你

**O(n)**。源码：

```
public E get(int index) {
checkElementIndex(index);
return node(index).item;
}
```

核心是 `node(index)`，见下一题。

这意味着一段看起来无害的代码可能是灾难：

```
// ❌ 反面教材：O(n²) 遍历
LinkedList<String> list = ...;
for (int i = 0; i < list.size(); i++) {
System.out.println(list.get(i));   // 每次 get 都 O(n)
}
```

正确写法是**用迭代器 / for-each**：

```
// ✅ 正确：O(n) 遍历
for (String s : list) {
System.out.println(s);
}
```

追问 如果用 `for (int i=0; i<n; i++) list.get(i)` 去遍历 LinkedList，复杂度是多少？

**O(n²)**。每次 `get(i)` 都要从头/尾遍历到第 i 个节点，n 次调用总代价是 `n × n/2 = O(n²)`。LinkedList 上跑 for-i 循环，1 万个元素就要 5000 万次指针跳转 —— 缓存又不友好，性能会非常糟糕。这是新手用 LinkedList 最典型的性能事故。

## 面试场景 4：LinkedList 的 remove(int) 和 remove(Object) 有什么区别？

🧑‍💻 你

方法签名相似，语义完全不同：

- `remove(int index)`：**按索引**删除。先 `node(index)` 定位到节点（O(n)），再 `unlink`（O(1)）。

- `remove(Object o)`：**按 equals 删除首个匹配项**。从 `first` 开始遍历，逐个 `equals` 比较（O(n) 查找 + O(1) 断链）。

```
public boolean remove(Object o) {
if (o == null) {
for (Node<E> x = first; x != null; x = x.next) {
if (x.item == null) { unlink(x); return true; }
}
} else {
for (Node<E> x = first; x != null; x = x.next) {
if (o.equals(x.item)) { unlink(x); return true; }
}
}
return false;
}
```

注意 `null` 单独处理（用 `==` 比较），因为 `o.equals(null)` 有 NPE 风险。这是 JDK 集合里的通用套路。

`unlink` 本身很短，就是把待删节点的前驱后继串起来，再置空引用帮 GC：

```
E unlink(Node<E> x) {
final E element = x.item;
final Node<E> next = x.next;
final Node<E> prev = x.prev;

if (prev == null) first = next;
else { prev.next = next; x.prev = null; }

if (next == null) last = prev;
else { next.prev = prev; x.next = null; }

x.item = null;
size--;
modCount++;
return element;
}
```

陷阱 `list.remove(1)` 到底调用哪个重载？**调用 `remove(int)`**，因为编译器在选重载时优先精确匹配 `int`。想调 `remove(Object)` 必须显式装箱：`list.remove(Integer.valueOf(1))`。这个坑 ArrayList 也一样，面试很爱问。

## 面试场景 5：node(int) 的二分方向优化

🎤 面试官

你说 `get(i)` 是 O(n)。那 LinkedList 就是老老实实从头遍历吗？

🧑‍💻 你

不是。`node(int)` 做了一个**双向链表的天然优化**：判断 index 靠近头还是靠近尾，从近的一端出发。

```
Node<E> node(int index) {
if (index < (size >> 1)) {          // index 在前半段
Node<E> x = first;
for (int i = 0; i < index; i++)
x = x.next;
return x;
} else {                                // index 在后半段
Node<E> x = last;
for (int i = size - 1; i > index; i--)
x = x.prev;
return x;
}
}
```

`size >> 1` 就是 `size / 2`（位运算更快，也是 JDK 惯例）。这样最坏情况从 O(n) 优化到 **O(n/2)**，平均遍历 n/4 个节点。渐近复杂度还是 O(n)，但常数减半。

这也解释了为什么 LinkedList 是*双向*而不是单向 —— 单向链表做不了这个优化。

追问 为什么用 `size >> 1` 而不是 `size / 2`？

本质上编译器会把 `size / 2` 优化成移位（对无符号或已知正数的除以 2 的幂），两者字节码几乎相同。JDK 源码大量使用移位是**历史与风格惯例**：早期 JIT 优化没这么强，直接写 `>>` 更保险；同时移位一眼就能看出是「除以 2」的意图。今天写业务代码用 `/ 2` 完全可以，可读性更好。

## 面试场景 6：ArrayList vs LinkedList 什么场景选哪个？⭐核心

🎤 面试官

你们项目里用 ArrayList 还是 LinkedList？为什么？

🧑‍💻 你

**几乎永远选 ArrayList**。对比表：

维度ArrayListLinkedList

底层结构动态数组 `Object[]`双向链表 `Node<E>`
随机访问 `get(i)`O(1)O(n)，双向优化后平均 n/4
头部插入 `add(0, x)`O(n)（要搬移全部）O(1) ✅
尾部插入 `add(x)`均摊 O(1)（偶尔扩容）O(1)
中间按下标插入O(n)（定位 O(1) + 搬移 O(n)）O(n)（定位 O(n) + 断链 O(1)）
迭代器遍历快（内存连续，缓存友好）慢（Node 分散，缓存失效）
内存占用紧凑（元素 + 少量空槽）大约 3-4 倍（对象头 + prev/next）
实现 RandomAccess是否
实现 Deque否是
典型场景**几乎所有 List 场景**基本没有，除非兼容旧接口

🧑‍💻 你

结论很干脆：**业务代码里遇到 `List` 需求，无脑用 ArrayList**。理由：

1. ArrayList 的「插入慢」是理论上的 O(n)，实际由 `System.arraycopy`（JNI/memcpy）实现，常数极小。

2. LinkedList 的「插入快」只在*头部*成立；中间插入既没优势，还带来遍历慢、内存大的代价。

3. 现代 CPU 有很强的**预取**（prefetch）和多级缓存 —— ArrayList 连续内存是最友好的形态。

追问 Josh Bloch（LinkedList 作者、《Effective Java》作者）自己都说不推荐 LinkedList，为什么？

他在多次演讲和 Twitter 上说过大意：「Does anyone actually use LinkedList? I wrote it, and I never use it.」原因就是**现代 CPU 的缓存友好性**压倒了链表在算法书里的理论优势。链表每个节点是独立堆分配对象，物理地址完全散乱，遍历时几乎每次访问都是一次缓存 miss；而数组是一整块连续内存，CPU 预取直接把后面若干元素都拉进 L1 缓存。同样是 O(n) 遍历，实测 ArrayList 通常快数倍甚至十几倍。

追问 LinkedList 内存开销比 ArrayList 大多少？

ArrayList 每存一个 `Object`，实际占 **1 个引用**（4 或 8 字节，加上偶尔的空槽）。LinkedList 每存一个 `Object`，要创建一个 `Node`：**对象头（12 或 16 字节）+ item 引用 + prev 引用 + next 引用**，还要考虑对齐填充 —— 一个 Node 通常占 32 字节以上。所以粗算 LinkedList 内存开销是 ArrayList 的 **3-4 倍**。存一千万个 Long？ArrayList 约 80 MB，LinkedList 可能要 300+ MB。

## 面试场景 7：LinkedList 实现了 Deque，能当栈/队列用

🧑‍💻 你

因为实现了 `Deque`，LinkedList 提供了完整的双端操作，一份 API 三种角色：

- **队列（FIFO）**：`offer(e)` 尾部入队 / `poll()` 头部出队 / `peek()` 看头。

- **栈（LIFO）**：`push(e)` 头部压栈（内部调 `addFirst`）/ `pop()` 头部弹栈 / `peek()` 看栈顶。

- **双端队列**：`offerFirst/offerLast`、`pollFirst/pollLast`、`peekFirst/peekLast`。

但今天要提栈或队列，**首选不是 LinkedList**：

- 需要栈 → 用 `ArrayDeque`（不要用祖传的 `Stack`，那玩意继承自 `Vector`，方法全 synchronized，性能差还有语义坑）。

- 需要普通队列 → 用 `ArrayDeque`。

- 需要阻塞队列 → 用 `ArrayBlockingQueue` / `LinkedBlockingQueue`（第 0017 课细讲）。

- 需要优先队列 → `PriorityQueue`。

追问 ArrayDeque vs LinkedList，谁做 Deque 更好？

**ArrayDeque 更好**。ArrayDeque 底层是**循环数组**（capacity 是 2 的幂，用位运算算索引，头尾指针环绕），没有 Node 对象开销、缓存友好、扩容摊销 O(1)。`Deque` 接口文档明确推荐：「ArrayDeque is likely to be faster than `Stack` when used as a stack, and faster than LinkedList when used as a queue.」唯一 LinkedList 略胜的场景是*你就是要一个 List + Deque 双身份*的对象，但这种需求几乎不存在。

## 面试场景 8：为什么 LinkedList 遍历比 ArrayList 慢很多？

🧑‍💻 你

核心原因是 **CPU 缓存局部性**。

- **ArrayList**：底层是 `Object[]`，元素引用连续存放在一段内存里。CPU 从内存读一个元素时会一次性把附近的一整个 cache line（64 字节）拉进 L1 缓存 —— 相邻的下 7~15 个引用就*已经在缓存里了*。遍历时几乎全是缓存命中。

- **LinkedList**：每个 `Node` 是独立 `new` 出来的对象，物理地址完全散乱（GC 移动后可能更乱）。遍历时 `x = x.next` 是一次**指针追踪（pointer chasing）**，几乎每一步都是缓存 miss，甚至可能触发 TLB miss。

结果就是：同样是 O(n) 遍历，实测 ArrayList 常常快 **5-10 倍**甚至更多。渐近复杂度一样，常数差着数量级。

陷阱 面试时如果只说「LinkedList 遍历是 O(n)，跟 ArrayList 一样」，会显得没深度。加上「但因为链表节点内存不连续，缓存命中率极差，实测常常比 ArrayList 慢一个数量级」，档次立刻上去。

## 面试场景 9：LinkedList 的 fail-fast 也有 modCount 吗？

🧑‍💻 你

有。`modCount` 是从** `AbstractList`** 继承来的（`AbstractSequentialList` 继承自 `AbstractList`）。所有会改变结构的方法（`linkFirst`、`linkLast`、`linkBefore`、`unlink`、`clear` 等）内部都会 `modCount++`。

迭代器（`ListItr`）在创建时把当前 `modCount` 保存为 `expectedModCount`，每次 `next`/`previous`/`remove`/`set` 都会调 `checkForComodification`：

```
final void checkForComodification() {
if (modCount != expectedModCount)
throw new ConcurrentModificationException();
}
```

所以在遍历过程中，如果*别的线程*或*当前线程绕过迭代器*直接调 `list.add/remove`，下一次迭代器操作就会抛 `ConcurrentModificationException`。

唯一安全的边遍历边删除方式是**用迭代器自己的 `remove()`**，它会同步更新 `expectedModCount`。

## 面试场景 10：实际生产中还有用 LinkedList 的场景吗？

🎤 面试官

你实际项目里用过 LinkedList 吗？什么场景？

🧑‍💻 你

诚实地回答：**几乎没有**。可以按需求给出替代方案：

- 需要 `Deque`（双端队列/栈）→ **`ArrayDeque`**。

- 需要阻塞队列 → **`ArrayBlockingQueue`**（有界）或 **`LinkedBlockingQueue`**（可选无界）。

- 需要并发无锁队列 → **`ConcurrentLinkedQueue`**（虽然名字含 Linked，但内部是特殊的 CAS 单向链表，跟 LinkedList 无关）。

- 需要 LRU 缓存 → **`LinkedHashMap`**（另一种链表 + 哈希）。

- 只是一个普通 List → **`ArrayList`**。

LinkedList 今天更多是**历史遗留**和**接口兼容**的存在 —— 某个老接口返回 `LinkedList`，或者某段老代码写了 `new LinkedList()`，没人愿意去改。真正的新代码，几乎不会主动 `new LinkedList()`。

面试时能大胆说出这个结论，反而会显得你有独立思考，不是背书式回答。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：手动模拟 LinkedList 内部 Node 结构

```
// 亲手实现一个极简双向链表，感受 LinkedList 的骨架
public class TinyLinkedList<E> {
private static class Node<E> {
E item;
Node<E> prev, next;
Node(Node<E> p, E e, Node<E> n) { prev = p; item = e; next = n; }
}

private Node<E> first, last;
private int size = 0;

public void addLast(E e) {
Node<E> l = last;
Node<E> newNode = new Node<>(l, e, null);
last = newNode;
if (l == null) first = newNode;
else l.next = newNode;
size++;
}

public void addFirst(E e) {
Node<E> f = first;
Node<E> newNode = new Node<>(null, e, f);
first = newNode;
if (f == null) last = newNode;
else f.prev = newNode;
size++;
}

public E get(int index) {
// 二分方向优化
Node<E> x;
if (index < (size >> 1)) {
x = first;
for (int i = 0; i < index; i++) x = x.next;
} else {
x = last;
for (int i = size - 1; i > index; i--) x = x.prev;
}
return x.item;
}

public int size() { return size; }

public static void main(String[] args) {
TinyLinkedList<String> list = new TinyLinkedList<>();
list.addLast("A"); list.addLast("B"); list.addLast("C");
list.addFirst("Z");
// 现在链表是：Z <-> A <-> B <-> C
for (int i = 0; i < list.size(); i++)
System.out.print(list.get(i) + " ");   // Z A B C
}
}
```

### 验证 2：用 LinkedList 当栈（LIFO）

```
import java.util.LinkedList;
import java.util.Deque;

public class LinkedListAsStack {
public static void main(String[] args) {
Deque<Integer> stack = new LinkedList<>();
stack.push(1);       // 内部 addFirst
stack.push(2);
stack.push(3);
System.out.println(stack.peek());  // 3  ← 栈顶
System.out.println(stack.pop());   // 3  ← 弹栈
System.out.println(stack.pop());   // 2
System.out.println(stack.peek());  // 1
// 生产环境请改用：Deque<Integer> stack = new ArrayDeque<>();
}
}
```

### 验证 3：用 LinkedList 当队列（FIFO）

```
import java.util.LinkedList;
import java.util.Queue;

public class LinkedListAsQueue {
public static void main(String[] args) {
Queue<String> queue = new LinkedList<>();
queue.offer("first");    // 尾部入队
queue.offer("second");
queue.offer("third");
System.out.println(queue.peek());  // first  ← 队首
System.out.println(queue.poll());  // first  ← 出队
System.out.println(queue.poll());  // second
// 生产环境同样推荐：Queue<String> queue = new ArrayDeque<>();
}
}
```

### 验证 4：ArrayList vs LinkedList 遍历性能对比

```
import java.util.*;

public class TraverseBenchmark {
public static void main(String[] args) {
int n = 1_000_000;
List<Integer> arr = new ArrayList<>(n);
List<Integer> lnk = new LinkedList<>();
for (int i = 0; i < n; i++) { arr.add(i); lnk.add(i); }

// for-each（迭代器）遍历
long t1 = System.nanoTime();
long s1 = 0; for (int x : arr) s1 += x;
long t2 = System.nanoTime();
long s2 = 0; for (int x : lnk) s2 += x;
long t3 = System.nanoTime();

System.out.printf("ArrayList  for-each: %.2f ms%n", (t2 - t1) / 1e6);
System.out.printf("LinkedList for-each: %.2f ms%n", (t3 - t2) / 1e6);
// 典型输出：ArrayList ~5ms，LinkedList ~30ms（差 5-10 倍）
}
}
```

### 验证 5：用 for-i 遍历 LinkedList 的灾难性能

```
import java.util.LinkedList;

public class LinkedListForIndexTrap {
public static void main(String[] args) {
LinkedList<Integer> list = new LinkedList<>();
for (int i = 0; i < 50_000; i++) list.add(i);

long t1 = System.nanoTime();
long sum = 0;
for (int i = 0; i < list.size(); i++) sum += list.get(i);  // ❌ O(n²)
long t2 = System.nanoTime();
System.out.printf("for-i get(i): %.2f ms%n", (t2 - t1) / 1e6);
// 50000 个元素约 500-2000 ms

long t3 = System.nanoTime();
long sum2 = 0;
for (int x : list) sum2 += x;  // ✅ O(n)
long t4 = System.nanoTime();
System.out.printf("for-each:     %.2f ms%n", (t4 - t3) / 1e6);
// for-each 约 1-5 ms
}
}
```

跑一次这段代码，for-i 和 for-each 的差距会给你留下终身印象。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 LinkedList 的 `add(int index, E e)` 是不是 O(1)？为什么？</summary>

**不是，是 O(n)**。虽然「断链-接链」只要 O(1)，但源码里必须先调 `node(index)` 从头/尾遍历定位到目标节点，定位本身就是 O(n)。只有 `addFirst`、`addLast`（或用迭代器边遍历边插入）才是真正的 O(1)。

</details>

<details>

<summary>Q2 `node(int index)` 的核心优化是什么？</summary>

**二分方向优化**：判断 `index < (size >> 1)`，如果 index 在前半段就从 `first` 向后遍历，否则从 `last` 向前遍历。平均遍历 n/4 个节点。渐近复杂度仍是 O(n)，但常数减半。这也是链表设计成双向的一个动机。

</details>

<details>

<summary>Q3 ArrayList 和 LinkedList，业务代码应该优先选哪个？为什么？</summary>

**绝大多数场景选 ArrayList**。三点原因：（1）ArrayList 内存连续，CPU 缓存友好，实测遍历常常比 LinkedList 快 5-10 倍；（2）ArrayList 单个元素内存开销小得多，LinkedList 每个 Node 还带 prev/next 引用和对象头，大约 3-4 倍；（3）ArrayList 用 `System.arraycopy` 做搬移，常数极小。LinkedList 唯一优势是**头部插入 O(1)**，但这个需求可以用 `ArrayDeque` 满足得更好。

</details>

<details>

<summary>Q4 ArrayDeque 相比 LinkedList，做 Deque 有什么优势？</summary>

ArrayDeque 底层是**循环数组**（capacity 为 2 的幂，用位运算算索引），头尾指针环绕。相比 LinkedList：（1）没有 Node 对象，内存开销小得多；（2）内存连续，缓存友好，遍历快；（3）扩容也是摊销 O(1)。`Deque` 官方文档明确推荐：作为栈用比 `Stack` 快，作为队列用比 `LinkedList` 快。

</details>

<details>

<summary>Q5 `list.remove(1)` 到底删的是什么？如果 list 是 `LinkedList<Integer>`，怎么按值删除元素 1？</summary>

`list.remove(1)` 调用的是 **`remove(int index)`**，删除的是「下标为 1」的元素 —— 因为编译器优先精确匹配 `int`。想按值删除元素 1，必须显式装箱：`list.remove(Integer.valueOf(1))`，才会走 `remove(Object)` 重载。这个坑 ArrayList 和 LinkedList 通用，面试非常爱问。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.util.LinkedList` API

- JDK 21 · `java.util.ArrayDeque` API —— 官方推荐的 Deque 首选

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0013：**HashMap 源码分析** —— 阶段二绝对的重头戏，链表 + 红黑树 + 扩容 + 死循环历史坑，一课讲透。

💬 有任何疑问 ——「为什么 LinkedList 作者自己都不用它？」「面试真被追问过 LinkedList 迭代器怎么实现，怎么答？」「ArrayDeque 循环数组扩容具体怎么做？」—— 直接问我。我是你的老师，也是你的追问陪练。


