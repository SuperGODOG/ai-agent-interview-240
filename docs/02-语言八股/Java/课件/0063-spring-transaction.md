> Lesson 0063 · 阶段八 · Spring · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0063 · Spring 事务：ACID & 7 种传播行为 & 隔离级别 & 失效场景

这一课覆盖 的全部核心考点。Spring 面试的**第二硬骨头**就在这里（第一是 IoC/AOP，见 ）—— 能不能在白板上把 **7 种传播行为**说清楚、能不能背出 **8 种失效场景**并给出解法，就是这轮 Spring 深挖的过关线。

核心认知先摆出来：*Spring 事务不是「自己实现事务」，只是「管理事务边界」*。真正的 ACID 是数据库引擎（InnoDB）在做，Spring 干的活是 —— 什么时候开事务、什么时候提交、什么时候回滚、多个 `@Transactional` 方法互相调用的时候怎么合并事务。这句话理解到位，后面所有的行为都能推出来。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `@Transactional` 加在 `private` 方法上会生效吗？</summary>

**不生效**。Spring 事务基于 AOP 代理拦截方法调用，JDK 动态代理只能代理接口方法（一定 public），CGLIB 代理生成子类也无法覆盖 `private`。所以私有方法不会被代理，`@Transactional` 就是一段死代码。第 7 题细讲。

</details>

<details>

<summary>Q0.2 `REQUIRED` 和 `REQUIRES_NEW` 的区别是什么？</summary>

REQUIRED（默认）：*有事务就加入*，没有就新建，内外共享一个物理事务，任一方回滚全部回滚。REQUIRES_NEW：*不管外层有没有事务，都新建一个独立事务*，并把当前事务挂起，内外互不影响。日志场景常用 REQUIRES_NEW —— 主流程回滚也不能丢失审计日志。第 5 题深挖。

</details>

## 面试场景 1：Spring 事务是什么？和 JDBC 事务什么关系？

🎤 面试官

说说 Spring 事务是什么？它和 JDBC 事务有什么关系？

🧑‍💻 你

Spring 事务是*对底层事务 API 的抽象封装*，本身**不产生 SQL 事务**，只做「事务边界管理」这一件事。

它的核心接口是 `PlatformTransactionManager`，屏蔽了下面这些底层实现的差异：

- `DataSourceTransactionManager` —— 走 JDBC 原生 `Connection.setAutoCommit(false) / commit() / rollback()`

- `JpaTransactionManager` —— 走 JPA `EntityManager`

- `HibernateTransactionManager` —— 走 Hibernate `Session`

- `JtaTransactionManager` —— 走 JTA 分布式事务

用一句话说：**ACID 是数据库引擎（如 InnoDB）保证的，Spring 只帮你「什么时候 begin、commit、rollback」，以及「多个方法互相调用时事务怎么合并」**。

追问 Spring 事务是不是完全依赖数据库事务？

**是的**。Spring 事务本质上就是拿到底层 `Connection`，调 `setAutoCommit(false)` 开事务、`commit()`/`rollback()` 结束事务。所以：（1）如果数据库引擎不支持事务（比如 MySQL 的 MyISAM），加了 `@Transactional` 也没用；（2）ACID 中的 A（原子性，靠 undo log）、I（隔离性，靠锁 + MVCC）、D（持久性，靠 redo log）都是 InnoDB 在做，Spring 只是「边界管理层」。

追问 ACID 各自是怎么保证的？

**A 原子性**：InnoDB 的 undo log 记录修改前的镜像，事务失败按 undo log 回滚。**C 一致性**：是*目的*不是手段，靠 A/I/D 三个手段一起支撑（应用层业务规则也要参与）。**I 隔离性**：InnoDB 用行锁、间隙锁 + MVCC 实现。**D 持久性**：redo log 顺序写 + fsync 到磁盘，即便宕机也能恢复。详细见 。

## 面试场景 2：编程式事务 vs 声明式事务

🎤 面试官

Spring 提供了几种事务管理方式？你在项目里用哪种？

