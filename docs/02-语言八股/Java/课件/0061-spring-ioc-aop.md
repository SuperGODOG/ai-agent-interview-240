> Lesson 0061 · 阶段八 · Spring · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 8 个追问

# 0061 · Spring IoC & AOP & Bean 生命周期 & 循环依赖

Spring 的两大基石：**IoC**（Inversion of Control，控制反转）把对象的*创建与依赖管理*交给容器；**AOP**（Aspect-Oriented Programming，面向切面编程）把*日志/事务/权限*等横切逻辑从业务代码里抽离。这两个概念背后串起了一整条面试高频问题链：**Bean 生命周期是什么、循环依赖怎么解决、三级缓存为什么设计成三级、AOP 代理什么时候生成**。这一课把它们串成一条完整的技术故事线。

对应 ，并补齐原文没展开的 Bean 生命周期和三级缓存源码级细节 —— 这些是**大厂面试实打实的必考题**。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 IoC 和 DI 是同一回事吗？</summary>

不是。**IoC 是思想**（控制反转 —— 对象创建权交给容器），**DI 是它的具体实现方式**（依赖注入 —— 容器把依赖塞给对象）。Martin Fowler 认为 DI 这个词更精准，因为「控制反转」太笼统。第 1、3 场景会展开。

</details>

<details>

<summary>Q0.2 Spring 三级缓存分别是哪三级？</summary>

`singletonObjects`（一级，完整 Bean）→ `earlySingletonObjects`（二级，早期暴露的半成品 Bean，可能是 AOP 代理）→ `singletonFactories`（三级，ObjectFactory，按需生成早期引用）。第 8、9 场景会画流程图。

</details>

## 面试场景 1：IoC 是什么？为什么叫「控制反转」？

🎤 面试官

Spring 的 IoC 到底是什么？为什么叫「控制反转」？反转的是什么？

🧑‍💻 你

**IoC = Inversion of Control，控制反转**。它是一种*设计思想*而非某种技术。

- **控制** 指的是「对象的*创建、实例化、依赖装配、生命周期管理*」这些权力。

- **反转** 指的是这些权力从*业务代码*转移到*IoC 容器*。

对比一下传统写法和 IoC 写法：

```
// 传统方式：Service 自己 new Dao，强耦合
public class UserService {
private UserDao dao = new UserDaoMysqlImpl();  // ← 想换成 UserDaoOracleImpl 要改代码
}

// IoC 方式：Service 只声明「我要一个 UserDao」，容器负责给我
@Service
public class UserService {
@Autowired
private UserDao dao;  // ← 换实现只需改容器配置或 @Primary 注解
}
```

IoC 解决的核心痛点：**降低对象之间的耦合度**，让替换依赖变得像替换插件一样简单。

追问 IoC 和 DI 是什么关系？

**IoC 是思想，DI 是 IoC 最主流的实现方式**。IoC 只说「控制权反转了」，但没说反转到哪、怎么反转。DI（Dependency Injection，依赖注入）明确了实现路径 ——「容器把依赖*注入*到对象里」。Martin Fowler 在 2004 年的经典文章里就说过：DI 比 IoC 表意更精准。另一种较少见的 IoC 实现是 Service Locator，但 Spring 主要用 DI。

## 面试场景 2：IoC 容器 BeanFactory vs ApplicationContext

🎤 面试官

Spring 的 IoC 容器有哪些？BeanFactory 和 ApplicationContext 有什么区别？

🧑‍💻 你

Spring IoC 容器有两个核心接口：

- **`BeanFactory`**：*根接口*，IoC 容器的最底层规范，提供最基础的 Bean 管理能力（`getBean()`、类型判断、别名等）。*懒加载* —— 第一次 `getBean()` 时才实例化 Bean。

- **`ApplicationContext`**：`BeanFactory` 的*子接口*，是*生产环境实际使用*的容器。在 BeanFactory 基础上扩展了：

