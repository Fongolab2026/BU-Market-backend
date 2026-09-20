from django.urls import path

from . import views

urlpatterns = [
    path("admin/stats/", views.AdminStatsView.as_view(), name="admin-stats"),
    path("admin/activity/", views.AdminActivityView.as_view(), name="admin-activity"),
    path(
        "admin/moderation-queue/",
        views.AdminModerationQueueView.as_view(),
        name="admin-moderation-queue",
    ),
    path("admin/meta/", views.AdminMetaView.as_view(), name="admin-meta"),
    path("settings/", views.PlatformSettingsView.as_view(), name="platform-settings"),
    path("admin/settings/", views.PlatformSettingsView.as_view(), name="admin-settings"),
]