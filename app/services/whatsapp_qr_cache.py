QR_CACHE = {}


def salvar_qr(instance_name, qr_base64):
    if instance_name and qr_base64:
        QR_CACHE[instance_name] = qr_base64


def buscar_qr(instance_name):
    return QR_CACHE.get(instance_name)