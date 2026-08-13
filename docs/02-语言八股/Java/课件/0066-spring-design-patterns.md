****
> Lesson 0066 · 阶段八 · Spring 收尾 · ⭐⭐⭐ · 预计 60 分钟｜10 个面试场景 · 4 段可跑代码 · 5 道自测 · · 全课程收官 66/66 🎓

# 0066 · Spring 设计模式 & @Async 原理

这是 **66 节课的最后一节**。合并 与 —— 前者是宏观架构鉴赏，后者是 AOP 的一个具体应用。学完这一节，Java 后端八股的地图就*整个铺展开*了。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Spring 用了哪些经典设计模式？至少说出 5 个。</summary>

工厂（BeanFactory）、单例（默认 scope）、代理（AOP）、模板方法（JdbcTemplate）、观察者（ApplicationEvent）、适配器（HandlerAdapter）、责任链（HandlerInterceptor）、装饰器（BufferedInputStream 之类）、策略、命令等。第 1-8 题细讲。

</details>

<details>

<summary>Q0.2 `@Async` 忘记加 `@EnableAsync` 会怎样？</summary>

不生效！方法照常同步执行。因为没有 `@EnableAsync` 就没有 `AsyncAnnotationBeanPostProcessor`，也就不会给带 `@Async` 的 Bean 生成 AOP 代理。第 9 题细讲。

</details>

## 面试场景 1：Spring 的设计模式全景（★核心）

🎤 面试官

说说 Spring 用了哪些设计模式？各在什么地方？

🧑‍💻 你

模式应用位置作用

**工厂**`BeanFactory` / `ApplicationContext`集中创建 Bean，屏蔽 new 细节
**单例**Bean 默认 `scope=singleton`容器级别共享实例，省资源
**代理**Spring AOP（JDK 动态代理 / CGLIB）横切关注点（事务/日志/权限）
**模板方法**`JdbcTemplate` / `RestTemplate` / `TransactionTemplate`固定骨架 + 回调填空
**观察者**`ApplicationEvent` / `ApplicationListener`事件驱动解耦
**适配器**`HandlerAdapter` / `AdvisorAdapter`让不兼容接口协同工作
**责任链**`HandlerInterceptor` / Filter 链多个处理器依次处理请求
**装饰器**BufferedInputStream 家族（Java 层）；Spring 里较少不修改类的前提下增强行为
**策略**`Resource` 家族（ClassPathResource / UrlResource / FileSystemResource）同一接口多种实现按需选择
**命令**Spring MVC 的 `Command` 对象请求参数封装成命令对象

## 面试场景 2：工厂模式 —— BeanFactory 是最典型的工厂

🧑‍💻 你

```
// 你想拿 Bean，不用 new
ApplicationContext ctx = new AnnotationConfigApplicationContext(AppConfig.class);
UserService svc = ctx.getBean(UserService.class);
// 由容器根据配置元数据（@Configuration / XML / 注解扫描）创建、装配、生命周期管理
```

好处：*调用方不用关心怎么创建*；扩展新 Bean 只需加注解或配置，无需改容器代码 —— 满足 OCP（开闭原则）。

追问 BeanFactory 和 FactoryBean 有什么区别？（★易混）

**BeanFactory** 是*容器*（生产 Bean 的工厂本身）；**FactoryBean** 是一种*特殊 Bean* —— 实现该接口的 Bean，容器返回的不是它本身而是它 `getObject()` 返回的东西（用来生产复杂对象，比如 MyBatis 的 `SqlSessionFactoryBean`）。

## 面试场景 3：单例模式 —— Bean 默认 scope

🧑‍💻 你

Spring 单例存在 `DefaultSingletonBeanRegistry` 里：

```
private final Map<String, Object> singletonObjects
= new ConcurrentHashMap<>(256);       // 一级缓存：完整 Bean
private final Map<String, Object> earlySingletonObjects
= new HashMap<>(16);                  // 二级缓存：早期引用（回顾 0061）
private final Map<String, ObjectFactory<?>> singletonFactories
= new HashMap<>(16);                  // 三级缓存：ObjectFactory
```

