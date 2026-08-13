> Lesson 0060 · 阶段八 · Spring · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 7 个追问

# 0060 · Spring 概览 & Spring 全家桶 & 面试题总结

欢迎来到**阶段八 · Spring** —— 这是国内 Java 后端面试*命中率最高*的一块内容，也是这门 66 节课的最后一个阶段。前七个阶段我们从 JVM、集合、并发、MySQL、Redis 一路啃过来，接下来 6 节课要把 Spring 生态里最容易被追问的点全部收进来。

这一课是**开篇课**，主打*全景视野*：先搞清 **Spring Framework / Spring Boot / Spring Cloud** 三者的定位差异，再把 Spring Framework 的模块地图、核心注解、Spring MVC 请求处理流程串起来 —— 后面 、、 各自深挖单点，而这一课负责先把地图铺开。

本课主源：。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Spring 和 Spring Boot 有什么本质区别？</summary>

Spring Boot **不是**一个新框架，而是 Spring Framework 之上的*约定优于配置*脚手架 —— 靠 `starter` 依赖 + 自动装配 + 内嵌 Tomcat，把 Spring 应用「零 XML、一行 `main`」跑起来。本质上 Spring Boot = Spring + 一堆默认配置 + `java -jar` 部署。见场景 4。

</details>

<details>

<summary>Q0.2 Spring 常用的注解你能一口气说出多少个？至少要覆盖哪些类别？</summary>

至少要能分四类背出来：**Bean 定义**（`@Component`/`@Service`/`@Repository`/`@Controller`/`@Configuration`/`@Bean`）、**依赖注入**（`@Autowired`/`@Resource`/`@Qualifier`/`@Value`）、**Spring MVC**（`@RestController`/`@RequestMapping`/`@GetMapping`/`@PostMapping`/`@RequestBody`/`@PathVariable`/`@RequestParam`）、**Spring Boot 入口**（`@SpringBootApplication`）。见场景 7。

</details>

## 面试场景 1：Spring 是什么？为什么这么流行？

🎤 面试官

你能一分钟介绍一下 Spring 是什么、为什么这么多年一直是 Java 后端的事实标准吗？

🧑‍💻 你

Spring 是一个**轻量级 Java 企业级开发框架**，2003 年 Rod Johnson 为了对抗当时臃肿的 EJB 而写。它的核心是三件事：

- **IoC 容器**：把对象的创建、依赖、生命周期交给容器 —— 业务代码只管声明「我需要什么」，不用 `new`。

- **AOP**：把日志、事务、权限、监控这些*横切关注点*从业务代码抽离，做成切面。

- **Bean 管理**：所有被容器托管的对象叫 Bean，Spring 负责实例化、装配、初始化、销毁全流程。

它流行的四个原因：**解耦**（依赖注入让模块可替换）、**可测试**（POJO + mock 就能跑）、**生态丰富**（Spring MVC、Data、Security、Cloud 全家桶）、**无侵入**（业务类不需要继承任何 Spring 基类，只是普通 POJO）。

追问 Spring 为什么被叫作「轻量级」框架？

相对参照物是当年的 **EJB（Enterprise JavaBeans）**那种*重量级*容器 —— EJB 要求业务类继承特定接口、依赖容器才能启动、部署到重型应用服务器（WebLogic/WebSphere）、单元测试极难。Spring 的「轻」体现在三点：**无侵入**（普通 POJO 即可被托管，不需要继承 Spring 类）、**按需引入**（想用哪个模块就依赖哪个 jar，不用把整个容器拉进来）、**可脱离 Spring 运行**（业务代码本身就能单测，不必启动容器）。

## 面试场景 2：Spring 全家桶（Spring 家族三大件）

🎤 面试官

说到 Spring 你能想到哪些项目？Spring Framework、Spring Boot、Spring Cloud 各自是干什么的？

🧑‍💻 你

Spring 家族项目非常多（Spring Data、Spring Security、Spring Batch……），但面试里必须记住的是**三大件**：

