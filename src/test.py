def get_two_binary_str(num):
    binary_str = bin(num)[2:].zfill(16)  # 16位，即2字节
    formatted_str = " : ".join([binary_str[:8], binary_str[8:]])
    char_str = ":".join([f"0x{int(binary_str[i : i + 8], 2):02X}" for i in range(0, 16, 8)])
    return f"{formatted_str} : {char_str}"

print(get_two_binary_str(0x0301))