注意：**Spring 单例 ≠ 单例模式的经典实现**。经典单例是「类内私有构造 + 静态实例」，Spring 单例是「容器级别的 Map 缓存」—— 容器扔了 Bean 就没了，同一 JVM 里可以有多个容器实例，每个都有自己的单例池。

陷阱 单例 Bean 有**线程安全隐患**：多个请求线程共享同一个 Bean 实例，任何可变成员变量都可能竞态。解决：① 避免可变成员（无状态 Bean 最好）；② 用 `ThreadLocal`；③ 改 `@Scope("prototype")`（不推荐，性能差）。

## 面试场景 4：代理模式 —— AOP 的底盘

🧑‍💻 你

回顾  和 ：Spring AOP 就是*代理模式*的工程化应用。

- 目标类有接口 → JDK 动态代理（Proxy + InvocationHandler）

- 目标类无接口 → CGLIB（ASM 生成子类）

- Spring Boot 2.0+ 默认全 CGLIB，避免混用问题

**@Transactional、@Async、@Cacheable、@RateLimiter 等注解**本质都是「AOP 代理拦截 → 加通知」的应用。

## 面试场景 5：模板方法模式 —— JdbcTemplate

🧑‍💻 你

模板方法核心：**骨架代码固定，某些步骤由子类/回调填充**。

```
// JdbcTemplate 的固定骨架：
//   getConnection → prepareStatement → execute → 处理结果 → close
// 变化的部分（SQL + 参数 + 结果映射）通过 Lambda/回调传入

List<User> users = jdbcTemplate.query(
"SELECT * FROM users WHERE age > ?",
new Object[]{18},
(rs, i) -> new User(rs.getLong("id"), rs.getString("name"))   // RowMapper
);
```

你不用写「打开连接 → 关闭连接 → 处理异常」重复代码，交给模板即可。类似的还有 `RestTemplate`、`RedisTemplate`、`TransactionTemplate`。

## 面试场景 6：观察者模式 —— ApplicationEvent 事件

🧑‍💻 你

Spring 事件驱动模型三角色：

- **事件**：继承 `ApplicationEvent`（如 `ContextRefreshedEvent`、自定义 `OrderCreatedEvent`）

- **发布者**：注入 `ApplicationEventPublisher`，调 `publishEvent(event)`

- **监听者**：实现 `ApplicationListener<T>` 或注解 `@EventListener`；`@Async` 可让监听异步

```
// 事件
public class OrderCreatedEvent extends ApplicationEvent {
public final Long orderId;
public OrderCreatedEvent(Object src, Long orderId) { super(src); this.orderId = orderId; }
}

// 发布
@Service
public class OrderService {
@Autowired ApplicationEventPublisher publisher;
public void createOrder(...) {
// ... 业务
publisher.publishEvent(new OrderCreatedEvent(this, orderId));
}
}

// 监听
@Component
public class OrderCreatedNotifier {
@EventListener
@Async                         // 异步监听
public void onCreated(OrderCreatedEvent e) {
// 发短信/推消息/...
}
}
```

好处：*解耦*—— 下游依赖不用被 OrderService 感知，动态增减监听不改核心业务。

## 面试场景 7：适配器模式 —— HandlerAdapter

🧑‍💻 你

Spring MVC 里 Controller 有多种写法：`@Controller + @RequestMapping`、实现 `Controller` 接口、实现 `HttpRequestHandler`、函数式路由等。`DispatcherServlet` 不想为每种写法都写 `if-else`，就通过 **HandlerAdapter** 适配：

```
DispatcherServlet.doDispatch(req):
HandlerExecutionChain chain = handlerMapping.getHandler(req);   // 找处理器
HandlerAdapter adapter = getHandlerAdapter(chain.getHandler()); // 找适配器
adapter.handle(req, resp, chain.getHandler());                  // 统一入口
```

四大 HandlerAdapter：`RequestMappingHandlerAdapter`（注解式 Controller）、`SimpleControllerHandlerAdapter`（实现 Controller 接口）、`HttpRequestHandlerAdapter`、`HandlerFunctionAdapter`（WebFlux 函数式）。

