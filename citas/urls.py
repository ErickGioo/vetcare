from django.urls import path
from . import views
from .tv import television
app_name = 'citas'
urlpatterns = [
    path('tv/', television, name='television'),
    path('', views.lista, name='lista'),
    path('nueva/', views.crear, name='crear'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/estado/<str:estado>/', views.cambiar_estado, name='cambiar_estado'),
]
