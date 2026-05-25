"""URL routing for the healthcare prompt manager."""

from django.urls import include, path

urlpatterns = [
    path('', include('prompts.urls')),
]
