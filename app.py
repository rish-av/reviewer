import os
import io
import uuid
from flask import Flask, render_template, request, jsonify
import fitz  # PyMuPDF for PDF processing
import openai
import requests

# Set your API keys here or load from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")  # if needed

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Global dictionary to hold ephemeral GPT sessions
# In production, consider a more robust cache with expiration.
sessions = {}


def pdf_to_html(pdf_path):
    """Converts PDF to HTML using PyMuPDF. Note: This is a simplified conversion."""
    doc = fitz.open(pdf_path)
    html_content = "<html><body>"
    for page in doc:
        page_html = page.get_text("html")
        html_content += page_html
    html_content += "</body></html>"
    return html_content


def get_top_citations(pdf_text):
    """
    Uses OpenAI API to extract and retrieve top 5 citations from the provided PDF text.
    """
    prompt = (
        "Extract the top 5 citations from the following text and provide their titles, "
        "authors, and years, separated by ' - ' on each line:\n\n" + pdf_text
    )
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
        )
        citations_text = response.choices[0].message.content.strip()
        
        citations = []
        for line in citations_text.split("\n"):
            parts = line.split(" - ")
            if len(parts) == 3:
                title, authors, year = parts
                citations.append({
                    "title": title.strip(),
                    "authors": authors.strip(),
                    "year": year.strip()
                })
        
        # Use Semantic Scholar API to get DOIs and PDF links
        for citation in citations:
            query = f"{citation['title']} {citation['authors']} {citation['year']}"
            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "fields": "title,authors,year,doi,url"},
                headers={"x-api-key": SEMANTIC_SCHOLAR_API_KEY}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    paper = data["data"][0]
                    citation["doi"] = paper.get("doi", "N/A")
                    citation["pdf_link"] = paper.get("url", "N/A")
                else:
                    citation["doi"] = "N/A"
                    citation["pdf_link"] = "N/A"
            else:
                citation["doi"] = "N/A"
                citation["pdf_link"] = "N/A"
    except Exception as e:
        citations = [{"error": f"Error calling OpenAI or Semantic Scholar API: {str(e)}"}]
    
    return citations


def init_gpt_session(domain_knowledge):
    """
    Initializes an ephemeral GPT session by creating a conversation context.
    The context begins with a system message that includes the provided domain knowledge.
    """
    session_id = str(uuid.uuid4())
    system_message = (
        "You are a knowledgeable assistant. The following is the domain knowledge for the session:\n\n"
        + domain_knowledge
    )
    sessions[session_id] = [{"role": "system", "content": system_message}]
    return session_id


def query_gpt(session_id, question):
    """
    Appends the user's question to the conversation context stored in the session,
    queries OpenAI, then updates the session with the assistant's answer.
    """
    if session_id not in sessions:
        return "Session expired or invalid."
    
    conversation = sessions[session_id]
    conversation.append({"role": "user", "content": question})
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation,
            temperature=0.2,
            max_tokens=150,
        )
        answer = response.choices[0].message.content.strip()
        conversation.append({"role": "assistant", "content": answer})
    except Exception as e:
        answer = f"Error calling OpenAI API: {str(e)}"
    
    return answer


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    pdf_file = request.files["pdf"]
    if pdf_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_file.filename)
    pdf_file.save(file_path)
    
    # Convert PDF to HTML
    html_content = pdf_to_html(file_path)
    
    # Extract text from PDF for citation analysis
    with fitz.open(file_path) as doc:
        pdf_text = "\n".join([page.get_text() for page in doc])
    
    # Retrieve top 5 citations
    citations = get_top_citations(pdf_text)
    
    # Build domain knowledge from the PDF text and citations.
    domain_knowledge = pdf_text + "\n\nCitations:\n"
    for citation in citations:
        domain_knowledge += (
            f"{citation.get('title', 'N/A')} ({citation.get('year', 'N/A')}) by "
            f"{citation.get('authors', 'N/A')} - DOI: {citation.get('doi', 'N/A')}\n"
        )
        if citation.get("pdf_link") and citation["pdf_link"] != "N/A":
            try:
                response = requests.get(citation["pdf_link"])
                if response.status_code == 200:
                    # Use PyMuPDF to extract text from the fetched PDF
                    fetched_doc = fitz.open(stream=response.content, filetype="pdf")
                    fetched_pdf_text = "\n".join([page.get_text() for page in fetched_doc])
                    domain_knowledge += f"\nFetched PDF Text:\n{fetched_pdf_text}\n"
            except Exception as e:
                domain_knowledge += f"\nError fetching PDF: {str(e)}\n"
    
    # Initialize an ephemeral GPT session with the domain knowledge.
    session_id = init_gpt_session(domain_knowledge)
    
    return jsonify({
        "html": html_content,
        "session_id": session_id,
        "citations": citations
    })


@app.route("/qna", methods=["POST"])
def qna():
    data = request.get_json()
    question = data.get("question", "")
    session_id = data.get("session_id", "")
    
    if not question or not session_id:
        return jsonify({"error": "Missing question or session ID"}), 400
    
    answer = query_gpt(session_id, question)
    return jsonify({"answer": answer})


@app.route("/kill_session", methods=["POST"])
def kill_session():
    """
    Endpoint to terminate an ephemeral GPT session.
    """
    data = request.get_json()
    session_id = data.get("session_id", "")
    if session_id in sessions:
        del sessions[session_id]
        return jsonify({"message": "Session terminated."})
    else:
        return jsonify({"error": "Invalid session ID."}), 400


if __name__ == "__main__":
    app.run(debug=True)
