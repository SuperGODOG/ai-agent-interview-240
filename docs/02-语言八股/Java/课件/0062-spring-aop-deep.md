> Lesson 0062 · 阶段八 · Spring · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0062 · Spring AOP 深入：JDK vs CGLIB & Bean 后置处理器 & 常见坑

上一课  把 IoC 和 AOP 的*概念、通知类型、应用场景*讲清楚了。这一课要深挖 AOP 的**内部机制**：Spring 何时选 JDK 何时选 CGLIB？Pointcut 表达式怎么写？多个切面的执行顺序谁定？为什么 `@Transactional` 在自调用时会失效？底层的 `BeanPostProcessor` 是怎么把普通 Bean 换成代理 Bean 的？—— 这些是 P6/P7 面试的高频追问点，也是线上 bug 最常见的源头。

本课主源仍是 的 AOP 部分，并结合 Spring Framework 源码（`AbstractAutoProxyCreator`）补齐  没细讲的**「代理选择规则、Pointcut 语法、自调用失效」**三个高频追问。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Spring Boot 2.x 里，一个实现了 `UserService` 接口的 `UserServiceImpl` 被 `@Service` 标注，Spring 生成的代理是 JDK 代理还是 CGLIB 代理？</summary>

**CGLIB**。Spring Boot 2.0 起 `spring.aop.proxy-target-class` 默认为 `true`，无论有没有接口都用 CGLIB。老 Spring Framework 才是「有接口用 JDK」的规则。第 3 题细讲。

</details>

<details>

<summary>Q0.2 一个类里 `methodA()` 直接调用 `this.methodB()`，而 `methodB()` 上加了 `@Transactional`。事务会开启吗？</summary>

**不会。**`this` 是原始对象不是代理对象，绕过了 AOP 拦截器链。这是 Spring 事务失效的 Top 1 场景。第 6 题给三种解法。

</details>

## 面试场景 1：Spring AOP 和 AspectJ 的区别？

🎤 面试官

你用的是 Spring AOP 还是 AspectJ？它们有什么区别？

🧑‍💻 你

项目里用的是 Spring AOP，但注解语法（`@Aspect`、`@Pointcut`）借用的是 AspectJ 的。两者本质区别在**织入时机**：

- **Spring AOP**：*运行时字节码代理*。Bean 初始化后由 `BeanPostProcessor` 生成一个代理对象包装原 Bean。只能拦截**方法级**调用，不能拦截字段读写、构造器、静态方法。

- **AspectJ**：*编译时或类加载时字节码织入*。用 `ajc` 编译器把切面代码直接织进 `.class` 字节码，或者用 LTW（Load-Time Weaving）在类加载时织入。功能强大得多 —— 能拦截字段、构造器、甚至 `final` 方法。

- **实际项目怎么选**：绝大多数场景 Spring AOP 够用，只有*需要拦截字段访问 / 构造器*时才上 AspectJ。Spring 官方推荐组合是 **Spring AOP 实现 + AspectJ 注解语法**，兼顾易用性和运行时灵活性。

追问 AspectJ 编译时织入具体怎么做？

用 `ajc`（AspectJ Compiler）替代 `javac` 编译 `.java` 和 `.aj` 文件。`ajc` 会分析所有切面定义，直接**把通知代码内联进目标方法的字节码**。比如 `@Before` 就在目标方法的第一条字节码前插入调用；`@Around` 会把原方法体包装到内部。因为已经改字节码了，运行时无需代理，*直接调用目标对象的方法就自带增强* —— 这就是为什么 AspectJ 能拦截 `final` 方法。

追问 Spring AOP 用 AspectJ 注解，但底层不用 AspectJ 织入，是什么关系？

Spring 只是**借用** AspectJ 的 `@Aspect`、`@Before`、`@Pointcut` 等注解语法（因为大家用得熟），底层实现仍是自己的 JDK Proxy / CGLIB 运行时代理。也就是说：你在类上写 `@Aspect`，Spring 扫描到之后会解析这些注解生成自己的 `Advisor`，然后交给 `ProxyFactory` 生成代理 —— 全程*不涉及 AspectJ 运行时或 `ajc`*。

