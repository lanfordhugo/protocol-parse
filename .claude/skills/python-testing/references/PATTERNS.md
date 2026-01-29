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

### 测试金字塔

**测试层次与比例：**

```text
        /\
       /  \      E2E 测试: 10%
      /____\     - 端到端场景验证
     /      \    - 真实环境集成
    /        \   - 运行慢、维护成本高
   /__________\
  /  集成测试   \  集成测试: 20%
  /____________\ - 模块间交互验证
 /              \ - 数据库、API 集成
/________________\
    单元测试        单元测试: 70%
  - 快速、隔离、易维护
  - 覆盖核心业务逻辑
  - 可并行执行
```

**分层原则：**

| 测试类型 | 关注点 | 典型场景 | 执行频率 |
|:---|:---|:---|:---|
| **单元测试** | 单个函数/类的行为 | 业务逻辑、数据转换、算法 | 每次提交 |
| **集成测试** | 模块间交互 | 数据库操作、API 调用 | 每次合并 |
| **E2E 测试** | 完整用户流程 | 登录→下单→支付 | 每日构建 |

**为什么金字塔结构？**

```python
# ✅ 推荐：大量单元测试（快速、隔离、稳定）
def test_calculate_discount():
    # 纯函数测试，无外部依赖
    assert calculate_discount(100, 0.1) == 90
    assert calculate_discount(100, 0.0) == 100

# ⚠️ 谨慎使用：集成测试（较慢、需环境）
def test_user_repository_integration(db_session):
    # 需要数据库环境
    user = User(name="Alice")
    db_session.add(user)
    db_session.commit()
    assert db_session.query(User).filter_by(name="Alice").first() is not None

# ❌ 避免过度：E2E 测试（慢、脆弱、难调试）
def test_complete_purchase_flow(browser):
    # 启动浏览器、访问页面、点击按钮...
    # 只保留少数关键业务流程
```

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

### TDD 工作流（测试驱动开发）

**Red-Green-Refactor 循环：**

```text
1. Red   : 写一个失败的测试
2. Green : 写最少代码让测试通过
3. Refactor: 重构改进代码质量
```

**何时使用 TDD：**

| 场景 | 是否适合 TDD | 原因 |
|:---|:---|:---|
| 有明确接口规范的模块 | ✅ 适合 | 测试可以指导接口设计 |
| 核心业务逻辑 | ✅ 适合 | 确保关键功能正确性 |
| 复杂算法实现 | ✅ 适合 | 边界条件清晰，易于验证 |
| 快速原型开发 | ❌ 不适合 | 接口变动频繁，测试成本高 |
| UI/交互逻辑 | ⚠️ 谨慎 | 需要结合视觉测试工具 |

**TDD 实战示例：**

```python
# 1. Red: 先写失败的测试
def test_calculate_price_with_discount():
    result = calculate_price(100, discount_percent=10)
    assert result == 90  # 测试失败：函数还不存在

# 2. Green: 写最少代码让测试通过
def calculate_price(price, discount_percent=0):
    if discount_percent:
        return price * (1 - discount_percent / 100)
    return price

# 3. Refactor: 重构改进代码质量
def calculate_price(price, discount_percent=0):
    """计算折后价格

    Args:
        price: 原价
        discount_percent: 折扣百分比（0-100）

    Returns:
        折后价格
    """
    if not 0 <= discount_percent <= 100:
        raise ValueError("折扣必须在 0-100 之间")

    discount_amount = price * (discount_percent / 100)
    return price - discount_amount
```

**TDD 的优势：**

- ✅ 确保测试覆盖：先写测试保证 100% 覆盖率
- ✅ 指导接口设计：测试视角设计更易用的 API
- ✅ 重构信心：有测试保护可以放心重构
- ✅ 文档作用：测试用例即使用示例

**TDD 的局限性：**