## 面试场景 8：责任链 —— HandlerInterceptor

🧑‍💻 你

Spring MVC 的拦截器链：请求 → 多个 `HandlerInterceptor.preHandle` 依次调用 → Controller → 依次 `postHandle` → `afterCompletion`。任一 `preHandle` 返回 `false` 就打断。

```
@Component
public class AuthInterceptor implements HandlerInterceptor {
@Override
public boolean preHandle(HttpServletRequest req, HttpServletResponse resp, Object handler) {
if (!isLoggedIn(req)) {
resp.setStatus(401);
return false;    // 打断链条
}
return true;
}
}

// 注册
@Configuration
public class WebConfig implements WebMvcConfigurer {
@Autowired AuthInterceptor auth;
public void addInterceptors(InterceptorRegistry r) {
r.addInterceptor(auth).addPathPatterns("/api/**").excludePathPatterns("/api/login");
}
}
```

类似的：Servlet 的 Filter 链、Netty 的 ChannelPipeline、Spring Security 的 FilterChainProxy —— 都是责任链模式。

## 面试场景 9：@Async 注解原理（★核心）

🎤 面试官

`@Async` 是怎么让方法异步执行的？

🧑‍💻 你

本质是 **AOP 代理 + 线程池**：

1. 启动类 `@EnableAsync` → `@Import(AsyncConfigurationSelector.class)` → 加载 `ProxyAsyncConfiguration` → 注册 `AsyncAnnotationBeanPostProcessor`

2. 该后置处理器扫到带 `@Async` 的 Bean → 为其生成 AOP 代理（JDK/CGLIB）

3. 外部调用 `service.asyncMethod()` 走代理 → `AsyncExecutionInterceptor` 拦截

4. 拦截器把方法包成 `Callable`，*提交到线程池*；主线程立即返回

5. 子线程执行方法体；如果返回 `Future`，主线程可通过 `Future.get()` 拿结果

```
// 完整示例
@SpringBootApplication
@EnableAsync                    // ← 不加就没效果
public class App { ... }

@Service
public class MailService {
@Async                      // 走线程池
public void sendMail(String to) {
// 耗时的发邮件逻辑
}

@Async
public CompletableFuture<String> sendWithResult(String to) {
// ...
return CompletableFuture.completedFuture("sent");
}
}
```

陷阱 **默认线程池是 `SimpleAsyncTaskExecutor`！**每次任务都*新建一个线程*不复用 —— 高并发下线程数爆炸。*生产必须自定义 `ThreadPoolTaskExecutor`*：

```
@Bean("myExecutor")
public Executor myExecutor() {
ThreadPoolTaskExecutor exec = new ThreadPoolTaskExecutor();
exec.setCorePoolSize(10);
exec.setMaxPoolSize(50);
exec.setQueueCapacity(1000);
exec.setThreadNamePrefix("async-");
exec.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
exec.initialize();
return exec;
}
// 使用
@Async("myExecutor")
public void task() { ... }
```

## 面试场景 10：@Async 失效场景 & 返回值选择

失效场景原因解决

忘记 `@EnableAsync`没启用后置处理器启动类加 `@EnableAsync`
自调用 `this.async()`绕过代理（回顾 0062）注入 self / `AopContext.currentProxy()`
`static` 方法不参与继承代理无法拦截改非静态
`private` 方法JDK 代理不代理，CGLIB 也代理不了改 public/protected
返回非 `Future` 类型的值Spring 无处存放异步结果用 `Future` / `CompletableFuture`

**返回值类型选择**：

- `void`：不需要结果的后台任务（发邮件、写日志）；异常靠 `AsyncUncaughtExceptionHandler`

- `Future<T>` / `CompletableFuture<T>`：需要拿结果；推荐 `CompletableFuture`（能链式组合，回顾 ）

- 其他类型：**返回 null**！业务代码会拿到 null 引发 NPE，是常见坑

## 💻 代码验证

### 验证 1：手写 ApplicationEvent 观察者模式

