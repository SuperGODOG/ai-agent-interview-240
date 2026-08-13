> Lesson 0038 · 阶段五 · IO · ⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0038 · Java IO 基础 & 设计模式（装饰器/适配器/工厂）

欢迎来到**阶段五 · IO**。这一阶段是网络编程（Netty、Tomcat、Dubbo）和文件处理的地基，也是很多人「看得懂但写不好」的重灾区 —— 类多、名字长、组合花样多，一不小心就写出 `new BufferedInputStream(new DataInputStream(new FileInputStream(...)))` 这种嵌套长龙。

本课把两篇  原文合并：先讲 **Java IO 基础**（），把四大抽象类 + 字节字符流 + 桥接 + Buffered 这些基本盘补齐；再讲 **Java IO 里的设计模式**（），看清嵌套长龙背后的*装饰器*、*适配器*、*工厂*三张面孔。基础打好之后，第 0039 课讲 IO 模型（BIO/NIO/AIO），第 0040 课深入 NIO 三大件（Buffer/Channel/Selector）。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `InputStream` 和 `Reader` 有什么区别？</summary>

`InputStream` 是**字节流**基类，每次读一个 `byte`（0-255）；`Reader` 是**字符流**基类，每次读一个 `char`（Java 里是 UTF-16 code unit），构造时可以指定 **Charset** 自动做编码转换。处理二进制（图片、音频）用前者，处理文本用后者。第 2 题详解。

</details>

<details>

<summary>Q0.2 `BufferedInputStream` 用了什么设计模式？</summary>

**装饰器模式**。它继承自 `FilterInputStream`（进而继承 `InputStream`），构造时接收另一个 `InputStream` 并在其外面「套一层」缓冲区。这样可以任意组合：`BufferedInputStream` 既能装饰 `FileInputStream`，也能装饰 `SocketInputStream`、`ZipInputStream`...。第 5 题细讲。

</details>

## 面试场景 1：Java IO 是怎么分类的？

🎤 面试官

你能说说 Java IO 库这么多类，是按什么维度组织的吗？

🧑‍💻 你

Java IO 类库主要按**三个维度**切分：

- **按方向**：输入（`Input`/`Reader`，从外部读到内存）、输出（`Output`/`Writer`，从内存写到外部）。

- **按操作单位**：字节流（`InputStream`/`OutputStream`，处理 `byte`）、字符流（`Reader`/`Writer`，处理 `char`）。

- **按功能层次**：*节点流*（直接对接数据源，如 `FileInputStream`、`ByteArrayInputStream`）、*处理流*（在节点流外面包一层，加缓冲/加数据格式/加压缩，如 `BufferedInputStream`、`DataInputStream`）。

三个维度交叉，形成 `java.io` 包里几十个类的矩阵。记忆的关键不是背类名，而是**沿这三个维度定位**：我要「读」还是「写」？处理「字节」还是「字符」？需不需要「加功能」？

追问 那 NIO 和 IO 是什么关系？

NIO（`java.nio`，New IO）是 JDK 1.4 引入的新 API，核心概念是 **Buffer + Channel + Selector**，支持非阻塞和多路复用。它*不是替代 IO*，而是补充 —— 面向**高并发网络场景**。传统 `java.io`（BIO）现在仍然是最常用的文件处理方式。第 0039、0040 课细讲。

## 面试场景 2：字节流 vs 字符流有什么区别？★经典

🎤 面试官

为什么 Java 既提供了 `InputStream` 又提供了 `Reader`？直接用字节流不行吗？

🧑‍💻 你

技术上「只有字节流」也能干活 —— 毕竟磁盘、网络本来就只传字节。但 Java 单独设计字符流有**两个理由**：

1. **处理编码更方便**。字节流读中文得自己拿 `String(byte[], Charset)` 解码；字符流构造时传 `Charset`，读进来直接就是 `char`，中间的字节→字符转换由 `StreamDecoder` 内部完成。

2. **避免乱码**。字节流一次读固定字节数，如果一个 UTF-8 中文字符占 3 字节而缓冲区边界正好在字符中间，就会切出「半个字」—— 拼起来看就是乱码。字符流按 *字符* 边界读，天然不会切坏。

维度字节流字符流

基类`InputStream` / `OutputStream``Reader` / `Writer`
操作单位`byte`（8 位）`char`（16 位 UTF-16）
编码处理需手动转构造时指定 Charset 自动转
适用场景图片、音视频、压缩包等二进制文本文件（.txt、.json、.log）

