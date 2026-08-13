> Lesson 0065 · 阶段八 · Spring · ⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测 · 8 个追问

# 0065 · SpringBoot 自动装配原理 & starter & 条件注解

这一课覆盖的完整链条。SpringBoot 的核心魔法就一句话：**引入一个 starter，剩下全都不用配**。面试官几乎必问：**「`@SpringBootApplication` 底层做了什么？」「怎么写一个自定义 starter？」「`@ConditionalOnMissingBean` 为什么这么重要？」**—— 这三个问题连起来，就是本节课的骨架。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 `@SpringBootApplication` 等于哪几个注解合起来？</summary>

三合一：`@SpringBootConfiguration`（等价 `@Configuration`）+ `@EnableAutoConfiguration`（自动装配入口）+ `@ComponentScan`（扫描当前包及子包）。第 2 题细讲。

</details>

<details>

<summary>Q0.2 `spring.factories` 和 SpringBoot 3 的 `AutoConfiguration.imports` 文件有什么关系？</summary>

同一个功能的新旧两代载体。老格式 `META-INF/spring.factories` 用 `key=value`；新格式 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` 一行一个类名。2.7 两者共存，3.0 之后官方只认新格式。第 4 题细讲。

</details>

## 面试场景 1：Spring Boot 是什么？相比 Spring 好在哪？

🎤 面试官

用一分钟介绍下 Spring Boot，它相比原生 Spring 有什么优势？

🧑‍💻 你

Spring Boot 是 Spring 团队为了简化 Spring 应用开发做的一层「脚手架」。原生 Spring 要跑个 Web 应用，得写一堆 `web.xml` / `DispatcherServlet` / `ViewResolver` 配置。Spring Boot 把这些做成了默认，只要引入 starter 就能开跑。核心优势有五点：

- **约定优于配置**：绝大多数配置都有合理默认值，不用改也能跑。

- **starter 机制**：`spring-boot-starter-web` 一键引入 Web 全套依赖（Spring MVC + Tomcat + Jackson）。

- **自动装配**：根据 classpath 上有什么类，自动配置对应 Bean。

- **内嵌 Tomcat**：不用装外部容器，`java -jar` 直接跑。

- **Actuator 监控**：内置一批健康检查、指标暴露端点。

追问 为什么 Spring Boot 内嵌 Tomcat 但也能改用 Jetty / Undertow？

`spring-boot-starter-web` 默认**传递依赖** `spring-boot-starter-tomcat`；想切成 Jetty 只需在 pom 里排除 tomcat，再引入 `spring-boot-starter-jetty`：`<exclusions><exclusion>spring-boot-starter-tomcat</exclusion></exclusions>`。自动装配靠 `@ConditionalOnClass` 判断 classpath 上有哪种 Servlet 容器，就自动装哪种。

## 面试场景 2：`@SpringBootApplication` 是三合一 ⭐核心

🎤 面试官

启动类上的 `@SpringBootApplication`，它其实是几个注解的组合，你能拆开讲讲吗？

🧑‍💻 你

翻源码可以看到：

```
@SpringBootConfiguration        // ← ①
@EnableAutoConfiguration        // ← ② 自动装配的入口
@ComponentScan                  // ← ③
public @interface SpringBootApplication { ... }
```

1. **`@SpringBootConfiguration`**：本质就是 `@Configuration`，把启动类自身也当成一个配置类，允许在里面写 `@Bean` 方法。

2. **`@EnableAutoConfiguration`**：*整个 Spring Boot 最核心的那个*。它通过 `@Import(AutoConfigurationImportSelector.class)` 触发自动装配。

3. **`@ComponentScan`**：默认扫描*启动类所在包及子包*下所有 `@Component` / `@Service` / `@Controller` / `@Repository`。

这也解释了为什么大家习惯把启动类放在包的最顶层 —— 放深了，兄弟包的 Bean 就扫不到。

追问 `@Import` 和 `@Component` 有什么区别？

`@Component` 靠 `@ComponentScan` 扫描发现，前提是这个类必须落在扫描范围内。`@Import` 是*显式导入*某个类，跨模块场景里特别有用 —— 比如自动装配的候选类往往在别的 jar 里，扫描根本扫不到，只能靠 `@Import` 把它们「拽」进当前容器。

## 面试场景 3：`@EnableAutoConfiguration` 的核心 ⭐核心

🧑‍💻 你

`@EnableAutoConfiguration` 本身没多少代码，关键在这两行：

```
@AutoConfigurationPackage                          // 把启动类所在包记下来
@Import(AutoConfigurationImportSelector.class)     // ★ 真正干活的
public @interface EnableAutoConfiguration { ... }
```

`AutoConfigurationImportSelector` 实现了 `DeferredImportSelector` 接口，它的 `selectImports()` 方法会：

1. 扫描 classpath 下*所有* jar 的自动配置元数据文件（下题细讲位置）；

2. 把里面写的所有配置类*全名字符串*拿出来；

3. 去重、按 `exclude` 移除、按 `@Conditional*` 过滤；

4. 把幸存的配置类交给 Spring 容器去加载。

追问 为什么用 `DeferredImportSelector` 而不是普通 `ImportSelector`？

`DeferredImportSelector` 会**延后到所有普通 `@Configuration` 处理完之后**再执行。这样自动配置类看到的容器已经有用户手写的 Bean 了，`@ConditionalOnMissingBean` 才能正确判断「用户是否已经自己提供了」。

## 面试场景 4：自动配置元数据文件的位置演进

🎤 面试官

SpringBoot 2 和 SpringBoot 3 在自动装配上有什么变化？

🧑‍💻 你

关键就在*自动配置元数据文件*的位置：

版本文件位置写法

≤ 2.6
`META-INF/spring.factories`
`org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
com.xxx.XxxAutoConfiguration,\
com.yyy.YyyAutoConfiguration`

2.7
两者共存，向后兼容
推荐用新格式

≥ 3.0
`META-INF/spring/
org.springframework.boot.autoconfigure.AutoConfiguration.imports`
一行一个类全名，无 key，无逗号，无反斜杠

追问 Spring Boot 3.0 为什么废弃 `spring.factories`？

三个原因：**①** 老格式一个 properties 文件承载了 *N 种* 扩展点（`EnableAutoConfiguration`、`ApplicationListener`、`EnvironmentPostProcessor`...），key 挤在一起可读性差；**②** 新格式一个 imports 文件*只干一件事*，一行一个类名，语法极简；**③** 更契合 JDK 9+ 的 *Java Module* 系统 —— 自动配置类可以放在 module 内部，通过 imports 显式对外暴露。

## 面试场景 5：自动装配的完整链条 ⭐核心

🧑‍💻 你

把整条链路串起来，闭着眼也能背：

```
① 启动 SpringApplication.run(App.class)
│
▼
② 扫到启动类上的 @SpringBootApplication
│
├─→ @ComponentScan         (扫本包及子包的 @Component)
├─→ @SpringBootConfiguration (自己也是配置类)
└─→ @EnableAutoConfiguration  ★
│
▼
③ @Import(AutoConfigurationImportSelector.class)
│
▼
④ AutoConfigurationImportSelector.selectImports()
│
├─ 读所有 jar 的 META-INF/spring/....AutoConfiguration.imports
├─ 拿到候选配置类全名列表（可能上百个）
├─ 应用 exclude / excludeName
└─ 逐个应用 @Conditional* 过滤
│
▼
⑤ 幸存的 XxxAutoConfiguration 被激活
│
└─ 里面的 @Bean 定义注册到 IoC 容器
```

整个过程的精髓是「**候选池很大，但真正被激活的只是满足条件的那一小部分**」—— 这就是 Spring Boot 既功能齐全、又启动不慢的关键。

## 面试场景 6：常见条件注解 ⭐核心

🎤 面试官

你说条件过滤，具体有哪些 `@Conditional*`？举几个最常用的。

🧑‍💻 你

注解触发条件典型用途

`@ConditionalOnClass`classpath 上有指定的类`@ConditionalOnClass(RedisTemplate.class)`：引入 redis 依赖时才装配
`@ConditionalOnMissingClass`classpath 上没有指定的类老新框架二选一时用
`@ConditionalOnBean`容器已有指定 Bean依赖别的 Bean 存在时才装
`@ConditionalOnMissingBean` ★容器*没有*该 Bean 才装让用户自定义能覆盖默认
`@ConditionalOnProperty`配置项匹配`havingValue = "true"`：开关式装配
`@ConditionalOnWebApplication`当前是 Web 项目只在 Web 环境下装的 MVC 相关
`@ConditionalOnNotWebApplication`非 Web 项目批处理、纯 CLI 场景
`@ConditionalOnExpression`SpEL 结果为 true复杂逻辑判断

追问 `@ConditionalOnMissingBean` 到底有什么用？为什么它是最重要的一个？

它是 Spring Boot「**合理默认 + 可覆盖**」哲学的技术支柱。比如 `RedisAutoConfiguration` 里定义了默认的 `RedisTemplate`：`@Bean @ConditionalOnMissingBean public RedisTemplate<?, ?> redisTemplate(...)`。如果你在业务代码里自己写了一个 `@Bean RedisTemplate`，容器里就已经有了，官方那个 `@ConditionalOnMissingBean` 判断不通过，就*不装配*了 —— 你的自定义 Bean 完美「覆盖」了默认，两者不会冲突。这就是「零配置又能定制」的秘密。

## 面试场景 7：starter 是什么？⭐核心

🧑‍💻 你

starter 的本质是「**一个 pom 依赖聚合 + 一个自动配置类**」，起到两件事：

1. **依赖聚合**：通过 Maven 的传递依赖，一次性把「实现 XX 功能所需的所有 jar」都拉进来。用户不用手动挑版本、不用担心兼容。

2. **自动装配**：starter 内部（或对应的 autoconfigure 模块）注册了 `XxxAutoConfiguration`，通过 `@Conditional*` 判断，一旦引入就自动装好 Bean。

所以业务代码只需要写一句 `<dependency>spring-boot-starter-data-redis</dependency>`，就同时得到了「依赖 + 配置」两件事 —— 这就是 starter 的魔法。

## 面试场景 8：官方 starter 举例

🧑‍💻 你

Starter拉进来什么装好什么 Bean

`spring-boot-starter-web`
Spring MVC + Tomcat + Jackson
`DispatcherServlet`、`MappingJackson2HttpMessageConverter`、内嵌 `TomcatServletWebServerFactory`

`spring-boot-starter-data-jpa`
Hibernate + Spring Data JPA + HikariCP
`EntityManagerFactory`、`TransactionManager`、Repository 代理

`spring-boot-starter-data-redis`
Lettuce（默认）或 Jedis
`RedisConnectionFactory`、`RedisTemplate`、`StringRedisTemplate`

`spring-boot-starter-test`
JUnit 5 + Mockito + AssertJ + Spring Test
`@SpringBootTest`、`TestRestTemplate`、`MockMvc` 支持

`spring-boot-starter-actuator`
Actuator + Micrometer
`/actuator/health`、`/actuator/metrics`、`/actuator/env` 等端点

追问 Actuator 是什么？生产上要注意什么？

Actuator 是 Spring Boot 内置的**监控与运维**组件，暴露 `/actuator/health`（健康检查）、`/actuator/metrics`（指标）、`/actuator/env`（配置）、`/actuator/heapdump`（堆转储）等一批 HTTP 端点。生产上必须注意：**①** `/env`、`/heapdump`、`/threaddump` 会泄漏敏感信息，默认要关闭或加认证；**②** 用 `management.endpoints.web.exposure.include=health,info` 白名单控制；**③** 建议把 Actuator 端口和业务端口*分开*（`management.server.port=9090`），只对内网开放。

## 面试场景 9：怎么自定义一个 starter？

🎤 面试官

假设让你封装一个团队通用的线程池 starter，你会怎么做？

🧑‍💻 你

四步走：

1. **建 Maven 模块** `myapp-spring-boot-starter`（注意第三方命名规范放在下题）。引入 `spring-boot-autoconfigure`。

2. **建 `@ConfigurationProperties`**：把用户可配的项都定义好，前缀取 `myapp.xxx`。

3. **建自动配置类**：`@Configuration + @ConditionalOnClass + @EnableConfigurationProperties + @Bean + @ConditionalOnMissingBean`。

4. **建 imports 文件**：`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`，一行写自动配置类全名。

完整骨架代码见下面的「代码验证」小节。

## 面试场景 10：约定命名规范

🧑‍💻 你

官方和第三方 starter 的命名规范*正好相反*，这是 Spring 团队的硬性约定：

- **官方 starter**：`spring-boot-starter-*`，如 `spring-boot-starter-web`、`spring-boot-starter-data-redis`。

- **第三方 starter**：`*-spring-boot-starter`，如 `mybatis-spring-boot-starter`、`druid-spring-boot-starter`、`knife4j-spring-boot-starter`。

这样做是为了**避免和官方冲突**，一眼从名字就能判断出「这是官方 / 这是社区」。自己写 starter 一定要遵守这个规范，否则会被同行嫌弃。

陷阱 有些新手把自己团队的 starter 命名成 `spring-boot-starter-mycompany`，误以为「和官方一样气派」。这其实是*反规范*，正确命名应该是 `mycompany-spring-boot-starter`。真被同行看到会觉得业务不熟。

## 💻 代码验证：写一个 `threadpool-spring-boot-starter`

### 验证 1：配置属性类

```
package com.example.threadpool;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.thread-pool")
public class ThreadPoolProperties {
private int corePoolSize = 10;
private int maxPoolSize = 20;
private int queueCapacity = 100;
private int keepAliveSeconds = 60;
private boolean enabled = true;

// getter / setter 略
}
```

### 验证 2：自动配置类

```
package com.example.threadpool;

