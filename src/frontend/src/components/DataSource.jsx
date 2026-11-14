export function sourceLabel(source, persistence) {
  const label = { live: 'Live · Flask API', demo: 'Demo · Sample data', local: 'Local · Browser storage', unavailable: 'Unavailable', unknown: 'Flask API · Source non précisée' }[source] ?? 'Source non précisée';
  return label + (persistence === 'browser' && source !== 'local' ? ' · Local · Browser storage' : '');
}
export function DataSource({ source, persistence }) {
  return <small className="data-source" role="status">{sourceLabel(source, persistence)}</small>;
}