🧑‍💻 你

两种：

1. **编程式事务**：手动通过 `TransactionTemplate` 或 `PlatformTransactionManager` 控制事务边界。

- 优点：控制精细，可以在方法内动态决定「这段代码进事务、那段不进」。

- 缺点：代码侵入性高，业务逻辑和事务逻辑混在一起。

2. **声明式事务**：用 `@Transactional` 注解，Spring 通过 AOP 自动织入事务代码。

- 优点：注解一贴，业务代码干净。

- 缺点：*基于 AOP 代理*，有一大堆失效场景（第 7-10 题的主题）。

项目里 **99% 用声明式**，只有需要「事务中间分段提交」「事务和非事务代码交织」的少数场景才降级用编程式。

追问 编程式事务什么时候必须用？

典型场景是**「大事务需要拆成小事务批量提交」**。比如 100 万条数据批处理，你不想全部塞进一个事务（占锁久、undo log 巨大、回滚代价高），可以在 `TransactionTemplate.execute` 里每 1000 条提交一次。另一个场景是**「事务边界依赖运行时判断」**，比如「配置开关打开时才开事务」，注解是编译期决定的做不到。

## 面试场景 3：`@Transactional` 的核心属性

🎤 面试官

`@Transactional` 有哪些常用属性？各自默认值？

属性作用默认值常见踩坑

`propagation`
事务传播行为（内外事务怎么合并）
`REQUIRED`
REQUIRES_NEW 和 NESTED 混淆

`isolation`
事务隔离级别
`DEFAULT`（用 DB 的）
MySQL 默认 REPEATABLE_READ，改成 READ_COMMITTED 常见

`timeout`
超时秒数，超时自动回滚
`-1`（不超时）
只对*获取新连接*后有效，长查询里没生效

`readOnly`
只读事务提示（DB 可优化）
`false`
只读事务里写数据可能被 DB 拒绝

`rollbackFor`
触发回滚的异常类
仅 `RuntimeException` 和 `Error`
抛 `IOException` 不回滚（第 9 题）

`noRollbackFor`
*不*触发回滚的异常类（白名单）
空
用于「业务预期异常」如 `StockShortageException`

`transactionManager`
指定用哪个事务管理器
默认唯一那个
多数据源时必须显式指定

追问 `readOnly = true` 有什么实际收益？

三方面：（1）**DB 优化**：MySQL 可能关闭 undo log 生成、跳过 MVCC 版本记录；（2）**Hibernate/JPA 优化**：会跳过脏检查（dirty checking），一级缓存里的对象不会被 flush 到 DB；（3）**读一致性**：多条 SELECT 保证在同一个事务快照里，避免中间被别人改。*但单条 SELECT 不需要开事务*，DB 单语句本身就是原子的。

## 面试场景 4：7 种传播行为 ⭐核心必背

🎤 面试官

Spring 有几种事务传播行为？各自什么含义？

🧑‍💻 你

7 种。我按「用不用当前事务」分三档记：

档位传播行为外层有事务外层没事务常见场景

**共享档**
`REQUIRED`（默认）
加入
新建
90% 的业务方法

`SUPPORTS`
加入
非事务运行
查询方法，可选择性事务

`MANDATORY`
加入
*抛异常*
强制要求被事务调用（少用）

**独立档**
`REQUIRES_NEW`
*挂起外层，新建独立事务*
新建
审计日志、发通知（主流程回滚也要记）

`NESTED`
*创建 SAVEPOINT 嵌套事务*
新建（相当于 REQUIRED）
子任务允许单独失败

**非事务档**
`NOT_SUPPORTED`
挂起外层，非事务运行
非事务运行
大量数据读，不需要事务开销

`NEVER`
*抛异常*
非事务运行
断言「不能在事务里」（极少用）

