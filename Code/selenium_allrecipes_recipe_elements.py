#
# Ian Hoffman (ijh6) and Tianjie Sun (ts755)
#
# selenium_allrecipes_demo.py
#
# Thursday, December 5th, 2017
#

import re

def expand_time_string(string):
	split_str = string.split()
	
	# Get singular or plural version of hour after hour value if it exists
	try:
		hour_index = split_str.index('h')
		split_str[hour_index] = 'hour' if split_str[hour_index - 1] == '1' else 'hours'
	except ValueError:
		pass

	# Get singular or plural version of minute after minute value if it exists
	try:
		minute_index = split_str.index('m')
		split_str[minute_index] = 'minute' if split_str[minute_index - 1] == '1' else 'minutes'
	except ValueError:
		pass

	return ' '.join(split_str)

DENOMINATOR_WORDS_SINGULAR = {
	2: 'half',
	3: 'third',
	4: 'quarters',
	5: 'fifth',
	6: 'sixth',
	7: 'seventh',
	8: 'eighth',
	9: 'ninth',
	10: 'tenth',
	11: 'eleventh',
	12: 'twelfth',
	13: 'thirteenth',
	14: 'fourteenth',
	15: 'fifteenth',
	16: 'sixteenth'
}

DENOMINATOR_WORDS_PLURAL = {
	2: 'halves',
	3: 'thirds',
	4: 'quarters',
	5: 'fifths',
	6: 'sixths',
	7: 'sevenths',
	8: 'eighths',
	9: 'ninths',
	10: 'tenths',
	11: 'elevenths',
	12: 'twelfths',
	13: 'thirteenths',
	14: 'fourteenths',
	15: 'fifteenths',
	16: 'sixteenths'
}

def denominator_to_word(value, pluralize):
	return (DENOMINATOR_WORDS_PLURAL if pluralize else DENOMINATOR_WORDS_SINGULAR)[value]

def fraction_replace(match):
	string = match.group()
	split_str = string.split()
	output_string = ''
	
	# If we have an improper fraction, add an 'and'
	if len(split_str) > 1:
		output_string += split_str[0] + ' and '
		string = split_str[1]
	
	# Convert fraction to speech-compatible fraction
	parts = string.split('/')
	output_string += parts[0] + ' '
	output_string += denominator_to_word(int(parts[1]), parts[0] != '1')
	return output_string

# Converts a string with fractions to speech-compatible fractions
def convert_fraction_string(string):
	return re.sub(r'([\d]* )?[\d]+/[\d]+', fraction_replace, string)

class RecipeElements:

	def __init__(self, driver, recipe_info):
		# Get simple single-step values
		self.name = recipe_info[0]
		self.rating = recipe_info[1]
		self.url = recipe_info[2]

		# Two-step values (need an existence check)
		servings_span = driver.find_elements_by_css_selector('span.servings-count span:not(servings-count__desc)')
		self.servings = servings_span[0].text if servings_span != [] else None

		prep_time_elt = driver.find_elements_by_css_selector('time[itemprop="prepTime"]')
		self.prep_time = expand_time_string(prep_time_elt[0].text) if prep_time_elt != [] else None

		cook_time_elt = driver.find_elements_by_css_selector('time[itemprop="cookTime"]')
		self.cook_time = expand_time_string(cook_time_elt[0].text) if cook_time_elt != [] else None

		total_time_elt = driver.find_elements_by_css_selector('time[itemprop="totalTime"]')
		self.total_time = expand_time_string(total_time_elt[0].text) if total_time_elt != [] else None

		self.has_times = (self.total_time != None) and (self.cook_time != None) and (self.prep_time != None)

		calories_elt = driver.find_elements_by_css_selector('span.calorie-count')
		self.calories = calories_elt[0].text if calories_elt != [] else None

		# Get ingredient list
		self.ingredients = []
		ingredient_dom_nodes = driver.find_elements_by_css_selector('span.recipe-ingred_txt')
		for ingredient_dom_node in ingredient_dom_nodes:
			ingredient_text = ingredient_dom_node.text
			if ingredient_text != 'Add all ingredients to list':
				self.ingredients.append(convert_fraction_string(ingredient_text))

		# Get list of steps
		self.steps = []
		recipe_step_dom_nodes = driver.find_elements_by_css_selector('span.recipe-directions__list--item')
		for recipe_step_dom_node in recipe_step_dom_nodes:
			recipe_step_text = recipe_step_dom_node.text
			if recipe_step_text != '':
				self.steps.append(convert_fraction_string(recipe_step_text))

