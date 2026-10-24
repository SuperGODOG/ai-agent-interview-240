# AI Infra · 高性能算子、分布式并行、投机解码与大模型量化面试题索引

> **分类描述**: 涵盖 TensorFlow/PyTorch 算子适配与交付、CUDA Graph/TP 融合通信挂死定位、Triton/CuTe DSL 选型、MoE/Router 并行数据流、滑动窗口 Attention 确定性反向优化 (dQ)、国产 GPU 算子 Benchmark 与互联通信 Profiling、投机解码（EAGLE3/DFlash/DSpark、Tree Attention Mask、拒绝采样保分布、长文本与单卡瓶颈）及大模型量化（AWQ/GPTQ/SmoothQuant、FP8 缩放、Router 保留 BF16 精度敏感性）。
> **题目统计**: 共 31 题（基础 Infra 9 题 + 投机解码 17 题 + 模型量化 5 题）
> **唯一语料数据源**: `agent-project-grill/references/题库/items.json`

## 一、算子开发、分布式通信与硬件架构（9 题）

| 题目 ID | 行号 | 深度 | 标签 | 题目简述 |
|---|---|---|---|---|
| `L599` | 599 | L3 | TensorFlow算子/工程交付 | 团队职责、上下游交付与算子场景：你在过去的团队中具体负责什么、算子研发工作的交付对象是谁（算法研究员、训练框架团队或线上推理部署团队）？定制的 TensorFlow 算子适配面向什么业务或模型场景？算子的输入输出规范、内存管理、性能收益与正确性验收流水线应如何设计？ |
| `L600` | 600 | L4 | CUDA Graph/Tensor Parallelism/通信挂死 | CUDA Graph 与 TP 融合通信卡死定位：在大模型训练/推理开启 CUDA Graph 且 TP > 1 时出现进程死锁/卡死（Hang），为什么关闭 Graph 或将 TP 降为 1 现象消失只是“定位线索”而非“根因结论”？如何通过变量矩阵与 Profiler/Trace 工具逐步排查至融合通信算子？通信状态标记（flag）存放在何处、为何选用浮点类型、其内存一致性与同步协议在原实现中如何设计？修复后如何通过最小复现用例与模型级端到端回归进行验证？ |
| `L601` | 601 | L3 | Kernel选型/Triton/CuTe | 算子开发工具选型：在现代 AI 基础设施与大模型算子研发中，原生 CUDA C++、OpenAI Triton 与 NVIDIA CuTe DSL（CUTLASS 提供的 Python 前端/元编程 DSL）各自的适用场景与设计权衡是什么？请从底层控制粒度、具体算子需求（如 Fused Pointwise vs GEMM/Attention）、团队协作效率（算法工程师与底层系统工程师协同）及工程可维护性展开对比。 |
| `L602` | 602 | L4 | MoE/Router Replay/Expert Parallelism | MoE 前向数据流、Router Replay 与并行通信：一个 Token 进入混合专家模型（MoE）后的完整前向流程是什么（Gate 选路、Top-K 分配、Token Dispatch、专家计算与 Combine 汇聚）？在 Rollout 阶段记录的 Token、Layer、Top-K 路由（Router Replay）信息是在训练侧哪个具体环节被恢复与消费的？分布式训练中 Expert Parallelism (EP) 与 Tensor Parallelism (TP) 作为逻辑切分轴，其进程分组与实际通信实现（如 All-to-All、AllGather、Reduce-Scatter 等）有何不同？ |
| `L603` | 603 | L4 | Attention反向/确定性计算/dQ累加 | 滑动窗口 Attention (SWA) 确定性反向传播优化与 dQ 累加：在 SWA 反向计算中，梯度 dQ 的累加等待开销来自哪里？如何通过收敛同步范围（如从全局同步下沉到局部/Tile 级）并调整执行顺序使独立的计算链重叠并行？多线程块并发 atomicAdd 累加 dQ 时，浮点加法的非结合性在何种条件下会导致跨运行 bitwise 结果漂移？优化后如何通过严格测试保证数值正确性与确定性边界？ |
| `L604` | 604 | L3 | GPU Benchmark/国产加速卡 | 国产 AI 加速卡算子 Benchmark 与多基线对齐评测方法论：在国产 GPU / AI 加速卡上对自研或适配算子进行性能评测时，如何设计严谨的 Benchmark 测试矩阵（涵盖不同 Shape、Batch Size、Sequence Length 与 Dtype）？为了消除评测偏差，Warmup 次数、计时方式（如硬件 Event 同步 vs CPU 计时）、Stream 同步与 CUDA Graph/执行图配置应如何标准化？如何与芯片厂商高性能库、旧有开源实现及自写 Kernel 进行同语义、公平基线（Fair Baseline）的对比？ |
| `L605` | 605 | L4 | 硬件架构/显存带宽/通信拓扑 | AI 加速卡硬件架构、显存带宽瓶颈与多卡互联通信 Profiling：面对未知或新型号的 AI 加速卡，如何系统化查证与度量其硬件核心指标（计算核心数、Tensor Core/专用矩阵单元峰值算力、寄存器堆、Shared Memory/L1/L2 缓存层次与容量、HBM 理论峰值带宽）？如何通过带宽测试（Bandwidth Test）测量实际显存带宽与卡间互联（如 PCIe vs 自研/专有互联）带宽？在分布式作业中，如何使用 Profiling 工具区分一个任务是计算受限（Compute-bound）、访存受限（Memory-bound）还是通信受限（Communication-bound）？ |
| `L300` | 300 | LNone | - | 混合专家模型（MoE）与传统稠密（Dense）Transformer 架构的核心区别和优缺点是什么？ |
| `L229` | 229 | LNone | - | 线上大模型服务是否有应用Continuous Batching、KV Cache Manager（如PagedAttention）等优化机制？ |