记忆技巧 三档的核心关键词：**共享（REQUIRED/SUPPORTS/MANDATORY）**是「有就加入」；**独立（REQUIRES_NEW/NESTED）**是「另起炉灶」；**非事务（NOT_SUPPORTED/NEVER）**是「拒绝事务」。MANDATORY 和 NEVER 是一对反义词 —— 前者要求「必须有事务」、后者要求「必须没事务」。

追问 REQUIRES_NEW 是怎么「挂起」外层事务的？

Spring 在 `AbstractPlatformTransactionManager.handleExistingTransaction()` 里：（1）把当前事务的 `Connection`、`TransactionSynchronization` 等状态*暂存*到 `SuspendedResourcesHolder`；（2）从连接池**获取一个新的 Connection**，开一个全新事务；（3）新事务提交/回滚后，把之前暂存的资源恢复回来。所以 REQUIRES_NEW 会用**两个数据库连接**，高并发时要注意连接池够不够用（外层挂起的连接不会释放）。

## 面试场景 5：REQUIRED vs REQUIRES_NEW vs NESTED 深度对比 ⭐经典

🎤 面试官

假设方法 A 调用方法 B，A 用 REQUIRED、B 分别用 REQUIRED/REQUIRES_NEW/NESTED 三种，A 或 B 抛异常时的回滚行为分别是什么？

B 的传播行为物理事务B 抛异常且 A 未 catchB 抛异常但 A catch 了A 抛异常

`REQUIRED`
共用 1 个
A、B 都回滚
❗ *依然全部回滚*（UnexpectedRollbackException）
A、B 都回滚

`REQUIRES_NEW`
2 个独立事务
B 回滚，A 感知异常也回滚
B 回滚，*A 不回滚*
A 回滚，*B 已提交不受影响*

`NESTED`
1 个物理事务 + SAVEPOINT
B 回滚到 SAVEPOINT，A 感知异常后整体回滚
*B 回滚到 SAVEPOINT，A 继续提交*
A、B 都回滚

重点陷阱 REQUIRED 场景下，「B 抛异常 + A catch」**依然会整体回滚**！因为 Spring 内层 B 抛异常时会把当前事务标记为 `rollback-only`，外层 A 尝试 commit 时会抛 `UnexpectedRollbackException: Transaction silently rolled back because it has been marked as rollback-only`。*想让 A catch 后不回滚，B 必须用 REQUIRES_NEW 或 NESTED*。

追问 REQUIRES_NEW 和 NESTED 都能「内层单独失败」，两者区别是？

**物理事务数不同**：REQUIRES_NEW 是*两个独立的物理事务（两个 Connection）*，内层提交后即便外层回滚也不影响；NESTED 是*一个物理事务里用 SAVEPOINT 划分子事务*，共用一个 Connection —— 外层回滚时，内层即便已经「回到 SAVEPOINT 后继续跑」的数据也会跟着回滚。**REQUIRES_NEW 更彻底**（日志、审计首选），**NESTED 更省资源**（一个连接搞定，但依赖 DB 支持 SAVEPOINT —— MySQL InnoDB 支持，很多老库不支持）。

追问 事务里发消息 MQ 或调用 RPC，怎么保证一致性？

Spring 本地事务管不了外部资源，标准方案有：（1）**本地消息表 + 定时补偿**：把消息先落库跟业务一个事务，后台任务扫表推 MQ；（2）**RocketMQ 事务消息**：half message + 回查机制，两阶段保证；（3）**Seata AT/TCC/SAGA** 分布式事务框架；（4）最简单可靠的**「先提交事务再发消息」+ 消费端幂等**，允许短暂不一致。绝对不要在 `@Transactional` 方法内直接发 MQ —— 消息发出去了但事务回滚是常见事故。

## 面试场景 6：5 种隔离级别

🧑‍💻 你

Spring 定义了 5 个隔离级别（`Isolation` 枚举），前 4 个跟 SQL 标准一致，多一个 `DEFAULT`：

隔离级别脏读不可重复读幻读使用场景

