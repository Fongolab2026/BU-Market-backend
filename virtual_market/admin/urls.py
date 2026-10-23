from django.urls import path

from . import views

urlpatterns = [
    path("stats/", views.AdminStatsView.as_view(), name="admin-stats"),
    path("activity/", views.AdminActivityView.as_view(), name="admin-activity"),
    path(
        "moderation-queue/",
        views.AdminModerationQueueView.as_view(),
        name="admin-moderation-queue",
    ),
    path("meta/", views.AdminMetaView.as_view(), name="admin-meta"),
    path("settings/", views.PlatformSettingsView.as_view(), name="platform-settings"),
    path("", views.PlatformSettingsView.as_view(), name="admin-settings"),
]