- **事件发布**（`ApplicationEventPublisher`）—— 支持 `@EventListener`

- **国际化**（`MessageSource`）

- **资源加载**（`ResourceLoader`）

- **AOP、事务**等企业级功能的自动装配

- *预加载* —— 容器启动时就实例化所有非懒加载单例 Bean（便于早期发现配置错误）

常见的 `ApplicationContext` 实现：

```
ClassPathXmlApplicationContext        // 从 classpath 下的 XML 加载配置
FileSystemXmlApplicationContext       // 从文件系统路径加载 XML
AnnotationConfigApplicationContext    // 从 @Configuration 类加载（Spring Boot 用这个）
WebApplicationContext                 // Web 环境专用（Servlet 集成）
```

追问 为什么 Spring 要拆成 BeanFactory 和 ApplicationContext 两层？

**接口隔离原则**。`BeanFactory` 只关心「怎么造 Bean、怎么拿 Bean」，是纯粹的 IoC 内核；`ApplicationContext` 面向应用开发，把事件、国际化、AOP 这些企业级能力叠加上去。这样嵌入式场景（比如资源受限的 IoT 设备）可以只用 `BeanFactory`，通用场景用 `ApplicationContext`。同时也符合*开闭原则* —— 扩展新能力不动底层接口。

## 面试场景 3：DI 的三种注入方式怎么选？

🎤 面试官

Spring 有几种依赖注入方式？它们的优缺点是什么？你日常用哪种？

🧑‍💻 你

三种主流注入方式，Spring 官方从 4.x 开始**推荐构造器注入**：

方式写法优点缺点

**构造器注入**（推荐）
`public UserService(UserDao dao) { ... }`
可用 `final`（不可变）；强制依赖，容器启动时缺失就报错；便于单元测试（直接 new）
构造器参数多时较冗长（Lombok `@RequiredArgsConstructor` 可缓解）；*无法解决构造器循环依赖*

Setter 注入
`@Autowired public void setDao(UserDao dao) { ... }`
可选依赖友好；*能容忍单例循环依赖*（三级缓存起作用）
字段可变（不能用 final）；对象可能处于「半初始化」状态

字段注入 `@Autowired`（不推荐）
`@Autowired private UserDao dao;`
代码短
无法用 final；*单元测试必须依赖 Spring 容器或反射*；隐藏了强依赖关系；容易写出循环依赖

Spring 官方建议：**强制依赖用构造器，可选依赖用 Setter**，字段注入尽量别用（IDEA 都会给黄色警告）。

追问 为什么构造器注入能用 `final`？为什么字段注入不能？

`final` 字段必须在*构造器结束前*赋值。构造器注入在 `new` 的时候就把依赖传进去了，符合 `final` 的初始化时机。字段注入依赖*反射在构造完成之后*塞值，此时 `final` 已经锁定，无法赋值（Spring 通过反射强行 setAccessible 破坏 final 语义在早期版本能跑，但 JDK 17 之后受模块系统限制会更严）。

陷阱 **字段注入 + 构造器同时写** 会踩坑：如果构造器里访问 `@Autowired` 字段，字段还是 `null`—— 因为字段注入发生在构造器执行*之后*。正确的做法是要么全用构造器注入，要么用 `@PostConstruct` 做初始化后的逻辑。

## 面试场景 4：AOP 是什么？核心概念有哪些？

🎤 面试官

AOP 是什么？说说 Aspect、Pointcut、Advice、JoinPoint 这几个概念。

🧑‍💻 你

**AOP = Aspect-Oriented Programming，面向切面编程**。它是 OOP 的补充，不是替代 —— 用来解决 OOP 难处理的*横切关注点*（cross-cutting concerns）：日志、事务、权限、限流、缓存、埋点等散布在多个业务方法里的重复逻辑。

核心概念（面试常按这个次序问）：

