> Lesson 0064 · 阶段八 · Spring · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 5 段可跑代码 · 5 道自测 · 12 处追问 · 3 处陷阱

# 0064 · Spring 常用注解 & MVC 请求流程 & 参数校验

Spring 一整套注解体系号称「注解驱动开发」，注解本身好几十个，面试官一问「**@Service 和 @Component 有什么区别？**」「**@RequestBody 和 @RequestParam 有什么区别？**」你必须*秒答且能说出底层为什么*。这一课把最高频的 **Bean 定义、依赖注入、Spring MVC 映射、参数绑定、参数校验、异常处理、配置绑定、Spring Boot 特有注解**打包成一张地图 —— 同时把面试官最爱追的「**DispatcherServlet 的请求处理完整流程**」拉出来对着讲，让你面试时能连着注解一起串出来。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `@Component` 家族一共有几个？分别语义化到哪一层？</summary>

四个：`@Component`（通用）、`@Service`（业务层）、`@Repository`（DAO 层，会翻译数据访问异常）、`@Controller`（Web 层）。后三个都是 `@Component` 的*元注解派生*，功能上等价，语义上分层。第 1 题细讲。

</details>

<details>

<summary>Q0.2 `@RequestBody` 和 `@RequestParam` 拿的是请求的哪一部分？</summary>

`@RequestParam` 拿 URL 查询参数（`?id=1`）或表单字段（`application/x-www-form-urlencoded`）；`@RequestBody` 拿 HTTP *请求体*，通常是 JSON，用 Jackson/Gson 反序列化成对象。一个方法只能有一个 `@RequestBody`，但可以有多个 `@RequestParam`。第 4 题细讲。

</details>

## 面试场景 1：Bean 定义注解 —— @Component / @Service / @Repository / @Controller / @Configuration / @Bean

🎤 面试官

`@Component`、`@Service`、`@Repository`、`@Controller`，它们有什么区别？在什么场景下用哪个？`@Configuration` + `@Bean` 又是干嘛的？

🧑‍💻 你

先分两组：

- **类扫描组**：`@Component`、`@Service`、`@Repository`、`@Controller`。加在*类*上，被 `@ComponentScan` 扫描到后注册成 Bean。

- **手动装配组**：`@Configuration` + `@Bean`。`@Bean` 加在*方法*上，方法返回值就是 Bean —— 适合*无法改源码的第三方类*。

四个类扫描注解的关系：

```
@Component  ← 元注解，通用组件
├── @Service      ← 语义化：业务层（Service Layer）
├── @Repository   ← 语义化：DAO 层 + 数据访问异常翻译（PersistenceExceptionTranslator）
└── @Controller   ← 语义化：Web 控制层，通常配合 @RequestMapping
```

**功能上四个几乎等价**（都是注册成 Bean），差异有三处：

1. **语义**：分层清晰，看到 `@Service` 就知道是业务代码，看到 `@Repository` 就知道是数据访问。

2. **`@Repository` 独有能力**：会被 `PersistenceExceptionTranslationPostProcessor` 处理，把原生数据库异常（如 JDBC `SQLException`、Hibernate `HibernateException`）翻译成 Spring 的 `DataAccessException` 体系 —— 上层不用感知底层持久化技术。

3. **AOP 切点表达式友好**：`@Pointcut("@within(org.springframework.stereotype.Service)")` 可以精确切到业务层。

追问 `@Component` 和 `@Bean` 到底有什么区别？为什么要有两套？

**作用位置和使用场景不同**：`@Component` 加在*类*上，让 Spring 主动扫描注册，适合*自己写的类*；`@Bean` 加在 `@Configuration` 类的*方法*上，方法返回值成为 Bean —— 适合*第三方库的类*（比如 `RedisTemplate`、`RestTemplate`、`DataSource`），你没法给别人的源码加注解，只能在自己的 `@Configuration` 里写方法手动 new 出来。`@Bean` 还有一个优势：方法体里可以写复杂的构造逻辑（读配置、条件判断、装配依赖），比构造函数灵活。

追问 `@Configuration` 类里的 `@Bean` 方法互相调用，会不会重复创建 Bean？

不会。`@Configuration` 类会被 **CGLIB 代理**，方法调用会被拦截 —— 第一次调用真正 `new`，之后每次都从 IoC 容器返回同一个单例。所以 `@Bean` 方法之间可以放心互调。如果换成 `@Component` 类里写 `@Bean`（Lite 模式），没有 CGLIB 代理，方法互调就会*各自 new 出多个实例*。所以配置类务必用 `@Configuration`。

追问 `@Import` 是干嘛的？和 `@ComponentScan` 有什么区别？

`@ComponentScan` 是*包扫描*，只能扫指定包路径下带 `@Component` 派生注解的类；`@Import` 是*显式导入*，直接把某个类/配置注册进容器，不受包路径限制。三种典型用法：`@Import(SomeConfig.class)` 导入其它 `@Configuration`；`@Import(SomeBean.class)` 直接把某个普通类注册成 Bean；`@Import(ImportSelector.class)` 动态返回要导入的类名数组 —— Spring Boot 的 `@EnableAutoConfiguration` 就是靠 `AutoConfigurationImportSelector` 加载 `META-INF/spring.factories` 里的自动配置类。

