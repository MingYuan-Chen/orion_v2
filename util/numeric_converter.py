import sys

class NumericConverter:
    """
    A class for converting numeric values to different units.
    """
    _instance = None  # Singleton instance
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(NumericConverter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        pass

    def hex_to_signed_decimal(self, hex_string):
        """
        Convert 16-bit hexadecimal string to its corresponding signed decimal integer (using two's complement representation).

        Parameters:
        hex_string (str): 16-bit hexadecimal string, e.g. "0xF45E" or "0x0ABC".
                         The "0x" prefix is optional, but recommended.

        Returns:
        int: The corresponding signed decimal integer.
        """
        # Remove the possible "0x" prefix
        if "0x" in hex_string:
            hex_string = hex_string.replace("0x", "").replace(" ", "")

        # Ensure the hexadecimal string is an even length, if not, pad with a leading zero
        # For example, "F" -> "0F"
        if len(hex_string) % 2 != 0:
            hex_string = '0' + hex_string

        try:
            # Convert the hexadecimal string to a byte string
            # bytes.fromhex("F45E") will get b'\xf4\x5e'
            byte_representation = bytes.fromhex(hex_string)

            # Convert the byte string to a signed integer
            # byteorder='big' means the most significant byte is first (e.g. 0xF4 before 0x5E)
            # signed=True tells Python to interpret these bytes as two's complement
            return int.from_bytes(byte_representation, byteorder='big', signed=True)
        except ValueError as e:
            print(f"Error: Invalid hexadecimal string or length mismatch: {e}", file=sys.stderr)
            return None # or raise an exception

numeric_converter = NumericConverter()

if __name__ == "__main__":
    # Test examples:

    converter = NumericConverter()
    # Test examples:
    # 16 bit (2 bytes)
    print(f"0xF45E (16-bit) -> {converter.hex_to_signed_decimal('0xf45e')}")
    print(f"0x0ABC (16-bit) -> {converter.hex_to_signed_decimal('0x0abc')}")
    print(f"0xFFFF (16-bit) -> {converter.hex_to_signed_decimal('0xFFFF')}")
    print(f"0x7FFF (16-bit) -> {converter.hex_to_signed_decimal('0x7FFF')}")
    print(f"0x8000 (16-bit) -> {converter.hex_to_signed_decimal('0x8000')}")

    # Test values within your expected range
    print(f"0xFC18 (16-bit) -> {converter.hex_to_signed_decimal('0xFC18')}")
    print(f"0x03E8 (16-bit) -> {converter.hex_to_signed_decimal('0x03E8')}")

    # Test values with odd length
    print(f"0x0F10 (16-bit) -> {converter.hex_to_signed_decimal('0xf10')}") # 3856
    print(f"0xF45E (16-bit) -> {converter.hex_to_signed_decimal('0xf4 0x5e')}") # 3856

    # Test without "0x" prefix
    print(f"F45E (16-bit) -> {converter.hex_to_signed_decimal('F45E')}")

    # Can also handle other byte sizes, e.g. 8-bit (1 byte)
    print(f"0xFF (8-bit) -> {converter.hex_to_signed_decimal('0xFF')}") # -1
    print(f"0x7F (8-bit) -> {converter.hex_to_signed_decimal('0x7F')}") # 127

    # Handle 32-bit (4 bytes)
    print(f"0xFFFFFFFF (32-bit) -> {converter.hex_to_signed_decimal('0xFFFFFFFF')}") # -1
    print(f"0x80000000 (32-bit) -> {converter.hex_to_signed_decimal('0x80000000')}") # -2147483648

