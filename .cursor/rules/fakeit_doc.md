# FakeIt 快速开始

**Franck W** 于 2023年4月20日编辑 · 91次修订

## 包含内容

- [Stubbing（存根）](#stubbing存根)
- [Faking（模拟）](#faking模拟)
- [参数匹配](#参数匹配)
- [调用匹配](#调用匹配)
- [验证](#验证)
- [监视（Spying）](#监视spying)
- [重置 Mock 到初始状态](#重置-mock-到初始状态)
- [继承与动态类型转换](#继承与动态类型转换)
- [模拟重载方法](#模拟重载方法)

FakeIt 设计简洁且表达力强。通过使用许多 C++11 的语言特性，包括变长模板（Variadic templates）、Lambda 表达式、用户自定义字面量（User-defined literals）等，实现了这一设计目标。一些 C++11 特性（如用户自定义字面量）在 MS Visual Studio 2013 中尚未完全支持。如果需要使用 MSVC2013 进行编译，请参考 MSC++ Quickstart。如果使用 VS2015、GCC 或 Clang，这份快速开始指南适合您。

---

## 包含头文件

在测试文件中应包含以下头文件：

```cpp
#include <fakeit.hpp>
```

您可能还需要添加：

```cpp
using namespace fakeit;
```

---

## 核心语法概览

以下是 FakeIt 主要功能的快速语法索引：

- **创建 Mock:** `Mock<Interface> mock;`
- **获取 Mock 实例:** `Interface& instance = mock.get();`
- **存根 (Stubbing):**
  - 选择方法: `Method(mock, methodName)`, `Dtor(mock)`, `OverloadedMethod(mock, name, signature)`, `ConstOverloadedMethod(...)`
  - 设置行为: `When(...)`
    - 返回值 (单次): `.Return(value)`
    - 返回值 (持续): `.AlwaysReturn(value)`, 或 `=`
    - 抛异常 (单次): `.Throw(exception)`
    - 抛异常 (持续): `.AlwaysThrow(exception)`
    - 自定义行为 (单次): `.Do(lambda)`
    - 自定义行为 (持续): `.AlwaysDo(lambda)`
    - 设置出参并返回 (单次): `.ReturnAndSet(retVal, out1, out2)`
    - 设置出参并返回 (持续): `.AlwaysReturnAndSet(retVal, out1, out2)`
    - 重复N次: `.Return(N_Times(value))`, `.Throw(N_Times(exception))`
  - 模拟空行为: `Fake(Method(mock, methodName))`
- **参数匹配 (Argument Matching):**
  - 指定参数: `.Using(arg1, arg2)`
  - 内置匹配器: `Eq(v)`, `Ne(v)`, `Gt(v)`, `Ge(v)`, `Lt(v)`, `Le(v)`, `ApproxEq(v, delta)`, `Any()`, `_` (通配符), `StrEq(s)`, `StrNe(s)`, etc.
- **调用匹配 (Invocation Matching):**
  - 基于 Lambda 的复杂匹配: `.Matching(lambda)`
- **验证 (Verification):**
  - 基本验证: `Verify(Method(mock, methodName))`
  - 次数验证: `.AtLeastOnce()`, `.AtLeast(n)`, `.Exactly(n)`, `.Once()`, `.Never()`
  - 参数匹配验证: `.Using(...)`
  - 调用匹配验证: `.Matching(...)`
  - 调用顺序验证: `Verify(Method(mock, m1), Method(mock, m2))`
  - 调用序列验证: `Verify(Method(...) + Method(...) * N)`
  - 验证范围: `Using(mock1, mock2).Verify(...)`
  - 无其他调用验证: `VerifyNoOtherInvocations(mock)`, `VerifyNoOtherInvocations(Method(mock, m))`
- **监视 (Spying):**
  - 创建 Spy: `Mock<ConcreteClass> spy(realObject);`
  - 监视方法 (记录调用): `Spy(Method(spy, methodName))`
  - 监视但不记录参数 (用于验证): `SpyWithoutVerify(Method(spy, methodName))`
- **重置 Mock:**
  - 完全重置: `mock.Reset();`
  - 清空调用记录: `mock.ClearInvocationHistory();`

---

## Stubbing（存根）

假设我们有以下接口：

```cpp
struct SomeInterface {
   virtual int foo(int) = 0;
   virtual int bar(int, int) = 0;
   virtual int baz(int*, int&) = 0;
};
```

创建一个 Mock 对象并设置行为：

```cpp
Mock<SomeInterface> mock;

// 存根方法 foo 返回一个值
When(Method(mock, foo)).Return(1);

// 存根多个返回值（以下两行效果相同）
When(Method(mock, foo)).Return(1, 2, 3);
When(Method(mock, foo)).Return(1).Return(2).Return(3);

// 返回相同的值多次（例如 56 次）
When(Method(mock, foo)).Return(56_Times(1));

// 返回多个值多次（前 100 次返回 1，接下来 200 次返回 2）
When(Method(mock, foo)).Return(100_Times(1), 200_Times(2));

// 始终返回一个值（以下两行效果相同）
When(Method(mock, foo)).AlwaysReturn(1);
Method(mock, foo) = 1; // 赋值语法也表示 AlwaysReturn
```

> **💡 关键注意: `Return()` vs `AlwaysReturn()`**
>
> - 默认情况下，`.Return(value)` 配置的返回值仅供**一次**匹配调用消耗。
> - 如果后续有更多匹配的调用发生，而没有新的规则，将抛出 `UnexpectedMethodCallException`。
> - **强烈建议**: 如果预期一个规则需要匹配**多次**调用，请使用 `AlwaysReturn`, `AlwaysDo`, `N_Times()` 或赋值 (`=`) 语法。

### 更具体的存根

```cpp
// 存根 foo(1) 返回值 '100' 一次（以下两行效果相同）
When(Method(mock, foo).Using(1)).Return(100);
When(Method(mock, foo)(1)).Return(100);

// 存根 'foo(1)' 始终返回 '100'，其他调用始终返回 0
When(Method(mock, foo)).AlwaysReturn(0); // 任意调用 foo 返回 0
When(Method(mock, foo).Using(1)).AlwaysReturn(100); // 覆盖 foo(1) 返回 100

// 以下两行效果相同
When(Method(mock, foo).Using(1)).AlwaysReturn(0);
Method(mock, foo).Using(1) = 0;
```

### 存根方法抛出异常

```cpp
// 抛出一次异常
When(Method(mock, foo)).Throw(exception());

// 抛出多个异常
When(Method(mock, foo)).Throw(exception(), exception());

// 抛出多次异常（例如 23 次）
When(Method(mock, foo)).Throw(23_Times(exception()));

// 始终抛出异常
When(Method(mock, foo)).AlwaysThrow(exception());
```

> **💡 注意:** `.Throw()` 默认也是一次性的，多次抛出需使用 `.AlwaysThrow()` 或 `N_Times()`。

### 为输出参数赋值

```cpp
// 存根方法，赋值输出参数并返回一个值一次
// 调用 i.baz(&a, b) 将返回 1，并将 2 和 3 赋值给 a 和 b
When(Method(mock, baz)).ReturnAndSet(1, 2, 3);

// 存根多个赋值
When(Method(mock, baz)).ReturnAndSet(1, 2, 3).ReturnAndSet(4, 5, 6);

// 存根部分赋值
// 将 2 赋值给 a，但 b 不会被修改
When(Method(mock, baz)).ReturnAndSet(1, 2);

// 始终赋值并返回指定的值
When(Method(mock, baz)).AlwaysReturnAndSet(1, 2, 3);

// 选择性地赋值参数，使用 std::placeholders 或 fakeit::placeholders
// 注意: <= 语法可能特定于某些版本或有误，文档原文如此，实际使用时请验证
When(Method(mock, baz)).ReturnAndSet(1, _1 <= 2, _2 <= 3);
When(Method(mock, baz)).AlwaysReturnAndSet(1, _2 <= 5);
```

> **💡 注意:** `ReturnAndSet` 对指针类型的输出参数使用占位符 (`fakeit::_`) 可能有限制或无法按预期工作。对于需要部分设置输出参数的复杂场景，使用 `.AlwaysDo` 配合 Lambda 通常更可靠。

### 使用 Lambda 表达式进行更灵活的存根

```cpp
// 使用 Lambda 表达式自定义行为
When(Method(mock, foo)).Do([](int a) -> int { 
    // 自定义实现
    return a * 2;
});
When(Method(mock, foo)).AlwaysDo([](int a) -> int { 
    // 自定义实现
    return a * 2;
});

// 或者，使用 C++14 的自动参数类型推导
When(Method(mock, foo)).AlwaysDo([](auto a) { 
    // 自定义实现
    return a * 2;
});
```

### 存根析构函数

```cpp
struct SomeInterface {
   virtual ~SomeInterface() = 0;
};

Mock<SomeInterface> mock;

// 使用 Lambda 表达式存根虚析构函数
When(Dtor(mock)).Do([]() {
    // 自定义实现
});
```

---

## Faking（模拟）

在许多情况下，我们只是需要存根方法以什么都不做。可以通过显式存根方法为空行为，或使用 Faking 来实现。

```cpp
struct SomeInterface {
   virtual void foo(int) = 0;
   virtual int bar(int, int) = 0;
   virtual ~SomeInterface() = 0;
};

Mock<SomeInterface> mock;

// 以下三行效果相同
Fake(Method(mock, foo)); 
When(Method(mock, foo)).AlwaysReturn(); 
When(Method(mock, foo)).AlwaysDo([](...) {});

// 另一个示例
Fake(Method(mock, bar)); 
When(Method(mock, bar)).AlwaysReturn(0); 
When(Method(mock, bar)).AlwaysDo([](...) { return 0; });
```

也可以使用一行代码模拟多个方法：

```cpp
Fake(Method(mock, foo), Method(mock, bar));
```

### 模拟析构函数

```cpp
// 模拟虚析构函数
Fake(Dtor(mock));
```

---

## 参数匹配

```cpp
// 存根 foo 仅在 arg > 1 时返回 1
When(Method(mock, foo).Using(Gt(1))).Return(1);

// 存根 foo 仅在 arg >= 1 时返回 1
When(Method(mock, foo).Using(Ge(1))).Return(1);

// 存根 foo 仅在 arg < 1 时返回 1
When(Method(mock, foo).Using(Lt(1))).Return(1);

// 存根 foo 仅在 arg <= 1 时返回 1
When(Method(mock, foo).Using(Le(1))).Return(1);

// 存根 foo 仅在 arg != 1 时返回 1
When(Method(mock, foo).Using(Ne(1))).Return(1);

// 存根 foo 仅在 arg == 1 时返回 1
// 以下两行效果相同
When(Method(mock, foo).Using(Eq(1))).Return(1);
When(Method(mock, foo).Using(1)).Return(1);

// 对于浮点数，存根 foo 在 arg 为 1 +/- 0.00005 时返回 1
When(Method(mock, foo).Using(ApproxEq(1, 0.00005))).Return(1);

// 存根 foo 对任何值返回 1
// 以下两行效果相同
When(Method(mock, foo).Using(Any())).Return(1);
When(Method(mock, foo).Using(_)).Return(1);

// 存根 foo 当 arg1 == 1 且 arg2 为任意 int 时返回 1
// 以下三行效果相同
When(Method(mock, foo).Using(1, _)).Return(1);
When(Method(mock, foo).Using(1, Any())).Return(1);
When(Method(mock, foo).Using(Eq(1), _)).Return(1);

// 如果匹配的参数是 C 字符串，可以使用基于 strcmp 的匹配器
// 存根 foostr 仅在 strcmp(arg, "something") == 0 时返回 1
When(Method(mock, foostr).Using(StrEq("something"))).Return(1);

// 还有 StrGt, StrGe, StrLt, StrLe, StrNe，这些与非 Str 部分等效，但使用 strcmp 代替比较运算符
```

> **💡 注意: 规则顺序与覆盖**
>
> - 当定义多个可能匹配同一调用的 `When` 规则时，**定义顺序非常重要**。
> - 通常，**后定义的规则会覆盖先定义的规则**所匹配的范围。
>
>   ```cpp
>   // 示例：
>   When(Method(mock, foo).Using(Gt(0))).Return(1); // arg > 0
>   When(Method(mock, foo).Using(Ge(10))).Return(10); // arg >= 10 (后定义，会覆盖 Gt(0) 中 >= 10 的部分)
>   ```
>
> - **建议**:
>   1. 尽量使用明确、不冲突的规则。
>   2. 避免依赖复杂的覆盖逻辑，尤其是涉及宽泛匹配器（如 `Ne`, `_`, `Any`）时。
>   3. 如果必须使用覆盖，仔细安排定义顺序，将最具体的规则放在最后。

---

## 调用匹配

### 匹配仅基于单个参数的调用

对于大多数情况，参数匹配已经足够使用，如上所述。

### 更复杂的调用匹配

如果需要基于多个参数或更复杂的条件进行匹配，可以使用 Invocation Matching。

```cpp
// 存根 foo 仅在参数 'a' 为偶数时返回 1
auto argument_a_is_even = [](int a) { return a % 2 == 0; };
When(Method(mock, foo).Matching(argument_a_is_even)).Return(1);

// 仅在参数 'a' 为负数时抛出异常
auto argument_a_is_negative = [](int a) { return a < 0; };
When(Method(mock, foo).Matching(argument_a_is_negative)).Throw(exception());

// 存根 bar 仅在 'a' 大于 'b' 时抛出异常
auto a_is_bigger_than_b = [](int a, int b) { return a > b; };
When(Method(mock, bar).Matching(a_is_bigger_than_b)).Throw(exception());

// 或者，使用 C++14 的 Lambda 表达式
When(Method(mock, bar).Matching([](auto a, auto b) { return a > b; })).Throw(exception());
```

---

## 验证

```cpp
Mock<SomeInterface> mock;
When(Method(mock, foo)).AlwaysReturn(1);

SomeInterface &i = mock.get();

// 生产代码
i.foo(1);
i.foo(2);
i.foo(3);
i.bar(2, 1);

// 验证 foo 被至少调用一次（以下四行效果相同）
Verify(Method(mock, foo));
Verify(Method(mock, foo)).AtLeastOnce();
Verify(Method(mock, foo)).AtLeast(1);
Verify(Method(mock, foo)).AtLeast(1_Time);

// 验证 foo 被精确调用 3 次（以下两行效果相同）
Verify(Method(mock, foo)).Exactly(3);
Verify(Method(mock, foo)).Exactly(3_Times);

// 验证 foo(1) 被精确调用一次
Verify(Method(mock, foo).Using(1)).Once();
Verify(Method(mock, foo).Using(1)).Exactly(Once);

// 验证 bar(a > b) 被精确调用一次
Verify(Method(mock, bar).Matching([](int a, int b) { return a > b; })).Exactly(Once);
// 或者，使用 C++14 的 Lambda 表达式
Verify(Method(mock, bar).Matching([](auto a, auto b) { return a > b; })).Exactly(Once);
```

> **💡 注意: 验证无参数方法**
>
> - 验证无参数方法时，直接 `Verify(Method(...))` 即可，**不要**附加空的 `.Using()`。
>
>   ```cpp
>   // 错误示例: 
>   Verify(OverloadedMethod(mock, func, int()).Using()).Once();
>   // 正确示例: 
>   Verify(OverloadedMethod(mock, func, int())).Once();
>   ```

### 验证调用顺序

```cpp
// 验证 foo(1) 在 foo(3) 之前被调用
Verify(Method(mock, foo).Using(1), Method(mock, foo).Using(3));
```

### 验证精确的调用序列

```cpp
// 验证实际调用序列包含 foo 连续调用两次
Verify(Method(mock, foo) * 2); 

// 验证实际调用序列包含 foo 连续调用两次，仅一次
Verify(Method(mock, foo) * 2).Exactly(Once);

// 验证实际调用序列包含 foo(1) 后跟 bar(1,2)，精确调用两次
Verify(Method(mock, foo).Using(1) + Method(mock, bar).Using(1, 2)).Exactly(2_Times);
```

### 验证序列涉及多个 Mock 实例

```cpp
Mock<SomeInterface> mock1;
Mock<SomeInterface> mock2;

When(Method(mock1, foo)).AlwaysReturn(0);
When(Method(mock2, foo)).AlwaysReturn(0);

SomeInterface &i1 = mock1.get();
SomeInterface &i2 = mock2.get();

// 生产代码
i1.foo(1);
i2.foo(1);
i1.foo(2);
i2.foo(2);
i1.foo(3);
i2.foo(3);

// 验证序列 {mock1.foo(any int) + mock2.foo(any int)} 精确调用 3 次
Verify(Method(mock1, foo) + Method(mock2, foo)).Exactly(3_Times);
```

### 验证无其他调用

```cpp
Mock<SomeInterface> mock;
When(Method(mock, foo)).AlwaysReturn(0);
When(Method(mock, bar)).AlwaysReturn(0);
SomeInterface &i = mock.get();

// 调用 foo 两次和 bar 一次
i.foo(1);
i.foo(2);
i.bar("some string");

// 验证 foo(1) 被调用
Verify(Method(mock, foo).Using(1));

// 验证没有其他方法调用（将失败，因为 foo(2) 和 bar("some string") 尚未被验证）
VerifyNoOtherInvocations(mock);

// 验证仅方法 foo 无其他调用（将失败，因为 foo(2) 尚未被验证）
VerifyNoOtherInvocations(Method(mock, foo));

Verify(Method(mock, foo).Using(2));

// 验证没有其他调用（将失败，因为 bar("some string") 尚未被验证）
VerifyNoOtherInvocations(mock);

// 验证仅方法 foo 无其他调用（如果已验证 foo(1) 和 foo(2)）
VerifyNoOtherInvocations(Method(mock, foo));

Verify(Method(mock, bar)); // 验证 bar 被调用（任何参数）
 
// 验证没有其他方法调用（如果已验证 foo(1)、foo(2) 和 bar("some string")）
VerifyNoOtherInvocations(mock);
```

### 忽略琐碎方法的调用

如果希望在验证过程中忽略一些琐碎方法的调用（例如 getter 方法）：

```cpp
// 以下验证将通过，前提是 important_method 被精确调用 3 次，且不会关注 trivial_getter 的调用
Verify(Method(mock, important_method)).Exactly(3);
Verify(Method(mock, trivial_getter)).Any();
VerifyNoOtherInvocations(mock);
```

---

## 验证范围

验证范围是明确指定用于验证序列的实际调用集的方法。

假设有以下接口：

```cpp
struct IA {
   virtual void a1(int) = 0;
   virtual void a2(int) = 0;
};
struct IB {
   virtual void b1(int) = 0;
   virtual void b2(int) = 0;
};
```

以及以下两个 Mock 对象：

```cpp
Mock<IA> aMock;
Mock<IB> bMock;
```

生产代码创建了以下实际调用序列：

```cpp
aMock.a1(1);
bMock.b1(1);
aMock.a2(1);
bMock.b2(1);
```

然后：

```cpp
// 将通过，因为场景 {aMock.a1 + bMock.b1} 是实际调用序列的一部分
Using(aMock, bMock).Verify(Method(aMock, a1) + Method(bMock, b1)); 

// 将失败，因为场景 {aMock.a1 + bMock.b1} 不是实际调用序列的一部分
Using(aMock).Verify(Method(aMock, a1) + Method(bMock, b1)); 

// 将通过，因为场景 {aMock.a1 + aMock.a2} 是实际调用序列的一部分
Using(aMock).Verify(Method(aMock, a1) + Method(aMock, a2)); 
```

默认情况下，FakeIt 使用所有参与验证场景的 Mock 对象来隐式定义验证范围。即，以下两行效果相同：

```cpp
// 明确使用 aMock 和 bMock 的所有方法调用
Using(aMock, bMock).Verify(Method(aMock, a1) + Method(bMock, b1)); 

// 隐式使用 aMock 和 bMock 的所有方法调用
Verify(Method(aMock, a1) + Method(bMock, b1)); 
```

---

## 监视（Spying）

在某些情况下，监视一个现有对象非常有用。FakeIt 是唯一支持监视的 C++ 开源 Mock 框架。

```cpp
class SomeClass {
public:
   virtual int func1(int arg) {
      return arg;
   }
   virtual int func2(int arg) {
      return arg;
   }
};

SomeClass obj;
Mock<SomeClass> spy(obj);

// 重写 func1 返回 10
When(Method(spy, func1)).AlwaysReturn(10);

// 监视 func2 不改变其行为
Spy(Method(spy, func2));

SomeClass &i = spy.get();
cout << i.func1(1); // 输出 10
cout << i.func2(1); // 输出 1（func2 未被存根）
```

**💡 注意:** `Spy()` 会复制函数的参数以便在后续的 `Verify()` 过程中进行比较。如果参数是只可移动的，或者不希望复制参数，请使用 `SpyWithoutVerify()`。它会转发参数，如果参数是按值传递，则会移动它们，从而使它们在后续的 `Verify()` 过程中不可用。

---

## 重置 Mock 到初始状态

在大多数情况下，您需要在每个测试方法之前/之后重置 Mock 对象到初始状态。只需在测试的设置/拆卸代码中为每个 Mock 对象添加以下行：

```cpp
mock.Reset();
```

您也可以仅清除收集的调用记录，同时保留存根：

```cpp
mock.ClearInvocationHistory();
```

> **💡 注意:**
>
> - `ClearInvocationHistory()` 只清除调用记录，不改变已配置的存根。
> - 如果存根使用的是一次性的 `.Return()` 或 `.Throw()`，且已被消耗，即使清除了历史记录，该存根也不会再次生效。
> - `Reset()` 会清除所有调用记录和存根配置。

---

## 继承与动态类型转换

```cpp
struct A {
  virtual int foo() = 0;
};

struct B : public A {
  virtual int foo() override = 0;
};

struct C : public B {
   virtual int foo() override = 0;
};

// 向上转型支持
Mock<C> cMock;
When(Method(cMock, foo)).AlwaysReturn(0);

C &c = cMock.get();
B &b = c;
A &a = b;

cout << c.foo(); // 输出 0
cout << b.foo(); // 输出 0
cout << a.foo(); // 输出 0
```

### 动态类型转换支持

```cpp
Mock<C> cMock;
When(Method(cMock, foo)).AlwaysReturn(0);

A &a = cMock.get(); // 获取实例并向上转型为 A&

B &b = dynamic_cast<B&>(a); // 向下转型为 B&
cout << b.foo(); // 输出 0

C &c = dynamic_cast<C&>(a); // 向下转型为 C&
cout << c.foo(); // 输出 0
```

---

## 模拟重载方法

在模拟重载方法时，您需要指定方法的原型。以下示例代码演示了如何模拟重载方法：

```cpp
struct SomeInterface {
  virtual int func() = 0;
  virtual int func(int) = 0;
  virtual int func(int, std::string) = 0;
};

Mock<SomeInterface> mock;

// 存根无参数的 func
When(OverloadedMethod(mock, func, int())).Return(1); 

// 存根一个 int 参数的 func
When(OverloadedMethod(mock, func, int(int))).Return(2); 

// 存根两个参数（int 和 std::string）的 func
When(OverloadedMethod(mock, func, int(int, std::string))).Return(3);

SomeInterface &i = mock.get();
cout << i.func();         // 输出 1
cout << i.func(1);       // 输出 2
cout << i.func(1, "");   // 输出 3
```

### 模拟 const 重载方法

```cpp
struct SomeInterface {
  virtual int func(int) = 0;
  virtual int func(int) const = 0;
};

Mock<SomeInterface> mock;

// 存根带一个 int 参数的 func（非常量方法）
When(OverloadedMethod(mock, func, int(int))).Return(1);

// 存根带一个 int 参数的 func（常量方法）
When(ConstOverloadedMethod(mock, func, int(int))).Return(2);

SomeInterface &v = mock.get();
const SomeInterface &c = mock.get();

cout << v.func(1);    // 输出 1
cout << c.func(1);    // 输出 2
```

此外，还有 `RefOverloadedMethod`、`ConstRefOverloadedMethod`、`RValRefOverloadedMethod` 和 `ConstRValRefOverloadedMethod`，用于引用限定的重载方法。

---

更多详细信息和示例，请参考 [FakeIt 的 GitHub 仓库](https://github.com/eranpeer/FakeIt)。

**关于高级用法、常见陷阱和特定问题的调试经验，请参考 [FakeIt 高级用法、陷阱与调试技巧](./fakeit_advanced_usage.md)。**
