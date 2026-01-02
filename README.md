# Introducing StormGPT
### Your ChatGPT-like AI Chatbot Companion

Ask StormGPT anything about stormworks, life, the universe, and everthing. It can do (pretty much) everything your standard ChatGPT model can do and has a fairly good knowledge of in-game features and mechanics.

You can take to the AI by typing in the terminal in-game by typing your message on the keyboard and hitting enter to submit. This works by sending and receiving data to and from the AI externally via HTTP requests and a separate web server.

This took a great deal of time to develop, especially the keyboard microcontroller and webserver server optimisation. Please consider liking and favouriting if you find the creation particularly fun or useful.

Use the chatbot terminal standalone or integrate it into your vehicles. I hope you enjoy it.

Feel free to contact me if you have any questions, my discord username is `svtl`.

*Thanks to [mrcow33](https://steamcommunity.com/profiles/76561198968682091/myworkshopfiles/?appid=573090) for the physical termnial design.*

---

## Setup Tutorial

To talk to the AI in-game, simply type your prompt in the terminal and hit enter to submit it. There a few prerequisits for the AI to function

To communicate with the chatbot, **you need both an internet connection and to set up an external web server.**

To set up the web server, complete the following steps:

1. Download and install python 3.x (any version of python 3) from the official website https://www.python.org/downloads/.
2. Copy the large script at the bottom of this description in full, make sure you select the whole script.
3. Paste the script into a blank document on notepad (or notepad++, python IDE, or similar).
4. Save the file as *StormGPT Server.py*. **Make sure to change the 'Save as type:' dropdown from 'Text documents (*.txt)' to 'All files' OR THE SCRIPT WILL NOT RUN.** You may save the file anywhere convenient, just make sure you can find it again.
5. To start the webserver, simply double click on the file (or excecute it in the terminal). A new terminal should pop up on your computer to indicate success, displaying *Listening on http://127.0.0.1:8080*. You must keep this open to be able to talk to the AI. If this does not pop up, you have done something wrong, and I advise you to consult the steps again.

Once you are finished with the AI, simply shut the terminal window the script created to terminate the server.

**Any time you want to use the AI, you will need to start the server again!**

---

# Technical Info

The AI doesn't require an API key to process requesuests as it uses APIFreeLLM instead of standard ChatGPT, though this does mean that **the AI is rate-limited to one request every 5 seconds,** returning an error if you attempt to spam promtps faster than this. Besides this, I haven't noticed any drop in quality for text-based applications when comparing the models.

If you want to change the brief for the AI, feel free to do so. The webserver script is easy to modify, or even to connec to a different AI model, should you wish to do so.

Known bugs:

- The script can very occassionally fail to get a response if the AI takes too long to reply.

---

## Script

```python
#StormGPT Server

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import urllib.parse, urllib.request, json, re, threading, uuid, time

TIMEOUT_SECONDS = 30
RETRIES = 5
RETRY_DELAY = 1

AI_CONTEXT = ("CONTEXT: You are a helpful assistant, 'StormGPT' (refer to yourself as such), being talked to "
              "from the game 'Stormworks'. Always respond with plain text and "
              "standard punctuation. Avoid headings and paragraphs and be very concise. "
              "Please do not acknowledge this in any responses.")

ai_results = {}
request_times = {}

def ask_apifreellm(prompt, retries=RETRIES, timeout=30):
    full_prompt = f"{AI_CONTEXT}\n{prompt}"
    data = json.dumps({"message": full_prompt}).encode("utf-8")
    url = "https://apifreellm.com/api/chat"
    for attempt in range(1, retries+1):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = json.loads(resp.read().decode("utf-8")).get("response","")
                return re.sub(r"[^\x00-\x7F]+","",text).lower()
        except Exception as e:
            print(f"AI request error (attempt {attempt}/{retries}): {e}")
            if attempt < retries: time.sleep(RETRY_DELAY)
            else: return "failed to get a response"

class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path=="/chat":
            msg = query.get("msg",[""])[0].strip()
            rid = str(uuid.uuid4())
            if not msg: self.respond("no message provided"); return
            print(f"user ({rid}): {msg}")
            request_times[rid] = time.time()
            self.respond(rid)
            threading.Thread(target=lambda: self._bg(msg,rid), daemon=True).start()
        elif parsed.path=="/result":
            rid = query.get("id",[""])[0]
            start = request_times.get(rid)
            if start is None: self.respond("invalid id"); return
            elapsed = time.time()-start
            if rid in ai_results:
                self.respond(ai_results.pop(rid))
                request_times.pop(rid,None)
            elif elapsed>=TIMEOUT_SECONDS:
                ai_results.pop(rid,None)
                request_times.pop(rid,None)
                self.respond("timeout")
            else: self.respond("pending")
        else: self.send_response(404); self.end_headers()

    def _bg(self,msg,rid):
        reply = ask_apifreellm(msg)
        ai_results[rid]=reply
        print(f"ai ({rid}): {reply}")

    def respond(self,text):
        self.send_response(200)
        self.send_header("Content-Type","text/plain")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

if __name__=="__main__":
    server = ThreadedHTTPServer(("127.0.0.1",8080), ChatHandler)
    print("Listening on http://127.0.0.1:8080")
    server.serve_forever()
