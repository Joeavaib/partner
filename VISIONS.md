# 🔮 CXM Vision: The Harvest Mode

Diese Vision beschreibt die Erweiterung von CXM (ContextMachine) zur primären Kontext-Engine für agentische Workflows (wie die Raven-Luna-Trees Architektur in Maestro).

## 🎯 Ziel: Non-Interactive Context Harvesting
Bisher ist CXM auf den interaktiven Dialog mit einem menschlichen Entwickler ausgelegt. Um als 'Boden für die Trees' zu dienen, benötigt CXM einen rein maschinellen Modus, der präzisen Kontext für isolierte Coding-Aufgaben liefert.

### Der 'cxm harvest' Befehl
Ein neuer CLI-Befehl, der ohne Benutzerinteraktion (Gaps werden ignoriert oder inferiert) einen injizierbaren Kontext-Block für LLMs erzeugt.

**Beispiel-Aufruf:**
```bash
cxm harvest "auth_logic.py, jwt_helper" --intent "add_refresh_token" --format "xml"
```

---

## 🛠️ Technisches Konzept

1.  **CLI-Integration:** Erweiterung der `cli.py` um einen `harvest` Subparser.
2.  **Automated RAG-Pipeline:**
    *   **Intent-Analysis:** Nutzt den bestehenden `IntentAnalyzer`, um Fokus-Keywords zu extrahieren.
    *   **Silent Retrieval:** Führt das Retrieval & Reranking durch, ohne Rückfragen bei fehlenden Informationen zu stellen (Best-Effort Prinzip).
    *   **Context Assembly:** Formatiert die gefundenen Code-Snippets in ein für Coder-Modelle optimiertes Format (z.B. mit `<file_context>` Tags).
3.  **Output-Handling:** Der Kontext wird direkt über `stdout` ausgegeben, um in Bash-Pipes oder Variablen (`CONTEXT=$(cxm harvest ...)`) genutzt werden zu können.

---

## ⏱️ Aufwandsschätzung

Der geschätzte Gesamtaufwand beträgt ca. **3 Stunden**, da die Kern-Logik (RAG, Indexing, Assembler) bereits in der CXM-Library modular vorhanden ist.

| Task | Beschreibung | Aufwand |
| :--- | :--- | :--- |
| **CLI Extension** | Hinzufügen des `harvest` Subparsers in `cli.py`. | 0.5h |
| **Logic Handler** | Implementierung von `handle_harvest` (non-interactive flow). | 1.0h |
| **Formatting** | Erstellung eines spezialisierten XML/Markdown Output-Formats. | 0.5h |
| **Validation** | Tests der Bash-Pipes und Integrationstests mit Maestro. | 1.0h |

---

## 🔗 Integration in Maestro
Nach der Umsetzung kann Maestro (`orchestrator.py`) CXM direkt als "Sonderwerkzeug" nutzen, um Spezialisten-Prompts mit chirurgisch präzisem Projekt-Kontext anzureichern, was die Token-Kosten senkt und die Erfolgsrate (First-Try-Success) massiv steigert.