from django.urls import path
from . import views
app_name='inventario'
urlpatterns=[path('puntos/<int:pk>/editar/',views.editar_punto,name='editar_punto'),path('',views.panel,name='panel'),path('puntos/',views.puntos,name='puntos')]
