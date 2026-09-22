"""Helpers para NeoNet/CyberSource Secure Acceptance Hosted Checkout."""
import base64
import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


def configured():
    return all((settings.NEONET_ACCESS_KEY, settings.NEONET_PROFILE_ID, settings.NEONET_SECRET_KEY))


def sign(fields):
    """Firma los campos en el orden indicado por signed_field_names."""
    names = fields['signed_field_names'].split(',')
    payload = ','.join(f'{name}={fields.get(name, "")}' for name in names)
    digest = hmac.new(
        settings.NEONET_SECRET_KEY.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode('ascii')


def verify_response(fields):
    """Verifica la firma HMAC recibida sin confiar en los datos del navegador."""
    signature = fields.get('signature', '')
    signed_names = fields.get('signed_field_names', '')
    if not signature or not signed_names:
        return False
    try:
        expected = sign({'signed_field_names': signed_names, **fields})
    except (KeyError, UnicodeError):
        return False
    return hmac.compare_digest(signature, expected)


def checkout_fields(pago):
    if not configured():
        raise ImproperlyConfigured('Faltan las credenciales de NeoNet/CyberSource.')
    venta = pago.venta
    fields = {
        'access_key': settings.NEONET_ACCESS_KEY,
        'profile_id': settings.NEONET_PROFILE_ID,
        'transaction_uuid': pago.transaction_uuid,
        'signed_date_time': timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'locale': 'es-GT',
        'transaction_type': 'sale',
        'reference_number': pago.referencia,
        'amount': f'{venta.total:.2f}',
        'currency': settings.NEONET_CURRENCY,
    }
    fields['signed_field_names'] = ','.join(fields.keys())
    fields['signature'] = sign(fields)
    return fields
