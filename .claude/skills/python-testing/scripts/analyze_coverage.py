#!/usr/bin/env python3
"""
pytest 覆盖率分析脚本
分析覆盖率报告并识别测试缺口
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple


def parse_coverage_report(coverage_file: Path) -> Dict[str, Dict]:
    """
    解析覆盖率报告

    Args:
        coverage_file: 覆盖率文件路径

    Returns:
        包含模块覆盖信息的字典
    """

    if not coverage_file.exists():
        print(f"错误: 覆盖率文件不存在 - {coverage_file}")
        sys.exit(1)

    modules = {}

    with open(coverage_file, 'r', encoding='utf-8') as f:
        current_module = None

        for line in f:
            # 模块名称行 (例如: src/module.py)
            if line.startswith('src/') or line.startswith('src\\'):
                module_name = line.strip()
                current_module = {
                    'name': module_name,
                    'missing_lines': [],
                    'total_lines': 0,
                    'covered_lines': 0,
                    'coverage_percent': 0
                }
                modules[module_name] = current_module

            # 未覆盖的行
            elif current_module and line.strip().startswith('lines:'):
                # 提取行号范围
                match = re.search(r'lines:\s+(\d+-\d+(?:,\s*\d+-\d+)*)', line)
                if match:
                    ranges = match.group(1)
                    current_module['missing_lines'] = parse_line_ranges(ranges)

    return modules


def parse_line_ranges(ranges_str: str) -> List[int]:
    """
    解析行号范围字符串

    Args:
        ranges_str: 例如 "1-5, 10-15"

    Returns:
        未覆盖的行号列表
    """

    lines = []
    for part in ranges_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            lines.extend(range(start, end + 1))
        else:
            lines.append(int(part))
    return lines


def analyze_source_files(project_root: Path) -> Dict[str, Dict]:
    """
    分析源代码文件

    Args:
        project_root: 项目根目录

    Returns:
        包含源文件信息的字典
    """

    src_dir = project_root / "src"

    if not src_dir.exists():
        print(f"错误: src/ 目录不存在 - {src_dir}")
        sys.exit(1)

    source_files = {}

    for py_file in src_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        rel_path = py_file.relative_to(project_root)
        content = py_file.read_text(encoding='utf-8')

        # 统计行数（排除空行和注释）
        code_lines = []
        for i, line in enumerate(content.split('\n'), 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                code_lines.append(i)

        source_files[str(rel_path)] = {
            'path': py_file,
            'total_code_lines': len(code_lines),
            'code_lines': code_lines
        }

    return source_files


def identify_gaps(modules: Dict, source_files: Dict) -> List[Dict]:
    """
    识别测试缺口

    Args:
        modules: 覆盖率模块信息
        source_files: 源文件信息

    Returns:
        测试缺口列表
    """

    gaps = []

    for module_path, module_info in modules.items():
        if module_path not in source_files:
            continue

        source_info = source_files[module_path]

        # 计算覆盖率
        missing_count = len(module_info['missing_lines'])
        total_count = source_info['total_code_lines']
        covered_count = total_count - missing_count

        coverage_percent = (covered_count / total_count * 100) if total_count > 0 else 0

        module_info['total_lines'] = total_count
        module_info['covered_lines'] = covered_count
        module_info['coverage_percent'] = coverage_percent

        # 识别低覆盖率模块
        if coverage_percent < 85:
            gaps.append({
                'module': module_path,
                'coverage': coverage_percent,
                'missing_lines': module_info['missing_lines'],
                'priority': 'high' if coverage_percent < 70 else 'medium'
            })

    return gaps


def suggest_test_cases(gaps: List[Dict]) -> List[str]:
    """
    建议测试用例

    Args:
        gaps: 测试缺口列表

    Returns:
        测试建议列表
    """

    suggestions = []

    for gap in gaps:
        module = gap['module']
        coverage = gap['coverage']
        missing_lines = gap['missing_lines']

        suggestion = f"\n模块: {module} (覆盖率: {coverage:.1f}%)\n"

        # 建议覆盖的行
        if missing_lines:
            # 取前 10 个未覆盖行作为示例
            sample_lines = missing_lines[:10]
            suggestion += f"  需要覆盖的行示例: {sample_lines}\n"

        suggestion += f"  建议: 为该模块编写测试用例\n"

        if gap['priority'] == 'high':
            suggestion += f"  ⚠️  高优先级 - 覆盖率严重不足\n"

        suggestions.append(suggestion)

    return suggestions


def generate_report(gaps: List[Dict], source_files: Dict, total_coverage: float):
    """
    生成分析报告

    Args:
        gaps: 测试缺口列表
        source_files: 源文件信息
        total_coverage: 总体覆盖率
    """

    print("=" * 60)
    print("pytest 覆盖率分析报告")
    print("=" * 60)

    print(f"\n总体覆盖率: {total_coverage:.1f}%")

    if total_coverage >= 85:
        print("✓ 达到目标覆盖率 (≥85%)")
    else:
        shortfall = 85 - total_coverage
        print(f"✗ 未达到目标，还需提升 {shortfall:.1f}%")

    print(f"\n分析结果:")
    print(f"  源文件总数: {len(source_files)}")
    print(f"  需要改进的模块: {len(gaps)}")

    if gaps:
        print(f"\n高优先级改进项 (覆盖率 <70%):")
        high_priority = [g for g in gaps if g['priority'] == 'high']
        if high_priority:
            for gap in high_priority:
                print(f"  - {gap['module']}: {gap['coverage']:.1f}%")
        else:
            print("  无")

        print(f"\n中优先级改进项 (覆盖率 70-85%):")
        medium_priority = [g for g in gaps if g['priority'] == 'medium']
        if medium_priority:
            for gap in medium_priority:
                print(f"  - {gap['module']}: {gap['coverage']:.1f}%")
        else:
            print("  无")

        # 显示测试建议
        print("\n" + "=" * 60)
        print("测试建议")
        print("=" * 60)

        suggestions = suggest_test_cases(gaps[:5])  # 只显示前5个
        for suggestion in suggestions:
            print(suggestion)

        if len(gaps) > 5:
            print(f"\n... 还有 {len(gaps) - 5} 个模块需要改进\n")

    else:
        print("\n✓ 所有模块覆盖率良好!")

    print("\n" + "=" * 60)
    print("改进建议")
    print("=" * 60)
    print("""
