/**
 * Expandable list of retrieved source chunks (source name + similarity
 * score).
 */
export default function SourceList({ retrievedDocuments }) {
  if (!retrievedDocuments || retrievedDocuments.length === 0) return null;

  return (
    <details className="source-list">
      <summary>📄 Sources ({retrievedDocuments.length})</summary>
      <ul>
        {retrievedDocuments.map((doc, i) => (
          <li key={`${doc.source}-${i}`}>
            <div className="source-item-header">
              <span className="source-name">{doc.source}</span>
              <span className="source-score">{Math.round(doc.score * 100)}% match</span>
            </div>
            <p className="source-snippet">{doc.content.slice(0, 220)}{doc.content.length > 220 ? "…" : ""}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}
