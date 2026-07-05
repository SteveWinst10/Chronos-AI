import cognee
import inspect

def check_apis():
    print(f"Cognee Version: {getattr(cognee, '__version__', 'unknown')}")
    for api in ["improve", "memify"]:
        if hasattr(cognee, api):
            print(f"API '{api}' exists.")
            sig = inspect.signature(getattr(cognee, api))
            print(f"  Signature: {sig}")
        else:
            print(f"API '{api}' NOT found.")

if __name__ == "__main__":
    check_apis()
