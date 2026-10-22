from django.urls import path
from . import views

app_name = 'pacientes'

urlpatterns = [
    path('razas/', views.razas, name='razas'),
    path('servicios/nuevo/', views.crear_servicio, name='crear_servicio'),
    path('', views.lista, name='lista'),
    path('nuevo/', views.crear, name='crear'),
    path('catalogos/', views.catalogos, name='catalogos'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/historial/nuevo/', views.agregar_historial, name='agregar_historial'),
    path('<int:pk>/historial/<int:historial_pk>/', views.detalle_historial, name='detalle_historial'),
    path('<int:pk>/historial/<int:historial_pk>/facturar/', views.facturar, name='facturar'),
    path('<int:pk>/historial/<int:historial_pk>/post-consulta/', views.post_consulta, name='post_consulta'),
]
