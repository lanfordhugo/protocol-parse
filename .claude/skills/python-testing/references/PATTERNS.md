# 测试模式和最佳实践

## AAA 模式（Arrange-Act-Assert）

**结构：**
```python
def test_user_creation():
    # Arrange (准备测试数据和环境)
    user_data = {"name": "Alice", "email": "alice@example.com"}
    repository = MockUserRepository()

    # Act (执行被测试的操作)
    user = repository.create_user(user_data)

    # Assert (验证结果)
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.id is not None
```

**Given-When-Then 变体：**
```python
def test_purchase_with_insufficient_balance():
    # Given: 账户余额不足
    account = Account(balance=50)

    # When: 尝试购买100元的商品
    result = account.purchase(amount=100)

    # Then: 交易被拒绝
    assert result.success is False
    assert result.error == "Insufficient balance"
```

## 测试策略

### 优先黑盒测试

**通过公共接口测试模块行为：**
```python
# ✅ 好的做法：测试公共API
def test_calculator_addition():
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5

# ❌ 避免：直接测试私有方法
def test_calculator_internal_sum():
    calc = Calculator()
    result = calc._sum(2, 3)  # 不要这样做
```

### 必要时白盒测试

**关键内部逻辑验证：**
```python
# 测试辅助函数（如果是公共接口）
def test_parse_date_string():
    result = parse_date("2025-01-28")
    assert result.year == 2025
    assert result.month == 1
    assert result.day == 28
```

### 依赖隔离

**使用 Mock 隔离外部依赖：**
```python
def test_send_email_with_mock():
    # 使用 patch 隔离外部服务
    with patch('module.smtplib.SMTP') as mock_smtp:
        send_email("user@example.com", "Hello")

        # 验证外部调用
        mock_smtp.return_value.send_message.assert_called_once()
```

### 参数化测试

**使用 @pytest.mark.parametrize 进行多场景测试：**
```python
@pytest.mark.parametrize("input,expected", [
    ("valid@email.com", True),
    ("invalid-email", False),
    ("", False),
    ("@example.com", False),
])
def test_email_validation(input, expected):
    assert is_valid_email(input) == expected
```

## Mock 和 Fixture 使用

### pytest fixture 定义

```python
# conftest.py
@pytest.fixture
def sample_user():
    """返回一个测试用户实例"""
    return User(
        id=1,
        name="Test User",
        email="test@example.com"
    )

@pytest.fixture
def database(tmp_path):
    """返回临时数据库连接"""
    db_path = tmp_path / "test.db"
    db = Database.connect(db_path)
    yield db
    db.close()  # 清理

# 使用 fixture
def test_user_update(sample_user, database):
    sample_user.name = "Updated Name"
    database.save(sample_user)
    assert database.get_user(1).name == "Updated Name"
```

### unittest.mock 使用

```python
from unittest.mock import Mock, patch, MagicMock

# Mock 对象
mock_service = Mock()
mock_service.get_data.return_value = {"status": "ok"}
result = mock_service.get_data()
assert result == {"status": "ok"}

# Patch 装饰器
@patch('module.external_api_call')
def test_with_patch(mock_api):
    mock_api.return_value = {"success": True}
    result = module.process_data()
    assert result is True
    mock_api.assert_called_once()

# MagicMock（自动创建方法）
mock = MagicMock()
mock.any_method().any_attribute.return_value = "value"
```

## 验证重点

### 状态验证（优先）

**验证返回值和对象状态：**
```python
def test_calculation_result():
    result = calculate_tax(100, 0.19)
    assert result == 19.00

def test_object_state():
    account = Account(balance=100)
    account.withdraw(30)
    assert account.balance == 70
```

### 行为验证（外部依赖交互）

**验证方法调用和副作用：**
```python
def test_logging_behavior(caplog):
    process_order(order)
    assert "Order processed" in caplog.text

def test_external_service_call():
    with patch('module.api_client') as mock_api:
        process_payment(amount=100)
        mock_api.charge.assert_called_with(amount=100, currency="USD")
```

## 常见反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 测试私有方法 | 耦合实现细节 | 测试公共API |
| 过度使用 Mock | 测试变成Mock配置 | 只隔离外部依赖 |
| 测试第三方库 | 重复测试库本身 | 假设库工作正常 |
| 断言太少 | 测试不充分 | 验证所有关键方面 |
| 测试实现细节 | 脆弱，频繁重构 | 测试行为契约 |
