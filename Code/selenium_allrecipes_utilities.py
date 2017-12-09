#
# Ian Hoffman (ijh6) and Tianjie Sun (ts755)
#
# selenium_allrecipes_demo.py
#
# Thursday, December 4th, 2017
#

import urllib
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium_allrecipes_recipe_elements import *
import aiy.audio
import aiy.cloudspeech
import aiy.voicehat

recognizer = aiy.cloudspeech.get_recognizer()

# Replace raw_input with recognizer
def voice_input(prompt):
	print (prompt)
	return recognizer.recognize()

CHROMIUM_DRIVER_PATH = '/usr/lib/chromium-browser/chromedriver'

# FSM actions
NO_ACTION = -1
COOK_RECIPE = 0
GO_TO_RESULTS = 1
GO_TO_SEARCH = 2
GO_TO_RECIPE = 3
GO_TO_INGREDIENTS = 4
REPEAT_STEP = 5
FINISHED_RECIPE = 6

# State options
OPTION_STRINGS = {
	'RECIPE': "To show ingredients, type 'ingredients'. To cook this recipe, type 'cook'. To go back to results, type 'results'. To go back to search, type 'search'.",
	'INGREDIENT': "To cook this recipe, type 'cook'. To go back to the recipe, type 'recipe'. To go back to results, type 'results'. To go back to search, type 'search'."
}
VIEW_OPTIONS = {
	'RECIPE': ['cook', 'results', 'ingredients', 'search'],
	'INGREDIENT': ['repeat', 'cook', 'recipe', 'results', 'search']
}

RECOGNIZED_INGREDIENTS = []

def load_ingredients(filename):
	with open(filename) as f:
		global RECOGNIZED_INGREDIENTS
		RECOGNIZED_INGREDIENTS += sorted([line.strip() for line in f.readlines()], key = len, reverse = True)

def get_ingredients_from_string(str):
	parsed_ingredients = []
	if str == '':
		return []
		
	for ingredient in RECOGNIZED_INGREDIENTS:
		if ingredient in str:
			parsed_ingredients.append(ingredient)
			str = str.replace(ingredient, '')
			
	return parsed_ingredients

def get_chrome_driver():
	# Use option to disable image loading for speedy load and enable headless browser mode
	chrome_options = Options()
	chrome_options.add_argument("--headless")
	prefs = {'profile.managed_default_content_settings.images': 2}
	chrome_options.add_experimental_option('prefs', prefs)

	return webdriver.Chrome(executable_path=CHROMIUM_DRIVER_PATH, chrome_options=chrome_options)

def get_phantomjs_driver():
	return webdriver.PhantomJS(service_args=['--load-images=no'])

def get_ingredients(driver):
	# Keep entering ingredients (user-prompted in Terminal, for now) until empty line
	ingredients_entered = []
	while True:
		prompt = "What ingredients do you have?" if ingredients_entered == [] else "What else?"
		aiy.audio.say(prompt)
		spoken_words = voice_input(prompt)
		spoken_words = spoken_words.lower() if spoken_words != None else ''
		found_ingredients = get_ingredients_from_string(spoken_words)

		# Empty line entered
		if 'nothing' in spoken_words or 'that\'s all' in spoken_words or 'that\'s it' in spoken_words:
			# Don't search on empty line if no ingredients have been entered
			if len(ingredients_entered) == 0:
				print ('No ingredients entered')
				aiy.audio.say('I can\'t find you recipes without any ingredients!')
				continue

			# Break out of ingredient entry loop if we have ingredients and search for recipes
			print ('Searching recipes...')
			aiy.audio.say('I\'m finding you some recipes now!')
			break
		
		if found_ingredients == []:
			continue

		# Ingredient entered
		ingredients_entered += found_ingredients
		print (found_ingredients)
		
		aiy.audio.say('Okay, you have')
		for found_ingredient in found_ingredients:
			aiy.audio.say(found_ingredient)

	return ingredients_entered

def get_recipes_info(driver):
	# Get recipe cards and filter by those with an 'a.favorite' child since
	# valid recipes have a favorite button (ads and unrelated recipes do not)
	recipe_cards = driver.find_elements_by_css_selector('div#searchResultsApp article')
	total_cards = len(recipe_cards)
	recipe_cards = [card for card in recipe_cards if len(card.find_elements_by_css_selector('a.favorite')) > 0]
	filtered_cards = total_cards - len(recipe_cards)

	parsed_cards = []
	for recipe_card in recipe_cards:
		# 2 different ways to represent text header/link
		name_link_1 = recipe_card.find_elements_by_css_selector('h3 a')
		name_link_2 = recipe_card.find_elements_by_css_selector('a h3')

		name_text = ''
		if len(name_link_1) != 0:
			name_text = name_link_1[0].text
			# Sometimes the text for a card is within a span
			if name_text == '':
				span_element = name_link_1[0].find_elements_by_css_selector('span')
				if len(span_element) > 0:
					name_text = span_element[0].text
		elif len(name_link_2) != 0:
			name_text = name_link_2[0].text

		# Get link address and rating
		recipe_links = recipe_card.find_elements_by_css_selector('a:not(.favorite)')
		recipe_link = [link for link in recipe_links if len(link.find_elements_by_css_selector('div.grid-col__ratings')) > 0][0]

		link_address = recipe_link.get_attribute('href')
		rating = recipe_link.find_element_by_css_selector('div.grid-col__ratings span.stars').get_attribute('data-ratingstars')
		rating = round(float(rating), 1)

		if name_text != '':
			parsed_cards.append((name_text, rating, link_address))
		else:
			filtered_cards += 1

	return (parsed_cards, total_cards, filtered_cards)

