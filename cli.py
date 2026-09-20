from app.agent import Agent
import sys

def main():
    if len(sys.argv)<2:
        print('Usage: python -m cli "request"'); return 2
    try: print(Agent().run(" ".join(sys.argv[1:])))
    except Exception as e: print(f"ERROR: {e}"); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
