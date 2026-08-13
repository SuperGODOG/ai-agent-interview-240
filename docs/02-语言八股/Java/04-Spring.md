# 04 · Spring

## 一、IOC / DI

### 是什么
- IOC（控制反转）：对象的创建和依赖关系交给容器管理，而不是在代码里 new。
- DI（依赖注入）：容器在创建 Bean 时把依赖注入进去（构造器/Setter/字段 @Autowired）。
- 好处：解耦、统一管理生命周期、方便扩展和测试。

### BeanFactory vs ApplicationContext
- BeanFactory：最底层容器，懒加载（getBean 时才实例化）。
- ApplicationContext：BeanFactory 的子接口，支持 AOP、事件、国际化、资源加载，默认预加载（单例 Bean 启动时就创建）。日常用后者。

### Bean 作用域
- singleton（默认）、prototype（每次 getBean 新实例）、request/session/application（Web 场景）。
- 注意：singleton 里注入 prototype 拿到的永远是同一个实例，用 ObjectProvider / @Lookup / ScopedProxy 解决。

### Bean 生命周期（必背）
实例化（构造器）→ 属性填充（依赖注入）→ Aware 回调（BeanNameAware/BeanFactoryAware/ApplicationContextAware）→ BeanPostProcessor.beforeInitialization → @PostConstruct（InitializingBean.afterPropertiesSet）→ BeanPostProcessor.afterInitialization（AOP 代理在这里生成）→ 就绪使用 → @PreDestroy（DisposableBean.destroy）→ 销毁。

### Bean 定义方式
- XML、@Component 系列（@Service/@Repository/@Controller）、@Bean、@Import、FactoryBean。

## 二、循环依赖与三级缓存（高频）

### 什么是循环依赖
- A 依赖 B、B 依赖 A（构造器循环依赖无法解决，只能字段/Setter 注入）。

### 三级缓存
1. singletonObjects：一级，成品单例池
2. earlySingletonObjects：二级，提前暴露的半成品（早期引用）
3. singletonFactories：三级，ObjectFactory 工厂，用于生成早期引用
- 流程：创建 A → 实例化后放入三级缓存（lambda 工厂）→ 填充属性发现需要 B → 创建 B → B 填充属性发现 A → 从三级缓存拿到 A 的早期引用（此时会升级到二级）→ B 完成 → B 入一级 → A 拿到 B 完成 → A 入一级。
- 为什么三级而不是二级：三级缓存存的是 ObjectFactory，可以延迟 AOP 代理的创建——只有真正出现循环依赖时才提前生成代理，避免所有 Bean 都提前被代理（省性能）。
- AOP 与循环依赖：如果 A 需要代理，三级缓存工厂返回的是代理对象，保证 B 拿到的 A 也是代理。

## 三、AOP

### 是什么
- 面向切面编程：把日志、事务、权限等横切逻辑抽出来，动态织入目标方法，不改业务代码。

### 核心概念
- Aspect 切面、JoinPoint 连接点、Pointcut 切点（表达式）、Advice 通知（Before/After/AfterReturning/AfterThrowing/Around）、织入 Weaving。

### 实现方式（必考）
1. JDK 动态代理：目标类实现接口时用，Proxy.newProxyInstance 生成实现接口的代理类，通过 InvocationHandler 转发；只能代理接口。
2. CGLIB：目标类没有接口时用，生成目标类的子类，通过继承 + 字节码增强（ASM）重写方法；不能代理 final 类/final 方法。
- Spring 默认：目标实现了接口 → JDK 代理；否则 CGLIB（Spring Boot 2.x 后默认 CGLIB，可配置）。
- 自调用问题：同类内部方法调用 this.method() 不走代理，AOP 不生效；解决：注入自身代理、AopContext.currentProxy()、拆类。

### 应用
- @Transactional 事务、日志切面、鉴权、MyBatis 的 Mapper 动态代理、Feign 接口代理。

## 四、事务

- @Transactional 默认只回滚 RuntimeException 和 Error，检查异常（Exception）不回滚，要 rollbackFor = Exception.class。
- 事务失效场景：自调用（同类方法直接调，不走代理）、方法非 public、异常被 try-catch 吞掉、类没被 Spring 管理、传播行为错误、数据库引擎不支持（MyISAM）。
- 传播行为：REQUIRED（默认，加入或新建）、REQUIRES_NEW（挂起旧事务开新的）、NESTED（嵌套，savepoint 部分回滚）等。
- 隔离级别：读未提交/读已提交/可重复读/串行化。

## 五、Spring Boot 自动配置（必考）

### 原理
1. 启动类 @SpringBootApplication = @SpringBootConfiguration + @EnableAutoConfiguration + @ComponentScan。
2. @EnableAutoConfiguration 导入 AutoConfigurationImportSelector。
3. 它扫描 META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports（老版本 spring.factories），读取所有自动配置类（如 RedisAutoConfiguration、DataSourceAutoConfiguration）。
4. 自动配置类用 @ConditionalOnClass / @ConditionalOnMissingBean / @ConditionalOnProperty 等条件注解，按"类路径有没有这个类、用户有没有自定义 Bean"决定是否生效。
5. 生效后再绑定属性（@ConfigurationProperties，如 spring.redis.* 映射 RedisProperties）。

### Starter 机制
- spring-boot-starter-xxx 只做一件事：把依赖打包 + 提供自动配置入口，开发者零配置使用。

### 为什么说"约定大于配置"
- 提供默认值（端口 8080、数据源等），改了配置才需要显式写。

## 六、Spring MVC 请求流程（背流程图）

1. 请求到达 DispatcherServlet（前端控制器）。
2. HandlerMapping 找到对应的 Handler（Controller 方法）。
3. HandlerAdapter 调用处理器，执行拦截器、参数绑定（@RequestBody/@PathVariable）、方法调用。
4. 返回 ModelAndView 或 @ResponseBody 序列化（Jackson）。
5. 视图解析器渲染（前后端分离时代多直接返回 JSON）。
6. 响应返回，拦截器 afterCompletion。

### 组件
- DispatcherServlet、HandlerMapping、HandlerAdapter、HandlerInterceptor、ViewResolver、@RestControllerAdvice 全局异常处理。

## 七、@Autowired vs @Resource

- @Autowired：Spring 提供，默认 byType，再按 @Qualifier/byName 区分；required=true 找不到会报错。
- @Resource：JSR-250，默认 byName 再 byType。
- 构造器注入推荐（不可变、方便测试、避免循环依赖误用）；字段注入简单但隐藏依赖。

## 八、常问追问

1. 循环依赖为什么构造器注入不行？→ 构造器没执行完，对象还没实例化完成，没有"早期引用"可用。
2. 三级缓存为什么存 ObjectFactory？→ 延迟 AOP 代理创建，只有循环依赖时才提前代理。
3. JDK 代理和 CGLIB 的区别？→ 接口 vs 子类；final 限制。
4. @Transactional 什么时候失效？→ 自调用/异常被吞/非 public/引擎不支持等。
5. Spring Boot 自动配置怎么生效的？→ imports 文件 + 条件注解。
6. Spring 怎么解决 Bean 冲突？→ @Primary / @Qualifier / 按名字。
7. 单例 Bean 线程安全吗？→ Bean 本身无状态才安全；有状态字段要注意并发（如用 ThreadLocal）。
8. BeanPostProcessor 和 BeanFactoryPostProcessor 区别？→ 前者处理 Bean 实例，后者处理 BeanDefinition。
