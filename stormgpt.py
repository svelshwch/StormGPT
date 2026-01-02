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
