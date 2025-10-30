# scraper/menu_scraper.py
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import re
import os


class BruinPlateScraper:
    def __init__(self):
        self.base_url = "https://dining.ucla.edu/bruin-plate/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_menu(self, max_items=None):
        """
        Scrape the full menu with nutrition details
        max_items: limit number of items (None for all)
        """
        print("Fetching main menu page...")
        response = requests.get(self.base_url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch page: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"✓ Successfully fetched page (Status: {response.status_code})")
        
        # Build a map of food items with their meal times and categories
        food_items_with_meta = self.map_foods_to_meals_and_sections(soup)
        
        if max_items:
            food_items_with_meta = food_items_with_meta[:max_items]
        
        total_items = len(food_items_with_meta)
        print(f"✓ Found {total_items} food items\n")
        
        all_foods = []
        
        for idx, item_info in enumerate(food_items_with_meta, 1):
            try:
                link = item_info['link']
                food_name = item_info['name']
                meal_time = item_info['meal_time']
                category = item_info['category']
                
                # Get the detail page URL
                detail_url = link.get('href')
                
                if not detail_url:
                    print(f"  Skipping item {idx} (no URL)")
                    continue
                
                # Make absolute URL
                if detail_url.startswith('/'):
                    detail_url = f"https://dining.ucla.edu{detail_url}"
                
                print(f"[{idx}/{len(food_items_with_meta)}] {food_name} ({meal_time}) [{category}]")
                
                # Fetch nutrition details
                nutrition = self.get_nutrition_details(detail_url, food_name, meal_time)
                
                if nutrition:
                    nutrition['category'] = category
                    all_foods.append(nutrition)
                    print(f"  ✓ {nutrition['calories']} cal, {nutrition['protein']}g protein\n")
                else:
                    print(f"  ✗ Failed to extract nutrition\n")
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  ✗ Error: {e}\n")
                continue
        
        print(f"\n{'='*60}")
        print(f"Successfully extracted {len(all_foods)}/{len(food_items_with_meta)} food items")
        print(f"{'='*60}\n")
        
        self.save_to_json(all_foods)
        return all_foods
    
    def map_foods_to_meals_and_sections(self, soup):
        """
        Map each food item to its meal time and section/category
        """
        food_items = []
        
        # Known section headers (lowercase, normalized)
        SECTION_HEADERS = [
            'freshly bowled', 'harvest', 'stone fired', 'simply grilled',
            'farmstand', 'soups', 'fruit', 'sweet bites', 'yogurt bar',
            'cereal / oatmeal', 'beverage special', 'greens \'n more',
            'frozen yogurt', 'grab & go'
        ]
        
        all_links = soup.find_all('a', string='See Meal Details')
        
        for link in all_links:
            food_name = self.extract_food_name(link)
            
            # Find category by searching backwards for section headers (must match known list)
            food_category = "unknown"
            current_element = link

            for _ in range(30):  # Search depth limit
                prev_heading = current_element.find_previous(['h2', 'h3', 'h4'])
                if not prev_heading:
                    break
                heading_text = prev_heading.get_text(strip=True).lower()
                # Must match known section exactly (not food names)
                # Use normalized comparison and ignore case
                match = next((section for section in SECTION_HEADERS if section in heading_text), None)
                if match:
                    food_category = match.title()  # For nice capitalization
                    break
                
                # Stop if we hit a meal header (we've gone too far)
                if any(meal in heading_text for meal in ['breakfast', 'lunch', 'dinner']):
                    break
                current_element = prev_heading

            # Find meal time
            current_meal = "unknown"
            current_element = link
            for _ in range(50):
                prev = current_element.find_previous(['h2', 'h1'])
                if prev:
                    heading_text = prev.get_text(strip=True).upper()
                    if 'BREAKFAST' in heading_text:
                        current_meal = 'breakfast'
                        break
                    elif 'LUNCH' in heading_text:
                        current_meal = 'lunch'
                        break
                    elif 'DINNER' in heading_text:
                        current_meal = 'dinner'
                        break
                    current_element = prev
                else:
                    break
            
            food_items.append({
                'link': link,
                'name': food_name,
                'meal_time': current_meal,
                'category': food_category
            })
        
        return food_items

    
    def extract_food_name(self, link):
        """Extract food name from the menu page"""
        food_name = "Unknown"
        try:
            parent = link.find_parent(['li', 'div', 'article'])
            if parent:
                heading = parent.find(['h3', 'h4', 'h5'])
                if heading:
                    food_name = heading.get_text(strip=True)
            
            if food_name == "Unknown":
                prev_heading = link.find_previous(['h3', 'h4', 'h5'])
                if prev_heading:
                    heading_text = prev_heading.get_text(strip=True)
                    # Make sure it's not a category heading
                    if heading_text and not any(cat in heading_text.lower() for cat in 
                        ['breakfast', 'lunch', 'dinner', 'freshly bowled', 'harvest', 
                         'stone fired', 'simply grilled', 'farmstand', 'soups', 'fruit', 
                         'sweet bites', 'yogurt', 'cereal', 'beverage', 'greens']):
                        food_name = heading_text
        except Exception:
            pass
        
        return food_name
    
    def get_nutrition_details(self, url, food_name, meal_time):
        """Fetch and parse nutrition information from detail page"""
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if food_name == "Unknown":
                title = soup.find(['h1', 'h2'])
                if title:
                    food_name = title.get_text(strip=True)
            
            nutrition = {
                'name': food_name,
                'meal_time': meal_time,
                'url': url,
                'calories': 0,
                'protein': 0,
                'carbs': 0,
                'fat': 0,
                'fiber': 0,
                'sodium': 0,
                'serving_size': '',
                'dietary_tags': []
            }
            
            page_text = soup.get_text()
            
            # Extract serving size
            serving_match = re.search(r'Serving Size:\s*([^\n]+?)(?:Calories|\n)', page_text, re.IGNORECASE)
            if serving_match:
                nutrition['serving_size'] = serving_match.group(1).strip()
            
            # Extract calories
            calories_match = re.search(r'Calories\s*(\d+)', page_text, re.IGNORECASE)
            if calories_match:
                nutrition['calories'] = float(calories_match.group(1))
            
            # Extract macros
            fat_match = re.search(r'Total Fat\s*([\d.]+)\s*g', page_text, re.IGNORECASE)
            if fat_match:
                nutrition['fat'] = float(fat_match.group(1))
            
            carb_match = re.search(r'Total Carbohydrate\s*([\d.]+)\s*g', page_text, re.IGNORECASE)
            if carb_match:
                nutrition['carbs'] = float(carb_match.group(1))
            
            protein_match = re.search(r'Protein\s*([\d.]+)\s*g', page_text, re.IGNORECASE)
            if protein_match:
                nutrition['protein'] = float(protein_match.group(1))
            
            fiber_match = re.search(r'Dietary Fiber\s*([\d.]+)\s*g', page_text, re.IGNORECASE)
            if fiber_match:
                nutrition['fiber'] = float(fiber_match.group(1))
            
            sodium_match = re.search(r'Sodium\s*([\d.]+)\s*mg', page_text, re.IGNORECASE)
            if sodium_match:
                nutrition['sodium'] = float(sodium_match.group(1))
            
            # Extract dietary tags
            allergen_match = re.search(r'Allergens\*?:\s*([^\n]+)', page_text, re.IGNORECASE)
            if allergen_match:
                allergen_text = allergen_match.group(1).lower()
                if 'gluten' in allergen_text:
                    nutrition['dietary_tags'].append('contains_gluten')
                if 'dairy' in allergen_text or 'milk' in allergen_text:
                    nutrition['dietary_tags'].append('contains_dairy')
                if 'eggs' in allergen_text:
                    nutrition['dietary_tags'].append('contains_eggs')
            
            if 'vegan' in page_text.lower():
                nutrition['dietary_tags'].append('vegan')
            elif 'vegetarian' in page_text.lower():
                nutrition['dietary_tags'].append('vegetarian')
            
            return nutrition
            
        except Exception as e:
            print(f"    Error fetching details: {e}")
            return None
    
    def save_to_json(self, foods):
        """Save extracted food data to JSON"""
        data = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'scraped_at': datetime.now().isoformat(),
            'total_items': len(foods),
            'foods': foods
        }
        
        filename = 'data/menu_data.json'
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Saved {len(foods)} items to {filename}")
        
        breakfast_count = sum(1 for f in foods if f['meal_time'] == 'breakfast')
        lunch_count = sum(1 for f in foods if f['meal_time'] == 'lunch')
        dinner_count = sum(1 for f in foods if f['meal_time'] == 'dinner')
        
        print(f"\nMeal breakdown:")
        print(f"  Breakfast: {breakfast_count} items")
        print(f"  Lunch: {lunch_count} items")
        print(f"  Dinner: {dinner_count} items")
        
        if foods:
            avg_calories = sum(f['calories'] for f in foods) / len(foods)
            avg_protein = sum(f['protein'] for f in foods) / len(foods)
            print(f"\nAverage per item:")
            print(f"  Calories: {avg_calories:.0f}")
            print(f"  Protein: {avg_protein:.1f}g")


if __name__ == "__main__":
    scraper = BruinPlateScraper()
    print("Scraping full menu...\n")
    print("="*60)
    foods = scraper.scrape_menu()  # Full scrape