- ⚠️ 学习曲线：需要练习才能掌握节奏
- ⚠️ 不适合所有场景：探索性开发、UI 开发
- ⚠️ 可能过度设计：为了可测试而引入不必要的抽象

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
| :--- | :--- | :--- |
| 测试私有方法 | 耦合实现细节 | 测试公共API |
| 过度使用 Mock | 测试变成Mock配置 | 只隔离外部依赖 |
| 测试第三方库 | 重复测试库本身 | 假设库工作正常 |
| 断言太少 | 测试不充分 | 验证所有关键方面 |
| 测试实现细节 | 脆弱，频繁重构 | 测试行为契约 |

## 测试可维护性

### 测试数据管理

**使用测试数据工厂：**

```python
# 使用 factory_boy 生成测试数据
import factory
from factory import fuzzy

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    name = factory.Faker('name')
    email = factory.Faker('email')
    age = fuzzy.FuzzyInteger(18, 100)

# 使用
def test_user_creation():
    user = UserFactory()
    assert user.id is not None
    assert "@" in user.email

# 自定义数据
def test_with_specific_data():
    user = UserFactory(name="Alice", age=25)
    assert user.name == "Alice"
    assert user.age == 25
```

**使用 faker 生成随机数据：**

```python
from faker import Faker

fake = Faker()

def test_with_fake_data():
    user = User(
        name=fake.name(),
        email=fake.email(),
        phone=fake.phone_number(),
        address=fake.address()
    )
    # 测试逻辑...
```

### 降低测试耦合

**避免测试间共享状态：**

```python
# ❌ 错误：测试间共享状态
class TestUserManager:
    user = None  # 类变量，所有测试共享

    def test_create_user(self):
        self.user = create_user("Alice")
        assert self.user.name == "Alice"

    def test_delete_user(self):
        # 依赖 test_create_user 先执行
        delete_user(self.user)  # 如果单独运行会失败

# ✅ 正确：每个测试独立
class TestUserManager:
    def test_create_user(self):
        user = create_user("Alice")
        assert user.name == "Alice"

    def test_delete_user(self):
        user = create_user("Bob")  # 自己创建测试数据
        delete_user(user)
        assert get_user(user.id) is None
```

**使用 fixture 而非全局变量：**

```python
# ❌ 错误：全局变量
test_config = {"debug": True}

def test_feature_one():
    assert test_config["debug"] is True

# ✅ 正确：使用 fixture
@pytest.fixture
def test_config():
    return {"debug": True}

def test_feature_one(test_config):
    assert test_config["debug"] is True
```

### 测试性能优化

**并行执行：**

```bash
# 安装 pytest-xdist
pip install pytest-xdist

# 自动并行运行
pytest -n auto

# 指定进程数
pytest -n 4
```

**标记慢速测试：**

```python
import pytest

@pytest.mark.slow
def test_large_file_processing():
    # 处理大文件，较慢
    process_file("large_data.csv")

# 运行时跳过慢速测试
# pytest -m "not slow"
```

**使用临时资源：**

```python
# 使用 pytest 内置的 tmp_path fixture
def test_file_operations(tmp_path):
    # tmp_path 自动创建和清理
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    assert test_file.read_text() == "test content"
    # 测试结束后自动删除
```

**避免重复设置：**

```python
# ❌ 错误：每次测试都重复设置
class TestDatabase:
    def test_query_one(self):
        db = Database.connect(":memory:")
        db.setup_schema()
        # 测试代码...
        db.close()

    def test_query_two(self):
        db = Database.connect(":memory:")
        db.setup_schema()
        # 测试代码...
        db.close()

# ✅ 正确：使用 fixture 复用设置
@pytest.fixture
def database():
    db = Database.connect(":memory:")
    db.setup_schema()
    yield db
    db.close()

class TestDatabase:
    def test_query_one(self, database):
        # 直接使用 database
        assert database.query("SELECT 1") == [(1,)]

    def test_query_two(self, database):
        assert database.query("SELECT 2") == [(2,)]
```

### 测试命名和组织

**清晰的测试命名：**