import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.*;

@Configuration
@ConditionalOnClass(ThreadPoolExecutor.class)                    // classpath 有 JUC
@EnableConfigurationProperties(ThreadPoolProperties.class)       // 绑定配置
@ConditionalOnProperty(
prefix = "app.thread-pool",
name   = "enabled",
havingValue    = "true",
matchIfMissing = true                                        // 默认开
)
public class ThreadPoolAutoConfiguration {

@Bean
@ConditionalOnMissingBean                                    // ★ 用户没自己定义时才装
public ThreadPoolExecutor appThreadPool(ThreadPoolProperties p) {
return new ThreadPoolExecutor(
p.getCorePoolSize(),
p.getMaxPoolSize(),
p.getKeepAliveSeconds(),
TimeUnit.SECONDS,
new LinkedBlockingQueue<>(p.getQueueCapacity()),
new ThreadPoolExecutor.CallerRunsPolicy()             // 默认拒绝策略
);
}
}
```

### 验证 3：SpringBoot 3.x 的注册文件

```
# 文件路径：
# src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports

com.example.threadpool.ThreadPoolAutoConfiguration
```

如果要兼容 SpringBoot 2.6 及以下，额外加一份：

```
# src/main/resources/META-INF/spring.factories
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
com.example.threadpool.ThreadPoolAutoConfiguration
```

### 验证 4：业务侧使用

```
# application.yml
app:
thread-pool:
enabled: true
core-pool-size: 16
max-pool-size: 32
queue-capacity: 500
```

```
// 业务代码里直接注入
@RestController
public class DemoController {

private final ThreadPoolExecutor pool;

public DemoController(ThreadPoolExecutor pool) {   // ← 自动装配好的 Bean
this.pool = pool;
}

@GetMapping("/async")
public String async() {
pool.execute(() -> System.out.println("run in " + Thread.currentThread().getName()));
return "submitted";
}
}
```

*要覆盖默认怎么办？* 用户自己写一个 `@Bean ThreadPoolExecutor appThreadPool()`，因为 `@ConditionalOnMissingBean` 的存在，我们 starter 里的默认实现*不会*被装配，两个 Bean 不会打架。这就是「合理默认 + 可覆盖」在 starter 里的具体实现。

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 `@SpringBootApplication` 由哪三个注解组合而成？各起什么作用？</summary>

`@SpringBootConfiguration`（等价 `@Configuration`，让启动类自身成为配置类）+ `@EnableAutoConfiguration`（通过 `@Import(AutoConfigurationImportSelector.class)` 触发自动装配）+ `@ComponentScan`（默认扫描启动类所在包及子包）。

</details>

<details>

<summary>Q2 自动装配的候选配置类，SpringBoot 3.0 从哪个文件读取？和之前有什么不同？</summary>

从 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` 读取，一行一个类全名。之前用 `META-INF/spring.factories`，通过 `EnableAutoConfiguration=` key 拼接类名列表。2.7 两者共存，3.0 之后不再支持 `spring.factories` 里的 `EnableAutoConfiguration` key。

