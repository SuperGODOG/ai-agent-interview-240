> Lesson 0040 · 阶段五收尾 · IO · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 6 个追问

# 0040 · Java NIO 核心：Buffer & Channel & Selector 三件套

上一课（）把 **BIO / NIO / IO 多路复用 / AIO** 的抽象讲透了，现在这节课把镜头拉近到 *Java 标准库里到底怎么写 NIO*：**Buffer**（数据容器）+ **Channel**（双向通道）+ **Selector**（多路复用器）三件套。理解了它们，你才能在下一步读 Netty 源码时不至于卡在 `ByteBuf` / `NioEventLoop` / `SelectionKey` 这些概念上。

面试频次上，本课是**「网关 / 中间件 / RPC 岗几乎必问」**：即使不写 Netty，Kafka 的零拷贝、Redis 的 IO 线程、Tomcat NIO 连接器背后都是这套 API。原文对应 。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `Buffer` 的 `position` / `limit` / `capacity` 三个指针分别是什么？</summary>

`capacity`：Buffer 分配的总容量，创建后不变；`limit`：本次操作的上限，「写模式」= capacity，「读模式」= 上次写到哪；`position`：下一个要读或写的位置。三者关系恒为 `0 ≤ mark ≤ position ≤ limit ≤ capacity`。第 2、3 题细讲。

</details>

<details>

<summary>Q0.2 `FileChannel.transferTo(0, size, socketChannel)` 快在哪？</summary>

走底层 `sendfile(2)` 系统调用，数据在**内核态**直接从文件页缓存传给 socket 缓冲区，*不经过用户态*，省了 2 次 CPU 拷贝和 2 次上下文切换 —— 这就是「零拷贝 zero-copy」。Kafka / Netty 大量用。第 8 题细讲。

</details>

## 面试场景 1：Java NIO 的三件套是什么？各自扮演什么角色？⭐核心

🎤 面试官

Java NIO 你应该熟吧，能不能一分钟讲清楚它由哪几个核心组件组成？

🧑‍💻 你

Java NIO（*New IO*，从 JDK 1.4 引入）的核心是三件套，缺一不可：

- **Buffer**（缓冲区）：数据容器，本质是一段带指针的数组。所有 NIO 的读写都以 Buffer 为中转 —— *Channel 只跟 Buffer 打交道，不再像 BIO 那样一个字节一个字节流。*

- **Channel**（通道）：双向数据通道，类似 BIO 里 `InputStream + OutputStream` 的合体。常见实现有 `FileChannel`、`SocketChannel`、`ServerSocketChannel`、`DatagramChannel`。

- **Selector**（选择器 / 多路复用器）：一个线程通过 `Selector` 监听多个 Channel 的就绪事件（可读 / 可写 / 可 accept / 可 connect）。这是 NIO 能**用少量线程扛住大量连接**的关键。

三者的关系可以画成这样：

```
┌──── Channel A ────► Buffer ──►
│                                 应用层
Selector ─── Channel B ────► Buffer ──►
│                                 处理数据
└──── Channel C ────► Buffer ──►

↑ 一个线程 select() 出所有就绪的 Channel，
再从各自 Channel 读到对应 Buffer。
```

追问 NIO 和 BIO 最本质的差异是什么？

两条：**①「面向流」变成「面向缓冲」** —— BIO 是 `InputStream.read()` 一次一个字节流出去，NIO 是 `channel.read(buffer)` 一批塞进 Buffer，可回退可跳读。**②「阻塞」变成「非阻塞 + 多路复用」** —— BIO 里 `accept()`/`read()` 会把线程钉死，NIO 通过 `configureBlocking(false)` + `Selector` 让一个线程管上万个连接。

## 面试场景 2：Buffer 的核心字段有哪些？7 个子类是什么？

🎤 面试官

Buffer 你打开源码看过吗？它的核心字段是哪几个？

🧑‍💻 你

抽象基类 `java.nio.Buffer` 里就 4 个核心 int 字段（顺序有关）：

```
public abstract class Buffer {
private int mark     = -1;   // 标记位（可选，配合 reset 用）
private int position = 0;    // 下一个要读/写的位置
private int limit;           // 本次操作的边界
private int capacity;        // 总容量（创建后不变）
}
```