## 面试场景 2：依赖注入注解 —— @Autowired / @Resource / @Value / @Qualifier / @Primary

🎤 面试官

`@Autowired` 和 `@Resource` 有什么区别？如果一个接口有两个实现类，怎么让 Spring 知道注入哪个？

🧑‍💻 你

对比表：

维度`@Autowired``@Resource`

来源Spring 提供（`org.springframework`）JSR-250（JDK 标准，`javax.annotation` / `jakarta.annotation`）
默认注入方式**按类型**（byType）**按名称**（byName），找不到再按类型
多候选处理配合 `@Qualifier("beanName")` 或 `@Primary`直接 `@Resource(name="beanName")`
是否必需`required=true`（默认，找不到抛异常）不支持 required 属性
作用位置构造器、Setter、字段、方法参数**只支持字段和 Setter**，不支持构造器
解耦度耦合 Spring标准注解，理论上换容器不用改

🧑‍💻 你（续）

多实现类的场景：

```
public interface PaymentService { }

@Service("wechatPay")
public class WechatPayService implements PaymentService { }

@Service("alipay")
public class AlipayService implements PaymentService { }

@Service
public class OrderService {

// 方案 1：@Autowired + @Qualifier
@Autowired
@Qualifier("wechatPay")
private PaymentService payment;

// 方案 2：@Resource 按名称
@Resource(name = "alipay")
private PaymentService payment2;

// 方案 3：字段名匹配 Bean 名（不推荐，重构改名就坏）
@Autowired
private PaymentService wechatPay;
}
```

还有一种是在其中一个 Bean 上加 `@Primary`，让 Spring 在无 `@Qualifier` 时优先选它 —— 适合*有一个「默认实现」的场景*。

追问 字段注入、Setter 注入、构造器注入，Spring 官方推荐哪种？为什么？

**构造器注入**。三大理由：

1. **依赖不可变**：字段可以声明 `final`，线程安全。

2. **依赖必须**：构造时就必须传，避免 NPE。

3. **不依赖 Spring**：不用反射就能 `new Foo(bar)` 单元测试，纯 POJO。

从 Spring 4.3 开始，*类只有一个构造函数时可以省略 `@Autowired`*。Lombok 的 `@RequiredArgsConstructor` 就是配合构造器注入的最佳搭档。字段注入的最大问题是*循环依赖不会立刻爆*，会隐藏很多设计问题，还有*单元测试必须靠反射注入或 Spring 容器*。

追问 `@Value` 支持哪些语法？`${xxx}` 和 `#{xxx}` 有什么区别？

`${xxx}` 是 **属性占位符**（PropertyPlaceholder），从 `application.properties`/`application.yml`/环境变量取值：`@Value("${server.port:8080}")`（`:8080` 是默认值）。`#{xxx}` 是 **SpEL 表达式**（Spring Expression Language），可以做运算、调用 Bean 方法：`@Value("#{T(Math).PI}")`、`@Value("#{userService.count()}")`。日常用得最多的是 `${}`，SpEL 偶尔用于运算或 Bean 引用。

陷阱 `@Autowired` 不能直接注入到 `static` 字段。Spring 容器只管实例化 Bean 的成员字段，静态字段不属于任何实例。要给静态字段赋值，得用 *Setter 注入* —— `@Autowired` 加在非静态 Setter 上，在 Setter 里把参数赋给静态字段（可以，但不推荐；更推荐把这类工具类改成单例 Bean，别用 static）。

## 面试场景 3：Spring MVC 请求映射注解 —— @RequestMapping 家族 & @RestController

🎤 面试官

`@RestController` 和 `@Controller` 有什么区别？`@GetMapping` 相比 `@RequestMapping` 有什么优势？

🧑‍💻 你

**`@RestController` = `@Controller` + `@ResponseBody`**。二者的分工：

- `@Controller`：传统 MVC，方法返回值是*视图名*（如 `"user/list"`），交给 `ViewResolver` 解析成 JSP/Thymeleaf/FreeMarker 页面。

- `@RestController`：REST API 场景，方法返回值直接*序列化为 JSON*（通过 `HttpMessageConverter`，通常是 Jackson）写回响应体。

如果你写 REST API 却用了 `@Controller` 而忘了 `@ResponseBody`，Spring 会把你返回的字符串当成视图名找视图，通常报 404。

方法级注解简化对比：

```
// 老写法
@RequestMapping(value = "/user/{id}", method = RequestMethod.GET)

// 新写法（Spring 4.3+）
@GetMapping("/user/{id}")
```

`@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`、`@PatchMapping` 都是 `@RequestMapping` 的组合注解，语义更清晰、代码更短。类上通常用 `@RequestMapping("/api/users")` 定义前缀，方法上用 HTTP 方法特化的注解。