```python
# ❌ 不清晰
def test_user():
    assert user.name == "Alice"

# ✅ 清晰：test_<被测试函数>_<场景>_<预期结果>
def test_create_user_with_valid_data_returns_user_object():
    user = create_user(name="Alice", email="alice@example.com")
    assert user.name == "Alice"
    assert user.id is not None

def test_create_user_with_duplicate_email_raises_error():
    with pytest.raises(UserExistsError):
        create_user(name="Bob", email="alice@example.com")
```

**使用测试类组织相关测试：**

```python
class TestUserCreation:
    """用户创建相关测试"""

    def test_with_valid_data(self):
        pass

    def test_with_invalid_email(self):
        pass

    def test_with_duplicate_name(self):
        pass

class TestUserDeletion:
    """用户删除相关测试"""

    def test_existing_user(self):
        pass

    def test_non_existing_user(self):
        pass
```

## 异步测试

### pytest-asyncio 使用

**安装和配置：**

```bash
pip install pytest-asyncio
```

**基本用法：**

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None

@pytest.mark.asyncio
async def test_async_with_fixture(async_client):
    response = await async_client.get("/api/users")
    assert response.status_code == 200
```

**异步 fixture：**

```python
@pytest.fixture
async def async_database():
    db = AsyncDatabase(":memory:")
    await db.connect()
    yield db
    await db.disconnect()

@pytest.mark.asyncio
async def test_async_query(async_database):
    result = await async_database.query("SELECT * FROM users")
    assert len(result) > 0
```

**异步类测试：**

```python
@pytest.mark.asyncio
class TestAsyncAPI:
    async def test_get_user(self, async_client):
        response = await async_client.get("/api/users/1")
        assert response.status_code == 200

    async def test_create_user(self, async_client):
        response = await async_client.post("/api/users", json={
            "name": "Alice"
        })
        assert response.status_code == 201
```

**配置 pytest.ini：**

```ini
[pytest]
asyncio_mode = auto
```

## Mock 最佳实践

### 使用 spec 确保接口一致性

```python
from unittest.mock import Mock, patch

# ✅ 使用 spec 确保接口一致
with patch('module.ExternalService', spec=RealExternalService) as mock_service:
    # 如果 RealExternalService 没有 some_method，这里会报错
    mock_service.some_method()

# ❌ 不使用 spec：可能调用不存在的方法
with patch('module.ExternalService') as mock_service:
    mock_service.non_existent_method()  # 不会报错，但实际服务没有此方法
```

### Spy 模式（部分 Mock）

```python
# Spy 模式：保留真实实现，只 Mock 特定方法
service = RealService()
service.method_that_should_be_mocked = Mock(return_value="mocked value")

# 调用 Mock 的方法
result = service.method_that_should_be_mocked()
assert result == "mocked value"

# 调用真实实现
result = service.other_method()  # 使用真实的 other_method
```

### Mock 异常处理

```python
def test_exception_handling():
    with patch('module.external_api') as mock_api:
        # Mock 抛出异常
        mock_api.side_effect = ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            module.call_external_api()

        # 验证异常被正确处理
        mock_api.assert_called_once()
```

### Mock 返回值序列

```python
def test_multiple_calls():
    mock_service = Mock()

    # 每次调用返回不同值
    mock_service.get_data.side_effect = [1, 2, 3]

    assert mock_service.get_data() == 1
    assert mock_service.get_data() == 2
    assert mock_service.get_data() == 3
```

### 避免过度 Mock

```python
# ❌ 过度 Mock：测试变成了 Mock 配置
def test_with_over_mocking():
    with patch('module.ServiceA'):
        with patch('module.ServiceB'):
            with patch('module.ServiceC'):
                # 所有依赖都被 Mock，测试失去了意义
                result = module.process()
                assert result is not None

# ✅ 适当 Mock：只隔离外部依赖
def test_with_proper_mocking():
    with patch('module.ExternalAPI'):  # 只 Mock 真正外部依赖
        result = module.process()
        assert result == expected_value
```
