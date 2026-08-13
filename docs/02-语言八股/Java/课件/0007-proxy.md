> Lesson 0007 · 阶段一 · Java 基础 · ⭐⭐⭐⭐⭐ · 预计 60 分钟｜含 10 个面试场景 · 4 段可跑代码 · 5 道自测

# 0007 · 代理模式深挖：静态代理 & JDK 动态代理 & CGLIB & Spring AOP 应用

这一课覆盖的全部核心内容。一句话概括：**代理 = 在不修改原类的前提下增强行为**。`@Transactional`、`@Cacheable`、`@Async`、`@PreAuthorize`、Feign、MyBatis Mapper —— 这些日常用得飞起的注解和框架，底层无一例外都建立在**反射 + 动态代理**之上。上一课我们把反射讲透了，这一课就是把「反射能干什么」中最重要的那件事讲透。

面试频度极高，且几乎必定追问细节：**「Spring AOP 用的是 JDK 还是 CGLIB？」「`this.xxx()` 内部调用为什么让 `@Transactional` 失效？」「CGLIB 为什么不能代理 final 方法？」**—— 这些追问是筛掉「只会背 API」和「真理解原理」的分水岭。

## 学前热身

Warm-up · 凭直觉答一下

<details>

<summary>Q0.1 Spring AOP 默认使用哪一种代理？JDK 动态代理还是 CGLIB？</summary>

要分版本回答。Spring 5 之前：**目标类实现了接口就用 JDK，没有接口就用 CGLIB**；Spring Boot 2.0+：**默认全部用 CGLIB**，可通过 `spring.aop.proxy-target-class=false` 切回按接口判断。第 7 题细讲。

</details>

<details>

<summary>Q0.2 `final` 方法能被 CGLIB 代理吗？</summary>

不能。CGLIB 生成的代理类是**目标类的子类**，子类无法覆盖 `final` 方法，所以 `final` 方法上的 AOP 增强会静默失效。`final` 类更彻底 —— 连子类都生成不出来，直接报错。第 5、8 题细讲。

</details>

## 面试场景 1：什么是代理模式？为什么要用？

🎤 面试官

先用一分钟解释一下代理模式是什么，我们为什么需要它？

🧑‍💻 你

代理模式属于结构型设计模式。核心思想：**用一个代理对象替代对真实对象的访问，在不修改原类的前提下，给原方法织入额外行为**。UML 上是三个角色：

- **Subject 接口**：抽象出「被代理什么行为」。

- **RealSubject（目标类）**：真正干活的类。

- **Proxy（代理类）**：持有 RealSubject 引用，实现相同接口/继承相同父类，转发调用并在前后加自己的逻辑。

为什么要用？—— 因为业务里大量存在**横切关注点（cross-cutting concerns）**，它们不属于业务本身但每个方法都要做：

- **日志**：进入/退出方法打日志、打耗时。

- **事务**：方法开始 `begin`，成功 `commit`，异常 `rollback`。

- **权限**：调用前检查当前用户角色/接口白名单。

- **缓存**：先查缓存，命中直接返回，未命中走真实方法后回写。

- **限流/熔断**：进入前问一下 Sentinel/Hystrix「让不让过？」。

- **远程调用**：Feign / Dubbo 把「本地方法调用」代理成「HTTP/RPC 请求」。

如果把这些逻辑硬塞进每个业务方法，会产生海量重复代码。代理模式（配合 AOP 思想）把这些切面统一抽出去，业务代码只关心业务本身。

追问 代理模式和装饰器模式看起来很像，怎么区分？

结构几乎一样（都持有目标对象、都实现相同接口），区别在**意图**：**代理关注的是「访问控制」**（要不要让你调、能不能调、调之前后加什么统一逻辑），**装饰器关注的是「行为增强/组合」**（给对象动态叠加新能力，且经常多层嵌套，比如 `BufferedReader(InputStreamReader(FileInputStream(...)))`）。面试时能说出「意图不同」就够加分了。

## 面试场景 2：静态代理是怎么写的？有什么缺点？

🎤 面试官

先讲讲静态代理，写伪代码就行。你觉得它的痛点在哪？

🧑‍💻 你

**静态代理**：代理类在编译期就写好、编译好。三步走：

