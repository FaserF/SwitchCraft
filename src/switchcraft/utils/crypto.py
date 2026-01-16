import base64

class SimpleCrypto:
    """
    Simple obfuscation for registry values to avoid plaintext storage.
    Uses XOR with a static key + Base64.
    NOTE: This is NOT strong encryption. It only hides values from casual view.
    The key is hardcoded here, so anyone with the source can decrypt it.
    This satisfies the requirement "not plaintext in registry".
    """
    _KEY = b"SwitchCraft_Registry_Obfuscation_Key_2025"

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not plaintext:
            return ""
        data = plaintext.encode('utf-8')
        key_len = len(cls._KEY)
        encrypted = bytearray()
        for i, b in enumerate(data):
            encrypted.append(b ^ cls._KEY[i % key_len])
        return base64.b64encode(encrypted).decode('ascii')

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            data = base64.b64decode(ciphertext)
            key_len = len(cls._KEY)
            decrypted = bytearray()
            for i, b in enumerate(data):
                decrypted.append(b ^ cls._KEY[i % key_len])
            return decrypted.decode('utf-8')
        except Exception:
            return ""