追问 `@RequestMapping` 除了 path 和 method，还能匹配什么？

还能按 **请求头**（`headers = "X-API-Version=2"`）、**Content-Type**（`consumes = "application/json"`，只接收 JSON 请求）、**Accept**（`produces = "application/json;charset=UTF-8"`，只对能接受 JSON 的客户端响应）、**查询参数**（`params = "type=vip"`）来匹配。`consumes` 和 `produces` 在 API 版本控制和多格式响应时很有用。

## 面试场景 4：参数绑定注解 —— @RequestParam / @PathVariable / @RequestBody / @RequestHeader / @CookieValue / @ModelAttribute

🎤 面试官

把参数绑定注解都过一遍：分别从请求的哪部分拿数据？

注解来源典型示例关键点

`@RequestParam`
URL 查询参数 `?a=1` 或表单 `application/x-www-form-urlencoded`
`@RequestParam(value="page", defaultValue="1") int page`
可指定 `required`、`defaultValue`

`@PathVariable`
URL 路径段 `/user/{id}`
`@PathVariable("id") Long id`
RESTful 风格必备

`@RequestBody`
HTTP 请求体（通常 JSON）
`@RequestBody @Valid UserDTO dto`
一个方法只能有一个；不能配 GET

`@RequestHeader`
请求头
`@RequestHeader("Authorization") String token`
取鉴权、UA、Accept-Language

`@CookieValue`
Cookie
`@CookieValue("SESSIONID") String sid`
取单个 Cookie

`@ModelAttribute`
表单字段整体绑定到对象
`@ModelAttribute UserForm form`
传统表单提交场景

🧑‍💻 你

核心记忆口诀：**「Param 拿 query，Path 拿路径，Body 拿 JSON，Header 拿头，Cookie 拿 Cookie，ModelAttribute 拿表单」**。前端 Axios 里 `params` 对应 `@RequestParam`，`data` 对应 `@RequestBody`，是最容易搞混的一对。

追问 `@RequestBody` 能不能配合 GET 请求？

**技术上可以，但不规范**。Spring 不会阻止你在 GET 方法上加 `@RequestBody`，但 HTTP 语义规定 GET 是*安全幂等且没有请求体*的，Swagger/OpenAPI、浏览器、CDN、代理服务器、curl 的默认行为都不支持 GET 带 body。真实业务里遇到「GET 参数太多想放 body」的场景，正确做法是*改成 POST*（比如复杂查询用 POST /search），而不是硬塞 body 到 GET。

追问 为什么一个方法只能有一个 `@RequestBody`？

因为 HTTP 请求*只有一个请求体*。`@RequestBody` 是把整个请求体反序列化为对象，第二个 `@RequestBody` 就没数据可读了。如果确实要传多个对象，把它们包装成一个大 DTO：`class OrderCreateRequest { User user; List<Item> items; }`。

追问 `@RequestParam` 什么时候可以省略？

Spring MVC 有一个默认规则：*方法参数是简单类型（String、包装类、基本类型）且名字和查询参数名一致时，可以省略 `@RequestParam`*。但强烈建议**不要省略** —— 一旦你想指定 `required=false` 或 `defaultValue`，或者编译时优化把参数名擦除（没加 `-parameters` 编译选项），就会绑定失败。加上更明确、也更安全。

## 面试场景 5：Spring MVC 请求处理完整流程（★核心）

🎤 面试官

一个 HTTP 请求打到 Spring Boot 应用，从进入 `DispatcherServlet` 到返回响应，中间经历了哪些组件？请把完整流程画出来。

🧑‍💻 你

```
Client
│  HTTP Request
▼
┌─────────────────────────────────────────────────────────────────┐
│  DispatcherServlet （Spring MVC 前端控制器，Servlet 3.0+ 自动注册）  │
└───────────────┬─────────────────────────────────────────────────┘
│  1. 根据 URL 找 Handler
▼
HandlerMapping （RequestMappingHandlerMapping 是主要实现）
│
│  2. 返回 HandlerExecutionChain
│    = Handler（Controller 方法）+ 若干 HandlerInterceptor
▼
HandlerAdapter （RequestMappingHandlerAdapter 是主要实现）
│
│  3. preHandle() 逐个执行 Interceptor
▼
HandlerInterceptor.preHandle()
│  返回 true 才继续
▼
HandlerMethodArgumentResolver （参数解析器）
│
│  4. 把 HttpServletRequest 转成方法参数
│    @RequestParam → RequestParamMethodArgumentResolver
│    @PathVariable → PathVariableMethodArgumentResolver
│    @RequestBody  → RequestResponseBodyMethodProcessor
▼
Controller 方法执行（你写的业务代码）
│
│  5. 返回值走 HandlerMethodReturnValueHandler
│    @ResponseBody → RequestResponseBodyMethodProcessor
│                    经过 HttpMessageConverter（Jackson）序列化为 JSON
│    普通对象      → ModelAndView
▼
HandlerInterceptor.postHandle()
│
▼
ViewResolver （若返回的是视图名而非 @ResponseBody）
│  6. 解析视图名 → View（JSP / Thymeleaf / FreeMarker）
▼
View.render() 渲染响应
│
▼
HandlerInterceptor.afterCompletion() （不管是否异常都执行）
│
▼
HTTP Response → Client
```

