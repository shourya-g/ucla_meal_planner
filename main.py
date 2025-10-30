"""
Bruin Plate Meal Planner - Flask Backend
=========================================
REST API for meal optimization
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
from flask import send_file

# Add this route after the other routes


# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimizer.meal_optimizer import MealOptimizer

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Initialize optimizer
MENU_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'menu_data.json')

try:
    optimizer = MealOptimizer(menu_data_path=MENU_DATA_PATH)
    print(f"✓ Loaded {len(optimizer.foods)} menu items from {MENU_DATA_PATH}")
except Exception as e:
    print(f"✗ Error loading menu data: {e}")
    optimizer = None

@app.route('/')
def home():
    """API status endpoint"""
    return jsonify({
        "name": "Bruin Plate Meal Planner API",
        "status": "running",
        "version": "1.0",
        "endpoints": {
            "GET /": "API status",
            "GET /api/menu": "Get all menu items",
            "POST /api/optimize": "Generate single meal plan",
            "POST /api/optimize/multiple": "Generate multiple meal plans"
        }
    })

@app.route('/api/menu', methods=['GET'])
def get_menu():
    """Get all available menu items"""
    if optimizer is None:
        return jsonify({"error": "Optimizer not initialized"}), 500
    
    # Group foods by meal time
    foods_by_meal = {
        "breakfast": [],
        "lunch": [],
        "dinner": []
    }
    
    for food in optimizer.foods:
        meal_time = food.get("meal_time", "unknown")
        if meal_time in foods_by_meal:
            foods_by_meal[meal_time].append(food)
    
    return jsonify({
        "total_items": len(optimizer.foods),
        "by_meal": foods_by_meal,
        "all_items": optimizer.foods
    })

@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    Generate a single optimized meal plan
    
    Expected JSON body:
    {
        "target_calories": 2000,
        "target_protein": 150,
        "selected_meals": ["lunch", "dinner"],
        "min_fruits": 1,
        "max_fruits": 3,
        "calorie_tolerance": 300,
        "protein_tolerance": 20,
        "diversity_weight": 0.1,
        "max_servings_per_item": 3
    }
    """
    if optimizer is None:
        return jsonify({"error": "Optimizer not initialized"}), 500
    
    try:
        data = request.json
        
        # Validate required fields
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract parameters with defaults
        params = {
            'target_calories': float(data.get('target_calories', 2000)),
            'target_protein': float(data.get('target_protein', 150)),
            'selected_meals': data.get('selected_meals', ['breakfast', 'lunch', 'dinner']),
            'min_fruits': int(data.get('min_fruits', 1)),
            'max_fruits': int(data.get('max_fruits', 3)),
            'calorie_tolerance': float(data.get('calorie_tolerance', 300)),
            'protein_tolerance': float(data.get('protein_tolerance', 20)),
            'diversity_weight': float(data.get('diversity_weight', 0.1)),
            'max_servings_per_item': int(data.get('max_servings_per_item', 3))
        }
        
        result = optimizer.optimize_meal_plan(**params)
        
        return jsonify(result)
    
    except ValueError as e:
        return jsonify({"error": f"Invalid parameter value: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/optimize/multiple', methods=['POST'])
def optimize_multiple():
    """
    Generate multiple meal plan alternatives
    
    Expected JSON body:
    {
        "num_plans": 3,
        "target_calories": 2000,
        "target_protein": 150,
        "selected_meals": ["lunch", "dinner"],
        ... (same as /api/optimize)
    }
    """
    if optimizer is None:
        return jsonify({"error": "Optimizer not initialized"}), 500
    
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        num_plans = int(data.get('num_plans', 3))
        
        if num_plans < 1 or num_plans > 10:
            return jsonify({"error": "num_plans must be between 1 and 10"}), 400
        
        # Extract parameters
        params = {
            'target_calories': float(data.get('target_calories', 2000)),
            'target_protein': float(data.get('target_protein', 150)),
            'selected_meals': data.get('selected_meals', ['breakfast', 'lunch', 'dinner']),
            'min_fruits': int(data.get('min_fruits', 1)),
            'max_fruits': int(data.get('max_fruits', 3)),
            'calorie_tolerance': float(data.get('calorie_tolerance', 300)),
            'protein_tolerance': float(data.get('protein_tolerance', 20)),
            'diversity_weight': float(data.get('diversity_weight', 0.1)),
            'max_servings_per_item': int(data.get('max_servings_per_item', 3))
        }
        
        plans = optimizer.generate_multiple_plans(
            num_plans=num_plans,
            **params
        )
        
        return jsonify({
            "status": "success",
            "count": len(plans),
            "plans": plans
        })
    
    except ValueError as e:
        return jsonify({"error": f"Invalid parameter value: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "optimizer_loaded": optimizer is not None,
        "menu_items": len(optimizer.foods) if optimizer else 0
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.route('/app')
def serve_app():
    return send_file('index.html')
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🍽️  BRUIN PLATE MEAL PLANNER API")
    print("="*60)
    print(f"Server starting on http://localhost:5000")
    print(f"Menu data: {MENU_DATA_PATH}")
    print(f"Items loaded: {len(optimizer.foods) if optimizer else 0}")
    print("\nAvailable endpoints:")
    print("  GET  /                      - API info")
    print("  GET  /api/health            - Health check")
    print("  GET  /api/menu              - Get menu items")
    print("  POST /api/optimize          - Generate meal plan")
    print("  POST /api/optimize/multiple - Generate multiple plans")
    print("\nPress CTRL+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)