export default function EmptyState({ icon: Icon, title, hint, action }) {
  return (
    <div className="empty-state">
      {Icon && <Icon size={34} strokeWidth={1.5} />}
      <div className="empty-state-title">{title}</div>
      {hint && <p className="empty-state-hint">{hint}</p>}
      {action}
    </div>
  );
}