三大核心组件的职责：

- **`HandlerMapping`**：URL → Handler 的路由表。`RequestMappingHandlerMapping` 启动时扫描所有 `@Controller`/`@RequestMapping` 建映射表。

- **`HandlerAdapter`**：适配器模式，抽象「怎么调用 Handler」。因为 Handler 可能是 `@RequestMapping` 方法、`HttpRequestHandler`、`Controller` 接口实现等多种形态，用适配器统一调用。

- **`HandlerInterceptor`**：拦截器，三个钩子 `preHandle`（处理前）、`postHandle`（处理后视图渲染前）、`afterCompletion`（视图渲染后，一定执行，可以做资源清理）。区别于 Servlet `Filter`：Interceptor 是 Spring 层面，能拿到 Handler；Filter 是 Servlet 层面，早于 `DispatcherServlet`。

追问 Spring MVC 的 `HandlerMethodArgumentResolver` 是什么？可以自定义吗？

**参数解析器接口**。每种参数注解（`@RequestParam`、`@PathVariable`、`@RequestBody` 等）对应一个 `HandlerMethodArgumentResolver` 实现，负责把 `HttpServletRequest` 里的数据转换成方法参数值。可以*自定义*：实现 `HandlerMethodArgumentResolver`，重写 `supportsParameter`（判断是否处理这个参数）和 `resolveArgument`（真正解析）。典型场景：从请求头 `Authorization` 里解析 JWT，自定义 `@CurrentUser` 注解直接注入登录用户对象，业务代码里就不用每次 `request.getHeader("Authorization")` 再解析了。

追问 `HandlerInterceptor` 和 Servlet `Filter` 的区别和执行顺序？

执行顺序：`Filter.doFilter(前)` → `DispatcherServlet` → `Interceptor.preHandle` → Controller → `Interceptor.postHandle` → 视图渲染 → `Interceptor.afterCompletion` → `Filter.doFilter(后)`。区别：Filter 是 Servlet 规范（`javax.servlet`），不依赖 Spring，早于 `DispatcherServlet`；Interceptor 是 Spring 抽象，能拿到 `HandlerMethod`（可以知道打到哪个 Controller 方法上），能访问 Spring 容器里的 Bean。日志、鉴权推荐用 Interceptor（能拿到 Handler 元信息做精细化控制），编码、跨域推荐用 Filter（更底层，早生效）。

## 面试场景 6：响应处理注解 —— @ResponseBody & @ResponseStatus

🧑‍💻 你

- **`@ResponseBody`**：方法返回值不走 `ViewResolver`，直接经 `HttpMessageConverter` 写入响应体（返回对象 → JSON，返回 `String` → 纯文本）。加在类上等价于给所有方法加。`@RestController` = `@Controller` + `@ResponseBody`。

- **`@ResponseStatus`**：指定响应的 HTTP 状态码。既能加在 Controller 方法上（`@ResponseStatus(HttpStatus.CREATED)`），也能加在自定义异常类上（异常被 `@ExceptionHandler` 处理时按此状态码返回）。

```
@ResponseStatus(HttpStatus.NOT_FOUND)
public class UserNotFoundException extends RuntimeException {
public UserNotFoundException(Long id) {
super("User " + id + " not found");
}
}
// Controller 里 throw new UserNotFoundException(id)
// 客户端会收到 HTTP 404，无需额外配置
```

## 面试场景 7：异常处理注解 —— @ExceptionHandler & @ControllerAdvice & @RestControllerAdvice

🎤 面试官

怎么做一个*全局异常处理器*？`@ControllerAdvice` 是怎么捕获到所有 Controller 抛出的异常的？

🧑‍💻 你

三个注解的分工：

- **`@ExceptionHandler(XxxException.class)`**：声明*某个异常*的处理方法。放在 Controller 里只对本 Controller 生效；放在 `@ControllerAdvice` 里对*所有 Controller 生效*。

- **`@ControllerAdvice`**：*全局 Controller 增强*。类上加此注解，Spring 启动时会把里面的 `@ExceptionHandler`/`@InitBinder`/`@ModelAttribute` 应用到所有匹配的 Controller。

- **`@RestControllerAdvice`**：= `@ControllerAdvice` + `@ResponseBody`。异常处理方法返回值直接序列化为 JSON —— REST API 项目首选。

典型全局异常处理器：