- **Spring Framework**：最*底层*的核心框架 —— IoC 容器、AOP、事务管理、Spring MVC、JDBC/ORM 抽象、Testing 等都在这里。*其他所有 Spring 项目都建立在它之上*。

- **Spring Boot**：Spring Framework 之上的*脚手架*。核心卖点是**约定优于配置** + **`spring-boot-starter-*` 一站式依赖** + **自动装配（AutoConfiguration）** + **内嵌 Tomcat/Jetty**。目的是让「新建一个 Spring Web 项目」从半天缩短到 5 分钟。

- **Spring Cloud**：*微服务*解决方案的集合。包括注册中心（Eureka/Nacos）、服务调用（Feign/OpenFeign）、限流熔断（Hystrix/Sentinel）、网关（Gateway）、配置中心（Config/Nacos Config）、链路追踪（Sleuth）等。它自己不发明轮子，而是把这些组件整合到 Spring Boot 生态里 —— 每个组件都是一个 starter。

一句话总结三者关系：**Spring Boot 是 Spring 的封装，Spring Cloud 是 Spring Boot 的组合**。

陷阱 别把「Spring Boot 替代 Spring Framework」当答案。Spring Boot *本质上就是 Spring*，它没有重写 IoC 容器，只是**把默认配置和 starter 依赖打包好**。用 Spring Boot 写的应用，运行时跑的还是 Spring Framework 的 `ApplicationContext`。

## 面试场景 3：Spring Framework 有哪些核心模块？

🧑‍💻 你

Spring Framework 按功能分成五大模块群，官方图长这样：

```
┌─────────────────────────────────────────────────────────────┐
│                        Spring Framework                     │
├─────────────────────────────────────────────────────────────┤
│  Data Access / Integration        │       Web              │
│  ┌──────┬──────┬──────┬─────┐    │  ┌──────┬──────────┐   │
│  │ JDBC │ ORM  │ OXM  │ JMS │    │  │ MVC  │ WebFlux  │   │
│  ├──────┴──────┴──────┴─────┤    │  ├──────┼──────────┤   │
│  │      Transactions        │    │  │ Web  │WebSocket │   │
│  └──────────────────────────┘    │  └──────┴──────────┘   │
├─────────────────────────────────────────────────────────────┤
│                         AOP  │  Aspects  │  Instrument     │
├─────────────────────────────────────────────────────────────┤
│                    Core Container                           │
│         Beans │ Core │ Context │ SpEL                       │
├─────────────────────────────────────────────────────────────┤
│                       Test                                  │
└─────────────────────────────────────────────────────────────┘
```

- **Core Container（核心容器）**：`spring-core`（IoC 基础工具）、`spring-beans`（Bean 定义/装配）、`spring-context`（`ApplicationContext`，最常用的容器接口）、`spring-expression`（SpEL 表达式语言，如 `@Value("#{...}")`）。

- **AOP**：`spring-aop`（基于代理的 AOP）、`spring-aspects`（集成 AspectJ）、`spring-instrument`（JVM Agent 支持）。

- **Data Access / Integration**：`spring-jdbc`（JdbcTemplate）、`spring-tx`（事务抽象）、`spring-orm`（Hibernate/JPA 集成）、`spring-oxm`（Object/XML 映射）、`spring-jms`（消息）。

- **Web**：`spring-web`（通用 Web 工具、`RestTemplate`）、`spring-webmvc`（Servlet 栈 Spring MVC）、`spring-webflux`（Reactive 栈，Spring 5 引入）、`spring-websocket`。

- **Test**：`spring-test`（配合 JUnit 做集成测试，能加载 `ApplicationContext`）。

追问 BeanFactory 和 ApplicationContext 有什么区别？

都是 IoC 容器接口，**ApplicationContext 继承自 BeanFactory**。区别在于：**BeanFactory** 是最底层的容器接口，*懒加载* —— 只有 `getBean()` 时才真正初始化；**ApplicationContext** 是「工程实用版」，除了 BeanFactory 的能力外，还加了：*国际化*（MessageSource）、*事件发布/订阅*（ApplicationEventPublisher）、*资源加载*（ResourceLoader）、*AOP 支持*，并且**启动时预初始化所有 singleton Bean**（快速暴露配置错误）。实际项目 99% 用 ApplicationContext（`ClassPathXmlApplicationContext`、`AnnotationConfigApplicationContext`、Spring Boot 里的 `AnnotationConfigServletWebServerApplicationContext`）。