1. 定义接口 `SmsService`。

2. 写目标类 `SmsServiceImpl implements SmsService`。

3. 写代理类 `SmsProxy implements SmsService`，构造里注入目标对象，方法里前后加逻辑并转发。

```
public interface SmsService {
String send(String message);
}

public class SmsServiceImpl implements SmsService {
@Override public String send(String message) {
System.out.println("send message: " + message);
return message;
}
}

public class SmsProxy implements SmsService {
private final SmsService target;
public SmsProxy(SmsService target) { this.target = target; }

@Override public String send(String message) {
System.out.println("before send()");
String result = target.send(message);
System.out.println("after send()");
return result;
}
}
```

痛点非常明显：

- **代理类爆炸**：每一个目标接口/类都要写一份代理，10 个 Service 就是 10 个 Proxy，重复度极高。

- **接口变更成本高**：接口新增一个方法，目标类和所有代理类都得跟着加，改一处动全身。

- **横切逻辑分散**：日志逻辑复制粘贴 N 份，改一次就得挨个改。

正因为这些痛点，才有了运行时才生成代理类的**动态代理**。

追问 静态代理现在还有实际使用场景吗？

有，但很少见。一般是**代理逻辑非常轻、只有一两个类要代理、并且希望编译期就能看到全部实现**的场景 —— 比如给某个 SDK 加一层薄薄的包装、或者做单元测试时手写一个假实现。Java 标准库里 `Collections.synchronizedList()` 返回的其实就是一种静态代理（同步包装类）。绝大部分业务场景，都被动态代理取代了。

## 面试场景 3：JDK 动态代理怎么写？⭐核心

🎤 面试官

手撕一下 JDK 动态代理，把 `Proxy` 和 `InvocationHandler` 都用上。

🧑‍💻 你

核心两个类，都在 `java.lang.reflect` 包下：

- `Proxy`：静态方法 `newProxyInstance(...)` 生成代理对象。

- `InvocationHandler`：函数式接口，只有一个 `invoke(Object proxy, Method method, Object[] args)`，代理对象的**所有方法调用**都会被路由到这里。

`Proxy.newProxyInstance()` 三个参数：

1. `ClassLoader loader`：由哪个类加载器加载生成的代理类，一般传目标类的 ClassLoader。

2. `Class<?>[] interfaces`：代理类要实现哪些接口。

3. `InvocationHandler h`：所有方法调用的回调。

标准写法：

```
public class DebugInvocationHandler implements InvocationHandler {
private final Object target;
public DebugInvocationHandler(Object target) { this.target = target; }

@Override
public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
System.out.println("before " + method.getName());
Object result = method.invoke(target, args);        // 反射调用真实对象
System.out.println("after " + method.getName());
return result;
}
}

public class JdkProxyFactory {
@SuppressWarnings("unchecked")
public static <T> T getProxy(T target) {
return (T) Proxy.newProxyInstance(
target.getClass().getClassLoader(),
target.getClass().getInterfaces(),
new DebugInvocationHandler(target));
}
}

// 使用
SmsService proxy = JdkProxyFactory.getProxy(new SmsServiceImpl());
proxy.send("hello");
// 输出：
// before send
// send message: hello
// after send
```

关键限制一句话：**JDK 动态代理只能代理实现了接口的类**，因为生成的代理类是「实现了那些接口的兄弟类」，不是「目标类的子类」。目标类没有接口就没法「用同一种类型接住代理对象」。

追问 为什么 `InvocationHandler.invoke` 里要用 `method.invoke(target, args)`，而不是 `method.invoke(proxy, args)`？

**因为传 `proxy` 会无限递归 StackOverflow！** `proxy` 就是代理对象本身，对它再调 `method` 又会回到 `invoke`，永远出不去。必须传**目标对象 `target`**，让反射调用真正的原始实现。`invoke` 的第一个参数 `proxy` 一般*只用于判断/日志*（例如判断代理是不是同一个），几乎不会拿来调方法。

追问 MyBatis 的 Mapper 只有接口，没有实现类，方法调用是怎么落地到 SQL 的？