```
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

// 处理参数校验异常
@ExceptionHandler(MethodArgumentNotValidException.class)
@ResponseStatus(HttpStatus.BAD_REQUEST)
public ApiResult<Void> handleValidation(MethodArgumentNotValidException ex) {
String msg = ex.getBindingResult().getFieldErrors().stream()
.map(err -> err.getField() + ": " + err.getDefaultMessage())
.collect(Collectors.joining("; "));
return ApiResult.fail(400, msg);
}

// 处理业务异常
@ExceptionHandler(BusinessException.class)
public ApiResult<Void> handleBusiness(BusinessException ex) {
return ApiResult.fail(ex.getCode(), ex.getMessage());
}

// 兜底
@ExceptionHandler(Exception.class)
@ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
public ApiResult<Void> handleAll(Exception ex) {
log.error("Unexpected error", ex);
return ApiResult.fail(500, "系统繁忙");
}
}
```

追问 `@ControllerAdvice` 是怎么捕获全局异常的？底层原理？

本质是 **AOP 思想 + 责任链**。`DispatcherServlet` 处理请求时如果 Controller 抛异常，会遍历 `HandlerExceptionResolver` 责任链，找能处理该异常的 resolver。其中 `ExceptionHandlerExceptionResolver` 会扫描所有 `@ControllerAdvice` 类里的 `@ExceptionHandler` 方法，按*异常类型精确度*选最匹配的一个来处理（比如同时有 `SQLException` 和 `Exception` 的 handler，抛 `SQLException` 会命中前者）。命中后调用该方法，返回值继续走 `HandlerMethodReturnValueHandler` 序列化写响应。

追问 `@ControllerAdvice` 能限定作用范围吗？

能。`@ControllerAdvice` 支持三种限定条件：`basePackages = "com.foo.api"`（按包）、`assignableTypes = SomeController.class`（按具体 Controller 类）、`annotations = RestController.class`（按注解）。比如后台管理和对外 API 想用不同的异常响应格式，就可以写两个 `@ControllerAdvice`，各自限定作用范围。

## 面试场景 8：JSR-303 参数校验注解 —— @Valid & @Validated & 字段级注解

🎤 面试官

Spring 里怎么做参数校验？`@Valid` 和 `@Validated` 有什么区别？

🧑‍💻 你

核心分两步：**DTO 字段上加约束注解** + **Controller 参数前加触发注解**。字段约束注解都是 JSR-303 / Bean Validation 标准（`jakarta.validation.constraints`）：

注解适用类型含义

`@NotNull`任意不能为 null（允许空字符串 `""`）
`@NotEmpty`String / Collection / Map / 数组不为 null 且长度/大小 > 0
`@NotBlank`CharSequence不为 null 且 `trim()` 后长度 > 0
`@Size(min, max)`String / Collection / Map / 数组长度/大小在区间内
`@Min(v)` / `@Max(v)`数字≥ v / ≤ v
`@DecimalMin` / `@DecimalMax`数字（含 `BigDecimal`）字符串表示的最小/最大值
`@Positive` / `@Negative`数字正数 / 负数
`@Pattern(regexp)`String匹配正则
`@Email`String邮箱格式
`@Past` / `@Future`时间过去 / 未来

🧑‍💻 你（续）

`@Valid` 和 `@Validated` 对比：

- **`@Valid`**：JSR-303 标准注解（`jakarta.validation.Valid`）。加在 *方法参数*、*字段*（触发嵌套对象校验）、*数组/集合元素* 上。不支持分组。

- **`@Validated`**：Spring 扩展（`org.springframework.validation.annotation.Validated`）。加在 *类*（对方法参数校验）或 *方法参数* 上。**支持分组校验**。

校验失败会抛 `MethodArgumentNotValidException`（`@RequestBody` 校验失败）或 `ConstraintViolationException`（`@RequestParam`/`@PathVariable` 校验失败），通常在全局异常处理器里统一捕获并返回友好错误信息。

追问 分组校验是什么？怎么用？

同一个 DTO 在*新增*和*更新*场景下校验规则不同 —— 新增时 `id` 应该为空，更新时 `id` 必填。分组校验解决这种场景：

```
public interface Create {}
public interface Update {}

public class UserDTO {
@Null(groups = Create.class)
@NotNull(groups = Update.class)
private Long id;

@NotBlank(groups = {Create.class, Update.class})
private String name;
}

// Controller
@PostMapping public void create(@Validated(Create.class) @RequestBody UserDTO dto) { }
@PutMapping  public void update(@Validated(Update.class) @RequestBody UserDTO dto) { }
```

`@Valid` 做不到这个，必须用 `@Validated`。

追问 嵌套对象校验怎么触发？

DTO 里嵌套的对象字段前**必须加 `@Valid`**，否则 Spring 不会递归校验嵌套对象的字段：

```
public class OrderDTO {
@NotNull private Long userId;

@Valid                    // ← 关键！不加就不会校验 items 里的字段
@NotEmpty
private List<ItemDTO> items;
}
```

