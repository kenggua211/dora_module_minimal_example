# Dora-rs Module System: Minimum Example Implementation

## 背景与目标

我们正在为 dora-rs 设计一个 **module 系统**，目标是让用户能够将一组 dora 节点打包成可复用的子图（module），通过声明式的方式嵌入到更大的 dataflow 中，类似于编程语言里的函数封装。

这个任务是实现一个 minimum example，验证这套机制的可行性。

---

## 核心概念

### Module 系统的设计逻辑

module 是一个**可展开的子图声明**，它有：

- 声明对外暴露的 inputs 和 outputs（边界接口）
- 内部的若干 dora 节点和它们之间的连接关系
- 内部节点之间的引用使用**相对引用**（不带命名空间前缀）

展开时预处理器做两件事：

1. 所有内部节点 ID 加上 `namespace/` 前缀，例如 `costmap` 变成 `nav/costmap`
2. 把 module 的 inputs/outputs 替换成用户在 `dataflow.yml` 里声明的实际连接

展开结果是一个标准的 dora dataflow yaml，对 dora 运行时完全透明，**dora 不需要知道 module 存在过**。

### 安全约束

module 内部节点的 outputs 只能流向：

- 其他内部节点
- module 声明的 outputs 列表中的接口

不允许内部节点直接写全局 channel，否则攻击者可以通过提供恶意 module 向外部图注入数据（例如直接输出 `cmd_vel` 绕过主控节点）。预处理器在展开阶段必须做这项静态校验，校验失败则拒绝展开并报错。

---

## 需要创建的文件

### 文件结构

```
project/
├── minimum_test.module.yml   # module 定义
├── dataflow.yml              # 用户侧 dataflow
├── compose.py                # 预处理器脚本
├── source_node.py            # source 算子
├── node_a.py                 # module 内部第一个算子
├── node_b.py                 # module 内部第二个算子
└── sink_node.py              # sink 算子
```

---

### 文件 1：`minimum_test.module.yml`

一个最小的 module 定义，包含：

- module 名称
- 对外暴露的 inputs 列表（1个：`data_in`）
- 对外暴露的 outputs 列表（1个：`data_out`）
- 内部 2 个节点：
  - `node_a`：消费 module 的 input，把数据加 1，输出中间结果
  - `node_b`：消费 `node_a` 的输出，把数据乘 2，产生 module 的 output
- 内部节点使用**相对引用**互相连接

格式示例：

```yaml
module: minimum_test
inputs:
  - data_in
outputs:
  - data_out

nodes:
  - id: node_a
    path: node_a.py
    inputs:
      data_in: module/data_in        # 相对引用：绑定到 module 的 input
    outputs:
      - intermediate

  - id: node_b
    path: node_b.py
    inputs:
      intermediate: node_a/intermediate   # 相对引用：引用内部节点
    outputs:
      - data_out                           # 绑定到 module 的 output
```

> 注意：具体的 dora dataflow yaml 语法以 dora-rs 官方文档或仓库 examples 为准，上面是示意格式，实现时需要对照实际语法调整。

---

### 文件 2：`dataflow.yml`

用户侧的 dataflow 定义，包含：

- 一个 `source` 节点：每秒产生一个递增的整数
- 引入 `minimum_test.module.yml` 作为 module，namespace 为 `test_module`
- 把 `source` 的输出连接到 module 的 `data_in`
- 一个 `sink` 节点：接收 module 的 `data_out` 并打印

格式示例：

```yaml
nodes:
  - id: source
    path: source_node.py
    outputs:
      - number

  - id: sink
    path: sink_node.py
    inputs:
      result: test_module/data_out

modules:
  - id: test_module
    source: minimum_test.module.yml
    inputs:
      data_in: source/number
    outputs:
      data_out: sink/result
```

---

### 文件 3：`compose.py`

预处理器脚本，逻辑如下：

