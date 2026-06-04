from duckduckgo_search import DDGS
try:
    with DDGS() as ddgs:
        results = list(ddgs.text("Apple", max_results=3))
        print(f"Results: {results}")
except Exception as e:
    print(f"Error: {e}")