陷阱 `@NotNull`、`@NotEmpty`、`@NotBlank` 三兄弟很容易搞混。记忆：**NotNull** 允许空串 `""`；**NotEmpty** 不允许空串但允许纯空格 `"   "`；**NotBlank** 连纯空格也不行（会 `trim()`）。字符串字段 99% 想要的是 `@NotBlank`。集合字段只能用 `@NotEmpty`（`@NotBlank` 不支持集合）。

## 面试场景 9：配置注解 —— @PropertySource / @ConfigurationProperties / @Profile / @Conditional

🧑‍💻 你

- **`@PropertySource("classpath:xxx.properties")`**：加载额外的 `.properties` 文件到 `Environment`。Spring Boot 默认加载 `application.properties`/`application.yml`，如果想加载自定义文件就用这个。*不支持 YAML*，Spring Boot 里改用 `spring.config.import`。

- **`@ConfigurationProperties(prefix="xxx")`**：*批量绑定*配置到对象。Spring Boot 推荐用法，比 `@Value` 一个个注入优雅得多，支持嵌套对象、List、Map、类型安全、IDE 自动补全（配合 `spring-boot-configuration-processor`）。

- **`@Profile("dev")`**：环境条件化 Bean。只在 `spring.profiles.active=dev` 时才注册该 Bean，用于区分开发/测试/生产环境的组件（如不同的 `DataSource`、Mock/真实的第三方客户端）。

- **`@Conditional(SomeCondition.class)`**：*Spring Boot 自动装配的核心*。传入一个 `Condition` 实现类，`matches` 返回 `true` 才注册。`@Profile` 本质就是 `@Conditional(ProfileCondition.class)`。Spring Boot 还派生出 `@ConditionalOnClass`、`@ConditionalOnMissingBean`、`@ConditionalOnProperty` 等一系列衍生注解。

```
// @ConfigurationProperties 示例
# application.yml
app:
api:
base-url: https://api.example.com
timeout: 3000
retry-count: 3

@Component
@ConfigurationProperties(prefix = "app.api")
@Data
public class ApiConfig {
private String baseUrl;
private int timeout;
private int retryCount;
}
```

追问 `@ConfigurationProperties` 和 `@Value` 有什么区别？什么时候用哪个？

`@Value` 适合*单个属性*，语法灵活支持 SpEL，但每处都要写全 key、类型转换弱、无嵌套、无 IDE 自动补全。`@ConfigurationProperties` 适合*一组相关配置*，声明一个 POJO 就能自动绑定，类型安全、支持嵌套/List/Map、支持 JSR-303 校验（`@Validated` + 字段约束），是 Spring Boot 推荐姿势。经验规则：*只用一次的散配置*用 `@Value`，*成组的模块配置*用 `@ConfigurationProperties`。

## 面试场景 10：Spring Boot 特有注解 —— @SpringBootApplication & @Conditional 家族

🎤 面试官

`@SpringBootApplication` 里包含了哪三个注解？分别是干嘛的？

🧑‍💻 你

**`@SpringBootApplication` = `@SpringBootConfiguration` + `@EnableAutoConfiguration` + `@ComponentScan`**：

- **`@SpringBootConfiguration`**：本质是 `@Configuration`，标记为配置类。

- **`@EnableAutoConfiguration`**：*Spring Boot 的灵魂*。启用自动装配机制，通过 `AutoConfigurationImportSelector` 加载 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（Spring Boot 2.7 前是 `META-INF/spring.factories`）里列出的所有自动配置类。下一课 0065 深挖。

- **`@ComponentScan`**：从主类所在包开始向下扫描 `@Component` 派生的 Bean。*所以主类一定要放在包的最顶层*，否则子包的 Bean 扫描不到。

自动配置类内部大量用 **`@Conditional` 家族**控制「什么时候加载」：

- `@ConditionalOnClass(RedisTemplate.class)`：类路径里存在指定类时才生效 —— 只有引入了 `spring-boot-starter-data-redis` 才装配 Redis 相关 Bean。

- `@ConditionalOnMissingBean(DataSource.class)`：容器里*没有*指定类型 Bean 时才生效 —— 用户没自定义 `DataSource` 才用默认的 HikariCP。

- `@ConditionalOnProperty(name="feature.x.enabled", havingValue="true")`：配置项等于指定值时才生效 —— 靠 `application.yml` 一键开关某个功能。

- `@ConditionalOnBean`：容器里*存在*指定 Bean 时才生效（与 MissingBean 相反）。

- `@ConditionalOnWebApplication` / `@ConditionalOnNotWebApplication`：Web 环境判断。

追问 Spring Boot 是怎么知道要加载哪些自动配置类的？

启动时 `AutoConfigurationImportSelector.selectImports()` 被 `@Import` 触发调用，用 `SpringFactoriesLoader` 读取所有 jar 包的 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（老版本是 `META-INF/spring.factories` 里 `EnableAutoConfiguration` 的 value），拿到一大堆 `XxxAutoConfiguration` 类名。这些类都带 `@Configuration` + `@ConditionalOnXxx`，Spring 挨个尝试装配，条件不满足的直接跳过。这样第三方库只要按约定放 imports 文件，用户依赖就自动生效。下一课 0065 详细分析源码。

