from django.urls import path

from . import views
from . import operacion

app_name = 'informes'

urlpatterns = [
    path('', operacion.admin_report(views.resumen), name='resumen'),
    path('servicios/', operacion.admin_report(views.servicios), name='servicios'),
    path('ventas/', operacion.admin_report(views.ventas), name='ventas'),
    path('inventario/', operacion.stock, name='inventario'),
    path('cierres/', operacion.cierre, name='cierres'),
    path('consultas/', operacion.consultas, name='consultas'),
    path('consulta/<int:historial_pk>/dueno/', operacion.propietario, name='propietario'),
    path('pantalla/', views.pantalla, name='pantalla'),
]