## 面试场景 2：Spring AOP 的两种代理机制

🎤 面试官

Spring AOP 用哪两种动态代理？分别怎么工作？

🧑‍💻 你

回顾 ：

- **JDK 动态代理**：`Proxy.newProxyInstance(loader, interfaces, handler)` 在运行时生成一个*实现同一组接口*的代理类。方法调用会走 `InvocationHandler.invoke()`。**要求目标类必须实现接口**。

- **CGLIB 动态代理**：用 ASM 字节码库*动态生成目标类的子类*，重写所有非 `final` 的方法。方法调用会走 `MethodInterceptor.intercept()`。**不要求接口，但要求目标类和方法都不能是 `final`**。

Spring 里对这两者都做了封装，统一暴露 `ProxyFactory` API：

```
ProxyFactory factory = new ProxyFactory(targetBean);
factory.addAdvice(new MyMethodInterceptor());
factory.setProxyTargetClass(true);   // 强制走 CGLIB
Object proxy = factory.getProxy();
```

追问 JDK 代理和 CGLIB 代理生成的代理类分别继承 / 实现了什么？

JDK 代理类：`public final class $Proxy0 extends java.lang.reflect.Proxy implements UserService` —— 继承 `Proxy`，实现目标接口，*不是*目标类的子类。所以 `proxy instanceof UserServiceImpl` 是 `false`。

CGLIB 代理类：`public class UserServiceImpl$$EnhancerByCGLIB$$abc123 extends UserServiceImpl` —— 继承目标类。所以 `proxy instanceof UserServiceImpl` 是 `true`。

## 面试场景 3：Spring 何时选 JDK 何时选 CGLIB？⭐经典

🎤 面试官

Spring AOP 是怎么决定用 JDK 还是 CGLIB 的？Spring Boot 2 之后有什么变化？

🧑‍💻 你

核心决策来自 `DefaultAopProxyFactory#createAopProxy`：

```
public AopProxy createAopProxy(AdvisedSupport config) {
if (!NativeDetector.inNativeImage()
&& (config.isOptimize()
|| config.isProxyTargetClass()
|| hasNoUserSuppliedProxyInterfaces(config))) {
Class<?> targetClass = config.getTargetClass();
if (targetClass.isInterface() || Proxy.isProxyClass(targetClass)) {
return new JdkDynamicAopProxy(config);
}
return new ObjenesisCglibAopProxy(config);   // ← CGLIB
}
return new JdkDynamicAopProxy(config);           // ← JDK
}
```

翻译成人话：

- **Spring Framework 默认规则**（`proxyTargetClass=false`）：目标类*有实现接口*就用 JDK 代理；*没有接口*就用 CGLIB。

- **Spring Boot 2.0+ 默认规则**：`spring.aop.proxy-target-class=true` —— **不管有没有接口，一律用 CGLIB**。想恢复自动选择要显式改回 `false`。

追问 Spring Boot 2 为什么要改成默认 CGLIB？

老规则「有接口用 JDK」有一个经典坑：假如你的 `UserServiceImpl implements UserService`，Spring 生成的是 JDK 代理（实现 `UserService` 但*不是* `UserServiceImpl`）。如果你在别处写 `@Autowired private UserServiceImpl userService;`（按具体类注入），会抛 `BeanNotOfRequiredTypeException` —— 因为 Bean 容器里存的是 JDK 代理，没法转成 `UserServiceImpl`。全 CGLIB 之后，代理类是 `UserServiceImpl` 的子类，两种注入方式都能拿到，兼容性最好。

追问 我想在 Spring Boot 里强制某个 Bean 走 JDK 代理，怎么做？

三种方式，从粗到细：

① 全局配置 `spring.aop.proxy-target-class=false`（影响所有 Bean）；

② 在 `@EnableAspectJAutoProxy(proxyTargetClass=false)` 上关闭（影响所有切面代理）；

③ 用 `ProxyFactoryBean` 或手动 `ProxyFactory` 显式控制单个 Bean。生产环境不建议改，保持 CGLIB 一致性。

## 面试场景 4：Pointcut 表达式怎么写？⭐核心

