#
# Ian Hoffman (ijh6) and Tianjie Sun (ts755)
#
# selenium_allrecipes_demo.py
#
# Thursday, November 16th, 2017
#

#
# Note: this script requires having the Chrome webdriver in PATH.
# This webdriver (or one for another browser of your choice) can
# be downloaded here: https://sites.google.com/a/chromium.org/chromedriver/downloads
#

from selenium_allrecipes_utilities import *
from subprocess import call

GREETING_ENABLED = True
VOLUME = 30

def button_func():
    print ("Shutting down...")
    driver.quit()
    call("sudo shutdown -h now", shell=True)

def main(driver):
	# Current action in control flow
	action = NO_ACTION
	
	# Greeting
	if GREETING_ENABLED:
		aiy.audio.say("""
			Hi! I'm Recipe Helper, an assistant for your recipe needs.
			I can find recipes using the ingredients you have in your
			kitchen, and walk you through them. Let's get started!
		""")

	# Ingredient search loop
	while True:
		ingredients = get_ingredients(driver)
		driver.get(construct_search_url(ingredients))

		# Result navigation loop
		recipes_info, recipes_found, recipes_filtered = (None, None, None)
		while True:
			# Parse recipe cards on page into essential info (recipe name, rating, and hyperlink)
			if action != GO_TO_RESULTS:
				recipes_info, recipes_found, recipes_filtered = get_recipes_info(driver)
			else:
				action = NO_ACTION

			result_string = "I found you %d recipes and removed %d unrelated results" % (len(recipes_info), recipes_filtered)
			print (result_string)
			aiy.audio.say(result_string)

			# Get most common substring and print it
			common_substrings = get_common_recipe_substrings(recipes_info, 1)
			if len(common_substrings) > 0:
				# This won't be true if there is no multi-word overlap between recipes
				common_term_string = "The most common term I found was %s" % common_substrings[0]
				print (common_term_string)
				aiy.audio.say(common_term_string)

			# Get recipe selection (by number for now)
			print ("Select your recipe from the following examples by saying the number:")
			aiy.audio.say("Say next to hear the next recipe, previous to hear the previous recipe, or go to choose a recipe.")
			
			current_index = 0
			chosen_index = None
			while chosen_index == None:
				curr = recipes_info[current_index]
				aiy.audio.say("%s, rated %.1f out of %d stars" % (curr[0], curr[1], 5))
				
				# Get response
				request = ''
				while True:
					request = voice_input("next, previous, or go")
					if request == None:
						print ("Couldn't hear you")
						aiy.audio.say("I'm sorry, I didn't catch that")
						continue
					
					if 'next' in request:
						if current_index == len(recipes_info) - 1:
							print ('No more recipes')
							aiy.audio.say('There are no more recipes!')
							continue
						
						current_index += 1
						break
					elif 'previous' in request:
						if current_index == 0:
							print ('Already on first recipe')
							aiy.audio.say('This is already the first recipe!')
							continue
						
						current_index -= 1
						break
					elif 'go' in request:
						chosen_index = current_index
						break
					else:
						print ('Unrecognized command')
						aiy.audio.say("I don't understand. Try saying next, previous, or go.")

			# Recipe view
			recipe_elements = None
			while True:
				chosen_recipe_string = "You chose %s." % recipes_info[chosen_index][0]
				print (chosen_recipe_string)
				aiy.audio.say(chosen_recipe_string)

				# Get all relevant recipe info and print it (for now)
				if action != GO_TO_RECIPE and action != FINISHED_RECIPE:
					print ("Loading recipe...")
					print ('\n')
					aiy.audio.say("I'm loading this recipe now!")
					recipe_elements = get_recipe_elements_from_recipe_info(driver, recipes_info[chosen_index])
				#else:
				#	action = NO_ACTION

				print ("Recipe name: %s" % recipe_elements.name)
				print ("Recipe rating: %s" % recipe_elements.rating)
				print ("Serves %s" % recipe_elements.servings)
				print ("Contains %s calories" % recipe_elements.calories)
				print ("Cook time: %s" % recipe_elements.cook_time)
				print ("Prep time: %s" % recipe_elements.prep_time)
				print ("Total time: %s" % recipe_elements.total_time)
				print ('\n')
				
				# Only say recipe information if the recipe is not done after cooking
				if action != FINISHED_RECIPE and action != GO_TO_RECIPE:
					aiy.audio.say("%s" % recipe_elements.name)
					if recipe_elements.servings != None:
						aiy.audio.say("This recipe serves %s people." % recipe_elements.servings)
					if recipe_elements.calories != None:
						aiy.audio.say("This recipe has %s calories." % recipe_elements.calories)
						calorie_class = get_calorie_class(recipe_elements.calories)
						aiy.audio.say("This is a %s calorie food" % calorie_class)
					if recipe_elements.has_times:
						aiy.audio.say("This recipe takes %s to prep, %s to cook, and %s total." % (recipe_elements.prep_time, recipe_elements.cook_time, recipe_elements.total_time))
				else:
					action = NO_ACTION

				# Get next step from recipe view
				step_result = get_next_step_from_view('RECIPE')
				if step_result == GO_TO_SEARCH or step_result == GO_TO_RESULTS:
					# Break out of recipe view to search or results
					action = step_result
					break
				elif step_result == GO_TO_INGREDIENTS:
					step_result = ingredients_mode(recipe_elements.ingredients)
					while step_result == REPEAT_STEP:
						step_result = ingredients_mode(recipe_elements.ingredients)
					if step_result == GO_TO_SEARCH or step_result == GO_TO_RESULTS:
						action = step_result
						break

				# Separate if so that you can enter cook mode from ingredient mode
				if step_result == COOK_RECIPE:
					# Cook recipe and do actions similar to above
					step_result = cook_mode(recipe_elements.steps)
					if step_result == GO_TO_SEARCH or step_result == GO_TO_RESULTS:
						action = step_result
						break
				
				# Reuse currently loaded recipe without reloading it (time-saver)
				if step_result == GO_TO_RECIPE or step_result == FINISHED_RECIPE:
					action = step_result

			# Break out of results view
			if action == GO_TO_SEARCH:
				action = NO_ACTION
				break

if __name__ == '__main__':
	load_ingredients('/home/pi/voice-recognizer-raspi/src/ingredients.txt')
	driver = get_phantomjs_driver()
	global DRIVER
	DRIVER = driver

	# Open new tab for recipe access, then return to search tab
	driver.execute_script('window.open();')
	driver.switch_to_window(driver.window_handles[0])
	
	# Set up AIY resources
	aiy.audio.get_recorder().start()
	aiy.audio.set_tts_volume(VOLUME)
	aiy.voicehat.get_button().on_press(button_func)

	# Run main recipe helper function
	try:
		main(driver)
	except KeyboardInterrupt:
		print ("Exiting...")
		driver.quit()