四者恒满足 `0 <= mark <= position <= limit <= capacity`。

具体的 Buffer 有 **7 个子类**，对应 Java 除 `boolean` 外的 7 种基本类型：

- `ByteBuffer`（★最常用，网络 / 文件 IO 都是它）

- `CharBuffer`

- `ShortBuffer`

- `IntBuffer`

- `LongBuffer`

- `FloatBuffer`

- `DoubleBuffer`

创建时**不能 `new`**，只能用工厂方法：`ByteBuffer.allocate(1024)`（堆内）或 `ByteBuffer.allocateDirect(1024)`（堆外）。

追问 为什么没有 `BooleanBuffer`？

`boolean` 在 JVM 里存储无固定规范（见  Q7），Buffer 的定位是「与底层字节序列直接映射的容器」—— `boolean` 不好统一为定长基本类型，且业务上极少需要「布尔数组的 IO」，就没做。要传 boolean 就用 `ByteBuffer` 一个字节代替。

## 面试场景 3：flip / clear / rewind / compact 的语义分别是什么？⭐经典

🎤 面试官

Buffer 有几个「切换模式」的方法：`flip`、`clear`、`rewind`、`compact`，你能讲清楚它们分别改了哪几个字段吗？

🧑‍💻 你

这几个方法是 NIO 编程最容易出 bug 的地方，一定要背清楚：

方法用途做的事数据是否清空

`flip()`
「写模式 → 读模式」
limit = position; position = 0; mark = -1
否（限定读到刚才写的边界）

`clear()`
「读模式 → 写模式」（新一轮写）
position = 0; limit = capacity; mark = -1
否（数据还在，只是被覆盖）

`rewind()`
重新从头读一遍
position = 0; mark = -1（limit 保持）
否

`compact()`
把未读数据前移，再切写模式
未读部分移到 [0, remaining)；position = remaining; limit = capacity
否（保留未读的）

`mark()` / `reset()`
打标 / 回到标
mark = position； reset 时 position = mark
否

典型流程是 **write → flip → read → clear → write ...**，形成一个循环。

陷阱 `clear()` 的名字有强烈误导性 —— 它**不清数据**，只把三个指针重置。真正的数据要等到下一次 `put()` 把旧数据覆盖掉才「消失」。要清零数据得手动 `Arrays.fill(buffer.array(), (byte)0)`。

追问 Buffer 写完之后忘了 `flip()` 直接 `get()` 会发生什么？

你会从「刚写完的 position」继续往后读，直到 limit（写模式下 limit = capacity），读到的是**还没写过的位置** —— 要么是 0（allocate 出来的默认值），要么是上一轮 clear 之后没被覆盖的旧数据。业务上表现为「消息内容莫名其妙有一堆 0」或「数据错乱」。这是 NIO 手写业务代码最经典的 bug，也是大家宁愿用 Netty 的 `ByteBuf`（读写指针分开）也不愿直接用 `ByteBuffer` 的一大原因。

追问 `compact()` 和 `clear()` 有什么本质区别？什么场景下必须用 `compact()`？

`clear()` 假设「读完了」，直接重置指针；`compact()` 假设「可能没读完」，把没读的搬到前面继续写。典型场景是**网络编程中一次 read 出来的数据不够解析一条完整消息**：读了半条消息后要接着从 Channel 收更多字节，这时候只能用 `compact()` 把半条消息保留下来，让新数据接在后面。用 `clear()` 会把半条丢掉。

## 面试场景 4：Channel 是什么？常见实现有哪些？

🎤 面试官

Channel 相比 BIO 里的 InputStream / OutputStream 有什么区别？

🧑‍💻 你

Channel 相当于 `InputStream + OutputStream` 的合体，主要差别有三：

1. **双向**：一个 Channel 可以既读又写（Stream 是单向的）。

2. **必须配 Buffer 使用**：不能直接 `channel.read(byte[])`，得 `channel.read(ByteBuffer)`。

3. **可以非阻塞**：`configureBlocking(false)` 之后，`read`/`accept` 立刻返回而不是等数据到。

常见实现：

Channel对应场景类似 BIO 的谁

`FileChannel`文件读写、内存映射、零拷贝FileInputStream / FileOutputStream
`SocketChannel`TCP 客户端（也是 server 接受连接后的读写通道）Socket
`ServerSocketChannel`TCP 服务端监听ServerSocket
`DatagramChannel`UDP 收发DatagramSocket

