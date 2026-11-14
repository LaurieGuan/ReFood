import unittest

from schemas.ingredients import IngredientWithQuantity
from schemas.recipes import Recipe, RecipeMatch, RecipeSearchRequest
from services.recipe_matcher import find_recipes, match_recipes


def ingredient(ingredient_id="ing_egg", amount=None, unit="unknown", name="egg"):
    return IngredientWithQuantity.model_validate({
        "ingredient_id": ingredient_id, "name": name,
        "quantity": {"amount": amount, "unit": unit},
    })


class MatcherTests(unittest.TestCase):
    def match(self, stock, requirements):
        recipe = Recipe(recipe_id="test", title="Test", ingredients=requirements)
        return match_recipes(RecipeSearchRequest(ingredients=stock), [recipe])[0]

    def test_fixture_ranking_and_schema(self):
        results = find_recipes(RecipeSearchRequest(ingredients=[
            ingredient(amount=2, unit="piece"), ingredient("ing_milk", 50, "ml"),
        ]))
        self.assertEqual(results[0].recipe.recipe_id, "demo_omelette")
        self.assertEqual(results[0].match_score, 1)
        self.assertFalse(results[0].quantity_uncertain)
        for result in results:
            RecipeMatch.model_validate(result.model_dump(mode="json"))

    def test_missing_and_partial_coverage(self):
        result = self.match([ingredient()], [ingredient(), ingredient("ing_milk")])
        self.assertEqual(result.match_score, .5)
        self.assertEqual([item.ingredient_id for item in result.missing_ingredients], ["ing_milk"])
        self.assertTrue(result.quantity_uncertain)

    def test_exact_ids_ignore_names(self):
        result = self.match([ingredient(name="oeuf")], [ingredient()])
        self.assertEqual(result.match_score, 1)
        result = self.match([ingredient("other", name="egg")], [ingredient()])
        self.assertEqual(result.match_score, 0)

    def test_quantity_unknown_incompatible_and_shortage(self):
        required = [ingredient(amount=2, unit="piece")]
        for stock in ([ingredient()], [ingredient(amount=2, unit="g")]):
            result = self.match(stock, required)
            self.assertTrue(result.quantity_uncertain)
            self.assertEqual(result.missing_ingredients, [])
        result = self.match([ingredient(amount=1, unit="piece")], required)
        self.assertFalse(result.quantity_uncertain)
        self.assertEqual(result.missing_ingredients[0].quantity.amount, 2)

    def test_conversion_and_duplicate_stock(self):
        result = self.match([ingredient(amount=.1, unit="kg"), ingredient(amount=100, unit="g")],
                            [ingredient(amount=200, unit="g")])
        self.assertEqual(result.missing_ingredients, [])
        self.assertFalse(result.quantity_uncertain)

    def test_duplicate_requirements_use_total(self):
        result = self.match([ingredient(amount=2, unit="piece")],
                            [ingredient(amount=2, unit="piece"), ingredient(amount=1, unit="piece")])
        self.assertEqual(result.missing_ingredients[0].quantity.amount, 3)

    def test_zero_stock_is_missing(self):
        self.assertEqual(self.match([ingredient(amount=0)], [ingredient()]).match_score, 0)

    def test_missing_duplicate_requirements_preserve_total(self):
        result = self.match([], [ingredient(amount=2, unit="piece"),
                                 ingredient(amount=1, unit="piece")])
        self.assertEqual(result.missing_ingredients[0].quantity.amount, 3)

    def test_unknown_extra_stock_does_not_hide_known_sufficiency(self):
        result = self.match([ingredient(amount=2, unit="piece"), ingredient()],
                            [ingredient(amount=2, unit="piece")])
        self.assertFalse(result.quantity_uncertain)
        self.assertEqual(result.missing_ingredients, [])

    def test_filter_limit_and_empty_inventory(self):
        self.assertEqual(find_recipes(RecipeSearchRequest(ingredients=[], max_missing=0)), [])
        self.assertEqual(len(find_recipes(RecipeSearchRequest(ingredients=[], limit=1))), 1)

    def test_empty_recipe_skipped_and_stable_tie(self):
        recipes = [Recipe(recipe_id=key, title=key, ingredients=[ingredient()]) for key in ("b", "a")]
        recipes.append(Recipe(recipe_id="empty", title="Empty", ingredients=[]))
        results = match_recipes(RecipeSearchRequest(ingredients=[]), recipes)
        self.assertEqual([result.recipe.recipe_id for result in results], ["a", "b"])

    def test_results_do_not_mutate_fixture(self):
        request = RecipeSearchRequest(ingredients=[])
        find_recipes(request)[0].recipe.title = "changed"
        self.assertNotEqual(find_recipes(request)[0].recipe.title, "changed")
