from django import forms


class FlightSearchForm(forms.Form):
    origin = forms.ChoiceField(
        label='From',
        label_suffix='',
        choices=[]
    )
    destination = forms.ChoiceField(
        label='To',
        label_suffix='',
        choices=[]
    )
    depart_date = forms.DateField(
        label='Depart',
        label_suffix='',
        widget=forms.DateInput({'type': 'date'}),
        input_formats=['%Y-%m-%d'],
    )
    return_date = forms.DateField(
        label='Return',
        label_suffix='',
        widget=forms.DateInput({'type': 'date'}),
        input_formats=['%Y-%m-%d'],
        required=False,
    )
    travellers = forms.IntegerField(
        label='Travellers',
        label_suffix='',
        min_value=1,
        max_value=6,
        initial=1,
        widget=forms.NumberInput()
    )

    def __init__(self, *args, **kwargs):
        origin_choices = kwargs.pop('origin_choices', [])
        destination_choices = kwargs.pop('destination_choices', [])
        super().__init__(*args, **kwargs)

        self.fields['origin'].choices = origin_choices
        self.fields['destination'].choices = destination_choices


class FlightBookForm(forms.Form):
    select_depart = forms.ChoiceField(
        label="Select departure",
        label_suffix='',
        widget=forms.RadioSelect,
        choices=[],
    )
    select_return = forms.ChoiceField(
        label="Select return",
        label_suffix='',
        widget=forms.RadioSelect,
        required=False,
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        depart_choices = kwargs.pop('depart_choices', [])
        return_choices = kwargs.pop('return_choices', [])
        super().__init__(*args, **kwargs)

        self.fields['select_depart'].choices = depart_choices
        if return_choices:
            self.fields['select_return'].choices = return_choices
            self.fields['select_return'].required = True


class CustomerDetailsForm(forms.Form):
    title = forms.ChoiceField(
        choices=[
            ('mr', 'Mr'),
            ('mrs', 'Mrs'),
            ('miss', 'Miss'),
            ('ms', 'Ms'),
        ],
        label='Title',
        label_suffix='',
    )
    fname = forms.CharField(
        label='First Name',
        label_suffix='',
        max_length=50,
    )
    lname = forms.CharField(
        label='Last Name',
        label_suffix='',
        max_length=50,
    )
    sex = forms.ChoiceField(
        choices=[
            ('m', 'Male'),
            ('f', 'Female'),
        ],
        label='Sex',
        label_suffix='',
        widget=forms.RadioSelect,
    )
    email = forms.EmailField(
        label='Email',
        label_suffix='',
        max_length=254,
    )


class EmailForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        max_length=254,
        widget=forms.EmailInput({'placeholder': 'Enter your email'})
    )

    def __init__(self, *args, **kwargs):
        label = kwargs.pop('label', None)
        placeholder = kwargs.pop('placeholder', None)
        super().__init__(*args, **kwargs)

        if label:
            self.fields['email'].label = label
        if placeholder:
            self.fields['email'].widget.attrs.update({'placeholder': placeholder})


class ConfirmForm(forms.Form):
    pass

class CancelForm(forms.Form):
    ref = forms.CharField(widget=forms.HiddenInput())

