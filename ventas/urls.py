from django.urls import path
from . import views
app_name = 'ventas'
urlpatterns = [
    path('', views.lista, name='lista'),
    path('nueva/', views.crear, name='crear'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('<int:pk>/comprobante/', views.comprobante, name='comprobante'),
    path('<int:pk>/pagar/', views.confirmar_pago, name='pagar'),
    path('<int:pk>/pagar/neonet/', views.iniciar_pago_neonet, name='pagar_neonet'),
    path('pagos/neonet/respuesta/', views.respuesta_neonet, name='respuesta_neonet'),
    path('historial/', views.historial, name='historial'),
]
