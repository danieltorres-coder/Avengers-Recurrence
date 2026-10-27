"""Protege una página con clave (PBKDF2-SHA256 150k + AES-GCM, igual que las páginas del Speech).
La clave se normaliza (minúsculas, sin espacios) y se pide una sola vez por sesión (sessionStorage «sp_pw»).
Uso: LOCK_PW='<clave>' python3 tools/lock.py <pagina_en_claro.html> <salida.html> "<Título>"
La página en claro NO se sube al repositorio: guárdala fuera de él para editarla después."""
import base64, html, os, sys
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

src, dst, titulo = sys.argv[1:4]
pw = os.environ['LOCK_PW'].lower().replace(' ', '')
texto = open(src, encoding='utf-8').read()
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=150000).derive(pw.encode())
blob = base64.b64encode(salt + iv + AESGCM(key).encrypt(iv, texto.encode(), None)).decode()
t = html.escape(titulo)
page = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>{t}</title>
<style>
:root{{--bg:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--muted:#52514e;--line:#e1e0d9;--accent:#2a78d6;--bad:#c93a3a}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d0d0d;--surface:#1a1a19;--ink:#fff;--muted:#c3c2b7;--line:#2c2c2a;--accent:#3987e5;--bad:#e0605f}}}}
html,body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
.g{{max-width:380px;margin:12vh auto;padding:28px 24px;background:var(--surface);border:1px solid var(--line);border-radius:12px;display:flex;flex-direction:column;gap:12px}}
h1{{font-size:20px;margin:0}}p{{margin:0;color:var(--muted);font-size:13.5px}}
input{{font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}}
button{{font:600 15px system-ui;padding:10px;border:0;border-radius:8px;background:var(--accent);color:#fff;cursor:pointer}}
#e{{color:var(--bad);min-height:1.2em}}
.row{{display:flex;gap:8px}}.row input{{flex:1;min-width:0}}
button.sec{{background:transparent;color:var(--accent);border:1px solid var(--line);font-weight:500}}
.hint{{font-size:12px}}
</style></head><body>
<form class="g" id="f"><h1>{t}</h1><p>Contenido interno de Aprende Institute. Ingresa la clave.</p>
<div class="row"><input type="password" id="p" name="clave_tablero_ltv" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Clave" autofocus><button type="button" id="ver" class="sec">Mostrar</button></div>
<button type="submit">Entrar</button><p id="e" role="alert"></p>
<p class="hint">Si el navegador rellenó otra clave guardada (por ejemplo, la del QA), bórrala y escribe la de este tablero.</p></form>
<script>
(()=>{{
const D="{blob}",I=150000;
const norm=s=>s.toLowerCase().replace(/\\s+/g,'');
async function dec(pw){{const b=Uint8Array.from(atob(D),c=>c.charCodeAt(0));const km=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);const k=await crypto.subtle.deriveKey({{name:'PBKDF2',salt:b.slice(0,16),iterations:I,hash:'SHA-256'}},km,{{name:'AES-GCM',length:256}},false,['decrypt']);return new TextDecoder().decode(await crypto.subtle.decrypt({{name:'AES-GCM',iv:b.slice(16,28)}},k,b.slice(28)))}}
async function go(pw,auto){{try{{const h=await dec(pw);try{{sessionStorage.setItem('sp_pw',pw)}}catch(_){{}}document.open();document.write(h);document.close()}}catch(_){{if(!auto){{try{{sessionStorage.removeItem('sp_pw')}}catch(__){{}}document.getElementById('e').textContent='Clave incorrecta.'}}}}}}
const P=document.getElementById('p'),E=document.getElementById('e');
document.getElementById('ver').addEventListener('click',()=>{{const v=P.type==='password';P.type=v?'text':'password';document.getElementById('ver').textContent=v?'Ocultar':'Mostrar';P.focus()}});
document.getElementById('f').addEventListener('submit',e=>{{e.preventDefault();const v=norm(P.value);if(!v){{E.textContent='Escribe la clave.';P.focus();return}}if(!(window.crypto&&crypto.subtle)){{E.textContent='Este navegador no permite abrir la página. Ábrela en Chrome, Edge o Safari actualizados.';return}}E.textContent='Abriendo…';go(v)}});
try{{const s=sessionStorage.getItem('sp_pw');if(s)go(s,true)}}catch(_){{}}
}})();
</script></body></html>'''
open(dst, 'w', encoding='utf-8').write(page)
print('ok', dst, len(page))