追问 `InputStream.read()` 返回 `int` 而不是 `byte` 为什么？

`byte` 在 Java 里是有符号的，取值范围 **-128 ~ 127**。如果 `read()` 返回 `byte`，就没有一个「不在 byte 范围里」的值可以用来表示 **EOF（读到末尾）** —— 用 `-1` 表示 EOF 会和真实字节 `0xFF`（补码 -1）撞车，分不清是数据还是结束。所以规范让 `read()` 返回 `int`：*0-255* 表示真实字节（无符号），*-1* 专门表示 EOF。`Reader.read()` 同理，返回 `int`：0-65535 表示 `char`，-1 表示 EOF。

陷阱 `FileReader` 默认用**平台默认字符集**（Windows 中文常常是 GBK，Linux/Mac 是 UTF-8）—— 跨平台读文件是乱码常客。JDK 11 开始 `FileReader` 才支持传 `Charset` 参数，之前只能用 `new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8)`。生产代码**永远显式指定编码**，别信默认值。

## 面试场景 3：IO 的四大抽象基类是哪些？

🧑‍💻 你

`java.io` 的顶层设计围绕四个抽象类展开：

基类方向 / 单位关键抽象方法典型实现

`InputStream`字节读`int read()``FileInputStream`、`ByteArrayInputStream`、`BufferedInputStream`、`DataInputStream`、`ObjectInputStream`
`OutputStream`字节写`void write(int b)``FileOutputStream`、`ByteArrayOutputStream`、`BufferedOutputStream`、`DataOutputStream`、`PrintStream`
`Reader`字符读`int read(char[], int, int)``FileReader`、`InputStreamReader`、`BufferedReader`、`CharArrayReader`
`Writer`字符写`void write(char[], int, int)``FileWriter`、`OutputStreamWriter`、`BufferedWriter`、`PrintWriter`

命名有规律：以 `File-` 开头的是**文件节点流**；以 `ByteArray-`/`CharArray-` 开头的对接内存数组；以 `Buffered-`/`Data-`/`Object-`/`Print-` 开头的是**处理流**（装饰器）；`InputStreamReader`/`OutputStreamWriter` 是**桥接**（适配器）。看到一个新类名，往这四类里对号入座就行。

追问 `System.out` 是什么类型？`println` 从哪来？

`System.out` 是 `PrintStream` 类型（`OutputStream` 的子类），封装了标准输出的字节流并加了**格式化打印**能力：`println`、`printf`、`print(int)`/`print(double)`... 都是 `PrintStream` 提供的。等价的字符流版本是 `PrintWriter`，写文本文件更推荐用后者。

## 面试场景 4：字节流怎么转字符流？`InputStreamReader` / `OutputStreamWriter`

🎤 面试官

我手里有一个 `InputStream`（比如网络的 `Socket.getInputStream()`），但我想按字符读取，怎么办？

🧑‍💻 你

用**桥接类** `InputStreamReader`。它继承 `Reader`，构造时接收一个 `InputStream` 和一个 `Charset`，内部持有 `StreamDecoder` 负责把字节流按指定编码解码成字符流：

```
InputStream in = socket.getInputStream();
Reader reader = new InputStreamReader(in, StandardCharsets.UTF_8);
// 之后就能按 char 读了，通常再套一层 BufferedReader 拿 readLine()
BufferedReader br = new BufferedReader(reader);
String line = br.readLine();
```

写端对称：`OutputStreamWriter` 把 `Writer` 的 `char` 编码成 `byte`，写进底层 `OutputStream`。

这两个类是**整个 IO 体系里字节世界和字符世界的唯一桥梁** —— `FileReader` 内部其实也是 `InputStreamReader`，`BufferedReader` 也得先套一层 `InputStreamReader` 才能对接 `InputStream`。

追问 不传 `Charset` 会怎样？

使用**平台默认字符集**（`Charset.defaultCharset()`）。Windows 中文版是 `GBK`、Linux/Mac 通常是 `UTF-8`。跨环境几乎必然踩乱码坑。规则很简单：**永远显式传 `StandardCharsets.UTF_8`**，除非你有极强的理由。JDK 18 起 `file.encoding` 默认改成了 UTF-8（JEP 400），但兼容旧环境还是要显式指定。

## 面试场景 5：装饰器模式在 IO 里怎么用？★核心

🎤 面试官

