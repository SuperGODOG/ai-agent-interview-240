> Lesson 0039 · 阶段五 · IO · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0039 · IO 模型：BIO/NIO/AIO & 多路复用 select/poll/epoll

这一课覆盖 的完整考点，并按面试真实追问的深度重新组织。**IO 模型是 Netty、Redis、Nginx、Kafka 的底层地基** —— 面试问「Java IO 模型」看似基础，但只要你能把 `select` 和 `epoll` 的区别画出来、把 LT/ET 讲清楚、把「同步非阻塞 IO」和「IO 多路复用」的边界说明白，面试官立刻会把你从「背八股」升级到「懂原理」的档位。

本课要建立的心智模型：**「同步/异步」讲的是结果由谁通知，「阻塞/非阻塞」讲的是等结果时线程会不会被挂起**。这两组概念是正交的，交叉出的四象限就是所有 IO 模型的地图。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 一台机器上如果每个 TCP 连接对应一个线程，10K 连接扛不扛得住？</summary>

扛不住。每个线程默认 1MB 栈，10K 线程光栈就要 10GB；上下文切换开销也会把 CPU 打满。这就是著名的 **C10K 问题**，也是 NIO + epoll 出现的根本动机。第 2、5 题会展开。

</details>

<details>

<summary>Q0.2 `epoll` 相比 `select` 快在哪？</summary>

三点：**①** 没有 1024 fd 上限（红黑树管理）；**②** 就绪 fd 是内核通过回调放入就绪列表，用户拿到的是 O(1) 就绪集，不用像 select 一样 O(n) 遍历所有 fd；**③** 不用每次系统调用都拷贝整个 fd_set 到内核。第 5 题细讲。

</details>

## 面试场景 1：同步/异步 vs 阻塞/非阻塞 到底怎么区分？★经典

🎤 面试官

说一下 **同步、异步、阻塞、非阻塞** 这四个词怎么区分？很多人混着用。

🧑‍💻 你

这是两组正交的概念，分别回答不同的问题：

- **同步 vs 异步**：结果是**调用方主动等/拿**，还是**被调方完成后通知调用方**？同步是我主动查；异步是它做完通知我（回调 / Future / 事件）。

- **阻塞 vs 非阻塞**：调用发出后到结果返回前，**当前线程会不会被 OS 挂起**？阻塞是线程被挂起交出 CPU；非阻塞是立即返回（成功、失败或「未就绪」），线程可以去干别的。

把两组维度交叉，就是 IO 模型的四象限地图：

```
┌────────────────────┬────────────────────┐
│      同步          │       异步          │
┌────────────────┼────────────────────┼────────────────────┤
│   阻塞         │  BIO（同步阻塞）   │  （理论存在，无用）│
├────────────────┼────────────────────┼────────────────────┤
│  非阻塞        │  NIO（同步非阻塞） │  AIO（异步非阻塞） │
│                │  + 多路复用        │  JDK 1.7 NIO.2     │
└────────────────┴────────────────────┴────────────────────┘
```

注意：**IO 多路复用（Java Selector / Linux epoll）仍然是「同步非阻塞」** —— 就绪事件由内核告诉你，但拿数据的 `read` 还是你自己调用、还是同步的。真正异步的只有 AIO：`read` 也交给 OS，完成后 OS 回调你。

追问 C10K / C10M 问题是什么？

**C10K**：单机同时处理 **1 万** 并发连接的挑战，Dan Kegel 1999 年提出。当时用 BIO「一连接一线程」的模型完全扛不住 —— 线程栈内存爆炸、上下文切换 CPU 打满。**解法**就是 IO 多路复用（Linux 用 epoll、BSD 用 kqueue、Windows 用 IOCP）+ 事件驱动 —— Nginx、Redis、Netty 都是这个套路。**C10M** 是升级版：单机 1000 万连接。这时不仅要 epoll，还要用户态协议栈（DPDK）、无锁数据结构、CPU 亲和、绑核 —— 已经进入操作系统级优化的领域了。

追问 「同步非阻塞 IO」和「IO 多路复用」有什么区别？两个都是同步非阻塞的？

