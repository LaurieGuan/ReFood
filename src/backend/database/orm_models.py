"""Relational storage only; payloads retain optional shared-schema metadata."""
from sqlalchemy import Column, Float, ForeignKey, ForeignKeyConstraint, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class IngredientRow(Base):
    __tablename__ = "ingredients"
    ingredient_id = Column(String(191), primary_key=True)
    name = Column(String(512), nullable=False)


class RecipeRow(Base):
    __tablename__ = "recipes"
    recipe_id = Column(String(191), primary_key=True)
    metadata_json = Column(JSON, nullable=False)


class RecipeIngredientRow(Base):
    __tablename__ = "recipe_ingredients"
    recipe_id = Column(String(191), ForeignKey("recipes.recipe_id"), primary_key=True)
    position = Column(Integer, primary_key=True)
    ingredient_id = Column(String(191), ForeignKey("ingredients.ingredient_id"), nullable=False)
    name = Column(String(512), nullable=False)
    amount = Column(Float, nullable=True)
    unit = Column(String(20), nullable=False)


class PantryInventoryRow(Base):
    __tablename__ = "pantry_inventory"
    user_id = Column(String(191), primary_key=True)
    position = Column(Integer, primary_key=True)
    ingredient_id = Column(String(191), ForeignKey("ingredients.ingredient_id"), nullable=False)
    name = Column(String(512), nullable=False)
    amount = Column(Float, nullable=True)
    unit = Column(String(20), nullable=False)
    remaining_fraction = Column(Float, nullable=True)


class GroceryProductRow(Base):
    __tablename__ = "grocery_products"
    provider = Column(String(100), primary_key=True)
    provider_product_id = Column(String(191), primary_key=True)
    payload = Column(JSON, nullable=False)


class StorePriceRow(Base):
    __tablename__ = "store_prices"
    __table_args__ = (ForeignKeyConstraint(
        ["provider", "provider_product_id"],
        ["grocery_products.provider", "grocery_products.provider_product_id"]),)
    provider = Column(String(100), primary_key=True)
    provider_product_id = Column(String(191), primary_key=True)
    store = Column(String(191), primary_key=True)
    payload = Column(JSON, nullable=False)


class MarketplaceLockRow(Base):
    __tablename__ = "marketplace_lock"
    lock_id = Column(Integer, primary_key=True)
    revision = Column(Integer, nullable=False, default=0)


class ExchangeOfferRow(Base):
    __tablename__ = "marketplace_offers"
    offer_id = Column(String(191), primary_key=True)
    owner_id = Column(String(191), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    payload = Column(JSON, nullable=False)


class ExchangeProposalRow(Base):
    __tablename__ = "marketplace_proposals"
    proposal_id = Column(String(191), primary_key=True)
    target_offer_id = Column(String(191), ForeignKey("marketplace_offers.offer_id"), nullable=False)
    proposer_offer_id = Column(String(191), ForeignKey("marketplace_offers.offer_id"), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    payload = Column(JSON, nullable=False)


class ExchangeReservationRow(Base):
    __tablename__ = "marketplace_reservations"
    proposal_id = Column(String(191), ForeignKey("marketplace_proposals.proposal_id"), primary_key=True)
    user_id = Column(String(191), primary_key=True)
    ingredient_id = Column(String(191), ForeignKey("ingredients.ingredient_id"), nullable=False)
    amount = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)


class DonationOfferRow(Base):
    __tablename__ = "donation_offers"
    offer_id = Column(String(191), primary_key=True)
    business_id = Column(String(191), nullable=False, index=True)
    cancelled = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=False)


class DonationReservationRow(Base):
    __tablename__ = "donation_reservations"
    reservation_id = Column(String(191), primary_key=True)
    offer_id = Column(String(191), ForeignKey("donation_offers.offer_id"), nullable=False, index=True)
    student_id = Column(String(191), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    payload = Column(JSON, nullable=False)
