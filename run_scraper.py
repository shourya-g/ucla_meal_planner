# run_scraper.py
"""
Script to run the menu scraper
"""
from scraper.menu_scraper import BruinPlateScraper

def main():
    scraper = BruinPlateScraper()
    
    # Scrape all items
    print("Starting full menu scrape...\n")
    foods = scraper.scrape_menu()
    
    print(f"\n✓ Complete! Scraped {len(foods)} items")
    print("Data saved to: data/menu_data.json")

if __name__ == "__main__":
    main()