是的，两者都在四象限的「同步非阻塞」格子里。区别在于「感知就绪的方式」：**朴素同步非阻塞 IO** 是用户线程自己在死循环里反复 `read()`，返回 `EWOULDBLOCK` 就再试 —— *纯粹的用户态轮询，CPU 白烧*。**IO 多路复用** 把「问哪些 fd 就绪」这一步交给内核（`select`/`poll`/`epoll`），用户线程阻塞在这个多路复用 API 上，一次唤醒可以拿到多个就绪 fd —— *用一次系统调用取代 N 次轮询*，这才是真正能扛 C10K 的方案。

## 面试场景 2：BIO 是什么？为什么扛不住 C10K？

🎤 面试官

先讲 BIO。它是怎么工作的？为什么现在几乎没人用了？

🧑‍💻 你

**BIO (Blocking IO)** 是 JDK 1.0 就有的 `java.io` 那套 API —— `Socket` / `ServerSocket` / `InputStream` / `OutputStream`。核心特征是所有 IO 操作都会**阻塞当前线程**：

- `serverSocket.accept()` —— 没连接来就一直挂着，线程被 OS 挂起

- `inputStream.read(buf)` —— 对端没发数据就一直挂着，直到有数据或对端关闭

所以经典的 BIO 服务端只能写成**「一个连接一个线程」**：主线程 `accept`，每次 accept 到就 `new Thread`（或丢线程池）去处理这个连接的读写。

它的**致命问题**是：

1. **线程数爆炸**：1 万连接 = 1 万线程。JVM 每个线程默认 1MB 栈，10K 线程光栈内存就要 10GB。

2. **上下文切换代价**：内核调度 10K 就绪态/阻塞态线程，CPU 大量时间花在切换上（保存/恢复寄存器、TLB 失效），而不是真正处理业务。

3. **大部分线程都在闲置**：像 IM、长连接推送这种业务，绝大多数连接空闲无数据，却各自占一个线程 —— 极度浪费。

**适用场景**：连接数少（一般 < 100）、连接稳定、每个连接吞吐高的场景 —— 比如内部微服务的 RPC 长连接、数据库连接池。编程简单是它唯一的优点。

追问 「伪异步 BIO」（BIO + 线程池）能解决 C10K 吗？

**不能**。线程池只解决了「频繁创建销毁线程」的开销，没改变「每个连接必须占一个线程」的本质 —— 1 万连接依然要 1 万线程同时活着。线程池反而引入新问题：**队列积压**（超过 corePoolSize 的连接排队）、**拒绝策略**（队列满怎么办）。所以「伪异步 BIO」只是把「线程爆炸」缓和了一点，本质还是 BIO 的天花板 —— 突破天花板必须换到 NIO。

## 面试场景 3：NIO 是什么？三大组件的作用

🎤 面试官

Java NIO 是什么？和 BIO 最关键的区别在哪？

🧑‍💻 你

**NIO (Non-blocking IO / New IO)** 是 JDK 1.4 引入的 `java.nio` 包 —— 底层对应「同步非阻塞 IO + 多路复用」模型。核心三件套：

- **Buffer（缓冲区）**：所有数据读写都通过 `ByteBuffer` 等 Buffer 承载，取代了 BIO 里面向流（Stream）的字节流模式。Buffer 内部有 `position/limit/capacity` 三个指针，配合 `flip()`/`clear()`/`compact()` 切换读写模式。

- **Channel（通道）**：类似 BIO 的 Stream，但是**双向**的、可以设置为**非阻塞模式**的。常见实现：`SocketChannel`、`ServerSocketChannel`、`FileChannel`、`DatagramChannel`。

- **Selector（选择器/多路复用器）**：核心组件。**一个 Selector 可以同时管理多个 Channel**，把它们注册进来，`selector.select()` 会阻塞等待任意 Channel 上出现就绪事件，然后返回一批就绪的 `SelectionKey`。

Channel 注册到 Selector 时要声明感兴趣的事件类型（`SelectionKey` 常量）：

- `OP_ACCEPT`：ServerSocketChannel 收到新连接

- `OP_CONNECT`：SocketChannel 连接建立完成

- `OP_READ`：Channel 有数据可读

- `OP_WRITE`：Channel 可以写入（发送缓冲区有空间）

关键差异：**BIO 是「阻塞等一个连接」，NIO 是「一个线程阻塞等所有连接的事件」**。10K 空闲连接在 BIO 里要 10K 线程，在 NIO 里只需要 1 个 Selector 线程 + 1 次 `select()` 系统调用。

