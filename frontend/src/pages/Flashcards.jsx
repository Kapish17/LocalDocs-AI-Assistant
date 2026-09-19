import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Download, Layers, RefreshCw } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import ErrorBanner from "../components/common/ErrorBanner";
import { LoadingRow } from "../components/common/LoadingState";
import { useDocuments } from "../hooks/useDocuments";
import { getFlashcards, flashcardsExportUrl } from "../services/api";

export default function Flashcards() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const { documents, loading: docsLoading } = useDocuments();

  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function generate() {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    setIndex(0);
    setFlipped(false);
    try {
      const res = await getFlashcards(documentId, 8);
      setCards(res.flashcards);
    } catch (err) {
      setError(err.message || "Failed to generate flashcards.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setCards([]);
    if (documentId) generate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  function next() {
    setFlipped(false);
    setIndex((i) => Math.min(i + 1, cards.length - 1));
  }

  function prev() {
    setFlipped(false);
    setIndex((i) => Math.max(i - 1, 0));
  }

  if (!documentId) {
    return (
      <div>
        <div className="page-heading">
          <div>
            <h1>Flashcards</h1>
            <p className="subtitle">Pick a document to generate study flashcards from.</p>
          </div>
        </div>
        {docsLoading ? (
          <LoadingRow />
        ) : documents.length === 0 ? (
          <EmptyState icon={Layers} title="No documents yet" hint="Upload a document from the Documents page first." />
        ) : (
          <div className="doc-table">
            {documents.map((d) => (
              <button
                key={d.document_id}
                className="doc-row"
                style={{ cursor: "pointer", textAlign: "left", width: "100%" }}
                onClick={() => navigate(`/flashcards/${encodeURIComponent(d.document_id)}`)}
              >
                <div className="doc-row-icon">
                  <Layers size={18} />
                </div>
                <div className="doc-row-main">
                  <div className="doc-row-name">{d.filename}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  const card = cards[index];

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Flashcards — {documentId}</h1>
          <p className="subtitle">Grounded in this document — click a card to flip it.</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="icon-btn" title="Regenerate" onClick={generate}>
            <RefreshCw size={15} />
          </button>
          <a
            className="icon-btn"
            title="Export as Markdown"
            href={flashcardsExportUrl(documentId, 8)}
            download={`${documentId}-flashcards.md`}
          >
            <Download size={15} />
          </a>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={generate} />

      {loading && <LoadingRow label="Generating flashcards from the document…" />}

      {!loading && cards.length === 0 && !error && (
        <EmptyState icon={Layers} title="No flashcards yet" />
      )}

      {!loading && cards.length > 0 && card && (
        <>
          <div className="flashcard-toolbar">
            <span className="flashcard-progress">
              Card {index + 1} of {cards.length}
            </span>
          </div>

          <div className="flashcard-stage">
            <button className="flashcard-nav-btn" onClick={prev} disabled={index === 0} aria-label="Previous card">
              <ChevronLeft size={18} />
            </button>

            <div
              className={`flashcard${flipped ? " flipped" : ""}`}
              onClick={() => setFlipped((f) => !f)}
              role="button"
              tabIndex={0}
              aria-label="Flip card"
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") setFlipped((f) => !f);
              }}
            >
              <div className="flashcard-inner">
                <div className="flashcard-face flashcard-face--front">
                  <span className="flashcard-face-label">Question</span>
                  {card.question}
                </div>
                <div className="flashcard-face flashcard-face--back">
                  <span className="flashcard-face-label">Answer</span>
                  {card.answer}
                </div>
              </div>
            </div>

            <button
              className="flashcard-nav-btn"
              onClick={next}
              disabled={index === cards.length - 1}
              aria-label="Next card"
            >
              <ChevronRight size={18} />
            </button>
          </div>

          {card.source && (
            <div className="flashcard-source">
              Source: {card.source.filename}
              {card.source.page ? ` · page ${card.source.page}` : ""}
            </div>
          )}
        </>
      )}
    </div>
  );
}
