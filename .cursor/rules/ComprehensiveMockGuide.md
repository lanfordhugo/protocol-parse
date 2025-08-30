# 单元测试 Mock 核心指南：FakeIt 实践与通用原则

本文档整合了 FakeIt Mocking 框架的高级用法、常见陷阱，以及通用的单元测试 Mock 最佳实践，旨在帮助开发者构建简单、稳定、可预测且易于维护的单元测试。

## 一、Mock 通用核心原则

在单元测试中有效使用 Mock 至关重要，以下是普适性的最佳实践：

1. **明确 Mock 的目的：隔离被测单元 (Isolate the System Under Test - SUT)**
    * Mock 的核心目标是将你正在测试的代码（SUT）与其依赖项隔离开。
    * **实践:** 只 Mock 那些*直接*与你的 SUT 交互的依赖项。

2. **优先 Mock "外部"或"不稳定"依赖 (Mock External/Unstable Dependencies)**
    * 最适合 Mock 的对象通常是：外部系统（数据库、网络服务）、非确定性行为（时间、随机数）、运行缓慢的依赖。
    * **实践:** 简单的配置类或数据结构通常不应该被 Mock。

3. **拥抱依赖注入 (Embrace Dependency Injection - DI)**
    * 让类依赖于抽象（接口或基类），通过构造函数或方法注入依赖。
    * **实践:** DI 使得在测试时可以轻松传入 Mock 对象，是有效 Mock 的前提。

4. **倾向于 Stub 而不是 Mock (Prefer Stubs over Mocks for State Verification)**
    * **Stub (存根):** 提供固定的返回值或状态，让 SUT 能够顺利执行。测试重点是验证 SUT 的*最终状态*或*返回值*。
    * **Mock (模拟):** 除了 Stub 功能，还强调**验证** SUT 是否以特定方式与依赖项**交互**（如方法调用、参数等）。
    * **实践:** 优先编写验证 SUT 状态的测试。仅在*必须*验证关键交互（且无法通过参数捕获和状态断言间接验证）时才考虑交互验证。

5. **交互验证的首选方案：参数捕获与状态断言**
    * 当需要验证 SUT 是否以特定方式与依赖项交互时（例如，调用了某个方法特定次数，或传入了特定参数），**首选且唯一推荐的方式**是通过参数捕获（见后续 FakeIt 核心验证策略）和对捕获数据的断言来完成，而不是依赖 Mock 框架的直接交互验证功能。
    * **实践:** 关注 SUT 的*公开行为*和*最终结果*，以及通过参数捕获间接验证其与依赖的交互。

6. **保持 Mock 存根简单 (Keep Mock Stubs Simple)**
    * 复杂的 Mock 存根设置 (`When` 链、复杂条件) 通常是测试设计问题的信号。
    * **实践:** 若 Mock 存根设置复杂，考虑是否 SUT 职责过多或依赖接口设计需改进。

7. **不要 Mock 你不拥有的类型，除非必要 (Don't Mock Types You Don't Own, Unless Necessary)**
    * 避免 Mock 标准库或第三方库的稳定类型。
    * **实践:** 如需控制第三方库行为，编写包装类（Adapter 模式），Mock 你自己的包装接口。

