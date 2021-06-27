# Copyright (C) 2018 The MindbreakersServer Contributors.
#
# This file is part of MindbreakersServer.
#
# MindbreakersServer is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# MindbreakersServer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Hunter2.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from .models import Person
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout
from crispy_forms.bootstrap import StrictButton, InlineField
from django.core.exceptions import ValidationError
import re


class GuessForm(forms.Form):
    response = forms.CharField(max_length=400, label='response', initial="Wrong Answer")
    sub_id = forms.CharField(label='sub_id')


class UnlockForm(forms.Form):
    team_id = forms.CharField(label='team_id')
    puzzle_id = forms.CharField(label='puzzle_id')


class PersonForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PersonForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Person
        fields = []


class UserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['password'].widget = forms.PasswordInput()

    required_css_class = 'required'
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput())

    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        if email and User.objects.filter(email=email).exclude(username=username).exists():
            raise forms.ValidationError('Someone is already using that email address.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if(re.match("^[a-zA-Z0-9]+([_-]?[a-zA-Z0-9])*$", username) is None or len(username)>40):
            raise forms.ValidationError("Username must contain only letters, digits, or '-' or '_' and at most 40 characters")
        return username

    def clean_confirm_password(self):
        password1 = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('confirm_password')
        if password1 and password2 and (password1 == password2):
            return password1
        else:
            raise forms.ValidationError('Passwords must match')

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        help_texts = {
            'username': "Required. 30 characters or fewer. Letters, digits and '-' or '_' only.",
        }


class EmailForm(forms.Form):
    subject = forms.CharField(label='Subject')
    message = forms.CharField(label='Message', widget=forms.Textarea)


class LookupForm(forms.Form):
    search_string = forms.CharField(max_length=100, label='Search String',
                                    help_text="Searches team names, team locations, usernames, "
                                              "first/last names, and user emails")

    def __init__(self, *args, **kwargs):
        super(LookupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline lookupdiv'
        self.helper.field_template = 'bootstrap5/layout/inline_field.html'
        self.helper.layout = Layout(
            'search_string',
            Submit('submit', 'Submit', css_class='btn btn-primary')
        )
