import pandas as pd
import json

def prepare_anonymized_portfolio_data(df, gesamtwert):
    if df.empty or gesamtwert <= 0:
        return ""
    
    anonymized_data = [f"Gesamtwert des Portfolios: {gesamtwert:,.2f} EUR\n"]
    for _, row in df.iterrows():
        name = row.get('Wertpapier', 'Unbekannt')
        ticker = row.get('Ticker', '')
        if pd.isna(ticker) or str(ticker).strip() == "":
            identifier = name
        else:
            identifier = f"{name} ({ticker})"
            
        kaufwert = row['Kaufpreis'] + row['Orderkost']
        
        if 'Live_Kurs' in df.columns and pd.notna(row.get('Live_Kurs')):
            akt_wert = row['St_Nom'] * row['Live_Kurs']
        else:
            akt_wert = row['Wert']
            
        gewichtung = (akt_wert / gesamtwert * 100) if gesamtwert > 0 else 0
        gewinn = akt_wert - kaufwert
        performance = (gewinn / kaufwert * 100) if kaufwert > 0 else 0
        
        anonymized_data.append(f"- Position: {identifier} | Anteil am Portfolio: {gewichtung:.2f}% | Performance bisher: {performance:.2f}%")
        
    return "\n".join(anonymized_data)

def get_llm_response_stream(config, history, retries=1):
    import time
    from backend.prompts import get_advisor_system_prompt
    
    system_instruction = get_advisor_system_prompt()
    
    for attempt in range(retries + 1):
        try:
            if config['provider'] == 'Google Gemini':
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=config['api_key'])
                contents = []
                for idx, msg in enumerate(history):
                    role = "user" if msg['role'] == 'user' else "model"
                    if idx < len(history) - 1 and role == "user" and 'display' in msg:
                        content_to_send = msg['display']
                    else:
                        content_to_send = msg['content']
                    contents.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=content_to_send)])
                    )
                
                genai_config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=8192
                )
                
                response_stream = client.models.generate_content_stream(
                    model=config.get('model', 'gemini-2.5-flash'),
                    contents=contents,
                    config=genai_config
                )
                
                def gen():
                    try:
                        for chunk in response_stream:
                            if chunk.text:
                                yield chunk.text
                    except Exception as e:
                        yield f"\n\n*[Verbindung zur KI unterbrochen: {e}]*"
                return gen(), None
            elif config['provider'] == 'Anthropic Claude':
                import requests
                headers = {
                    "x-api-key": config['api_key'],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                messages = []
                for idx, msg in enumerate(history):
                    role = "user" if msg['role'] == 'user' else "assistant"
                    
                    if idx < len(history) - 1 and role == "user" and 'display' in msg:
                        content_to_send = msg['display']
                    else:
                        content_to_send = msg['content']
                        
                    messages.append({"role": role, "content": content_to_send})
                    
                cache_slots = 0
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i]["role"] == "user":
                        messages[i]["content"] = [
                            {
                                "type": "text",
                                "text": messages[i]["content"],
                                "cache_control": {"type": "ephemeral"}
                            }
                        ]
                        cache_slots += 1
                        if cache_slots >= 2:
                            break
                    
                payload = {
                    "model": config.get('model', 'claude-sonnet-4-6'),
                    "system": [{"type": "text", "text": system_instruction, "cache_control": {"type": "ephemeral"}}],
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 8192
                }
                
                url = 'https://api.anthropic.com/v1/messages'
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=300)
                response.raise_for_status()
                
                def claude_gen():
                    try:
                        with response:
                            for line in response.iter_lines():
                                if line:
                                    line = line.decode('utf-8')
                                    if line.startswith('data: '):
                                        data_str = line[6:]
                                        if data_str.strip() == '[DONE]':
                                            continue
                                        try:
                                            data = json.loads(data_str)
                                            if data.get('type') == 'content_block_delta' and data.get('delta', {}).get('type') == 'text_delta':
                                                yield data['delta']['text']
                                        except Exception:
                                            pass
                    except Exception as e:
                        yield f"\n\n*[Verbindung zur KI unterbrochen: {e}]*"
                return claude_gen(), None
            else:
                import requests
                headers = {"Content-Type": "application/json"}
                if config.get('api_key'):
                    headers["Authorization"] = f"Bearer {config['api_key']}"
                
                messages = [{"role": "system", "content": system_instruction}]
                for idx, msg in enumerate(history):
                    role = "user" if msg['role'] == 'user' else "assistant"
                    
                    if idx < len(history) - 1 and role == "user" and 'display' in msg:
                        content_to_send = msg['display']
                    else:
                        content_to_send = msg['content']
                        
                    messages.append({"role": role, "content": content_to_send})
                    
                payload = {
                    "model": config.get('model', 'local-model'),
                    "messages": messages,
                    "stream": True
                }
                
                url = config.get('base_url', 'http://localhost:11434/v1').rstrip('/') + '/chat/completions'
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=300)
                response.raise_for_status()
                
                def local_gen():
                    reasoning_started = False
                    reasoning_ended = False
                    try:
                        with response:
                            for line in response.iter_lines():
                                if line:
                                    line = line.decode('utf-8')
                                    if line.startswith('data: '):
                                        data_str = line[6:]
                                        if data_str.strip() == '[DONE]':
                                            break
                                        try:
                                            data = json.loads(data_str)
                                            delta = data['choices'][0].get('delta', {})
                                            
                                            reasoning = delta.get('reasoning_content')
                                            if reasoning:
                                                if not reasoning_started:
                                                    yield "🤔 **Gedankengang der KI:**\n\n"
                                                    reasoning_started = True
                                                yield reasoning
                                                
                                            content = delta.get('content')
                                            if content:
                                                if reasoning_started and not reasoning_ended:
                                                    yield "\n\n---\n\n**Antwort:**\n\n"
                                                    reasoning_ended = True
                                                yield content
                                        except Exception:
                                            pass
                    except Exception as e:
                        yield f"\n\n*[Verbindung zur KI unterbrochen: {e}]*"
                return local_gen(), None
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and "RESOURCE_EXHAUSTED" in error_msg:
                return None, "⚠️ **API Limit erreicht (429 Rate Limit)**"
            if attempt < retries:
                import time
                time.sleep(2)
                continue
            return None, f"Fehler bei der KI-Analyse nach {retries+1} Versuchen: {error_msg}"