典型的 JDK 动态代理应用。MyBatis 在初始化时用 `MapperProxyFactory` 为每个 Mapper 接口生成一个 `MapperProxy`（`implements InvocationHandler`）。你调 `userMapper.findById(1L)`，其实调的是代理对象，`invoke` 里根据 `Method` 拿到对应的 `MappedStatement`（就是 XML 里那条 SQL 或注解上的 SQL），交给 `SqlSession` 执行、把 `ResultSet` 映射成对象返回。所以「接口没实现类也能调」的魔法，就是动态代理 + SQL 解析。

## 面试场景 4：JDK 动态代理的原理是什么？⭐字节码层面

🎤 面试官

`Proxy.newProxyInstance` 返回的到底是什么？能不能看到它长什么样？

🧑‍💻 你

返回的是一个**运行时生成的类的实例**，类名形如 `com.sun.proxy.$Proxy0`（0、1、2 依次递增）。这个类在磁盘上原本不存在，是 JDK 内部的 `ProxyGenerator` 通过拼字节码**在内存里生成 `byte[]`**，再交给 `defineClass` 加载到 JVM 的。

它长这样（伪代码）：

```
public final class $Proxy0 extends Proxy implements SmsService {
private static Method m3;   // SmsService.send 的 Method 对象
// 还有 m0(hashCode), m1(equals), m2(toString) ...

public $Proxy0(InvocationHandler h) { super(h); }

public final String send(String arg0) {
try {
return (String) super.h.invoke(this, m3, new Object[]{ arg0 });
} catch (RuntimeException | Error e) { throw e; }
catch (Throwable e) { throw new UndeclaredThrowableException(e); }
}
// hashCode / equals / toString 同理，也走 h.invoke
static {
m3 = Class.forName("SmsService").getMethod("send", String.class);
// ...
}
}
```

关键点：

1. **继承 `java.lang.reflect.Proxy`**：这是为什么 JDK 动态代理只能实现接口 —— Java 单继承，代理类已经继承了 `Proxy`，就没法再继承业务目标类。

2. **实现你传入的所有接口**：每个接口方法在代理类里都被覆写，方法体统一是「把调用打包成 `(this, Method, args)` 交给 `InvocationHandler`」。

3. **方法调用即回调**：这就是为什么 `invoke` 能拦到所有方法。

想亲眼看字节码？加一个 JVM 参数把生成的类 dump 到磁盘：

```
# JDK 8：
-Dsun.misc.ProxyGenerator.saveGeneratedFiles=true

# JDK 9+：
-Djdk.proxy.ProxyGenerator.saveGeneratedFiles=true
```

然后在项目根目录的 `com/sun/proxy/` 下就能找到 `$Proxy0.class`，用 `javap -p -c` 或 IDEA 反编译看得清清楚楚。

陷阱 生成 `$Proxy0` 的过程是**有开销的**（拼字节码 + `defineClass`），但 `Proxy` 内部有**缓存**（`ProxyClassCache`，Key = ClassLoader + 接口集合），同一组接口只会生成一次代理类。所以「创建代理」的耗时主要发生在第一次，之后都是 `new $Proxy0(handler)`，几乎没成本。这也是为什么 Spring 启动时会「预热」一下所有 Bean 的代理。

## 面试场景 5：CGLIB 动态代理怎么用？原理是什么？⭐核心

🎤 面试官

如果目标类**没有实现接口**，JDK 动态代理不能用了，怎么办？

🧑‍💻 你

用 CGLIB（Code Generation Library）。它基于 **ASM 字节码操作库**，运行时**动态生成一个继承目标类的子类**，然后覆写所有非 `final` 方法，把调用转发给拦截器。

核心两个 API：

- `Enhancer`：CGLIB 的入口，负责生成代理类。`setSuperclass(目标类)` + `setCallback(拦截器)` + `create()`。

- `MethodInterceptor`：拦截器接口，唯一方法 `intercept(Object obj, Method method, Object[] args, MethodProxy methodProxy)`。

标准写法：

