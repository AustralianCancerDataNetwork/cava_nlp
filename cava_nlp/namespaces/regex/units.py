weight_units = ['kg', 'kilo', 'kilos', 'g', 'gr', 'kilogram', 'kilograms', 'kgs', 
                'BMI', 'bmi', 'lb', 'lbs', 'pounds', 'KG','Kg', 'kG']


# added special cases to capture units with a slash in the middle
units_num = ['mg', 'mcg', 'g', 'units', 'u', 'mgs', 'mcgs', 'gram', 'grams', 'mG', 'mL', 'mol']
units_denom = ['mg', 'mcg', 'g', 'kg', 'ml', 'l', 'm2', 'm^2', 'hr', 'liter', 'gram', 'L', 'mL', 'KG', 'MG',
               'mG', 'kG', 'kilogram', 'lb', 'pounds', 'lbs', 'kilos', 'Kg', 'mol', 'mmol']
unit_suffix = []

for a in units_num:
    for b in units_denom:
        if a != b:
            unit_suffix.append(f'{a}/{b}')

#units_regex = '|'.join([f'{u}' for u in units_denom])
units_regex = r'^(' + '|'.join(units_denom) + r')$'