- **横切关注点（Cross-cutting Concern）**：需要在多个类的多个方法中重复出现的逻辑（比如「进方法打日志、出方法打日志」）。

- **切面（Aspect）**：对横切关注点的封装，通常是加 `@Aspect` 的类。

- **连接点（JoinPoint）**：程序执行过程中可以被拦截的*点*（Spring AOP 里只支持方法执行 JoinPoint）。

- **切点（Pointcut）**：一个*表达式*，用来筛选「哪些 JoinPoint 需要被这个切面增强」，如 `execution(* com.foo.service.*.*(..))`。

- **通知（Advice）**：切面在切点上要执行的*动作*，有 `@Before`/`@After`/`@Around` 等。

- **织入（Weaving）**：把切面「编织」到目标对象、生成代理的过程。Spring AOP 是*运行时织入*（动态代理），AspectJ 支持*编译时/加载时织入*（字节码增强，性能更高）。

追问 Spring AOP 和 AspectJ 有什么区别？

**Spring AOP** = 基于*动态代理*（JDK Proxy 或 CGLIB）的*运行时织入*，只支持方法级别的 JoinPoint，只能拦截 Spring 管理的 Bean。优点是无需额外编译步骤、和 Spring 容器无缝集成。**AspectJ** = 基于*字节码修改*的*编译时/后编译/加载时织入*，支持方法、字段、构造器、静态初始化等所有 JoinPoint，能拦截非 Spring 对象，性能更好（无代理调用开销）。*切面很多、性能敏感场景*选 AspectJ；*普通业务场景*用 Spring AOP 足够。Spring 实际上是「用 AspectJ 的注解语法 + 自己的代理实现」。

## 面试场景 5：AOP 的 5 种 Advice 分别在什么时机执行？

🧑‍💻 你

Spring AOP 提供 5 种 Advice 注解，按执行时机分：

注解执行时机典型用途

`@Before`目标方法执行*前*参数校验、权限检查、开启资源
`@After`目标方法执行*后*（**无论成败**都会执行，类似 `finally`）释放资源、清理 ThreadLocal
`@AfterReturning`目标方法*正常返回*后（能拿到返回值）缓存返回值、日志记录返回结果
`@AfterThrowing`目标方法*抛异常*后（能拿到异常对象）异常日志、告警通知
`@Around`*环绕*目标方法（前后都能插逻辑，可以决定是否放行、修改参数、修改返回值）事务、限流、性能统计 —— **最强大也最容易写错**

执行顺序（**正常返回**时）：`@Around 前置` → `@Before` → *目标方法* → `@AfterReturning` → `@After` → `@Around 后置`。

执行顺序（**抛异常**时）：`@Around 前置` → `@Before` → *目标方法（抛异常）* → `@AfterThrowing` → `@After`（`@Around 后置`不执行，因为异常已经打断了）。

陷阱 `@Around` 必须**手动调用 `ProceedingJoinPoint.proceed()`** 才能放行目标方法。忘记 `proceed()` 会导致目标方法根本不执行、返回 `null`—— 这是新手写限流/事务切面的经典 bug。

## 面试场景 6：Bean 的完整生命周期（★核心必背）

🎤 面试官

说一下 Spring Bean 的完整生命周期。

🧑‍💻 你

Spring Bean 从「诞生」到「销毁」经历**八大阶段**：

