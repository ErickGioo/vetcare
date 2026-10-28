"""Aplica los permisos de Django también fuera del administrador."""
from django.core.exceptions import PermissionDenied
from django.utils.deprecation import MiddlewareMixin


class PermisosModulosMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated or request.user.is_superuser:
            return None
        match = request.resolver_match
        namespace, action = match.namespace, match.url_name
        models = {'productos':'producto','clientes':'cliente','pacientes':'paciente',
                  'proveedores':'proveedor','empleados':'empleado','citas':'cita','ventas':'venta'}
        required = []
        if namespace in models:
            model = models[namespace]
            if namespace == 'ventas' and action == 'respuesta_neonet':
                return None  # Callback autenticado por firma, no por sesión.
            if namespace == 'productos' and action in ('categorias','crear_categoria','editar_categoria'):
                model = 'categoria'
            verb = 'view'
            if action in ('crear','crear_categoria','agregar_historial','crear_servicio'):
                verb = 'add'
            elif action in ('editar','editar_categoria','post_consulta','ajustar_inventario','cambiar_estado','pagar','pagar_neonet','facturar'):
                verb = 'change'
            elif action == 'eliminar':
                verb = 'delete'
            elif namespace == 'ventas' and action == 'detalle' and request.method == 'POST':
                verb = 'change'
            if namespace == 'pacientes':
                if action in ('agregar_historial','detalle_historial','post_consulta','facturar'):
                    model = 'historialmedico'
                if action == 'razas':
                    model = 'raza'
                if action == 'crear_servicio':
                    required = ['productos.add_producto']
                if action == 'catalogos':
                    required = ['pacientes.view_especie','pacientes.view_raza']
                    if request.method == 'POST':
                        required += ['pacientes.add_especie' if 'guardar_especie' in request.POST else 'pacientes.add_raza']
                if action in ('agregar_historial','facturar'):
                    required += ['ventas.add_venta']
                    if request.POST.get('proxima_cita'):
                        required += ['citas.add_cita']
                if action == 'post_consulta' and request.POST.get('proxima_cita'):
                    required += ['citas.add_cita','citas.change_cita']
            if not (namespace == 'pacientes' and action in ('catalogos','crear_servicio')):
                required += [f'{namespace}.{verb}_{model}']
            if namespace == 'productos' and action == 'ajustar_inventario':
                required += ['productos.add_movimientoinventario']
        elif namespace == 'informes':
            required = {'propietario':['pacientes.view_historialmedico'], 'consultas':['pacientes.view_historialmedico'],
                'inventario':['productos.view_producto','productos.view_movimientoinventario'],
                'resumen':['ventas.view_venta','citas.view_cita','productos.view_producto'],
                'servicios':['citas.view_cita'], 'pantalla':['citas.view_cita','ventas.view_venta','productos.view_producto']}.get(action,['ventas.view_venta'])
        elif namespace == 'caja':
            required = ['caja.view_cajadiaria']
            if action == 'accesos':
                required += ['caja.view_accesosistema']
            elif request.method == 'POST':
                verb = request.POST.get('accion')
                required += [{'abrir':'caja.add_cajadiaria','cerrar':'caja.change_cajadiaria',
                    'solicitar_reapertura':'caja.add_reaperturacaja',
                    'aprobar_reapertura':'caja.change_reaperturacaja','rechazar_reapertura':'caja.change_reaperturacaja'}.get(verb,'caja.change_cajadiaria')]
        if required and not request.user.has_perms(required):
            raise PermissionDenied('Tu cuenta no tiene permiso para esta acción. Solicita al administrador los permisos necesarios.')