🎤 面试官

写一个 Pointcut，匹配 `com.example.service` 包下所有 public 方法。再写一个匹配所有带 `@Transactional` 的方法。

🧑‍💻 你

Pointcut 表达式核心语法（AspectJ 表达式）：

```
execution(修饰符? 返回类型 包.类.方法(参数) 异常?)
```

常用 designator（切点指示符）：

指示符作用示例

`execution`匹配方法执行`execution(* com.example.service.*.*(..))`
`within`匹配类型（比 execution 快）`within(com.example.service.*)`
`this`匹配代理对象是某类型`this(com.example.UserService)`
`target`匹配目标对象是某类型`target(com.example.UserServiceImpl)`
`args`匹配参数类型`args(java.lang.String, ..)`
`@annotation`匹配方法带某注解`@annotation(org.springframework.transaction.annotation.Transactional)`
`@within`匹配类带某注解`@within(org.springframework.stereotype.Service)`
`bean`匹配 Bean 名称（Spring 扩展）`bean(userService)` 或 `bean(*Service)`

回答两个题目：

```
@Pointcut("execution(public * com.example.service.*.*(..))")
public void allPublicServiceMethods() {}

@Pointcut("@annotation(org.springframework.transaction.annotation.Transactional)")
public void transactionalMethods() {}
```

追问 表达式里的 `*` 和 `..` 有什么区别？

`*` 匹配**一个**：一个包段（不含 `.`）、一个字符组成的方法名、一个参数类型。`..` 匹配**零个或多个**：包路径（跨多个 `.`）、参数列表里的任意数量任意类型。例：`execution(* com..service.*.*(..))` 匹配 `com` 下任意子包里 `service` 包的所有类所有方法，参数任意。

追问 多个 Pointcut 表达式怎么组合？

用 `&&`、`||`、`!` 组合（在 XML 里要写 `and`/`or`/`not`）：

`@Pointcut("execution(* com.example.service.*.*(..)) && !@annotation(NoLog)")` —— 匹配 service 包所有方法但排除带 `@NoLog` 的。也可以复用别的 Pointcut 方法：`@Before("allPublicServiceMethods() && args(userId,..)")`。

## 面试场景 5：多个 Advice 的执行顺序

🎤 面试官

一个方法上同时有 `@Around`、`@Before`、`@After`、`@AfterReturning`、`@AfterThrowing`，执行顺序是什么？

🧑‍💻 你

单个切面内 5 种 Advice 的执行顺序（Spring 4.3+ 修正后）：

```
@Around（前半）
└─ @Before
└─ 目标方法执行
└─ @AfterReturning（正常返回时）或 @AfterThrowing（抛异常时）
└─ @After（相当于 finally，一定执行）
@Around（后半，proceed() 之后）
```

验证一下调用日志：`Around-start → Before → target → AfterReturning → After → Around-end`。

**多个切面之间**的顺序用 `@Order` 或实现 `Ordered` 接口控制，值越*小*越先执行（*进入*时先执行，*退出*时最后执行 —— 像洋葱圈）：

```
@Aspect @Order(1) public class LogAspect { ... }     // 最外层
@Aspect @Order(2) public class AuthAspect { ... }
@Aspect @Order(3) public class TxAspect { ... }      // 最内层
```

执行序：`Log-in → Auth-in → Tx-in → target → Tx-out → Auth-out → Log-out`。

陷阱 Spring 4.3 之前，`@After` 和 `@AfterReturning` 的相对顺序不稳定，有时会先 `@After` 再 `@AfterReturning`。4.3 之后**修正为规范顺序**（`@AfterReturning` 先于 `@After`）。老项目升级时要注意，如果依赖了错误顺序的代码要重跑测试。

追问 `@Transactional` 和自定义日志切面同时存在，事务提交前还是提交后打日志？

看 `@Order`。默认 `@Transactional` 走的是 `TransactionInterceptor`，其 order 是 `Ordered.LOWEST_PRECEDENCE`（最大值 = 最里层）。所以自定义日志切面不加 order 时也是默认最大值，顺序不确定。**让日志切面 `@Order(1)`**，日志就会在事务外面 —— 「先记日志，再开事务；事务提交，最后打完成日志」。反之如果想在事务内记日志（比如日志也参与回滚），就把 order 设得比 `@Transactional` 大。

