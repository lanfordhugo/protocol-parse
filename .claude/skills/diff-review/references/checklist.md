# Diff Review 详细检查清单

本文档提供详细的代码审查检查清单，包含常见问题和模式。

## 1. 逻辑错误和错误行为

### 1.1 算法错误

**常见问题：**

- 循环终止条件错误（off-by-one 错误）
- 除零错误未处理
- 数学运算精度问题（浮点数比较）
- 逻辑运算符优先级错误
- 位运算错误

**检查方法：**

```python
# 错误示例
for i in range(len(items)):  # 应该用 enumerate
    process(i, items[i])

# 正确示例
for i, item in enumerate(items):
    process(i, item)
```

### 1.2 条件判断错误

**常见问题：**

- 缺少 else 分支
- 逻辑与/或混淆（and/or）
- 赋值与比较混淆（= vs ==）
- 布尔值比较冗余

**检查方法：**

```python
# 错误示例
if status == True:  # 冗余比较
    pass

if x = 5:  # 赋值非比较
    pass

# 正确示例
if status:
    pass

if x == 5:
    pass
```

### 1.3 状态管理错误

**常见问题：**

- 状态机转换不完整
- 状态更新不同步
- 并发修改状态未保护

**检查方法：**

```python
# 错误示例
class StateMachine:
    def __init__(self):
        self.state = "idle"

    def process(self):
        if self.state == "idle":
            self.state = "running"
        # 缺少其他状态的处理

# 正确示例
class StateMachine:
    def __init__(self):
        self.state = "idle"
        self.transitions = {
            "idle": ["running"],
            "running": ["paused", "stopped"],
            "paused": ["running", "stopped"],
            "stopped": ["idle"]
        }

    def can_transition_to(self, new_state):
        return new_state in self.transitions.get(self.state, [])
```

## 2. 边界条件

### 2.1 空值处理

**常见问题：**

- None 值未检查
- 空字符串/空列表未处理
- 数据库查询可能返回 None

**检查方法：**

```python
# 错误示例
def get_user_name(user_id):
    user = db.query(user_id)
    return user.name  # user 可能为 None

# 正确示例
def get_user_name(user_id):
    user = db.query(user_id)
    if user is None:
        return "Unknown"
    return user.name
```

### 2.2 集合边界

**常见问题：**

- 空列表/字典未处理
- 单元素列表特殊情况
- 访问索引越界

**检查方法：**

```python
# 错误示例
def get_first_item(items):
    return items[0]  # 空列表会抛出异常

def get_middle(items):
    return items[len(items) // 2]  # 单元素列表正确，但边界不清晰

# 正确示例
def get_first_item(items):
    if not items:
        return None
    return items[0]

def get_middle(items):
    if not items:
        return None
    return items[len(items) // 2]
```

### 2.3 数值极值

**常见问题：**

- 整数溢出
- 除零错误
- 浮点数精度

**检查方法：**

```python
# 错误示例
def calculate_average(numbers):
    return sum(numbers) / len(numbers)  # 空列表除零

# 正确示例
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
```

## 3. 空值和未定义引用

### 3.1 可选参数未检查

**常见问题：**

- 可选类型未解包
- 可能 None 的属性直接访问

**检查方法：**

```python
# 错误示例
def process_config(config: Optional[dict]):
    return config["key"]  # config 可能为 None

# 正确示例
def process_config(config: Optional[dict]):
    if config is None:
        config = {}
    return config.get("key", default)
```

### 3.2 字典/对象访问

**常见问题：**

- 直接访问不存在的键
- 缺少默认值

**检查方法：**

```python
# 错误示例
data = {"name": "test"}
value = data["missing_key"]  # KeyError

# 正确示例
data = {"name": "test"}
value = data.get("missing_key", default_value)
```

### 3.3 函数返回值

**常见问题：**

- 未检查返回值是否成功
- 忽略可能的错误返回

**检查方法：**

```python
# 错误示例
result = parse_input(input_string)
process(result)  # result 可能为 None

# 正确示例
result = parse_input(input_string)
if result is None:
    handle_error()
else:
    process(result)
```

## 4. 竞态条件和并发问题

### 4.1 数据竞争

**常见问题：**

- 共享变量无锁保护
- 多线程同时修改数据

**检查方法：**

```python
# 错误示例
counter = 0

def increment():
    global counter
    counter += 1  # 非原子操作

# 正确示例
import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    with lock:
        counter += 1
```

### 4.2 死锁风险

**常见问题：**

- 多个锁顺序不一致
- 锁未释放

**检查方法：**

```python
# 错误示例
def transfer(a, b):
    lock_a.acquire()
    lock_b.acquire()
    # 可能死锁
    lock_a.release()
    lock_b.release()

# 正确示例
def transfer(a, b):
    # 按顺序获取锁
    locks = sorted([lock_a, lock_b], key=id)
    for lock in locks:
        lock.acquire()
    try:
        # 操作
        pass
    finally:
        for lock in reversed(locks):
            lock.release()
```

## 5. 安全漏洞

### 5.1 注入攻击

**常见问题：**

- SQL 注入
- 命令注入
- 路径遍历

**检查方法：**

```python
# 错误示例
def get_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query)

# 正确示例
def get_user(username):
    query = "SELECT * FROM users WHERE name = ?"
    return db.execute(query, [username])
```