**注意**：`FileChannel` 无法设置非阻塞模式（`configureBlocking(false)` 会抛异常），所以文件 IO 用不上 Selector —— Selector 是给*网络 Channel* 服务的。

## 面试场景 5：Channel 有哪三种典型用法？

🧑‍💻 你

Channel 就三种数据流向：

1. **Channel → Buffer**（读）：`int n = channel.read(buffer);` 从通道读到 Buffer。返回 `-1` 表示 EOF。

2. **Buffer → Channel**（写）：`channel.write(buffer);` 把 Buffer 里 `[position, limit)` 之间的数据写出去。*写之前必须 flip！*

3. **Channel → Channel**（零拷贝）：`srcChannel.transferTo(0, size, dstChannel);` 或 `dstChannel.transferFrom(srcChannel, 0, size);` 数据不经过用户态，直接在内核态转发。

## 面试场景 6：Selector 是什么？SelectionKey 的 4 种事件？⭐核心

🎤 面试官

Selector 是干嘛的？为什么说它是 NIO 的灵魂？

🧑‍💻 你

Selector 是 Java 对操作系统 **IO 多路复用**（`epoll` / `kqueue` / `select` —— 见上一课）的封装。用法：

1. 创建一个 Selector：`Selector selector = Selector.open();`

2. 把非阻塞 Channel 注册到 Selector 上，声明*感兴趣的事件*：`channel.register(selector, SelectionKey.OP_READ);`

3. 调用 `selector.select()` 阻塞，直到有 Channel 就绪。

4. 拿到就绪 Channel 集合 `selector.selectedKeys()`，遍历处理。

5. **处理完必须从集合里 `remove()`**，否则下次循环还会命中。

**SelectionKey 定义了 4 种事件**：

常量值触发时机适用 Channel

`OP_READ`1Channel 里有数据可读SocketChannel
`OP_WRITE`4Channel 内核写缓冲有空间可写SocketChannel
`OP_CONNECT`8客户端 connect 完成SocketChannel（client）
`OP_ACCEPT`16有新连接到来ServerSocketChannel

可以按位 OR 组合，如 `OP_READ | OP_WRITE`。

追问 `Selector.select()` 为什么可能返回 0？NIO 的「空轮询 bug」是什么？

三种情况：**①正常超时**（`select(timeout)`）；**②被 `wakeup()` 中断**；**③臭名昭著的「JDK NIO 空轮询 bug」** —— 在 Linux 下 `epoll_wait` 有时会因内核事件（比如 poll 返回但 event mask 全是 0）被立即唤醒但没实际就绪事件，导致 `select()` 返回 0，进而 while 循环空转打到 **CPU 100%**。Netty 的 workaround 是：统计 `select()` 在极短时间内连续返回 0 的次数，超过阈值（默认 512）就**「rebuild selector」** —— 新建一个 Selector，把老的 Channel 都迁过去，把有 bug 的老 Selector 扔掉。这是所有网络框架都必须处理的坑。

追问 处理完 `SelectionKey` 忘了 `remove()` 会怎样？

下次 `select()` 返回时，`selectedKeys()` 里**还会有那个老 key**（因为它是「累加式」的集合，JDK 不会自动清），你会以为它又就绪了，去执行 `key.channel().read()`，实际上什么都读不到（或读 0 字节），业务出错。所以标准写法是 `while (it.hasNext()) { SelectionKey key = it.next(); it.remove(); ... }`，先 remove 再处理，或者处理完立即 remove。

## 面试场景 7：NIO Server 的完整编程模型？⭐核心

🎤 面试官

不用 Netty，直接用 JDK 的 NIO API 写一个 echo server 大致什么骨架？

🧑‍💻 你

标准骨架分三步：

1. **初始化**：创建 `ServerSocketChannel`，`bind` 端口，`configureBlocking(false)`，注册到 `Selector` 上并声明 `OP_ACCEPT`。

2. **主循环**：`while (true) { selector.select(); ... }`，阻塞等事件。

3. **事件分发**：遍历 `selectedKeys()`，按 `isAcceptable / isReadable / isWritable` 分类处理；新接收的连接注册 `OP_READ`。