**输入**：`dataflow.yml`
**输出**：`composed.yml`（标准 dora dataflow yaml，可直接被 `dora run` 运行）

处理步骤：

1. 读取 `dataflow.yml`，解析 `modules` 字段
2. 对每个 module 实例：
   a. 读取对应的 `.module.yml` 文件
   b. **安全校验**：遍历所有内部节点的 outputs，确认每个 output 要么流向其他内部节点，要么是 module 声明的 outputs 列表中的接口。发现违规则报错退出，打印具体的违规节点和 channel 名称
   c. **命名空间展开**：给所有内部节点 ID 加上 `<module_id>/` 前缀
   d. **相对引用替换**：把内部节点之间的相对引用也加上相同前缀，例如 `node_a/intermediate` 变成 `test_module/node_a/intermediate`
   e. **边界绑定**：把 module 的 inputs/outputs 替换成 `dataflow.yml` 中声明的实际连接
3. 把展开后的节点合并进 `dataflow.yml` 原有的 `nodes` 列表
4. 删除 `modules` 字段（运行时不需要它）
5. 写出 `composed.yml`

**多实例支持**：如果同一个 module 被实例化两次（不同的 `id`），两套节点的前缀不同，不会互相干扰。

---

### 文件 4：算子 Python 文件

按照 dora-rs 标准 Python operator 写法实现以下四个文件：

**`source_node.py`**
每秒产生一个递增整数，从 0 开始，持续输出到 `number` channel。

**`node_a.py`**
接收 `data_in`，将数值加 1，输出到 `intermediate`。

**`node_b.py`**
接收 `intermediate`，将数值乘 2，输出到 `data_out`。

**`sink_node.py`**
接收 `result`，打印收到的值和时间戳。

预期输出示例（source 产生 0, 1, 2, 3...）：

```
[sink] received: 2   # (0+1)*2
[sink] received: 4   # (1+1)*2
[sink] received: 6   # (2+1)*2
[sink] received: 8   # (3+1)*2
```

---

## 验证方式

```bash
# 第一步：展开 module，生成 composed.yml
python compose.py

# 第二步：检查 composed.yml，确认内容符合预期
#   - 应该包含 source、test_module/node_a、test_module/node_b、sink 四个节点
#   - 不应该包含 modules 字段
#   - 所有节点引用应该是完整路径，没有相对引用

# 第三步：运行数据流
dora run composed.yml
```

---

## 注意事项

- 所有文件路径使用相对路径
- `compose.py` 输出的 `composed.yml` 要能直接被 `dora run` 运行，不需要任何额外修改
- module 内部节点的相对引用格式需要和 dora 标准节点引用格式保持一致，展开后不能有格式错误
- 如果不确定 dora 当前版本的 dataflow yaml 格式，先查阅 dora-rs 官方文档（https://dora-rs.ai）或查看 dora 仓库中的 `examples/` 目录
- Python 算子的写法参考 dora-rs 官方 Python API 文档，确保使用当前版本的正确 API
- 使用uv 进行环境管理和包管理，不许使用pip。
- 将执行过的所有cli命令都写入 command.md， 确保操作路径可追溯

---

## 背景参考：为什么需要 Module 系统

dora-rs 目前没有原生的子图复用机制。用户如果想复用一组节点（例如一套导航算法由 costmap、planner、controller、coordinator 四个节点组成），只能手动把所有节点和边复制粘贴到自己的 dataflow 中，并手动处理命名冲突。

Module 系统通过编译时展开解决这个问题：

- **对用户**：引入一个 module 只需要声明 inputs/outputs 绑定，不需要了解内部结构
- **对运行时**：展开后的图和手写没有任何区别，零运行时开销
- **对安全性**：展开阶段的静态校验可以阻止恶意 module 向外部图注入数据

这个 minimum example 的目标是验证展开机制本身的可行性，为后续更复杂的实现（多级嵌套 module、module 包管理）打基础。