## 面试场景 4：Spring 和 Spring Boot 的区别（★经典）

🎤 面试官

你说 Spring Boot 是 Spring 的封装，具体简化了哪些东西？请从*配置、部署、依赖管理*三个维度对比一下。

维度Spring FrameworkSpring Boot

配置
大量 XML 或 `@Configuration` 类，手动配 `DispatcherServlet`、`DataSource`、事务管理器等
**约定优于配置**，主要用 `application.yml`；自动装配（`@EnableAutoConfiguration`）根据 classpath 自动配好绝大多数组件

依赖管理
手动挑版本、拼版本，容易冲突（如 Spring 5.x 配哪个版本的 Jackson？）
`spring-boot-starter-*` 一站式依赖：想做 Web 就引 `spring-boot-starter-web`，一个 starter 拽进来所有相关依赖*且版本已协调*

部署方式
打成 `war`，部署到外部 Tomcat/Jetty
内嵌 Tomcat/Jetty/Undertow，打成 *fat jar*，直接 `java -jar app.jar`

启动入口
`web.xml` 或 `WebApplicationInitializer`
一个带 `@SpringBootApplication` 的 `main` 方法

监控/运维
需要自己集成 JMX、健康检查
内置 **Actuator**，开箱即用的 `/actuator/health`、`/actuator/metrics` 等端点

本质
底层框架，提供所有核心能力
建立在 Spring Framework 之上的*脚手架*，运行时依然是 Spring 容器

追问 Spring Boot 到底加了什么魔法？拆开看是三件事：

**1）Starter 依赖**：`spring-boot-starter-web` 就是一个「元 pom」，里面 `<dependency>` 列出了 Spring MVC、Jackson、Tomcat、Validation 等一整套 —— 版本已由 Spring Boot 统一锁定，避免冲突。**2）自动装配**：`@EnableAutoConfiguration` 触发扫描 `META-INF/spring.factories`（Spring Boot 2.x）或 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（Spring Boot 3.x），把符合条件（`@ConditionalOnClass`、`@ConditionalOnMissingBean`）的自动配置类加载进容器。**3）内嵌容器**：直接把 Tomcat 作为一个依赖引入，通过 `ServletWebServerFactory` 编程式启动，不再需要外部 Servlet 容器。深挖看 。

## 面试场景 5：IoC 是什么？（下一课深挖预告）

🎤 面试官

你反复提到 IoC，那 IoC 到底是什么？和 DI 是同一个东西吗？

🧑‍💻 你

**IoC（Inversion of Control，控制反转）**是一种*设计思想*，不是具体技术。传统写法里，对象自己去 `new` 依赖：

```
// 传统方式：UserService 主动 new 依赖
public class UserService {
private UserDao userDao = new UserDaoImpl();  // ← 硬编码
}
```

控制反转后，对象**不再自己创建依赖**，而是*被动接收*容器注入的依赖：

```
// IoC 方式：UserService 只声明「我要一个 UserDao」，谁给我不管
@Service
public class UserService {
@Autowired
private UserDao userDao;  // ← 容器帮我塞进来
}
```

控制权从「对象自己」**反转**到了「容器」，所以叫控制反转。

**DI（Dependency Injection，依赖注入）**是 IoC *最主要的实现技术*。可以理解为：IoC 是*思想*，DI 是*手段*。Spring 里 IoC 容器通过 DI 把依赖装配到 Bean 里，三种注入方式（构造器/Setter/字段）在  详解。

追问 IoC 带来的最大好处是什么？