整个流程就是「Reactor 模式」的单线程版：一个 EventLoop 线程负责事件分发。Netty 的多 Reactor（boss + worker）就是把这套思路扩展成主从多线程。

## 面试场景 8：零拷贝 zero-copy 是什么？Java 里怎么用？⭐经典

🎤 面试官

Kafka 常说零拷贝，Java 里怎么实现的？

🧑‍💻 你

先看**传统 IO 从文件发到网卡**要走几次拷贝：

```
用户态：       ┌──── read() ────┐              ┌──── write() ────┐
│                │              │                 │
▼                │              ▼                 │
内核态：  磁盘 ──DMA──► 内核缓冲区 ──CPU──► 用户缓冲区 ──CPU──► socket 缓冲区 ──DMA──► 网卡
①               ②                ③               ④

共 2 次 DMA + 2 次 CPU 拷贝，2 次系统调用 (read/write)，4 次内核态↔用户态切换。
```

**零拷贝（`sendfile` 系统调用）**把中间那两次 CPU 拷贝省掉：

```
用户态：             ┌──── sendfile() ────┐
│                      │
▼                      │
内核态：  磁盘 ──DMA──► 内核缓冲区 ────► socket 缓冲区 ──DMA──► 网卡
①              (仅 offset+length 传递)         ②

Linux 2.4+ 支持 DMA scatter/gather 后，中间那步连拷贝都不用，纯粹传递描述符。
```

Java 里两种入口：

- `FileChannel.transferTo(position, count, targetChannel)`：把当前文件通道的一段直接发到另一个 Channel（通常是 `SocketChannel`）。底层就是 `sendfile(2)`。

- `FileChannel.transferFrom(sourceChannel, position, count)`：反向。

典型用户：**Kafka** 消费者拉数据时把 log 文件直接 `transferTo` socket；**Netty** 的 `FileRegion`；**Nginx** 静态文件；**Tomcat** 的 `sendfile` 配置。

追问 `MappedByteBuffer` 是什么？它算零拷贝吗？

`fileChannel.map(MapMode.READ_ONLY, 0, size)` 把文件用 `mmap(2)` 系统调用映射到虚拟内存 —— 读文件变成读内存，页缺失时内核自动把文件页调进来。**严格来说 `mmap + write` 减少了 1 次 CPU 拷贝但不是「0 拷贝」**（仍需 1 次内核缓冲→socket 缓冲的拷贝）。真正的零拷贝是 `sendfile`。**Kafka 存储日志用 `mmap`（写入场景），发送数据用 `sendfile`（读取场景）**，两个都用了。

陷阱 `MappedByteBuffer` 关闭映射不是 `close()`，JDK 没提供直接 unmap 的公开 API，只能等 GC 回收 DirectByteBuffer 的 Cleaner 触发。Windows 下不 unmap 会导致文件被锁无法删除。生产上要用反射调 `sun.misc.Unsafe.invokeCleaner()` 强制解除（JDK 9+ 用 `Unsafe#invokeCleaner`）。

## 面试场景 9：DirectByteBuffer 堆外内存的原理与坑

🎤 面试官

`ByteBuffer.allocateDirect(1024)` 和 `ByteBuffer.allocate(1024)` 有什么区别？为什么高性能 IO 都用前者？

🧑‍💻 你

`allocate` 分配在 **JVM 堆**里（`HeapByteBuffer`），`allocateDirect` 分配在 **堆外**（`DirectByteBuffer`，走 `Unsafe.allocateMemory`，本质是 `malloc`）。

**为什么 IO 场景喜欢堆外？**因为系统调用（如 `write`）要传的是*连续的内存地址*，而 JVM 堆内的对象**可能被 GC 移动**（Compact），地址会变。所以从堆内 Buffer 做 IO 时，JDK 会先**把数据拷贝到一块临时堆外内存**再交给 syscall。用 DirectByteBuffer 就省掉这次拷贝。

**回收机制**：DirectByteBuffer 对象本身在堆内很小（就几十字节），但持有一个指向堆外内存的指针；同时关联一个 `Cleaner`（`sun.misc.Cleaner`，PhantomReference 虚引用的子类）。当 DirectByteBuffer 被 GC 时，JVM 触发 Cleaner，Cleaner 调用 `Unsafe.freeMemory()` 释放堆外内存。

