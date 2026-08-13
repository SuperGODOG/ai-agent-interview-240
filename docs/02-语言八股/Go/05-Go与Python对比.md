# 15 · Go 与 Python：共性与区别（学 Go 的引导篇）

> 目标：如果你已经会 Python，这篇帮你用最短路径理解 Go 是什么、和 Python 像在哪、差在哪，以及怎么开始学。

## 一、共性（Go 对你来说不会陌生）

| 维度 | 共同点 |
| --- | --- |
| 语法简洁 | 两者都强调代码简洁、可读性，缩进/短小函数文化接近 |
| 自动内存管理 | 都有垃圾回收，不用手动 free |
| 标准库强大 | 网络、JSON、加密、压缩、测试基本开箱即用 |
| 快速上手 | 都能"写小脚本快速验证想法"（Go 也可以当脚本写，`go run`） |
| 跨平台 | 都能在 Windows/Linux/macOS 开发部署 |
| 服务端友好 | 写 HTTP 服务、CLI 工具都很顺手 |
| 并发是卖点 | Python 有 asyncio 协程；Go 有 goroutine（概念上同源，Go 更彻底） |

一句话：Python 里"写起来快"的感觉，Go 同样有；只是"解释执行"换成了"编译执行"。

## 二、核心区别（面试/选型必讲）

### 1. 类型系统：动态 vs 静态
- Python：运行时才确定类型，鸭子类型，写起来自由但大项目靠类型注解（mypy）兜底。
- Go：静态强类型，编译期检查；但用 `:=` 类型推断，写起来并不啰嗦：
```go
name := "go"        // 自动推断 string，不用写类型
var n int = 1       // 显式声明也可以
```
- 迁移感受：从"不写类型"到"类型自动推"，适应成本很低；换来的是改代码时编译器帮你找错。

### 2. 性能：解释执行 vs 编译执行
- Python：字节码解释执行 + GIL，慢（IO 场景可用协程弥补）。
- Go：直接编译成机器码，接近 C 的性能；没有 GIL，多核并行。
- 量级感受：同样的 CPU 计算，Go 通常比 Python 快 10~100 倍；启动速度也是毫秒级 vs 秒级。

### 3. 并发模型：GIL 与协程 vs goroutine
- Python：多线程被 GIL 限制，CPU 密集靠多进程；协程靠 asyncio 手动组织事件循环。
- Go：goroutine 由 runtime 调度（GMP），几 KB 一个，百万级随便开；channel 通信，语言级支持。
- 对比：asyncio 的 `async/await` 和 Go 的 `go func()`，Go 把"协程"做成了默认公民，不用想"该不该用"。

### 4. 面向对象：类 vs 结构体 + 接口
- Python：class、继承、多态，一切皆对象。
- Go：没有类、没有继承；用 struct 装数据，方法绑定在类型上，接口是隐式实现。
```go
type Dog struct{ Name string }
func (d Dog) Speak() string { return "汪汪" }   // 方法绑定
```
- 迁移感受：把"继承"换成"组合 + 接口"，更简单也更灵活；概念要重新理解，但代码更直白。

### 5. 错误处理：异常 vs 返回值
- Python：try/except 捕获异常，任何地方都可能抛。
- Go：函数返回 (result, error)，显式检查错误（几乎每步都 if err != nil）。
```go
f, err := os.Open("x.txt")
if err != nil { return err }
```
- 迁移感受：从"默认可能抛异常"变成"错误是值，必须面对"，一开始觉得啰嗦，久了发现错误路径不会漏。

### 6. 部署形态：解释器 vs 单二进制
- Python：环境依赖（Python 版本 + pip 包），部署要配虚拟环境/容器。
- Go：编译成一个二进制文件，无依赖，扔到服务器就能跑；容器镜像可以小到几 MB。

### 7. 生态方向
- Python 强在：AI/数据分析、脚本、爬虫、科学计算（numpy/pandas/torch）。
- Go 强在：后端服务、微服务、云原生（K8s/Docker 本身是 Go 写的）、中间件、网关、CLI 工具、区块链。
- 两者不是替代关系：同一家公司常"AI 部分用 Python，核心服务用 Go"。

## 三、Python 知识 → Go 对照表（快速迁移）

