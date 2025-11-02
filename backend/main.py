import os
import uvicorn
import base64
import pymysql
import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime

# GCP Imports
from google.cloud import secretmanager
from google.cloud.sql.connector import Connector
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel

from agent_hub import (
    AGENT_PROMPTS, PROMPT_ORCHESTRATOR, PROMPT_ANALYST, 
    PROMPT_GUIDE, PROMPT_STRATEGIST, PROMPT_ARCHIVIST
)

from tts_service import generate_tts_bytes

# --- GCP Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
REGION = os.environ.get("GCP_REGION")
DB_INSTANCE_NAME = os.environ.get("DB_INSTANCE_NAME")
DB_NAME = ""
DB_USER = "root"
DB_PASS_SECRET_NAME = os.environ.get("DB_PASS_SECRET_NAME")

# --- Global Clients ---
app = FastAPI()
db_pool = None
gemini_flash = None
embedding_model = None

# --- Pydantic Models for Journal ---
class JournalEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True) 
    id: int
    created_at: datetime
    content: str 

class JournalResponse(BaseModel):
    entries: List[JournalEntry]

# --- Helper Functions ---
def get_db_pass():
    """Fetches the DB password from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{DB_PASS_SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

@app.on_event("startup")
def startup_event():
    """Initialize all GCP clients and DB pool."""
    global db_pool, gemini_flash, embedding_model
    
    vertexai.init(project=PROJECT_ID, location=REGION)
    gemini_flash = GenerativeModel("gemini-1.5-flash-001")
    embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
    
    try:
        connector = Connector()
        db_pass = get_db_pass()
        def getconn() -> pymysql.connections.Connection:
            return connector.connect(
                f"{PROJECT_ID}:{REGION}:{DB_INSTANCE_NAME}",
                "pymysql", user=DB_USER, password=db_pass, db=DB_NAME,
                cursorclass=pymysql.cursors.DictCursor # Use DictCursor!
            )
        db_pool = getconn()
        print("DB pool initialized.")
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        raise e

def get_or_create_default_journal(user_id: str) -> int:
    """
    Finds the user's 'Default Journal' (for all chats).
    If it doesn't exist, this creates it.