</details>

<details>

<summary>Q3 `@ConditionalOnMissingBean` 的核心价值是什么？举一个具体例子。</summary>

它让 starter 提供的默认 Bean 只在*用户没自己定义*时才装配，从而实现「合理默认 + 可覆盖」。例如 `RedisAutoConfiguration` 里的 `RedisTemplate` 就用了这个注解，用户在业务代码里自己 `@Bean RedisTemplate` 就能无冲突地覆盖它。

</details>

<details>

<summary>Q4 官方 starter 和第三方 starter 的命名规范分别是什么？</summary>

官方 `spring-boot-starter-*`（如 `spring-boot-starter-web`）；第三方 `*-spring-boot-starter`（如 `mybatis-spring-boot-starter`、`druid-spring-boot-starter`）。反着命名是为了避免与官方冲突，一眼可辨来源。

</details>

<details>

<summary>Q5 自定义一个 starter 的最小构件是哪几样？</summary>

四样：**①** 一个 `@ConfigurationProperties` 类承接 yml 配置；**②** 一个 `@Configuration` 自动配置类，配上 `@ConditionalOnClass` / `@ConditionalOnMissingBean` 等条件注解和 `@Bean` 方法；**③** `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` 文件（3.0+）或 `META-INF/spring.factories`（≤2.6）注册配置类；**④** 一份聚合了运行时依赖的 pom。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- Spring Boot Reference · Developing Auto-configuration —— 官方指南

- Spring Boot Reference · Actuator —— 生产监控端点

#### 🔗 关联课件

- ``````

-

- ``

#### 🧭 下一课预告

Lesson 0066：**Spring 里的设计模式** —— 单例、工厂、代理、模板方法、观察者、责任链在 Spring 源码里的落地。阶段八 Spring 大结局。

💬 有任何疑问 —— 「imports 文件为什么用这么长的路径？」「`@Conditional` 自定义条件怎么写？」「面试真被问过 XX 变体，怎么答？」—— 直接问我。我是你的老师，也是你的追问陪练。