追问 Buffer 里的 `flip()` 到底做了什么？

`flip()` 把 Buffer 从「写模式」切到「读模式」。具体操作：**`limit = position; position = 0;`**。写模式下 `position` 指向下一个可写位置；`flip` 后 `limit` 变成刚写到哪、`position` 归零 —— 于是 `[0, limit)` 就是刚写入的有效数据区，可以从头读到 limit。忘记 `flip` 直接读，会读到还没写的空区，是 NIO 初学者头号 bug。下一课 0040 会把 Buffer 三指针画成动图讲透。

追问 NIO 就等同于「IO 多路复用」吗？

**不等同**。`java.nio` 包里既有对应「IO 多路复用」的 `Selector` + 非阻塞 `SelectableChannel`，也有**纯阻塞的通道**（`FileChannel` 的读写、默认阻塞模式的 `SocketChannel`）、也有**文件 IO / 内存映射**（`MappedByteBuffer`）。所以严格说：**Java NIO ⊃ 基于 Selector 的多路复用**。面试要抠字眼时，别说「NIO 就是多路复用」。

## 面试场景 4：AIO 是什么？JDK 里的 AIO 为什么没火？

🧑‍💻 你

**AIO (Asynchronous IO)** 是 JDK 1.7 引入的 `java.nio.channels` 下的异步通道 API（也叫 NIO.2），包括 `AsynchronousSocketChannel`、`AsynchronousServerSocketChannel`、`AsynchronousFileChannel`。

它对应「真正的异步 IO」模型：**发起调用后立即返回，OS 在数据准备好且拷贝完成后，通过回调（`CompletionHandler`）或 `Future` 通知用户** —— 用户线程从头到尾都不阻塞。

两种拿结果的方式：

1. **Future 模式**：`Future<Integer> f = channel.read(buf); int n = f.get();` —— `get()` 时才阻塞，本质上不算真异步。

2. **Callback 模式**：`channel.read(buf, attachment, new CompletionHandler<Integer, Attach>() { public void completed(Integer n, Attach a) {...} })` —— OS 完成后回调 `completed`，用户线程可以立即去做别的。

问题在于 AIO 在 Linux 上**没有真正的内核级实现**。Windows 的 IOCP 才是原生异步；Linux 的 `io_uring`（5.1 才有）之前，只能用 **epoll 在用户态模拟异步** —— 底层还是 IO 多路复用，性能没实质提升，反而 API 更复杂。所以：

- Netty 早期用过 AIO，后来**放弃回到 NIO**；

- 业界主流服务端框架（Netty、Vert.x、gRPC-java）几乎都用 NIO；

- AIO 只在少数场景（大文件异步读写、Windows 平台）有点用武之地。

追问 Linux 上的 `io_uring` 会不会颠覆现状？

有可能。`io_uring`（Linux 5.1+）是内核提供的**真正的异步 IO 接口**，通过 SQ/CQ 两个共享内存 ring buffer 让用户态和内核态零拷贝地交换任务和完成事件 —— 号称「Linux 上第一个正确设计的异步 IO」。目前 Netty、Envoy 都在实验性接入。但 JDK 本身还没跟进（截至 JDK 21），Java 生态用 io_uring 主要靠 Netty 的 `io.netty.channel.uring` 模块（native）。所以短期内 Java 服务端还是 NIO + epoll 的天下。

## 面试场景 5：select / poll / epoll 三代多路复用的区别 ★核心

🎤 面试官

Linux 上 `select`、`poll`、`epoll` 三代多路复用 API 的区别？为什么 epoll 快？

🧑‍💻 你

维度selectpollepoll

fd 数量上限**1024**（FD_SETSIZE 硬编码）无上限（链表）无上限（红黑树）
数据结构三个位图 fd_set（读/写/异常）`struct pollfd` 数组内核红黑树 + 就绪链表
每次调用是否拷贝 fd 集是（用户→内核，每次都拷）是（每次都拷）否（`epoll_ctl` 注册一次，内核长期持有）
就绪 fd 查找方式返回后**遍历所有 fd** O(n)返回后**遍历所有 fd** O(n)只返回**就绪的 fd** O(1)
内核通知机制轮询设备驱动轮询设备驱动设备就绪时**回调**把 fd 塞进就绪链表
触发模式只有 LT只有 LTLT + ET
跨平台几乎全平台Unix-like仅 Linux 2.6+

