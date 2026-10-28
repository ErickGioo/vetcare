from .models import AccesoSistema


class RegistroAccesoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario_inicial = request.user if request.user.is_authenticated else None
        response = self.get_response(request)
        usuario = request.user if request.user.is_authenticated else usuario_inicial
        # No se almacenan consultas, cuerpos de formularios, IP ni credenciales.
        if usuario and not request.path.startswith(('/static/', '/media/', '/healthz/')):
            match = request.resolver_match
            pantalla = (match.view_name if match else 'sin_ruta')[:200]
            # El refresco automático de TV no equivale a un acceso nuevo del usuario.
            if pantalla != 'pacientes:razas' and not (pantalla == 'citas:television' and request.headers.get('X-Vetcare-Refresh') == '1'):
                AccesoSistema.objects.create(usuario=usuario, pantalla=pantalla,
                    metodo=request.method[:10], resultado=response.status_code)
        return response
