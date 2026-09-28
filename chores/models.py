import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def generate_invite_code():
	return uuid.uuid4().hex[:8].upper()


class Household(models.Model):
	name = models.CharField(max_length=100)
	invite_code = models.CharField(
		max_length=8,
		unique=True,
		default=generate_invite_code,
		editable=False,
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name


class Member(models.Model):
	household = models.ForeignKey(
		Household,
		on_delete=models.CASCADE,
		related_name="members",
	)
	display_name = models.CharField(max_length=100)
	joined_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["display_name"]
		constraints = [
			models.UniqueConstraint(
				fields=["household", "display_name"],
				name="unique_member_name_per_household",
			),
		]

	def __str__(self):
		return f"{self.display_name} ({self.household.name})"


class Chore(models.Model):
	RECURRENCE_CHOICES = [
		("once", "One-time"),
		("daily", "Daily"),
		("weekly", "Weekly"),
		("monthly", "Monthly"),
	]
	STATUS_CHOICES = [
		("available", "Available"),
		("claimed", "Claimed"),
		("completed", "Completed"),
		("verified", "Verified"),
	]

	household = models.ForeignKey(
		Household,
		on_delete=models.CASCADE,
		related_name="chores",
	)
	name = models.CharField(max_length=150)
	description = models.TextField(blank=True)
	points = models.PositiveIntegerField(validators=[MinValueValidator(1)])
	due_date = models.DateField()
	recurrence = models.CharField(
		max_length=10,
		choices=RECURRENCE_CHOICES,
		default="once",
	)
	status = models.CharField(
		max_length=10,
		choices=STATUS_CHOICES,
		default="available",
	)
	claimant = models.ForeignKey(
		Member,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="claimed_chores",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["due_date", "name"]
		constraints = [
			models.CheckConstraint(
				condition=models.Q(points__gte=1),
				name="chore_points_positive",
			),
			models.CheckConstraint(
				condition=models.Q(
					recurrence__in=["once", "daily", "weekly", "monthly"],
				),
				name="chore_recurrence_valid",
			),
		]

	def clean(self):
		super().clean()
		if (
			self.claimant_id
			and self.household_id
			and self.claimant.household_id != self.household_id
		):
			raise ValidationError(
				{"claimant": "The claimant must belong to this household."}
			)

	@property
	def is_overdue(self):
		return self.due_date < timezone.localdate() and self.status not in {
			"completed",
			"verified",
		}

	def __str__(self):
		return self.name