你刚提到 `BufferedInputStream` 是装饰器。能具体讲讲装饰器模式在 Java IO 里的应用吗？

🧑‍💻 你

**装饰器模式**的核心是：*装饰器和被装饰对象继承同一个抽象类*，装饰器持有被装饰对象的引用，转发调用的同时增加自己的功能。这样可以「层层套娃」组合出任意能力。

Java IO 里的装饰器基类是 `FilterInputStream` / `FilterOutputStream`（以及对应的 `FilterReader`/`FilterWriter`）。它们本身也继承 `InputStream`，构造时接收一个 `InputStream`：

```
public class FilterInputStream extends InputStream {
protected volatile InputStream in;   // ← 被装饰对象
protected FilterInputStream(InputStream in) { this.in = in; }
public int read() throws IOException { return in.read(); }  // 默认转发
}
```

常见装饰器：

- `BufferedInputStream`：加**缓冲**，减少系统调用次数。

- `DataInputStream`：加**数据格式**能力，`readInt()`/`readUTF()`/`readLong()` 直接读基本类型。

- `ObjectInputStream`：加**对象反序列化**能力，`readObject()`（历史包袱，不推荐用）。

- `ZipInputStream`、`GZIPInputStream`：加**解压**能力（严格说 `ZipInputStream` 继承 `InflaterInputStream`，不走 `FilterInputStream`，但也是装饰器思想）。

典型嵌套：

```
DataInputStream dis = new DataInputStream(
new BufferedInputStream(
new FileInputStream("data.bin")));
int x = dis.readInt();     // 从文件读 → 走缓冲 → 按 int 解析
```

追问 为什么 IO 到处都用装饰器？换成继承体系不行吗？

**会类爆炸**。设想一下：想给 `FileInputStream`、`SocketInputStream`、`ByteArrayInputStream`、`PipedInputStream`...（M 个数据源）加上「缓冲」「数据格式」「加密」「压缩」...（N 个功能），如果走继承，就得写出 `BufferedFileInputStream`、`BufferedSocketInputStream`、`DataBufferedFileInputStream`、`EncryptedBufferedZipFileInputStream`... 数量爆炸到 `2^N × M`。装饰器让每种功能只写一个类，总共 `M + N` 个，任意组合。

追问 `BufferedInputStream` 到底比 `FileInputStream` 快多少？

逐字节 `read()` 场景下能差**几十到几百倍**。 原文测过 524.9 MB 的文件：`BufferedInputStream` 15 秒，裸 `FileInputStream` 2555 秒（165 倍）。原因是*系统调用开销* —— 每次 `FileInputStream.read()` 都要陷入内核走一次 `read(2)`；`BufferedInputStream` 一次读 8 KB 到内存缓冲，之后 8192 次读都在用户态直接切数组。反过来，如果你已经用 `read(byte[8192])` 一次读 8 KB 数组，Buffered 的优势就微乎其微了。

## 面试场景 6：适配器模式在 IO 里怎么用？

🧑‍💻 你

**适配器模式**的核心是：*把一个接口转换成另一个接口*，让原本不兼容的类能协作。IO 里最经典的适配器就是** `InputStreamReader` **—— 它把「字节流接口」（`InputStream`）适配成了「字符流接口」（`Reader`）：

```
public class InputStreamReader extends Reader {   // ← 目标接口
private final StreamDecoder sd;                // ← 内部真正干活的
public InputStreamReader(InputStream in) {     // ← 被适配对象
sd = StreamDecoder.forInputStreamReader(in, this, (String) null);
}
public int read() throws IOException { return sd.read(); }
}
```

调用方拿到 `Reader`，感觉自己在用字符流；底层其实还是字节流 + `StreamDecoder` 做编码转换。`OutputStreamWriter` 对称：把 `Writer` 适配到 `OutputStream`。

追问 装饰器和适配器都是「包一层」，本质区别是什么？

看**接口是否变化**：装饰器包完之后接口*不变*（`BufferedInputStream` 还是 `InputStream`），目的是**增强功能**；适配器包完之后接口*变了*（`InputStreamReader` 从 `InputStream` 变成 `Reader`），目的是**兼容对接**。附带区别：装饰器天然支持嵌套（因为接口不变），适配器一般不嵌套。

## 面试场景 7：工厂模式在 IO 里怎么用？

🧑‍💻 你

NIO2 引入的 `java.nio.file.Files` 工具类里，大量使用**静态工厂**：

