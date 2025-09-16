import os
from flask import Flask, render_template_string, request, jsonify, session
from openai import OpenAI
from flask_session import Session

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")  # Needed for sessions
app.config["SESSION_TYPE"] = "filesystem"  # Store in memory
Session(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- HTML UI ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AI Chatbot + Image Generator</title>
  <style>
    body {
      font-family: "Segoe UI", Roboto, Arial, sans-serif;
      background: #f9fafb;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
    }
    #chatbox {
      width: 100%;
      max-width: 600px;
      height: 80vh;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 6px 18px rgba(0,0,0,0.1);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    #header {
      padding: 16px;
      background: #4CAF50;
      color: white;
      font-size: 18px;
      font-weight: bold;
      text-align: center;
    }
    #messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f4f6f8;
    }
    .msg {
      max-width: 75%;
      padding: 12px 16px;
      border-radius: 16px;
      line-height: 1.4;
      font-size: 15px;
    }
    .user {
      align-self: flex-end;
      background: #DCF8C6;
      border-bottom-right-radius: 4px;
    }
    .bot {
      align-self: flex-start;
      background: #fff;
      border: 1px solid #e2e2e2;
      border-bottom-left-radius: 4px;
    }
    .img {
      align-self: center;
      max-width: 100%;
    }
    .img img {
      max-width: 100%;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    #inputBox {
      display: flex;
      padding: 12px;
      border-top: 1px solid #eee;
      background: #fff;
    }
    #input {
      flex: 1;
      padding: 12px;
      border-radius: 12px;
      border: 1px solid #ccc;
      outline: none;
      font-size: 15px;
    }
    button {
      margin-left: 8px;
      padding: 12px 16px;
      border: none;
      background: #4CAF50;
      color: white;
      font-size: 15px;
      border-radius: 12px;
      cursor: pointer;
      transition: background 0.2s;
    }
    button:hover {
      background: #43a047;
    }
  </style>
</head>
<body>
  <div id="chatbox">
    <div id="header">🤖 AI Chatbot + 🎨 Image Generator</div>
    <div id="messages"></div>
    <div id="inputBox">
      <input type="text" id="input" placeholder="Type a message or 'draw: cat in space'" />
      <button onclick="sendMessage()">Send</button>
    </div>
  </div>

<script>
  function sendMessage() {
    let input = document.getElementById("input").value;
    if (input.trim() === "") return;
    addMessage("user", input);
    document.getElementById("input").value = "";

    fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({msg: input})
    })
    .then(res => res.json())
    .then(data => {
      if (data.type === "text") {
        addMessage("bot", data.reply);
      } else if (data.type === "image") {
        addImage(data.url);
      }
    });
  }

  function addMessage(sender, text) {
    let msgDiv = document.createElement("div");
    msgDiv.classList.add("msg", sender);
    msgDiv.innerText = text;
    document.getElementById("messages").appendChild(msgDiv);
    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
  }

  function addImage(url) {
    let imgDiv = document.createElement("div");
    imgDiv.classList.add("img");
    imgDiv.innerHTML = `<img src="${url}" alt="Generated Image">`;
    document.getElementById("messages").appendChild(imgDiv);
    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
  }
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("msg")

    # Initialize conversation memory
    if "history" not in session:
        session["history"] = [
            {"role": "system", "content": "You are a helpful AI assistant with text + image generation."}
        ]

    # If user asks for image
    if user_msg.lower().startswith("draw:"):
        prompt = user_msg[5:].strip()
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="512x512"
        )
        img_url = result.data[0].url
        return jsonify({"type": "image", "url": img_url})

    # Add user message to history
    session["history"].append({"role": "user", "content": user_msg})

    # GPT call with memory
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=session["history"]
    )
    bot_reply = response.choices[0].message.content

    # Save bot reply to memory
    session["history"].append({"role": "assistant", "content": bot_reply})

    return jsonify({"type": "text", "reply": bot_reply})

# For Vercel
def handler(event, context):
    return app(event, context)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