一句话总结 **epoll 快在哪**：

1. **省拷贝**：fd 集通过 `epoll_ctl` 一次注册到内核，之后 `epoll_wait` 不需要每次把 fd_set 从用户态拷到内核。

2. **省遍历**：内核用回调机制（就绪时把 fd 挂到就绪链表），`epoll_wait` 返回的直接是就绪列表，用户不需要 O(n) 扫一遍所有 fd 看谁就绪。

3. **无上限**：红黑树管理 fd，理论上限就是系统 fd 上限（`ulimit -n`）。

所以在高并发（10K+ 连接）、活跃比例低（大部分空闲）的场景，epoll 相比 select 是数量级的性能差距。

追问 `epoll_create`、`epoll_ctl`、`epoll_wait` 三个系统调用分别做什么？

**`epoll_create(size)`**：在内核创建一个 epoll 实例（一个红黑树 + 一个就绪链表），返回一个 fd。**`epoll_ctl(epfd, op, fd, event)`**：把某个 fd「注册/修改/删除」到 epoll 实例。`op` 是 `EPOLL_CTL_ADD`/`MOD`/`DEL`；`event` 指定感兴趣的事件（`EPOLLIN`/`EPOLLOUT`/`EPOLLET`）。**`epoll_wait(epfd, events, maxevents, timeout)`**：阻塞等待就绪事件，把就绪链表拷贝到用户传入的 `events` 数组返回。就绪列表由内核维护 —— 硬件驱动收到数据触发中断 → 内核回调把 fd 挂到就绪链表 → 唤醒 `epoll_wait`。

追问 select 的 1024 上限是硬件限制还是软件限制？能不能改？

**是编译期硬编码的宏**（`FD_SETSIZE`），不是硬件限制。理论上可以改内核头文件后重编 glibc + 内核绕过，但没人这么做 —— 因为即使把上限调到 10 万，select 的 O(n) 遍历和每次拷贝 fd_set 的开销还是让它没法用。业界的解法是直接切 poll / epoll，而不是硬撑 select。

## 面试场景 6：epoll 的 LT 和 ET 触发模式有什么区别？

🎤 面试官

epoll 的 **LT（水平触发）** 和 **ET（边缘触发）** 分别是什么？为什么 Netty 和 Redis 都默认用 LT？

🧑‍💻 你

两个模式描述的是「什么时候通知你 fd 就绪」：

- **LT（Level Triggered，水平触发，默认）**：**只要缓冲区里还有数据没读完，每次 `epoll_wait` 都会通知你**。你可以只读一部分、下次再读，epoll 会继续「提醒」直到读完。

- **ET（Edge Triggered，边缘触发）**：**只在 fd 状态从「未就绪」变为「就绪」的那个瞬间通知一次** —— 之后即使缓冲区还有数据，也不再通知。所以 ET 模式下用户**必须一次把数据全读完**（循环 `read` 直到返回 `EAGAIN`），否则剩下的数据就没机会再被处理了。

对比：

```
数据到达 socket 缓冲区（1000 字节）
│
▼
┌────────────── LT 模式 ──────────────┐
│  epoll_wait 返回 → 我 read 300 字节 │
│  epoll_wait 返回 → 我 read 300 字节 │  ← 只要缓冲区非空，就一直通知
│  epoll_wait 返回 → 我 read 400 字节 │
│  缓冲区空 → 不再通知                │
└─────────────────────────────────────┘

┌────────────── ET 模式 ──────────────┐
│  epoll_wait 返回一次（从无到有）    │
│  我必须 while(true) read 直到 EAGAIN│  ← 只通知这一次！
│  如果只 read 300 字节就退出         │
│  剩下 700 字节永远没人处理 → bug    │
└─────────────────────────────────────┘
```

为什么 **Netty / Redis 默认用 LT**？

1. **编程简单、不容易漏数据**：LT 允许「先处理一部分，下轮再处理」，容错性强。ET 一旦漏读或没循环到 EAGAIN 就丢数据。

2. **可以平滑限流**：LT 下可以每次只读一定量，避免单个连接把 Worker 线程占太久（重要！Netty 里靠 `maxMessagesPerRead` 控制）。