```
// 事件
public class UserRegisteredEvent extends ApplicationEvent {
public final String email;
public UserRegisteredEvent(Object src, String email) {
super(src); this.email = email;
}
}

// 监听 1：发欢迎邮件
@Component
public class WelcomeMailListener {
@EventListener
@Async("myExecutor")
public void on(UserRegisteredEvent e) {
System.out.println("send welcome to " + e.email);
}
}

// 监听 2：增加统计计数（同步）
@Component
public class StatsListener {
@EventListener
public void on(UserRegisteredEvent e) { registeredCount.increment(); }
}

// 发布
@Service
public class UserService {
@Autowired ApplicationEventPublisher publisher;
public void register(String email) {
// ... 存 DB
publisher.publishEvent(new UserRegisteredEvent(this, email));
}
}
```

### 验证 2：JdbcTemplate 模板方法用法

```
@Repository
public class UserDao {
@Autowired JdbcTemplate jdbc;

public List<User> findAll() {
return jdbc.query(
"SELECT id, name, age FROM users",
(rs, i) -> new User(rs.getLong("id"), rs.getString("name"), rs.getInt("age"))
);
}
public int updateName(long id, String name) {
return jdbc.update("UPDATE users SET name = ? WHERE id = ?", name, id);
}
public User findOne(long id) {
return jdbc.queryForObject(
"SELECT * FROM users WHERE id = ?",
(rs, i) -> new User(rs.getLong("id"), rs.getString("name"), rs.getInt("age")),
id
);
}
}
// 不用写「打开连接 → 处理异常 → 关闭」重复代码，模板搞定
```

### 验证 3：@Async 完整示例 + 自定义线程池

```
@Configuration
@EnableAsync
public class AsyncConfig {
@Bean("mailExecutor")
public Executor mailExecutor() {
ThreadPoolTaskExecutor exec = new ThreadPoolTaskExecutor();
exec.setCorePoolSize(4);
exec.setMaxPoolSize(16);
exec.setQueueCapacity(200);
exec.setThreadNamePrefix("mail-");
exec.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
exec.initialize();
return exec;
}
}

@Service
public class MailService {
@Async("mailExecutor")
public CompletableFuture<Boolean> send(String to) {
try {
Thread.sleep(2000);   // 模拟耗时
System.out.println("sent to " + to + " on " + Thread.currentThread().getName());
return CompletableFuture.completedFuture(true);
} catch (Exception e) {
return CompletableFuture.completedFuture(false);
}
}
}

// 使用
@RestController
public class Ctrl {
@Autowired MailService mail;
@GetMapping("/notify")
public String notify() {
mail.send("a@x.com");                    // 立即返回，任务后台执行
mail.send("b@x.com").thenAccept(ok ->   // 拿结果做后续
System.out.println("b done: " + ok));
return "ok";
}
}
```

### 验证 4：@Async 自调用失效 & 解决

