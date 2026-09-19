import { FileText } from "lucide-react";

/**
 * Expandable list of retrieved source chunks. These are exactly the chunks
 * core.rag_engine.answer_question() sent to Gemini for this answer (see
 * retrieved_documents in the /query response) — never a separately
 * computed or decorative list, so what's shown here always matches what
 * the model actually saw.
 */
export default function SourceList({ retrievedDocuments }) {
  if (!retrievedDocuments || retrievedDocuments.length === 0) return null;

  return (
    <details className="source-list">
      <summary>
        <FileText size={12} style={{ verticalAlign: "-2px", marginRight: 4 }} />
        Sources ({retrievedDocuments.length})
      </summary>
      <ul>
        {retrievedDocuments.map((doc, i) => (
          <li key={`${doc.source}-${i}`}>
            <div className="source-item-header">
              <span className="source-name">
                {doc.source}
                {doc.page ? ` · page ${doc.page}` : ""}
              </span>
              <span className="source-score">{Math.round(doc.score * 100)}% match</span>
            </div>
            <p className="source-snippet">
              {doc.content.slice(0, 220)}
              {doc.content.length > 220 ? "…" : ""}
            </p>
          </li>
        ))}
      </ul>
    </details>
  );
}