```
① 实例化 Instantiation
└─ 通过反射调用构造器 new 出裸对象（此时字段都是默认值）
│
▼
② 属性赋值 PopulateBean
└─ 依赖注入：@Autowired / @Value / setter 把依赖塞进去
│
▼
③ Aware 接口回调
├─ BeanNameAware.setBeanName(name)          ← 告诉 Bean 自己在容器里的名字
├─ BeanFactoryAware.setBeanFactory(bf)      ← 拿到 BeanFactory 引用
└─ ApplicationContextAware.setApplicationContext(ctx)
│
▼
④ BeanPostProcessor.postProcessBeforeInitialization
└─ 初始化前拦截（比如 @PostConstruct 就在这里被处理）
│
▼
⑤ 初始化 Initialization（三种方式，按序执行）
├─ @PostConstruct 注解方法
├─ InitializingBean.afterPropertiesSet()
└─ XML 里配置的 init-method="xxx"
│
▼
⑥ BeanPostProcessor.postProcessAfterInitialization
└─ ★ AOP 代理就是在这里生成的（AbstractAutoProxyCreator）
│
▼
⑦ 使用中（Bean 就绪，业务代码可 getBean 拿到）
│
▼
⑧ 销毁 Destruction（容器关闭时，三种方式按序）
├─ @PreDestroy 注解方法
├─ DisposableBean.destroy()
└─ XML 里配置的 destroy-method="xxx"
```

**面试速记口诀**：*实例化 → 注入 → Aware → BPP前 → 初始化 → BPP后 → 使用 → 销毁*。

追问 Bean 的三种初始化钩子，谁先谁后？

严格顺序：**`@PostConstruct` → `InitializingBean.afterPropertiesSet()` → 自定义 `init-method`**。`@PostConstruct` 由 `CommonAnnotationBeanPostProcessor` 在 *BPP 前*阶段调用，比后两者早；`afterPropertiesSet` 是接口回调，比 `init-method`（配置驱动）早。销毁顺序类似：`@PreDestroy` → `destroy()` → `destroy-method`。

追问 AOP 代理是在 Bean 生命周期的哪一步生效的？

在 **⑥ BeanPostProcessor.postProcessAfterInitialization** 阶段。Spring 有一个专门的 `AbstractAutoProxyCreator`（实现了 `BeanPostProcessor`），它在*初始化后*检查这个 Bean 是不是需要代理（有没有匹配的 `@Aspect` 切点）—— 如果需要，就用 JDK Proxy 或 CGLIB 生成代理对象，**用代理替换掉原始 Bean** 放进容器。所以业务代码 `@Autowired` 拿到的其实是代理对象。

## 面试场景 7：Bean 的作用域有哪些？

🧑‍💻 你

Scope含义生命周期

`singleton`（默认）整个容器唯一一个实例容器启动创建 → 容器关闭销毁
`prototype`每次 `getBean` 都新建一个Spring *不管销毁*（拿到后 GC 决定）
`request`每个 HTTP 请求一个（Web 环境）请求开始 → 请求结束
`session`每个 HTTP Session 一个Session 创建 → Session 销毁
`application`每个 ServletContext 一个（比 singleton 广一层）Web 应用启动 → 应用关闭
`websocket`每个 WebSocket 会话一个WS 连接期间

用法：`@Scope("prototype")` 或 `@Scope(ConfigurableBeanFactory.SCOPE_PROTOTYPE)`。**99% 的业务 Bean 都是 `singleton`**，因为无状态服务只需要一份。有状态对象（比如 Web 环境的用户上下文）才用 `request`/`session`。

陷阱 **singleton Bean 里注入 prototype Bean** 时，prototype 只会被注入*一次*——即容器启动时。之后 singleton 每次调用都是同一个 prototype 实例，*失去了 prototype 的意义*。解决办法：注入 `ObjectProvider<T>` 或用 `@Lookup` 方法注入，每次调用时从容器*动态获取*。

## 面试场景 8：循环依赖是什么？Spring 怎么解决？（★经典）

🎤 面试官

什么是循环依赖？Spring 是怎么解决单例 Bean 的循环依赖的？

🧑‍💻 你

**循环依赖**：A 依赖 B，B 又依赖 A（可以是二人环，也可以更长）。如果没有特殊处理，创建 A 需要 B、创建 B 需要 A，就会陷入死循环 `StackOverflowError`。