**解耦**。业务类只依赖*接口*，具体实现由容器注入 —— 想换 `UserDaoImpl` 为 `UserDaoMockImpl`（测试用）或 `UserDaoRedisImpl`（换存储），改配置即可，业务代码零改动。附带好处还有：*可测试*（mock 依赖轻而易举）、*生命周期集中管理*（容器统一负责创建、初始化、销毁）、*横切能力可插拔*（在容器层加 AOP 就能给所有 Bean 织入事务/日志）。

## 面试场景 6：AOP 是什么？（0061 / 0062 深挖预告）

🧑‍💻 你

**AOP（Aspect-Oriented Programming，面向切面编程）**解决的问题是：*横切关注点*（cross-cutting concerns）—— 日志、事务、权限校验、性能监控、缓存 —— 这些逻辑**散布在几乎每个方法里**，如果直接写在业务代码里会有两个问题：

1. **代码重复**：每个 Service 方法开头写 `logger.info(...)`，结尾写 `tx.commit()`，改一次要改无数处。

2. **业务与非业务混杂**：一个方法 30 行有 25 行是日志和事务，真正的业务逻辑只有 5 行，可读性极差。

AOP 的做法是：把这些横切逻辑抽成**切面（Aspect）**，通过*切点（Pointcut）*声明「织入到哪些方法」，通过*通知（Advice）*声明「织入什么逻辑」。Spring AOP 基于**动态代理**实现 —— 目标类有接口就用 *JDK 动态代理*，没接口就用 *CGLIB* 生成子类代理。

```
@Aspect
@Component
public class LogAspect {
@Around("execution(* com.example.service.*.*(..))")
public Object logAround(ProceedingJoinPoint pjp) throws Throwable {
long start = System.currentTimeMillis();
Object result = pjp.proceed();       // 执行原方法
long cost = System.currentTimeMillis() - start;
System.out.println(pjp.getSignature() + " cost " + cost + "ms");
return result;
}
}
```

就这样，一个切面把「所有 Service 方法的耗时统计」全部搞定，业务代码完全不动。

## 面试场景 7：Spring 常用注解全景（★背下来）

🎤 面试官

Spring 常用的注解你能分类说一下吗？至少 15 个。

### 7.1 Bean 定义类

注解作用位置说明

`@Component`类通用的 Bean 声明，让类被 `@ComponentScan` 扫描到并注册进容器
`@Service`类（业务层）本质是 `@Component`，仅语义化标记业务层
`@Repository`类（DAO 层）本质是 `@Component`，额外把持久层异常翻译成 Spring 的 `DataAccessException`
`@Controller`类（Web 层）本质是 `@Component`，被 Spring MVC 扫描为控制器
`@Configuration`类标记这是一个 Java 配置类，等价于一份 `<beans>` XML
`@Bean`方法（配置类内）方法返回值注册为 Bean；主要用于集成第三方类（无法加 `@Component`）

### 7.2 依赖注入类

注解提供方默认匹配策略

`@Autowired`Spring先按**类型**（byType），多个候选时再按**名称**（byName）
`@Resource`JSR-250（JDK 标准）先按**名称**（byName），找不到再按**类型**
`@Qualifier("beanName")`Spring配合 `@Autowired`，显式指定要注入哪个 Bean
`@Primary`Spring多候选时标记*首选* Bean
`@Value("${key}")`Spring注入 `application.yml` / 环境变量 / SpEL 表达式的值

### 7.3 Spring MVC 类

注解说明

`@RestController`= `@Controller` + `@ResponseBody`；类内所有方法返回值直接序列化为 JSON
`@RequestMapping("/path")`通用请求映射，可指定 `method = RequestMethod.GET` 等
`@GetMapping` / `@PostMapping` / `@PutMapping` / `@DeleteMapping``@RequestMapping` 的 HTTP 方法快捷版
`@RequestBody`把 HTTP 请求体（JSON）反序列化为 Java 对象
`@ResponseBody`把 Java 对象序列化为响应体（JSON），`@RestController` 已自动加
`@PathVariable`取 URL 路径变量：`/user/{id}` 中的 `id`
`@RequestParam`取 query string 或 form 参数：`?name=alice` 中的 `name`
`@RequestHeader`取请求头