`DEFAULT`跟随数据库默认**业务默认选它**，MySQL 就是 REPEATABLE_READ
`READ_UNCOMMITTED`❌❌❌几乎不用
`READ_COMMITTED`✅❌❌Oracle/PostgreSQL 默认；MySQL 高并发场景常改成它
`REPEATABLE_READ`✅✅❌*MySQL InnoDB 默认，靠 MVCC + Next-Key Lock 也基本防幻读
`SERIALIZABLE`✅✅✅强一致性对账，性能很差极少用

*MySQL InnoDB 在 REPEATABLE_READ 下用 Next-Key Lock 已经防住了幻读，是*特化实现*，SQL 标准里 RR 不防幻读。详见 。

追问 生产为什么 90% 的 `@Transactional` 都不显式设 `isolation`？

因为**用 DB 默认的就够了**。业务级别应该关注「传播行为」而不是「隔离级别」—— 隔离级别应该在 DB 层面全局统一设置（如 MySQL 的 `transaction_isolation` 参数），而不是散在每个业务方法里。散着设的副作用是：不同方法用不同隔离级别、切换连接时 DB 要重新协商，性能差还容易出诡异 bug。

## 面试场景 7：失效场景 1 —— `private`/`final` 方法 ⭐经典

🎤 面试官

为什么 `@Transactional` 加在 `private` 方法上不生效？`final` 呢？

🧑‍💻 你

因为 Spring 事务是**基于 AOP 代理**实现的，代理机制天然拦不到这两种方法：

- **JDK 动态代理**：只能代理接口方法 —— 接口方法一定是 public，`private` 根本进不了代理。

- **CGLIB 代理**：通过生成子类覆盖方法实现拦截。子类无法覆盖 `private`（子类看不见父类 private）；也无法覆盖 `final`（Java 语法禁止覆盖 final 方法）。

所以 `@Transactional` 加在这两种方法上不会报错，但注解就是*一段死代码*，事务不会开启。`static` 方法同理 —— 代理是实例方法级别的，static 也无法拦截。

追问 Spring Boot 默认用 JDK 还是 CGLIB 代理？

Spring Boot 2.x 之后**默认全部用 CGLIB**（`spring.aop.proxy-target-class=true`）。原因是「不管有没有实现接口都能代理，行为一致」。所以在 Spring Boot 里你的类不需要实现接口也能被事务代理。但 `private`/`final`/`static` 的限制依旧存在。

追问 那 `protected` 方法呢？

能生效，但依赖代理类型：CGLIB 能代理 `protected`（子类看得见 protected），JDK 动态代理不能（因为 protected 不在接口里）。所以在 Spring Boot 默认 CGLIB 下 protected 可以，但**不推荐依赖这个特性**——业务方法保持 public 最保险。

## 面试场景 8：失效场景 2 —— 自调用 ⭐经典

🎤 面试官

看这段代码，猜下 `methodB` 里的事务生效吗？

```
@Service
public class OrderService {
public void methodA() {
this.methodB();   // ← 直接 this. 调用
}

@Transactional
public void methodB() {
// insert into orders ...
throw new RuntimeException("boom");
}
}
```

🧑‍💻 你

**不生效**。因为 `this.methodB()` 是*直接调用当前对象*（也就是被代理的目标对象，不是代理对象），完全绕过了 AOP 代理，`TransactionInterceptor` 根本没机会拦截。

调用链示意：

**
```
外部调用 orderService.methodA()
↓
代理对象 OrderService$$EnhancerBySpringCGLIB
↓ (代理拦截，但 methodA 没 @Transactional，直接放行)
真实对象 methodA()
↓ this.methodB()
真实对象 methodB()  ← 事务没开！
```

三种解决方案：

1. **方法拆到另一个 Bean**：让 A 注入 B，跨 Bean 调用自然走代理。最干净的做法。

2. **注入自己（self-inject）**：

```
@Service
public class OrderService {
@Autowired
private OrderService self;   // 注入的是代理对象

public void methodA() {
self.methodB();          // 走代理，事务生效
}
}
```

3. **从 `AopContext` 拿代理**（需要 `@EnableAspectJAutoProxy(exposeProxy = true)`）：

