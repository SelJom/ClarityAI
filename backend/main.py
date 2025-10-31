import os
import uvicorn
import base64
import pymysql
import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import List

# GCP Imports
from google.cloud import texttospeech, secretmanager
from google.cloud.sql.connector import Connector
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel

from agent_hub import (
    AGENT_PROMPTS, PROMPT_ORCHESTRATOR, PROMPT_ANALYST, 
    PROMPT_GUIDE, PROMPT_STRATEGIST, PROMPT_ARCHIVIST
)

# --- GCP Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
REGION = os.environ.get("GCP_REGION")
DB_INSTANCE_NAME = os.environ.get("DB_INSTANCE_NAME")
DB_NAME = "clarity_db"
DB_USER = "root"
DB_PASS_SECRET_NAME = os.environ.get("DB_PASS_SECRET_NAME")

# --- Global Clients ---
app = FastAPI()
db_pool = None
gemini_flash = None
embedding_model = None
tts_client = None

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
    global db_pool, gemini_flash, embedding_model, tts_client
    
    vertexai.init(project=PROJECT_ID, location=REGION)
    gemini_flash = GenerativeModel("gemini-1.5-flash-001")
    embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
    tts_client = texttospeech.TextToSpeechClient()
    
    try:
        connector = Connector()
        db_pass = get_db_pass()
        def getconn() -> pymysql.connections.Connection:
            return connector.connect(
                f"{PROJECT_ID}:{REGION}:{DB_INSTANCE_NAME}",
                "pymysql", user=DB_USER, password=db_pass, db=DB_NAME
            )
        db_pool = getconn()
        print("DB pool initialized.")
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        raise e


@app.get("/")
def health_check():
    return {"status": "Clarity AI 'Trusted Server' is running!"}

async def rag():
    pass

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            # 1. Wait for a message from the client
            data_json = await websocket.receive_json()
            
            if data_json.get("type") == "NEW_ENTRY":
                payload = data_json["payload"]
                raw_text = payload["raw_text"]

                # 2. EMBED
                print("Task 1: Generating vector...")
                embeddings = embedding_model.get_embeddings([raw_text])
                vector = embeddings[0].values

                # 3. STORE (Async)
                print("Task 2: Storing plaintext entry...")
                with db_pool.cursor() as cursor:
                    sql = "INSERT INTO user_entries (user_id, plaintext_text, text_vector) VALUES (%s, %s, %s)"
                    vector_str = str(vector) 
                    cursor.execute(sql, (user_id, raw_text, vector_str))
                db_pool.commit()
                
                # 4. ORCHESTRATOR: Decide if we should respond
                print("Task 3: Calling Orchestrator...")
                orchestrator_prompt = f"{PROMPT_ORCHESTRATOR}\n<new_entry>{raw_text}</new_entry>"
                orchestrator_response = await gemini_flash.generate_content_async([orchestrator_prompt])
                
                try:
                    decision = json.loads(orchestrator_response.text)
                    route = decision.get("route", "NONE")
                    print(f"Orchestrator decision: {route}")
                except Exception as e:
                    print(f"Orchestrator failed to return valid JSON: {e}")
                    route = "NONE"

                # 5. ROUTING: If no response, do nothing.
                if route == "NONE":
                    await websocket.send_json({"type": "ACK", "status": "saved_and_processed"})
                    continue 

                # 6. RAG RETRIEVAL (Fast, 1-step, Server-Side)
                print("Task 4: Running SERVER-SIDE RAG (fetch)...")
                
                # We only run RAG if the agent needs it.
                # The Guide doesn't need history.
                history = "No relevant history found."
                if route in ["Analyst", "Strategist", "Archivist"]:
                    plaintext_context = await rag(user_id, vector)
                    if plaintext_context:
                        history = "\n---\n".join(plaintext_context)
                
                # 7. SPECIALIST AGENT: Call the chosen agent
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
                
                # 9. TTS: Once text is complete, get audio
                print("Task 7: Generating TTS...")
                #Eve to complete
                

    except WebSocketDisconnect:
        print(f"Client {user_id} disconnected.")
    except Exception as e:
        print(f"An error occurred in websocket: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))