### 7.4 事务 & AOP 类

注解说明

`@Transactional`声明式事务，可设置传播行为、隔离级别、回滚异常等（详见 ）
`@Aspect`声明这是一个切面类
`@Pointcut("execution(...)")`声明切点表达式
`@Before` / `@After` / `@AfterReturning` / `@AfterThrowing`前置/后置/正常返回后/异常时的通知
`@Around`环绕通知，最强大，可以决定是否/何时执行原方法

### 7.5 Spring Boot 入口

🧑‍💻 你

`@SpringBootApplication` 是 Spring Boot 应用的**入口标记**，它是三个注解的组合：

- `@Configuration`：标记这是一个配置类

- `@EnableAutoConfiguration`：开启自动装配（Spring Boot 的灵魂）

- `@ComponentScan`：自动扫描当前包及子包下的 `@Component`/`@Service`/`@Repository`/`@Controller`

追问 @Service 和 @Component 有区别吗？

本质**没有**区别 —— `@Service`、`@Repository`、`@Controller` 都是 `@Component` 的*特化*（用 `@Component` 元注解标注），运行时都会被 `@ComponentScan` 注册进容器。但语义上：`@Service` 标记业务层、`@Repository` 标记 DAO 层（且能触发*持久层异常翻译*）、`@Controller` 标记 Web 层（会被 Spring MVC 识别为控制器）。**分层清晰** + **方便 AOP 按注解切**（如 `@Pointcut("@within(org.springframework.stereotype.Service)")`）就是它们的额外价值。

## 面试场景 8：@Autowired vs @Resource（★经典）

🎤 面试官

项目里注入依赖有的人用 `@Autowired`，有的人用 `@Resource`，这两个有什么区别？你更推荐哪个？

维度`@Autowired``@Resource`

提供方Spring（`org.springframework.beans.factory.annotation`）JSR-250 / JDK 标准（`jakarta.annotation` 或旧 `javax.annotation`）
默认匹配按**类型**（byType）按**名称**（byName）
多候选时再按*字段名/参数名*匹配；仍模糊则报错，需要 `@Qualifier` 或 `@Primary`先 `name` 属性 → 字段名 → 类型；仍模糊则报错
找不到时默认**抛异常**，可用 `required = false` 允许为 null抛异常
可作用位置字段、setter、构造器、方法参数字段、setter
可移植性绑定 SpringJDK 标准，可脱离 Spring（如 Guice、CDI 也支持）

🧑‍💻 你

实际选择：

- 需要按名字精确匹配 → `@Resource(name="fooService")` 一个注解搞定，比 `@Autowired` + `@Qualifier` 更短。

- 纯 Spring 项目、想用构造器注入 → `@Autowired`（`@Resource` 不支持构造器）。

- Spring 官方最推荐：**构造器注入**，且从 Spring 4.3 起*唯一构造器可省略 `@Autowired`*。

追问 Spring 的循环依赖是怎么解决的？

Spring 用**三级缓存**解决 *singleton scope + 字段/Setter 注入*的循环依赖：**一级缓存 `singletonObjects`** 存已完全初始化的 Bean；**二级缓存 `earlySingletonObjects`** 存已实例化但未初始化的*提前暴露对象*；**三级缓存 `singletonFactories`** 存 `ObjectFactory`（用于生成代理对象，如 AOP 代理）。当 A 依赖 B、B 依赖 A：创建 A → 实例化后把 A 的 `ObjectFactory` 放三级缓存 → 装配 A 时发现要 B → 创建 B → B 装配时要 A → 从三级缓存取出 A 的 `ObjectFactory`、生成早期 A（可能是代理）放二级缓存、B 拿到 A 完成初始化 → 回到 A 拿到已就绪的 B 完成初始化 → A 放入一级缓存。**但构造器循环依赖和 prototype Bean 无法解决**（实例化都还没完成就要依赖对方）。下一课  深挖。

## 面试场景 9：Spring MVC 请求处理流程（★经典）

🎤 面试官

