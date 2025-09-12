# 代码风格和约定

## Python代码规范
- **编码规范**: 遵循PEP 8 Python编码规范
- **Python版本**: Python 3.7+ (推荐3.8+)
- **导入顺序**: 标准库 → 第三方库 → 本地模块
- **命名约定**:
  - 类名: PascalCase (如: `UnifiedProtocol`, `BaseProtocol`)
  - 函数/变量名: snake_case (如: `parse_data_content`, `head_len`)
  - 常量: UPPER_SNAKE_CASE (如: `PROTOCOL_CONFIGS`)
  - 私有方法: 下划线前缀 (如: `_extract_field_value`)

## 文档字符串
- 所有公共类和方法都有中文文档字符串
- 格式：三引号，简要描述功能
- 示例:
  ```python
  def parse_data_content(self, data_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
      \"\"\"使用配置驱动的头部字段解析\"\"\"
  ```

## 类型注解
- 使用类型注解提高代码可读性
- 导入typing模块的类型 (如: `List`, `Dict`, `Any`)
- 函数参数和返回值都有类型注解
- 示例:
  ```python
  from typing import Any, Dict, List
  def method(self, data: List[str]) -> Dict[str, Any]:
  ```

## 设计模式
- **配置驱动模式**: 通过配置文件定义协议，零代码扩展
- **抽象基类**: BaseProtocol定义通用接口
- **策略模式**: 不同协议有不同解析策略
- **工厂模式**: 通过协议名称创建对应实例

## 错误处理
- 使用异常处理机制 (try/except)
- 有日志输出支持 (log.e_print, log.d_print, log.i_print)
- 参数验证和边界检查

## 配置管理
- 协议配置集中在 `protocol_configs.py`
- 使用NamedTuple定义配置结构
- 配置项有详细的中文注释说明
- 支持字段级配置：偏移量、长度、字节序、类型等

## 模块组织
- 单一职责原则：每个模块有明确的功能
- 依赖倒置：面向抽象编程，不依赖具体实现
- 开闭原则：对扩展开放，对修改封闭