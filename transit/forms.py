import json

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Mark, Route, validate_in_city


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ["username", "email"]


class MarkForm(forms.ModelForm):
    class Meta:
        model = Mark
        fields = ["title", "category", "description", "lat", "lng"]
        widgets = {
            "lat": forms.HiddenInput(),
            "lng": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        error_messages = {
            "lat": {"required": "Pick a location on the map."},
            "lng": {"required": "Pick a location on the map."},
        }


class RouteForm(forms.ModelForm):
    """Route form. The line and stops come from the map editor as JSON."""

    path = forms.CharField(widget=forms.HiddenInput())
    stops = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Route
        fields = ["number", "name", "color", "is_active", "path"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["path"] = json.dumps(self.instance.path)
            self.initial["stops"] = json.dumps(
                [{"name": s.name, "lat": s.lat, "lng": s.lng} for s in self.instance.ordered_stops()]
            )

    def clean_path(self):
        try:
            data = json.loads(self.cleaned_data["path"])
        except (TypeError, ValueError):
            raise forms.ValidationError("Invalid route line data.")
        if not isinstance(data, list) or len(data) < 2:
            raise forms.ValidationError("Draw a line of at least 2 points on the map.")
        return data

    def clean_stops(self):
        raw = self.cleaned_data.get("stops") or "[]"
        try:
            data = json.loads(raw)
            stops = [
                {"name": str(s["name"]).strip()[:120], "lat": float(s["lat"]), "lng": float(s["lng"])}
                for s in data
            ]
        except (TypeError, ValueError, KeyError):
            raise forms.ValidationError("Invalid stop data.")
        for s in stops:
            if not s["name"]:
                raise forms.ValidationError("Every stop needs a name.")
            validate_in_city(s["lat"], s["lng"])
        return stops
