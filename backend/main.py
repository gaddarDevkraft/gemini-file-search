import os
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Handle CORS origins
raw_origins = os.getenv("FRONTEND_URL", "*")
if raw_origins == "*":
    # IMPORTANT: If using wildcard "*", allow_credentials MUST be False
    # Otherwise, browsers will block the request.
    origins_list = ["*"]
    allow_creds = False
else:
    # Set this in Vercel to: https://gemini-file-search-ui.vercel.app
    origins_list = [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]
    allow_creds = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "backend running", "cors_origins": origins_list}

@app.get("/api")
def root():
    return {"status": "backend ok", "frontend_allowed": FRONTEND_URL}

# Setup Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
client = genai.Client(api_key=GEMINI_API_KEY)


file_search_store_id = os.getenv("FILE_SEARCH_STORE_ID")

@app.post("/upload-doc")
async def upload_doc(file: UploadFile = File(...)):
    global file_search_store_id
    
    file_path = f"/tmp/temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        store = client.file_search_stores.create(
            config={'display_name': f'Store_{file.filename}'}
        )
        file_search_store_id = store.name
        print(f"Created store: {store}")
        
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=file_search_store_id,
            config={'display_name': file.filename}
        )

        while not operation.done:
            time.sleep(2)
            operation = client.operations.get(operation)

        return {"message": "Document uploaded and indexed successfully", "store_id": file_search_store_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/search")
async def search(question: str = Form(...), file_search_store_id_param: str = Form(None)):
    
    target_store_id = os.getenv("FILE_SEARCH_STORE_ID")
    
    if not target_store_id:
        target_store_id = file_search_store_id_param
    
    if not target_store_id:
        raise HTTPException(status_code=400, detail="No Store ID available.")

    prompt = f"""
        Answer the following question based only on the provided documents.

        Question:
        {question}

        Instructions:
        - Provide a clear and concise answer.
        - Do not invent information or sources.
        - At the bottom of the answer, include the source details in the exact format shown below.
        - Use slide numbers (not page numbers) for PPT files.
        - If the answer is not found in the documents, clearly state that and set the confidence score to 0.

        Response format:

        Answer:
        <write the answer here>

        Source:
        - Document: <document_name.ppt>
        - Slide Number(s): <slide numbers>
        - Confidence Score: <integer between 0 and 100>

        """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[target_store_id]
                        )
                    )
                ]
            )
        )

        answer = response.text if response.text else "No answer content returned."
        
        citations = []
        if response.candidates and response.candidates[0].grounding_metadata:
            meta = response.candidates[0].grounding_metadata
            citations = meta.grounding_chunks

        return {
            "data" : response,
            "answer": answer,
            "citations": citations
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)