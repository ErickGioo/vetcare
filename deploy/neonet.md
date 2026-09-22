# Configuración de NeoNet / CyberSource

VetCare usa **Secure Acceptance Hosted Checkout**: la tarjeta se captura en NeoNet/CyberSource, no en VetCare.

## Credenciales y perfil

Solicita a NeoNet las credenciales de **sandbox** `access key`, `profile ID` y `secret key`. En el perfil de Secure Acceptance configura como *custom receipt page* una URL HTTPS pública:

```
https://TU-DOMINIO/ventas/pagos/neonet/respuesta/
```

Después agrega en AWS Secrets Manager (o localmente en `.env`) las variables:

```dotenv
NEONET_ACCESS_KEY=...
NEONET_PROFILE_ID=...
NEONET_SECRET_KEY=...
NEONET_ENDPOINT=https://testsecureacceptance.cybersource.com/pay
NEONET_CURRENCY=GTQ
```

Para producción, NeoNet debe confirmar el endpoint y sustituirlo por el de producción; normalmente es `https://secureacceptance.cybersource.com/pay`. No cambies a producción hasta completar transacciones de prueba autorizadas por NeoNet.

## Flujo implementado

1. Una venta con método **Tarjeta** crea un intento con referencia y UUID únicos.
2. VetCare firma monto, moneda, referencia y perfil con HMAC-SHA256; el navegador envía ese formulario a NeoNet.
3. NeoNet envía el resultado por `POST` a la URL de recibo.
4. VetCare verifica la firma recibida y, solamente con decisión `ACCEPT`, marca la venta como pagada. Las respuestas repetidas son idempotentes.

No ingreses ni almacenes PAN, CVV o claves de NeoNet en el código fuente. El endpoint de recibo debe permanecer disponible desde Internet detrás de HTTPS para que NeoNet pueda devolver el resultado.