8. **不要 Mock 被测类本身 (Don't Mock the Class Under Test)**
    * 单元测试的目标就是测试这个类，Mock 它则失去意义。

9. **测试应该是可读和可维护的 (Tests Should Be Readable and Maintainable)**
    * 遵循 Arrange-Act-Assert (AAA) 或 Given-When-Then (GWT) 模式。
    * 使用清晰的命名描述测试目的和 Mock 行为。

10. **结合集成测试 (Combine with Integration Tests)**
    * 单元测试验证单元独立功能，集成测试确保单元间正确协作。
    * **实践:** 编写集成测试，使用真实依赖（或部分真实依赖）验证组件交互。

11. **确保 Mock 在测试间重置 (Reset Mocks Between Tests)**
    * Mock 对象有状态。确保每个测试在干净的 Mock 状态下运行。
    * **实践:** 在 `tearDown` (或每个测试开始时) 调用 Mock 对象的 `Reset()` 方法。

## 二、FakeIt 框架实践与技巧

FakeIt 是一个强大的 C++ Mocking 框架。以下是使用 FakeIt 的核心原则、最佳实践和常见问题处理。

### **核心验证策略：禁止使用 `Verify`，强制参数捕获**

**背景与观察：**
在本项目实践中，FakeIt 的 `Verify` 关键字（包括所有形式的调用验证、次数验证、参数匹配验证以及序列验证如 `VerifyNoOtherInvocations`）已被证实是导致测试不稳定、崩溃或终端输出异常的主要原因。GDB backtrace 中涉及 `fakeit::SequenceVerificationExpectation` 的内部异常通常与此相关。

**强制指导原则：**

1. **禁止直接使用 `Verify`：**
    * **全面禁止**：在任何情况下，**禁止**在测试代码中使用 `fakeit::Verify(...)` 语句及其所有变体。这包括但不限于 `Verify(Method(...)).Once()`, `Verify(...).Using(...)`, `Verify(...).Matching(...)`, `Verify(...).Exactly(...)`, `Verify(sequence...)`, `VerifyNoOtherInvocations(...)` 等。
    * **理由**：规避 FakeIt 内部验证和错误报告机制的复杂性与不稳定性。

2. **强制采用参数捕获与手动断言进行交互验证：**
    * **唯一标准**：验证方法调用、调用次数及调用参数的**唯一标准方法**是：
        1. 在测试类的成员变量中定义用于存储捕获参数的容器（通常是 `std::vector` 或 `std::list`）。
        2. 在 Mock 方法的存根配置中，使用 `.AlwaysDo([this](/*params*/){ this->captured_params_vector.push_back(/*param_or_tuple*/); /* [optional] return value_if_needed; */ });` 来捕获调用时传入的参数。
        3. 在测试逻辑的 `// ===== Then =====` 部分，使用标准的 Unity 断言宏（如 `TEST_ASSERT_EQUAL_INT_MESSAGE`，`TEST_ASSERT_TRUE_MESSAGE` 等）来检查捕获参数容器的大小（对应调用次数）和容器内元素的值（对应调用参数）。
    * **优势**：此方法将验证逻辑完全置于测试代码的控制之下，行为直接、透明、可预测且高度稳定。

**示例（替代 `Verify` 的标准模式）：**

```cpp
// 假设需要验证 mockObj.doSomething(int x, std::string y) 被调用了2次，
// 第一次参数是 (10, "alpha")，第二次是 (20, "beta")

// 1. 在测试类中定义捕获容器:
// std::vector<std::tuple<int, std::string>> capturedDoSomethingParams;

// 2. 在 Mock 配置中捕获参数:
// When(Method(mockObj, doSomething))
//     .AlwaysDo([this](int x, const std::string& y) {
//         this->capturedDoSomethingParams.emplace_back(x, y);
//         // return some_value_if_method_is_not_void;
//     });

// 3. 在测试断言阶段:
// TEST_ASSERT_EQUAL_INT_MESSAGE(2, capturedDoSomethingParams.size(), "doSomething应被调用2次");
// if (capturedDoSomethingParams.size() == 2) {
//     TEST_ASSERT_EQUAL_INT_MESSAGE(10, std::get<0>(capturedDoSomethingParams[0]), "第一次调用x参数错误");
//     TEST_ASSERT_EQUAL_STRING_MESSAGE("alpha", std::get<1>(capturedDoSomethingParams[0]).c_str(), "第一次调用y参数错误");
//     TEST_ASSERT_EQUAL_INT_MESSAGE(20, std::get<0>(capturedDoSomethingParams[1]), "第二次调用x参数错误");
//     TEST_ASSERT_EQUAL_STRING_MESSAGE("beta", std::get<1>(capturedDoSomethingParams[1]).c_str(), "第二次调用y参数错误");
// }
```

**历史代码迁移：**
项目中现存的 `Verify` 调用应被视为技术债务，并逐步按上述参数捕获与手动断言的模式进行重构，以提升测试套件的整体稳定性。

---

### 1. FakeIt 核心存根原则 (Stubbing Principles)

* **简单性:** 优先使用最直接、最简单的方式配置 Mock 存根行为。
* **稳定性:** 确保测试行为一致，不易受 Mock 框架内部机制影响。
* **可预测性:** Mock 存根的行为应符合直觉，易于理解和维护。

### 2. FakeIt 推荐的最佳实践 (Stubbing & General Usage)

* **优先选择持久性规则 (`Always...`)**
  * **实践**: **默认使用 `AlwaysDo`, `AlwaysReturn`, `AlwaysThrow`** 来定义 Mock 行为，除非确定行为只需发生一次。
  * **理由**: 一次性规则 (`Do`, `Return`, `Throw`) 调用后即失效，是 `UnexpectedMethodCallException` 的常见原因，尤其在回调或不确定调用次数场景。

* **将 Mock 配置限定在测试内部**
  * **实践**: 特定测试用例的 `When(...)` 规则，**直接在该测试函数开头配置**，而非全局 `setUp`（除非是极简通用 `Fake()` 配置）。
  * **理由**: 增强测试独立性和清晰度，避免全局状态干扰。

* **保持 Mock Action Lambda 纯粹简单 (尤其用于参数捕获)**
  * **实践**: 在 `.Do(...)` 或 `.AlwaysDo(...)` Lambda 中，**核心任务是捕获参数到成员变量并（如果需要）返回计算值**。避免其他副作用如日志、文件IO等。
  * **理由**: Lambda 内副作用是隐藏 Bug 温床，可能导致 Mock 框架行为异常。参数捕获应直接且无副作用。

* **谨慎、简单地使用参数匹配器 (`Using`, `Matching`)**
  * **实践**: 当为存根行为（如 `When(...).AlwaysReturn(...)`）或参数捕获的Lambda指定条件时，从最简形式开始。对非关键参数或复杂类型（尤其 `std::string`），优先用通配符 `_` 或 `Any()`。
  * **理由**: 复杂的参数匹配（尤其 `Using` 配合多或非首个 `std::string`）可能引入不稳定性。

* **确保测试隔离：总是重置 Mock (`mock.Reset()`)**
  * **实践**: 每个测试用例开始时（`setUp` 或测试函数开头），调用 `mock.Reset()` 清除规则和调用记录。
  * **理由**: 防止状态影响，保证测试独立性。理解 `Reset` (清规则和历史) 与 `ClearInvocationHistory` (仅清历史) 的区别。

### 3. FakeIt 常见陷阱与调试案例 (不涉及 `Verify`)

* **调试基础：GDB Backtrace**
  * 遇到 FakeIt 异常或崩溃，**使用 GDB 获取 backtrace 是最高效的定位手段**。

* **案例 1: `UnexpectedMethodCallException` - 规则去哪儿了？**
  * **原因**: Mock 方法被调用，但 FakeIt 找不到匹配的 `When` 或 `Fake` 规则。
  * **常见子原因1：一次性 vs. 持久性规则**
    * `.Return()`, `.Throw()`, `.Do()` 默认只生效一次。若方法可能被多次调用或在不确定时机（回调、异步）调用，**强烈建议用持久性规则** (`.AlwaysReturn()`, `.AlwaysDo()`, `N_Times()`)。
  * **常见子原因2：规则顺序与覆盖**
    * 多个 `When` 规则可匹配同一调用时，定义顺序重要。
    * FakeIt 匹配逻辑：**最新定义**且**匹配最特异**（显式参数 > 通配符）的规则被选中。
    * 单次规则执行后消耗。总是规则持续生效，除非被后续能匹配相同调用的新规则覆盖。
    * **启示:** 理解覆盖机制，但尽量避免过度依赖，保持规则清晰。

* **案例 2: Mock Action Lambda 未执行 / 参数未捕获**
  * **陷阱：规则被后续配置无意覆盖**
    * **症状:** 配置了 `.AlwaysDo` 捕获参数，但断言捕获集合为空或不完整。
    * **排查:** 检查是否有对同一 Mock 方法的后续 `When` 配置（如 `.Return` 或其他 `.AlwaysDo`）覆盖了之前的参数捕获规则。
    * **解决方案:** 将 Mock 配置限定在测试内部，避免无意覆盖。仔细检查同一方法的所有 `When` 配置。

* **案例 3: 处理 unique_ptr 返回值**
  * **陷阱：模拟返回 std::unique_ptr 的方法**
    * **症状:** 使用 `.AlwaysReturn(std::unique_ptr<T>(...))` 导致编译错误（不能拷贝 unique_ptr）
    * **解决方案:** 使用 `.AlwaysDo()` 配合 lambda 函数在每次调用时创建新的 unique_ptr:

          ```cpp
          When(Method(mock, createObject)).AlwaysDo([]() -> std::unique_ptr<IObject> {
              return std::unique_ptr<IObject>(new ConcreteObject());
          });
          ```

* **案例 4: 测试隔离的具体案例**
  * **陷阱：复杂测试中的状态干扰**
    * **症状:** 大型测试类中多个测试方法共享 mock 对象，导致前一个测试的配置或捕获的参数干扰后续测试。
    * **解决方案:**
            1. 每个测试用例开头显式调用 `mockObj.Reset()` 重置所有使用的 mock，并清空测试类中所有相关的参数捕获容器。
            2. 将 mock 配置限定在测试方法内部，而不是依赖 setUp 中的通用配置（除非是极简且确信无害的 Fake()）。
            3. 考虑为每个测试方法创建一个独立的测试实例（如果测试类设计允许），避免共享状态。

* **案例 5: C++11 兼容性与智能指针返回值**
  * **陷阱：C++11 环境下的 `std::make_unique` 问题**
    * **症状:** 在配置返回 `std::unique_ptr` 的 Mock 方法时，使用 `std::make_unique` 导致编译错误。
    * **根本原因:** `std::make_unique` 在 C++14 才引入，项目使用 C++11 标准。
    * **解决方案:**

      ```cpp
      // 错误 (C++11 不支持)
      When(Method(mock, createObject)).AlwaysDo([]() {
          return std::make_unique<ConcreteObject>();
      });
      
      // 正确 (C++11 兼容)
      When(Method(mock, createObject)).AlwaysDo([]() -> std::unique_ptr<IObject> {
          return std::unique_ptr<IObject>(new ConcreteObject());
      });
      ```

* **案例 6: 异步环境下的 Mock 调用时序问题**
  * **陷阱：异步任务处理器环境中的参数捕获不完整**
    * **症状:** 在涉及 `CAsyncTaskProcessor` 的测试中，参数捕获容器的大小与预期不符，或者捕获的参数顺序混乱。
    * **根本原因:** 异步任务的执行时机不确定，测试断言时异步操作可能尚未完成。
    * **解决方案:**

      ```cpp
      // 在异步操作后添加适当的等待时间
      eventManager->trigger(event);
      std::this_thread::sleep_for(std::chrono::milliseconds(200)); // 等待异步处理
      
      // 或者使用更健壮的等待机制
      auto startTime = std::chrono::steady_clock::now();
      while (capturedParams.size() < expectedCount && 
             std::chrono::steady_clock::now() - startTime < std::chrono::seconds(1)) {
          std::this_thread::sleep_for(std::chrono::milliseconds(10));
      }
      ```

* **案例 7: Mock 对象生命周期与测试固件类的交互**
  * **陷阱：测试固件类中 Mock 对象的不当初始化顺序**
    * **症状:** 在测试固件类的 `setUp()` 方法中，Mock 配置失效或者出现意外的方法调用。
    * **根本原因:** Mock 对象的 `Reset()` 调用与后续配置的时序问题，或者被测对象在构造时就调用了 Mock 方法。
    * **解决方案:**

      ```cpp
      void setUp() {
          // 1. 首先重置所有 Mock 对象
          mockFileOps.Reset();
          mockComFunc.Reset();
          
          // 2. 清空所有捕获容器
          capturedParams.clear();
          
          // 3. 配置 Mock 行为
          setupMockBehavior();
          
          // 4. 最后创建被测对象（避免构造时调用未配置的 Mock）
          sut = std::unique_ptr<SUT>(new SUT(&mockFileOps.get(), &mockComFunc.get()));
      }
      ```

* **案例 8: 复杂参数类型的捕获与验证**
  * **陷阱：结构体参数的深度比较问题**
    * **症状:** 捕获包含复杂结构体的参数时，Unity 断言无法直接比较结构体内容。
    * **解决方案:**

      ```cpp
      // 对于复杂结构体，分别验证关键字段
      std::vector<SComplexStruct> capturedStructs;
      
      When(Method(mock, processStruct)).AlwaysDo([this](const SComplexStruct& s) {
          this->capturedStructs.push_back(s);
      });
      
      // 验证时分别检查关键字段
      TEST_ASSERT_EQUAL_INT_MESSAGE(1, capturedStructs.size(), "应捕获1个结构体");
      if (capturedStructs.size() == 1) {
          TEST_ASSERT_EQUAL_STRING_MESSAGE("expected", 
                                         capturedStructs[0].stringField.c_str(), 
                                         "字符串字段验证");
          TEST_ASSERT_EQUAL_INT_MESSAGE(42, capturedStructs[0].intField, "整数字段验证");
      }
      ```

* **案例 9: Mock 方法的条件性行为配置**
  * **陷阱：基于输入参数的不同返回值配置复杂化**
    * **症状:** 需要根据不同的输入参数返回不同的值，但使用 `.Using()` 配置过于复杂且不稳定。
    * **解决方案:**

      ```cpp
      // 使用 Lambda 内部逻辑替代复杂的参数匹配
      When(Method(mock, processFile)).AlwaysDo([this](const std::string& path) -> bool {
          this->capturedFilePaths.push_back(path);
          
          // 根据路径特征返回不同结果
          if (path.find("success") != std::string::npos) {
              return true;
          } else if (path.find("failure") != std::string::npos) {
              return false;
          }
          return true; // 默认成功
      });
      ```

* **案例 10: 测试中的真实组件与 Mock 组件混合使用**
  * **陷阱：真实组件与 Mock 组件的生命周期管理冲突**
    * **症状:** 在测试中同时使用真实的 `EventManager` 和 Mock 的文件操作接口时，组件间的交互出现意外行为。
    * **解决方案:**

      ```cpp
      class TestFixture {
          // 真实组件使用智能指针管理
          std::shared_ptr<common::EventManager> realEventManager;
          
          // Mock 组件使用 FakeIt 管理
          Mock<IFileOperations> mockFileOps;
          
          void setUp() {
              // 先创建真实组件
              realEventManager = std::make_shared<common::EventManager>();
              
              // 再配置 Mock 组件
              mockFileOps.Reset();
              setupMockBehavior();
              
              // 最后创建被测对象，注入混合依赖
              sut = std::unique_ptr<SUT>(new SUT(realEventManager.get(), &mockFileOps.get()));
          }
          
          void tearDown() {
              // 按相反顺序清理
              sut.reset();
              realEventManager.reset();
          }
      };
      ```

* **案例 11: 编译环境特定的 FakeIt 问题**
  * **陷阱：特定编译器版本下的模板实例化问题**
    * **症状:** 在某些 GCC 版本下，FakeIt 的模板推导失败，导致编译错误。
    * **解决方案:**

      ```cpp
      // 显式指定模板参数，避免编译器推导失败
      When(OverloadedMethod(mock, methodName, ReturnType(ParamType1, ParamType2)))
          .AlwaysDo([this](ParamType1 p1, ParamType2 p2) -> ReturnType {
              // 实现逻辑
          });
      ```

### **项目特定的最佳实践总结**

1. **严格的 C++11 兼容性检查**: 避免使用 C++14+ 特性，特别是 `std::make_unique`。

2. **异步环境的时序控制**: 在涉及异步组件的测试中，必须添加适当的等待机制。

3. **混合依赖的生命周期管理**: 真实组件与 Mock 组件混用时，注意创建和销毁的顺序。

4. **复杂参数的分解验证**: 对于复杂数据结构，分别验证关键字段而非整体比较。

5. **条件性行为的 Lambda 实现**: 使用 Lambda 内部逻辑替代复杂的 FakeIt 参数匹配机制。

这些经验进一步强化了核心原则：**在项目特定环境中，简单、直接的 Mock 配置和验证方式比复杂的框架特性更可靠**。

## 三、总结

有效的 Mock 策略和熟练运用 Mock 工具（如 FakeIt）是高质量单元测试的基石。核心在于**隔离被测单元、保持测试简单可维护、并准确验证关键行为与状态（通过参数捕获和手动断言）**。结合通用 Mock 原则和 FakeIt 的具体实践，可以显著提升测试的健壮性和开发效率。

## 四、项目实战中发现的额外问题与解决方案

基于 V8MCU 项目的实际测试开发经验，以下是 ComprehensiveMockGuide 原文档中未涵盖的重要发现：

### **案例 5: C++11 兼容性与智能指针返回值**

* **陷阱：C++11 环境下的 `std::make_unique` 问题**
  * **症状:** 在配置返回 `std::unique_ptr` 的 Mock 方法时，使用 `std::make_unique` 导致编译错误。
  * **根本原因:** `std::make_unique` 在 C++14 才引入，项目使用 C++11 标准。
  * **解决方案:**

    ```cpp
    // 错误 (C++11 不支持)
    When(Method(mock, createObject)).AlwaysDo([]() {
        return std::make_unique<ConcreteObject>();
    });
    
    // 正确 (C++11 兼容)
    When(Method(mock, createObject)).AlwaysDo([]() -> std::unique_ptr<IObject> {
        return std::unique_ptr<IObject>(new ConcreteObject());
    });
    ```

### **案例 6: 异步环境下的 Mock 调用时序问题**

* **陷阱：异步任务处理器环境中的参数捕获不完整**
  * **症状:** 在涉及 `CAsyncTaskProcessor` 的测试中，参数捕获容器的大小与预期不符，或者捕获的参数顺序混乱。
  * **根本原因:** 异步任务的执行时机不确定，测试断言时异步操作可能尚未完成。
  * **解决方案:**

    ```cpp
    // 在异步操作后添加适当的等待时间
    eventManager->trigger(event);
    std::this_thread::sleep_for(std::chrono::milliseconds(200)); // 等待异步处理
    
    // 或者使用更健壮的等待机制
    auto startTime = std::chrono::steady_clock::now();
    while (capturedParams.size() < expectedCount && 
           std::chrono::steady_clock::now() - startTime < std::chrono::seconds(1)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    ```

### **案例 7: Mock 对象生命周期与测试固件类的交互**

* **陷阱：测试固件类中 Mock 对象的不当初始化顺序**
  * **症状:** 在测试固件类的 `setUp()` 方法中，Mock 配置失效或者出现意外的方法调用。
  * **根本原因:** Mock 对象的 `Reset()` 调用与后续配置的时序问题，或者被测对象在构造时就调用了 Mock 方法。
  * **解决方案:**

    ```cpp
    void setUp() {
        // 1. 首先重置所有 Mock 对象
        mockFileOps.Reset();
        mockComFunc.Reset();
        
        // 2. 清空所有捕获容器
        capturedParams.clear();
        
        // 3. 配置 Mock 行为
        setupMockBehavior();
        
        // 4. 最后创建被测对象（避免构造时调用未配置的 Mock）
        sut = std::unique_ptr<SUT>(new SUT(&mockFileOps.get(), &mockComFunc.get()));
    }
    ```

### **案例 8: 复杂参数类型的捕获与验证**

* **陷阱：结构体参数的深度比较问题**
  * **症状:** 捕获包含复杂结构体的参数时，Unity 断言无法直接比较结构体内容。
  * **解决方案:**

    ```cpp
    // 对于复杂结构体，分别验证关键字段
    std::vector<SComplexStruct> capturedStructs;
    
    When(Method(mock, processStruct)).AlwaysDo([this](const SComplexStruct& s) {
        this->capturedStructs.push_back(s);
    });
    
    // 验证时分别检查关键字段
    TEST_ASSERT_EQUAL_INT_MESSAGE(1, capturedStructs.size(), "应捕获1个结构体");
    if (capturedStructs.size() == 1) {
        TEST_ASSERT_EQUAL_STRING_MESSAGE("expected", 
                                       capturedStructs[0].stringField.c_str(), 
                                       "字符串字段验证");
        TEST_ASSERT_EQUAL_INT_MESSAGE(42, capturedStructs[0].intField, "整数字段验证");
    }
    ```

### **案例 9: Mock 方法的条件性行为配置**

* **陷阱：基于输入参数的不同返回值配置复杂化**
  * **症状:** 需要根据不同的输入参数返回不同的值，但使用 `.Using()` 配置过于复杂且不稳定。
  * **解决方案:**

    ```cpp
    // 使用 Lambda 内部逻辑替代复杂的参数匹配
    When(Method(mock, processFile)).AlwaysDo([this](const std::string& path) -> bool {
        this->capturedFilePaths.push_back(path);
        
        // 根据路径特征返回不同结果
        if (path.find("success") != std::string::npos) {
            return true;
        } else if (path.find("failure") != std::string::npos) {
            return false;
        }
        return true; // 默认成功
    });
    ```

### **案例 10: 测试中的真实组件与 Mock 组件混合使用**

* **陷阱：真实组件与 Mock 组件的生命周期管理冲突**
  * **症状:** 在测试中同时使用真实的 `EventManager` 和 Mock 的文件操作接口时，组件间的交互出现意外行为。
  * **解决方案:**

    ```cpp
    class TestFixture {
        // 真实组件使用智能指针管理
        std::shared_ptr<common::EventManager> realEventManager;
        
        // Mock 组件使用 FakeIt 管理
        Mock<IFileOperations> mockFileOps;
        
        void setUp() {
            // 先创建真实组件
            realEventManager = std::make_shared<common::EventManager>();
            
            // 再配置 Mock 组件
            mockFileOps.Reset();
            setupMockBehavior();
            
            // 最后创建被测对象，注入混合依赖
            sut = std::unique_ptr<SUT>(new SUT(realEventManager.get(), &mockFileOps.get()));
        }
        
        void tearDown() {
            // 按相反顺序清理
            sut.reset();
            realEventManager.reset();
        }
    };
    ```

### **案例 11: 编译环境特定的 FakeIt 问题**

* **陷阱：特定编译器版本下的模板实例化问题**
  * **症状:** 在某些 GCC 版本下，FakeIt 的模板推导失败，导致编译错误。
  * **解决方案:**

    ```cpp
    // 显式指定模板参数，避免编译器推导失败
    When(OverloadedMethod(mock, methodName, ReturnType(ParamType1, ParamType2)))
        .AlwaysDo([this](ParamType1 p1, ParamType2 p2) -> ReturnType {
            // 实现逻辑
        });
    ```

### **项目特定的最佳实践总结**

1. **严格的 C++11 兼容性检查**: 避免使用 C++14+ 特性，特别是 `std::make_unique`。

2. **异步环境的时序控制**: 在涉及异步组件的测试中，必须添加适当的等待机制。

3. **混合依赖的生命周期管理**: 真实组件与 Mock 组件混用时，注意创建和销毁的顺序。

4. **复杂参数的分解验证**: 对于复杂数据结构，分别验证关键字段而非整体比较。

5. **条件性行为的 Lambda 实现**: 使用 Lambda 内部逻辑替代复杂的 FakeIt 参数匹配机制。

这些经验进一步强化了核心原则：**在项目特定环境中，简单、直接的 Mock 配置和验证方式比复杂的框架特性更可靠**。