```
@Service
public class A {
@Autowired private B b;   // A 需要 B
}

@Service
public class B {
@Autowired private A a;   // B 需要 A → 循环
}
```

Spring 通过 **三级缓存（Three-level Cache）**解决*单例 Bean 通过 setter/字段注入形成的循环依赖*。三级缓存都定义在 `DefaultSingletonBeanRegistry`：

级别字段名存的什么作用

一级`singletonObjects`完全初始化好的 Bean（成品）正常 `getBean` 直接从这里拿
二级`earlySingletonObjects`提前暴露的 Bean（半成品，可能是 AOP 代理）循环依赖时给「后来者」用
三级`singletonFactories``ObjectFactory<?>`（Bean 工厂）按需生成早期引用，处理 AOP 提前代理

**关键设计**：三级缓存里放的不是对象，而是*能生成对象的工厂*。这样只有真正被循环依赖时，才触发工厂的 `getObject()`，避免每个 Bean 都提前生成代理。

追问 三级缓存能不能改成两级？

能，但会带来*额外的性能开销*。如果只有二级缓存（直接存早期 Bean），那么**每个 Bean 在实例化后都必须提前生成 AOP 代理**（因为不知道谁会来循环依赖你），这对不需要代理的 Bean 也是浪费。三级缓存里放 `ObjectFactory`，只有真正被别人依赖时才 `getObject()` 生成代理，*按需生成*。这就是为什么设计成三级 —— **三级 = 延迟代理的能力**。

## 面试场景 9：三级缓存的完整流程（源码级）

🧑‍💻 你

以 `A 依赖 B、B 依赖 A` 为例，一步步走：

```
步骤 1：getBean("a")
→ 一级、二级、三级都没有 → 走创建流程
→ ① 实例化 A（构造器创建裸对象 rawA）
→ ★ 把 () -> getEarlyBeanReference(rawA) 放进三级缓存 singletonFactories
→ ② 属性赋值：发现要注入 B → getBean("b")

步骤 2：getBean("b")（在 A 的属性赋值过程中触发）
→ 一级、二级、三级都没有 → 走创建流程
→ ① 实例化 B（rawB）
→ ★ 把 () -> getEarlyBeanReference(rawB) 放进三级缓存
→ ② 属性赋值：发现要注入 A → getBean("a")

步骤 3：getBean("a")（在 B 的属性赋值过程中触发）
→ 一级没有 → 二级没有 → ★ 三级有！
→ 调 singletonFactories.get("a").getObject()
→ 内部走一遍 SmartInstantiationAwareBeanPostProcessor.getEarlyBeanReference
→ 如果 A 需要 AOP，就在这里生成代理 proxyA
→ 否则返回 rawA
→ 把 proxyA（或 rawA）放进二级 earlySingletonObjects
→ 从三级缓存移除 A 的 factory
→ 返回 proxyA 给 B

步骤 4：B 拿到 A 的早期引用 → 继续初始化 B → B 完成 → 放进一级 singletonObjects
→ 从二级、三级移除 B

步骤 5：A 的属性赋值完成（B 已注入）→ 继续初始化 A → A 完成 → 放进一级 singletonObjects
→ 从二级、三级移除 A

完成。A 和 B 都在一级缓存里了。
```

追问 步骤 3 里为什么要走 `getEarlyBeanReference` 而不是直接返回 `rawA`？

因为要处理**循环依赖 + AOP 的组合场景**。假设 A 需要被 AOP 代理，那么 B 里拿到的 A 应该是*代理对象*而不是原始 A—— 否则最后一级缓存里放的是代理 A，B 里持有的是原始 A，**同一个 Bean 两个身份**就出问题了。`getEarlyBeanReference` 通过 `SmartInstantiationAwareBeanPostProcessor`（AOP 用它的 `AbstractAutoProxyCreator`）提前生成代理，保证「B 里的 A」和「容器里的 A」是同一个代理对象。