```
Path p = Paths.get("data.txt");
InputStream in  = Files.newInputStream(p);              // 工厂方法
OutputStream out = Files.newOutputStream(p);
BufferedReader br = Files.newBufferedReader(p, UTF_8);
Stream<String> lines = Files.lines(p, UTF_8);
```

调用方不需要知道*具体返回哪个实现类* —— `Files.newInputStream` 返回的可能是普通文件流、也可能是 `ZipFileSystem` 的条目流、还可能是内存文件系统 Jimfs 的流。**由 `FileSystem` 决定**，调用方只用 `InputStream` 接口。

类似的还有 `Channels.newInputStream(Channel)`（把 NIO 的 `Channel` 工厂化成传统 `InputStream`）、`FileSystems.getDefault()`（获取默认文件系统实例）。

追问 那 `new FileInputStream("x.txt")` 和 `Files.newInputStream(Paths.get("x.txt"))` 该用哪个？

现代代码推荐**后者**。原因：① 抛的异常更具体（`NoSuchFileException` vs 通用 `FileNotFoundException`），便于精细处理；② 可扩展到非默认文件系统（`ZipFileSystem`、内存 FS）；③ 和 `Path`、`Files` 生态无缝衔接。`FileInputStream` 还有个历史坑 —— 它有 `finalize()` 方法（JDK 9 之前），GC 时会走 finalizer 队列，性能负担和 bug 都很烦。

## 面试场景 8：常用的 IO 组合姿势（★背下来）

🎤 面试官

写一段代码，把一个 UTF-8 文本文件按行读进来。

🧑‍💻 你

三种姿势都要会：

**姿势一：经典组合（最能考察你对 IO 体系的理解）**

```
try (BufferedReader br = new BufferedReader(
new InputStreamReader(
new FileInputStream("app.log"),
StandardCharsets.UTF_8))) {
String line;
while ((line = br.readLine()) != null) {
System.out.println(line);
}
}
```

从内到外三层：`FileInputStream`（节点流，读字节）→ `InputStreamReader`（适配器，字节转字符，指定 UTF-8）→ `BufferedReader`（装饰器，加缓冲 + `readLine()`）。

**姿势二：NIO2 现代姿势**

```
try (BufferedReader br = Files.newBufferedReader(
Paths.get("app.log"), StandardCharsets.UTF_8)) {
String line;
while ((line = br.readLine()) != null) {
System.out.println(line);
}
}
```

**姿势三：Stream + 惰性按行（大文件必用）**

```
try (Stream<String> lines = Files.lines(
Paths.get("app.log"), StandardCharsets.UTF_8)) {
lines.filter(l -> l.contains("ERROR"))
.forEach(System.out::println);
}
```

三种姿势都用 `try-with-resources` 自动关闭，都显式指定 `UTF-8`。

追问 读大文件（比如 10 GB 日志）应该用哪种？

用 `Files.lines(path)` 或 `new BufferedReader(...).lines()`。它们返回 `Stream<String>`，**惰性按行读**，只在流水线消费时才读下一行，内存占用恒定几十 KB。**绝对不要用 `Files.readString(path)` 或 `Files.readAllLines(path)`** —— 前者一次性把整个文件读成一个 `String`，后者读成 `List<String>`，10 GB 文件直接 `OutOfMemoryError`。

## 面试场景 9：NIO2 的 `Files` 工具类

🧑‍💻 你

JDK 7 引入的 `java.nio.file.Files`（NIO2）把很多常见 IO 操作封装成了一行 API：

需求传统 IONIO2 Files

读整个文件为字符串手写 BufferedReader 循环`Files.readString(path)`（JDK 11+）
读所有行手写循环 `readLine``Files.readAllLines(path)`
惰性按行读BufferedReader.lines()`Files.lines(path)`
读所有字节循环 `read(byte[])``Files.readAllBytes(path)`
写字符串到文件手写 Writer`Files.writeString(path, str)`（JDK 11+）
拷贝文件循环 read/write`Files.copy(src, dst)`
是否存在`new File(...).exists()``Files.exists(path)`
创建文件夹`file.mkdirs()``Files.createDirectories(path)`

写现代 Java 代码，除非要控制底层细节，否则**优先用 `Files`/`Path`**。老 `File` 类的 API 设计得比较古老（很多方法返回 `boolean` 表示成功失败，出错也不抛异常，troubleshooting 很难），不推荐新代码用。

追问 `File` 和 `Path` 的关系是什么？