```
@Service
public class BadService {
@Async
public void asyncMethod() { /* ... */ }

public void call() {
this.asyncMethod();      // ❌ 走原对象不走代理 → 同步执行
}
}

// ✅ 解决：注入 self
@Service
public class GoodService {
@Autowired
private GoodService self;    // 注入自己（Spring 4.3+ 支持）

@Async
public void asyncMethod() { /* ... */ }

public void call() {
self.asyncMethod();      // 走代理 → 真异步
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 说出 Spring 用到的 5 种设计模式和对应位置。</summary>

工厂 → BeanFactory；单例 → 默认 scope；代理 → AOP；模板方法 → JdbcTemplate；观察者 → ApplicationEvent；适配器 → HandlerAdapter；责任链 → HandlerInterceptor。

</details>

<details>

<summary>Q2 BeanFactory 和 FactoryBean 有什么区别？</summary>

BeanFactory 是*容器本身*（生产 Bean 的工厂）；FactoryBean 是一种*特殊 Bean 接口*，容器返回其 `getObject()` 结果而非 Bean 本身。典型例子：MyBatis 的 `SqlSessionFactoryBean`。

</details>

<details>

<summary>Q3 Spring 单例的线程安全隐患怎么解决？</summary>

① 避免可变成员（无状态 Bean 最好）；② 用 `ThreadLocal` 存请求级状态；③ 改 `@Scope("prototype")` 每次新建（性能差，不推荐）。

</details>

<details>

<summary>Q4 @Async 的完整工作机制？</summary>

@EnableAsync 注册 AsyncAnnotationBeanPostProcessor → 后置处理器给带 @Async 的 Bean 生成 AOP 代理 → 调用时被 AsyncExecutionInterceptor 拦截 → 方法包成 Callable 提交到线程池 → 主线程立即返回。

</details>

<details>

<summary>Q5 @Async 的四大失效场景？</summary>

① 忘记 @EnableAsync；② 自调用 this.method()；③ private 或 static 方法；④ 返回非 Future 类型（返回 null）。

</details>

## 🎓 全课程收官 —— 66 节完成回顾

🧑‍💻 你已经走完

- **阶段一 · Java 基础**（0001-0009）：JVM/JDK/JRE、OOP、泛型、反射、代理、SPI、Unsafe

- **阶段二 · 集合**（0010-0017）：ArrayList、LinkedList、★HashMap、LinkedHashMap+LRU、★ConcurrentHashMap、CopyOnWrite、阻塞队列

- **阶段三 · 并发**（0018-0029）：线程、★synchronized 锁升级、volatile+JMM、CAS+ABA、Atomic、★AQS、ReentrantLock+Condition、ThreadLocal、★线程池、CompletableFuture、虚拟线程

- **阶段四 · JVM**（0030-0037）：★内存区域、对象布局、★GC 三大算法+分代+CMS/G1/ZGC、类文件、类加载 5 阶段、★类加载器+双亲委派、参数调优+线上排查

- **阶段五 · IO**（0038-0040）：装饰器/适配器、★BIO/NIO/AIO+多路复用、Buffer/Channel/Selector

- **阶段六 · MySQL**（0041-0050）：概览、SQL 执行+两阶段提交、★索引+B+树、索引失效、explain、★事务隔离、★MVCC、锁、三大日志、优化规范

- **阶段七 · Redis**（0051-0059）：缓存基础、★5+3 数据类型、跳表+listpack、★持久化 RDB/AOF、★缓存三兄弟、阻塞+淘汰策略、延时+Stream+分布式锁、主从+哨兵+Cluster

- **阶段八 · Spring**（0060-0066）：概览、★IoC/AOP+三级缓存、AOP 深入、★事务 7 传播、注解+MVC、SpringBoot 自动装配、设计模式+@Async

共 **66 节课件**，每节 30-50KB，包含 *~660 个面试场景 · ~330 段可跑代码 · ~330 道自测题*。整个 Java 后端八股的地图已经在你手里。

下一步 **把课件当成「回忆索引」，不是「背诵材料」**。真正备战面试的顺序建议：

1. 按学习路线图 *顺序过一遍*课件（不必全记，先建立地图）

2. 结合  原文*深读 ★ 标记的核心课*，尤其 HashMap / ConcurrentHashMap / AQS / 线程池 / GC / 类加载 / 索引 / MVCC / IoC / 事务

3. 找几套「模拟面试题」按*自测模式*合上课件口答，卡壳的地方回看

4. **实战验证**：跑代码段、用 `javap` 看字节码、用 `explain` 看 SQL、用 `redis-cli` 看数据结构；*亲手敲过的知识才是自己的*

5. Mock 面试：找同学或 Interviewing.io 类平台*说出来*—— 知道 ≠ 能说清

#### 📖 原文

-

-

- Spring Framework 官方文档

#### 🔗 关联课件

-

-

-

-

-

#### 🧭 下一课预告

**没有下一课了。** 66/66 全部完成 🎓 —— 是时候把课件从「学」进阶到「面」了。

💬 想问「实际面试中怎么把这些课件里的知识组织成回答？」「哪几节最应该反复看？」「模拟面试怎么准备？」—— 欢迎继续追问，我陪你到面试通关。


