import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import binascii

str="avaneesh"

def hashEncoder(action,string):
    string_hash = string

    for i in range(0,2):
        string_hash = hashlib.sha256(string_hash.encode())
        string_hash = action + string_hash.hexdigest()
        action = ''
    
    return string_hash


def RSAEncrypter(string):
    keyPair = RSA.generate(3072)

    pubKey = keyPair.publickey()
    # print(f"Public key:  (n={hex(pubKey.n)}, e={hex(pubKey.e)})")
    pubKeyPEM = pubKey.exportKey()
    # print(pubKeyPEM.decode('ascii'))

    # print(f"Private key: (n={hex(pubKey.n)}, d={hex(keyPair.d)})")
    privKeyPEM = keyPair.exportKey()
    # print(privKeyPEM.decode('ascii'))

    string = string.encode('ascii')
    encryptor = PKCS1_OAEP.new(pubKey)
    encrypted = encryptor.encrypt(string)
    print("Encrypted:", binascii.hexlify(encrypted))

def RSADecrypter(string):
    keyPair = RSA.generate(3072)

    pubKey = keyPair.publickey()
    # print(f"Public key:  (n={hex(pubKey.n)}, e={hex(pubKey.e)})")
    pubKeyPEM = pubKey.exportKey()
    # print(pubKeyPEM.decode('ascii'))

    # print(f"Private key: (n={hex(pubKey.n)}, d={hex(keyPair.d)})")
    privKeyPEM = keyPair.exportKey()
    # print(privKeyPEM.decode('ascii'))

    string = string.encode('ascii')
    encryptor = PKCS1_OAEP.new(pubKey)
    encrypted = encryptor.encrypt(string)
    print("Encrypted:", binascii.hexlify(encrypted))
print(hashEncoder('unlock',str))  
print(RSAEncrypter('unlock'))  

  