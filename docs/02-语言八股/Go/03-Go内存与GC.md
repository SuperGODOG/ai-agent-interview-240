# 03 · Go 内存与 GC 八股

## 一、内存分配

### 基本模型（借鉴 tcmalloc）
- 大块内存从操作系统申请（mheap），切成不同大小等级的 span（mspan，8B ~ 32KB 共约 67 个等级）。
- mcache：每个 P 一个本地缓存，无锁分配小对象；不够了向 mcentral 申请，mcentral 不够向 mheap 申请。
- 小对象（<=32KB）按大小分级分配；大对象（>32KB）直接从 mheap 分配。

### 栈 vs 堆
- 栈：函数帧，自动分配/释放，快；goroutine 栈初始 2KB，动态扩缩。
- 堆：需要 GC 管理；分配慢（还要回收）。
- 面试点：变量到底在栈还是堆 → 看**逃逸分析**。

## 二、逃逸分析（必考）

### 是什么
- 编译器（go 编译器，不是 runtime）分析变量作用域：判断变量能不能分配在栈上；只要生命周期逃出函数就"逃逸"到堆。

### 常见逃逸场景
1. 返回局部变量指针：`func f() *T { x := T{}; return &x }` → x 逃逸。
2. 闭包捕获变量：闭包被返回/长期持有 → 捕获变量逃逸。
3. 接口装箱：把具体类型赋给 interface{}，编译器不确定实际类型 → 可能逃逸。
4. 大对象：编译器认为栈放不下 → 堆。
5. 变量被 map/slice（堆上）持有：如 append 指针到 slice → 逃逸。

### 怎么看
- `go build -gcflags="-m"` 或 `go tool compile -m main.go`：输出 "escapes to heap"。

### 为什么关心
- 逃逸到堆增加 GC 压力，性能敏感路径要减少无谓逃逸。
- 例子：字符串转 []byte 有拷贝，但编译器可能优化（非逃逸时）避免拷贝。

## 三、垃圾回收（必考）

### 算法：并发三色标记清除
- 三色：白（未访问/可能垃圾）→ 灰（自身已访问，引用的对象还没处理）→ 黑（已处理完）。
- 流程：
  1. 标记开始（STW，极短）：根对象（全局变量、栈、寄存器）置灰。
  2. 并发标记：从灰色对象出发扫描，把引用的白色置灰，处理完置黑；期间应用继续跑。
  3. 标记结束（STW 很短）：剩余的白色对象是不可达 → 垃圾。
  4. 清除：回收白色对象内存（Go 的清除是懒清除，边分配边清）。
- 因为没有 mark-sweep 的整理，Go 堆会有碎片，由大小分级缓解。

### 写屏障（关键）
- 并发标记时应用还在改对象引用，可能"黑色对象指向白色对象"导致垃圾被误收。
- 混合写屏障（Go 1.8+）：在堆写入时插入屏障，保证"黑色对象新增的引用对象至少置灰"。
- 结果：允许对象在 GC 期间移动（如栈重扫），把 STW 压到亚毫秒级。

### GC 触发
- 堆增长：上次 GC 后的堆大小 × GOGC（默认 100，即翻倍触发）。
- 定时（后台触发）；手动 runtime.GC()（生产一般不手动）。
- GOGC 调大 → 更少 GC、内存峰值更高；调小 → 更频繁、内存更平稳。GOGC=off 关闭（慎用）。

### 为什么 Go 的 GC 停顿低
- 三色并发标记 + 混合写屏障 + 清除懒执行；STW 只发生在标记开始/结束的极小窗口。

## 四、内存与 goroutine 泄漏场景（必考）

1. goroutine 泄漏：
   - 阻塞在无接收者的 channel 发/收；select 没配超时/ctx。
   - for 循环起 goroutine 且不退出（每请求一个永不结束的 goroutine）。
   - 解决：context 取消、select+timeout、errgroup。
2. time.Ticker 未 Stop：ticker 一直占定时器资源。
3. 全局缓存无限增长：map/slice 只加不减 → 用带淘汰的缓存。
4. 大对象被长期引用：某 goroutine 持有巨大 slice 的头部引用不放。
5. 资源未关闭：文件/DB/HTTP 连接泄漏（defer Close + 检查错误）。

### 排查
- pprof goroutine profile：看哪个函数 goroutine 数量异常。
- heap profile：看内存被谁持有（`go tool pprof` 看 inuse_space，配 -base 对比增量）。
- 线上工具：gops、go-pprof（net/http/pprof 暴露端口）。

## 五、pprof 性能排查（必考流程）

- 引入 `_ "net/http/pprof"`，访问 /debug/pprof/。
- 采集：
  - CPU：`go tool pprof http://host/debug/pprof/profile?seconds=30`
  - 堆：`.../heap`（-inuse_space 当前占用 / -alloc_space 累计分配）
  - goroutine：`.../goroutine`（看数量、看阻塞）
  - block / mutex：锁竞争。
- 分析：top 看热点函数；list 看行级；web 出火焰图。
- 常见结论：字符串拼接热点、锁竞争、GC 频繁（先看 alloc 再优化）、syscall 阻塞。

## 六、常问追问

1. 变量什么时候逃逸到堆？→ 返回指针、闭包、接口装箱、大对象、被堆结构持有。
2. 逃逸分析是谁做的？→ 编译器，不是 runtime。
3. 三色标记为什么不会误收？→ 写屏障保证黑色对象新引用至少置灰。
4. STW 发生在什么时候？→ 标记开始/结束的极小窗口。
5. GOGC 是什么？→ 堆增长触发阈值，默认 100；调大省 GC 涨内存。
6. 为什么 goroutine 会泄漏？→ 阻塞等待永不满足；要用 ctx/超时兜底。
7. pprof 怎么定位内存泄漏？→ heap profile 两次对比，看增长。
8. Go 的清除为什么懒？→ 标记完不立刻扫全堆，边分配边清，摊平开销。
9. mcache 为什么每 P 一个？→ 无锁分配，避免多线程竞争。
10. 栈会无限增长吗？→ 有上限（默认 1GB 64 位），超限程序崩溃（goroutine stack exceeds）。