一个 HTTP 请求从进来到返回，在 Spring MVC 里经过了哪些组件？请把完整流程说一下。

🧑‍💻 你

Spring MVC 的核心是**前端控制器 `DispatcherServlet`**，所有请求先进它这里，再分发给合适的组件。完整流程：

```
Client HTTP 请求
│
▼
┌─────────────────────────────────────────┐
│    DispatcherServlet（前端控制器）      │  ← 唯一入口 Servlet
└─────────────────────────────────────────┘
│  1. 询问：这个 URL 归谁处理？
▼
┌─────────────────────────────────────────┐
│    HandlerMapping                       │  ← 根据 URL 找到对应 Controller 方法
│    （返回 HandlerExecutionChain：       │     + 拦截器链
│     Handler + Interceptor 链）          │
└─────────────────────────────────────────┘
│  2. 拿到 Handler，交给 Adapter 执行
▼
┌─────────────────────────────────────────┐
│    HandlerAdapter                       │  ← 适配不同类型的 Handler
│    （RequestMappingHandlerAdapter 处理  │     统一入口，解决 Controller 多样性
│     @RequestMapping 方法）              │
└─────────────────────────────────────────┘
│  3. 反射调用 Controller 方法
▼
┌─────────────────────────────────────────┐
│    Controller（你写的业务方法）         │  ← 处理业务，返回 ModelAndView / 对象
└─────────────────────────────────────────┘
│  4. 拿到 ModelAndView
▼
┌─────────────────────────────────────────┐
│    ViewResolver                         │  ← 把逻辑视图名（"index"）
│                                         │     解析成 View 实现
└─────────────────────────────────────────┘
│  5. View 渲染
▼
┌─────────────────────────────────────────┐
│    View（Thymeleaf / JSP / JSON 等）    │  ← 生成最终响应内容
└─────────────────────────────────────────┘
│
▼
Client HTTP 响应
```

关键点：

- **DispatcherServlet**：所有请求的中央调度员，本身是一个 `Servlet`，注册在 Servlet 容器（Tomcat）里。

- **HandlerMapping**：URL → Handler 的映射表。有多个实现，最常用 `RequestMappingHandlerMapping`（处理 `@RequestMapping`）。

- **HandlerAdapter**：适配器模式，让 `DispatcherServlet` 用统一接口调用各种 Handler（`@Controller`、`HttpRequestHandler`、`Servlet`）。

- **ViewResolver**：视图解析器。前后端分离时，用 `@RestController` 直接返回 JSON，就*跳过* ViewResolver（通过 `HttpMessageConverter` 序列化）。

追问 @RestController 和 @Controller 有什么区别？

`@RestController` = `@Controller` + `@ResponseBody`。区别在于：**@Controller** 方法返回值默认走 **ViewResolver**，把字符串当作*视图名*去解析（用于返回 HTML 页面，如 JSP/Thymeleaf 模板）；**@RestController** 方法返回值默认走 **HttpMessageConverter**（常用 Jackson），把对象*序列化为 JSON* 写进响应体。前后端分离项目里 99% 用 `@RestController`。想让 `@Controller` 的某个方法也直接返回 JSON？在方法上加 `@ResponseBody` 即可 —— 这就是 `@RestController` 帮你做的事。

## 面试场景 10：Spring 5 / Spring 6 的重要新特性

🎤 面试官

Spring 5 和 Spring 6 有哪些值得说的新特性？

### Spring 5（2017）

🧑‍💻 你

- **响应式编程 WebFlux**：新增 `spring-webflux` 模块，基于 *Project Reactor*（`Mono`/`Flux`），提供非阻塞式 Web 栈。适合*高并发 + IO 密集*场景（如网关、SSE）。

- **Kotlin 一等公民支持**：内置 Kotlin 扩展函数、null 安全适配。

- **函数式 Bean 注册**：用 lambda 直接注册 Bean，不需要 `@Bean` 方法。

- **JDK 8 baseline**，全面拥抱 `Optional`、方法引用。

