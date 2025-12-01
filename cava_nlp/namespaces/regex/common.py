# emails = r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9]+(\.[A-Za-z]{2,3})+' - this version caused catastrophic backtracking on long strings
emails = r'\w+(?:[.-]\w+)*@\w+(?:[.-]\w+)*(?:\.\w{2,3})+'
# single alpha char with no whitespace to merge abbreviatons like p.o. or i.v.
abbv = r'^[a-zA-Z]$'
# alpha string of arbitrary length with no whitespace as 2nd part of abbreviations like o/night b'fast 
no_whitespace = r'^[a-zA-Z]+$'