.
    """
    with db_pool.cursor() as cursor:
        # Check if the user exists 
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            print(f"Warning: User {user_id} not found. Creating a test user.")
            cursor.execute(
                "INSERT INTO users (id, email, password, full_name) VALUES (%s, %s, %s, %s)",
                (user_id, f"test_{user_id}@clarity.ai", "pass", "Test User")
            )
            # db_pool.commit() 
        

        cursor.execute(
            "SELECT id FROM journals WHERE user_id = %s AND title = 'Default Journal' LIMIT 1",
            (user_id,)
        )
        journal = cursor.fetchone()
        
        if journal:
            return journal['id']
        else:
            print(f"Creating 'Default Journal' for user {user_id}...")
            cursor.execute(
                "INSERT INTO journals (user_id, title) VALUES (%s, 'Default Journal')",
                (user_id,)
            )
            db_pool.commit()
            return cursor.lastrowid

# --- RAG FUNCTION ---
async def get_relevant_entries_from_db(journal_id: int, vector: List[float]) -> List[str]:
    """
    Performs a server-side RAG query on the journal_pages table.
    """
    with db_pool.cursor() as cursor:
        vector_str = str(vector)
        sql = """
            SELECT content FROM journal_pages
            WHERE journal_id = %s
            ORDER BY COSINE_SIMILARITY(text_vector, %s) DESC
            LIMIT 5
        """
        cursor.execute(sql, (journal_id, vector_str))
        
        plaintext_entries = [row['content'] for row in cursor.fetchall()]
        return plaintext_entries

# --- MAIN WEBSOCKET ENDPOINT ---
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    # At the start of the chat, find the journal we'll be writing to.
    try:
        journal_id = get_or_create_default_journal(user_id)
        print(f"User {user_id} connected. Writing to journal_id {journal_id}.")
    except Exception as e:
        print(f"CRITICAL DB ERROR: Could not get journal for user {user_id}. {e}")
        await websocket.close(code=1011)
        return

    try:
        while True:
            data_json = await websocket.receive_json()
            
            if data_json.get("type") == "NEW_ENTRY":
                payload = data_json["payload"]
                raw_text = payload["raw_text"]

                # 2. EMBED
                print("Task 1: Generating vector...")
                embeddings = embedding_model.get_embeddings([raw_text])
                vector = embeddings[0].values

                # 3. STORE (Async)
                print("Task 2: Storing in journal_pages...")
                with db_pool.cursor() as cursor:
                    sql = """
                        INSERT INTO journal_pages (journal_id, content, text_vector, entry_type) 
                        VALUES (%s, %s, %s, 'text')
                    """
                    vector_str = str(vector) 
                    cursor.execute(sql, (journal_id, raw_text, vector_str))
                db_pool.commit()
                
                # 4. ORCHESTRATOR
                print("Task 3: Calling Orchestrator...")
                orchestrator_prompt = f"{PROMPT_ORCHESTRATOR}\n<new_entry>{raw_text}</new_entry>"
                orchestrator_response = await gemini_flash.generate_content_async([orchestrator_prompt])
                try:
                    decision = json.loads(orchestrator_response.text)
                    route = decision.get("route", "NONE")
                except Exception:
                    route = "NONE"
                print(f"Orchestrator decision: {route}")

                # 5. ROUTING
                if route == "NONE":
                    await websocket.send_json({"type": "ACK", "status": "saved_and_processed"})
                    continue 

                # 6. RAG RETRIEVAL (Fast, 1-step, Server-Side)
                print("Task 4: Running SERVER-SIDE RAG (fetch)...")
                history = "No relevant history found."
                if route in ["Analyst", "Strategist", "Archivist", "Guide"]:
                    plaintext_context = await get_relevant_entries_from_db(journal_id, vector) 
                    if plaintext_context:
                        history = "\n---\n".join(plaintext_context)
                
                # 7. SPECIALIST AGENT
                print(f"Task 5: Calling Specialist Agent: {route}")
                specialist_prompt_template = AGENT_PROMPTS.get(route)
                full_prompt = f"""
                <system_instructions>{specialist_prompt_template}</system_instructions>
                <history>{history}</history>
                <new_entry>{raw_text}</new_entry>
                Provide your agentic response:
                """
                
                # 8. STREAMING RESPONSE
                print("Task 6: Streaming response...")
                stream = await gemini_flash.generate_content_async([full_prompt], stream=True)
                full_text_response = ""
                async for chunk in stream:
                    token = chunk.text
                    full_text_response += token
                    await websocket.send_json({"type": "TOKEN", "payload": token})
                
                # 9. TTS 
                print("Task 7: Generating TTS...")
                audio_bytes = generate_tts_bytes(full_text_response)
                
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    await websocket.send_json({"type": "AUDIO", "payload": audio_base64})
                else:
                    print("TTS generation failed, not sending audio.")

    except WebSocketDisconnect:
        print(f"Client {user_id} disconnected.")
    except Exception as e:
        print(f"An error occurred in websocket: {e}")

# --- SCHEDULED ANALYST ENDPOINT  ---
SCHEDULER_TOKEN = "YOUR_OWN_SECRET_CRON_TOKEN_12345" 
@app.post("/run-longitudinal-analysis/{user_id}")
async def run_longitudinal_analysis(user_id: str, request: Request):
    token = request.headers.get("X-Scheduler-Token")
    if token != SCHEDULER_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        journal_id = get_or_create_default_journal(user_id)
    except Exception as e:
        return {"status": "error", "detail": f"Could not find user/journal: {e}"}

    print(f"Task 1: Starting longitudinal analysis for user {user_id} (journal_id {journal_id})...")
    
    with db_pool.cursor() as cursor:
        sql = """
            SELECT content FROM journal_pages
            WHERE journal_id = %s AND created_at >= NOW() - INTERVAL 7 DAY
            ORDER BY created_at ASC
        """
        cursor.execute(sql, (journal_id,))
        entries = [row['content'] for row in cursor.fetchall()]

    if not entries:
        return {"status": "success", "detail": "No new entries"}

    full_transcript = "\n---\n".join(entries)

    print("Task 2: Calling Analyst agent...")
    analysis_request = "Please analyze my entries from the past week and provide one single, profound insight..."
    full_prompt = full_prompt = f"""
    <system_instructions>{PROMPT_ANALYST}</system_instructions>
    <history>{full_transcript}</history>
    <new_entry>{analysis_request}</new_entry>
    Provide your agentic response:
    """
    response = await gemini_flash.generate_content_async([full_prompt])
    insight_text = response.text

    print("Task 3: Saving new insight to database...")
    with db_pool.cursor() as cursor:
        sql = "INSERT INTO analysis_reports (user_id, insight_text) VALUES (%s, %s)"
        cursor.execute(sql, (user_id, insight_text))
    db_pool.commit()
    
    return {"status": "success", "insight_generated": insight_text[:50] + "..."}

@app.get("/v1/journal/{user_id}", response_model=JournalResponse)
async def get_journal_entries(user_id: str):
    try:
        journal_id = get_or_create_default_journal(user_id)
    except Exception:
        return JournalResponse(entries=[])

    print(f"Fetching journal history for user {user_id} (journal_id {journal_id})...")
    
    with db_pool.cursor() as cursor:
        sql = """
            SELECT id, created_at, content 
            FROM journal_pages
            WHERE journal_id = %s
            ORDER BY created_at DESC
        """
        cursor.execute(sql, (journal_id,))
        results = cursor.fetchall()
        entries = [JournalEntry(**row) for row in results]

    return JournalResponse(entries=entries)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))