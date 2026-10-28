from django.urls import path
from .views import panel, accesos
app_name = 'caja'
urlpatterns = [path('accesos/', accesos, name='accesos'), path('', panel, name='panel')]
