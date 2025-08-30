# V8MCU C++ 测试风格指南 (精简版)

本文档为 AI 提供 **V8MCU C++ 项目**中使用 **Unity** 和 **EasyLog** 编写单元测试的核心规范。AI 应已具备通用测试基础。

## 1. 核心结构与命名

### 1.1. 文件命名

遵循 **`.cursor/rules/testing.mdc`** 中的"文件命名与映射规则"小节。该小节包含最新的项目实际命名约定和映射规则。

### 1.2. 测试装置类 (Test Fixture Class)

推荐使用测试装置类管理 mocks、SUT 及每个测试用例的状态。

* **命名:** `<被测类名>Test` 或 `<被测类名>Fixture` (例如: `CCommonLogUploaderTest`)。
* **成员:**
  * 非静态 Mocks (例如: `fakeit::Mock<IMyInterface> mockMyInterface;`)
  * 非静态 SUT 实例 (例如: `std::unique_ptr<CMyClass> sut_;`)
  * 非静态参数捕获容器。
* **方法:**
  * `void setUp()`: 每个测试用例前执行 (重置 mocks, 清理捕获容器, 初始化 SUT)。
  * `void tearDown()`: 每个测试用例后执行 (清理 SUT 和资源)。
  * `void test_Feature_Scenario()`: 非静态测试方法。
* **与 Unity 集成 (宏):** 使用 `UNITY_FIXTURE_TEST_CASE` 宏为每个非静态测试方法生成静态包装器。

```cpp
// 宏定义 (通常在共享测试头文件或本文件顶部)
#define UNITY_FIXTURE_TEST_CASE(FIXTURE_CLASS, TEST_METHOD_NAME) \
    static void run_##TEST_METHOD_NAME() \
    { \
        FIXTURE_CLASS fixture; \
        fixture.setUp(); \
        try { fixture.TEST_METHOD_NAME(); } \
        catch (const std::exception& e) { EasyLogError("测试 " #TEST_METHOD_NAME " 抛出标准异常: %s", e.what()); fixture.tearDown(); throw; } \
        catch (...) { EasyLogError("测试 " #TEST_METHOD_NAME " 抛出未知异常"); fixture.tearDown(); throw; } \
        fixture.tearDown(); \
    }

class CMyClassTest 
{
public:
    fakeit::Mock<IDependency> mockDep;
    std::unique_ptr<CMyClass> sut;

    void setUp() {
        mockDep.Reset();
        sut = std::make_unique<CMyClass>(&mockDep.get());
    }
    void tearDown() {
        sut.reset();
    }

    void test_DoSomething_Nominal() {
        // GIVEN
        // WHEN
        // THEN
    }
    UNITY_FIXTURE_TEST_CASE(CMyClassTest, test_DoSomething_Nominal)
};
```

### 1.3. 测试方法命名 (装置类内)

`test_<功能名称>[_<场景描述>]` (例如: `test_GetValue_NotFound`)。

### 1.4. 套件级别设置 (可选)

静态 `suiteSetUp()` / `suiteTearDown()` 可用于整个测试文件的全局一次性设置/清理，由 Unity 全局 `setUp()`/`tearDown()` 调用。**谨慎使用共享状态。**

## 2. 注释

* **文件头:** 标准项目文件头。
* **测试装置类:** Doxygen `@brief` 描述。
* **测试方法 (装置类内):**
  * Doxygen `@brief` 描述测试点。
  * 方法体内使用 `// ===== Given =====`, `// ===== When =====`, `// ===== Then =====` 注释块组织逻辑。

## 3. 代码组织

### 3.1. 测试文件结构

1. 文件头注释。
2. Includes: `unity.h`, `fakeit.hpp`, 被测头文件, `easyLog.h`, 其他。
3. `UNITY_FIXTURE_TEST_CASE` 宏定义 (如果未在共享头文件中)。
4. 测试装置类定义。
5. Unity 全局 `setUp`, `tearDown` (调用装置类的 `suiteSetUp`/`suiteTearDown`，如果存在)。
6. `main` 函数。

### 3.2. `main` 函数结构

```cpp
// (如果定义了 suiteSetUp/suiteTearDown)
// void setUp() { YourFixtureClassName::suiteSetUp(); }
// void tearDown() { YourFixtureClassName::suiteTearDown(); }

int main()
{
    UNITY_BEGIN();
    EasyLogInfo("==================== 开始测试套件: %s ====================", "YourFixtureClassName");
    
    // 测试初始化功能：创建缓存目录并订阅事件 （每个测试用例前添加注释）
    RUN_TEST(YourFixtureClassName::run_test_Feature1_ScenarioA);
    // ... 其他 RUN_TEST 调用
    
    EasyLogInfo("==================== 测试套件完成: %s ====================", "YourFixtureClassName");
    return UNITY_END();
}
```

### 3.3. 测试方法内部组织

* 优先基本功能，然后边界值，再到错误处理。
* 使用空行分隔 GWT 逻辑块。

## 4. 日志记录 (`easyLog.h`)

* **允许的宏:** `EasyLogInfo`, `EasyLogError`, `EasyLogDebug`。
* **套件日志:** 使用 `EasyLogInfo` 在 `main` 函数中标记测试套件的开始与结束。
* **测试用例标题日志:** 在每个非静态测试方法的开始处使用 `EasyLogInfo` 打印测试用例描述。

    ```cpp
    void CMyClassTest::test_MyFeature_SpecificScenario() {
        EasyLogInfo("===== 测试: MyFeature 在 SpecificScenario 下的行为 =====");
        // GWT ...
    }
    ```

* **错误/调试:** 仅在必要时使用 `EasyLogError` / `EasyLogDebug`。
* **禁止:** 不要在 GWT 块内使用日志宏替代断言或代码逻辑。

## 5. 断言 (Unity)

* **验证策略:** 优先通过公开接口验证状态。谨慎使用 `friend` 访问内部状态。
* **选择:**
  * 使用最精确的断言类型 (例如 `TEST_ASSERT_EQUAL_INT_MESSAGE` 而非通用 `TEST_ASSERT_EQUAL_MESSAGE` 处理整数)。
  * **必须使用带 `_MESSAGE` 后缀的断言宏。**
* **常用:** `TEST_ASSERT_EQUAL_INT_MESSAGE`, `TEST_ASSERT_EQUAL_STRING_MESSAGE`, `TEST_ASSERT_TRUE_MESSAGE`, `TEST_ASSERT_FALSE_MESSAGE`, `TEST_ASSERT_NULL_MESSAGE`, `TEST_ASSERT_NOT_NULL_MESSAGE`。
* **失败消息:** 清晰、具体，描述预期行为及相关上下文。例如: `"键 'X' 的值应为 Y，但得到 Z"`。

## 6. 测试数据

* 每个测试用例应准备其独立的、有意义的测试数据。
* 覆盖正常、边界和错误情况。
* 对于多组输入/输出测试，可考虑在测试方法内部使用循环处理数据数组/结构体。

## 7. 代码风格与可测试性

* 遵循项目主代码风格规范 `coding_style.mdc`。
* 依赖通过接口注入，便于 mock。
* 限制静态方法和全局状态的使用，以利于测试隔离。
