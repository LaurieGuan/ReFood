export function preferencesFromForm(form, preferences, nutrients) {
  const nutrition_limits = Object.fromEntries(
    nutrients.map(({ id }) => [
      id,
      {
        min:
          form.get(`${id}_min`) === "" ? null : Number(form.get(`${id}_min`)),
        max:
          form.get(`${id}_max`) === "" ? null : Number(form.get(`${id}_max`)),
      },
    ]),
  );

  return {
    ...preferences,
    dietary_restrictions: form.getAll("dietary_restrictions"),
    allergens: form.getAll("allergens"),
    intolerances: form.getAll("intolerances"),
    excluded_ingredient_ids: form.getAll("excluded_ingredient_ids"),
    nutrition_limits,
    max_budget_cad: form.get("max_budget_cad") || null,
    max_minutes: form.get("max_minutes")
      ? Number(form.get("max_minutes"))
      : null,
    servings: Number(form.get("servings")),
  };
}