def reverse_key_value(k, v):
	return (v, k)

def get_common_recipe_substrings(recipes_info, num_results):
	substring_count_dict = {}

	for recipe_info in recipes_info:
		split_name = recipe_info[0].split()
		for i in range(len(split_name)):
			for j in range(i, len(split_name)):
				if i == j:
					continue

				substring = ' '.join(split_name[i : (j + 1)])
				if substring in substring_count_dict:
					substring_count_dict[substring] += 1
				else:
					substring_count_dict[substring] = 1

	# Sort results by frequency and return the num_results most common substrings (discarding counts)
	return [k for v,k in sorted([(v, k) for k,v in substring_count_dict.items()], reverse=True)][:num_results]

def construct_search_url(ingredients):
	ingredient_url_string = urllib.parse.quote(','.join(ingredients))
	full_search_url = 'http://allrecipes.com/search/results/?ingIncl=' + ingredient_url_string + '&sort=re'
	return full_search_url

def get_recipe_elements_from_recipe_info(driver, recipe_info):
	# Load recipe in other tab
	driver.switch_to_window(driver.window_handles[1])
	driver.get(recipe_info[2])

	# Get all relevant recipe info and print it (for now)
	recipe_elements = RecipeElements(driver, recipe_info)

	# Switch back to search tab and return recipe elements
	driver.switch_to_window(driver.window_handles[0])
	return recipe_elements

def not_valid_step_from_view(step, view_options):
	if step == None:
		step = ''
	found_match = False
	for action in view_options:
		if action in step:
			found_match = True
			break
	return (not found_match)

def parse_step(step):
	if 'cook' in step:
		return COOK_RECIPE
	elif 'results' in step:
		return GO_TO_RESULTS
	elif 'ingredients' in step:
		return GO_TO_INGREDIENTS
	elif 'recipe' in step:
		return GO_TO_RECIPE
	elif 'search' in step:
		return GO_TO_SEARCH
	elif 'repeat' in step:
		return REPEAT_STEP
	else:
		return NO_ACTION

def get_next_step_from_view(view_name):
	subsequent_step = ''
	while not_valid_step_from_view(subsequent_step, VIEW_OPTIONS[view_name]):
		subsequent_step = voice_input(OPTION_STRINGS[view_name])
	return parse_step(subsequent_step)

def cook_mode(steps):
	aiy.audio.say("Great! Let's get cooking! Are you ready?")
	spoken_words = ''
	while True:
		spoken_words = voice_input("Are you ready to cook?")
		if spoken_words == None:
			continue
			
		spoken_words = spoken_words.lower()
		
		if 'yes' in spoken_words:
			break
		if 'no' in spoken_words:
			print ("Cook process cancelled")
			aiy.audio.say("That's ok! I hope you want to cook with me soon.")
			return GO_TO_RECIPE
		
		aiy.audio.say("I'm sorry, I don't understand.")
	
	# We've confirmed the cook, now let's cook
	aiy.audio.say("Ok. I'll give you the first step.")
	current_step = 0
	while current_step < len(steps):
		aiy.audio.say(steps[current_step])
		
		# See if the user wants to move on, restart, go back, stop, or repeat
		spoken_words = ''
		while True:
			spoken_words = voice_input("User action during cook")
			if spoken_words == None:
				continue
				
			spoken_words = spoken_words.lower()
			
			if 'restart' in spoken_words:
				current_step = 0
				print ("Restarting recipe")
				aiy.audio.say("Ok. Let's start over.")
				break
			if 'next' in spoken_words:
				current_step += 1
				print ("Advancing to next step")
				if current_step < len(steps):
					aiy.audio.say("Here's the next step")
				break
			if 'previous' in spoken_words:
				if current_step == 0:
					aiy.audio.say("We're already on the first step")
					continue
				current_step -= 1
				print ("Going back to the previous step")
				aiy.audio.say("Let's redo that")
				break
			if 'repeat' in spoken_words:
				print ("Repeating step")
				aiy.audio.say("Let's hear that again")
				break
			if 'stop' in spoken_words:
				print ("Stopping cook")
				aiy.audio.say("Ok. Let's cook again soon.")
				return FINISHED_RECIPE
			
			aiy.audio.say("I'm sorry, I don't understand.")
	
	aiy.audio.say("You finished the recipe! Great job!")
	return FINISHED_RECIPE

def ingredients_mode(ingredients):
	print ("\nIngredients:")
	aiy.audio.say("This recipe's ingredients are")
	
	for ingredient in ingredients:
		print (ingredient)
		aiy.audio.say(ingredient)
		
	print ('\n')
	
	return get_next_step_from_view('INGREDIENT')

def get_calorie_class(calorie_string):
	try:
		calorie_num = int(calorie_string)
		if calorie_num < 400:
			return 'low'
		if calorie_num < 800:
			return 'medium'
		return 'high'
	except ValueError:
		return 'medium'
