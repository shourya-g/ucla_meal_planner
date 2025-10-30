"""
Bruin Plate Meal Optimizer - Enhanced Version
==============================================
This module uses linear programming to create optimal meal plans based on
nutritional targets and constraints.

Features:
- Select specific meals (breakfast, lunch, dinner, or any combination)
- Generate multiple alternative meal plans
- Configurable nutritional targets and constraints

Author: Shourya goyal 
Date: 2025-10-28
"""

import json
from typing import Dict, List, Optional
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus, value, LpConstraint


class MealOptimizer:
    """
    Optimizes meal selection based on nutritional targets and constraints.
    
    The optimizer uses linear programming to select food items that:
    - Meet calorie and protein targets (with tolerance ranges)
    - Ensure balanced meals (each meal has at least 1/4 of total calories)
    - Maximize protein while minimizing repetition
    - Respect fruit consumption limits
    """
    
    def __init__(self, menu_data_path: str = "data/menu_data.json"):
        """
        Initialize the optimizer with menu data.
        
        Args:
            menu_data_path: Path to the JSON file containing menu items
        """
        self.menu_data = self._load_menu_data(menu_data_path)
        self.foods = self.menu_data.get("foods", [])
        
    def _load_menu_data(self, path: str) -> Dict:
        """Load menu data from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)
    
    def optimize_meal_plan(
        self,
        target_calories: float,
        target_protein: float,
        selected_meals: List[str] = None,
        min_fruits: int = 1,
        max_fruits: int = 3,
        calorie_tolerance: float = 300,
        protein_tolerance: float = 20,
        diversity_weight: float = 0.1,
        max_servings_per_item: int = 3,
        exclude_items: List[str] = None
    ) -> Dict:
        """
        Create an optimized meal plan based on targets and constraints.
        
        Args:
            target_calories: Target daily calories
            target_protein: Target daily protein (grams)
            selected_meals: List of meals to include (e.g., ["lunch", "dinner"])
                          If None, includes all meals (breakfast, lunch, dinner)
            min_fruits: Minimum number of fruit servings
            max_fruits: Maximum number of fruit servings
            calorie_tolerance: Acceptable deviation from target calories (±)
            protein_tolerance: Acceptable deviation from target protein (±)
            diversity_weight: Weight for diversity in optimization (0-1)
                            Higher = more diverse meals, lower = more protein focus
            max_servings_per_item: Maximum servings allowed for any single item
            exclude_items: List of food names to exclude from this plan
        
        Returns:
            Dictionary containing:
                - status: Optimization status
                - meals: Breakfast, lunch, dinner plans
                - totals: Total nutritional values
                - items_selected: List of all selected items
        """
        
        # Default to all meals if none specified
        if selected_meals is None:
            selected_meals = ["breakfast", "lunch", "dinner"]
        
        # Validate meal selection
        valid_meals = ["breakfast", "lunch", "dinner"]
        selected_meals = [m.lower() for m in selected_meals if m.lower() in valid_meals]
        
        if not selected_meals:
            return {
                "status": "Error",
                "message": "No valid meals selected. Choose from: breakfast, lunch, dinner",
                "meals": {},
                "totals": {}
            }
        
        # Create exclude set for faster lookup
        exclude_set = set(exclude_items) if exclude_items else set()
        
        # Create the optimization problem
        prob = LpProblem("Meal_Plan_Optimization", LpMaximize)
        
        # Decision variables: how many servings of each food to include
        food_vars = {}
        for i, food in enumerate(self.foods):
            # Skip foods from excluded meals or excluded items
            if food.get("meal_time") not in selected_meals:
                continue
            if food.get("name") in exclude_set:
                continue
                
            # Create INTEGER variable for each food item
            food_vars[i] = LpVariable(
                f"food_{i}", 
                lowBound=0, 
                upBound=max_servings_per_item, 
                cat='Integer'
            )
        
        if not food_vars:
            return {
                "status": "Error",
                "message": f"No foods available for selected meals: {', '.join(selected_meals)}",
                "meals": {},
                "totals": {}
            }
        
        # OBJECTIVE FUNCTION
        protein_objective = lpSum([
            food_vars[i] * self.foods[i].get("protein", 0) 
            for i in food_vars.keys()
        ])
        
        diversity_term = -diversity_weight * lpSum([food_vars[i] for i in food_vars.keys()])
        
        prob += protein_objective + diversity_term
        
        # CONSTRAINT 1: Calorie Range
        total_calories = lpSum([
            food_vars[i] * self.foods[i].get("calories", 0) 
            for i in food_vars.keys()
        ])
        prob += total_calories >= target_calories - calorie_tolerance, "Min_Calories"
        prob += total_calories <= target_calories + calorie_tolerance, "Max_Calories"
        
        # CONSTRAINT 2: Protein Range
        total_protein = lpSum([
            food_vars[i] * self.foods[i].get("protein", 0) 
            for i in food_vars.keys()
        ])
        prob += total_protein >= target_protein - protein_tolerance, "Min_Protein"
        prob += total_protein <= target_protein + protein_tolerance, "Max_Protein"
        
        # CONSTRAINT 3: Each selected meal should have minimum calories
        num_selected_meals = len(selected_meals)
        min_meal_calories = target_calories / max(num_selected_meals, 1)
        
        for meal_time in selected_meals:
            meal_foods = [i for i in food_vars.keys() 
                         if self.foods[i].get("meal_time") == meal_time]
            
            if meal_foods:
                meal_calories = lpSum([
                    food_vars[i] * self.foods[i].get("calories", 0) 
                    for i in meal_foods
                ])
                
                # Adjust constraint based on meal type and selection
                if meal_time == "breakfast" and num_selected_meals > 1:
                    # Breakfast can be smaller if other meals are selected
                    prob += meal_calories >= min_meal_calories * 0.5, f"Min_{meal_time}_calories"
                else:
                    prob += meal_calories >= min_meal_calories * 0.8, f"Min_{meal_time}_calories"
        
        # CONSTRAINT 4: Fruit limits
        fruit_foods = [i for i in food_vars.keys() if self._is_fruit(self.foods[i])]
        
        if fruit_foods:
            total_fruits = lpSum([food_vars[i] for i in fruit_foods])
            prob += total_fruits >= min_fruits, "Min_Fruits"
            prob += total_fruits <= max_fruits, "Max_Fruits"
        
        # Solve the problem
        prob.solve()
        
        # Extract results
        status = LpStatus[prob.status]
        
        if status == "Optimal":
            result = self._format_results(food_vars)
            result["selected_meals"] = selected_meals
            return result
        else:
            return {
                "status": status,
                "message": "Could not find optimal solution. Try relaxing constraints.",
                "meals": {},
                "totals": {},
                "selected_meals": selected_meals
            }
    
    def generate_multiple_plans(
        self,
        num_plans: int,
        target_calories: float,
        target_protein: float,
        selected_meals: List[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Generate multiple alternative meal plans.
        
        This method generates diverse plans by excluding items from previous
        plans, ensuring variety across all generated plans.
        
        Args:
            num_plans: Number of alternative plans to generate
            target_calories: Target daily calories
            target_protein: Target daily protein (grams)
            selected_meals: List of meals to include
            **kwargs: Additional arguments passed to optimize_meal_plan()
        
        Returns:
            List of meal plan dictionaries, each containing the same structure
            as returned by optimize_meal_plan()
        """
        plans = []
        excluded_items = []
        
        for plan_num in range(num_plans):
            print(f"\nGenerating plan {plan_num + 1}/{num_plans}...")
            
            # Generate plan with current exclusions
            result = self.optimize_meal_plan(
                target_calories=target_calories,
                target_protein=target_protein,
                selected_meals=selected_meals,
                exclude_items=excluded_items,
                **kwargs
            )
            
            if result["status"] != "Optimal":
                print(f"  Could not generate plan {plan_num + 1}")
                print(f"  Status: {result['status']}")
                if plan_num == 0:
                    print("  Try relaxing constraints or reducing number of plans")
                break
            
            plans.append(result)
            
            # Add items from this plan to exclusion list for next iteration
            # Only exclude the most prominent items to allow for some overlap
            items_to_exclude = [
                item["name"] for item in result["items_selected"]
                if item["servings"] >= 2  # Only exclude items with 2+ servings
            ]
            excluded_items.extend(items_to_exclude)
            
            print(f"  ✓ Plan {plan_num + 1} generated successfully")
        
        return plans
    
    def _is_fruit(self, food: Dict) -> bool:
        """Determine if a food item is a fruit."""
        name = food.get("name", "").lower()
        category = food.get("category", "").lower()
        fruit_keywords = ["fruit"]
        return any(keyword in category for keyword in fruit_keywords)
    
    def _format_results(self, food_vars: Dict) -> Dict:
        """Format the optimization results into a readable structure."""
        selected_items = []
        meals = {"breakfast": [], "lunch": [], "dinner": []}
        
        for i, var in food_vars.items():
            servings = value(var)
            if servings > 0.01:
                food = self.foods[i].copy()
                food["servings"] = int(round(servings))
                selected_items.append(food)
                
                meal_time = food.get("meal_time", "unknown")
                if meal_time in meals:
                    meals[meal_time].append(food)
        
        totals = {
            "calories": sum(item.get("calories", 0) * item["servings"] for item in selected_items),
            "protein": sum(item.get("protein", 0) * item["servings"] for item in selected_items),
            "carbs": sum(item.get("carbs", 0) * item["servings"] for item in selected_items),
            "fat": sum(item.get("fat", 0) * item["servings"] for item in selected_items),
            "fiber": sum(item.get("fiber", 0) * item["servings"] for item in selected_items),
            "sodium": sum(item.get("sodium", 0) * item["servings"] for item in selected_items),
        }
        
        return {
            "status": "Optimal",
            "meals": meals,
            "totals": totals,
            "items_selected": selected_items,
            "num_items": len(selected_items)
        }
    
    def print_meal_plan(self, result: Dict, plan_number: int = None):
        """Pretty print the meal plan results."""
        header = "OPTIMIZED MEAL PLAN"
        if plan_number is not None:
            header = f"MEAL PLAN #{plan_number}"
        
        print("\n" + "="*60)
        print(header)
        print("="*60)
        
        if result["status"] != "Optimal":
            print(f"\nStatus: {result['status']}")
            print(result.get("message", ""))
            return
        
        # Show which meals are included
        selected = result.get("selected_meals", ["breakfast", "lunch", "dinner"])
        print(f"\nMeals: {', '.join(m.title() for m in selected)}")
        
        # Print each meal
        for meal_time in ["breakfast", "lunch", "dinner"]:
            if meal_time not in selected:
                continue
                
            print(f"\n{meal_time.upper()}:")
            print("-" * 60)
            
            meal_items = result["meals"].get(meal_time, [])
            if not meal_items:
                print("  No items selected")
                continue
            
            meal_cals = sum(item.get("calories", 0) * item["servings"] for item in meal_items)
            meal_protein = sum(item.get("protein", 0) * item["servings"] for item in meal_items)
            
            for item in meal_items:
                servings = item["servings"]
                serving_text = f" x{servings}" if servings > 1 else ""
                print(f"  • {item['name']}{serving_text}")
                print(f"    {item.get('calories', 0) * servings:.0f} cal | "
                      f"{item.get('protein', 0) * servings:.1f}g protein | "
                      f"{item.get('carbs', 0) * servings:.1f}g carbs | "
                      f"{item.get('fat', 0) * servings:.1f}g fat")
            
            print(f"  Meal Total: {meal_cals:.0f} cal | {meal_protein:.1f}g protein")
        
        # Print daily totals
        print("\n" + "="*60)
        print("DAILY TOTALS:")
        print("-" * 60)
        totals = result["totals"]
        print(f"  Calories: {totals['calories']:.0f}")
        print(f"  Protein:  {totals['protein']:.1f}g")
        print(f"  Carbs:    {totals['carbs']:.1f}g")
        print(f"  Fat:      {totals['fat']:.1f}g")
        print(f"  Fiber:    {totals['fiber']:.1f}g")
        print(f"  Sodium:   {totals['sodium']:.1f}mg")
        print(f"\n  Total Items: {result['num_items']}")
        print("="*60 + "\n")