## 二、投机解码专项：EAGLE3、DFlash、DSpark、树状验证与采样（17 题）

| 题目 ID | 行号 | 深度 | 标签 | 题目简述 |
|---|---|---|---|---|
| `L629` | 629 | L3 | 投机解码/草稿架构选型 | EAGLE3、DFlash、DSpark三者的区别是什么？ |
| `L630` | 630 | L4 | 投机解码/推理引擎接入流程 | DFlash / DSpark在实际推理时需要哪些输入？接入vLLM / SGLang，整体流程是什么？ |
| `L631` | 631 | L3 | 投机解码/KV Cache维护机制 | EAGLE3需要维护KV Cache，那么DFlash、DSpark需要吗？ |
| `L632` | 632 | L4 | 投机解码/Hidden States与KV复用 | Target Model在推理过程中产生的Hidden States / KV Cache，DFlash、DSpark是怎么利用的？ |
| `L633` | 633 | L4 | 投机解码/MoE架构显存与算力制约 | 为什么MoE模型做Speculative Decoding时，加速收益不能像Dense Model一样随着一次Verify的Token数增加而近似线性提升？ |
| `L634` | 634 | L3 | 投机解码/EAGLE3三阶段流程 | EAGLE3的Proposal → Verify → Accept三个阶段分别是怎么做的？ |
| `L635` | 635 | L4 | 投机解码/动态树生成与剪枝 | EAGLE3的Proposal阶段是怎么生成Tree的？如何控制Tree不无限膨胀？ |
| `L636` | 636 | L5 | 投机解码/Tree Attention Mask构造与验证 | Tree Attention Mask是怎么构造的？给定一棵Tree，如何生成对应的Attention Mask？具体用了什么方法，指针吗？Tree Attention得到多个Token的Logits后，怎么判断有多少个Token能被Accept？ |
| `L637` | 637 | L4 | 投机解码/拒绝采样与分布保全 | 采样（非Greedy）模式下，Speculative Decoding怎么通过Rejection Sampling保证最终分布不变？ |
| `L638` | 638 | L2 | 投机解码/Decode加速基本原理 | Speculative Decoding为什么能够加速Decode？ |
| `L639` | 639 | L3 | 投机解码/Memory Bound与算力利用率 | 为什么Decode阶段通常是Memory Bound？一次Verify多个Token为什么能够提高GPU利用率？ |
| `L640` | 640 | L4 | 投机解码/单卡MoE显存带宽瓶颈 | 如果不考虑多GPU通信，只考虑单GPU，为什么MoE的Speculative Decoding加速效率仍可能不如Dense Model？ |
| `L641` | 641 | L3 | 投机解码/长文本挑战与前沿发展 | 除了EAGLE3、DFlash、DSpark，还看过哪些Speculative Decoding相关的新工作？有没有关注超长Context下的Speculative Decoding？ |
| `L642` | 642 | L3 | 投机解码/草稿模型训练与数据规模 | Draft Model是怎么训练的？训练数据从哪里来，规模多大？ |
| `L643` | 643 | L4 | 投机解码/草稿模型训练收敛与早停判据 | Draft Model Training有没有分析Loss曲线？怎么判断训练完成？ |
| `L644` | 644 | L3 | 投机解码/生产环境Benchmark实测 | 你实际Benchmark中DFlash、DSpark、EAGLE3的结果怎么样？ |
| `L645` | 645 | L4 | 投机解码/论文加速比偏差归因 | 你的Benchmark结果为什么和对应Paper的结论不一致？有没有定位具体原因？ |

## 三、大模型量化专项：AWQ、GPTQ、SmoothQuant 与 MoE Router 精度（5 题）

| 题目 ID | 行号 | 深度 | 标签 | 题目简述 |
|---|---|---|---|---|
| `L646` | 646 | L3 | 大模型量化/AWQ与GPTQ核心机理 | AWQ和GPTQ的核心区别是什么？两者分别是怎么做的？ |
| `L647` | 647 | L4 | 大模型量化/AWQ-FP8缩放与校准集 | 你的AWQ-FP8具体怎么选择Scale？Calibration Data在里面起什么作用？ |
| `L648` | 648 | L3 | 大模型量化/误差重构目标与优化函数 | 量化时比较的是Weight Error还是Output Reconstruction Error？为什么？ |
| `L649` | 649 | L3 | 大模型量化/异常值处理与迁移哲学 | SmoothQuant和AWQ的区别是什么？为什么把这两个方法放在一起比较？ |
| `L650` | 650 | L4 | 大模型量化/MoE量化与Router精度敏感性 | MoE Quantization最大的问题是什么？为什么Router往往需要保留BF16？ |