## 面试场景 10：构造器循环依赖为什么解决不了？

🎤 面试官

三级缓存这么厉害，那构造器注入的循环依赖能不能解决？

🧑‍💻 你

**解决不了**。原因很本质：三级缓存的核心前提是「*实例化后、初始化前*能提前暴露一个引用」——而构造器注入要求**依赖必须在构造器执行时就传入**，此时对象还没被 `new` 出来，*连裸对象都没有，更别说放进缓存了*。

```
创建 A → 调 A 的构造器 → 构造器要求传 B
→ 去创建 B → 调 B 的构造器 → 构造器要求传 A
→ 去创建 A → 一级没有、二级没有、三级也没有（A 还没实例化完，没进缓存）
→ 又要创建 A → 死循环 → BeanCurrentlyInCreationException
```

Spring 会检测到并直接抛异常：`Requested bean is currently in creation: Is there an unresolvable circular reference?`

**三种解法**：

1. **改成 Setter 或字段注入**：至少一方从构造器改成 setter，让 Spring 能在实例化后提前暴露引用。

2. **用 `@Lazy` 注解**：给循环依赖的一方加 `@Lazy`，Spring 会注入一个*代理对象*而不是真实 Bean，实际调用方法时才去容器解析。

3. **重构消除循环**：*循环依赖本身通常是设计问题*—— 提取共同的第三方服务、事件解耦、依赖倒置。

追问 `@Lazy` 到底怎么打破循环依赖？

Spring 遇到 `@Lazy` 修饰的注入点时，注入的不是真正的 Bean，而是**一个代理对象**（JDK Proxy 或 CGLIB）。这个代理内部持有 `BeanFactory`，等到*真正调用代理方法时*才从容器里 `getBean` 拿到真身，然后转发调用。这就把「构造时立刻要依赖」推迟成了「用时才拿依赖」—— 类似 JIT 的懒加载思路。所以构造器循环依赖场景，给其中一方参数加 `@Lazy` 就能救。

陷阱 Spring Boot 2.6+ **默认禁止循环依赖**（`spring.main.allow-circular-references=false`），启动直接失败。这是官方推动开发者*重构消除循环*的强制信号 —— 循环依赖能解决≠应该有。真的需要，改配置为 `true`，但更推荐重构。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：三种注入方式对比

```
// 推荐：构造器注入 + final + Lombok
@Service
@RequiredArgsConstructor
public class OrderService {
private final UserDao userDao;
private final PayGateway payGateway;
}

// 可选：Setter 注入（允许循环依赖）
@Service
public class UserService {
private OrderService orderService;

@Autowired
public void setOrderService(OrderService orderService) {
this.orderService = orderService;
}
}

// 不推荐：字段注入
@Service
public class ItemService {
@Autowired private ItemDao itemDao;  // ← IDEA 会警告 "Field injection is not recommended"
}
```

### 验证 2：Bean 生命周期的所有钩子

```
@Component
public class LifecycleDemo
implements BeanNameAware, BeanFactoryAware, ApplicationContextAware,
InitializingBean, DisposableBean {

public LifecycleDemo() {
System.out.println("① 构造器 → 实例化");
}

@Autowired
public void setDep(SomeDep dep) {
System.out.println("② 属性赋值 → 注入 " + dep);
}

@Override public void setBeanName(String name) {
System.out.println("③ Aware: setBeanName = " + name);
}
@Override public void setBeanFactory(BeanFactory bf) {
System.out.println("③ Aware: setBeanFactory");
}
@Override public void setApplicationContext(ApplicationContext ctx) {
System.out.println("③ Aware: setApplicationContext");
}

@PostConstruct
public void postConstruct() {
System.out.println("⑤ @PostConstruct");
}

@Override public void afterPropertiesSet() {
System.out.println("⑤ InitializingBean.afterPropertiesSet");
}

// XML/JavaConfig 里指定的 init-method
public void customInit() {
System.out.println("⑤ custom init-method");
}

@PreDestroy
public void preDestroy() {
System.out.println("⑧ @PreDestroy");
}

@Override public void destroy() {
System.out.println("⑧ DisposableBean.destroy");
}

public void customDestroy() {
System.out.println("⑧ custom destroy-method");
}
}

// 加一个 BeanPostProcessor 看④和⑥
@Component
public class DemoBPP implements BeanPostProcessor {
@Override public Object postProcessBeforeInitialization(Object bean, String name) {
if (bean instanceof LifecycleDemo) System.out.println("④ BPP before");
return bean;
}
@Override public Object postProcessAfterInitialization(Object bean, String name) {
if (bean instanceof LifecycleDemo) System.out.println("⑥ BPP after (AOP 代理在这里生成)");
return bean;
}
}
```

