from django.contrib import admin
from .models import *

admin.site.register(Course)
admin.site.register(Section)
admin.site.register(Room)
admin.site.register(Element)
admin.site.register(UserCourseAccessLevel)
admin.site.register(UserSectionAccessLevel)
admin.site.register(ProgressOfElement)
admin.site.register(Tag)
admin.site.register(SavedProblem)
admin.site.register(Dictionary)
admin.site.register(DictionaryEntry)