from django.contrib import admin
from .models import StudentProfile, ExpertProfile, Specialization, ConsultationType

admin.site.register(StudentProfile)
admin.site.register(ExpertProfile)
admin.site.register(Specialization)
admin.site.register(ConsultationType)