### 验证 3：AOP 五种 Advice 执行顺序

```
@Aspect
@Component
public class LoggingAspect {

@Pointcut("execution(* com.example.service.*.*(..))")
public void serviceMethods() {}

@Before("serviceMethods()")
public void before(JoinPoint jp) {
System.out.println("@Before  → " + jp.getSignature().getName());
}

@After("serviceMethods()")
public void after(JoinPoint jp) {
System.out.println("@After   → " + jp.getSignature().getName());
}

@AfterReturning(pointcut = "serviceMethods()", returning = "ret")
public void afterReturning(JoinPoint jp, Object ret) {
System.out.println("@AfterReturning → ret = " + ret);
}

@AfterThrowing(pointcut = "serviceMethods()", throwing = "ex")
public void afterThrowing(JoinPoint jp, Throwable ex) {
System.out.println("@AfterThrowing → " + ex.getMessage());
}

@Around("serviceMethods()")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
System.out.println("@Around 前");
long start = System.currentTimeMillis();
try {
Object ret = pjp.proceed();   // ← 必须调，否则目标方法不执行
System.out.println("@Around 后（耗时 " + (System.currentTimeMillis() - start) + "ms）");
return ret;
} catch (Throwable t) {
System.out.println("@Around 捕获异常：" + t.getMessage());
throw t;
}
}
}
```

### 验证 4：手工触发循环依赖（观察 Spring 报错）

```
@Service
public class ServiceA {
private final ServiceB b;
public ServiceA(ServiceB b) { this.b = b; }   // ← 构造器注入 B
}

@Service
public class ServiceB {
private final ServiceA a;
public ServiceB(ServiceA a) { this.a = a; }   // ← 构造器注入 A → 循环
}

// 启动直接报错：
// BeanCurrentlyInCreationException: Error creating bean with name 'serviceA':
//   Requested bean is currently in creation: Is there an unresolvable circular reference?

// 修复方案：给一方加 @Lazy
@Service
public class ServiceA {
private final ServiceB b;
public ServiceA(@Lazy ServiceB b) { this.b = b; }  // ← @Lazy 注入代理，打破循环
}
```

### 验证 5：观察三级缓存（用反射 peek 底层）

