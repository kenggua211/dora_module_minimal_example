#!/usr/bin/env python3
"""
Dora-rs Module System Preprocessor
Expands module definitions into standard dora dataflow YAML
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, List, Set, Any


class ModuleExpander:
    def __init__(self, dataflow_path: str):
        self.dataflow_path = Path(dataflow_path)
        self.base_dir = self.dataflow_path.parent

    def load_yaml(self, path: Path) -> Dict:
        """Load YAML file"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def save_yaml(self, data: Dict, path: Path):
        """Save YAML file"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def validate_module_security(self, module_def: Dict, module_id: str) -> None:
        """
        安全校验：确保内部节点的 outputs 只能流向内部节点或 module 声明的 outputs
        """
        declared_outputs = set(module_def.get('outputs', []))
        internal_node_ids = {node['id'] for node in module_def.get('nodes', [])}

        # 收集所有内部节点的 inputs，找出哪些 outputs 被内部消费
        consumed_outputs = set()
        for node in module_def.get('nodes', []):
            for input_id, source in node.get('inputs', {}).items():
                if isinstance(source, str) and '/' in source:
                    # 解析 source，格式为 node_id/output_id
                    parts = source.split('/')
                    if len(parts) >= 2 and parts[0] in internal_node_ids:
                        consumed_outputs.add(source)

        # 检查每个节点的 outputs
        for node in module_def.get('nodes', []):
            node_id = node['id']
            outputs = node.get('outputs', [])

            for output in outputs:
                output_ref = f"{node_id}/{output}"

                # 检查这个 output 是否被合法使用
                is_consumed_internally = output_ref in consumed_outputs
                is_module_output = output in declared_outputs

                if not (is_consumed_internally or is_module_output):
                    raise SecurityError(
                        f"Security violation in module '{module_id}': "
                        f"Node '{node_id}' output '{output}' is not consumed internally "
                        f"and not declared in module outputs. "
                        f"This could allow unauthorized data injection."
                    )

    def expand_module(self, module_instance: Dict, dataflow: Dict) -> List[Dict]:
        """
        展开单个 module 实例，返回展开后的节点列表
        """
        module_id = module_instance['id']
        module_source = self.base_dir / module_instance['source']

        # 加载 module 定义
        module_def = self.load_yaml(module_source)

        # 安全校验
        self.validate_module_security(module_def, module_id)

        # 获取 module 的输入输出绑定
        module_inputs = module_instance.get('inputs', {})
        module_outputs = module_instance.get('outputs', [])

        expanded_nodes = []

        for node in module_def.get('nodes', []):
            expanded_node = {
                'id': f"{module_id}__{node['id']}",
                'path': node['path'],
            }

            # 处理 build 字段（如果存在）
            if 'build' in node:
                expanded_node['build'] = node['build']

            # 处理 inputs
            if 'inputs' in node:
                expanded_node['inputs'] = {}
                for input_id, source in node['inputs'].items():
                    if isinstance(source, str):
                        if source.startswith('module/'):
                            # 绑定到 module 的 input
                            module_input_name = source.split('/', 1)[1]
                            if module_input_name in module_inputs:
                                expanded_node['inputs'][input_id] = module_inputs[module_input_name]
                            else:
                                raise ValueError(
                                    f"Module '{module_id}' input '{module_input_name}' not bound"
                                )
                        elif '/' in source:
                            # 内部节点引用，加上命名空间前缀
                            parts = source.split('/', 1)
                            expanded_node['inputs'][input_id] = f"{module_id}__{parts[0]}/{parts[1]}"
                        else:
                            # 直接引用（如 dora/timer）
                            expanded_node['inputs'][input_id] = source
                    else:
                        expanded_node['inputs'][input_id] = source

            # 处理 outputs
            if 'outputs' in node:
                expanded_node['outputs'] = node['outputs']

            expanded_nodes.append(expanded_node)

        return expanded_nodes

    def compose(self, output_path: str = 'composed.yml') -> None:
        """
        主处理流程：展开所有 modules 并生成 composed.yml
        """
        # 加载原始 dataflow
        dataflow = self.load_yaml(self.dataflow_path)

        # 获取现有节点
        composed_nodes = dataflow.get('nodes', []).copy()

        # 展开所有 modules
        if 'modules' in dataflow:
            for module_instance in dataflow['modules']:
                expanded_nodes = self.expand_module(module_instance, dataflow)
                composed_nodes.extend(expanded_nodes)

        # 构建最终的 dataflow
        composed_dataflow = {
            'nodes': composed_nodes
        }

        # 保存结果
        output_file = self.base_dir / output_path
        self.save_yaml(composed_dataflow, output_file)

        print(f"[OK] Module expansion completed: {output_file}")
        print(f"  - Total nodes: {len(composed_nodes)}")
        if 'modules' in dataflow:
            print(f"  - Expanded modules: {len(dataflow['modules'])}")


class SecurityError(Exception):
    """Module security validation error"""
    pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python compose.py <dataflow.yml> [output.yml]")
        sys.exit(1)

    dataflow_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'composed.yml'

    try:
        expander = ModuleExpander(dataflow_path)
        expander.compose(output_path)
    except SecurityError as e:
        print(f"[ERROR] Security Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