def main():
    """
    Example usage of the enhanced MealOptimizer.
    """
    optimizer = MealOptimizer(menu_data_path="data/menu_data.json")
    
    TARGET_CALORIES = 1500
    TARGET_PROTEIN = 100
    
    print("="*60)
    print("EXAMPLE 1: Single meal (Lunch only)")
    print("="*60)
    
    result = optimizer.optimize_meal_plan(
        target_calories=TARGET_CALORIES,
        target_protein=TARGET_PROTEIN,
        selected_meals=["lunch"],  # Only lunch
        min_fruits=1,
        max_fruits=2,
        calorie_tolerance=150,
        protein_tolerance=20,
        diversity_weight=0.1,
        max_servings_per_item=2
    )
    optimizer.print_meal_plan(result)
    
    print("\n\n")
    print("="*60)
    print("EXAMPLE 2: Two meals (Lunch + Dinner)")
    print("="*60)
    
    result = optimizer.optimize_meal_plan(
        target_calories=TARGET_CALORIES,
        target_protein=TARGET_PROTEIN,
        selected_meals=["lunch", "dinner"],  # Lunch and dinner only
        min_fruits=2,
        max_fruits=4,
        calorie_tolerance=150,
        protein_tolerance=20,
        diversity_weight=0.1,
        max_servings_per_item=2
    )
    optimizer.print_meal_plan(result)
    
    print("\n\n")
    print("="*60)
    print("EXAMPLE 3: Generate 3 alternative plans for Lunch + Dinner")
    print("="*60)
    
    plans = optimizer.generate_multiple_plans(
        num_plans=3,
        target_calories=TARGET_CALORIES,
        target_protein=TARGET_PROTEIN,
        selected_meals=["lunch", "dinner"],
        min_fruits=2,
        max_fruits=4,
        calorie_tolerance=150,
        protein_tolerance=20,
        diversity_weight=0.15,
        max_servings_per_item=2
    )
    
    # Print all generated plans
    for i, plan in enumerate(plans, 1):
        optimizer.print_meal_plan(plan, plan_number=i)


if __name__ == "__main__":
    main()