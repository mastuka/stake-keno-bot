import os
import sys
import time
import curses
import random
import hashlib
import hmac
import requests
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

class StealthAPI:
    def __init__(self, session_token):
        self.base_url = "https://api.stake.com"
        self.session = requests.Session()
        self.session.headers = {
            "x-access-token": session_token,
            "user-agent": self._rotate_user_agent(),
            "x-request-signature": "",
        }
        self.proxies = self._init_proxies()
        
    def _rotate_user_agent(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
        ]
        return random.choice(agents)
    
    def _init_proxies(self):
        return {
            'http': os.getenv('PROXY_URL', 'socks5://user:pass@gate.zenrows.com:8001'),
            'https': os.getenv('PROXY_URL', 'socks5://user:pass@gate.zenrows.com:8001')
        }

    def _sign_request(self, payload):
        secret = bytes(os.getenv('API_SECRET', 'default_secret'), 'utf-8')
        return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()

    def get_history(self, limit=500):
        time.sleep(random.uniform(1.2, 3.5))  # Random delay
        try:
            response = self.session.post(
                f"{self.base_url}/crash/history",
                json={"limit": limit},
                proxies=self.proxies,
                timeout=10
            )
            return response.json()['rounds']
        except Exception as e:
            print(f"History error: {str(e)}")
            return []

    def place_bet(self, numbers, amount=0.01, currency='btc'):
        payload = {
            "amount": amount,
            "currency": currency,
            "numbers": numbers,
            "clientSeed": hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        }
        self.session.headers['x-request-signature'] = self._sign_request(str(payload))
        
        try:
            response = self.session.post(
                f"{self.base_url}/games/keno/bet",
                json=payload,
                proxies=self.proxies,
                timeout=8
            )
            return response.json()
        except Exception as e:
            print(f"Bet error: {str(e)}")
            return None

class KenoAI:
    def __init__(self):
        self.model = self._build_model()
        
    def _build_model(self):
        model = Sequential([
            LSTM(64, input_shape=(50, 20), return_sequences=True),
            LSTM(32),
            Dense(20, activation='softmax')
        ])
        model.compile(loss='categorical_crossentropy', optimizer='adam')
        return model
    
    def train(self, data):
        X = np.array([round['numbers'][-50:] for round in data])
        y = np.array([round['numbers'][:20] for round in data])
        self.model.fit(X, y, epochs=10, batch_size=32, verbose=0)
    
    def predict(self, last_round):
        sequence = np.array(last_round['numbers'][-50:]).reshape(1,50,20)
        return self.model.predict(sequence, verbose=0)[0]

class KenoCLI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.use_default_colors()
        self._init_ui()
        
    def _init_ui(self):
        self.stdscr.nodelay(1)
        self.win = curses.newwin(20, 80, 0, 0)
        
    def display(self, balance, history, prediction):
        self.win.clear()
        # Header
        self.win.addstr(0, 0, f"Balance: {balance:.8f} BTC | Last 5 bets")
        # History table
        for idx, bet in enumerate(history[-5:], 1):
            self.win.addstr(idx, 2, f"{bet['numbers']} → {bet['multiplier']:0.2f}x")
        # Prediction area
        self.win.addstr(7, 0, "Next round prediction:")
        self.win.addstr(8, 2, f"Numbers: {prediction}")
        self.win.refresh()

def main(stdscr):
    session_token = os.getenv('STAKE_TOKEN', 'your_session_token_here')
    
    # Init components
    api = StealthAPI(session_token)
    ai = KenoAI()
    ui = KenoCLI(stdscr)
    
    # Initial training
    history = api.get_history(500)
    ai.train(history)
    
    while True:
        try:
            # Get latest round
            current_round = api.get_history(1)[0]
            
            # Predict and bet
            prediction = ai.predict(current_round)
            if np.max(prediction) > 0.85:  # Confidence threshold
                bet_result = api.place_bet(
                    numbers=np.argsort(prediction)[-5:].tolist(),
                    amount=0.01
                )
                if bet_result:
                    history.append(bet_result)
            
            # Update UI
            balance = 1.0  # Implement actual balance check
            ui.display(balance, history, prediction)
            
            time.sleep(random.uniform(2.8, 4.2))
            
        except KeyboardInterrupt:
            sys.exit(0)

if __name__ == "__main__":
    curses.wrapper(main)
