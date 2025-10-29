#!/usr/bin/env python3
"""
YuntuServer 上下文提取脚本
用于提取项目中所有模块的核心上下文信息，包括类、函数、API端点等

用法:
    python scripts/collect_context.py                      # 提取所有模块
    python scripts/collect_context.py User Task            # 提取指定模块
    python scripts/collect_context.py --json               # 输出 JSON 格式
    python scripts/collect_context.py --output context.json # 保存到文件
"""

import os
import sys
import ast
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict


class CodeContextExtractor:
    """代码上下文提取器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.app_dir = self.project_root / "app"
        self.context = {
            "project": "YuntuServer",
            "models": {},
            "services": {},
            "api_routes": {},
            "schemas": {},
            "utils": {},
            "statistics": {
                "total_models": 0,
                "total_services": 0,
                "total_api_endpoints": 0,
                "total_schemas": 0,
            }
        }

    def extract_all(self, filter_modules: Optional[List[str]] = None):
        """提取所有上下文"""
        print("📊 开始提取项目上下文...\n", file=sys.stderr)

        self._extract_models(filter_modules)
        self._extract_services(filter_modules)
        self._extract_api_routes(filter_modules)
        self._extract_schemas(filter_modules)

        self._update_statistics()

        print(f"\n✅ 提取完成！", file=sys.stderr)
        print(f"   - Models: {self.context['statistics']['total_models']}", file=sys.stderr)
        print(f"   - Services: {self.context['statistics']['total_services']}", file=sys.stderr)
        print(f"   - API Endpoints: {self.context['statistics']['total_api_endpoints']}", file=sys.stderr)
        print(f"   - Schemas: {self.context['statistics']['total_schemas']}\n", file=sys.stderr)

        return self.context

    def _should_include_module(self, module_name: str, filter_modules: Optional[List[str]]) -> bool:
        """判断是否应该包含该模块"""
        if not filter_modules:
            return True
        return any(f.lower() in module_name.lower() for f in filter_modules)

    def _extract_models(self, filter_modules: Optional[List[str]] = None):
        """提取 Models"""
        models_dir = self.app_dir / "models"
        if not models_dir.exists():
            return

        print("🔍 提取 Models...", file=sys.stderr)

        for py_file in models_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            if not self._should_include_module(module_name, filter_modules):
                continue

            model_info = self._parse_model_file(py_file)
            if model_info:
                self.context["models"][module_name] = model_info
                print(f"   ✓ {module_name}: {len(model_info.get('classes', []))} 类", file=sys.stderr)

    def _extract_services(self, filter_modules: Optional[List[str]] = None):
        """提取 Services"""
        services_dir = self.app_dir / "services"
        if not services_dir.exists():
            return

        print("🔍 提取 Services...", file=sys.stderr)

        for py_file in services_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            if not self._should_include_module(module_name, filter_modules):
                continue

            service_info = self._parse_service_file(py_file)
            if service_info:
                self.context["services"][module_name] = service_info
                print(f"   ✓ {module_name}: {len(service_info.get('classes', []))} 类, {len(service_info.get('functions', []))} 函数", file=sys.stderr)

    def _extract_api_routes(self, filter_modules: Optional[List[str]] = None):
        """提取 API Routes"""
        api_dir = self.app_dir / "api" / "v1"
        if not api_dir.exists():
            return

        print("🔍 提取 API Routes...", file=sys.stderr)

        for py_file in api_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "router.py":
                continue

            module_name = py_file.stem
            if not self._should_include_module(module_name, filter_modules):
                continue

            route_info = self._parse_api_file(py_file)
            if route_info:
                self.context["api_routes"][module_name] = route_info
                print(f"   ✓ {module_name}: {len(route_info.get('endpoints', []))} 端点", file=sys.stderr)

    def _extract_schemas(self, filter_modules: Optional[List[str]] = None):
        """提取 Schemas"""
        schemas_dir = self.app_dir / "schemas"
        if not schemas_dir.exists():
            return

        print("🔍 提取 Schemas...", file=sys.stderr)

        for py_file in schemas_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            if not self._should_include_module(module_name, filter_modules):
                continue

            schema_info = self._parse_schema_file(py_file)
            if schema_info:
                self.context["schemas"][module_name] = schema_info
                print(f"   ✓ {module_name}: {len(schema_info.get('classes', []))} 模式", file=sys.stderr)

    def _parse_model_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 Model 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            info = {
                "file": str(file_path.relative_to(self.project_root)),
                "classes": [],
                "docstring": ast.get_docstring(tree) or ""
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "fields": [],
                        "relationships": [],
                        "methods": []
                    }

                    # 提取字段和关系
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    field_name = target.id
                                    field_info = {"name": field_name}

                                    # 尝试获取字段类型
                                    if isinstance(item.value, ast.Call):
                                        if hasattr(item.value.func, 'id'):
                                            field_info["type"] = item.value.func.id
                                        elif hasattr(item.value.func, 'attr'):
                                            field_info["type"] = item.value.func.attr

                                    # 判断是关系还是字段
                                    if field_info.get("type") == "relationship":
                                        class_info["relationships"].append(field_info)
                                    else:
                                        class_info["fields"].append(field_info)

                        elif isinstance(item, ast.FunctionDef):
                            if not item.name.startswith("_"):
                                class_info["methods"].append({
                                    "name": item.name,
                                    "docstring": ast.get_docstring(item) or ""
                                })

                    info["classes"].append(class_info)

            return info
        except Exception as e:
            print(f"   ⚠️  解析失败 {file_path.name}: {e}", file=sys.stderr)
            return {}

    def _parse_service_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 Service 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            info = {
                "file": str(file_path.relative_to(self.project_root)),
                "classes": [],
                "functions": [],
                "docstring": ast.get_docstring(tree) or ""
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "methods": []
                    }

                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "docstring": ast.get_docstring(item) or "",
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                                "parameters": [arg.arg for arg in item.args.args]
                            }
                            class_info["methods"].append(method_info)

                    info["classes"].append(class_info)

                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    # 顶层函数
                    func_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "parameters": [arg.arg for arg in node.args.args]
                    }
                    info["functions"].append(func_info)

            return info
        except Exception as e:
            print(f"   ⚠️  解析失败 {file_path.name}: {e}", file=sys.stderr)
            return {}

    def _parse_api_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 API 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            info = {
                "file": str(file_path.relative_to(self.project_root)),
                "endpoints": [],
                "docstring": ast.get_docstring(tree) or ""
            }

            # 查找 router 前缀
            router_prefix = ""
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "router":
                            if isinstance(node.value, ast.Call):
                                for keyword in node.value.keywords:
                                    if keyword.arg == "prefix":
                                        if isinstance(keyword.value, ast.Constant):
                                            router_prefix = keyword.value.value

            # 提取端点
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 检查装饰器
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Attribute):
                            if decorator.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                endpoint_info = {
                                    "method": decorator.attr.upper(),
                                    "function": node.name,
                                    "docstring": ast.get_docstring(node) or "",
                                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                                    "parameters": [arg.arg for arg in node.args.args]
                                }

                                # 尝试获取路径
                                if isinstance(decorator, ast.Attribute) and hasattr(decorator.value, 'id'):
                                    if decorator.value.id == 'router':
                                        # 查找第一个参数作为路径
                                        parent = None
                                        for p_node in ast.walk(tree):
                                            for child in ast.iter_child_nodes(p_node):
                                                if child == decorator:
                                                    parent = p_node
                                                    break

                                        # 简化处理：从函数名推断
                                        endpoint_info["path"] = router_prefix + "/" + node.name.replace("_", "-")

                                info["endpoints"].append(endpoint_info)

            return info
        except Exception as e:
            print(f"   ⚠️  解析失败 {file_path.name}: {e}", file=sys.stderr)
            return {}

    def _parse_schema_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 Schema 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            info = {
                "file": str(file_path.relative_to(self.project_root)),
                "classes": [],
                "docstring": ast.get_docstring(tree) or ""
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "fields": []
                    }

                    # 提取字段（带类型注解）
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            if isinstance(item.target, ast.Name):
                                field_info = {
                                    "name": item.target.id,
                                    "type": ast.unparse(item.annotation) if hasattr(ast, 'unparse') else ""
                                }
                                class_info["fields"].append(field_info)

                    info["classes"].append(class_info)

            return info
        except Exception as e:
            print(f"   ⚠️  解析失败 {file_path.name}: {e}", file=sys.stderr)
            return {}

    def _update_statistics(self):
        """更新统计信息"""
        self.context["statistics"]["total_models"] = sum(
            len(m.get("classes", [])) for m in self.context["models"].values()
        )
        self.context["statistics"]["total_services"] = sum(
            len(s.get("classes", [])) for s in self.context["services"].values()
        )
        self.context["statistics"]["total_api_endpoints"] = sum(
            len(a.get("endpoints", [])) for a in self.context["api_routes"].values()
        )
        self.context["statistics"]["total_schemas"] = sum(
            len(s.get("classes", [])) for s in self.context["schemas"].values()
        )


def main():
    parser = argparse.ArgumentParser(
        description="提取 YuntuServer 项目的代码上下文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/collect_context.py                      # 提取所有模块
  python scripts/collect_context.py User Task            # 仅提取 User 和 Task 相关模块
  python scripts/collect_context.py --json               # 输出 JSON 格式
  python scripts/collect_context.py -o context.json      # 保存到文件
  python scripts/collect_context.py User --pretty        # 美化输出
        """
    )

    parser.add_argument(
        "modules",
        nargs="*",
        help="要提取的模块名称（可选，不指定则提取所有）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式（默认）"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="保存到指定文件"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="美化 JSON 输出"
    )

    args = parser.parse_args()

    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 提取上下文
    extractor = CodeContextExtractor(str(project_root))
    context = extractor.extract_all(filter_modules=args.modules if args.modules else None)

    # 输出结果
    indent = 2 if args.pretty else None
    json_output = json.dumps(context, ensure_ascii=False, indent=indent)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"✅ 已保存到: {output_path}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
