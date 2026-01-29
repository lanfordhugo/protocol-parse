"""
测试辅助工具：字节数据构建器

用于方便地构造测试用的二进制数据
"""


class ByteDataBuilder:
    """字节数据构建器"""

    def __init__(self):
        self._data = bytearray()

    @classmethod
    def from_hex(cls, hex_string: str) -> bytes:
        """
        从十六进制字符串创建字节

        Args:
            hex_string: 十六进制字符串，如 "01 02 03" 或 "010203"

        Returns:
            字节数据
        """
        # 移除所有空格
        hex_string = hex_string.replace(" ", "")
        return bytes.fromhex(hex_string)

    def add_uint8(self, value: int, endian: str = "LE") -> "ByteDataBuilder":
        """添加1字节无符号整数"""
        self._data.append(value & 0xFF)
        return self

    def add_uint16(self, value: int, endian: str = "LE") -> "ByteDataBuilder":
        """添加2字节无符号整数"""
        if endian == "LE":
            self._data.extend(value.to_bytes(2, "little"))
        else:
            self._data.extend(value.to_bytes(2, "big"))
        return self

    def add_uint32(self, value: int, endian: str = "LE") -> "ByteDataBuilder":
        """添加4字节无符号整数"""
        if endian == "LE":
            self._data.extend(value.to_bytes(4, "little"))
        else:
            self._data.extend(value.to_bytes(4, "big"))
        return self

    def add_int8(self, value: int, endian: str = "LE") -> "ByteDataBuilder":
        """添加1字节有符号整数"""
        self._data.extend((value & 0xFF).to_bytes(1, "little", signed=True))
        return self

    def add_int16(self, value: int, endian: str = "LE") -> "ByteDataBuilder":
        """添加2字节有符号整数"""
        if endian == "LE":
            self._data.extend(value.to_bytes(2, "little", signed=True))
        else:
            self._data.extend(value.to_bytes(2, "big", signed=True))
        return self

    def add_int32(self, value: int, endian: str = "LE") -> "ByteDataBuilder":
        """添加4字节有符号整数"""
        if endian == "LE":
            self._data.extend(value.to_bytes(4, "little", signed=True))
        else:
            self._data.extend(value.to_bytes(4, "big", signed=True))
        return self

    def add_bytes(self, data: bytes) -> "ByteDataBuilder":
        """添加原始字节数据"""
        self._data.extend(data)
        return self

    def add_string(
        self, text: str, encoding: str = "ascii", length: int = None, pad_null: bool = True
    ) -> "ByteDataBuilder":
        """
        添加字符串

        Args:
            text: 字符串内容
            encoding: 编码方式（ascii/utf-8）
            length: 固定长度（不足填充空字节）
            pad_null: 是否用空字节填充

        Returns:
            self
        """
        encoded = text.encode(encoding)
        if length is not None:
            if len(encoded) > length:
                # 截断
                encoded = encoded[:length]
            elif len(encoded) < length:
                # 填充
                if pad_null:
                    encoded += b"\x00" * (length - len(encoded))
                else:
                    encoded += b" " * (length - len(encoded))
        self._data.extend(encoded)
        return self

    def add_bcd(self, value: int, digits: int) -> "ByteDataBuilder":
        """
        添加BCD编码数字

        Args:
            value: 整数值
            digits: 数字位数（必须是偶数）

        Returns:
            self
        """
        bcd_bytes = bytearray()
        value_str = f"{value:0{digits}d}"

        for i in range(0, len(value_str), 2):
            high = int(value_str[i])
            low = int(value_str[i + 1])
            bcd_bytes.append((high << 4) | low)

        self._data.extend(bcd_bytes)
        return self

    def build(self) -> bytes:
        """构建最终的字节数据"""
        return bytes(self._data)

    def clear(self) -> "ByteDataBuilder":
        """清空数据"""
        self._data.clear()
        return self