3. **性能差距其实不大**：ET 号称减少 `epoll_wait` 调用次数，但现代场景下这点开销可以忽略；反而 ET 需要用户配合非阻塞 IO + 死循环读，出 bug 概率高。

Nginx 是默认 ET 的经典 —— 因为它对性能极致追求，愿意用编程复杂度换那一点点系统调用节省。

追问 ET 模式下为什么必须配合非阻塞 socket？

因为 ET 下你要写 `while (true) { int n = read(fd, buf); if (n <= 0) break; }` 循环读到「读不到为止」。如果 socket 是**阻塞**的，当缓冲区读空后再调 `read` 会**永久阻塞**整个线程 —— Worker 就废了。**非阻塞**模式下缓冲区空时 `read` 返回 `-1` 且 `errno = EAGAIN`，你 `break` 出循环去处理下一个就绪 fd。所以 **ET = 非阻塞 fd + while 读到 EAGAIN**，这是绑死的组合。

## 面试场景 7：Java Selector 底层用的是什么？跨平台怎么办？

🎤 面试官

Java 的 `Selector.open()` 拿到的 Selector，底层到底是 select 还是 epoll？在不同 OS 上一样吗？

🧑‍💻 你

JDK 会根据 OS 自动选**最优的多路复用机制**：

操作系统Java Selector 底层Provider 实现类

Linux 2.6+`epoll_wait`（JDK 6+ 默认）`EPollSelectorProvider`
Linux 2.4 及更早`poll``PollSelectorProvider`
macOS / BSD`kqueue``KQueueSelectorProvider`
Windows`select`（NIO 用）；`IOCP`（仅 AIO 用）`WindowsSelectorProvider`
Solaris`/dev/poll` 或 event port`DevPollSelectorProvider`

可以用 `-Djava.nio.channels.spi.SelectorProvider=xxx` 手动指定，但基本没必要。JDK 6+ 在 Linux 上默认就是 epoll，所以 Java 服务端在 Linux 上跑天然享受 epoll 的性能。

一个隐藏彩蛋：**Windows 的 Java Selector 用的是 select** —— 所以 Windows 上跑高并发 Java 服务端性能相对差。这就是为什么生产环境 Java 服务几乎都跑 Linux。

追问 Netty 为什么还要自己写一个 Native Epoll Transport（`EpollEventLoopGroup`）？

因为 JDK 自带的 `EPollSelectorProvider` 有几个不完美的点：**①** 只暴露 LT 模式，用不了 ET；**②** 有历史 bug（著名的「epoll 空轮询」bug，Netty 靠计数重建 Selector 绕过）；**③** 不支持 Linux 独有的 `SO_REUSEPORT`、`TCP_CORK`、`TCP_QUICKACK` 等 socket 选项。Netty 用 JNI 直接调 Linux 原生 epoll API，避开了这些坑、还能用上 ET 和一些 Linux 特有优化 —— 是「同一台 Linux 上跑得更快」的黑魔法。生产上 Netty 服务端建议开 Native Epoll。

## 面试场景 8：Reactor 模式是什么？Netty 和 Redis 用的是哪种？

🧑‍💻 你

**Reactor 模式**是「基于 IO 多路复用的事件驱动架构」，是 Netty、Redis、Nginx、Vert.x 的底层通用范式。核心角色：

- **Reactor（分发器）**：跑在专门的线程里，循环调 `selector.select()` 拿到就绪事件，按事件类型分发给不同的 Handler。

- **Acceptor**：专门处理新连接（`OP_ACCEPT`），把新 Channel 注册到 Selector。

- **Handler**：处理 `OP_READ`/`OP_WRITE`，做真正的业务读写。

按 Reactor 数量分三种：

1. **单 Reactor 单线程**：一个线程既 `select` 又处理业务。*Redis 6.0 之前的模型*。优点：无锁；缺点：单核瓶颈。

2. **单 Reactor 多线程**：Reactor 线程只做 `select` + 分发，业务处理丢给 Worker 线程池。

3. **主从 Reactor（Master-Worker）**：**Main Reactor** 只处理 `OP_ACCEPT`；接受连接后把 Channel 交给 **Sub Reactor 池**；Sub Reactor 各自跑一个线程，负责自己名下 Channel 的 `OP_READ`/`OP_WRITE`。*Netty 默认就是这种* —— `bossGroup` = Main Reactor，`workerGroup` = Sub Reactor 池。