`java.io.File` 是 JDK 1.0 就有的老 API，表示**文件路径 + 一堆同步阻塞方法**（`exists()`、`mkdir()`、`delete()`），设计陈旧。`java.nio.file.Path` 是 NIO2 引入的替代品，**只表示路径**（不带方法），文件操作全部搬到 `Files` 工具类里 —— 更符合单一职责。两者之间有互转：`file.toPath()`、`path.toFile()`。

## 面试场景 10：IO 关闭有哪些坑？

🧑‍💻 你

三个坑：

1. **不关闭 → 资源泄漏**。文件描述符（fd）是 OS 有限资源，Linux 默认单进程 1024 个，泄漏多了会报 `Too many open files`。任何 `InputStream`/`OutputStream`/`Reader`/`Writer` 都实现了 `AutoCloseable`，必须用 `try-with-resources`。

2. **只关外层，内层没关？** 不用担心 —— 装饰器 `close()` 会级联调用被装饰对象的 `close()`。所以关最外层 `BufferedReader` 就够了。反过来，**只关内层**（`fis.close()` 而 `br` 没关）就有问题：`BufferedReader` 里剩下的缓冲数据没 flush，写场景会丢数据。

3. **写场景不 `close()` → 数据丢失**。`BufferedOutputStream` 内部有 8 KB 缓冲，只有满了、或者调 `flush()`/`close()` 才真正写到磁盘。如果程序没关闭就退出，缓冲里的数据永远到不了文件。

正确姿势永远是 `try-with-resources`：

```
try (BufferedWriter bw = Files.newBufferedWriter(
Paths.get("out.txt"), StandardCharsets.UTF_8)) {
bw.write("hello");
}   // ← 自动 close，自动 flush，异常自动传播
```

追问 `try-with-resources` 里 `close()` 也抛异常怎么办？

Java 7 起用了 **Suppressed Exception 机制**：*原始异常保留为主异常*，*close 抛的异常被追加到主异常的 suppressed 列表*。可以用 `e.getSuppressed()` 拿到那些被压制的异常。老式 try-finally 里，finally 抛异常会*覆盖*主异常 —— 排查现场直接丢失，这是 try-with-resources 相比 try-finally 的关键优势之一。

```
try (SomeResource r = new SomeResource()) {
r.doWork();          // 抛 IOException A
}                        // r.close() 抛 IOException B
// 最终外层看到 A，A.getSuppressed()[0] 是 B —— B 没有丢！
```

陷阱 多个资源要按**声明的反序**关闭，写在同一个 `try(...)` 里就自动这样做了：

```
try (FileInputStream fis = new FileInputStream("a");
BufferedInputStream bis = new BufferedInputStream(fis)) {
// ...
}
// 关闭顺序：先 bis.close() 再 fis.close() —— 反序，符合 LIFO
```

别写成两个嵌套 `try`，也别自己 finally 关 —— 交给编译器最省心。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：装饰器嵌套 —— 一行文件 → 读一个 int

```
import java.io.*;

public class DecoratorDemo {
public static void main(String[] args) throws IOException {
// 写：先写一个 int（4 字节）到文件
try (DataOutputStream dos = new DataOutputStream(
new BufferedOutputStream(
new FileOutputStream("num.bin")))) {
dos.writeInt(0x12345678);
}
// 读：反向嵌套读回来
try (DataInputStream dis = new DataInputStream(
new BufferedInputStream(
new FileInputStream("num.bin")))) {
System.out.printf("0x%08X%n", dis.readInt());   // 0x12345678
}
}
}
```

观察：从内到外是「节点流 → 缓冲装饰 → 数据格式装饰」，最外层调 `writeInt(0x12345678)`，内部转成 4 字节写进缓冲区，缓冲区满或 `close()` 时才写文件。

### 验证 2：适配器 —— 字节流转字符流按行读

```
import java.io.*;
import java.nio.charset.StandardCharsets;

public class AdapterDemo {
public static void main(String[] args) throws IOException {
// 先造一个假的字节流（模拟从网络/内存拿到的字节）
byte[] utf8 = "你好\nHello\n".getBytes(StandardCharsets.UTF_8);
InputStream in = new ByteArrayInputStream(utf8);

// InputStreamReader：字节流适配到字符流 + 指定编码
try (BufferedReader br = new BufferedReader(
new InputStreamReader(in, StandardCharsets.UTF_8))) {
String line;
while ((line = br.readLine()) != null) {
System.out.println("[" + line + "]");
}
}
}
}
// [你好]
// [Hello]
```

