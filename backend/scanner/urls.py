from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health, name='health'),
    path('scan/', views.scan, name='scan'),
    path('library/', views.library, name='library'),
    path('library/<int:pk>/', views.library_detail, name='library_detail'),
]
