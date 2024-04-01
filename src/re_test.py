import re

# 正则表达式
pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:|\.]\d{3}'

# 测试字符串
test_string1 = "11 2024-03-26 18:54:05:223 2024-03-26 18:54:05:223"
test_string2 = "2024-03-28 19:27:38:079"

# 检查是否匹配
match1 = re.search(pattern, test_string1)
match2 = re.search(pattern, test_string2)
print(match1)
if match1:
    print(f"匹配成功: {match1.group()}")
else:
    print("匹配失败")
    
if match2:
    print(f"匹配成功: {match2.group()}")
else:
    print("匹配失败")