陷阱 堆外内存**不受 `-Xmx` 限制**，受 `-XX:MaxDirectMemorySize` 限制（默认约等于 `-Xmx`）。而且 GC 只在*堆内压力大*时才触发，堆内的 DirectByteBuffer 对象很小、很少被回收，堆外内存却可能已经耗尽 —— 这就是**「堆外内存泄漏」/「堆外 OOM」**。表现是 `OutOfMemoryError: Direct buffer memory`。排查靠 `-XX:NativeMemoryTracking=detail` 或 arthas 的 `memory` 命令。

追问 堆外内存怎么被主动回收？

三种方式：**①自然回收** —— 等 DirectByteBuffer 对象被 GC，Cleaner 触发 `freeMemory`；**②`System.gc()`** —— 手动触发 Full GC 顺带回收 DirectByteBuffer；但这个可能被 `-XX:+DisableExplicitGC` 禁用（老一辈的运维喜欢加），加了这个参数堆外内存就永远回收不了；**③反射强制 clean** —— `((DirectBuffer)buffer).cleaner().clean();`（JDK 8）或 `Unsafe.invokeCleaner(buffer)`（JDK 9+）。Netty 就是走第三种主动管理。

## 面试场景 10：NIO 相比 BIO 到底强在哪？适合什么场景？

🧑‍💻 你

三条硬优势：

1. **一个线程管多个连接**：Selector 多路复用避免了「一连接一线程」的模型，1 万连接可能只需要几十个线程 —— 内存（每线程 1MB 栈）和上下文切换成本都省了。

2. **零拷贝支持**：`FileChannel.transferTo` 走 `sendfile`，大文件传输 CPU 占用低。

3. **堆外内存 + Direct IO**：省掉 JVM 堆 → 堆外的临时拷贝。

但也有代价：**API 极其难用**（Buffer 的 flip / clear 心智负担、拆包粘包要自己处理、空轮询 bug）—— 所以生产上极少直接用 JDK NIO，都用 **Netty** 封装。

**适用场景**：

- ✅ **高并发长连接**：IM、推送、网关、RPC（Dubbo / gRPC / Netty）

- ✅ **大文件传输**：Kafka、静态资源服务器

- ❌ **低并发短连接**：BIO 反而更简单省心，NIO 的调度开销不划算

追问 「NIO 编程为什么很难，大家都用 Netty」，具体难在哪三点？

面试常见的标准回答：**①`ByteBuffer` 手动 flip / clear 心智负担大**（Netty `ByteBuf` 分离读写指针，不需要模式切换）；**②拆包粘包要自己写**（TCP 是字节流，一个 `read()` 可能读出半个包或几个包混在一起，Netty 提供 `LengthFieldBasedFrameDecoder` / `LineBasedFrameDecoder` 等开箱即用）；**③JDK NIO 空轮询 bug、事件循环性能**（Netty 内置 rebuild selector、无锁化 EventLoop、内存池 `PooledByteBufAllocator` 等优化）。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：Buffer 状态迁移（flip / clear / rewind）

```
import java.nio.CharBuffer;

public class BufferStateDemo {
public static void main(String[] args) {
CharBuffer buf = CharBuffer.allocate(8);
System.out.printf("初始      pos=%d limit=%d cap=%d%n",
buf.position(), buf.limit(), buf.capacity());
// 初始      pos=0 limit=8 cap=8

buf.put('a').put('b').put('c');
System.out.printf("写入后    pos=%d limit=%d cap=%d%n",
buf.position(), buf.limit(), buf.capacity());
// 写入后    pos=3 limit=8 cap=8

buf.flip();  // ← 由写切读
System.out.printf("flip 后   pos=%d limit=%d cap=%d%n",
buf.position(), buf.limit(), buf.capacity());
// flip 后   pos=0 limit=3 cap=8

while (buf.hasRemaining()) {
System.out.print(buf.get());  // 输出 abc
}
System.out.println();

buf.clear();  // ← 由读切写（但底层数据 abc 还在）
System.out.printf("clear 后  pos=%d limit=%d cap=%d %s%n",
buf.position(), buf.limit(), buf.capacity(),
java.util.Arrays.toString(buf.array()));
// clear 后  pos=0 limit=8 cap=8 [a, b, c, \0, \0, \0, \0, \0]
// ↑ 注意 abc 还在，只是指针被重置了
}
}
```