追问 想禁用某个自动配置类怎么办？

三种方式：`@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class})` 编译期排除；`@EnableAutoConfiguration(excludeName = "...")` 按类名排除；`application.yml` 里 `spring.autoconfigure.exclude=xxx` 配置排除。日常最常见的场景：项目还没引入数据库，但 Spring Boot 检测到类路径有 `DataSource` 依赖硬要装配 `HikariCP`，启动失败 —— 就 `exclude` 掉 `DataSourceAutoConfiguration`。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：一个「够真实」的 REST Controller —— 涵盖 6 个参数注解

```
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor        // Lombok：为 final 字段生成构造器，配合构造器注入
public class UserController {

private final UserService userService;

// GET /api/users?page=1&size=10
@GetMapping
public PageResult<UserVO> list(
@RequestParam(defaultValue = "1") int page,
@RequestParam(defaultValue = "10") int size,
@RequestHeader("Authorization") String token) {
return userService.list(page, size);
}

// GET /api/users/42
@GetMapping("/{id}")
public UserVO getById(@PathVariable Long id) {
return userService.findById(id)
.orElseThrow(() -> new UserNotFoundException(id));
}

// POST /api/users （请求体是 JSON）
@PostMapping
@ResponseStatus(HttpStatus.CREATED)
public UserVO create(@Valid @RequestBody UserCreateRequest req) {
return userService.create(req);
}

// PUT /api/users/42
@PutMapping("/{id}")
public UserVO update(
@PathVariable Long id,
@Valid @RequestBody UserUpdateRequest req) {
return userService.update(id, req);
}

// DELETE /api/users/42
@DeleteMapping("/{id}")
@ResponseStatus(HttpStatus.NO_CONTENT)
public void delete(@PathVariable Long id) {
userService.delete(id);
}
}
```

### 验证 2：DTO + 参数校验（含分组、嵌套）

```
public interface Create {}
public interface Update {}

@Data
public class UserCreateRequest {

@NotBlank(message = "用户名不能为空")
@Size(min = 3, max = 20, message = "用户名长度 3-20")
private String username;

@NotBlank(message = "邮箱不能为空")
@Email(message = "邮箱格式不正确")
private String email;

@NotNull
@Min(value = 18, message = "年龄必须 ≥ 18")
@Max(value = 150, message = "年龄必须 ≤ 150")
private Integer age;

@Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式错误")
private String phone;

@Valid                                       // ← 嵌套校验必须加
@NotNull
private AddressDTO address;
}

@Data
public class AddressDTO {
@NotBlank private String province;
@NotBlank private String city;
@NotBlank private String detail;
}
```

### 验证 3：全局异常处理器（把校验异常翻译成友好响应）

```
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

// @RequestBody 校验失败
@ExceptionHandler(MethodArgumentNotValidException.class)
@ResponseStatus(HttpStatus.BAD_REQUEST)
public ApiResult<Void> handleBodyValidation(MethodArgumentNotValidException ex) {
String msg = ex.getBindingResult().getFieldErrors().stream()
.map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
.collect(Collectors.joining("; "));
return ApiResult.fail(400, msg);
}

// @RequestParam / @PathVariable 校验失败
@ExceptionHandler(ConstraintViolationException.class)
@ResponseStatus(HttpStatus.BAD_REQUEST)
public ApiResult<Void> handleParamValidation(ConstraintViolationException ex) {
String msg = ex.getConstraintViolations().stream()
.map(cv -> cv.getPropertyPath() + ": " + cv.getMessage())
.collect(Collectors.joining("; "));
return ApiResult.fail(400, msg);
}

// 业务异常
@ExceptionHandler(BusinessException.class)
public ResponseEntity<ApiResult<Void>> handleBusiness(BusinessException ex) {
return ResponseEntity.status(ex.getStatus())
.body(ApiResult.fail(ex.getCode(), ex.getMessage()));
}

// 兜底
@ExceptionHandler(Exception.class)
@ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
public ApiResult<Void> handleAll(Exception ex) {
log.error("Unexpected error at {}", MDC.get("traceId"), ex);
return ApiResult.fail(500, "系统繁忙，请稍后重试");
}
}
```

### 验证 4：自定义 HandlerInterceptor —— 打印请求耗时

```
@Component
@Slf4j
public class TimingInterceptor implements HandlerInterceptor {

private static final String START_TIME = "start_time";

@Override
public boolean preHandle(HttpServletRequest request,
HttpServletResponse response,
Object handler) {
request.setAttribute(START_TIME, System.currentTimeMillis());
return true;                                   // 返回 false 会中断请求
}

@Override
public void afterCompletion(HttpServletRequest request,
HttpServletResponse response,
Object handler, Exception ex) {
long cost = System.currentTimeMillis() - (long) request.getAttribute(START_TIME);
String method = request.getMethod();
String uri = request.getRequestURI();
log.info("{} {} cost {}ms status={}", method, uri, cost, response.getStatus());
}
}

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

private final TimingInterceptor timingInterceptor;

public WebMvcConfig(TimingInterceptor timingInterceptor) {
this.timingInterceptor = timingInterceptor;
}

@Override
public void addInterceptors(InterceptorRegistry registry) {
registry.addInterceptor(timingInterceptor)
.addPathPatterns("/api/**")           // 只拦 API
.excludePathPatterns("/api/health");  // 健康检查除外
}
}
```