| Python | Go | 备注 |
| --- | --- | --- |
| list | slice（[]T） | 底层是数组视图，有 len/cap/append |
| dict | map | 都是哈希表；Go 的 map 并发写会崩，要加锁 |
| tuple | struct / 多返回值 | Go 没有元组，用多返回值替代 |
| str（Unicode） | string（UTF-8）+ rune | 按字节/码点区分 |
| 类 + 继承 | struct + 嵌入（组合） | 没有继承，组合替代 |
| 抽象基类/接口 | interface（隐式实现） | Go 的接口不需要声明 implements |
| 异常 try/except | error 返回值 | 业务错误显式返回 |
| 生成器 yield | channel + goroutine | 数据流式处理对应管道模式 |
| asyncio | goroutine + channel | 并发主力 |
| 装饰器 | 函数作为一等公民 + 高阶函数 | Go 函数也可以传参/返回，但没语法糖 |
| 列表推导式 | 没有 | 用循环或泛型工具替代 |
| pip + venv | go mod | 模块化依赖管理 |
| @dataclass | struct + json tag | 数据对象定义 |

## 四、Go 的学习路线（从零到能写项目）

### 阶段一：语法基础（1 周）
- 变量/类型/流程控制/函数/多返回值
- struct、方法、接口
- slice、map、string
- 指针（理解"值 vs 引用"）
- 练习：LeetCode 简单题用 Go 刷 20 道（顺便熟悉语法）

### 阶段二：并发（1 周，Go 的灵魂）
- goroutine、channel、select
- sync 包：Mutex/WaitGroup/Once/atomic
- context（超时与取消）
- GMP 模型（面试要能讲清）
- 练习：写一个并发下载器 / worker pool

### 阶段三：标准库与 Web（1 周）
- net/http 写 REST API、中间件
- encoding/json（结构体 tag）
- 文件/日志/配置读取
- 练习：写一个 TODO API（增删改查 + 内存存储）

### 阶段四：工程化（1 周）
- go mod 依赖管理、项目目录结构
- 单元测试、表驱动测试、go test -race
- 数据库接入（database/sql 或 GORM）
- pprof 性能分析
- 练习：把 TODO API 接上 MySQL/Postgres + 加缓存

### 阶段五：小项目实战（2~4 周）
- 做一个带 JWT 认证的用户系统
- 或一个短链接服务（Redis 缓存 + 限流）
- 或一个简单的消息队列/任务调度器
- 或参与开源（K8s 周边、CLI 工具）

### 推荐资源
- 官方教程：A Tour of Go（必刷，2 小时）
- 书：《The Go Programming Language》（Go 圣经）
- 中文：《Go 语言圣经》译本、《Go 语言趣学指南》
- 进阶：《100 个 Go 错误》、《Go 专家编程》（并发/GC 深挖）
- 练习平台：exercism.org/go、LeetCode、Go By Example

## 五、从 Python 过渡的常见误区

1. 以为 Go 有类：没有，用 struct + 方法 + 接口。
2. 到处用异常：Go 用 error，忘检查 = 静默 bug。
3. map 当普通容器随便并发写：Go 直接崩，必须加锁。
4. 切片当 Python list 用：append 扩容、共享底层数组要心里有数。
5. 不习惯 err != nil：这是 Go 的"显式优于隐式"，接受它。
6. 忽略零值：Go 每个变量有零值，`var s []int` 是 nil 但可以 append。
7. 把 goroutine 当线程随便开：泄漏和 panic 是常见线上事故，注意生命周期管理。

## 六、为什么值得学（面试视角 + 职业视角）

- 面试：Go 岗位（后端/云原生/中间件）需求增长快；会 Python 又懂 Go 的"双语开发者"是加分项。
- 职业：Go 是云原生时代的事实标准语言（Docker、K8s、Prometheus、etcd 全是 Go），容器/微服务岗位几乎都要求。
- 学习成本：对有 Python 基础的人，Go 语法量很小，2~3 周就能写项目，性价比很高。

## 七、常问追问

1. Python 和 Go 怎么选？→ 业务开发/快速迭代/AI 用 Python；性能敏感/高并发/云原生基础设施用 Go。
2. Go 能替代 Python 吗？→ 不能，生态不同；Go 也能写脚本但 AI/数据分析生态差远了。
3. 有 Python 基础学 Go 难吗？→ 不难，语法比 Python 还少；主要新概念：指针、struct 方法、goroutine、error。
4. Go 的并发和 asyncio 哪个强？→ 场景不同；Go 的 goroutine 更轻、调度更彻底，asyncio 需要手动管理循环。
5. 为什么 Go 编译快？→ 编译器设计（简单类型系统、无模板实例化爆炸、并行编译），秒级出二进制。
6. Go 适合做 AI 吗？→ 生态弱；但模型服务网关/推理调度可以用 Go 做（性能好）。
7. 学 Go 之前要补什么？→ 有 Python 基础即可；建议补一点计算机基础（进程线程、内存、网络），Go 离系统更近。
8. Go 和 Java 比呢？→ Go 更简单轻量、启动快、内存占用小；Java 生态/框架/大厂存量更大。
