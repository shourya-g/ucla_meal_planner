import requests
import json

print("Testing Meal Optimization API...\n")

# Test 1: Single meal plan
print("=" * 60)
print("Test 1: Generate single meal plan (Lunch + Dinner)")
print("=" * 60)

response = requests.post('http://localhost:5000/api/optimize', json={
    "target_calories": 1500,
    "target_protein": 100,
    "selected_meals": ["lunch", "dinner"],
    "min_fruits": 2,
    "max_fruits": 4,
    "calorie_tolerance": 150,
    "protein_tolerance": 20
})

if response.status_code == 200:
    result = response.json()
    print(f"\nStatus: {result['status']}")
    print(f"Total Calories: {result['totals']['calories']:.0f}")
    print(f"Total Protein: {result['totals']['protein']:.1f}g")
    print(f"Items Selected: {result['num_items']}")
    print("\nMeals:")
    for meal_type in ["lunch", "dinner"]:
        if meal_type in result['meals'] and result['meals'][meal_type]:
            print(f"\n  {meal_type.upper()}:")
            for item in result['meals'][meal_type]:
                print(f"    - {item['name']} x{item['servings']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# Test 2: Multiple meal plans
print("\n\n" + "=" * 60)
print("Test 2: Generate 3 alternative meal plans")
print("=" * 60)

response = requests.post('http://localhost:5000/api/optimize/multiple', json={
    "num_plans": 3,
    "target_calories": 1500,
    "target_protein": 100,
    "selected_meals": ["lunch", "dinner"],
    "min_fruits": 2,
    "max_fruits": 4
})

if response.status_code == 200:
    result = response.json()
    print(f"\nGenerated {result['count']} plans\n")
    
    for i, plan in enumerate(result['plans'], 1):
        print(f"Plan {i}:")
        print(f"  Calories: {plan['totals']['calories']:.0f}")
        print(f"  Protein: {plan['totals']['protein']:.1f}g")
        print(f"  Items: {plan['num_items']}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)