```
// 目标类，没有接口
public class AliSmsService {
public String send(String message) {
System.out.println("ali send: " + message);
return message;
}
}

// 拦截器
public class DebugMethodInterceptor implements MethodInterceptor {
@Override
public Object intercept(Object obj, Method method, Object[] args, MethodProxy methodProxy) throws Throwable {
System.out.println("before " + method.getName());
// ★ 用 methodProxy.invokeSuper() 而不是 method.invoke()：
//    invokeSuper 走 CGLIB 优化过的 FastClass 索引，比反射快得多
Object result = methodProxy.invokeSuper(obj, args);
System.out.println("after " + method.getName());
return result;
}
}

// 工厂
public class CglibProxyFactory {
public static Object getProxy(Class<?> clazz) {
Enhancer enhancer = new Enhancer();
enhancer.setClassLoader(clazz.getClassLoader());
enhancer.setSuperclass(clazz);
enhancer.setCallback(new DebugMethodInterceptor());
return enhancer.create();
}
}

// 使用
AliSmsService proxy = (AliSmsService) CglibProxyFactory.getProxy(AliSmsService.class);
proxy.send("hello");
```

**原理关键点**：

1. CGLIB 用 ASM 直接编织字节码，生成的类名类似 `AliSmsService$$EnhancerByCGLIB$$abcd1234`。

2. 生成的类是**目标类的子类**，覆写所有非 `final` 方法。

3. 为了避免每次调用都走反射，CGLIB 还会生成一个 `FastClass`：把方法映射成整数索引，`methodProxy.invokeSuper()` 靠索引直接调 `super.xxx()`，比反射快一个数量级。

**限制**：

- `final` 类：无法生成子类，直接抛 `IllegalArgumentException: Cannot subclass final class ...`。

- `final` 方法：子类不能覆写，AOP 静默失效（代理里直接走父类原逻辑，没有拦截）。

- `private` 方法：不被子类继承，同样无法代理。

- 目标类必须有**可访问的无参构造器**（默认 `create()` 会调它），否则要用 `create(argTypes, args)`。

追问 CGLIB 依赖什么库？现在 Spring 里还需要单独引入吗？

CGLIB 依赖 **ASM**（一个非常底层的字节码操作库，能直接读写 `.class`）。Spring 从 3.2 起，把 CGLIB 3 的源码 **repackage 到 `org.springframework.cglib` 包下**并内置了，用户不用手动加依赖 —— 这样也避免了不同版本 CGLIB 的冲突。你在 Spring 里看到的其实是 `spring-core` 里内置的 CGLIB。

追问 CGLIB 为什么不能代理 `final` 方法/类？说得再底层一点。

CGLIB 的整个技术路线是「生成一个子类」。而 `final` 类在 JVM 层面就**禁止被继承**（class 的访问标志里有 `ACC_FINAL`，字节码校验器直接拒绝），`final` 方法在 JVM 层面**禁止被覆写**。所以不是 CGLIB「不想代理」，而是 JVM 根本不让它这么干 —— 强行生成字节码会在 `defineClass` 阶段被校验失败。

## 面试场景 6：JDK 动态代理 vs CGLIB 对比表 ⭐必背

维度JDK 动态代理CGLIB 动态代理

是否需要接口**必须实现接口**不需要接口
实现方式生成实现同一接口的兄弟类（继承 `Proxy`）生成目标类的子类
能否代理 `final` 类/方法不涉及（走接口，无所谓）**不能**（子类无法覆写）
能否代理 `private` 方法不能（接口里没这种东西）不能（子类看不见）
能否代理 `static` 方法不能（静态方法不属于对象）不能（同上）
依赖JDK 自带（`java.lang.reflect`）需要 CGLIB + ASM（Spring 已内置）
底层技术`ProxyGenerator` 拼字节码ASM 字节码 + FastClass 索引
创建代理速度较快较慢（要生成子类 + FastClass）
调用代理方法速度较慢（走反射 `method.invoke`）较快（FastClass 索引直调）
JDK 版本红利JDK 8 之后大幅优化，现代 JDK 里差距很小—
典型场景MyBatis Mapper、RPC Stub、JDK 自带 AOPSpring AOP（尤其 Boot 2.0+）、EasyMock、Hibernate 懒加载

追问 网上说「CGLIB 比 JDK 动态代理快」，你怎么看？

要分场景。**调用阶段**：CGLIB 的 FastClass 走索引直调，历史上比 JDK 动态代理的反射调用快 3~10 倍。但 **JDK 8 之后**，反射被 `MethodAccessor` 优化（超过 15 次调用会生成一个 accessor 直接调用而不走 `native`），差距缩小到几乎可以忽略。**创建阶段**：JDK 动态代理明显更快（不用生成 FastClass）。**结论**：现代 JDK 里两者性能差异很小，选型主要看「有没有接口」而不是性能。