## 面试场景 6：AOP 失效之一 —— 自调用⭐经典

🎤 面试官

看这段代码，`save()` 里调用 `update()`，事务会开吗？为什么？

```
@Service
public class UserService {

public void save(User user) {
userMapper.insert(user);
this.update(user);           // ← 关键这行
}

@Transactional
public void update(User user) {
userMapper.update(user);
}
}
```

🧑‍💻 你

**不会开事务。**原因：Spring AOP 只对*从外部调用代理对象*的方法生效。`this.update(user)` 里 `this` 是**原始的 `UserService` 实例**，不是被 `@Transactional` 包装的代理对象。调用绕过了代理的 `InvocationHandler`/`MethodInterceptor`，事务拦截器根本没进入。

这个坑不止 `@Transactional`，凡是*基于 AOP 实现的注解*都中招：`@Async`、`@Cacheable`、`@CacheEvict`、`@Retryable`、`@PreAuthorize` —— 全部在自调用时静默失效。

三种解法：

1. **拆到不同 Bean**（最推荐）：把 `update()` 挪到另一个 `UserUpdateService`，通过 `@Autowired` 注入调用。天然走代理。

2. **自注入（self-injection）**：`@Autowired private UserService self;`，然后 `self.update(user)`。`self` 拿到的就是代理对象。Spring 4.3+ 支持自注入，不会造成循环依赖问题。

3. **AopContext**：先开启 `@EnableAspectJAutoProxy(exposeProxy=true)`，然后 `((UserService) AopContext.currentProxy()).update(user)`。侵入性最强，不推荐。

追问 为什么自注入不会产生循环依赖异常？

Spring 有**三级缓存**处理循环依赖（0064 会细讲）：`singletonObjects`（成品）、`earlySingletonObjects`（半成品）、`singletonFactories`（工厂）。自注入时，`UserService` Bean 正在创建，Spring 会从二级/三级缓存里拿到自己的*早期引用*（如果开启了 AOP，早期引用就是已经生成好的代理）注入进去。所以 `self` 就是代理对象，且不会死循环。

追问 自调用失效有静态检查工具能发现吗？

SonarQube 的 `java:S6809` 规则 *"Methods with Spring proxy should not be called via `this`"* 就是干这个的，会扫出所有 `this.xxx()` 调用了带 `@Transactional`/`@Async`/`@Cacheable` 的方法。生产项目强烈建议开启。

## 面试场景 7：AOP 失效之二 —— final、private、static

🧑‍💻 你

三个方法修饰符会导致 AOP 失效：

- **`final` 方法**：CGLIB 通过*生成子类覆盖方法*实现代理，`final` 方法不能被覆盖，代理时会跳过（不报错但没增强）。JDK 代理不受影响（只代理接口方法）。

- **`private` 方法**：JDK 代理只能拦截*接口里声明的方法*，private 方法根本不在接口里；CGLIB 通过子类覆盖，private 方法子类看不到 —— 两种代理都不能拦截 private 方法。

- **`static` 方法**：属于类而非实例，代理对象是实例代理，天然拦不到静态方法。

此外还有*非隐含*的失效场景：

- 抛出的异常被自己 catch 吞掉 → `@AfterThrowing` 不触发、事务不回滚。

- 目标类没被 Spring 容器管理（`new` 出来的） → 根本没走 AOP 增强。

- 方法被 `@Configuration(proxyBeanMethods=false)` 关闭代理。

追问 CGLIB 遇到 `final` 类会怎样？

**直接抛异常**：`Cannot subclass final class ...`。因为 `final` 类根本无法被继承。所以想 Spring AOP 生效，目标类不能是 `final`；如果非要用 `final`（比如某些 DDD 场景），只能让它实现接口然后走 JDK 代理。

## 面试场景 8：AOP 底层 —— BeanPostProcessor 是怎么把 Bean 换成代理的？

🎤 面试官

