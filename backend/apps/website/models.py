from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model


User = get_user_model()


__all__ = [
    "Course",
    "Section",
    "Room",
    "Element",
    "UserCourseAccessLevel",
    "UserSectionAccessLevel",
    "ProgressOfElement",
    "Tag",
    "SavedProblem",
    "Dictionary",
    "DictionaryEntry",
]


class AccessLevel(models.TextChoices):
    ADMIN = "AD", _("ADMIN")
    VISITOR = "VI", _("VISITOR")


class VisibilityLevel(models.TextChoices):
    PRIVATE = "PRI", _("PRIVATE")   # devs only
    PUBLIC = "PUB", _("PUBLIC")     # available on web
    LIMITER = "LIM", _("LIMITER")   # certain users only

# The query sets below are used to sum the progress of all elements 
# that are relevant to the course/section/room 
# and return a percentage complete
class CourseQuerySet(models.QuerySet):
    def user_progress_percent(self, user):
        return self.annotate(
            total_elements=models.Count("sections__rooms__elements", distinct=True),
            completed_elements=models.Count(
                "sections__rooms__elements__progressofelement",
                filter=models.Q(
                    sections__rooms__elements__progressofelement__user=user,
                    sections__rooms__elements__progressofelement__status=Status.COMPLE,
                ),
                distinct=True,
            ),
        ).annotate(
            progress_percent=100.0 * models.F("completed_elements") / models.F("total_elements")
        )


class SectionQuerySet(models.QuerySet):
    def user_progress_percent(self, user):
        return self.annotate(
            total_elements=models.Count("rooms__elements", distinct=True),
            completed_elements=models.Count(
                "rooms__elements__progressofelement",
                filter=models.Q(
                    rooms__elements__progressofelement__user=user,
                    rooms__elements__progressofelement__status=Status.COMPLE,
                ),
                distinct=True,
            ),
        ).annotate(
            progress_percent=100.0 * models.F("completed_elements") / models.F("total_elements")
        )

    
class RoomQuerySet(models.QuerySet):
    def user_progress_percent(self, user):
        return self.annotate(
            total_elements=models.Count("elements", distinct=True),
            completed_elements=models.Count(
                "elements__progressofelement",
                filter=models.Q(
                    elements__progressofelement__user=user,
                    elements__progressofelement__status=Status.COMPLE
                ),
                distinct=True,
            ),
        ).annotate(
            progress_percent=100.0 * models.F("completed_elements") / models.F("total_elements")
        )

class Course(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        related_name="created_courses"
    )
    visibility = models.CharField(
        max_length=50,
        choices=VisibilityLevel,
        default=VisibilityLevel.PUBLIC
    )
    access_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="UserCourseAccessLevel",
        related_name="course_access",
        blank=True,
        help_text="Users who can access the course when visibility is set to LIMITER"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    objects = CourseQuerySet.as_manager()


class Section(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sections"
    )
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="created_sections"
    )
    visibility = models.CharField(
        max_length=50,
        choices=VisibilityLevel,
        default=VisibilityLevel.PUBLIC
    )
    access_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="UserSectionAccessLevel",
        related_name="section_access",
        blank=True,
        help_text="Users who can access the section when visibility is set to LIMITER"
    )
    number_of_problems = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.title if self.course else 'No Course'} - {self.title}"
    
    objects = SectionQuerySet.as_manager()


class Room(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        related_name="rooms"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        related_name="rooms"
    )
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="created_rooms"
    )
    number_of_problems = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.title if self.course else 'No Course'} - {self.title}"
    
    objects = RoomQuerySet.as_manager()


class ProblemType(models.TextChoices):
    MCQ = "MCQ", _("MULTIPLE CHOICE QUESTION")
    FREERESP = "FREE", _("FREE RESPONSE QUESTION")
    # More types can be added later


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Element(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        related_name="elements"
    )
    content = models.JSONField(default=dict, blank=True)
    type = models.CharField(
        max_length=50,
        choices=ProblemType
    )
    tags = models.ManyToManyField(Tag)
    point_value = models.IntegerField(default=0)
    interface_data = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room} - {self.type}"


class UserCourseAccessLevel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    access_level = models.CharField(
        max_length=50,
        choices=AccessLevel,
        default=AccessLevel.VISITOR
    )

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} → {self.course.title if self.course else 'No Course'} ({self.access_level})"


class UserSectionAccessLevel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True)
    access_level = models.CharField(
        max_length=50,
        choices=AccessLevel,
        default=AccessLevel.VISITOR
    )

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} → {self.section.title if self.section else 'No Section'} ({self.access_level})"


class Status(models.TextChoices):
    NOSTAR = "NOSTAR", _("NOT STARTED")
    INPROG = "INPROG", _("IN-PROGRESS")
    COMPLE = "COMPLE", _("COMPLETED")


class ProgressOfElement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    element = models.ForeignKey(Element, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=50,
        choices=Status,
        default=Status.NOSTAR
    )
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    score = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} → {self.room.title if self.Room else 'No Room'} ({self.status})"

class SavedProblem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    element = models.ForeignKey(Element, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=50,
        choices=Status,
        default=Status.NOSTAR
    )
    saved_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} → {self.element if self.element else 'No Saved Problems'} ({self.status})"

class Dictionary(models.Model):
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    language = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.language} Dictionary"

class DictionaryEntry(models.Model):
    language = models.ForeignKey(Dictionary, on_delete=models.SET_NULL, null=True)
    word = models.CharField(max_length=100)
    definition = models.CharField(max_length=200)
    part_of_speech = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.word}"