```
@Component
public class CachePeeker implements ApplicationContextAware {

@Override
public void setApplicationContext(ApplicationContext ctx) throws BeansException {
DefaultListableBeanFactory bf =
(DefaultListableBeanFactory) ((ConfigurableApplicationContext) ctx).getBeanFactory();

// 反射拿三级缓存字段
Map<String, Object> l1 = getField(bf, "singletonObjects");
Map<String, Object> l2 = getField(bf, "earlySingletonObjects");
Map<String, Object> l3 = getField(bf, "singletonFactories");

System.out.println("一级缓存 size = " + l1.size());
System.out.println("二级缓存 size = " + l2.size());
System.out.println("三级缓存 size = " + l3.size());
// 正常启动完之后：一级满、二三级基本空（除非中途 peek）
}

@SuppressWarnings("unchecked")
private static <T> T getField(Object obj, String name) {
try {
Field f = DefaultSingletonBeanRegistry.class.getDeclaredField(name);
f.setAccessible(true);
return (T) f.get(obj);
} catch (Exception e) { throw new RuntimeException(e); }
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 IoC 和 DI 是什么关系？为什么 Spring 官方推荐构造器注入？</summary>

IoC 是「控制反转」思想，DI 是它最主流的实现方式（依赖注入）。构造器注入的优势：字段可用 `final`（不可变、线程安全）、强制依赖启动时就校验、便于单元测试（直接 new，无需 Spring 容器）、避免字段注入的隐藏依赖问题。唯一缺点：无法解决构造器循环依赖 —— 但这本来就是设计问题。

</details>

<details>

<summary>Q2 完整背出 Bean 的生命周期八步。</summary>

① 实例化（构造器） → ② 属性赋值（DI） → ③ Aware 回调（BeanName/BeanFactory/ApplicationContext） → ④ BeanPostProcessor.postProcessBeforeInitialization → ⑤ 初始化（@PostConstruct → InitializingBean.afterPropertiesSet → init-method） → ⑥ BeanPostProcessor.postProcessAfterInitialization（**AOP 代理在这里生成**） → ⑦ 使用中 → ⑧ 销毁（@PreDestroy → DisposableBean.destroy → destroy-method）。

</details>

<details>

<summary>Q3 Spring 三级缓存分别是什么？为什么设计成三级而不是两级？</summary>

一级 `singletonObjects`（成品 Bean）、二级 `earlySingletonObjects`（早期暴露 Bean，可能是 AOP 代理）、三级 `singletonFactories`（ObjectFactory 工厂）。三级的意义：**把「生成早期代理」的动作延迟**——只有真正发生循环依赖时才调 factory.getObject() 生成代理，否则不生成，避免无效开销。二级缓存不够是因为无法区分「需不需要代理」，会导致所有 Bean 都提前代理化。

</details>

<details>

<summary>Q4 为什么构造器循环依赖 Spring 解决不了？怎么救？</summary>

三级缓存要求「实例化后、初始化前」暴露引用，而构造器注入在*实例化那步*就要求依赖 —— 对象连 new 都还没完成，无法进缓存，Spring 会抛 `BeanCurrentlyInCreationException`。救法：**①** 改一方为 setter 或字段注入；**②** 给一方参数加 `@Lazy`（注入代理，用时才解析）；**③** 重构消除循环（最好的方案，循环依赖通常是设计问题）。

</details>

<details>

<summary>Q5 AOP 的 5 种 Advice 里 @After 和 @AfterReturning 有什么区别？@Around 的最大陷阱是什么？</summary>

`@After` 无论目标方法正常返回还是抛异常都会执行（类似 finally），拿不到返回值；`@AfterReturning` 只在*正常返回*时执行，能通过 `returning` 参数拿到返回值。`@Around` 的最大陷阱：**必须手动调 `ProceedingJoinPoint.proceed()`**，忘记调会导致目标方法根本不执行、返回 null—— 事务/限流/性能切面的经典 bug。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Spring 官方 · The IoC Container —— `BeanFactory`/`ApplicationContext` 官方规范

- Spring 官方 · Aspect Oriented Programming with Spring —— AOP 完整章节

- Martin Fowler · Inversion of Control Containers and the Dependency Injection pattern —— DI 术语的经典出处

#### 🔗 关联课件

-

-

-

-

-

#### 🧭 下一课预告

Lesson 0062：**Spring AOP 深入 —— JDK Proxy vs CGLIB & 代理失效的三个经典场景（内部方法调用、private、static）**。本课打好 AOP 概念基础后，下一课直接扎到源码和踩坑现场。

💬 有任何疑问 —— 「三级缓存的这一步能不能再画细一点？」「@Lazy 的代理和 AOP 的代理是同一种吗？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