### 验证 2：FileChannel 读写文件 + transferTo 零拷贝

```
import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;

public class FileChannelDemo {
public static void main(String[] args) throws IOException {
// 1. 用 FileChannel 写文件
try (FileChannel out = new FileOutputStream("hello.txt").getChannel()) {
ByteBuffer buf = ByteBuffer.wrap("Hello NIO\n".getBytes());
out.write(buf);
}

// 2. 用 FileChannel 读文件
try (FileChannel in = new FileInputStream("hello.txt").getChannel()) {
ByteBuffer buf = ByteBuffer.allocate(64);
int n = in.read(buf);
buf.flip();                     // ← 读之前必须 flip
byte[] bytes = new byte[n];
buf.get(bytes);
System.out.println("读到: " + new String(bytes));
}

// 3. 零拷贝：把 src 文件的内容直接传到 dst 文件
try (FileChannel src = new FileInputStream("hello.txt").getChannel();
FileChannel dst = new FileOutputStream("hello_copy.txt").getChannel()) {
long transferred = src.transferTo(0, src.size(), dst);
// ↑ 底层走 sendfile(2)，如果 dst 是 SocketChannel 效果最明显
System.out.println("零拷贝传输 " + transferred + " 字节");
}
}
}
```

### 验证 3：Selector Echo Server（★核心示例）

下面是一个用纯 JDK NIO API 写的 Echo Server —— 客户端发什么，server 原样回什么。**整个 server 只有一个线程**，靠 Selector 扛所有连接。

```
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.*;
import java.util.Iterator;

public class NioEchoServer {

public static void main(String[] args) throws IOException {
// 1. 开一个 ServerSocketChannel，绑定端口，切非阻塞
ServerSocketChannel serverChannel = ServerSocketChannel.open();
serverChannel.bind(new InetSocketAddress(9090));
serverChannel.configureBlocking(false);

// 2. 开一个 Selector，把 serverChannel 注册进去，关心 ACCEPT 事件
Selector selector = Selector.open();
serverChannel.register(selector, SelectionKey.OP_ACCEPT);

System.out.println("EchoServer started on :9090");

// 3. 事件循环
while (true) {
int ready = selector.select();       // 阻塞直到有就绪事件
if (ready == 0) continue;             // 空转防御（简化版）

Iterator<SelectionKey> it = selector.selectedKeys().iterator();
while (it.hasNext()) {
SelectionKey key = it.next();
it.remove();                      // ← 必须先 remove！

try {
if (key.isAcceptable()) {
// 新连接到来
ServerSocketChannel ssc = (ServerSocketChannel) key.channel();
SocketChannel client = ssc.accept();
client.configureBlocking(false);
// 新连接注册到 selector 上，关心 READ
client.register(selector, SelectionKey.OP_READ,
ByteBuffer.allocate(1024));
System.out.println("Accepted: " + client.getRemoteAddress());

} else if (key.isReadable()) {
// 有数据可读
SocketChannel client = (SocketChannel) key.channel();
ByteBuffer buf = (ByteBuffer) key.attachment();
int n = client.read(buf);
if (n < 0) {                     // 对端关闭
client.close();
continue;
}
buf.flip();                      // 切读模式，准备回写
client.write(buf);               // Echo 回去
buf.clear();                     // 切回写模式，等下次
}
} catch (IOException e) {
key.cancel();
key.channel().close();
}
}
}
}
}
// 测试：另开终端跑 `nc localhost 9090`，敲什么它回什么。
// 再开一个 nc 连上去，一个线程照样并发处理两个连接。
```

### 验证 4：DirectByteBuffer 堆外分配 & 手动 clean

