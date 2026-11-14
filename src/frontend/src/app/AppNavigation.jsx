import { destinations } from "./navigation.js";

function NavigationLinks({ screen, onNavigate, savedCount, mobile = false }) {
  return destinations.map((item) => (
    <button
      key={item.id}
      className={
        mobile
          ? screen === item.id
            ? "active"
            : ""
          : `nav-link ${screen === item.id ? "selected" : ""}`
      }
      onClick={() => onNavigate(item.id)}
    >
      <span className={mobile ? undefined : "nav-icon"}>{item.icon}</span>
      {item.label}
      {!mobile && item.id === "saved" && savedCount > 0 && (
        <small>{savedCount}</small>
      )}
    </button>
  ));
}

export function AppNavigation({ screen, onNavigate, savedCount, apiUrl }) {
  return (
    <>
      <aside className="sidebar">
        <a
          className="brand"
          href="#scan"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("scan");
          }}
        >
          <span className="brand-mark">r.</span>
          <span>
            refood<span className="brand-dot">.</span>
          </span>
        </a>
        <p className="side-caption">VOTRE CUISINE</p>
        <nav>
          <NavigationLinks {...{ screen, onNavigate, savedCount }} />
        </nav>
        <div className="side-note">
          <span>i</span>
          <p>Confirmez les ingrédients proposés pour trouver des recettes.</p>
          <code>{apiUrl}</code>
        </div>
      </aside>
      <nav className="mobile-nav">
        <NavigationLinks {...{ screen, onNavigate, savedCount }} mobile />
      </nav>
    </>
  );
}
