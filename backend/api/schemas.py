"""Pydantic request/response models for the FastAPI backend."""

from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's question about the indexed documents.")
    document_id: Optional[str] = Field(
        None,
        description=(
            "Scope retrieval to one uploaded document (its filename). When "
            "set, only that document's chunks can be retrieved/cited — used "
            "for 'chat with this document' style questions. Omit to search "
            "across every indexed document."
        ),
    )
    session_id: Optional[str] = Field(
        None, description="Existing chat session to append this Q&A to. Omit for a stateless one-off query."
    )


class SourceDocument(BaseModel):
    source: str
    document_id: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    content: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[str]
    retrieved_documents: List[SourceDocument]
    latency_ms: int
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    kb_ready: bool
    llm_ready: bool
    llm_error: Optional[str] = None


class UploadedFileResult(BaseModel):
    filename: str
    status: str  # "indexed" | "failed"
    detail: Optional[str] = None


class UploadResponse(BaseModel):
    files: List[UploadedFileResult]
    kb_ready: bool


# --- Document library ---------------------------------------------------


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    file_type: str
    size_bytes: int
    uploaded_at: Optional[float] = None
    indexed: bool
    num_chunks: int
    num_pages: Optional[int] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentSummary]


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: bool
    kb_ready: bool


# --- Summarization --------------------------------------------------------


class SummarizeRequest(BaseModel):
    detail: str = Field("short", description="'short' or 'detailed'.")


class SummarizeResponse(BaseModel):
    document_id: str
    summary: str
    detail: str


# --- Flashcards -------------------------------------------------------------


class FlashcardSource(BaseModel):
    filename: str
    page: Optional[int] = None


class Flashcard(BaseModel):
    question: str
    answer: str
    source: Optional[FlashcardSource] = None


class FlashcardsRequest(BaseModel):
    num_cards: int = Field(8, ge=1, le=30)


class FlashcardsResponse(BaseModel):
    document_id: str
    flashcards: List[Flashcard]


# --- Chat sessions ----------------------------------------------------------


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: float
    sources: Optional[List[SourceDocument]] = None
    confidence: Optional[float] = None


class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int


class SessionDetail(BaseModel):
    session_id: str
    title: str
    created_at: float
    updated_at: float
    messages: List[ChatMessage]


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