```
import java.nio.ByteBuffer;
import sun.misc.Unsafe;                          // JDK 内部 API，编译加 --add-exports
import java.lang.reflect.Field;

public class DirectBufferDemo {
public static void main(String[] args) throws Exception {
// 1. 分配堆外 1MB
ByteBuffer direct = ByteBuffer.allocateDirect(1024 * 1024);
System.out.println("isDirect = " + direct.isDirect());  // true

direct.putInt(42);
direct.flip();
System.out.println("读回: " + direct.getInt());          // 42

// 2. 强制清理（JDK 9+ 用 Unsafe.invokeCleaner）
Field f = Unsafe.class.getDeclaredField("theUnsafe");
f.setAccessible(true);
Unsafe unsafe = (Unsafe) f.get(null);
unsafe.invokeCleaner(direct);
// ↑ 现在 direct 对应的堆外 1MB 已被 free 掉，
//   再访问会段错误（JVM crash），生产上要小心。

System.out.println("cleaned");
}
}
// 运行需要:
//   --add-exports java.base/sun.nio.ch=ALL-UNNAMED
//   --add-exports java.base/jdk.internal.misc=ALL-UNNAMED  (JDK 9+)
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `Buffer.flip()` 具体修改了哪几个字段？为什么这个方法叫「翻转」？</summary>

`limit = position; position = 0; mark = -1;`。「翻转」是指把 Buffer 从「写模式」翻到「读模式」—— 原来 position 指向写到哪里，flip 后 limit 指向读到哪为止、position 从头开始读。数据没动，只是「视角」调转 180°。

</details>

<details>

<summary>Q2 SelectionKey 的 4 种事件是什么？`ServerSocketChannel` 只能关心哪一种？</summary>

`OP_READ / OP_WRITE / OP_CONNECT / OP_ACCEPT`。`ServerSocketChannel` 只能关心 `OP_ACCEPT`（它只负责监听新连接，不参与数据读写）；`SocketChannel` 可以关心 `OP_READ / OP_WRITE / OP_CONNECT`（客户端 connect 完成时用最后一个）。

</details>

<details>

<summary>Q3 `FileChannel.transferTo` 为什么比 `read + write` 快？对应什么系统调用？</summary>

走 Linux 的 `sendfile(2)` 系统调用，数据直接在内核态从文件页缓存 → socket 缓冲区，不经过用户态。省了 2 次 CPU 拷贝、1 次系统调用、2 次内核↔用户态切换。DMA scatter/gather 加持下更是 0 次 CPU 拷贝。Kafka、Netty、Nginx 都用它。

</details>

<details>

<summary>Q4 处理完 `SelectionKey` 忘了 `iterator.remove()` 会发生什么？</summary>

`selectedKeys()` 是「累加式」的集合，JDK 不会自动清空。下次 `select()` 时那个老 key 还在里面，你会以为它又就绪了，去调 `channel.read()` 但读不到数据（返回 0），业务逻辑出错。标准写法：`while (it.hasNext()) { SelectionKey key = it.next(); it.remove(); ... }`。

</details>

<details>

<summary>Q5 堆外内存（DirectByteBuffer）由谁负责回收？为什么会出现「堆外 OOM」？</summary>

每个 DirectByteBuffer 关联一个 `Cleaner`（虚引用 PhantomReference 的子类）。DirectByteBuffer 对象在堆内被 GC 时，JVM 通知 Cleaner 调用 `Unsafe.freeMemory()` 释放堆外内存。**「堆外 OOM」原因**：DirectByteBuffer 对象本身很小，堆内几乎不会因为它触发 GC；但堆外可能已经分配了几百 MB。如果一直没有 Full GC 触发 Cleaner，堆外就撑爆（受 `-XX:MaxDirectMemorySize` 限制），抛 `OutOfMemoryError: Direct buffer memory`。解决方法是主动 `System.gc()` 或反射调 Cleaner。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.nio.ByteBuffer` —— Buffer 各方法官方定义

- JDK 21 · `java.nio.channels.Selector` —— Selector API 契约

- Linux man page · `sendfile(2)` —— 零拷贝的底层系统调用

#### 🔗 关联课件

- （BIO 侧的对照）

- （上一课，OS 层的抽象）

- （下一课，阶段六起点）

#### 🧭 下一课预告

**阶段六 · MySQL**：Lesson 0041 **MySQL 概览 & 存储引擎 & 三大范式** —— 从「谁在网络另一端」进入「谁在磁盘另一端」。IO 五节课到此收尾，恭喜你已经拥有读 Netty 源码的地基。

💬 有任何疑问 —— 「flip 到底是啥？」「空轮询 bug 面试真被追问过没有？」「Kafka mmap 和 sendfile 的分工能不能再讲细一点？」—— 直接问我。我是你的老师，也是你的追问陪练。


