from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Chore, Household, Member


class HouseholdModelTests(TestCase):
	def test_household_generates_an_uppercase_invite_code(self):
		household = Household.objects.create(name="Maple House")

		self.assertEqual(len(household.invite_code), 8)
		self.assertTrue(household.invite_code.isupper())
		self.assertTrue(household.invite_code.isalnum())

	def test_member_names_are_unique_within_a_household(self):
		household = Household.objects.create(name="Maple House")
		Member.objects.create(household=household, display_name="Alex")

		with self.assertRaises(IntegrityError):
			Member.objects.create(household=household, display_name="Alex")

	def test_same_member_name_is_allowed_in_different_households(self):
		first_household = Household.objects.create(name="Maple House")
		second_household = Household.objects.create(name="Cedar House")

		Member.objects.create(household=first_household, display_name="Alex")
		Member.objects.create(household=second_household, display_name="Alex")

		self.assertEqual(Member.objects.filter(display_name="Alex").count(), 2)

	def test_deleting_a_household_deletes_its_members(self):
		household = Household.objects.create(name="Maple House")
		Member.objects.create(household=household, display_name="Alex")

		household.delete()

		self.assertFalse(Member.objects.exists())


class JoinHouseholdViewTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Maple House")

	def test_join_page_is_available(self):
		response = self.client.get(reverse("join"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Join a household")

	def test_member_can_join_with_a_valid_invite_code(self):
		response = self.client.post(
			reverse("join"),
			{
				"invite_code": self.household.invite_code.lower(),
				"display_name": "Alex",
			},
		)

		self.assertRedirects(response, reverse("join"))
		member = Member.objects.get(display_name="Alex")
		self.assertEqual(member.household, self.household)
		self.assertEqual(self.client.session["member_id"], member.id)
		self.assertEqual(self.client.session["household_id"], self.household.id)

	def test_user_can_log_in_after_joining_a_household(self):
		self.client.post(
			reverse("join"),
			{
				"invite_code": self.household.invite_code,
				"display_name": "Alex",
			},
		)

		member = Member.objects.get(display_name="Alex")
		session = self.client.session

		self.assertEqual(session.get("member_id"), member.id)
		self.assertEqual(session.get("household_id"), self.household.id)

	def test_invalid_invite_code_does_not_create_a_member(self):
		response = self.client.post(
			reverse("join"),
			{"invite_code": "NOTFOUND", "display_name": "Alex"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "No household uses this invite code.")
		self.assertFalse(Member.objects.exists())

	def test_duplicate_member_name_is_rejected(self):
		Member.objects.create(household=self.household, display_name="Alex")

		response = self.client.post(
			reverse("join"),
			{
				"invite_code": self.household.invite_code,
				"display_name": "Alex",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "This name is already used in the household.")
		self.assertEqual(Member.objects.count(), 1)


class ChoreModelTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Maple House")
		self.member = Member.objects.create(
			household=self.household,
			display_name="Alex",
		)

	def test_chore_defaults_to_available_one_time(self):
		chore = Chore.objects.create(
			household=self.household,
			name="Wash dishes",
			points=3,
			due_date=timezone.localdate(),
		)

		self.assertEqual(chore.recurrence, "once")
		self.assertEqual(chore.status, "available")
		self.assertIsNone(chore.claimant)

	def test_chore_accepts_supported_recurrence_values(self):
		for recurrence, label in Chore.RECURRENCE_CHOICES:
			with self.subTest(recurrence=recurrence):
				chore = Chore(
					household=self.household,
					name=label,
					points=1,
					due_date=timezone.localdate(),
					recurrence=recurrence,
				)

				chore.full_clean()

	def test_chore_rejects_non_positive_points(self):
		chore = Chore(
			household=self.household,
			name="Invalid chore",
			points=0,
			due_date=timezone.localdate(),
		)

		with self.assertRaises(ValidationError):
			chore.full_clean()

	def test_chore_rejects_unknown_recurrence(self):
		chore = Chore(
			household=self.household,
			name="Invalid recurrence",
			points=1,
			due_date=timezone.localdate(),
			recurrence="yearly",
		)

		with self.assertRaises(ValidationError):
			chore.full_clean()

	def test_claimant_must_belong_to_the_chore_household(self):
		other_household = Household.objects.create(name="Cedar House")
		other_member = Member.objects.create(
			household=other_household,
			display_name="Jordan",
		)
		chore = Chore(
			household=self.household,
			name="Invalid claimant",
			points=1,
			due_date=timezone.localdate(),
			claimant=other_member,
		)

		with self.assertRaises(ValidationError):
			chore.full_clean()

	def test_open_past_due_chore_is_overdue(self):
		chore = Chore.objects.create(
			household=self.household,
			name="Past due chore",
			points=2,
			due_date=timezone.localdate() - timedelta(days=1),
			claimant=self.member,
			status="claimed",
		)

		self.assertTrue(chore.is_overdue)

	def test_completed_and_verified_past_due_chores_are_not_overdue(self):
		for status in ("completed", "verified"):
			with self.subTest(status=status):
				chore = Chore.objects.create(
					household=self.household,
					name=f"{status.title()} chore",
					points=2,
					due_date=timezone.localdate() - timedelta(days=1),
					claimant=self.member,
					status=status,
				)

				self.assertFalse(chore.is_overdue)

	def test_chore_string_representation_is_its_name(self):
		chore = Chore.objects.create(
			household=self.household,
			name="Wash dishes",
			points=3,
			due_date=timezone.localdate(),
		)

		self.assertEqual(str(chore), "Wash dishes")