Spring 是在什么时机、通过什么机制把普通 Bean 替换成代理 Bean 的？

🧑‍💻 你

核心机制是 **`BeanPostProcessor`**，具体实现类是 `AbstractAutoProxyCreator`（继承链末端是 `AnnotationAwareAspectJAutoProxyCreator`）。它在 Bean 生命周期的*初始化后*阶段介入：

```
Bean 生命周期简化版：
1. 实例化 (instantiate)
2. 属性注入 (populateBean)
3. Aware 回调
4. BeanPostProcessor.postProcessBeforeInitialization()
5. @PostConstruct / InitializingBean.afterPropertiesSet() / init-method
6. BeanPostProcessor.postProcessAfterInitialization()   ← ★ AOP 在这里介入
7. Bean 就绪，放入容器
```

在第 6 步，`AbstractAutoProxyCreator#postProcessAfterInitialization` 会：

1. 遍历所有已注册的 `Advisor`（切面 + 通知的组合）。

2. 调用 `Pointcut` 判断当前 Bean 是否有*任何*方法匹配。

3. 如果匹配到，用 `ProxyFactory` 生成代理对象。

4. 返回代理对象**替换**原 Bean —— 容器里存的从此就是代理。

所以后续任何 `@Autowired` 注入拿到的都是代理对象，AOP 才生效。

追问 如果 Bean A 依赖 Bean B，且 B 需要 AOP 代理，A 拿到的是原 B 还是代理 B？

**代理 B**。`populateBean`（属性注入）发生在*初始化之前*，而 A 是被*后于 B 创建*的（因为依赖 B），所以 A 注入的时候 B 已经走完 `postProcessAfterInitialization`，容器里存的是代理 B，A 拿到的也是代理 B。*但如果 A 和 B 存在循环依赖*，会走三级缓存机制提前暴露 B 的代理引用（`getEarlyBeanReference`），也能保证注入的是代理。

追问 为什么 AOP 用 `BeanPostProcessor` 而不用 `FactoryBean`？

`BeanPostProcessor` 是*批量、自动*的 —— 一次注册对所有 Bean 生效；`FactoryBean` 是*单个、手动*的 —— 每个要代理的 Bean 都要显式声明一个 `ProxyFactoryBean`。老 Spring XML 时代确实用 `ProxyFactoryBean`，Spring 2.0 引入 `<aop:config>` 之后就统一走 `AbstractAutoProxyCreator` 了 —— 一次注册，全局生效，无侵入。

## 面试场景 9：Spring 事务、Async、Cacheable 都是 AOP 实现的

🧑‍💻 你

Spring 的几个「魔法注解」本质都是 AOP 拦截器：

注解拦截器做的事本课件

`@Transactional``TransactionInterceptor`方法前开事务 / 方法后按结果 commit / rollback
`@Async``AsyncExecutionInterceptor`把方法调用*丢到线程池*异步执行，立即返回 `Future`
`@Cacheable``CacheInterceptor`调用前查缓存命中就直接返回，未命中执行方法并缓存结果—
`@Retryable``RetryOperationsInterceptor`方法抛异常时按策略自动重试—
`@PreAuthorize``MethodSecurityInterceptor`方法前做权限检查，无权限抛 `AccessDeniedException`—

知道这个映射关系，就能一眼看穿这些注解「为什么会失效」：*失效原因都是绕过了 AOP 代理*（自调用、内部方法、非 Bean 对象）。

追问 `@Async` 在同一个类的方法里自调用为什么不异步？

同「自调用失效」原理。`this.asyncMethod()` 直接调用原对象，绕过 `AsyncExecutionInterceptor`，就在当前线程同步执行完了。解法一样：拆到别的 Bean 或自注入 `self.asyncMethod()`。

## 面试场景 10：AOP 的性能开销

🎤 面试官

用了 AOP 会不会慢很多？

🧑‍💻 你

分几个维度回答：

- **代理生成成本（一次性）**：CGLIB 首次生成子类字节码需要几毫秒到几十毫秒（ASM 生成 + 类加载），生成后会缓存在 `Enhancer` 里。JDK 代理更快（`Proxy.newProxyInstance` 内部也有缓存）。这个成本只发生在*容器启动 Bean 初始化*时，运行时不再产生。

