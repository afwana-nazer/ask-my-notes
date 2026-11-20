
import { useState } from "react";
import "./App.css";

const API = "http://localhost:8000";

// Turns sources into short text, like "rules.pdf p.2"
function showSources(sources) {
  if (!sources || sources.length === 0) return "";

  const names = sources.map(
    (s) => `${s.source} p.${s.page}`
  );

  return [...new Set(names)].join(" · ");
}

function App() {

  // The app's memory
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Adds one message to the chat
  function addMessage(msg) {
    setMessages((old) => [...old, msg]);
  }

  // Runs when you press Ask
  async function askQuestion() {

    if (!question.trim() || loading) return;

    const myQuestion = question;

    addMessage({
      role: "user",
      text: myQuestion
    });

    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: myQuestion
        }),
      });

      if (!res.ok) {
        throw new Error("Server error");
      }

      const data = await res.json();

      addMessage({
        role: "bot",
        text: data.answer,
        sources: data.sources
      });

    } catch (error) {
      addMessage({
        role: "bot",
        text: "Oops! Is the backend running?"
      });

    } finally {
      setLoading(false);
    }
  }

  // Upload a PDF file
  async function uploadPdf(e) {

    const file = e.target.files[0];

    if (!file) return;

    // Check whether the selected file is a PDF
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      addMessage({
        role: "bot",
        text: "Please select a PDF file."
      });
      e.target.value = "";
      return;
    }

    const form = new FormData();

    form.append("file", file);

    setLoading(true);

    addMessage({
      role: "bot",
      text: `Uploading ${file.name}...`
    });

    try {
      const res = await fetch(`${API}/upload`, {
        method: "POST",
        body: form
      });

      if (!res.ok) {
        throw new Error("Upload error");
      }

      const data = await res.json();

      addMessage({
        role: "bot",
        text: data.message
      });

    } catch (error) {
      addMessage({
        role: "bot",
        text: "Upload failed. Try again."
      });

    } finally {
      setLoading(false);
      e.target.value = "";
    }
  }

  // What you see on the screen
  return (
    <div className="app">

      <h1>📚 Ask My Notes</h1>

      <div className="chat">

        {messages.length === 0 && (
          <p className="hint">
            Ask anything about your notes 👇
          </p>
        )}

        {messages.map((m, i) => (

          <div key={i} className={`msg ${m.role}`}>

            <p>{m.text}</p>

            {m.sources && (
              <small>
                📄 {showSources(m.sources)}
              </small>
            )}

          </div>

        ))}

        {loading && (
          <div className="msg bot">
            Thinking… 🤔
          </div>
        )}

      </div>

      <div className="ask-box">

        {/* PDF Upload Button */}
        <label className="upload">
          📎 PDF

          <input
            type="file"
            accept=".pdf,application/pdf"
            hidden
            onChange={uploadPdf}
            disabled={loading}
          />
        </label>

        {/* Question Input */}
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && askQuestion()
          }
          placeholder="Type your question…"
          disabled={loading}
        />

        {/* Ask Button */}
        <button
          onClick={askQuestion}
          disabled={loading}
        >
          Ask
        </button>

      </div>

    </div>
  );
}

export default App;