### 5.2 敏感数据

**常见问题：**

- 密码明文存储
- API Key 硬编码
- 日志泄露敏感信息

**检查方法：**

```python
# 错误示例
password = "secret123"
logger.info(f"User login: {username}, password: {password}")

# 正确示例
password = hash_password("secret123")
logger.info(f"User login: {username}")
```

## 6. 资源管理

### 6.1 文件/连接泄漏

**常见问题：**

- 文件未关闭
- 数据库连接未释放

**检查方法：**

```python
# 错误示例
f = open("file.txt")
data = f.read()
# 未关闭文件

# 正确示例
with open("file.txt") as f:
    data = f.read()
# 自动关闭
```

### 6.2 内存泄漏

**常见问题：**

- 循环引用
- 全局缓存无限制增长

**检查方法：**

```python
# 错误示例
cache = {}

def memoize(func):
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper
# 缓存无限增长

# 正确示例
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(x):
    return x * x
# 限制缓存大小
```

## 7. API 合约

### 7.1 参数验证

**常见问题：**

- 缺少参数类型检查
- 参数值范围未验证

**检查方法：**

```python
# 错误示例
def divide(a, b):
    return a / b  # b 可能为 0

# 正确示例
def divide(a, b):
    if b == 0:
        raise ValueError("Divisor cannot be zero")
    return a / b
```

## 8. 缓存问题

### 8.1 缓存失效问题

**常见问题：**

- 数据更新但缓存未失效
- 缓存时间过长

**检查方法：**

```python
# 错误示例
class UserService:
    def get_user(self, user_id):
        if user_id not in self.cache:
            self.cache[user_id] = db.query(user_id)
        return self.cache[user_id]

    def update_user(self, user_id, data):
        db.update(user_id, data)
        # 缓存未失效！

# 正确示例
class UserService:
    def get_user(self, user_id):
        if user_id not in self.cache:
            self.cache[user_id] = db.query(user_id)
        return self.cache[user_id]

    def update_user(self, user_id, data):
        db.update(user_id, data)
        self.cache.pop(user_id, None)  # 失效缓存
```

### 8.2 缓存键错误

**常见问题：**

- 缓存键计算不一致
- 缺少必要参数
- 键冲突

**检查方法：**

```python
# 错误示例
def get_posts(user_id, include_deleted=False):
    cache_key = f"posts:{user_id}"  # 缺少 include_deleted

    if cache_key in cache:
        return cache[cache_key]

    posts = db.query(user_id, include_deleted)
    cache[cache_key] = posts
    return posts
# include_deleted=True 时返回错误缓存

# 正确示例
def get_posts(user_id, include_deleted=False):
    cache_key = f"posts:{user_id}:{include_deleted}"

    if cache_key in cache:
        return cache[cache_key]

    posts = db.query(user_id, include_deleted)
    cache[cache_key] = posts
    return posts
```

### 8.3 无效缓存

**常见问题：**

- 缓存了不应缓存的结果
- 缓存条件错误

**检查方法：**

```python
# 错误示例
def get_current_time():
    if "time" not in cache:
        cache["time"] = datetime.now()
    return cache["time"]
# 时间不应该被缓存

# 正确示例
def get_current_time():
    return datetime.now()  # 不缓存
```

### 8.4 缓存无效（完全未命中）

**常见问题：**

- 缓存键每次不同
- 缓存逻辑错误导致永远不命中

**检查方法：**

```python
# 错误示例
def get_data(timestamp):
    cache_key = f"data:{timestamp}:{time.time()}"  # 时间戳导致每次不同
    # ...缓存逻辑
# 永远不会命中缓存

# 正确示例
def get_data(timestamp):
    cache_key = f"data:{timestamp}"
    # ...缓存逻辑
```

## 9. 代码规范

### 9.1 命名规范

**常见问题：**

- 变量名不清晰
- 函数名不符合约定
- 常量未大写

**检查方法：**

```python
# 错误示例
x = 5  # 不清晰的变量名
def get(d):  # 缩写不清晰
    pass

MAX_SIZE = 100  # 应该是常量

# 正确示例
user_count = 5
def get_user_data(user_id):
    pass

MAX_SIZE = 100  # 常量大写
```

### 9.2 代码重复

**常见问题：**

- 相同代码多次出现
- 应该提取为函数

**检查方法：**

```python
# 错误示例
if condition1:
    result = calculate(x, y, z)
    print(result)
    save_to_file(result)

if condition2:
    result = calculate(x, y, z)
    print(result)
    save_to_file(result)

# 正确示例
def process_result(result):
    print(result)
    save_to_file(result)

if condition1 or condition2:
    result = calculate(x, y, z)
    process_result(result)
```

## 审查报告模板

```markdown
## 文件：path/to/file.py:42

### 问题描述

[描述具体问题]

### 严重程度

- [ ] 严重（Critical）
- [ ] 重要（Major）
- [ ] 一般（Minor）

### 问题类型

- [ ] 逻辑错误
- [ ] 边界条件
- [ ] 空值引用
- [ ] 并发问题
- [ ] 安全漏洞
- [ ] 资源管理
- [ ] API 违规
- [ ] 缓存问题
- [ ] 规范违反

### 当前代码

```python
# 问题代码
```

### 建议修复

```python
# 修复后的代码
```

### 影响

[说明不修复的后果]
```
