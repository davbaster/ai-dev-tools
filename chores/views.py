from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import JoinHouseholdForm
from .models import Household, Member


def join_household(request):
	if request.method == "POST":
		form = JoinHouseholdForm(request.POST)
		if form.is_valid():
			try:
				household = Household.objects.get(
					invite_code=form.cleaned_data["invite_code"]
				)
			except Household.DoesNotExist:
				form.add_error("invite_code", "No household uses this invite code.")
			else:
				display_name = form.cleaned_data["display_name"]
				if Member.objects.filter(
					household=household,
					display_name=display_name,
				).exists():
					form.add_error(
						"display_name",
						"This name is already used in the household.",
					)
				else:
					member = Member.objects.create(
						household=household,
						display_name=display_name,
					)
					request.session["member_id"] = member.id
					request.session["household_id"] = household.id
					messages.success(request, f"You joined {household.name}.")
					return redirect("join")
	else:
		form = JoinHouseholdForm()

	return render(request, "chores/join.html", {"form": form})
