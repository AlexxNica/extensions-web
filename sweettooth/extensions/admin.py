
from django.contrib import admin

from extensions.models import Extension, ExtensionVersion
from extensions.models import STATUS_ACTIVE, STATUS_REJECTED
from review.models import CodeReview

class CodeReviewAdmin(admin.TabularInline):
    model = CodeReview
    fields = 'reviewer', 'comments',

class ExtensionVersionAdmin(admin.ModelAdmin):
    list_display = 'title', 'status',
    list_display_links = 'title',
    actions = 'approve', 'reject',

    def title(self, ver):
        return "%s (%d)" % (ver.extension.uuid, ver.version)
    title.short_description = "Extension (version)"

    inlines = [CodeReviewAdmin]

    def approve(self, request, queryset):
        queryset.update(status=STATUS_ACTIVE)

    def reject(self, request, queryset):
        queryset.update(status=STATUS_REJECTED)

admin.site.register(ExtensionVersion, ExtensionVersionAdmin)

class ExtensionVersionInline(admin.TabularInline):
    model = ExtensionVersion
    fields = 'version', 'status',
    extra = 0

class ExtensionAdmin(admin.ModelAdmin):
    list_display = 'name', 'uuid', 'num_versions', 'creator',
    list_display_links = 'name', 'uuid',
    search_fields = ('uuid', 'name')
    raw_id_fields = ('user',)

    def num_versions(self, ext):
        return ext.versions.count()
    num_versions.short_description = "#V"

    inlines = [ExtensionVersionInline]

admin.site.register(Extension, ExtensionAdmin)
