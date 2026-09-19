import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SourceList from "../sources/SourceList";
import ConfidenceBadge from "../common/ConfidenceBadge";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`chat-message chat-message--${isUser ? "user" : "assistant"}${message.error ? " chat-message--error" : ""}`}>
      <div className="chat-message-avatar">{isUser ? <User size={15} /> : <Bot size={15} />}</div>
      <div className="chat-message-body">
        {isUser ? (
          <p className="chat-message-text">{message.content}</p>
        ) : (
          <div className="chat-message-text">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}
        {!isUser && !message.error && <ConfidenceBadge confidence={message.confidence} />}
        {!isUser && !message.error && <SourceList retrievedDocuments={message.retrieved_documents} />}
      </div>
    </div>
  );
}