- **@Nullable / @NonNull**：为 API 提供 null-safety 元数据。

### Spring 6（2022）

🧑‍💻 你

- **Java 17 baseline**：不再支持 Java 8/11，最低 Java 17。

- **Jakarta EE 9+ 迁移**：所有 `javax.*` 包全部改为 `jakarta.*`（如 `javax.servlet` → `jakarta.servlet`）。*这是升级 Spring 6 最痛的点*，很多依赖都要换 jakarta 版本。

- **AOT 编译**：正式支持 *Ahead-Of-Time 编译*，配合 **GraalVM Native Image** 打出原生可执行文件 —— 启动毫秒级、内存占用极低，适合 Serverless。

- **HTTP Interface**：类似 Feign 的声明式 HTTP 客户端，写个接口 + `@GetExchange` 就能发请求。

- **Observability（可观测性）**：整合 Micrometer 的 Tracing/Metrics，指标和链路追踪的一等支持。

追问 Spring Boot 3.x 对应哪个 Spring 版本？升级要注意什么？

Spring Boot 3.x 基于 **Spring Framework 6**，同样要求 **Java 17+**，同样把 `javax.*` 换成 `jakarta.*`。升级最容易踩的坑：**1）** Servlet API 变了，用到 `javax.servlet.http.HttpServletRequest` 的所有地方要改成 `jakarta.servlet.http.HttpServletRequest`；**2）** JPA 的 `@Entity` 从 `javax.persistence` → `jakarta.persistence`；**3）** 部分老三方库（如某些老版本的 Redisson、MyBatis-Plus）还没适配 jakarta，需要升级版本；**4）** 想跑 Native Image 要额外配 `reflect-config.json` 声明反射类。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：最小 Spring Boot 应用（体会「约定优于配置」）

```
// build.gradle 只需要一个 starter
dependencies {
implementation 'org.springframework.boot:spring-boot-starter-web'
}

// Application.java —— 整个应用只要这一个类
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication         // = @Configuration + @EnableAutoConfiguration + @ComponentScan
@RestController                // = @Controller + @ResponseBody
public class Application {
public static void main(String[] args) {
SpringApplication.run(Application.class, args);
}

@GetMapping("/hello")
public String hello() {
return "Hello, Spring Boot!";
}
}
```

**运行**：`./gradlew bootRun` → 访问 `http://localhost:8080/hello`。整个过程没有 `web.xml`、没有外部 Tomcat、没有 XML 配置 —— 这就是 Spring Boot 的默认威力。

### 验证 2：Bean 定义 & 依赖注入的三种写法

```
// 1) @Component 类扫描注册
@Service
public class UserService {
// 构造器注入（Spring 官方推荐）—— 从 Spring 4.3 起唯一构造器可省 @Autowired
private final UserDao userDao;
public UserService(UserDao userDao) {
this.userDao = userDao;
}
}

// 2) @Bean 方法注册（用于第三方类）
@Configuration
public class RedisConfig {
@Bean
public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
RedisTemplate<String, Object> t = new RedisTemplate<>();
t.setConnectionFactory(factory);
return t;
}
}

// 3) 字段注入（不推荐，但很常见）
@Service
public class OrderService {
@Autowired          // 按类型
private PaymentService paymentService;

@Resource(name = "cnyRateService")   // 按名称
private RateService rateService;

@Value("${order.timeout:30}")        // 从 application.yml 注入
private int timeoutSeconds;
}
```

### 验证 3：Spring MVC 的常见 Controller 写法

```
@RestController
@RequestMapping("/api/users")
public class UserController {

private final UserService userService;
public UserController(UserService userService) {
this.userService = userService;
}

// GET /api/users/42
@GetMapping("/{id}")
public UserDTO getById(@PathVariable Long id) {
return userService.findById(id);
}

// GET /api/users?name=alice&page=1
@GetMapping
public List<UserDTO> search(
@RequestParam String name,
@RequestParam(defaultValue = "1") int page) {
return userService.search(name, page);
}

// POST /api/users   Body: {"name":"bob","age":20}
@PostMapping
public UserDTO create(@RequestBody CreateUserReq req) {
return userService.create(req);
}
}
```