```
public void methodA() {
((OrderService) AopContext.currentProxy()).methodB();
}
```

追问 为什么 `this.method()` 不走代理？画个内存图。

Spring 容器里存的是*代理对象*（`OrderService$$EnhancerBySpringCGLIB`），外部通过 `@Autowired` 拿到的都是代理。但代理对象内部持有一个 `target` 字段指向真实对象；当代理拦截到方法调用后，实际执行的是 `target.method()`。此时 `this` 就是 `target`（真实对象），`this.method2()` 就是真实对象调真实对象，跟代理没关系了。

## 面试场景 9：失效场景 3 —— 异常类型不匹配 ⭐经典

🎤 面试官

这段代码里的事务会回滚吗？

```
@Transactional
public void createOrder() throws IOException {
orderDao.insert(order);
fileService.writeAuditLog();   // 抛 IOException
}
```

🧑‍💻 你

**不会回滚**！`orderDao.insert(order)` 会被正常提交，尽管后面抛了 `IOException`。

原因：`@Transactional` 的 `rollbackFor` 默认*只回滚 `RuntimeException` 和 `Error`*，Checked Exception（`Exception` 的直接子类，如 `IOException`/`SQLException`）默认*不触发回滚*。

修复方式：

```
// 显式声明所有异常都回滚（生产项目建议默认加上）
@Transactional(rollbackFor = Exception.class)
public void createOrder() throws IOException {
...
}
```

追问 为什么 `rollbackFor` 默认只回滚 `RuntimeException`？

这是 Spring 沿用了 EJB 的历史设计。设计者认为：**Checked Exception 表示「预期内的业务异常」应该被业务代码自己 `catch` 处理并决定是否继续**；**RuntimeException 才是「意料之外的错误」应该整体回滚**。理念上说得通，但实际业务里 Checked Exception 也常常是「保存文件失败」「网络超时」这种需要回滚的场景。所以*生产项目建议把 `rollbackFor = Exception.class` 设成默认*，或者干脆全用 RuntimeException（Spring 5 之后的推荐姿势）。

追问 异常被 `catch` 掉了会怎样？

**事务不会回滚**！因为异常没抛到 `TransactionInterceptor` 那一层，拦截器以为方法正常返回，就执行 commit。修复：（1）catch 后*重新抛出*；（2）手动标记回滚：

```
try {
...
} catch (Exception e) {
TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
log.error("failed", e);
}
```

这行代码是所有「异常吞掉但要回滚」场景的通杀方案。

## 面试场景 10：其他失效场景合集

🎤 面试官

除了 private、自调用、异常不匹配，还有哪些 `@Transactional` 失效场景？

🧑‍💻 你

1. **类没被 Spring 管理**：忘了加 `@Service`/`@Component`，或者 `new` 出来的对象。Spring 只代理容器里的 Bean。

2. **数据库引擎不支持事务**：MySQL 的 MyISAM、MEMORY 引擎都不支持事务，Spring 层面开事务后到 DB 直接吞掉。

3. **未开启事务支持**：普通 Spring 项目要显式加 `@EnableTransactionManagement`。Spring Boot 自动配置了，不用管。

4. **异常被 `catch` 吞掉**（第 9 题追问已讲）。

5. **多线程调用**：`new Thread(() -> service.method())` 里事务失效 —— 因为事务上下文是 `ThreadLocal` 存的，子线程拿不到父线程的事务。

6. **错误的 `propagation`**：设成 `NEVER`，外层有事务时直接抛异常；设成 `NOT_SUPPORTED`，事务被挂起等于没开。

7. **方法用 `final`/`static`/`private`**（第 7 题）。

8. **Spring Boot 里 Bean 被父类的 `@Transactional` 覆盖**：子类方法没标注，用父类注解 —— 属性对不上时容易踩坑。

口诀 8 种失效场景背下来：**「非 public、类未管、自调用、静态 final、异常吞、异常错、跨线程、错传播」**。面试问「@Transactional 失效场景」能一口气报 5 个以上，就是加分项。

