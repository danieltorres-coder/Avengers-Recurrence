"""Cifra / descifra las páginas protegidas (PBKDF2-SHA256 150k + AES-GCM, igual que el JS de la página)."""
import base64, os, re, sys
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def _key(pw, salt, it):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(pw.encode())

def blob_de(html):
    m = re.search(r'const D="([^"]+)"(?:,I=(\d+))?', html)
    return m.group(1), int(m.group(2) or 150000)

def descifrar(html, pw):
    d, it = blob_de(html)
    b = base64.b64decode(d)
    return AESGCM(_key(pw, b[:16], it)).decrypt(b[16:28], b[28:], None).decode()

def cifrar(texto, pw, it=150000):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(pw, salt, it)).encrypt(iv, texto.encode(), None)
    return base64.b64encode(salt + iv + ct).decode()

def reemplazar_blob(html, nuevo_b64):
    return re.sub(r'const D="[^"]+"', 'const D="' + nuevo_b64 + '"', html, count=1)

if __name__ == '__main__':
    modo, ent, pw, sal = sys.argv[1:5]
    if modo == 'dec':
        open(sal, 'w', encoding='utf-8').write(descifrar(open(ent, encoding='utf-8').read(), pw))
