from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from ..forms import SignUpForm


def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! You can now add marks.")
        return redirect("map")
    return render(request, "registration/signup.html", {"form": form})