为什么高性能网络框架都选这个模式？**把「等 IO」和「处理业务」解耦** —— 少量线程扛住海量连接（等 IO），CPU 密集的业务再走 Worker，两边不互相阻塞。

追问 Redis 6.0 的「多线程 IO」具体多线程了什么？

**只有网络 IO 的 read/write 是多线程的，命令执行仍然是单线程**。具体：主线程从 socket 缓冲区收到请求 → 把「解析请求 + 写回响应」分给 IO 线程池并行做 → 请求解析完成后**回到主线程**串行执行命令 → 结果写入输出缓冲区再交给 IO 线程池并行 write。之所以命令保持单线程，是**为了保持 Redis 原有的「命令原子性 + 无锁数据结构」优势** —— 一旦多线程执行命令，所有 `SET`/`ZADD`/`HSET` 都要加锁，性能反而下降。6.0 只解决了「网络 IO 成为瓶颈」的场景（大 value、pipelining），是最小侵入式改造。

追问 Netty 是「同步」还是「异步」框架？

严格从 IO 模型角度：**Netty 是同步非阻塞（NIO + 多路复用）**。因为它底层用 `selector.select()` + 用户态 `read()`，read 那一步还是同步调用。**但从 API 使用者角度看是异步的** —— 所有操作（`writeAndFlush`、`bind`、`connect`）都返回 `ChannelFuture`，可以挂 listener 回调、不阻塞调用线程。这是把 *底层同步* 用 *事件回调 API 包装成异步语义* —— 面试要抠字眼时按「底层同步、编程模型异步」回答最准确。

## 面试场景 9：BIO / NIO / AIO 场景怎么选？

🧑‍💻 你

维度BIONIO（+ 多路复用）AIO

IO 模型同步阻塞同步非阻塞异步非阻塞
连接数少（< 100）多（10K+）多
连接活跃度高（每连接高吞吐）低（大量空闲长连接）高（长期读写）
编程复杂度低（顺序阻塞代码）中（事件回调，容易出 bug）高（回调地狱）
Linux 性能差（线程爆炸）好（epoll）一般（内核未原生支持）
典型场景内部 RPC 长连接、数据库连接池IM、聊天、推送、Web 服务、Netty大文件异步读写（少见）
代表框架Tomcat 7 之前默认 ConnectorNetty、Vert.x、Tomcat NIO Connector、Undertow较少（Netty 曾用过又放弃）

**结论**：生产环境 **99% 场景用 NIO**（框架层通常就是 Netty 或封装 Netty 的东西）。BIO 只在遗留代码或极简场景出现。AIO 在 Linux 上没有实质收益，反而 API 复杂，几乎被行业淘汰 —— 等 `io_uring` 生态成熟后可能翻身。

## 面试场景 10：Netty 为什么选 NIO 而不选 AIO？

🎤 面试官

你说 AIO 是异步、性能应该更好，为什么 Netty 反而用 NIO？

🧑‍💻 你

Netty 官方给过明确的解释，核心四点：

1. **Linux 上 AIO 没有真正的内核支持**：JDK 的 AIO 在 Linux 上用 epoll 模拟，本质还是 IO 多路复用。这层用户态模拟不但没提升性能，反而多了一层调度开销。

2. **Linux 上 AIO 不成熟、有 bug**：早期 `AsynchronousChannelGroup` 存在稳定性和内存使用问题，生产环境风险高。

3. **API 复杂、编程模型不友好**：AIO 强制走 `CompletionHandler` 回调，写起来嵌套深、错误处理散乱；Netty 自己的 `ChannelFuture` + `Promise` 已经把 NIO 包装得非常易用。

4. **NIO 已经足够快**：Netty 主要面向服务端网络编程，NIO + epoll + Reactor 模型在 Linux 上已经能扛百万连接（Netty 官方 benchmark），没有必要为了「架构上更纯粹」去承担 AIO 的复杂度。

换句话说：**「异步 IO」 是操作系统概念，「异步 API」 是编程模型概念**。Netty 用底层同步 IO + 上层异步 API 的组合，在实际工程里比「底层异步 + 上层也异步」的 AIO 方案更实用。

追问 零拷贝（zero-copy）是什么？和 IO 模型是什么关系？

