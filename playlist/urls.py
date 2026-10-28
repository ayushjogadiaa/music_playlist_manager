"""
URL configuration for the playlist app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/state/", views.api_state, name="api_state"),
    path("api/play/", views.api_play, name="api_play"),
    path("api/next/", views.api_next, name="api_next"),
    path("api/prev/", views.api_prev, name="api_prev"),
    path("api/insert/", views.api_insert, name="api_insert"),
    path("api/delete/", views.api_delete, name="api_delete"),
    path("api/move/", views.api_move, name="api_move"),
]