## 面试场景 7：Spring AOP 用了哪种代理？⭐经典追问

🎤 面试官

Spring AOP 底层用的是 JDK 动态代理还是 CGLIB？

🧑‍💻 你

要分版本回答，这是面试官特别喜欢挖的点：

- **Spring 5 / Spring Boot 1.x**：**目标类实现了接口 → JDK 动态代理；没有接口 → 自动 fallback 到 CGLIB。**可以通过 `@EnableAspectJAutoProxy(proxyTargetClass = true)` 强制全部用 CGLIB。

- **Spring Boot 2.0+**：**默认全部用 CGLIB。**配置项 `spring.aop.proxy-target-class` 默认 `true`，可以显式设成 `false` 恢复「有接口用 JDK」的老逻辑。

为什么 Spring Boot 2.0 改成默认 CGLIB？主要有两个原因：

1. **避免类型不一致的坑**：假设一个 `UserServiceImpl implements UserService`，如果被 JDK 代理，代理对象只能用 `UserService` 类型接住，用 `UserServiceImpl` 接会 `ClassCastException`。团队里有人 `@Autowired UserServiceImpl` 就会踩坑。CGLIB 生成的是子类，既能用父类型也能用子类型接住，容错性更高。

2. **Spring Boot 2 主推「按类型注入」+「构造器注入」**：这套用法下强类型子类代理更自然，不需要每个类都硬拆一个接口。

另一个常识：**Spring 事务（`@Transactional`）本质也是 AOP**，所以事务代理跟 Spring AOP 的策略完全一致。你在 Spring Boot 2.x 里看到的 `UserService$$EnhancerBySpringCGLIB$$xxx` 就是这么来的。

追问 强制走 CGLIB 之后，如果目标类是 `final` 或方法是 `final`，会发生什么？

启动时就报错：`Cannot subclass final class ...`；或者类是普通类但某个方法被 `final` 修饰，CGLIB 不会报错，但那个 `final` 方法上的切面（比如 `@Transactional`）会**静默失效**。所以在 Spring 项目里，Service 类和被切的方法都**不要加 `final`**。Kotlin 用户尤其容易踩这个坑 —— Kotlin 类默认 `final`，得加 `open` 关键字或用 `kotlin-spring` 插件自动打开。

## 面试场景 8：代理失效场景 ⭐高频陷阱

🎤 面试官

`@Transactional` 在实际项目中经常「莫名其妙」失效，你能列几个常见原因吗？

🧑‍💻 你

代理失效的本质：**调用没有走代理对象**。常见五种：

1. **同类内部调用（最经典）**：`this.internalMethod()`。`this` 指向的是**原始对象**，不是代理对象，切面被彻底绕过。举个例子：

```
@Service
public class OrderService {
public void create() {
// ❌ this.save() 走的是原始对象，@Transactional 不生效
this.save();
}
@Transactional
public void save() { /* ... */ }
}
```

解法：注入自己（`@Autowired OrderService self;`）、或者用 `((OrderService) AopContext.currentProxy()).save()`（要开 `exposeProxy=true`）、或者拆两个类。

2. **方法不是 `public`**：Spring 事务默认只切 `public` 方法。`private`/`protected`/包私有方法上的 `@Transactional` 是纯粹的注释。

3. **方法/类是 `final`**：CGLIB 子类覆写不了，切面静默失效（上一题已讲）。

4. **异常被吞掉**：`catch` 住 `Exception` 又没抛出去，事务觉得「一切正常」，不会 rollback。或者抛的是 *受检异常*，而 `@Transactional` 默认只对 `RuntimeException` 和 `Error` 回滚 —— 要 `@Transactional(rollbackFor = Exception.class)`。

5. **目标对象根本没被 Spring 管理**：`new OrderService()` 出来的对象没走容器，压根没被代理。

