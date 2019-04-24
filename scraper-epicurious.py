#!/usr/bin/env python3

import json
import base64
import requests

from pymongo import MongoClient
from scraperConnection import simple_get
from bs4 import BeautifulSoup


def get_html(page):
    '''
    This function grabs the search html for a recipe search based on name of meal

    :param query:
    :return:
    '''

    # Overall website 
    search_url = "https://www.epicurious.com/search?content=recipe&page={}&sort=highestRated".format(page)

    raw_search_html = simple_get(search_url)

    if raw_search_html:
        search_html = BeautifulSoup(raw_search_html, "html.parser")

        return search_html
    else:
        print ("failed")



def get_recipes():
    """
    This function returns n recipes with all the data associated with them
    based on ingredient, word, or category search
    :param search_type, num_recipes, query:
    :return:
    """
    pyclient = MongoClient()
    db = pyclient["chive"]
    collection = db["recipes"]
        
    recipes = []

    # Pages for loop, inserts each recipe

    #for page in range(1, 1994):
    for page in range(20, 40):
        search_html = get_html(page)

        # Pulls individual recipe webstie from recipe card
        for i, article in enumerate(search_html.find_all("article", {"class": "recipe-content-card"})):
            recipe_url = article.find("a")["href"]

            # gets data and fixes recipe link
            data_to_insert = get_recipe_info("https://www.epicurious.com{}".format(recipe_url))
            
            # Inserts into mongo database
            collection.insert_one(data_to_insert)

        # Print page to see progress of scraper
        print("Page: {} visited".format(page))



def get_recipe_info(url):
    '''
    Function to call all recipe information functions
    combines into final data dictionary 
    input: url for recipe
    output data dictionary
    '''
    raw_recipe_html = simple_get(url)
    recipe_html = BeautifulSoup(raw_recipe_html, "html.parser")


    name = get_recipe_name(recipe_html)
    description = get_description(recipe_html)
    rating = get_rating(recipe_html)
    ingredients = get_ingredients(recipe_html)
    directions = get_directions(recipe_html)
    image = get_image(recipe_html)

    data = {"name" : name, "description" : description, "ingredients" : ingredients, 
    "directions" : directions, "rating" : rating, "image" : image, "source": url, 
    "siteName": "epicurious"}
    print(data)
    
    return(data)    



def get_recipe_name(html):
    '''
    Function to retrieve recipe name from epicurious recipe site
    input: html : BeautifulSoup object
    output: name : string
    '''

    name = html.find("h1", {"itemprop" : "name"}).text.strip()
    return(name)

def get_rating(html):
    '''
    Function to retrieve rating of recipe 
    input: html : BeautifulSoup object
    output: rating : string
    '''
    rating = html.find("span", {"class" : "rating"})
    rating = rating.text.strip()
    rating = rating.split("/")
    rating = float(rating[0])/float(rating[1])
    return(rating)

def get_description(html):
    '''
    Function to retrieve description, if available, of recipe
    input: html : BeautifulSoup object
    output: desc : string 
    '''
    try:
        desc = html.find("div", {"itemprop" : "description"}).find('p').text.strip()
    except Exception as _:
        desc = ""
    return(desc)


def get_ingredients(html):
    '''
    Function to retrieve ingredients split by ingredient groups, if necessary, and parses
    them into ingredient quantity and unit of the ingredient string
    input: html : BeautifulSoup object
    output: ingredients : dict(ingredient : string, quantity : string, unit : string)
    '''
    # Unit array used in parsing
    units = ["pinch ", "pint ", "pints " ,"tsp. ", "teaspoons ", "teaspoon ", "Tbsp. ", "tablespoons ", "tablespoon ", "cups ", "cup ", "ounces ", "ounce ", "oz. ", "pounds ", "pound ", "lb. "]

    # for ingredient groups look for strong tag else default will be ingredients
    ingredient_groups = html.find_all("li", {"class" : "ingredient-group"})

    # continue search for ingredients on default group case
    ingredients = []
    for group in ingredient_groups:

        # continue search for ingredients on default group case

        group_name = None

        try:
            # more than one group
            group_name = group.find("strong").text.strip()
        except Exception as _:
            # one ingredient group
            group_name = "Ingredients"

        # Holds all ingredients in one ingredient group ie ("For dough : flour, etc")
        group_ingredients = []
        for i, li in enumerate(group.find_all('li', {"class":"ingredient"})):
            unit_found = False

            ingredient_string = li.text.strip()

            for unit in units:
                if unit in ingredient_string:
                    ingredient_string = ingredient_string.split(unit)
                    unit_found = True
                    break
            if not unit_found:
                ingredient_string = ingredient_string.split(" ")
                if ingredient_string[0].isdigit(): 
                    unit = ""
                    quantity = ingredient_string[0]
                    ingredient = ingredient_string[1:]
                    ingredient = ' '.join(ingredient)
                else:
                    unit = ""
                    quantity = ""
                    ingredient = ' '.join(ingredient_string)
            else:
                quantity = ingredient_string[0]
                ingredient = ingredient_string[1]


            group_ingredients.append({"name" : ingredient.strip(), "quantity" : quantity.strip(), "unit" : unit.strip()})
        
            group = {"groupName": group_name, "ingredients": group_ingredients}

        ingredients.append(group)
    return(ingredients)


        


def get_directions(html):
    '''
    Function to retrieve directions for recipe
    input: html : BeautifulSoup object
    output: directions : list(direction : string)
    '''
    # Holds all directions in this array
    directions = []
    for i, li in enumerate(html.find_all("li", {"class": "preparation-step"})):
        step = li.text.strip()
        directions.append(step)
    return(directions)


def get_image(html):
    '''
    Function to retrieve image src for recipe
    input: html : BeautifulSoup object
    output: image : string
    '''
    try:
        image_src = html.find("div", {"class" : "recipe-image"}).find('source')['srcset']
        image = base64.b64encode(requests.get(image_src).content)
    except Exception as _:
        image = ""

    return(image)


#def main():
if __name__ == "__main__":
    # Start the scraper
    get_recipes()