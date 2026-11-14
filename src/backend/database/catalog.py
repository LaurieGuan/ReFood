"""Consume normalized Recipe objects; fetching source data belongs to Dev 3."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from schemas.recipes import Recipe
from schemas.pantry import PantryResponse, PantryUpdateRequest
from schemas.prices import GroceryProduct
from .engine import get_engine
from .orm_models import (IngredientRow, RecipeRow, RecipeIngredientRow,
                         PantryInventoryRow, GroceryProductRow, StorePriceRow)


class SQLRepository:
    def __init__(self, engine=None):
        self.engine = engine if engine is not None else get_engine()

    @staticmethod
    def _upsert(session, row):
        if session.bind.dialect.name in ("mysql", "mariadb"):
            from sqlalchemy.dialects.mysql import insert
            values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
            statement = insert(row.__table__).values(**values)
            session.execute(statement.on_duplicate_key_update(**{
                key: statement.inserted[key] for key in values
                if not row.__table__.columns[key].primary_key}))
        else:
            session.merge(row)

    @staticmethod
    def _ingredient(session, item):
        SQLRepository._upsert(session, IngredientRow(ingredient_id=item.ingredient_id, name=item.name))
        session.flush()

    def save_recipes(self, recipes: list[Recipe]) -> int:
        recipes = [Recipe.model_validate(r.model_dump(mode="json")) for r in recipes]
        with Session(self.engine) as session, session.begin():
            for recipe in recipes:
                self._upsert(session, RecipeRow(recipe_id=recipe.recipe_id,
                    metadata_json=recipe.model_dump(mode="json", exclude={"ingredients"})))
                session.flush()
                session.execute(delete(RecipeIngredientRow).where(
                    RecipeIngredientRow.recipe_id == recipe.recipe_id))
                for position, item in enumerate(recipe.ingredients):
                    self._ingredient(session, item)
                    session.add(RecipeIngredientRow(recipe_id=recipe.recipe_id,
                        position=position, ingredient_id=item.ingredient_id, name=item.name,
                        amount=item.quantity.amount, unit=item.quantity.unit.value))
        return len({r.recipe_id for r in recipes})

    def get_recipes(self) -> list[Recipe]:
        with Session(self.engine) as session:
            ingredients = {}
            for item in session.scalars(select(RecipeIngredientRow).order_by(
                    RecipeIngredientRow.recipe_id, RecipeIngredientRow.position)):
                ingredients.setdefault(item.recipe_id, []).append(self._item(item))
            return [Recipe.model_validate({**row.metadata_json,
                "ingredients": ingredients.get(row.recipe_id, [])})
                for row in session.scalars(select(RecipeRow).order_by(RecipeRow.recipe_id))]

    @staticmethod
    def _item(row):
        return {"ingredient_id": row.ingredient_id, "name": row.name,
                "quantity": {"amount": row.amount, "unit": row.unit}}

    def get_pantry(self, user_id: str) -> PantryResponse:
        from .repositories import _validate_user
        _validate_user(user_id)
        with Session(self.engine) as session:
            return PantryResponse.model_validate({"items": [
                {**self._item(row), "remaining_fraction": row.remaining_fraction}
                for row in session.scalars(select(PantryInventoryRow).where(
                    PantryInventoryRow.user_id == user_id).order_by(PantryInventoryRow.position))]})

    def replace_pantry(self, user_id: str, request: PantryUpdateRequest) -> PantryResponse:
        from .repositories import _validate_user
        _validate_user(user_id)
        request = PantryUpdateRequest.model_validate(request.model_dump(mode="json"))
        with Session(self.engine) as session, session.begin():
            session.execute(delete(PantryInventoryRow).where(PantryInventoryRow.user_id == user_id))
            for position, item in enumerate(request.items):
                self._ingredient(session, item)
                session.add(PantryInventoryRow(user_id=user_id, position=position,
                    ingredient_id=item.ingredient_id, name=item.name, amount=item.quantity.amount,
                    unit=item.quantity.unit.value, remaining_fraction=item.remaining_fraction))
        return PantryResponse.model_validate(request.model_dump(mode="json"))

    def save_grocery_products(self, products: list[GroceryProduct]) -> int:
        with Session(self.engine) as session, session.begin():
            for product in products:
                data = product.model_dump(mode="json")
                self._upsert(session, GroceryProductRow(provider=product.provider,
                    provider_product_id=product.provider_product_id,
                    payload={k: v for k, v in data.items() if k != "store_prices"}))
                session.flush()
                for offer in product.store_prices:
                    self._upsert(session, StorePriceRow(provider=product.provider,
                        provider_product_id=product.provider_product_id, store=offer.store,
                        payload=offer.model_dump(mode="json")))
        return len({(p.provider, p.provider_product_id) for p in products})

    def get_grocery_products(self) -> list[GroceryProduct]:
        with Session(self.engine) as session:
            offers = {}
            for row in session.scalars(select(StorePriceRow).order_by(StorePriceRow.store)):
                offers.setdefault((row.provider, row.provider_product_id), []).append(row.payload)
            return [GroceryProduct.model_validate({**row.payload,
                "store_prices": offers.get((row.provider, row.provider_product_id), [])})
                for row in session.scalars(select(GroceryProductRow))]


def save_recipes(recipes: list[Recipe]) -> int:
    return SQLRepository().save_recipes(recipes)


def get_recipes() -> list[Recipe]:
    return SQLRepository().get_recipes()