### 验证 5：`@ConfigurationProperties` + `@Bean` —— 装配第三方 RestTemplate

```
# application.yml
app:
http:
connect-timeout: 3000
read-timeout: 5000
max-connections: 200

@Data
@ConfigurationProperties(prefix = "app.http")
@Validated
public class HttpClientProperties {
@NotNull @Min(100) private Integer connectTimeout;
@NotNull @Min(100) private Integer readTimeout;
@NotNull @Min(1)   private Integer maxConnections;
}

@Configuration
@EnableConfigurationProperties(HttpClientProperties.class)
public class HttpClientConfig {

// @Bean 手动装配第三方类
@Bean
public RestTemplate restTemplate(HttpClientProperties props) {
HttpComponentsClientHttpRequestFactory factory =
new HttpComponentsClientHttpRequestFactory();
factory.setConnectTimeout(props.getConnectTimeout());
factory.setReadTimeout(props.getReadTimeout());
return new RestTemplate(factory);
}
}
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `@Component`、`@Service`、`@Repository`、`@Controller` 有什么区别？</summary>

功能上都是注册 Bean，本质等价。区别有三：（1）**语义分层**，看到即知层次；（2）`@Repository` 会被 `PersistenceExceptionTranslationPostProcessor` 处理，把原生数据库异常翻译成 Spring 的 `DataAccessException`；（3）AOP 切点表达式可精准切某一层。

</details>

<details>

<summary>Q2 用一句话描述 Spring MVC 请求处理流程。</summary>

请求进入 `DispatcherServlet`，通过 `HandlerMapping` 找到 Handler（Controller 方法），`HandlerAdapter` 调用；调用前后经过 `HandlerInterceptor` 三个钩子；参数解析交给 `HandlerMethodArgumentResolver`，返回值处理交给 `HandlerMethodReturnValueHandler`（`@ResponseBody` 走 `HttpMessageConverter` 序列化 JSON；否则走 `ViewResolver` 解析视图）。

</details>

<details>

<summary>Q3 `@Autowired` 和 `@Resource` 的核心区别是什么？</summary>

`@Autowired` 是 Spring 提供，*默认按类型注入*，多候选用 `@Qualifier`/`@Primary` 区分，支持构造器/字段/Setter。`@Resource` 是 JSR-250 标准，*默认按名称注入*，找不到再按类型，不支持构造器注入。

</details>

<details>

<summary>Q4 `@Valid` 和 `@Validated` 有什么区别？校验失败会抛什么异常？</summary>

`@Valid` 是 JSR-303 标准，*不支持分组*；`@Validated` 是 Spring 扩展，*支持分组校验*，还可加在类上做方法级校验。`@RequestBody` 校验失败抛 `MethodArgumentNotValidException`；`@RequestParam`/`@PathVariable` 校验失败抛 `ConstraintViolationException`。通常在全局异常处理器统一捕获。

</details>

<details>

<summary>Q5 `@SpringBootApplication` 展开是哪三个注解？`@ConditionalOnMissingBean` 有什么用？</summary>

= `@SpringBootConfiguration`（= `@Configuration`） + `@EnableAutoConfiguration`（触发自动装配） + `@ComponentScan`（扫描主类所在包及子包的 Bean）。`@ConditionalOnMissingBean` 表示*容器里没有该类型 Bean 时才装配*，是「用户自定义优先，官方默认兜底」的关键机制 —— 你自己写了 `DataSource` Bean，Spring Boot 就不再自动装配默认的 HikariCP。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Spring Framework 官方文档 · The DispatcherServlet —— 请求处理流程权威描述

- Spring Framework · Java Bean Validation —— `@Valid`/`@Validated` 完整用法

- Spring Boot · Condition Annotations —— `@ConditionalOnXxx` 家族清单

#### 🔗 关联课件

-  —— 注解注册的 Bean 后续怎么走 BeanPostProcessor

-

-  —— 从 `@EnableAutoConfiguration` 一路拆到 `AutoConfigurationImportSelector`

#### 🧭 下一课预告

Lesson 0065：**Spring Boot 自动装配原理** —— 深挖 `@SpringBootApplication` 启动、`@EnableAutoConfiguration`、`AutoConfigurationImportSelector`、`spring.factories` / `AutoConfiguration.imports`、Starter 机制、`@Conditional` 家族源码级解析。今天认识的所有 `@ConditionalOnXxx` 明天会拆开看它们怎么被 Spring Boot 组织起来。

💬 有任何疑问 —— 「这里为什么这样？」「能不能再举一个例子？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


