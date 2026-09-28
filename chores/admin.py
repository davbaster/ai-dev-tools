from django.contrib import admin

from .models import Chore, Household, Member


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
	list_display = ("name", "invite_code", "created_at")
	search_fields = ("name", "invite_code")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
	list_display = ("display_name", "household", "joined_at")
	list_filter = ("household",)
	search_fields = ("display_name", "household__name")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"household",
		"points",
		"due_date",
		"recurrence",
		"status",
		"claimant",
	)
	list_filter = ("household", "recurrence", "status")
	search_fields = ("name", "description", "household__name")
