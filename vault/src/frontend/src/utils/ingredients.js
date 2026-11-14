const names = { egg: 'Œuf', tomato: 'Tomate', milk: 'Lait', avocado: 'Avocat', pasta: 'Pâtes', onion: 'Oignon', cheese: 'Fromage' };
const food = { egg: '🥚', tomato: '🍅', milk: '🥛', avocado: '🥑', pasta: '🍝', onion: '🧅', cheese: '🧀' };
export const label = (name) => names[name] ?? name;
export const icon = (name) => food[name] ?? '🥬';