**零拷贝**：减少数据在**内核态和用户态之间的拷贝次数**。传统 `read`+`write` 发文件：磁盘 → 内核 pagecache → **用户 buffer** → 内核 socket buffer → 网卡，共 4 次拷贝 + 4 次上下文切换。零拷贝可以省掉「用户 buffer」这一趟，甚至直接从 pagecache DMA 到网卡。Java 里的实现：**①** `FileChannel.transferTo(...)` —— 底层用 Linux `sendfile`；**②** `MappedByteBuffer`（`mmap`） —— 用户态和内核态共享内存映射；**③** Netty 的 `CompositeByteBuf` / `FileRegion`。**和 IO 模型关系**：正交概念 —— IO 模型解决「怎么感知就绪」，零拷贝解决「怎么少拷贝一次」。Kafka、Netty、Nginx 都大量用零拷贝，是海量数据吞吐的关键优化。第 0041 课会专门讲。

## 💻 代码验证

### 验证 1：BIO 一连接一线程（观察 10K 连接线程爆炸）

```
// BIOServer.java
import java.io.*;
import java.net.*;

public class BIOServer {
public static void main(String[] args) throws IOException {
ServerSocket server = new ServerSocket(9000);
System.out.println("BIO server listening on 9000");
while (true) {
Socket socket = server.accept();     // ← 阻塞 1：等新连接
new Thread(() -> handle(socket)).start();
}
}
static void handle(Socket socket) {
try (InputStream in = socket.getInputStream()) {
byte[] buf = new byte[1024];
int n = in.read(buf);                // ← 阻塞 2：等数据
System.out.println("recv " + n + " bytes on thread " + Thread.currentThread().getName());
} catch (IOException e) { e.printStackTrace(); }
}
}
// 用 ab 或 wrk 打 10K 并发观察：jstack 会看到 10K 个 Thread-N，
// 每个都阻塞在 socket.read()。JVM 可能直接 OOM: unable to create native thread。
```

### 验证 2：NIO Selector 单线程处理多连接

```
// NIOServer.java
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.*;
import java.util.Iterator;

public class NIOServer {
public static void main(String[] args) throws IOException {
Selector selector = Selector.open();
ServerSocketChannel server = ServerSocketChannel.open();
server.bind(new InetSocketAddress(9000));
server.configureBlocking(false);          // ← 关键：非阻塞
server.register(selector, SelectionKey.OP_ACCEPT);
System.out.println("NIO server listening on 9000");

while (true) {
selector.select();                    // ← 阻塞等任意 Channel 就绪
Iterator<SelectionKey> it = selector.selectedKeys().iterator();
while (it.hasNext()) {
SelectionKey key = it.next();
it.remove();                      // ← 必须 remove，否则重复处理
if (key.isAcceptable()) {
SocketChannel client = server.accept();
client.configureBlocking(false);
client.register(selector, SelectionKey.OP_READ);
} else if (key.isReadable()) {
SocketChannel client = (SocketChannel) key.channel();
ByteBuffer buf = ByteBuffer.allocate(1024);
int n = client.read(buf);
if (n > 0) {
buf.flip();
System.out.println("recv " + n + " bytes");
} else if (n == -1) {
client.close();
}
}
}
}
}
}
// 单个线程扛住 10K 空闲连接毫无压力 —— jstack 只看到 main 线程阻塞在 select()。
```

### 验证 3：AIO 用 CompletionHandler 感受回调风格

```
// AIOServer.java
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.*;

public class AIOServer {
public static void main(String[] args) throws Exception {
AsynchronousServerSocketChannel server =
AsynchronousServerSocketChannel.open().bind(new InetSocketAddress(9000));
System.out.println("AIO server listening on 9000");

server.accept(null, new CompletionHandler<AsynchronousSocketChannel, Object>() {
@Override
public void completed(AsynchronousSocketChannel client, Object att) {
server.accept(null, this);       // ← 继续接受下一个（递归注册）
ByteBuffer buf = ByteBuffer.allocate(1024);
client.read(buf, buf, new CompletionHandler<Integer, ByteBuffer>() {
@Override public void completed(Integer n, ByteBuffer b) {
b.flip();
System.out.println("recv " + n + " bytes (async)");
}
@Override public void failed(Throwable exc, ByteBuffer b) {
exc.printStackTrace();
}
});
}
@Override
public void failed(Throwable exc, Object att) { exc.printStackTrace(); }
});
Thread.currentThread().join();           // 主线程别退出
}
}
// 感受到「回调套回调」的复杂度了吗？这就是为什么 Netty 抛弃 AIO 的原因之一。
```