1. 优先为高优先级模块编写测试用例
2. 使用参数化测试覆盖多个场景
3. 确保 edge cases 和异常处理被测试
4. 运行: pytest --cov=src --cov-report=term-missing
5. 查看 HTML 报告: htmlcov/index.html
""")


def main():
    """主函数"""

    import argparse

    parser = argparse.ArgumentParser(description="pytest 覆盖率分析工具")
    parser.add_argument(
        "--coverage-file",
        default="coverage.txt",
        help="覆盖率报告文件路径 (默认: coverage.txt)"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="项目根目录 (默认: 当前目录)"
    )

    args = parser.parse_args()

    project_root = Path(args.project_root)
    coverage_file = Path(args.coverage_file)

    # 如果覆盖率文件不存在，尝试生成
    if not coverage_file.exists():
        print("覆盖率文件不存在，尝试生成...")
        print("运行: pytest --cov=src --cov-report=term-missing > coverage.txt")
        print("\n请先运行测试并生成覆盖率报告")
        sys.exit(1)

    try:
        # 解析覆盖率报告
        print("解析覆盖率报告...")
        modules = parse_coverage_report(coverage_file)

        # 分析源文件
        print("分析源代码文件...")
        source_files = analyze_source_files(project_root)

        # 识别测试缺口
        print("识别测试缺口...")
        gaps = identify_gaps(modules, source_files)

        # 计算总体覆盖率
        total_lines = sum(m['total_lines'] for m in modules.values())
        total_covered = sum(m['covered_lines'] for m in modules.values())
        total_coverage = (total_covered / total_lines * 100) if total_lines > 0 else 0

        # 生成报告
        generate_report(gaps, source_files, total_coverage)

        # 根据覆盖率返回退出码
        if total_coverage < 85:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