追问 多线程调用为什么失效？举个例子。

Spring 的事务信息（`Connection`、`TransactionStatus`）通过 `TransactionSynchronizationManager` 存在 `ThreadLocal` 里。`ThreadLocal` 是*线程隔离*的，子线程有自己的 ThreadLocal Map，拿不到父线程的事务对象。所以：

```
@Transactional
public void batchImport(List<Order> orders) {
orders.parallelStream().forEach(o -> {
orderDao.insert(o);     // ← 子线程里没有事务！
});
}
```

这里 `orderDao.insert` 每一次都是**自动提交**，异常也不会整体回滚。解决方案：（1）把事务边界包在子线程内部，每个子线程各自开事务；（2）用编程式事务 + `CountDownLatch`；（3）主线程收集所有数据后再统一入库。

追问 Spring 用 `@Async` 触发的方法能不能继承外层事务？

**不能**。`@Async` 会把方法丢到线程池执行，本质就是多线程，同样受 ThreadLocal 限制。`@Async` 方法要事务的话，自己方法上加 `@Transactional`，并且注意*它是新事务*，跟调用它的方法完全独立。

## 💻 代码验证（打开 IDE 跑一遍）

### 代码 1：`@Transactional` 基础使用与 rollbackFor

```
@Service
public class OrderService {

@Autowired
private OrderDao orderDao;

// ✅ 默认：只回滚 RuntimeException
@Transactional
public void createRuntimeErr() {
orderDao.insert(new Order(1L, "A"));
throw new IllegalStateException("boom");   // 会回滚
}

// ❌ 陷阱：Checked Exception 不回滚
@Transactional
public void createCheckedErr() throws IOException {
orderDao.insert(new Order(2L, "B"));
throw new IOException("io fail");           // 不会回滚！第 2 条会入库
}

// ✅ 修复：显式 rollbackFor
@Transactional(rollbackFor = Exception.class)
public void createAllRollback() throws IOException {
orderDao.insert(new Order(3L, "C"));
throw new IOException("io fail");           // 会回滚
}
}
```

### 代码 2：REQUIRED vs REQUIRES_NEW 行为对照

```
@Service
public class OuterService {
@Autowired InnerService inner;

@Transactional  // 默认 REQUIRED
public void run() {
orderDao.insert(new Order(1L, "outer"));
try {
inner.doInnerRequiresNew();     // 会新开事务
} catch (RuntimeException e) {
log.info("caught inner err, continue");
}
orderDao.insert(new Order(2L, "outer-after"));
// 结果：outer 的两条都提交；inner 的数据回滚
}
}

@Service
public class InnerService {
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void doInnerRequiresNew() {
orderDao.insert(new Order(99L, "inner"));
throw new RuntimeException("inner fail");
}
}
```

把上面 `Propagation.REQUIRES_NEW` 改成 `REQUIRED`，行为完全变了 —— 外层 catch 之后，*整个事务依然会在 commit 时抛 `UnexpectedRollbackException`*，两条 outer 数据也回滚。

### 代码 3：自调用失效 + 三种修复

```
@Service
public class UserService {
@Autowired
private UserService self;                       // 注入自己（Spring 4+ 支持）

// 场景：methodA 非事务，methodB 想开事务
public void methodA_selfCallFail() {
this.methodB();                             // ❌ 事务失效
}

public void methodA_selfInjectFix() {
self.methodB();                             // ✅ 生效
}

public void methodA_aopContextFix() {
// 需要在启动类加 @EnableAspectJAutoProxy(exposeProxy = true)
((UserService) AopContext.currentProxy()).methodB();   // ✅ 生效
}

@Transactional
public void methodB() {
userDao.updateEmail(...);
throw new RuntimeException("test rollback");
}
}
```

### 代码 4：编程式事务 —— 大批量拆段提交

