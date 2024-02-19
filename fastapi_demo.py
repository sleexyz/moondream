import uvicorn
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from PIL import Image
from moondream import Moondream, detect_device
from transformers import TextIteratorStreamer, CodeGenTokenizerFast as Tokenizer
import re
from threading import Thread
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

origins = [
    "http://localhost:1420", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Assuming the model and tokenizer are loaded similarly to gradio_demo.py
device, dtype = detect_device()
model_id = "vikhyatk/moondream1"
tokenizer = Tokenizer.from_pretrained(model_id)
moondream = Moondream.from_pretrained(model_id).to(device=device, dtype=dtype)
moondream.eval()

def answer_question(img, prompt):
    image_embeds = moondream.encode_image(img)
    # answers = moondream.answer_question(image_embeds=image_embeds, question=prompt, tokenizer=tokenizer)
    # clean_answers = [re.sub("<$|END$", "", answer) for answer in answers]
    # return clean_answers
    streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)
    thread = Thread(
        target=moondream.answer_question,
        kwargs={
            "image_embeds": image_embeds,
            "question": prompt,
            "tokenizer": tokenizer,
            "streamer": streamer,
        },
    )
    thread.start()
    # buffer = ""
    for new_text in streamer:
        clean_text = re.sub("<$|END$", "", new_text)
        # buffer += clean_text
        # data = buffer.strip("<END")
        yield "data: " + clean_text + "\n\n"


@app.post("/api/inference")
async def inference(prompt: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    # Assuming the model can process the image directly from bytes. 
    # You might need to convert it to the correct format depending on the model requirements.
    image = Image.open(BytesIO(contents))
    answers = answer_question(image, prompt)
    return StreamingResponse(answers, media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)