陷阱 同类调用失效不是 Spring 的 bug，而是**代理模式本身的天然限制**：JDK/CGLIB 生成的代理类只是「包了目标对象」，目标对象里的 `this` 永远指向自己。要「代理感知」内部调用只能靠 AspectJ 编译期/加载期织入（`ltw`），把切面直接编织进目标类的字节码 —— 那就不是 Spring AOP 的运行时代理了。

## 面试场景 9：CGLIB 通过什么实现字节码增强？

🧑‍💻 你

CGLIB 底层依赖 **ASM**（原名 Objectweb ASM）。ASM 是一个直接读写 `.class` 字节流的库，几乎和 JVM 规范一一对应，能力最低也最强 —— 你能读到每一条 `invokevirtual`，也能亲手拼一条 `iconst_3`。

CGLIB 在 ASM 之上封装了几个高层 API：

- `Enhancer`：生成继承目标类的子类。

- `MethodInterceptor` / `Callback`：拦截逻辑。

- `FastClass`：为目标类和代理类都生成一个「方法索引表」，`invoke(int index, Object obj, Object[] args)` 靠 switch-case 直调，绕开反射。

- `BeanCopier`、`KeyFactory`、`Mixin`：常用工具。

类似的字节码库还有 **Javassist**（API 更 Java 化，接近源码级别，写起来舒服但性能弱一点；Dubbo 老版本、Hibernate 都用过）、**Byte Buddy**（现代化 API、性能好，Mockito、Hibernate 5+、Skywalking Agent 都在用）。ASM 是三者里最底层、最快、门槛最高的那个。

追问 Hibernate 懒加载为什么也用 CGLIB？

Hibernate 的懒加载对象需要「你以为拿到的是 `Order`，实际上是一个占位子类，直到你真的访问它的字段才去查数据库」。这天然是「无接口 + 需要子类拦截 getter」的场景，CGLIB 完美契合。所以 `order.getUser().getName()` 的第二个点才会真正触发 SQL。

## 面试场景 10：动态代理的性能对比

🎤 面试官

动态代理有性能开销吗？多大？

🧑‍💻 你

有，但要分成**「创建代理」**和**「调用代理方法」**两个阶段单独看：

阶段直接调用JDK 动态代理CGLIB

创建代理无快（有缓存）慢（生成子类 + FastClass，首次尤其明显）
调用一次方法基线（约 1~2 ns）~10-20 ns（JDK 8+ 反射优化后与 CGLIB 接近）~5-10 ns（FastClass 索引直调）
JMH 数量级1约 5-10 倍慢约 3-5 倍慢

关键结论：

1. 「慢 5 倍」听起来吓人，但基数只有几纳秒 —— 对于绝大部分业务方法（内部还要查数据库、调 RPC，耗时毫秒级），代理开销可以忽略不计。

2. **反射有一次性预热成本**：前 15 次左右 `method.invoke` 走 native 桥接较慢，之后 JDK 会生成 `MethodAccessor` 变成 Java 直接调用，快很多。`setAccessible(true)` 也能省掉每次的访问检查。

3. **MethodHandle（JDK 7+）**：另一种更接近底层调用的机制，创建慢但调用极快，JDK 8 的 `LambdaMetafactory` 就基于它。有些高性能框架（Dubbo、Netty、Log4j2）会用 `MethodHandle` 代替反射。

4. 要真的想优化：**把代理创建移到启动期**（Spring 已经这么做）、**缓存 `Method`/`MethodHandle`**、**热点场景用编译期织入（AspectJ ltw）**。

追问 如果我一个接口调用被切了 5 个切面（日志 + 事务 + 缓存 + 权限 + 监控），会不会性能爆炸？

不会。Spring AOP 在启动时把匹配同一 join point 的所有 Advisor 组成一个**责任链（Interceptor Chain）**，运行时只是一次代理调用 + 一路链式 `proceed()`，没有 N 层代理嵌套。每个切面的开销就是一次普通方法调用 + 一次 `if` 判断，总开销依然可以忽略。真正需要担心的是**切面里干了重活**（比如同步写日志到磁盘、切面里查数据库），那是切面自己的问题，不是代理的问题。

## 💻 代码验证（打开 IDE 跑一遍）

### 验证 1：手撕 JDK 动态代理