### 验证 3：BufferedInputStream vs FileInputStream 性能对比

```
import java.io.*;
import java.nio.file.*;

public class BufferSpeedTest {
public static void main(String[] args) throws IOException {
// 先造一个 10 MB 的文件
Path p = Paths.get("big.dat");
Files.write(p, new byte[10 * 1024 * 1024]);

// 场景一：裸 FileInputStream，逐字节 read()
long t1 = System.currentTimeMillis();
try (FileInputStream fis = new FileInputStream(p.toFile())) {
while (fis.read() != -1) { /* discard */ }
}
System.out.println("Raw read():        " + (System.currentTimeMillis() - t1) + " ms");

// 场景二：BufferedInputStream 逐字节 read()
long t2 = System.currentTimeMillis();
try (BufferedInputStream bis = new BufferedInputStream(
new FileInputStream(p.toFile()))) {
while (bis.read() != -1) { /* discard */ }
}
System.out.println("Buffered read():   " + (System.currentTimeMillis() - t2) + " ms");
Files.delete(p);
}
}
// 典型输出：
// Raw read():        3200 ms
// Buffered read():   45 ms  ← 快约 70 倍
```

### 验证 4：try-with-resources 的 Suppressed Exception

```
public class SuppressedDemo implements AutoCloseable {
public void doWork() { throw new RuntimeException("work failed"); }
@Override public void close() { throw new RuntimeException("close failed"); }

public static void main(String[] args) {
try (SuppressedDemo r = new SuppressedDemo()) {
r.doWork();
} catch (Exception e) {
System.out.println("Main:       " + e.getMessage());
for (Throwable sup : e.getSuppressed()) {
System.out.println("Suppressed: " + sup.getMessage());
}
}
}
}
// Main:       work failed
// Suppressed: close failed   ← close 抛的异常被完整保留
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `InputStream.read()` 为什么返回 `int`？</summary>

因为 `byte` 是 *-128 ~ 127*，没有多余的值可以表示 EOF。规范用 `int`：*0-255* 表示真实字节（无符号），*-1* 表示 EOF。

</details>

<details>

<summary>Q2 `BufferedInputStream`、`InputStreamReader`、`Files.newInputStream` 分别对应什么设计模式？</summary>

分别是**装饰器**（继承 `FilterInputStream`，包一层加缓冲）、**适配器**（把 `InputStream` 适配成 `Reader`，接口都变了）、**工厂**（静态方法返回具体实现由文件系统决定）。

</details>

<details>

<summary>Q3 装饰器模式为什么能避免类爆炸？</summary>

M 个数据源 × N 个功能，走继承要写 `M×2^N` 个类；装饰器让每个功能只写一个类（继承同一抽象类、持有被装饰对象），总共 M+N 个，任意组合。

</details>

<details>

<summary>Q4 读一个 10 GB 日志文件，用什么姿势？</summary>

用 `Files.lines(path, UTF_8)` 或 `BufferedReader.lines()`，返回 `Stream<String>` 惰性按行读，内存恒定。绝不能用 `Files.readString`/`readAllLines`，会 OOM。

</details>

<details>

<summary>Q5 `try-with-resources` 里业务代码和 `close()` 都抛异常，最终外层拿到哪个？另一个哪去了？</summary>

拿到**业务异常**（主异常）；`close()` 抛的被 addSuppressed 追加，通过 `e.getSuppressed()` 取。老式 try-finally 里 finally 抛异常会*覆盖*主异常，是 try-with-resources 相比它的关键优势。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源 A

-  —— 本课主源 B

- JDK 21 · `java.io` API —— 四大抽象类和所有实现的官方索引

- JDK 21 · `java.nio.file.Files` API —— NIO2 现代姿势合集

- JEP 400 · UTF-8 by Default —— JDK 18 起默认字符集改成 UTF-8

#### 🔗 关联课件

-

-

-

#### 🧭 下一课预告

Lesson 0039：**IO 模型 · BIO / NIO / AIO / 多路复用（select/poll/epoll）** —— 从内核视角看阻塞、非阻塞、同步、异步的区别，为后续 Netty 打基础。

💬 有任何疑问 —— 「装饰器和代理模式又是什么关系？」「`Serializable` 为什么被官方标记为遗留？」「NIO 的 Channel 和这里的 Stream 到底怎么衔接？」—— 直接问我。我是你的老师，也是你的追问陪练。