- **调用开销（每次）**：*JDK 代理*：每次调用走一次 `Method.invoke`，早期 JDK 有反射开销，JDK 17+ 用 `MethodHandle` 优化后接近直接调用。*CGLIB 代理*：调用走 `MethodInterceptor.intercept`，内部用 `MethodProxy.invokeSuper` 直接调子类的父类方法（不走反射），性能极高，几乎和直接调用相当。

- **拦截器链**：每个 `Advisor` 都会加一层 `ReflectiveMethodInvocation`。10 个切面就多 10 层调用栈，但仍在纳秒级。

- **结论**：*绝大多数业务场景 AOP 开销可忽略*（每次 < 1μs），除非在极端 hot path（一秒调用百万次的场景）才需要优化 —— 那种场景本身就不该用 AOP。

追问 一个 Bean 上有 5 个切面，调用一次方法走多少层调用？

Spring 会把 5 个 `Advisor` 组成 `ReflectiveMethodInvocation` 链，每个 `proceed()` 递归调用下一个。所以调用栈会多 5-6 层（每个切面一层 + 最终目标方法一层）。栈深不会爆，但异常栈会长得吓人 —— 这就是 Spring 项目常见的百层异常栈的原因之一。

## 💻 代码验证

### 验证 1：一个完整的日志切面

```
// 1. 加依赖 spring-boot-starter-aop（自动导入 AspectJ 注解 + 织入器）

// 2. 定义切面
@Aspect
@Component
@Slf4j
public class LoggingAspect {

@Pointcut("execution(public * com.example.service.*.*(..))")
public void serviceLayer() {}

@Around("serviceLayer()")
public Object logAround(ProceedingJoinPoint pjp) throws Throwable {
String method = pjp.getSignature().toShortString();
long start = System.currentTimeMillis();
log.info("[BEFORE] {} args={}", method, Arrays.toString(pjp.getArgs()));
try {
Object ret = pjp.proceed();
log.info("[AFTER ] {} took={}ms ret={}", method,
System.currentTimeMillis() - start, ret);
return ret;
} catch (Throwable ex) {
log.error("[ERROR ] {} threw {}", method, ex.getMessage());
throw ex;
}
}
}

// 3. 被拦截的 Service
@Service
public class UserService {
public String greet(String name) {
return "Hello, " + name;
}
}

// 4. 调用 —— 输出会看到 BEFORE / AFTER 日志
userService.greet("Alice");
```

### 验证 2：证明 Spring Boot 2+ 默认走 CGLIB

```
@SpringBootApplication
public class DemoApp {
public static void main(String[] args) {
ConfigurableApplicationContext ctx = SpringApplication.run(DemoApp.class, args);
UserService bean = ctx.getBean(UserService.class);

System.out.println("Class = " + bean.getClass().getName());
// 输出：Class = com.example.service.UserService$$SpringCGLIB$$0
//      ↑ 含 "SpringCGLIB" 说明是 CGLIB 代理
//      ↑ 如果是 JDK 代理会输出 com.sun.proxy.$Proxy123

System.out.println("isCglib = " + AopUtils.isCglibProxy(bean));   // true
System.out.println("isJdk   = " + AopUtils.isJdkDynamicProxy(bean)); // false
}
}

// 加上 spring.aop.proxy-target-class=false 后
// UserService 若实现了接口 → 会切换成 JDK 代理，Class = com.sun.proxy.$ProxyXX
```

### 验证 3：自调用导致 `@Transactional` 失效

```
@Service
@Slf4j
public class OrderService {

@Autowired private OrderMapper orderMapper;
@Autowired private OrderService self;   // ← 自注入拿代理

public void createOrderWrong(Order o) {
orderMapper.insert(o);
this.updateStatus(o);          // ← this 是原对象，事务不生效！
}

public void createOrderRight(Order o) {
orderMapper.insert(o);
self.updateStatus(o);          // ← 通过 self（代理）调用，事务生效
}

@Transactional
public void updateStatus(Order o) {
orderMapper.updateStatus(o.getId(), "PAID");
throw new RuntimeException("模拟失败");
// createOrderWrong 走这里：updateStatus 的 update 已提交，不会回滚 ← BUG
// createOrderRight 走这里：updateStatus 内的 update 回滚 ← 正常
}
}
```