观察点：`@RestController` 让所有返回值走 Jackson 序列化为 JSON；`@PathVariable` 抓路径变量、`@RequestParam` 抓 query、`@RequestBody` 抓 JSON 请求体 —— 三个「抓参数」注解对应三种最常见的传参方式。

### 验证 4：一个最小 AOP 切面（提前尝一口 0062 的味道）

```
@Aspect
@Component
public class TimingAspect {

// 切点：拦截 com.example.service 下所有类的所有方法
@Pointcut("execution(* com.example.service..*.*(..))")
public void serviceMethods() {}

@Around("serviceMethods()")
public Object measure(ProceedingJoinPoint pjp) throws Throwable {
long start = System.nanoTime();
try {
return pjp.proceed();     // ← 执行原方法
} finally {
long costMs = (System.nanoTime() - start) / 1_000_000;
System.out.printf("[TIMING] %s cost %dms%n",
pjp.getSignature().toShortString(), costMs);
}
}
}
```

只要引入 `spring-boot-starter-aop`，这段切面就会自动为所有 Service 方法织入耗时统计 —— *业务代码完全无感知*。这就是 AOP 的威力。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话解释 Spring Framework、Spring Boot、Spring Cloud 三者的关系。</summary>

Spring Framework 是底层核心框架（IoC/AOP/MVC 等）；Spring Boot 是它之上的*约定优于配置*脚手架（starter + 自动装配 + 内嵌 Tomcat）；Spring Cloud 是基于 Spring Boot 的*微服务*组件集合（注册中心/Feign/网关等）。一句话：**Cloud 建在 Boot 上，Boot 建在 Framework 上**。

</details>

<details>

<summary>Q2 `@SpringBootApplication` 等价于哪三个注解？</summary>

`@Configuration`（本类是 Java 配置类）+ `@EnableAutoConfiguration`（开启自动装配）+ `@ComponentScan`（扫描当前包及子包）。

</details>

<details>

<summary>Q3 `@Autowired` 和 `@Resource` 的默认匹配策略分别是什么？</summary>

`@Autowired`（Spring 提供）默认**按类型**，多候选时再按字段名或用 `@Qualifier`；`@Resource`（JSR-250）默认**按名称**，找不到再按类型。*Name 优先记 `@Resource`*。

</details>

<details>

<summary>Q4 Spring MVC 请求处理流程按顺序说出四个核心组件。</summary>

**DispatcherServlet**（前端控制器，统一入口）→ **HandlerMapping**（URL 找到 Controller 方法）→ **HandlerAdapter**（调用方法，适配不同 Handler 类型）→ Controller 执行返回 ModelAndView → **ViewResolver**（解析视图名到 View）→ View 渲染。前后端分离时用 `@RestController`，直接由 `HttpMessageConverter` 写 JSON，*跳过 ViewResolver*。

</details>

<details>

<summary>Q5 `@RestController` 和 `@Controller` 有什么区别？</summary>

`@RestController` = `@Controller` + `@ResponseBody`。前者所有方法返回值默认**序列化为 JSON 写响应体**（走 `HttpMessageConverter`）；后者返回值默认**当视图名走 ViewResolver** 渲染 HTML。前后端分离用 `@RestController`，服务端渲染用 `@Controller`。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Spring Framework Reference · Overview —— 官方总览

- Spring Boot Reference —— Spring Boot 官方文档

#### 🔗 关联课件

-

-

-

-

#### 🧭 下一课预告

Lesson 0061：**Spring IoC 与 AOP 深挖** —— 三级缓存循环依赖、Bean 生命周期、JDK 动态代理 vs CGLIB、切点表达式语法，一次讲透。

💬 有任何疑问 —— 「注解为什么这么设计？」「面试真被问过 XX 变体，怎么答？」「Spring 6 升级踩过哪些坑？」—— 直接问我。这是阶段八的开篇，接下来 5 节课我们逐个深挖 Spring 的每个核心机制。


