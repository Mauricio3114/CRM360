import os
import json

CACHE_FILE = "/tmp/mava_whatsapp_qr_cache.json"


def _ler_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception:
        return {}


def _salvar_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as arquivo:
            json.dump(cache, arquivo)
    except Exception:
        pass


def salvar_qr(instance_name, qr_base64):
    if not instance_name or not qr_base64:
        return

    cache = _ler_cache()
    cache[instance_name] = qr_base64
    _salvar_cache(cache)


def buscar_qr(instance_name):
    cache = _ler_cache()
    return cache.get(instance_name)