### 验证 4：`@Order` 控制多切面顺序

```
@Aspect @Component @Order(1) @Slf4j
public class OuterAspect {
@Around("execution(* com.example.service.*.*(..))")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
log.info("Outer IN");
Object r = pjp.proceed();
log.info("Outer OUT");
return r;
}
}

@Aspect @Component @Order(2) @Slf4j
public class InnerAspect {
@Around("execution(* com.example.service.*.*(..))")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
log.info("Inner IN");
Object r = pjp.proceed();
log.info("Inner OUT");
return r;
}
}

// 输出：
// Outer IN
// Inner IN
//   ...target method...
// Inner OUT
// Outer OUT
// —— 小 order 值先进后出，像洋葱圈
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 Spring AOP 何时用 JDK 代理何时用 CGLIB？Spring Boot 2 之后的默认策略是什么？</summary>

Spring Framework 默认按有无接口自动选：有接口 → JDK，无接口 → CGLIB。Spring Boot 2.0+ 默认 `spring.aop.proxy-target-class=true`，**一律用 CGLIB**。原因是避免混用时按具体类注入拿不到 Bean。

</details>

<details>

<summary>Q2 写一个 Pointcut 匹配所有带 `@Transactional` 且返回值为 `void` 的方法。</summary>

`@Pointcut("@annotation(org.springframework.transaction.annotation.Transactional) && execution(void *..*(..))")`。用 `&&` 组合 `@annotation` 和 `execution`。

</details>

<details>

<summary>Q3 `@Transactional` 自调用失效的根本原因？给出至少两种解法。</summary>

根本原因：`this.methodA()` 里 `this` 是原始对象不是代理对象，绕过了 `TransactionInterceptor`。解法：① 拆到不同 Bean 通过 `@Autowired` 调用；② 自注入 `@Autowired private XxxService self;`；③ `((XxxService) AopContext.currentProxy()).methodA()`（需开启 `exposeProxy=true`）。

</details>

<details>

<summary>Q4 单个切面里 `@Around`、`@Before`、`@After`、`@AfterReturning` 的执行顺序？</summary>

@Around 前半 → @Before → 目标方法 → @AfterReturning（正常返回时） → @After → @Around 后半。可以简单记忆：Around 是最外层包裹，Before 在目标前，AfterReturning/AfterThrowing 是结果分支，After 是 finally。

</details>

<details>

<summary>Q5 AOP 底层是如何把普通 Bean 替换成代理 Bean 的？在 Bean 生命周期哪个阶段？</summary>

通过 `AbstractAutoProxyCreator`（一个 `BeanPostProcessor`），在 Bean 生命周期的 `postProcessAfterInitialization` 阶段（初始化*之后*）介入。它遍历所有 `Advisor` 检查当前 Bean 是否有方法匹配 Pointcut，匹配则用 `ProxyFactory` 生成代理对象并**返回代理替换原 Bean**。容器里从此存的都是代理。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源（AOP 部分）

- Spring Framework Reference · AOP —— 官方文档，最权威的 Pointcut 语法说明

- Spring Framework Reference · AOP API —— `ProxyFactory`、`Advisor`、`BeanPostProcessor` 底层

#### 🔗 关联课件

- （上一课：概念、通知类型、应用场景）

- （下一课：`@Transactional` 的传播行为和失效场景）

- （本课代理机制的底层深挖）

- （`@Async` 也是 AOP 实现的）

#### 🧭 下一课预告

Lesson 0063：**Spring 事务传播机制** —— 7 种 `Propagation`、事务失效的 8 大场景（自调用只是其一）、`rollbackFor` 为什么必须显式写。

💬 有任何疑问 —— 「AopContext 那种解法生产为什么不推荐？」「三级缓存和 AOP 的关系再讲一遍？」「面试真被问过 Pointcut 匹配算法怎么优化，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