```
import java.lang.reflect.*;

public class JdkProxyDemo {

interface SmsService {
String send(String message);
}

static class SmsServiceImpl implements SmsService {
@Override public String send(String message) {
System.out.println("  [real] send: " + message);
return "OK:" + message;
}
}

static class DebugHandler implements InvocationHandler {
private final Object target;
DebugHandler(Object target) { this.target = target; }

@Override
public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
System.out.println("[before] " + method.getName() + " args=" + java.util.Arrays.toString(args));
long t0 = System.nanoTime();
Object result = method.invoke(target, args);   // ★ 注意是 target，不是 proxy
System.out.println("[after ] " + method.getName() + " cost=" + (System.nanoTime() - t0) + "ns");
return result;
}
}

public static void main(String[] args) {
SmsService raw = new SmsServiceImpl();
SmsService proxy = (SmsService) Proxy.newProxyInstance(
raw.getClass().getClassLoader(),
raw.getClass().getInterfaces(),
new DebugHandler(raw));

System.out.println("代理类: " + proxy.getClass().getName());   // com.sun.proxy.$Proxy0
System.out.println("是接口的实例吗? " + (proxy instanceof SmsService));
System.out.println("是实现类的实例吗? " + (proxy instanceof SmsServiceImpl));   // false！
proxy.send("hello");
}
}
// 输出：
// 代理类: com.sun.proxy.$Proxy0
// 是接口的实例吗? true
// 是实现类的实例吗? false      ← JDK 代理和目标类之间没有继承关系
// [before] send args=[hello]
//   [real] send: hello
// [after ] send cost=XXXXns
```

加参数 `-Djdk.proxy.ProxyGenerator.saveGeneratedFiles=true` 启动，运行完就能在项目根目录 `com/sun/proxy/$Proxy0.class` 看到生成的字节码。

### 验证 2：手撕 CGLIB MethodInterceptor

```
// 需要引入：org.springframework:spring-core（自带 CGLIB），或直接依赖 cglib:cglib
import org.springframework.cglib.proxy.Enhancer;
import org.springframework.cglib.proxy.MethodInterceptor;
import org.springframework.cglib.proxy.MethodProxy;
import java.lang.reflect.Method;

public class CglibProxyDemo {

// 注意：没有接口，纯普通类
public static class AliSmsService {
public String send(String message) {
System.out.println("  [real] ali send: " + message);
return "OK:" + message;
}
// final 方法故意留个坑，看它是否会被拦截
public final String sendFinal(String m) {
System.out.println("  [real-final] " + m);
return m;
}
}

static class DebugInterceptor implements MethodInterceptor {
@Override
public Object intercept(Object obj, Method method, Object[] args, MethodProxy methodProxy) throws Throwable {
System.out.println("[before] " + method.getName());
Object result = methodProxy.invokeSuper(obj, args);   // ★ FastClass 索引直调 super
System.out.println("[after ] " + method.getName());
return result;
}
}

public static void main(String[] args) {
Enhancer enhancer = new Enhancer();
enhancer.setSuperclass(AliSmsService.class);
enhancer.setCallback(new DebugInterceptor());
AliSmsService proxy = (AliSmsService) enhancer.create();

System.out.println("代理类: " + proxy.getClass().getName());
// 输出形如：AliSmsService$$EnhancerBySpringCGLIB$$abcd1234
System.out.println("是目标类的子类吗? " + (proxy instanceof AliSmsService));   // true

proxy.send("hello");           // 会打印 before/after
proxy.sendFinal("hello");      // ⚠ final 方法：不会打印 before/after，切面静默失效
}
}
```

### 验证 3：Spring AOP 里 `this` 调用失效

```
@Service
public class OrderService {

// 外部调用能进事务
@Transactional
public void createOrder(Order o) {
orderMapper.insert(o);
// ❌ 这里的 this 是原始对象，saveDetail 上的 @Transactional 不会重新走事务传播
this.saveDetail(o);
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
public void saveDetail(Order o) {
detailMapper.insert(o.getDetail());
// 期待新事务，实际上还在外层事务里
}
}

// 正确写法一：注入自己
@Service
public class OrderService {
@Autowired private OrderService self;
public void createOrder(Order o) {
orderMapper.insert(o);
self.saveDetail(o);   // ✅ 走代理对象
}
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void saveDetail(Order o) { /*...*/ }
}

// 正确写法二：AopContext（需要 @EnableAspectJAutoProxy(exposeProxy = true)）
((OrderService) AopContext.currentProxy()).saveDetail(o);
```

