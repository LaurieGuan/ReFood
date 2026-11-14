---
tags: [refood, backend, stretch]
status: unimplemented
owner: Developer 1 API; Developer 2 database
---
# Marketplace

`src/backend/schemas/marketplace.py` is a placeholder / stretch goal.

**Developer 1:** offer browse/post/respond endpoints and state transitions. **Developer 2:** persistent offer, user/session, exchange request tables. **Developer 3:** optional ingredient/category normalization for offers.

Potential `ExchangeOffer`: `offer_id`, `owner_id`, `item_name`, `quantity`, `description`, `offered_in_exchange`, `meeting_area`, `status` (open/reserved/closed), `created_at`. Do not expose private addresses; meeting areas can be coarse. Use test users instead of implementing a complete authentication system for demo.

Distinguish exchanging unused ingredients from exchanging prepared meals. Both were discussed, but the teammate summary emphasizes ingredient barter. Pick one primary demo flow to avoid building two marketplaces.

See [[Backend Architecture]].
