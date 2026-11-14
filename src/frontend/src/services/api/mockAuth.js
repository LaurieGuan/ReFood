// Local demonstration account service. Replace with server-side authentication for production.
const ACCOUNTS = 'refood.demo.accounts';
const SESSION = 'refood.demo.session';
const readAccounts = () => JSON.parse(localStorage.getItem(ACCOUNTS) || '[]');
const digest = async (password) => {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(password));
  return Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, '0')).join('');
};
const publicUser = ({ name, email }) => ({ name, email });
export const mockAuth = {
  async currentUser() { return JSON.parse(localStorage.getItem(SESSION) || 'null'); },
  async register({ name, email, password }) {
    const normalized = email.trim().toLowerCase();
    if (!name.trim() || !normalized || password.length < 8) throw new Error('Indiquez votre nom, votre courriel et un mot de passe d’au moins huit caractères.');
    const accounts = readAccounts();
    if (accounts.some((account) => account.email === normalized)) throw new Error('Un compte existe déjà pour ce courriel.');
    const user = { name: name.trim(), email: normalized, passwordHash: await digest(password) };
    localStorage.setItem(ACCOUNTS, JSON.stringify([...accounts, user]));
    localStorage.setItem(SESSION, JSON.stringify(publicUser(user)));
    return publicUser(user);
  },
  async login({ email, password }) {
    const account = readAccounts().find((item) => item.email === email.trim().toLowerCase());
    if (!account || account.passwordHash !== await digest(password)) throw new Error('Courriel ou mot de passe incorrect.');
    localStorage.setItem(SESSION, JSON.stringify(publicUser(account)));
    return publicUser(account);
  },
  async logout() { localStorage.removeItem(SESSION); },
};