### 验证 4：观察 Spring Boot 里的代理类型

```
@RestController
public class DebugController {
@Autowired private OrderService orderService;

@GetMapping("/debug/proxy")
public String showProxy() {
return "class = " + orderService.getClass().getName()
+ ", isJdkProxy = " + java.lang.reflect.Proxy.isProxyClass(orderService.getClass())
+ ", isCglibProxy = " + orderService.getClass().getName().contains("$$");
}
}
// Spring Boot 2.x 默认输出：
//   class = com.example.OrderService$$EnhancerBySpringCGLIB$$e1a2b3c4
//   isJdkProxy = false
//   isCglibProxy = true
//
// 在 application.yml 加：spring.aop.proxy-target-class: false
// 且 OrderService 实现了接口时，输出会变成：
//   class = com.sun.proxy.$Proxy123
//   isJdkProxy = true
```

## 🧠 自测

Self-Quiz · 合上课件再答

<details>

<summary>Q1 用一句话总结代理模式的核心价值。</summary>

在**不修改目标类源码**的前提下，通过一个中间对象拦截方法调用，在方法前后**织入横切逻辑**（日志、事务、权限、缓存、限流、RPC 转发等）。

</details>

<details>

<summary>Q2 JDK 动态代理和 CGLIB 各自的核心限制是什么？</summary>

JDK 动态代理：**目标类必须实现接口**（因为生成的代理类已经继承了 `Proxy`，用不了单继承名额去继承目标类）。CGLIB：**不能代理 `final` 类和 `final`/`private`/`static` 方法**（子类无法覆写）。两者都无法代理 static。

</details>

<details>

<summary>Q3 `InvocationHandler.invoke(Object proxy, Method m, Object[] args)` 里，反射调用应该传 `proxy` 还是 `target`？为什么？</summary>

必须传 `target`。传 `proxy` 会无限递归 —— 对代理对象再调这个方法又会回到 `invoke`，最终 `StackOverflowError`。`proxy` 参数一般只用来做判断/日志。

</details>

<details>

<summary>Q4 Spring Boot 2.0+ 默认用哪种代理？为什么改的？</summary>

默认 CGLIB（`spring.aop.proxy-target-class=true`）。改的原因：**避免 JDK/CGLIB 混用导致的类型不一致**（比如同事 `@Autowired UserServiceImpl` 会 `ClassCastException`）；CGLIB 生成子类，父类型和子类型都能接住代理对象，容错性更高。

</details>

<details>

<summary>Q5 `@Transactional` 失效的五大常见原因？</summary>

1. 同类内部调用（`this.xxx()` 不走代理）；

2. 方法不是 `public`；

3. 方法/类是 `final`（CGLIB 覆写不了，静默失效）；

4. 异常被 `catch` 吞掉，或抛的是受检异常而没配 `rollbackFor`；

5. 对象不是 Spring 容器托管（`new` 出来的没被代理）。

</details>

#### 📖 原文（先读一遍，再回看本课件效果最好）

-  —— 本课主源

- JDK 21 · `java.lang.reflect.Proxy` API —— JDK 动态代理官方文档

- Spring Reference · AOP Proxying —— Spring 里 JDK vs CGLIB 选择规则

- CGLIB Wiki —— CGLIB 与 ASM 的关系

#### 🔗 关联课件

-  —— 动态代理的基础（`method.invoke` 就在这一层）

-

-  —— Spring 里 AOP 的完整链路

-  —— `@Transactional` 失效的完整案例分析

#### 🧭 下一课预告

Lesson 0008：**SPI 机制 & Java 序列化 & 语法糖** —— 覆盖 ServiceLoader、Dubbo SPI、Serializable 的坑、以及 `foreach`/`try-with-resources`/`switch expression` 这些语法糖的字节码真面目。

💬 有任何疑问 ——「Spring 里怎么手动拿到代理对象？」「Kotlin 里怎么写才能不踩 CGLIB 的 final 坑？」「Dubbo 的 Invoker 用的是哪种代理？」—— 直接问我。我是你的老师，也是你的追问陪练。