### 验证 4：用 `strace` 观察 Java Selector 底层调 epoll

```
# Linux 上跑上面的 NIOServer，另开一个终端
$ jps                                 # 找到 java 进程 pid
12345 NIOServer

$ sudo strace -p 12345 -e trace=epoll_create,epoll_ctl,epoll_wait
epoll_create1(EPOLL_CLOEXEC)         = 7      ← Selector.open() 底层
epoll_ctl(7, EPOLL_CTL_ADD, 8, ...)  = 0      ← register(OP_ACCEPT)
epoll_wait(7, [{EPOLLIN, fd=8}], 8192, -1)    ← selector.select()
epoll_ctl(7, EPOLL_CTL_ADD, 9, ...)  = 0      ← 新客户端注册 OP_READ
epoll_wait(7, [{EPOLLIN, fd=9}], 8192, -1)    ← 又一次 select
...
# 眼见为实：JDK 的 Selector 在 Linux 上就是三个 epoll 系统调用的封装。
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话区分「同步/异步」和「阻塞/非阻塞」。</summary>

「同步/异步」讲结果由**谁通知**（我自己拿 vs 对方回调我）；「阻塞/非阻塞」讲等结果时**线程会不会被 OS 挂起**。两组概念正交，交叉出 IO 模型的四象限。

</details>

<details>

<summary>Q2 为什么 BIO 扛不住 C10K？</summary>

BIO 是「一连接一线程」，1 万连接需要 1 万线程 —— 光线程栈内存就要 10GB（默认每线程 1MB），加上上下文切换开销把 CPU 打满，大部分线程还都在闲置等 IO。突破方式是 NIO + 多路复用（Selector / epoll），一个线程管所有连接的事件。

</details>

<details>

<summary>Q3 epoll 相比 select 快在哪三点？</summary>

① **无 1024 fd 上限**（红黑树 vs 位图）；② **不用每次拷贝 fd 集到内核**（`epoll_ctl` 一次注册，长期持有）；③ **就绪 fd 直接从内核回调式就绪链表拿到**，O(1) 拿到就绪集，无需 O(n) 遍历所有 fd。

</details>

<details>

<summary>Q4 epoll 的 LT 和 ET 有什么区别？Netty 为什么用 LT？</summary>

LT（水平触发）：只要缓冲区有数据，每次 `epoll_wait` 都通知；ET（边缘触发）：只在「从无到有」的瞬间通知一次，用户必须循环读到 `EAGAIN`。Netty 用 LT 是因为编程简单不易漏数据、可以限流（`maxMessagesPerRead`）、性能差距可忽略。

</details>

<details>

<summary>Q5 Netty 为什么不用 AIO？</summary>

① Linux 的 AIO 底层还是用 epoll 模拟，没真异步；② API 复杂、CompletionHandler 回调不易用；③ Linux 上 AIO 有稳定性问题；④ NIO + epoll + Reactor 已经足够扛百万连接，没必要换。*本质：「异步 IO 模型」和「异步 API 编程」是两件事，Netty 选了底层同步、上层异步 API 的组合。*

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Linux man page · `epoll(7)` —— epoll 三个系统调用官方文档

- Netty · Native Transports (Epoll / KQueue / io_uring) —— Netty Native Epoll 的动机

- 《UNIX 网络编程 卷1》第 6 章 —— 五种 IO 模型的经典阐述

#### 🔗 关联课件

-

- （下一课）

-

-

#### 🧭 下一课预告

Lesson 0040：**NIO 核心：Buffer 三指针 / Channel 类型 / Selector 事件循环** —— 本课的第 3 场景要深挖的地方，包括 `flip()`/`clear()`/`compact()` 的差异、直接内存 vs 堆内存 Buffer、以及 Netty 里 `ByteBuf` 相比 JDK `ByteBuffer` 的改进。

💬 有任何疑问 —— 「epoll 的红黑树是怎么组织的？」「主从 Reactor 里 Sub Reactor 之间会互相抢连接吗？」「LT 下 Netty 具体怎么防止一个 Channel 饿死其他 Channel？」—— 直接问我。IO 模型这一章的追问深度可以一直挖到内核源码，别客气。


