from hashlib import sha256

def encriptar(value):
    return sha256(value.encode('utf-8')).hexdigest()