
from django.contrib import admin
from django.contrib.comments.admin import CommentsAdmin
from django.utils.translation import ugettext_lazy as _

from sweettooth.ratings.models import RatingComment

class RatingCommentsAdmin(CommentsAdmin):
    fieldsets = (
        (None,
           {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (_('Content'),
           {'fields': ('user', 'rating', 'comment')}
        ),
        (_('Metadata'),
           {'fields': ('submit_date', 'ip_address', 'is_public', 'is_removed')}
        ),
     )

admin.site.register(RatingComment, RatingCommentsAdmin)