```
@Service
public class BatchImportService {

@Autowired
private TransactionTemplate transactionTemplate;

@Autowired
private OrderDao orderDao;

/**
* 100 万条数据每 1000 条一个事务，避免大事务
*/
public void importAll(List<Order> all) {
int batchSize = 1000;
for (int i = 0; i < all.size(); i += batchSize) {
List<Order> batch = all.subList(i, Math.min(i + batchSize, all.size()));
transactionTemplate.execute(status -> {
try {
orderDao.batchInsert(batch);
return null;
} catch (Exception e) {
status.setRollbackOnly();
log.error("batch {} failed", i, e);
throw e;
}
});
}
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话说清 Spring 事务和 JDBC 事务的关系。</summary>

Spring 事务是对 JDBC/JPA/JTA 等底层事务 API 的抽象封装，通过 `PlatformTransactionManager` 统一管理事务边界（begin/commit/rollback），*本身不产生事务*，ACID 靠底层数据库引擎（如 InnoDB）保证。

</details>

<details>

<summary>Q2 说出 7 种传播行为的名字，并按「共享 / 独立 / 非事务」分档。</summary>

共享档：`REQUIRED`（默认）、`SUPPORTS`、`MANDATORY`；独立档：`REQUIRES_NEW`、`NESTED`；非事务档：`NOT_SUPPORTED`、`NEVER`。REQUIRED = 有就加入没就新建（90% 场景）；REQUIRES_NEW = 挂起外层另起独立事务；NESTED = 一个物理事务里用 SAVEPOINT 嵌套。

</details>

<details>

<summary>Q3 A 用 REQUIRED，B 用 REQUIRED，A 里 catch 了 B 抛的异常，事务会怎样？</summary>

**整个事务依然会回滚**！B 抛异常时 Spring 会把当前事务标记为 `rollback-only`，外层 A 尝试 commit 时抛 `UnexpectedRollbackException`。想让 A catch 后继续提交，B 必须用 `REQUIRES_NEW` 或 `NESTED`。

</details>

<details>

<summary>Q4 @Transactional 失效场景至少举 5 个。</summary>

（1）非 public 方法（private/final/static）；（2）类未被 Spring 管理（缺 @Service）；（3）自调用（this.method()）；（4）异常被 catch 吞掉；（5）异常类型不匹配（默认只回滚 RuntimeException）；（6）多线程调用（ThreadLocal 隔离）；（7）DB 引擎不支持事务（MyISAM）；（8）错误的 propagation（NEVER/NOT_SUPPORTED）。

</details>

<details>

<summary>Q5 生产项目里 `@Transactional` 建议默认加什么参数？为什么？</summary>

建议 `@Transactional(rollbackFor = Exception.class)`。因为默认只回滚 `RuntimeException`，一旦业务方法抛出 Checked Exception（`IOException`/`SQLException` 等）就不会回滚，数据会出现「一半成功一半失败」的诡异状态。显式加上 `rollbackFor = Exception.class` 覆盖所有场景更安全。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Spring Framework Reference · Transaction Management —— 官方权威

- Spring API · `Propagation` 枚举 —— 7 种传播行为源码定义

#### 🔗 关联课件

-  —— 事务本质是 AOP 的一种应用，先懂 AOP 才能真正理解事务

-  —— *上一课*，代理机制细节，解释了为什么 private/自调用会失效

-  —— 底层 ACID 与 4 种隔离级别，是本课的 DB 侧支撑

-  —— *下一课*，把 @Transactional 和其他 20 多个核心注解串起来

#### 🧭 下一课预告

Lesson 0064：**Spring 常用注解全解** —— 从 @Component/@Service/@Autowired 到 @Conditional/@Profile/@Scheduled，一次搞定 Spring 面试的注解题。

💬 有任何疑问 —— 「REQUIRES_NEW 挂起外层时会不会死锁？」「Seata 的 AT 模式是怎么代替 @Transactional 的？」「自调用为什么不能通过 `this` 走代理？」—— 直接问我。事务这个话题面试能问的追问超过 30 个，你随便挑。


